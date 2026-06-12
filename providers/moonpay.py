"""
MoonPay fiat-to-crypto provider integration.
Docs: https://dev.moonpay.com
KYC tiers:
  - Level 0: no KYC, email only (limits ~$150/day)
  - Level 1: name + DOB + address (~$2,000/day)
  - Level 2: government ID (~$10,000/day)
"""
import hmac
import hashlib
import base64
import json
import time
import urllib.parse
from config import MOONPAY_API_KEY, MOONPAY_SECRET, MOONPAY_WEBHOOK_SECRET, MOONPAY_ENV, BASE_URL

WEBHOOK_TOLERANCE_SECONDS = 300


MOONPAY_BASE_URLS = {
    "sandbox":    "https://buy-sandbox.moonpay.com",
    "production": "https://buy.moonpay.com",
}

# MoonPay uses lowercase currency codes with network suffix
CRYPTO_MAP = {
    "BTC":   "btc",
    "ETH":   "eth",
    "USDT":  "usdt_erc20",
    "USDC":  "usdc",
    "BNB":   "bnb_bsc",
    "SOL":   "sol",
    "TRX":   "trx",
    "MATIC": "matic_polygon",
}


class MoonPayProvider:
    name = "moonpay"

    def build_widget_url(self, payment: dict) -> str:
        """Build signed MoonPay checkout URL."""
        base = MOONPAY_BASE_URLS.get(MOONPAY_ENV, MOONPAY_BASE_URLS["sandbox"])

        params = {
            "apiKey":            MOONPAY_API_KEY,
            "currencyCode":      CRYPTO_MAP.get(payment["crypto_currency"], "usdt_erc20"),
            "walletAddress":     payment["wallet_address"],
            "baseCurrencyCode":  payment["fiat_currency"].lower(),
            "redirectURL":       f"{BASE_URL}/pay/success/{payment['id']}",
            "externalTransactionId": payment["id"],
            "lockAmount":        "true" if payment.get("amount") else "false",
        }

        if payment.get("amount"):
            params["baseCurrencyAmount"] = str(payment["amount"])

        if payment.get("customer_email"):
            params["email"] = payment["customer_email"]

        # Use payment ID as stable customer ID (not email — customers may reuse different emails)
        params["externalCustomerId"] = payment["id"]

        query = urllib.parse.urlencode(params)

        # Sign the URL with the MoonPay secret
        signed_url = self._sign_url(query)
        return f"{base}?{query}&signature={urllib.parse.quote_plus(signed_url)}"

    def _sign_url(self, query_string: str) -> str:
        """HMAC-SHA256 sign the query string."""
        if not MOONPAY_SECRET or MOONPAY_SECRET.startswith("YOUR_"):
            return "dev-mode-no-sig"
        sig = hmac.new(
            MOONPAY_SECRET.encode(),
            f"?{query_string}".encode(),
            hashlib.sha256,
        ).digest()
        return base64.b64encode(sig).decode()

    def verify_webhook(
        self,
        raw_body: bytes,
        signature_header: str,
        authorization_header: str = "",
    ) -> bool:
        """Verify MoonPay webhook signatures.

        Supports MoonPay Commerce Pay Link/Deposit webhooks (`X-Signature` plus
        `Authorization: Bearer <sharedToken>`) and the on-ramp
        `Moonpay-Signature-V2` format.
        """
        if not MOONPAY_WEBHOOK_SECRET or MOONPAY_WEBHOOK_SECRET.startswith("YOUR_"):
            return True
        if not signature_header:
            return False

        signature_header = signature_header.strip()
        if signature_header.startswith("t=") or ",s=" in signature_header:
            return self._verify_onramp_webhook(raw_body, signature_header)

        token = ""
        auth_scheme, _, auth_value = (authorization_header or "").strip().partition(" ")
        if auth_scheme.lower() == "bearer":
            token = auth_value.strip()

        if not token or not hmac.compare_digest(token, MOONPAY_WEBHOOK_SECRET):
            return False

        signature = signature_header
        if signature.lower().startswith("sha256="):
            signature = signature.split("=", 1)[1]

        expected = hmac.new(
            MOONPAY_WEBHOOK_SECRET.encode(),
            raw_body,
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(expected, signature)

    def _verify_onramp_webhook(self, raw_body: bytes, signature_header: str) -> bool:
        """Verify Moonpay-Signature-V2 header."""
        parts = {}
        for piece in signature_header.split(","):
            if "=" in piece:
                k, v = piece.split("=", 1)
                parts[k.strip()] = v.strip()

        timestamp = parts.get("t", "")
        signature = parts.get("s", "")
        if not timestamp or not signature:
            return False

        try:
            if abs(int(time.time()) - int(timestamp)) > WEBHOOK_TOLERANCE_SECONDS:
                return False
        except ValueError:
            return False

        signed_payload = f"{timestamp}.{raw_body.decode('utf-8', errors='replace')}"
        expected = hmac.new(
            MOONPAY_WEBHOOK_SECRET.encode(),
            signed_payload.encode(),
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(expected, signature)

    def parse_webhook(self, payload: dict) -> dict | None:
        """Normalize MoonPay webhook payloads to internal format."""
        commerce = self._parse_commerce_webhook(payload)
        if commerce:
            return commerce

        return self._parse_onramp_webhook(payload)

    def _parse_onramp_webhook(self, payload: dict) -> dict | None:
        """Normalize MoonPay on-ramp webhook payloads."""
        tx = payload.get("data", payload)  # unwrap envelope; fall back to flat

        status_map = {
            "waitingPayment":  "pending",
            "pending":         "pending",
            "waitingAuthorization": "processing",
            "processing":      "processing",
            "completed":       "completed",
            "failed":          "failed",
            "refunded":        "refunded",
            "cancelled":       "failed",
        }

        return {
            "payment_id":        tx.get("externalTransactionId"),
            "provider_order_id": tx.get("id"),
            "provider_tx_id":    tx.get("cryptoTransactionId"),
            "status":            status_map.get(tx.get("status", ""), "pending"),
            "crypto_amount":     tx.get("cryptoAmount"),
            "exchange_rate":     tx.get("quoteCurrencyAmount"),
            "fee_amount":        tx.get("feeAmount"),
            "raw_status":        tx.get("status"),
        }

    def _parse_commerce_webhook(self, payload: dict) -> dict | None:
        """Normalize MoonPay Commerce Pay Link/Deposit webhook payloads."""
        event_name = str(payload.get("event") or "")
        tx = payload.get("transactionObject")
        if not isinstance(tx, dict):
            tx = _json_obj(payload.get("transaction"))

        is_deposit = event_name.startswith("DEPOSIT_") or bool(payload.get("depositId"))
        if not isinstance(tx, dict) and not is_deposit:
            return None

        tx = tx or {}
        meta = tx.get("meta") if isinstance(tx.get("meta"), dict) else {}
        token_quote = meta.get("tokenQuote") if isinstance(meta.get("tokenQuote"), dict) else {}
        additional = _json_obj(meta.get("additionalJSON"))
        customer_details = meta.get("customerDetails") if isinstance(meta.get("customerDetails"), dict) else {}
        customer_extra = _json_obj(customer_details.get("additionalJSON"))

        raw_status = (
            meta.get("transactionStatus")
            or tx.get("transactionStatus")
            or event_name
        )
        status = _map_commerce_status(str(raw_status or ""))

        payment_id = (
            additional.get("payment_id")
            or additional.get("paymentId")
            or additional.get("externalTransactionId")
            or additional.get("order_id")
            or additional.get("orderId")
            or customer_extra.get("payment_id")
            or customer_extra.get("paymentId")
            or customer_extra.get("externalTransactionId")
            or customer_extra.get("order_id")
            or customer_extra.get("orderId")
            or payload.get("customerId")
            or tx.get("customerId")
            or tx.get("externalCustomerId")
        )

        provider_order_id = (
            tx.get("paylinkId")
            or tx.get("depositId")
            or payload.get("paylinkId")
            or payload.get("depositId")
            or tx.get("id")
        )
        provider_tx_id = (
            tx.get("id")
            or meta.get("transactionSignature")
            or payload.get("transactionId")
            or payload.get("depositId")
            or provider_order_id
        )

        return {
            "payment_id":        payment_id,
            "provider_order_id": provider_order_id,
            "provider_tx_id":    provider_tx_id,
            "status":            status,
            "crypto_amount":     token_quote.get("toAmountDecimal") or payload.get("amount"),
            "exchange_rate":     None,
            "fee_amount":        tx.get("fee") or payload.get("feesPaid"),
            "raw_status":        raw_status,
        }


def _json_obj(value) -> dict:
    if isinstance(value, dict):
        return value
    if not isinstance(value, str) or not value.strip():
        return {}
    try:
        parsed = json.loads(value)
    except (TypeError, ValueError):
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _map_commerce_status(raw_status: str) -> str:
    status = raw_status.strip().upper()
    status_map = {
        "SUCCESS": "completed",
        "COMPLETED": "completed",
        "CONFIRMED": "completed",
        "DEPOSIT_TX_CONFIRMED": "completed",
        "DEPOSIT_TX_ENRICHED": "completed",
        "CREATED": "pending",
        "STARTED": "pending",
        "PENDING": "pending",
        "DEPOSIT_TX_SUBMITTED": "pending",
        "PROCESSING": "processing",
        "FAILED": "failed",
        "CANCELLED": "failed",
        "CANCELED": "failed",
        "ENDED": "failed",
    }
    return status_map.get(status, "pending")

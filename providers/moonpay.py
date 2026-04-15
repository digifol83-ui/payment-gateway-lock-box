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
import urllib.parse
from config import MOONPAY_API_KEY, MOONPAY_SECRET, MOONPAY_ENV, BASE_URL


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

    def verify_webhook(self, raw_body: bytes, signature: str) -> bool:
        """Verify MoonPay webhook signature (base64-encoded HMAC-SHA256)."""
        if not MOONPAY_SECRET or MOONPAY_SECRET.startswith("YOUR_"):
            return True
        if not signature:
            return False
        computed_bytes = hmac.new(
            MOONPAY_SECRET.encode(),
            raw_body,
            hashlib.sha256,
        ).digest()
        computed_b64 = base64.b64encode(computed_bytes).decode()
        return hmac.compare_digest(computed_b64, signature)

    def parse_webhook(self, payload: dict) -> dict | None:
        """Normalize MoonPay webhook to internal format."""
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

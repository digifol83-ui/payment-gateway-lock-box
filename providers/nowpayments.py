"""
NOWPayments crypto-native payment provider.
Docs: https://nowpayments.io/docs/api

Unlike Transak/MoonPay (fiat→crypto via card), NOWPayments accepts
crypto directly from the customer's existing wallet — zero KYC required.

Flow:
  1. Gateway creates a payment invoice via API
  2. Customer is shown wallet address + exact crypto amount to send
  3. NOWPayments detects on-chain payment and sends IPN webhook
  4. Status updated: waiting → confirming → confirmed → finished

Supports 300+ cryptocurrencies.
"""
import hmac
import hashlib
import json
import httpx
import urllib.parse
from config import (
    NOWPAYMENTS_API_KEY, NOWPAYMENTS_IPN_SECRET,
    NOWPAYMENTS_ENV, BASE_URL,
)

_API_URLS = {
    "sandbox":    "https://api-sandbox.nowpayments.io/v1",
    "production": "https://api.nowpayments.io/v1",
}

# NOWPayments currency codes (lowercase)
CRYPTO_MAP = {
    "BTC":   "btc",
    "ETH":   "eth",
    "USDT":  "usdterc20",
    "USDC":  "usdc",
    "BNB":   "bnbbsc",
    "SOL":   "sol",
    "TRX":   "trx",
    "MATIC": "maticpolygon",
    "LTC":   "ltc",
    "DOGE":  "doge",
    "XRP":   "xrp",
}

STATUS_MAP = {
    "waiting":        "pending",
    "confirming":     "processing",
    "confirmed":      "processing",
    "sending":        "processing",
    "partially_paid": "processing",
    "finished":       "completed",
    "failed":         "failed",
    "refunded":       "refunded",
    "expired":        "failed",
}


class NowPaymentsProvider:
    name = "nowpayments"

    def _base(self):
        return _API_URLS.get(NOWPAYMENTS_ENV, _API_URLS["sandbox"])

    def _headers(self):
        return {
            "x-api-key": NOWPAYMENTS_API_KEY,
            "Content-Type": "application/json",
        }

    async def create_invoice(self, payment: dict) -> dict:
        """
        Create a NOWPayments invoice and return the full API response.
        Callers should persist response['payment_id'] as provider_order_id
        and response['pay_address'] / response['pay_amount'] to the payment record.
        """
        body = {
            "price_amount":       payment["amount"],
            "price_currency":     payment["fiat_currency"].lower(),
            "pay_currency":       CRYPTO_MAP.get(payment["crypto_currency"], "btc"),
            "order_id":           payment["id"],
            "order_description":  payment.get("description") or "BeastPay payment",
            "ipn_callback_url":   f"{BASE_URL}/webhooks/nowpayments",
            "success_url":        f"{BASE_URL}/pay/success/{payment['id']}",
            "cancel_url":         f"{BASE_URL}/pay/{payment.get('link_id', '')}",
        }
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{self._base()}/payment",
                headers=self._headers(),
                json=body,
            )
            resp.raise_for_status()
            return resp.json()

    def build_widget_url(self, payment: dict) -> str:
        """
        Return the NOWPayments hosted payment page URL.

        Requires provider_order_id (the NOWPayments payment_id) to be set
        on the payment record before calling — this is done by initiate_payment()
        after create_invoice() completes.

        Falls back to a generic invoice link if provider_order_id is missing
        (should not happen in normal flow).
        """
        if payment.get("provider_order_id"):
            return f"https://nowpayments.io/payment/?iid={payment['provider_order_id']}"
        # Fallback: direct payment page (no IID, generic entry)
        params = urllib.parse.urlencode({
            "amount":    payment["amount"],
            "currency":  payment["fiat_currency"],
            "coin":      CRYPTO_MAP.get(payment["crypto_currency"], "btc"),
        })
        return f"https://nowpayments.io/payment/?{params}"

    def verify_webhook(self, raw_body: bytes, signature: str) -> bool:
        """Verify NOWPayments IPN HMAC-SHA512 signature.

        NOWPayments signs a compacted JSON representation of the payload with
        ALL object keys sorted recursively (not just top-level).
        The signature arrives in the ``x-nowpayments-sig`` request header as a
        lowercase hex string.

        Returns True (bypass) when NOWPAYMENTS_IPN_SECRET is not configured so
        that local development still works without credentials.
        """
        if not NOWPAYMENTS_IPN_SECRET or NOWPAYMENTS_IPN_SECRET.startswith("YOUR_"):
            return True
        if not signature:
            return False
        try:
            payload = json.loads(raw_body)
            # sort_keys=True handles recursive key sorting at all nesting levels
            sorted_payload = json.dumps(
                payload, sort_keys=True, separators=(",", ":")
            ).encode()
            computed = hmac.new(
                NOWPAYMENTS_IPN_SECRET.encode(),
                sorted_payload,
                hashlib.sha512,
            ).hexdigest()
            # NOWPayments sends the signature in lowercase hex
            return hmac.compare_digest(computed, signature.lower())
        except Exception:
            return False

    def parse_webhook(self, payload: dict) -> dict | None:
        """Normalize NOWPayments IPN payload to the internal payment update format.

        IPN fields reference:
          payment_id        — NOWPayments internal payment identifier (int)
          order_id          — our payment UUID passed as order_id at creation
          payment_status    — waiting / confirming / confirmed / finished / failed / expired
          pay_amount        — crypto amount the customer should send
          actually_paid     — crypto amount actually received so far
          price_amount      — fiat amount (what we charged in USD/EUR/etc.)
          pay_address       — destination wallet address
          outcome_amount    — net crypto amount after fees (present on finished payments)
        """
        now_payment_id = payload.get("payment_id")
        return {
            "payment_id":         payload.get("order_id"),          # our UUID
            "provider_order_id":  str(now_payment_id) if now_payment_id else "",
            "provider_tx_id":     str(now_payment_id) if now_payment_id else None,
            "status":             STATUS_MAP.get(payload.get("payment_status", ""), "pending"),
            "crypto_amount":      payload.get("actually_paid"),
            "exchange_rate":      None,  # not directly provided; derive externally if needed
            "fee_amount":         None,
            "pay_address":        payload.get("pay_address"),
            "raw_status":         payload.get("payment_status"),
        }

    async def get_payment_status(self, provider_order_id: str) -> dict:
        """Poll payment status from NOWPayments by their payment_id."""
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{self._base()}/payment/{provider_order_id}",
                headers=self._headers(),
            )
            resp.raise_for_status()
            data = resp.json()
            return {
                "status":        STATUS_MAP.get(data.get("payment_status", ""), "pending"),
                "pay_address":   data.get("pay_address"),
                "pay_amount":    data.get("pay_amount"),
                "actually_paid": data.get("actually_paid"),
                "raw_status":    data.get("payment_status"),
            }

    async def get_currencies(self) -> list:
        """Return list of supported currencies from NOWPayments."""
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{self._base()}/currencies",
                headers=self._headers(),
            )
            resp.raise_for_status()
            return resp.json().get("currencies", [])

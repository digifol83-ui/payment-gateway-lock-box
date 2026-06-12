"""
CoinRemitter — non-custodial crypto payment gateway.
Docs: https://coinremitter.com/docs/v3

Each coin has its own wallet on CoinRemitter with a separate API key + password.
We use COINREMITTER_COIN (default BTC) as the active wallet and
COINREMITTER_API_KEY / COINREMITTER_API_PASSWORD for its credentials.

Flow:
  1. POST /api/v3/{COIN}/create-invoice → returns invoice_id + hosted checkout URL
  2. Customer pays from their own wallet to the address shown
  3. CoinRemitter POSTs form-data to notify_url with `hash` signature
  4. Status: Pending → Paid (Confirmed) / Expired / Cancelled
"""
import hashlib
import json
import httpx
from config import (
    COINREMITTER_API_KEY,
    COINREMITTER_API_PASSWORD,
    COINREMITTER_COIN,
    BASE_URL,
)

API_BASE = "https://api.coinremitter.com/api/v3"

COIN_MAP = {
    "BTC":  "BTC",
    "ETH":  "ETH",
    "LTC":  "LTC",
    "DOGE": "DOGE",
    "TRX":  "TRX",
    "USDT": "USDTTRX",
    "USDC": "USDCTRX",
    "BCH":  "BCH",
    "DASH": "DASH",
}

STATUS_MAP = {
    "Pending":    "pending",
    "Processing": "processing",
    "Paid":       "completed",
    "Confirmed":  "completed",
    "Completed":  "completed",
    "Expired":    "failed",
    "Cancelled":  "failed",
    "Failed":     "failed",
}


class CoinRemitterProvider:
    name = "coinremitter"

    def _coin(self, override: str = None) -> str:
        symbol = (override or COINREMITTER_COIN or "BTC").upper()
        return COIN_MAP.get(symbol, symbol)

    def _url(self, coin: str, action: str) -> str:
        return f"{API_BASE}/{coin}/{action}"

    def _form(self, extra: dict = None) -> dict:
        body = {
            "api_key":  COINREMITTER_API_KEY,
            "password": COINREMITTER_API_PASSWORD,
        }
        if extra:
            body.update(extra)
        return body

    async def create_invoice(self, payment: dict) -> dict:
        """Create a CoinRemitter invoice. Caller persists data.invoice_id as
        provider_order_id and data.url as the hosted checkout link."""
        coin = self._coin(payment.get("crypto_currency"))
        body = self._form({
            "amount":       str(payment["amount"]),
            "currency":     payment.get("fiat_currency", "USD"),
            "name":         payment.get("description") or "BeastPay Invoice",
            "description":  payment.get("description") or "BeastPay payment",
            "notify_url":   f"{BASE_URL}/webhooks/coinremitter",
            "success_url":  f"{BASE_URL}/pay/success/{payment['id']}",
            "fail_url":     f"{BASE_URL}/pay/{payment.get('link_id', '')}",
            "custom_data1": payment["id"],
            "expire_time":  3600,
        })
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(self._url(coin, "create-invoice"), data=body)
            resp.raise_for_status()
            return resp.json()

    def build_widget_url(self, payment: dict) -> str:
        """Return the hosted checkout URL.

        CoinRemitter returns the URL in create-invoice response.data.url —
        the caller should persist it on the payment record before calling this.
        """
        return payment.get("widget_url") or payment.get("checkout_url") or ""

    async def get_payment_status(self, provider_order_id: str, coin: str = None) -> dict:
        """Poll an invoice by id."""
        coin_code = self._coin(coin)
        body = self._form({"invoice_id": provider_order_id})
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(self._url(coin_code, "get-invoice"), data=body)
            resp.raise_for_status()
            data = resp.json() or {}
            inv = (data.get("data") or {})
            return {
                "status":       STATUS_MAP.get(inv.get("status", ""), "pending"),
                "raw_status":   inv.get("status"),
                "amount_paid":  inv.get("amount_paid"),
                "pay_address":  inv.get("address"),
                "transactions": inv.get("transactions") or [],
            }

    def verify_webhook(self, form_data: dict) -> bool:
        """Verify CoinRemitter webhook hash.

        CoinRemitter signs each callback as:
            hash = md5( json(payload_without_hash, sorted) + wallet_password )

        Returns True (bypass) when no password is configured so dev still works.
        """
        if not COINREMITTER_API_PASSWORD:
            return True
        received = (form_data.get("hash") or "").lower()
        if not received:
            return False
        payload = {k: v for k, v in form_data.items() if k != "hash"}
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        computed = hashlib.md5((canonical + COINREMITTER_API_PASSWORD).encode()).hexdigest().lower()
        return computed == received

    def parse_webhook(self, payload: dict) -> dict | None:
        """Normalize CoinRemitter webhook to internal payment update format."""
        tx = payload.get("transaction")
        tx_id = None
        if isinstance(tx, dict):
            tx_id = tx.get("txid") or tx.get("id")
        elif isinstance(tx, list) and tx:
            first = tx[0] or {}
            tx_id = first.get("txid") or first.get("id")
        return {
            "payment_id":        payload.get("custom_data1"),
            "provider_order_id": payload.get("invoice_id"),
            "provider_tx_id":    tx_id,
            "status":             STATUS_MAP.get(payload.get("status", ""), "pending"),
            "crypto_amount":     payload.get("amount_paid") or payload.get("amount"),
            "pay_address":       payload.get("address"),
            "raw_status":        payload.get("status"),
        }

    async def get_balance(self, coin: str = None) -> dict:
        """Return wallet balance for the configured (or overridden) coin."""
        coin_code = self._coin(coin)
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(self._url(coin_code, "get-balance"), data=self._form())
            resp.raise_for_status()
            return resp.json()

    async def validate_address(self, address: str, coin: str = None) -> dict:
        """Validate a destination address for the configured coin."""
        coin_code = self._coin(coin)
        body = self._form({"address": address})
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(self._url(coin_code, "validate-address"), data=body)
            resp.raise_for_status()
            return resp.json()

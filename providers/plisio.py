"""
Plisio crypto payment gateway provider.
Docs: https://plisio.net/api
Non-custodial, zero-KYC crypto invoices.
"""
import hashlib
import hmac
import json
import urllib.parse
import aiohttp
from config import PLISIO_API_KEY, BASE_URL

PLISIO_API_BASE = "https://api.plisio.net/api/v1"


class PlisioProvider:
    name = "plisio"

    def __init__(self):
        self.api_key = PLISIO_API_KEY

    def is_configured(self) -> bool:
        return bool(self.api_key and not self.api_key.startswith("YOUR_"))

    # ── Invoice creation ─────────────────────────────────────────────────

    async def create_invoice(self, payment: dict) -> dict:
        """Create a Plisio crypto invoice.

        payment expects:
          - id: internal payment ID
          - amount: fiat amount (USD)
          - fiat_currency: e.g. USD, EUR
          - crypto_currency: e.g. BTC, ETH, USDT
          - customer_email: optional
          - description: optional
        """
        if not self.is_configured():
            raise ValueError("PLISIO_API_KEY not configured")

        order_name = payment.get("description") or f"BeastPay order {payment['id']}"
        order_number = payment["id"]

        params = {
            "api_key": self.api_key,
            "order_name": order_name,
            "order_number": order_number,
            "source_currency": (payment.get("fiat_currency") or "USD").upper(),
            "source_amount": float(payment.get("amount") or payment.get("fiat_amount") or 0),
            "currency": (payment.get("crypto_currency") or "USDT").upper(),
            "callback_url": f"{BASE_URL}/api/webhooks/deliver/plisio",
            "success_callback_url": f"{BASE_URL}/pay/success/{order_number}",
            "email": payment.get("customer_email") or "",
            "plugin": "BeastPay",
            "version": "1.0.0",
        }

        query = "&".join(f"{k}={v}" for k, v in params.items() if v not in (None, "", 0) or k == "email")

        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{PLISIO_API_BASE}/invoices/new?{query}",
                timeout=15,
            ) as resp:
                body = await resp.json()

        if body.get("status") != "success":
            error_msg = body.get("data", {}).get("message") or body.get("message") or "Unknown Plisio error"
            raise ValueError(f"Plisio invoice creation failed: {error_msg}")

        data = body.get("data", {})
        return {
            "flag": 1,
            "msg": "Invoice created",
            "data": {
                "txn_id": data.get("txn_id"),
                "invoice_url": data.get("invoice_url"),
                "invoice_total_sum": data.get("invoice_total_sum"),
                "currency": payment.get("crypto_currency", "USDT").upper(),
            },
        }

    # ── Status check ─────────────────────────────────────────────────────

    async def get_status(self, txn_id: str) -> dict:
        """Check Plisio invoice/transaction status."""
        if not self.is_configured():
            raise ValueError("PLISIO_API_KEY not configured")

        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{PLISIO_API_BASE}/operations/{txn_id}",
                params={"api_key": self.api_key},
                timeout=10,
            ) as resp:
                body = await resp.json()

        if body.get("status") != "success":
            return {"flag": 0, "msg": body.get("message", "Status check failed")}

        data = body.get("data", {})
        return {
            "flag": 1,
            "data": {
                "txn_id": data.get("txn_id"),
                "status": self._map_status(data.get("status", "")),
                "amount": data.get("amount"),
                "received_amount": data.get("sum"),
                "currency": data.get("currency"),
                "confirmations": data.get("confirmations", 0),
                "tx_url": data.get("tx_url"),
                "params": data.get("params", {}),
            },
        }

    def _map_status(self, raw_status: str) -> str:
        status_map = {
            "new": "pending",
            "pending": "pending",
            "completed": "completed",
            "expired": "failed",
            "error": "failed",
            "cancelled": "failed",
            "mismatch": "failed",
        }
        return status_map.get(raw_status.lower(), "pending")

    # ── Webhook verification ─────────────────────────────────────────────

    def verify_webhook(self, raw_body: bytes, signature: str) -> bool:
        """Verify Plisio webhook using HMAC-SHA256."""
        if not self.api_key:
            return True  # Allow unverified in dev

        try:
            body_str = raw_body.decode("utf-8")
        except Exception:
            return False

        expected = hmac.new(
            self.api_key.encode(),
            body_str.encode(),
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(expected, signature)

    def parse_webhook(self, payload: dict) -> dict | None:
        """Normalize Plisio webhook into internal format."""
        # Plisio sends: {"verify_hash": "...", "txn_id": "...", "status": "...", ...}
        data = payload.get("data", payload)

        status_map = {
            "new": "pending",
            "pending": "pending",
            "completed": "completed",
            "expired": "failed",
            "error": "failed",
            "cancelled": "failed",
            "mismatch": "failed",
        }

        return {
            "payment_id": data.get("order_number") or data.get("order_name"),
            "provider_order_id": data.get("txn_id"),
            "provider_tx_id": data.get("txn_id"),
            "status": status_map.get(str(data.get("status", "")).lower(), "pending"),
            "crypto_amount": data.get("amount"),
            "exchange_rate": None,
            "fee_amount": None,
            "raw_status": data.get("status"),
        }

    # ── Balance ──────────────────────────────────────────────────────────

    async def get_balance(self) -> dict:
        """Get Plisio account balances."""
        if not self.is_configured():
            raise ValueError("PLISIO_API_KEY not configured")

        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{PLISIO_API_BASE}/balances",
                params={"api_key": self.api_key},
                timeout=10,
            ) as resp:
                body = await resp.json()

        if body.get("status") != "success":
            return {"flag": 0, "msg": body.get("message", "Balance check failed")}

        return {
            "flag": 1,
            "msg": "Balance retrieved",
            "data": body.get("data", {}),
        }

    # ── Utility ──────────────────────────────────────────────────────────

    def _sign(self, data: str) -> str:
        """Legacy signing — Plisio v1 uses HMAC-SHA256."""
        if not self.api_key:
            return ""
        return hmac.new(
            self.api_key.encode(),
            data.encode(),
            hashlib.sha256,
        ).hexdigest()

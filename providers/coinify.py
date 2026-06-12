"""Coinify fiat-to-crypto gateway — regulated European payment processor.

Coinify is a regulated fiat-to-crypto gateway operating in 100+ countries
supporting AED, USD, EUR, GBP, and 50+ fiat currencies.
Offers card payments, bank transfers, and instant crypto settlement.

Dashboard: https://coinify.com
API Docs: https://apidocs.coinify.com
Base URL: https://api.coinify.com

Flow:
1. POST /v3/invoices to create a payment invoice
2. Redirect user to the payment page URL
3. Webhook callback or poll GET /v3/invoices/{id} for status
"""

from __future__ import annotations

import hashlib
import hmac
import time
from typing import Any

import httpx

from config import (
    BASE_URL,
    COINIFY_API_KEY,
    COINIFY_SECRET,
    COINIFY_ENV,
)

API_BASE_MAP = {
    "sandbox": "https://api.sandbox.coinify.com",
    "production": "https://api.coinify.com",
}

STATUS_MAP = {
    "new": "pending",
    "pending": "pending",
    "processing": "pending",
    "completed": "completed",
    "paid": "completed",
    "confirmed": "completed",
    "cancelled": "failed",
    "expired": "failed",
    "failed": "failed",
    "refunded": "failed",
}


class CoinifyProvider:
    """Coinify fiat-to-crypto payment provider.

    Creates a fiat-to-crypto buy invoice via Coinify's API and returns
    a hosted payment page URL for the customer.
    """

    name = "coinify"

    def __init__(
        self,
        api_key: str | None = None,
        secret: str | None = None,
        env: str | None = None,
        api_base: str | None = None,
        public_base_url: str | None = None,
    ):
        self.api_key = (api_key if api_key is not None else COINIFY_API_KEY).strip()
        self.secret = (secret if secret is not None else COINIFY_SECRET).strip()
        self.env = (env if env is not None else COINIFY_ENV or "sandbox").strip().lower()
        self.api_base = (
            api_base if api_base is not None else API_BASE_MAP.get(self.env, API_BASE_MAP["sandbox"])
        ).rstrip("/")
        self.public_base_url = (public_base_url or BASE_URL).rstrip("/")

    def is_configured(self) -> dict[str, Any]:
        enabled = bool(self.api_key)
        return {
            "enabled": enabled,
            "mode": "live" if self.env == "production" else "sandbox",
            "provider": self.name,
        }

    def _headers(self, body: str = "") -> dict[str, str]:
        if not self.api_key:
            raise RuntimeError("COINIFY_API_KEY is not configured")
        headers = {
            "Content-Type": "application/json",
            "X-Coinify-API-Key": self.api_key,
        }
        if self.secret and body:
            headers["X-Coinify-Signature"] = hmac.new(
                self.secret.encode(),
                body.encode(),
                hashlib.sha256,
            ).hexdigest()
        return headers

    async def create_order(self, payment: dict[str, Any]) -> dict[str, Any]:
        """Create a Coinify invoice for fiat-to-crypto purchase.

        Args:
            payment: dict with:
                - amount (float): order amount in fiat
                - currency (str): "USD", "AED", "EUR", etc.
                - reference (str): your internal payment ID
                - customer_email (str): buyer's email
                - crypto_currency (str): desired crypto, e.g. "BTC", "USDT"
                - description (str, optional)

        Returns:
            dict with order_id, url, status, raw
        """
        reference = payment["reference"]
        fiat_currency = (payment.get("currency") or payment.get("fiat_currency") or "USD").upper()
        crypto_currency = (payment.get("crypto_currency") or "BTC").upper()
        amount = float(payment["amount"])
        email = payment.get("customer_email", "")
        description = (
            payment.get("description")
            or payment.get("message")
            or f"BeastPay payment {reference}"
        )

        body = {
            "amount": amount,
            "currency": fiat_currency,
            "plugin_name": "BeastPay",
            "plugin_version": "1.0.0",
            "description": description,
            "custom": str(reference),
            "callback_url": f"{self.public_base_url}/webhooks/coinify",
            "callback_email": email or "",
            "return_url": payment.get(
                "success_url",
                f"{self.public_base_url}/pay/success/{reference}",
            ),
            "cancel_url": payment.get(
                "cancel_url",
                f"{self.public_base_url}/pay/{reference}",
            ),
            "buy_currency": crypto_currency,
        }

        import json

        body_str = json.dumps(body, separators=(",", ":"))

        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                f"{self.api_base}/v3/invoices",
                headers=self._headers(body_str),
                json=body,
            )
            resp.raise_for_status()
            data = resp.json()

        invoice = data.get("data", data)
        invoice_id = invoice.get("id") or invoice.get("invoice_id")
        payment_url = invoice.get("payment_url") or invoice.get("url")

        return {
            "order_id": invoice_id,
            "session_id": payment_url,
            "url": payment_url,
            "status": STATUS_MAP.get(str(invoice.get("state", "")).lower(), "pending"),
            "raw_status": invoice.get("state"),
            "raw": data,
        }

    async def get_status(self, invoice_id: str) -> dict[str, Any]:
        """Fetch invoice status from Coinify."""
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{self.api_base}/v3/invoices/{invoice_id}",
                headers=self._headers(),
            )
            resp.raise_for_status()
            data = resp.json()

        invoice = data.get("data", data)
        raw_state = str(invoice.get("state") or "").lower()
        return {
            "provider_order_id": invoice.get("id") or invoice_id,
            "status": STATUS_MAP.get(raw_state, "pending"),
            "raw_status": raw_state,
            "raw": data,
        }

    def verify_webhook(self, raw_body: bytes, signature: str | None) -> bool:
        """Verify Coinify webhook signature."""
        if not self.secret:
            return True
        if not signature:
            return False
        computed = hmac.new(
            self.secret.encode(),
            raw_body,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(computed, signature.lower())

    def parse_webhook(self, payload: dict[str, Any]) -> dict[str, Any] | None:
        """Parse Coinify webhook payload into normalized status."""
        invoice_id = payload.get("id") or payload.get("invoice_id")
        if not invoice_id:
            return None

        raw_state = str(payload.get("state") or payload.get("status") or "").lower()
        status = STATUS_MAP.get(raw_state)
        if not status:
            if raw_state in ("paid", "confirmed", "complete"):
                status = "completed"
            elif raw_state in ("fail", "decline", "refund"):
                status = "failed"
            else:
                status = "pending"

        return {
            "payment_id": payload.get("custom") or payload.get("reference"),
            "provider_order_id": invoice_id,
            "status": status,
            "raw_status": raw_state,
        }

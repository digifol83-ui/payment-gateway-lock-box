"""Kyrrex crypto payment gateway — Dubai-based, regulated.

Kyrrex Pay: online crypto payment processing.
Kyrrex On/Off-Ramp: fiat-to-crypto and crypto-to-fiat conversion.

Docs: https://kyrrex.com/global/payments
KYB: B2B partner onboarding at https://kyrrex.com

This provider creates a hosted checkout session via Kyrrex Pay API
and returns a redirect URL for the user to complete payment.
"""

from __future__ import annotations

import hashlib
import hmac
import time
from typing import Any
from urllib.parse import urlencode

import httpx

from config import (
    BASE_URL,
    KYRREX_API_KEY,
    KYRREX_SECRET,
    KYRREX_WEBHOOK_SECRET,
    KYRREX_ENV,
)

API_BASE_MAP = {
    "sandbox": "https://api.sandbox.kyrrex.com",
    "production": "https://api.kyrrex.com",
}

STATUS_MAP = {
    "pending": "pending",
    "processing": "pending",
    "waiting": "pending",
    "confirming": "pending",
    "paid": "completed",
    "completed": "completed",
    "success": "completed",
    "failed": "failed",
    "expired": "failed",
    "cancelled": "failed",
    "refunded": "failed",
}


class KyrrexProvider:
    """Kyrrex Pay + On/Off-Ramp provider.

    Flow:
    1. POST /api/v1/invoice to create an invoice
    2. Redirect user to the invoice URL
    3. Receive webhook or poll GET /api/v1/invoice/{id} for status
    """

    name = "kyrrex"

    def __init__(
        self,
        api_key: str | None = None,
        secret: str | None = None,
        webhook_secret: str | None = None,
        env: str | None = None,
        api_base: str | None = None,
        public_base_url: str | None = None,
    ):
        self.api_key = (api_key if api_key is not None else KYRREX_API_KEY).strip()
        self.secret = (secret if secret is not None else KYRREX_SECRET).strip()
        self.webhook_secret = (
            webhook_secret if webhook_secret is not None else KYRREX_WEBHOOK_SECRET
        ).strip()
        self.env = (env if env is not None else KYRREX_ENV or "sandbox").strip().lower()
        self.api_base = (
            api_base if api_base is not None else API_BASE_MAP.get(self.env, API_BASE_MAP["sandbox"])
        ).rstrip("/")
        self.public_base_url = (public_base_url or BASE_URL).rstrip("/")

    def is_configured(self) -> dict[str, Any]:
        enabled = bool(self.api_key) and bool(self.secret)
        return {
            "enabled": enabled,
            "mode": "live" if self.env == "production" else "sandbox",
            "provider": self.name,
        }

    def _sign(self, payload: str) -> str:
        """Generate HMAC-SHA256 signature for Kyrrex API."""
        return hmac.new(
            self.secret.encode(),
            payload.encode(),
            hashlib.sha256,
        ).hexdigest()

    def _headers(self, body: str = "") -> dict[str, str]:
        if not self.api_key:
            raise RuntimeError("KYRREX_API_KEY is not configured")
        headers = {
            "Content-Type": "application/json",
            "X-API-Key": self.api_key,
        }
        if self.secret and body:
            headers["X-Signature"] = self._sign(body)
        return headers

    async def create_order(self, payment: dict[str, Any]) -> dict[str, Any]:
        """Create a Kyrrex invoice and return the redirect URL.

        Args:
            payment: dict with:
                - amount (float): order amount in fiat
                - currency (str): "AED", "USD", etc.
                - reference (str): your internal payment ID
                - customer_email (str): buyer's email
                - crypto_currency (str): desired crypto, e.g. "USDT"
                - description (str, optional)

        Returns:
            dict with order_id, url, status, raw
        """
        reference = payment["reference"]
        fiat_currency = (payment.get("currency") or payment.get("fiat_currency") or "AED").upper()
        crypto_currency = (payment.get("crypto_currency") or "USDT").upper()
        amount = str(payment["amount"])
        email = payment.get("customer_email", "")
        description = (
            payment.get("description")
            or payment.get("message")
            or f"BeastPay payment {reference}"
        )
        success_url = payment.get(
            "success_url",
            f"{self.public_base_url}/pay/success/{reference}",
        )
        cancel_url = payment.get("cancel_url", f"{self.public_base_url}/pay/{reference}")

        body = {
            "amount": amount,
            "currency": fiat_currency,
            "crypto_currency": crypto_currency,
            "order_id": reference,
            "description": description,
            "customer_email": email,
            "success_url": success_url,
            "cancel_url": cancel_url,
            "callback_url": f"{self.public_base_url}/webhooks/kyrrex",
        }

        import json

        body_str = json.dumps(body, separators=(",", ":"))

        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                f"{self.api_base}/api/v1/invoice",
                headers=self._headers(body_str),
                json=body,
            )
            resp.raise_for_status()
            data = resp.json()

        invoice_url = data.get("invoice_url") or data.get("payment_url") or data.get("url")
        invoice_id = data.get("invoice_id") or data.get("id")

        return {
            "order_id": invoice_id,
            "session_id": invoice_url,
            "url": invoice_url,
            "status": STATUS_MAP.get(str(data.get("status", "")).lower(), "pending"),
            "raw_status": data.get("status"),
            "raw": data,
        }

    async def get_status(self, invoice_id: str) -> dict[str, Any]:
        """Fetch invoice status from Kyrrex."""
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{self.api_base}/api/v1/invoice/{invoice_id}",
                headers=self._headers(),
            )
            resp.raise_for_status()
            data = resp.json()

        raw_status = str(data.get("status") or "").lower()
        return {
            "provider_order_id": data.get("invoice_id") or data.get("id"),
            "status": STATUS_MAP.get(raw_status, "pending"),
            "raw_status": raw_status,
            "raw": data,
        }

    def verify_webhook(self, raw_body: bytes, signature: str | None) -> bool:
        """Verify webhook signature."""
        if not self.webhook_secret:
            return True
        if not signature:
            return False
        computed = hmac.new(
            self.webhook_secret.encode(),
            raw_body,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(computed, signature.lower())

    def parse_webhook(self, payload: dict[str, Any]) -> dict[str, Any] | None:
        """Parse Kyrrex webhook payload into normalized status."""
        invoice_id = payload.get("invoice_id") or payload.get("id")
        if not invoice_id:
            return None

        raw_status = str(payload.get("status") or "").lower()
        status = STATUS_MAP.get(raw_status)
        if not status:
            if raw_status in ("paid", "success", "complete"):
                status = "completed"
            elif raw_status in ("fail", "error", "decline"):
                status = "failed"
            else:
                status = "pending"

        return {
            "payment_id": payload.get("order_id") or payload.get("reference"),
            "provider_order_id": invoice_id,
            "status": status,
            "raw_status": raw_status,
        }

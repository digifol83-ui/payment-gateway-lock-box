"""Ziina Payment Intent provider.

Docs:
- https://docs.ziina.com/api-reference/payment-intent/index
- https://docs.ziina.com/api-reference/webhook/index
"""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
import hashlib
import hmac
from typing import Any

import httpx

from config import BASE_URL, ZIINA_API_TOKEN, ZIINA_ENV, ZIINA_WEBHOOK_SECRET


API_BASE = "https://api-v2.ziina.com/api"

STATUS_MAP = {
    "requires_payment_instrument": "pending",
    "requires_user_action": "pending",
    "pending": "pending",
    "completed": "completed",
    "failed": "failed",
}


class ZiinaProvider:
    name = "ziina"

    def __init__(
        self,
        api_token: str | None = None,
        webhook_secret: str | None = None,
        env: str | None = None,
        api_base: str | None = None,
        public_base_url: str | None = None,
    ):
        self.api_token = (api_token if api_token is not None else ZIINA_API_TOKEN).strip()
        self.webhook_secret = (
            webhook_secret if webhook_secret is not None else ZIINA_WEBHOOK_SECRET
        ).strip()
        self.env = (env if env is not None else ZIINA_ENV or "sandbox").strip().lower()
        self.api_base = (api_base or API_BASE).rstrip("/")
        self.public_base_url = (public_base_url or BASE_URL).rstrip("/")

    def is_configured(self) -> dict[str, Any]:
        token = self.api_token
        enabled = bool(token) and not token.startswith(("YOUR_", "zk_test_sichermayor_"))
        return {
            "enabled": enabled,
            "mode": "live" if self.env == "production" else "sandbox",
            "provider": self.name,
        }

    def _headers(self) -> dict[str, str]:
        if not self.api_token:
            raise RuntimeError("ZIINA_API_TOKEN is not configured")
        return {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }

    @staticmethod
    def _minor_units(amount: Any) -> int:
        value = Decimal(str(amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return int(value * 100)

    async def create_order(self, payment: dict[str, Any]) -> dict[str, Any]:
        """Create a Ziina Payment Intent and return the legacy checkout shape."""
        reference = payment["reference"]
        currency = (payment.get("currency") or payment.get("fiat_currency") or "AED").upper()
        description = (
            payment.get("description")
            or payment.get("message")
            or f"BeastPay payment {reference}"
        )
        success_url = payment.get(
            "success_url",
            f"{self.public_base_url}/pay/success/{reference}"
            "?provider=ziina&provider_payment_id={PAYMENT_INTENT_ID}",
        )
        cancel_url = payment.get("cancel_url", f"{self.public_base_url}/pay/{reference}")
        failure_url = payment.get("failure_url", f"{self.public_base_url}/pay/{reference}?status=failed")

        body = {
            "amount": self._minor_units(payment["amount"]),
            "currency_code": currency,
            "message": description,
            "success_url": success_url,
            "cancel_url": cancel_url,
            "failure_url": failure_url,
            "test": bool(payment.get("test", self.env != "production")),
            "allow_tips": False,
        }

        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                f"{self.api_base}/payment_intent",
                headers=self._headers(),
                json=body,
            )
            resp.raise_for_status()
            data = resp.json()

        redirect_url = data.get("redirect_url") or data.get("embedded_url")
        return {
            "order_id": data.get("id"),
            "payment_intent_id": data.get("id"),
            "session_id": redirect_url,
            "url": redirect_url,
            "status": STATUS_MAP.get(data.get("status"), "pending"),
            "raw_status": data.get("status"),
            "raw": data,
        }

    async def get_payment_intent(self, payment_intent_id: str) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{self.api_base}/payment_intent/{payment_intent_id}",
                headers=self._headers(),
            )
            resp.raise_for_status()
            data = resp.json()
        return {
            "provider_order_id": data.get("id"),
            "status": STATUS_MAP.get(data.get("status"), "pending"),
            "raw_status": data.get("status"),
            "raw": data,
        }

    def verify_webhook(self, raw_body: bytes, signature: str | None) -> bool:
        """Verify Ziina's X-Hmac-Signature header when a secret is configured."""
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
        if payload.get("event") and payload.get("event") != "payment_intent.status.updated":
            return None

        data = payload.get("data") or payload.get("payment_intent") or payload.get("order") or {}
        if not data:
            return None

        raw_status = str(data.get("status") or "").lower()
        status = STATUS_MAP.get(raw_status)
        if not status:
            return None

        metadata = data.get("metadata") or {}
        provider_order_id = data.get("id") or data.get("payment_intent_id") or data.get("orderId")
        payment_id = (
            metadata.get("payment_id")
            or data.get("reference")
            or data.get("referenceNo")
            or data.get("client_reference_id")
        )

        return {
            "payment_id": payment_id,
            "provider_order_id": provider_order_id,
            "status": status,
            "raw_status": raw_status,
        }

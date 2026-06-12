"""ChangeNOW fiat-to-crypto gateway — non-custodial instant exchange.

ChangeNOW offers non-custodial crypto exchanges and fiat-to-crypto
on-ramp supporting 1000+ cryptocurrencies, 60+ fiat currencies,
and settlement in 5-30 minutes.

Dashboard: https://changenow.io
API Docs: https://docs.changenow.io
Base URL: https://api.changenow.io/v2

Flow:
1. POST /v2/exchange to create an exchange (fiat→crypto or crypto→crypto)
2. Track via GET /v2/exchange/{id} or webhook
"""

from __future__ import annotations

import hashlib
import hmac
from typing import Any

import httpx

from config import (
    BASE_URL,
    CHANGENOW_API_KEY,
    CHANGENOW_SECRET,
    CHANGENOW_ENV,
)

STATUS_MAP = {
    "new": "pending",
    "waiting": "pending",
    "confirming": "pending",
    "exchanging": "pending",
    "sending": "pending",
    "finished": "completed",
    "completed": "completed",
    "success": "completed",
    "failed": "failed",
    "refunded": "failed",
    "expired": "failed",
    "overdue": "failed",
}


class ChangeNOWProvider:
    """ChangeNOW fiat-to-crypto exchange provider.

    Creates a fiat-to-crypto exchange via ChangeNOW's API and returns
    a redirect URL or payment details for the customer.
    """

    name = "changenow"

    def __init__(
        self,
        api_key: str | None = None,
        secret: str | None = None,
        env: str | None = None,
        api_base: str | None = None,
        public_base_url: str | None = None,
    ):
        self.api_key = (api_key if api_key is not None else CHANGENOW_API_KEY).strip()
        self.secret = (secret if secret is not None else CHANGENOW_SECRET).strip()
        self.env = (env if env is not None else CHANGENOW_ENV or "sandbox").strip().lower()
        self.api_base = (
            api_base if api_base is not None else "https://api.changenow.io/v2"
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
            raise RuntimeError("CHANGENOW_API_KEY is not configured")
        headers = {
            "Content-Type": "application/json",
            "x-changenow-api-key": self.api_key,
        }
        if self.secret and body:
            headers["x-changenow-signature"] = hmac.new(
                self.secret.encode(),
                body.encode(),
                hashlib.sha256,
            ).hexdigest()
        return headers

    async def create_order(self, payment: dict[str, Any]) -> dict[str, Any]:
        """Create a ChangeNOW fiat-to-crypto exchange.

        Args:
            payment: dict with:
                - amount (float): order amount in fiat
                - currency (str): "USD", "AED", "EUR", etc.
                - reference (str): your internal payment ID
                - customer_email (str): buyer's email
                - crypto_currency (str): desired crypto, e.g. "USDT"
                - wallet_address (str): destination wallet

        Returns:
            dict with order_id, url, status, raw
        """
        reference = payment["reference"]
        fiat_currency = (payment.get("currency") or payment.get("fiat_currency") or "USD").upper()
        crypto_currency = (payment.get("crypto_currency") or "USDT").upper()
        amount = str(payment["amount"])
        email = payment.get("customer_email", "")
        wallet_address = payment.get("wallet_address", "")

        body = {
            "from": fiat_currency.lower(),
            "to": crypto_currency.lower(),
            "amount": amount,
            "address": wallet_address,
            "extraId": payment.get("extra_id", ""),
            "userId": email or reference,
            "payload": {
                "ref": reference,
            },
            "flow": "standard",
            "type": "direct",
        }

        import json

        body_str = json.dumps(body, separators=(",", ":"))

        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                f"{self.api_base}/exchange",
                headers=self._headers(body_str),
                json=body,
            )
            resp.raise_for_status()
            data = resp.json()

        exchange_id = data.get("id") or data.get("payinId")
        redirect_url = data.get("redirectUrl") or data.get("payinAddress")

        result = {
            "order_id": exchange_id,
            "session_id": redirect_url,
            "url": redirect_url,
            "status": STATUS_MAP.get(str(data.get("status", "")).lower(), "pending"),
            "raw_status": data.get("status"),
            "raw": data,
        }

        if data.get("payinAddress"):
            result["payin_address"] = data.get("payinAddress")
        if data.get("payinExtraId"):
            result["payin_extra_id"] = data.get("payinExtraId")

        return result

    async def get_status(self, exchange_id: str) -> dict[str, Any]:
        """Fetch exchange status from ChangeNOW."""
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{self.api_base}/exchange/{exchange_id}",
                headers=self._headers(),
            )
            resp.raise_for_status()
            data = resp.json()

        raw_status = str(data.get("status") or "").lower()
        return {
            "provider_order_id": data.get("id") or exchange_id,
            "status": STATUS_MAP.get(raw_status, "pending"),
            "raw_status": raw_status,
            "raw": data,
        }

    def verify_webhook(self, raw_body: bytes, signature: str | None) -> bool:
        """Verify ChangeNOW webhook signature."""
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
        """Parse ChangeNOW webhook payload into normalized status."""
        exchange_id = payload.get("id") or payload.get("payinId")
        if not exchange_id:
            return None

        raw_status = str(payload.get("status") or "").lower()
        status = STATUS_MAP.get(raw_status, "pending")

        return {
            "payment_id": payload.get("ref") or payload.get("reference"),
            "provider_order_id": exchange_id,
            "status": status,
            "raw_status": raw_status,
        }

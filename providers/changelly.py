"""Changelly fiat-to-crypto gateway — instant exchange with fiat on-ramp.

Changelly offers crypto exchange and fiat-to-crypto on-ramp supporting
170+ countries, 500+ cryptocurrencies, and fiat rails via Visa/Mastercard,
Apple Pay, Google Pay, and bank transfers.

Dashboard: https://changelly.com
Fiat API Docs: https://docs.changelly.com
Base URL: https://api.changelly.com

Flow:
1. POST /api/v1/fiat/order to create a fiat buy order
2. Redirect user to the hosted checkout URL
3. Webhook or poll for status
"""

from __future__ import annotations

import hashlib
import hmac
from typing import Any

import httpx

from config import (
    BASE_URL,
    CHANGELLY_API_KEY,
    CHANGELLY_SECRET,
    CHANGELLY_ENV,
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
    "cancelled": "failed",
    "overdue": "failed",
}


class ChangellyProvider:
    """Changelly fiat-to-crypto on-ramp provider.

    Creates a fiat buy order via Changelly's fiat API and returns
    a redirect URL for the customer to complete the payment.
    """

    name = "changelly"

    def __init__(
        self,
        api_key: str | None = None,
        secret: str | None = None,
        env: str | None = None,
        api_base: str | None = None,
        public_base_url: str | None = None,
    ):
        self.api_key = (api_key if api_key is not None else CHANGELLY_API_KEY).strip()
        self.secret = (secret if secret is not None else CHANGELLY_SECRET).strip()
        self.env = (env if env is not None else CHANGELLY_ENV or "sandbox").strip().lower()
        self.api_base = (
            api_base if api_base is not None else "https://api.changelly.com"
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
            raise RuntimeError("CHANGELLY_API_KEY is not configured")
        headers = {
            "Content-Type": "application/json",
            "X-Api-Key": self.api_key,
        }
        if self.secret and body:
            headers["X-Api-Signature"] = hmac.new(
                self.secret.encode(),
                body.encode(),
                hashlib.sha256,
            ).hexdigest()
        return headers

    async def create_order(self, payment: dict[str, Any]) -> dict[str, Any]:
        """Create a Changelly fiat buy order.

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
            "amount_from": amount,
            "address": wallet_address,
            "customer_email": email,
            "success_url": payment.get(
                "success_url",
                f"{self.public_base_url}/pay/success/{reference}",
            ),
            "cancel_url": payment.get(
                "cancel_url",
                f"{self.public_base_url}/pay/{reference}",
            ),
            "callback_url": f"{self.public_base_url}/webhooks/changelly",
            "ref": reference,
        }

        import json

        body_str = json.dumps(body, separators=(",", ":"))

        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                f"{self.api_base}/api/v1/fiat/order",
                headers=self._headers(body_str),
                json=body,
            )
            resp.raise_for_status()
            data = resp.json()

        tx_id = data.get("id") or data.get("transaction_id") or data.get("order_id")
        redirect_url = data.get("redirect_url") or data.get("payment_url") or data.get("url")

        return {
            "order_id": tx_id,
            "session_id": redirect_url,
            "url": redirect_url,
            "status": STATUS_MAP.get(str(data.get("status", "")).lower(), "pending"),
            "raw_status": data.get("status"),
            "raw": data,
        }

    async def get_status(self, order_id: str) -> dict[str, Any]:
        """Fetch order status from Changelly."""
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{self.api_base}/api/v1/fiat/order/{order_id}",
                headers=self._headers(),
            )
            resp.raise_for_status()
            data = resp.json()

        raw_status = str(data.get("status") or "").lower()
        return {
            "provider_order_id": data.get("id") or data.get("order_id"),
            "status": STATUS_MAP.get(raw_status, "pending"),
            "raw_status": raw_status,
            "raw": data,
        }

    def verify_webhook(self, raw_body: bytes, signature: str | None) -> bool:
        """Verify Changelly webhook signature."""
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
        """Parse Changelly webhook payload into normalized status."""
        order_id = payload.get("id") or payload.get("order_id") or payload.get("transaction_id")
        if not order_id:
            return None

        raw_status = str(payload.get("status") or "").lower()
        status = STATUS_MAP.get(raw_status, "pending")

        return {
            "payment_id": payload.get("ref") or payload.get("reference"),
            "provider_order_id": order_id,
            "status": status,
            "raw_status": raw_status,
        }

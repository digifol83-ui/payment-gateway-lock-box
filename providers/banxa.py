"""Banxa fiat-to-crypto gateway — global on/off-ramp supporting AED & USD.

Banxa is a regulated fiat-to-crypto gateway operating in 180+ countries.
Supports card, bank transfer, Apple Pay, Google Pay.
Full KYC required; supports AED, USD, EUR, GBP, and more.

API Docs: https://docs.banxa.com
Dashboard: https://dashboard.banxa.com

Flow:
1. POST /api/orders to create a buy order
2. Redirect user to the checkout_url
3. Receive webhook or poll GET /api/orders/{order_id} for status
"""

from __future__ import annotations

import hashlib
import hmac
from typing import Any

import httpx

from config import (
    BASE_URL,
    BANXA_API_KEY,
    BANXA_SECRET,
    BANXA_SUBDOMAIN,
    BANXA_ENV,
)

API_BASE_MAP = {
    "sandbox": "https://api.sandbox.banxa.com",
    "production": "https://api.banxa.com",
}

STATUS_MAP = {
    "pendingPayment": "pending",
    "pending_payment": "pending",
    "paymentReceived": "pending",
    "inProgress": "pending",
    "in_progress": "pending",
    "pending": "pending",
    "processing": "pending",
    "completed": "completed",
    "complete": "completed",
    "succeeded": "completed",
    "success": "completed",
    "failed": "failed",
    "cancelled": "failed",
    "expired": "failed",
    "refunded": "failed",
}


class BanxaProvider:
    """Banxa fiat-to-crypto on/off-ramp provider.

    Creates an order via Banxa's Partner API and returns a hosted
    checkout URL for the customer to complete payment.
    """

    name = "banxa"

    def __init__(
        self,
        api_key: str | None = None,
        secret: str | None = None,
        subdomain: str | None = None,
        env: str | None = None,
        api_base: str | None = None,
        public_base_url: str | None = None,
    ):
        self.api_key = (api_key if api_key is not None else BANXA_API_KEY).strip()
        self.secret = (secret if secret is not None else BANXA_SECRET).strip()
        self.subdomain = (subdomain if subdomain is not None else BANXA_SUBDOMAIN).strip()
        self.env = (env if env is not None else BANXA_ENV or "sandbox").strip().lower()
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

    def _headers(self) -> dict[str, str]:
        if not self.api_key:
            raise RuntimeError("BANXA_API_KEY is not configured")
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

    def _sign_payload(self, payload: str) -> str:
        """Generate HMAC-SHA256 signature if secret is configured."""
        if not self.secret:
            return ""
        return hmac.new(
            self.secret.encode(),
            payload.encode(),
            hashlib.sha256,
        ).hexdigest()

    async def create_order(self, payment: dict[str, Any]) -> dict[str, Any]:
        """Create a Banxa buy order and return the checkout URL.

        Args:
            payment: dict with:
                - amount (float): order amount in fiat
                - currency (str): "AED", "USD", "EUR", etc.
                - reference (str): your internal payment ID
                - customer_email (str): buyer's email
                - crypto_currency (str): desired crypto, e.g. "USDT"
                - wallet_address (str): destination wallet for crypto

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
            "account_reference": self.subdomain or "",
            "source": fiat_currency,
            "source_amount": amount,
            "target": crypto_currency,
            "wallet_address": wallet_address,
            "return_url_on_success": payment.get(
                "success_url",
                f"{self.public_base_url}/pay/success/{reference}",
            ),
            "return_url_on_failure": payment.get(
                "cancel_url",
                f"{self.public_base_url}/pay/{reference}",
            ),
            "return_url_on_cancelled": payment.get(
                "cancel_url",
                f"{self.public_base_url}/pay/{reference}",
            ),
            "customer_email": email,
            "metadata": f"BeastPay-{reference}",
        }

        if payment.get("description"):
            body["metadata"] = payment["description"]

        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                f"{self.api_base}/api/orders",
                headers=self._headers(),
                json=body,
            )
            resp.raise_for_status()
            data = resp.json()

        order = data.get("data", data)
        order_id = order.get("id") or order.get("order_id")
        checkout_url = order.get("checkout_url") or order.get("redirect_url")

        return {
            "order_id": order_id,
            "session_id": checkout_url,
            "url": checkout_url,
            "status": "pending",
            "raw_status": order.get("status", "pendingPayment"),
            "raw": data,
        }

    async def get_status(self, order_id: str) -> dict[str, Any]:
        """Fetch order status from Banxa."""
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{self.api_base}/api/orders/{order_id}",
                headers=self._headers(),
            )
            resp.raise_for_status()
            data = resp.json()

        order = data.get("data", data)
        raw_status = str(order.get("status") or "").lower()
        status = STATUS_MAP.get(raw_status)
        if not status:
            if raw_status in ("paid", "success", "complete"):
                status = "completed"
            elif raw_status in ("fail", "error", "decline"):
                status = "failed"
            else:
                status = "pending"

        return {
            "provider_order_id": order.get("id") or order.get("order_id"),
            "status": status,
            "raw_status": raw_status,
            "raw": data,
        }

    def verify_webhook(self, raw_body: bytes, signature: str | None) -> bool:
        """Verify Banxa webhook signature using HMAC-SHA256."""
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
        """Parse Banxa webhook payload into normalized status."""
        order_id = payload.get("order_id") or payload.get("id")
        if not order_id:
            return None

        raw_status = str(payload.get("status") or "").lower()
        status = STATUS_MAP.get(raw_status)
        if not status:
            if raw_status in ("paid", "success", "complete", "completed"):
                status = "completed"
            elif raw_status in ("fail", "error", "decline", "cancelled"):
                status = "failed"
            else:
                status = "pending"

        return {
            "payment_id": payload.get("reference") or payload.get("metadata"),
            "provider_order_id": order_id,
            "status": status,
            "raw_status": raw_status,
        }

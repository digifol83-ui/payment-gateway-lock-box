"""Guardarian provider — fiat→crypto on-ramp.

Live API base: https://api-payments.guardarian.com/v1
Webhook signature: HMAC-SHA512 of the raw body with GUARDARIAN_WEBHOOK_SECRET,
sent in the X-Api-Signature header (Guardarian convention).
"""
from __future__ import annotations

import hashlib
import hmac
import logging
from typing import Any, Dict, Optional

import httpx

import config

logger = logging.getLogger(__name__)

_API_PROD = "https://api-payments.guardarian.com/v1"
_API_SBX = "https://api-payments.sandbox.guardarian.com/v1"


def _base_url() -> str:
    env = (getattr(config, "GUARDARIAN_ENV", "production") or "").strip().lower()
    return _API_PROD if env in {"prod", "production", "live"} else _API_SBX


def _headers() -> Dict[str, str]:
    api_key = (getattr(config, "GUARDARIAN_API_KEY", "") or "").strip()
    return {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "x-api-key": api_key,
    }


def _webhook_secret() -> str:
    return (getattr(config.settings, "GUARDARIAN_WEBHOOK_SECRET", "") or "").strip()


class GuardarianProvider:
    """Guardarian on-ramp adapter."""

    async def create_order(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Create a fiat→crypto transaction.

        Expected payload keys: amount, fiat, crypto, client_id, wallet_address.
        Returns: {"id": ..., "payment_url": ..., "raw": <full response>}.
        """
        api_key = (getattr(config, "GUARDARIAN_API_KEY", "") or "").strip()
        if not api_key or api_key.startswith(("YOUR_", "test_", "REPLACE")):
            raise RuntimeError("GUARDARIAN_API_KEY missing or placeholder")

        body = {
            "from_amount": payload["amount"],
            "from_currency": (payload["fiat"] or "USD").upper(),
            "to_currency": (payload["crypto"] or "USDT").upper(),
            "to_network": payload.get("network"),
            "payout_address": payload.get("wallet_address"),
            "external_partner_link_id": str(payload.get("client_id", "")),
        }
        body = {k: v for k, v in body.items() if v is not None}

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{_base_url()}/transaction", json=body, headers=_headers()
            )
        if resp.status_code >= 400:
            logger.error("Guardarian create_order failed: %s %s", resp.status_code, resp.text[:400])
            raise RuntimeError(f"Guardarian error {resp.status_code}: {resp.text[:200]}")

        data = resp.json()
        return {
            "id": data.get("id") or data.get("transaction_id"),
            "payment_url": data.get("redirect_url") or data.get("payment_url"),
            "raw": data,
        }

    async def get_status(self, order_id: str) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(
                f"{_base_url()}/transaction/{order_id}", headers=_headers()
            )
        if resp.status_code >= 400:
            raise RuntimeError(f"Guardarian status error {resp.status_code}: {resp.text[:200]}")
        return resp.json()

    @staticmethod
    def verify_webhook_signature(raw_body: bytes, signature_header: Optional[str]) -> bool:
        """HMAC-SHA512 of raw body == X-Api-Signature header (hex)."""
        secret = _webhook_secret()
        if not secret:
            logger.warning("GUARDARIAN_WEBHOOK_SECRET not configured — refusing webhook")
            return False
        if not signature_header:
            return False
        expected = hmac.new(
            secret.encode("utf-8"), raw_body, hashlib.sha512
        ).hexdigest()
        return hmac.compare_digest(expected, signature_header.strip().lower())

    async def handle_webhook(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Parsed webhook payload → normalized status dict."""
        txn = payload.get("transaction", payload) or {}
        status = (txn.get("status") or "").lower()
        status_map = {
            "completed": "completed",
            "finished": "completed",
            "exchanged": "completed",
            "failed": "failed",
            "cancelled": "failed",
            "expired": "failed",
            "waiting": "pending",
            "confirming": "pending",
            "exchanging": "pending",
        }
        return {
            "client_id": txn.get("external_partner_link_id") or txn.get("client_id"),
            "transaction_id": txn.get("id"),
            "status": status_map.get(status, "pending"),
            "raw_status": status,
        }

"""PayBis fiat-to-crypto on-ramp provider.

Web: API-based integration
- POST /v3/request to create a session → redirect user to widget URL
- GET /v2/transactions to check status
- Webhook at configured URL for async status updates

Docs: https://docs.payb.is/llms.txt
Sandbox: https://widget-api.sandbox.paybis.com
Production: https://widget-api.paybis.com
"""

from __future__ import annotations

import hashlib
import hmac
import base64
import json
from typing import Any
from urllib.parse import urlencode

import httpx

from config import (
    BASE_URL,
    PAYBIS_PARTNER_ID,
    PAYBIS_HMAC_KEY,
    PAYBIS_ENV,
    PAYBIS_WEBHOOK_SECRET,
)

# Sandbox vs production
API_BASE_MAP = {
    "sandbox": "https://widget-api.sandbox.paybis.com",
    "production": "https://widget-api.paybis.com",
}
WIDGET_BASE = "https://widget.paybis.com"

STATUS_MAP = {
    "pending": "pending",
    "processing": "pending",
    "completed": "completed",
    "success": "completed",
    "failed": "failed",
    "declined": "failed",
    "cancelled": "failed",
    "expired": "failed",
}


class PayBisProvider:
    """PayBis fiat-to-crypto on-ramp provider.

    Flow:
    1. POST /v3/request with partnerUserId, email, cryptoWalletAddress
    2. Receive requestId
    3. Redirect user to https://widget.paybis.com/?partnerId=...&requestId=...
    4. Receive webhook or poll GET /v2/transactions for status
    """

    name = "paybis"

    def __init__(
        self,
        partner_id: str | None = None,
        hmac_key: str | None = None,
        webhook_secret: str | None = None,
        env: str | None = None,
        api_base: str | None = None,
        public_base_url: str | None = None,
    ):
        self.partner_id = (partner_id if partner_id is not None else PAYBIS_PARTNER_ID).strip()
        self.hmac_key = (hmac_key if hmac_key is not None else PAYBIS_HMAC_KEY).strip()
        self.webhook_secret = (
            webhook_secret if webhook_secret is not None else PAYBIS_WEBHOOK_SECRET
        ).strip()
        self.env = (env if env is not None else PAYBIS_ENV or "sandbox").strip().lower()
        self.api_base = (
            api_base if api_base is not None else API_BASE_MAP.get(self.env, API_BASE_MAP["sandbox"])
        ).rstrip("/")
        self.public_base_url = (public_base_url or BASE_URL).rstrip("/")

    def is_configured(self) -> dict[str, Any]:
        enabled = bool(self.partner_id) and bool(self.hmac_key)
        return {
            "enabled": enabled,
            "mode": "live" if self.env == "production" else "sandbox",
            "provider": self.name,
        }

    def _sign_request(self, body: dict[str, Any]) -> str:
        """Generate HMAC-SHA256 signature for the request body.

        PayBis requires X-Request-Signature header on API calls.
        Signature = base64(HMAC-SHA256(base64_decode(hmac_key), compact_json_body))

        Compact JSON: no spaces, sorted keys.
        """
        compact = json.dumps(body, separators=(",", ":"), sort_keys=True)
        decoded_key = base64.b64decode(self.hmac_key)
        sig = hmac.new(decoded_key, compact.encode(), hashlib.sha256).digest()
        return base64.b64encode(sig).decode()

    def _headers(self) -> dict[str, str]:
        if not self.partner_id:
            raise RuntimeError("PAYBIS_PARTNER_ID is not configured")
        return {
            "Content-Type": "application/json",
            "X-Partner-Id": self.partner_id,
        }

    def _signed_headers(self, body: dict[str, Any]) -> dict[str, str]:
        headers = self._headers()
        if self.hmac_key:
            headers["X-Request-Signature"] = self._sign_request(body)
        return headers

    async def create_order(self, payment: dict[str, Any]) -> dict[str, Any]:
        """Create a PayBis on-ramp session and return the redirect URL.

        Args:
            payment: dict with:
                - amount (float/Decimal): fiat amount
                - currency (str): fiat currency, e.g. "AED" or "USD"
                - reference (str): your internal payment ID
                - customer_email (str): buyer's email
                - wallet_address (str): destination crypto wallet
                - crypto_currency (str): desired crypto, e.g. "USDT", "BTC"
                - description (str, optional): memo

        Returns:
            dict with order_id, url, session_id, status, raw
        """
        reference = payment["reference"]
        fiat_currency = (payment.get("currency") or payment.get("fiat_currency") or "AED").upper()
        crypto_currency = (payment.get("crypto_currency") or "USDT").upper()
        amount = str(payment["amount"])
        email = payment.get("customer_email", "")
        wallet = payment.get("wallet_address", "")

        # Step 1: optionally get quote to lock rate
        quote_id = None
        try:
            quote_body = {
                "currencyCodeFrom": fiat_currency,
                "currencyCodeTo": crypto_currency,
                "amount": amount,
                "directionChange": "from",
                "isReceivedAmount": False,
            }
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(
                    f"{self.api_base}/v2/quote",
                    headers=self._signed_headers(quote_body),
                    json=quote_body,
                )
                if resp.status_code == 200:
                    quote_data = resp.json()
                    quote_id = quote_data.get("quoteId")
        except Exception:
            quote_id = None  # quote is optional; proceed without it

        # Step 2: create request session
        request_body: dict[str, Any] = {
            "partnerUserId": reference,  # your payment ID as user identifier
            "partnerTransactionId": reference,
            "email": email,
            "userIp": payment.get("user_ip", "0.0.0.0"),
        }
        if quote_id:
            request_body["quoteId"] = quote_id
        if wallet:
            request_body["cryptoWalletAddress"] = {
                "address": wallet,
                "network": payment.get("network", ""),
            }

        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{self.api_base}/v3/request",
                headers=self._signed_headers(request_body),
                json=request_body,
            )
            resp.raise_for_status()
            data = resp.json()

        request_id = data.get("requestId") or data.get("id")

        # Build widget redirect URL
        params = {
            "partnerId": self.partner_id,
            "requestId": request_id,
            "transactionFlow": "buyCrypto",
        }
        redirect_url = f"{WIDGET_BASE}/?{urlencode(params)}"

        return {
            "order_id": request_id,
            "session_id": redirect_url,
            "url": redirect_url,
            "status": "pending",
            "raw_status": data.get("status", "pending"),
            "raw": data,
        }

    async def get_status(self, request_id: str) -> dict[str, Any]:
        """Fetch transaction status from PayBis."""
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get(
                f"{self.api_base}/v2/transactions",
                headers=self._headers(),
                params={"partnerTransactionId": request_id},
            )
            resp.raise_for_status()
            data = resp.json()

        transactions = data.get("data", [])
        if not transactions:
            return {"status": "pending", "raw_status": "unknown", "raw": data}

        tx = transactions[0]
        raw_status = str(tx.get("status") or "").lower()
        return {
            "provider_order_id": tx.get("id") or tx.get("requestId"),
            "status": STATUS_MAP.get(raw_status, "pending"),
            "raw_status": raw_status,
            "raw": tx,
        }

    def verify_webhook(self, raw_body: bytes, signature: str | None) -> bool:
        """Verify webhook signature if webhook_secret is configured."""
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
        """Parse PayBis webhook payload into normalized status."""
        event_id = payload.get("event_id")
        transaction_id = payload.get("transaction_id")
        if not event_id and not transaction_id:
            return None

        raw_status = str(payload.get("status") or "").lower()
        status = STATUS_MAP.get(raw_status)
        if not status:
            # Try to infer from structure
            if payload.get("digital_amount_sent"):
                status = "completed"
            elif payload.get("error") or payload.get("decline_reason"):
                status = "failed"
            else:
                status = "pending"

        return {
            "payment_id": payload.get("partnerTransactionId") or payload.get("reference"),
            "provider_order_id": transaction_id or event_id,
            "status": status,
            "raw_status": raw_status,
        }

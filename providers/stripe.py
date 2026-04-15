"""
Stripe payment provider integration.
Docs: https://stripe.com/docs/api/checkout/sessions
Flow: gateway creates a Checkout Session via Stripe API → customer pays on Stripe-hosted page
      → Stripe fires webhook (checkout.session.completed) → gateway updates payment status
"""
import hmac
import hashlib
import json
import time
import aiohttp
from config import STRIPE_SECRET_KEY, STRIPE_WEBHOOK_SECRET, STRIPE_ENV, BASE_URL


STRIPE_API_BASE = "https://api.stripe.com/v1"


class StripeProvider:
    name = "stripe"

    def build_widget_url(self, payment: dict) -> str:
        """
        Stripe requires an async API call to create a session.
        Call create_checkout_session() instead when using this provider.
        Returns a placeholder that will be replaced by the server endpoint.
        """
        return f"{BASE_URL}/api/stripe/checkout/{payment['id']}"

    async def create_checkout_session(self, payment: dict) -> str:
        """
        Create a Stripe Checkout Session and return the redirect URL.
        Called by initiate_payment() instead of build_widget_url().
        """
        if not STRIPE_SECRET_KEY or STRIPE_SECRET_KEY.startswith("sk_placeholder"):
            raise ValueError("STRIPE_SECRET_KEY not configured")

        # Build line items — Stripe amounts are in smallest currency unit (cents for USD)
        amount_cents = int(float(payment["amount"]) * 100)
        currency = payment.get("fiat_currency", "USD").lower()
        description = payment.get("description") or f"BeastPay · {payment.get('crypto_currency','Crypto')}"

        data = {
            "mode": "payment",
            "line_items[0][price_data][currency]": currency,
            "line_items[0][price_data][product_data][name]": description,
            "line_items[0][price_data][unit_amount]": str(amount_cents),
            "line_items[0][quantity]": "1",
            "client_reference_id": payment["id"],
            "success_url": f"{BASE_URL}/pay/success/{payment['id']}",
            "cancel_url": f"{BASE_URL}/pay/{payment.get('link_id', payment['id'])}",
        }
        if payment.get("customer_email"):
            data["customer_email"] = payment["customer_email"]

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{STRIPE_API_BASE}/checkout/sessions",
                data=data,
                auth=aiohttp.BasicAuth(STRIPE_SECRET_KEY, ""),
                headers={"Stripe-Version": "2023-10-16"},
            ) as resp:
                body = await resp.json()
                if resp.status != 200:
                    error = body.get("error", {}).get("message", str(body))
                    raise ValueError(f"Stripe API error: {error}")
                return body["url"]

    def verify_webhook(self, raw_body: bytes, signature_header: str) -> bool:
        """
        Verify Stripe webhook signature.
        Header format: t=<timestamp>,v1=<sig1>,v1=<sig2>,...
        Signed payload: <timestamp>.<raw_body>
        """
        if not STRIPE_WEBHOOK_SECRET or STRIPE_WEBHOOK_SECRET.startswith("whsec_placeholder"):
            return True  # skip in dev/test

        try:
            parts = {k: v for part in signature_header.split(",")
                     for k, v in [part.split("=", 1)]}
            timestamp = parts.get("t", "")
            v1_sigs = [v for k, v in (p.split("=", 1) for p in signature_header.split(","))
                       if k == "v1"]

            # Reject stale webhooks (5 min tolerance)
            if abs(time.time() - int(timestamp)) > 300:
                return False

            signed_payload = f"{timestamp}.".encode() + raw_body
            expected = hmac.new(
                STRIPE_WEBHOOK_SECRET.encode(),
                signed_payload,
                hashlib.sha256,
            ).hexdigest()
            return any(hmac.compare_digest(expected, sig) for sig in v1_sigs)
        except Exception:
            return False

    def parse_webhook(self, payload: dict) -> dict | None:
        """
        Normalize Stripe webhook into internal format.
        Handles: checkout.session.completed, payment_intent.payment_failed
        """
        event_type = payload.get("type", "")
        obj = payload.get("data", {}).get("object", {})

        status_map = {
            "checkout.session.completed":        "completed",
            "checkout.session.expired":          "failed",
            "payment_intent.succeeded":          "completed",
            "payment_intent.payment_failed":     "failed",
            "charge.refunded":                   "refunded",
        }

        status = status_map.get(event_type)
        if not status:
            return None

        # client_reference_id holds our internal payment_id
        payment_id = obj.get("client_reference_id") or obj.get("metadata", {}).get("payment_id")
        if not payment_id:
            return None

        return {
            "payment_id":        payment_id,
            "provider_order_id": obj.get("id"),
            "provider_tx_id":    obj.get("payment_intent"),
            "status":            status,
            "crypto_amount":     None,   # Stripe is fiat-only
            "exchange_rate":     None,
            "fee_amount":        None,
            "raw_status":        event_type,
        }

    def is_configured(self) -> dict:
        key = STRIPE_SECRET_KEY or ""
        mode = "live" if key.startswith("sk_live") else "test"
        return {
            "enabled":         bool(key and not key.startswith("sk_placeholder")),
            "env":             STRIPE_ENV,
            "mode":            mode,
            "publishable_key": "pk_" + key[3:8] + "…" if len(key) > 8 else "NOT SET",
            "secret_key":      key[:8] + "…" if key else "NOT SET",
            "webhook_secret":  "whsec_…" if STRIPE_WEBHOOK_SECRET and not STRIPE_WEBHOOK_SECRET.startswith("whsec_placeholder") else "NOT SET",
        }

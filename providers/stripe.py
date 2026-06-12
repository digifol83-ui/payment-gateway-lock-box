"""
Stripe payment provider — card checkout via Stripe Checkout Sessions.
Docs: https://docs.stripe.com/api/checkout/sessions
"""
import os
import stripe
from dotenv import load_dotenv

load_dotenv()

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
STRIPE_ENV = os.getenv("STRIPE_ENV", "test")
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")


class StripeProvider:
    name = "stripe"

    def __init__(self):
        self.secret_key = STRIPE_SECRET_KEY
        self.webhook_secret = STRIPE_WEBHOOK_SECRET
        if self.secret_key:
            stripe.api_key = self.secret_key

    def is_configured(self) -> dict:
        """Return enabled status and mode (test/live)."""
        if not self.secret_key:
            return {"enabled": False, "mode": "unconfigured"}
        mode = "live" if self.secret_key.startswith("sk_live_") else "test"
        return {"enabled": True, "mode": mode}

    # ── Webhook ──────────────────────────────────────────────────────────

    def verify_webhook(self, raw_body: bytes, signature: str) -> bool:
        """Verify Stripe webhook signature using the webhook secret."""
        if not self.webhook_secret:
            # Allow in dev without verification
            return STRIPE_ENV != "live"
        try:
            stripe.Webhook.construct_event(
                raw_body, signature, self.webhook_secret
            )
            return True
        except (stripe.error.SignatureVerificationError, ValueError):
            return False

    def parse_webhook(self, payload: dict) -> dict | None:
        """
        Normalize Stripe webhook event into internal format.
        Returns dict with: payment_id, status, provider_order_id, provider_tx_id, etc.
        """
        event_type = payload.get("type", "")
        obj = payload.get("data", {}).get("object", {})

        # Supported events
        if event_type not in (
            "checkout.session.completed",
            "checkout.session.expired",
            "checkout.session.async_payment_succeeded",
            "checkout.session.async_payment_failed",
            "payment_intent.succeeded",
            "payment_intent.payment_failed",
        ):
            return None

        payment_id = obj.get("client_reference_id") or obj.get("metadata", {}).get("payment_id")
        if not payment_id:
            return None

        status_map = {
            "checkout.session.completed": "completed",
            "checkout.session.expired": "expired",
            "checkout.session.async_payment_succeeded": "completed",
            "checkout.session.async_payment_failed": "failed",
            "payment_intent.succeeded": "completed",
            "payment_intent.payment_failed": "failed",
        }

        return {
            "payment_id": payment_id,
            "status": status_map.get(event_type, "unknown"),
            "provider_order_id": obj.get("id"),
            "provider_tx_id": obj.get("payment_intent"),
            "exchange_rate": None,
            "crypto_amount": None,
        }

    # ── Checkout Session ─────────────────────────────────────────────────

    async def create_checkout_session(self, payment: dict) -> str:
        """
        Create a Stripe Checkout Session and return the redirect URL.
        Payment dict keys: id, amount, fiat_currency, crypto_currency, customer_email, description
        """
        if not self.secret_key:
            raise ValueError("STRIPE_SECRET_KEY not configured")

        # Stripe expects amount in cents/smallest unit
        amount = int(float(payment.get("amount", 0)) * 100)
        currency = (payment.get("fiat_currency") or "aed").lower()

        session_params = {
            "mode": "payment",
            "success_url": f"{BASE_URL}/pay/success/{payment['id']}?session_id={{CHECKOUT_SESSION_ID}}",
            "cancel_url": f"{BASE_URL}/checkout/{payment['id']}",
            "client_reference_id": payment.get("id"),
            "metadata": {
                "payment_id": payment.get("id", ""),
                "crypto_currency": payment.get("crypto_currency", ""),
            },
            "line_items": [
                {
                    "price_data": {
                        "currency": currency,
                        "product_data": {
                            "name": payment.get("description", "BeastPay Checkout"),
                        },
                        "unit_amount": amount,
                    },
                    "quantity": 1,
                }
            ],
        }

        if payment.get("customer_email"):
            session_params["customer_email"] = payment["customer_email"]

        try:
            session = stripe.checkout.Session.create(**session_params)
            return session.url
        except stripe.error.StripeError as e:
            raise ValueError(f"Stripe session error: {e.user_message or str(e)}")

    # ── Auto-Pay: Save Card (SetupIntent) ─────────────────────────────────

    async def create_customer_and_setup_intent(
        self,
        customer_email: str = "",
        customer_name: str = "",
        metadata: dict | None = None,
    ) -> dict:
        """
        Create a Stripe Customer + SetupIntent for saving a card on file.
        Returns client_secret for Stripe Elements, customer_id, and setup_intent_id.
        The customer enters card details ONCE via Stripe Elements (hosted by you).
        After confirmation, the card is tokenized and stored by Stripe — NOT by us.
        """
        if not self.secret_key:
            raise ValueError("STRIPE_SECRET_KEY not configured")

        try:
            # Create or retrieve customer by email
            customer = None
            if customer_email:
                existing = stripe.Customer.list(email=customer_email, limit=1)
                if existing.data:
                    customer = existing.data[0]

            if not customer:
                customer = stripe.Customer.create(
                    email=customer_email or None,
                    name=customer_name or None,
                    metadata=metadata or {},
                )

            setup_intent = stripe.SetupIntent.create(
                customer=customer.id,
                payment_method_types=["card"],
                usage="off_session",
                metadata=metadata or {},
            )

            return {
                "customer_id": customer.id,
                "setup_intent_id": setup_intent.id,
                "client_secret": setup_intent.client_secret,
                "status": "requires_payment_method",
            }
        except stripe.error.StripeError as e:
            raise ValueError(f"Stripe setup error: {e.user_message or str(e)}")

    async def confirm_setup_status(self, setup_intent_id: str) -> dict:
        """Check if a SetupIntent has been confirmed (card saved)."""
        try:
            si = stripe.SetupIntent.retrieve(setup_intent_id)
            return {
                "setup_intent_id": si.id,
                "status": si.status,
                "payment_method_id": si.payment_method,
                "customer_id": si.customer,
                "confirmed": si.status == "succeeded",
            }
        except stripe.error.StripeError as e:
            raise ValueError(f"Stripe status error: {e.user_message or str(e)}")

    # ── Auto-Pay: Charge Saved Card (Off-Session) ─────────────────────────

    async def charge_saved_card(
        self,
        customer_id: str,
        amount: float,
        currency: str = "aed",
        description: str = "BeastPay Auto-Charge",
        metadata: dict | None = None,
        payment_method_id: str | None = None,
    ) -> dict:
        """
        Charge a saved card WITHOUT any redirect (off-session PaymentIntent).
        This is the auto-pay / usage-based charging endpoint.
        No customer interaction required — silent server-side charge.
        """
        if not self.secret_key:
            raise ValueError("STRIPE_SECRET_KEY not configured")

        amount_cents = int(float(amount) * 100)
        currency_lower = currency.lower()

        try:
            # Get customer's default payment method if not specified
            pm_id = payment_method_id
            if not pm_id:
                pms = stripe.PaymentMethod.list(
                    customer=customer_id, type="card", limit=1
                )
                if not pms.data:
                    raise ValueError(f"No saved card found for customer {customer_id}")
                pm_id = pms.data[0].id

            intent = stripe.PaymentIntent.create(
                amount=amount_cents,
                currency=currency_lower,
                customer=customer_id,
                payment_method=pm_id,
                off_session=True,
                confirm=True,
                description=description,
                metadata=metadata or {},
            )

            return {
                "payment_intent_id": intent.id,
                "status": intent.status,
                "amount": amount,
                "currency": currency_lower,
                "customer_id": customer_id,
                "payment_method_id": pm_id,
                "charged": intent.status == "succeeded",
                "requires_action": intent.status == "requires_action",
                "client_secret": intent.client_secret if intent.status == "requires_action" else None,
            }
        except stripe.error.CardError as e:
            return {
                "payment_intent_id": getattr(e, "payment_intent", {}).get("id", "") if isinstance(getattr(e, "payment_intent", None), dict) else "",
                "status": "failed",
                "error": e.user_message or str(e),
                "decline_code": getattr(e, "code", ""),
                "charged": False,
            }
        except stripe.error.StripeError as e:
            raise ValueError(f"Stripe charge error: {e.user_message or str(e)}")

    async def list_saved_cards(self, customer_id: str) -> list[dict]:
        """List all saved cards for a customer."""
        try:
            pms = stripe.PaymentMethod.list(customer=customer_id, type="card", limit=10)
            return [
                {
                    "id": pm.id,
                    "brand": pm.card.brand,
                    "last4": pm.card.last4,
                    "exp_month": pm.card.exp_month,
                    "exp_year": pm.card.exp_year,
                    "is_default": idx == 0,
                }
                for idx, pm in enumerate(pms.data)
            ]
        except stripe.error.StripeError as e:
            raise ValueError(f"Stripe list error: {e.user_message or str(e)}")

    async def remove_saved_card(self, customer_id: str, payment_method_id: str) -> dict:
        """Detach (remove) a saved card."""
        try:
            pm = stripe.PaymentMethod.detach(payment_method_id)
            return {"removed": True, "payment_method_id": pm.id}
        except stripe.error.StripeError as e:
            raise ValueError(f"Stripe detach error: {e.user_message or str(e)}")

"""
Webhook Handlers: Per-provider webhook processing with signature verification.

Each fiat-to-crypto provider sends transaction updates via webhooks.
This module routes webhooks to the correct handler and verifies signatures.
"""

import hmac
import hashlib
import json
import logging
from typing import Dict, Optional, Tuple
from datetime import datetime

from config import settings

logger = logging.getLogger(__name__)


class WebhookVerifier:
    """Signature verification for provider webhooks."""

    @staticmethod
    def verify_bleap_signature(payload: bytes, signature: str) -> bool:
        """Verify Bleap webhook signature."""
        secret = settings.BLEAP_SECRET
        if not secret:
            logger.warning("BLEAP_SECRET not configured")
            return False

        expected = hmac.new(
            secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(expected, signature)

    @staticmethod
    def verify_kast_signature(payload: bytes, signature: str) -> bool:
        """Verify KAST webhook signature (X-Signature header)."""
        secret = settings.KAST_SECRET
        if not secret:
            logger.warning("KAST_SECRET not configured")
            return False

        # KAST uses HMAC-SHA256 with format: "timestamp.signature"
        try:
            timestamp, sig = signature.split(".")
            expected = hmac.new(
                f"{settings.KAST_API_KEY}{timestamp}".encode(),
                payload,
                hashlib.sha256
            ).hexdigest()
            return hmac.compare_digest(expected, sig)
        except (ValueError, AttributeError):
            return False

    @staticmethod
    def verify_swapin_signature(payload: bytes, signature: str) -> bool:
        """Verify Swapin webhook signature."""
        secret = settings.SWAPIN_SECRET
        if not secret:
            logger.warning("SWAPIN_SECRET not configured")
            return False

        expected = hmac.new(
            secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(expected, signature)

    @staticmethod
    def verify_guardarian_signature(payload: bytes, signature: str) -> bool:
        """Verify Guardarian webhook signature."""
        secret = settings.GUARDARIAN_API_KEY
        if not secret:
            logger.warning("GUARDARIAN_API_KEY not configured")
            return False

        expected = hmac.new(
            secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(expected, signature)


class WebhookProcessor:
    """Process normalized webhook data."""

    @staticmethod
    async def process_payment_update(
        provider_id: str,
        webhook_data: Dict,
        db: any = None,
    ) -> bool:
        """
        Process payment status update from provider.

        Returns True if successfully processed.
        """
        logger.info(
            f"Processing {provider_id} webhook: "
            f"external_id={webhook_data.get('external_id')}, "
            f"status={webhook_data.get('status')}"
        )

        try:
            # Find payment by provider reference
            payment = await db.find_payment_by_provider_ref(
                provider_id=provider_id,
                provider_ref=webhook_data.get("external_id"),
            )

            if not payment:
                logger.warning(
                    f"Payment not found: {provider_id} "
                    f"ref={webhook_data.get('external_id')}"
                )
                return False

            # Update payment status
            old_status = payment.status
            payment.status = webhook_data.get("status")
            payment.provider_data = webhook_data
            payment.updated_at = datetime.utcnow()

            await db.update_payment(payment)

            logger.info(
                f"Updated payment {payment.id}: "
                f"{old_status} → {payment.status}"
            )

            # Notify webhook on merchant side if configured
            if payment.merchant.webhook_url:
                await notify_merchant_webhook(
                    webhook_url=payment.merchant.webhook_url,
                    payment_id=payment.id,
                    status=payment.status,
                    provider=provider_id,
                )

            return True

        except Exception as e:
            logger.error(f"Error processing webhook: {e}")
            return False


class BleapWebhookHandler:
    """Handle Bleap transaction webhooks."""

    WEBHOOK_SECRET_HEADER = "X-Bleap-Signature"

    @staticmethod
    async def handle(request_body: bytes, signature: str) -> Tuple[bool, Dict]:
        """
        Handle Bleap webhook.

        Returns (success, normalized_data)
        """
        # Verify signature
        if not WebhookVerifier.verify_bleap_signature(request_body, signature):
            logger.warning("Bleap webhook signature verification failed")
            return False, {}

        try:
            data = json.loads(request_body)

            # Normalize to common format
            normalized = {
                "provider": "bleap",
                "external_id": data.get("transaction_id"),
                "status": BleapWebhookHandler._map_status(data.get("status")),
                "amount_crypto": data.get("amount"),
                "amount_fiat": data.get("fiat_amount"),
                "fiat_currency": data.get("fiat_currency"),
                "crypto_currency": data.get("crypto"),
                "crypto_address": data.get("wallet_address"),
                "tx_hash": data.get("blockchain_tx_id"),
                "timestamp": data.get("completed_at"),
                "raw_data": data,
            }

            logger.info(f"Bleap webhook processed: {normalized['external_id']}")
            return True, normalized

        except Exception as e:
            logger.error(f"Bleap webhook parsing error: {e}")
            return False, {}

    @staticmethod
    def _map_status(bleap_status: str) -> str:
        """Map Bleap status to standard status."""
        mapping = {
            "pending": "pending",
            "processing": "processing",
            "completed": "completed",
            "failed": "failed",
            "cancelled": "cancelled",
        }
        return mapping.get(bleap_status, "unknown")


class KastWebhookHandler:
    """Handle KAST transaction webhooks."""

    WEBHOOK_SECRET_HEADER = "X-Kast-Signature"

    @staticmethod
    async def handle(request_body: bytes, signature: str) -> Tuple[bool, Dict]:
        """
        Handle KAST webhook.

        Returns (success, normalized_data)
        """
        # Verify signature
        if not WebhookVerifier.verify_kast_signature(request_body, signature):
            logger.warning("KAST webhook signature verification failed")
            return False, {}

        try:
            data = json.loads(request_body)

            # Normalize to common format
            normalized = {
                "provider": "kast",
                "external_id": data.get("order_id"),
                "status": KastWebhookHandler._map_status(data.get("status")),
                "amount_crypto": data.get("crypto_amount"),
                "amount_fiat": data.get("fiat_amount"),
                "fiat_currency": data.get("fiat_currency"),
                "crypto_currency": data.get("crypto_currency"),
                "crypto_address": data.get("wallet_address"),
                "tx_hash": data.get("transaction_hash"),
                "timestamp": data.get("completed_at"),
                "raw_data": data,
            }

            logger.info(f"KAST webhook processed: {normalized['external_id']}")
            return True, normalized

        except Exception as e:
            logger.error(f"KAST webhook parsing error: {e}")
            return False, {}

    @staticmethod
    def _map_status(kast_status: str) -> str:
        """Map KAST status to standard status."""
        mapping = {
            "awaiting_payment": "pending",
            "payment_received": "processing",
            "completed": "completed",
            "failed": "failed",
            "expired": "failed",
        }
        return mapping.get(kast_status, "unknown")


class SwapinWebhookHandler:
    """Handle Swapin transaction webhooks."""

    WEBHOOK_SECRET_HEADER = "X-Swapin-Signature"

    @staticmethod
    async def handle(request_body: bytes, signature: str) -> Tuple[bool, Dict]:
        """
        Handle Swapin webhook.

        Returns (success, normalized_data)
        """
        # Verify signature
        if not WebhookVerifier.verify_swapin_signature(request_body, signature):
            logger.warning("Swapin webhook signature verification failed")
            return False, {}

        try:
            data = json.loads(request_body)

            # Normalize to common format
            normalized = {
                "provider": "swapin",
                "external_id": data.get("uuid"),
                "status": SwapinWebhookHandler._map_status(data.get("status")),
                "amount_crypto": data.get("amount_out"),
                "amount_fiat": data.get("amount_in"),
                "fiat_currency": data.get("currency_in"),
                "crypto_currency": data.get("currency_out"),
                "crypto_address": data.get("address_out"),
                "tx_hash": data.get("hash_out"),
                "timestamp": data.get("created_at"),
                "raw_data": data,
            }

            logger.info(f"Swapin webhook processed: {normalized['external_id']}")
            return True, normalized

        except Exception as e:
            logger.error(f"Swapin webhook parsing error: {e}")
            return False, {}

    @staticmethod
    def _map_status(swapin_status: str) -> str:
        """Map Swapin status to standard status."""
        mapping = {
            "waiting_for_payment": "pending",
            "payment_received": "processing",
            "exchanging": "processing",
            "sending": "processing",
            "success": "completed",
            "failed": "failed",
            "expired": "failed",
        }
        return mapping.get(swapin_status, "unknown")


class GuardarianWebhookHandler:
    """Handle Guardarian transaction webhooks."""

    WEBHOOK_SECRET_HEADER = "X-Guardarian-Signature"

    @staticmethod
    async def handle(request_body: bytes, signature: str) -> Tuple[bool, Dict]:
        """
        Handle Guardarian webhook.

        Returns (success, normalized_data)
        """
        # Verify signature
        if not WebhookVerifier.verify_guardarian_signature(request_body, signature):
            logger.warning("Guardarian webhook signature verification failed")
            return False, {}

        try:
            data = json.loads(request_body)

            # Normalize to common format
            normalized = {
                "provider": "guardarian",
                "external_id": data.get("transaction_id"),
                "status": GuardarianWebhookHandler._map_status(data.get("status")),
                "amount_crypto": data.get("out_amount"),
                "amount_fiat": data.get("in_amount"),
                "fiat_currency": data.get("in_currency"),
                "crypto_currency": data.get("out_currency"),
                "crypto_address": data.get("out_address"),
                "tx_hash": data.get("blockchain_tx_id"),
                "timestamp": data.get("created_at"),
                "raw_data": data,
            }

            logger.info(f"Guardarian webhook processed: {normalized['external_id']}")
            return True, normalized

        except Exception as e:
            logger.error(f"Guardarian webhook parsing error: {e}")
            return False, {}

    @staticmethod
    def _map_status(gdn_status: str) -> str:
        """Map Guardarian status to standard status."""
        mapping = {
            "initial": "pending",
            "paying": "pending",
            "exchange": "processing",
            "sending": "processing",
            "completed": "completed",
            "failed": "failed",
            "cancelled": "cancelled",
        }
        return mapping.get(gdn_status, "unknown")


# Router: Map provider → handler
WEBHOOK_HANDLERS = {
    "bleap": BleapWebhookHandler,
    "kast": KastWebhookHandler,
    "swapin": SwapinWebhookHandler,
    "guardarian": GuardarianWebhookHandler,
}


async def handle_provider_webhook(
    provider_id: str,
    request_body: bytes,
    signature: str,
    db: any = None,
) -> bool:
    """
    Route webhook to appropriate handler.

    Returns True if successfully processed.
    """
    handler_class = WEBHOOK_HANDLERS.get(provider_id.lower())

    if not handler_class:
        logger.warning(f"No webhook handler for provider: {provider_id}")
        return False

    success, normalized = await handler_class.handle(request_body, signature)

    if not success:
        logger.error(f"Webhook verification failed for {provider_id}")
        return False

    # Process normalized webhook data
    if db:
        return await WebhookProcessor.process_payment_update(
            provider_id=provider_id,
            webhook_data=normalized,
            db=db,
        )

    return True


async def notify_merchant_webhook(
    webhook_url: str,
    payment_id: str,
    status: str,
    provider: str,
) -> bool:
    """Send payment status update to merchant webhook."""
    try:
        import httpx

        payload = {
            "payment_id": payment_id,
            "status": status,
            "provider": provider,
            "timestamp": datetime.utcnow().isoformat(),
        }

        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.post(
                webhook_url,
                json=payload,
                headers={"Content-Type": "application/json"},
            )

            if response.status_code == 200:
                logger.info(f"Merchant webhook sent: {webhook_url}")
                return True
            else:
                logger.warning(
                    f"Merchant webhook failed: {webhook_url} "
                    f"(status: {response.status_code})"
                )
                return False

    except Exception as e:
        logger.error(f"Error sending merchant webhook: {e}")
        return False

"""CodeWords Workflow Automation Integration.

Triggers CodeWords workflows when Stripe payment events occur.
Enables automated responses: notifications, crypto transfers, reconciliation, etc.
"""

import httpx
import json
import hmac
import hashlib
from typing import Optional, Dict, Any
from datetime import datetime
import os

class CodeWordsIntegration:
    """Integrate Stripe payment events with CodeWords workflows."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_url: str = "https://api.codewords.agemo.ai"
    ):
        """Initialize CodeWords integration.

        Args:
            api_key: CodeWords API key (from env or param)
            api_url: CodeWords API base URL
        """
        # Try to get API key from parameter, environment, or .env file
        if api_key:
            self.api_key = api_key
        else:
            # Check environment variable first
            self.api_key = os.getenv("CODEWORDS_API_KEY")

            # If not found, try reading from .env file directly
            if not self.api_key:
                try:
                    with open(".env", "r") as f:
                        for line in f:
                            if line.startswith("CODEWORDS_API_KEY="):
                                self.api_key = line.split("=", 1)[1].strip()
                                break
                except FileNotFoundError:
                    pass

        self.api_url = api_url
        self.client = httpx.AsyncClient(timeout=30)

    async def trigger_workflow(
        self,
        workflow_id: str,
        trigger_data: Dict[str, Any],
        webhook_secret: Optional[str] = None
    ) -> Dict[str, Any]:
        """Trigger a CodeWords workflow with payment data.

        Args:
            workflow_id: CodeWords workflow ID
            trigger_data: Payment event data to pass to workflow
            webhook_secret: Optional webhook secret for signature

        Returns:
            {"status": "triggered", "execution_id": "...", "workflow_id": "..."}
        """

        if not self.api_key:
            raise ValueError("CODEWORDS_API_KEY not configured")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "workflow_id": workflow_id,
            "trigger_data": trigger_data,
            "timestamp": datetime.utcnow().isoformat(),
        }

        # Add signature if webhook secret provided
        if webhook_secret:
            signature = self._sign_payload(json.dumps(payload), webhook_secret)
            headers["X-Signature"] = signature

        try:
            response = await self.client.post(
                f"{self.api_url}/v1/workflows/trigger",
                json=payload,
                headers=headers
            )

            if response.status_code == 200:
                return {
                    "status": "triggered",
                    "execution_id": response.json().get("execution_id"),
                    "workflow_id": workflow_id,
                    "timestamp": datetime.utcnow().isoformat()
                }
            else:
                return {
                    "status": "error",
                    "error": response.json().get("error", str(response.text)),
                    "code": response.status_code
                }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }

    async def on_payment_completed(
        self,
        payment_id: str,
        merchant_id: str,
        amount: float,
        fiat_currency: str,
        crypto_currency: str,
        wallet_address: str,
        customer_email: str,
        workflow_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Trigger workflow when payment is completed.

        Default workflow: payment_completed_{merchant_id}
        """

        workflow_id = workflow_id or f"payment_completed_{merchant_id}"

        trigger_data = {
            "event": "payment.completed",
            "payment_id": payment_id,
            "merchant_id": merchant_id,
            "amount": amount,
            "fiat_currency": fiat_currency,
            "crypto_currency": crypto_currency,
            "wallet_address": wallet_address,
            "customer_email": customer_email,
            "timestamp": datetime.utcnow().isoformat(),
        }

        return await self.trigger_workflow(workflow_id, trigger_data)

    async def on_payment_failed(
        self,
        payment_id: str,
        merchant_id: str,
        error_reason: str,
        customer_email: str,
        workflow_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Trigger workflow when payment fails."""

        workflow_id = workflow_id or f"payment_failed_{merchant_id}"

        trigger_data = {
            "event": "payment.failed",
            "payment_id": payment_id,
            "merchant_id": merchant_id,
            "error_reason": error_reason,
            "customer_email": customer_email,
            "timestamp": datetime.utcnow().isoformat(),
        }

        return await self.trigger_workflow(workflow_id, trigger_data)

    async def on_payment_refunded(
        self,
        payment_id: str,
        merchant_id: str,
        amount: float,
        wallet_address: str,
        workflow_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Trigger workflow when payment is refunded."""

        workflow_id = workflow_id or f"payment_refunded_{merchant_id}"

        trigger_data = {
            "event": "payment.refunded",
            "payment_id": payment_id,
            "merchant_id": merchant_id,
            "amount": amount,
            "wallet_address": wallet_address,
            "timestamp": datetime.utcnow().isoformat(),
        }

        return await self.trigger_workflow(workflow_id, trigger_data)

    async def get_workflow_status(self, execution_id: str) -> Dict[str, Any]:
        """Get status of a triggered workflow execution."""

        if not self.api_key:
            raise ValueError("CODEWORDS_API_KEY not configured")

        headers = {
            "Authorization": f"Bearer {self.api_key}",
        }

        try:
            response = await self.client.get(
                f"{self.api_url}/v1/executions/{execution_id}",
                headers=headers
            )

            if response.status_code == 200:
                return response.json()
            else:
                return {
                    "status": "error",
                    "error": response.json().get("error", str(response.text)),
                    "code": response.status_code
                }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }

    def _sign_payload(self, payload: str, secret: str) -> str:
        """Sign payload with HMAC-SHA256."""
        return hmac.new(
            secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()

    @staticmethod
    def create_workflow_templates() -> Dict[str, Dict]:
        """Return CodeWords workflow template definitions.

        These can be imported into CodeWords to set up automation:
        1. payment_completed - Send confirmation, transfer crypto
        2. payment_failed - Notify customer, log error
        3. payment_refunded - Reverse transaction, notify
        """

        return {
            "payment_completed_{merchant}": {
                "name": "Payment Completed - Transfer Crypto",
                "description": "Triggered when customer successfully pays via Stripe",
                "trigger": "webhook",
                "steps": [
                    {
                        "id": "step_1",
                        "type": "action",
                        "action": "send_email",
                        "params": {
                            "to": "{{ trigger_data.customer_email }}",
                            "subject": "Payment Received - Crypto Sent to Wallet",
                            "template": "payment_confirmed"
                        }
                    },
                    {
                        "id": "step_2",
                        "type": "action",
                        "action": "transfer_crypto",
                        "params": {
                            "wallet_address": "{{ trigger_data.wallet_address }}",
                            "amount": "{{ trigger_data.amount }}",
                            "crypto_currency": "{{ trigger_data.crypto_currency }}"
                        }
                    },
                    {
                        "id": "step_3",
                        "type": "action",
                        "action": "webhook",
                        "params": {
                            "url": "{{ merchant.webhook_url }}",
                            "data": {
                                "event": "payment.completed",
                                "payment_id": "{{ trigger_data.payment_id }}",
                                "status": "success"
                            }
                        }
                    },
                    {
                        "id": "step_4",
                        "type": "action",
                        "action": "send_notification",
                        "params": {
                            "channels": ["telegram", "whatsapp"],
                            "message": "Payment {{ trigger_data.payment_id }} completed. {{ trigger_data.amount }} {{ trigger_data.crypto_currency }} sent to wallet."
                        }
                    }
                ]
            },

            "payment_failed_{merchant}": {
                "name": "Payment Failed - Customer Notification",
                "description": "Triggered when payment fails at Stripe",
                "trigger": "webhook",
                "steps": [
                    {
                        "id": "step_1",
                        "type": "action",
                        "action": "send_email",
                        "params": {
                            "to": "{{ trigger_data.customer_email }}",
                            "subject": "Payment Failed - Please Try Again",
                            "template": "payment_failed"
                        }
                    },
                    {
                        "id": "step_2",
                        "type": "action",
                        "action": "log_event",
                        "params": {
                            "event_type": "payment_failure",
                            "payment_id": "{{ trigger_data.payment_id }}",
                            "reason": "{{ trigger_data.error_reason }}"
                        }
                    },
                    {
                        "id": "step_3",
                        "type": "action",
                        "action": "webhook",
                        "params": {
                            "url": "{{ merchant.webhook_url }}",
                            "data": {
                                "event": "payment.failed",
                                "payment_id": "{{ trigger_data.payment_id }}",
                                "reason": "{{ trigger_data.error_reason }}"
                            }
                        }
                    }
                ]
            },

            "payment_refunded_{merchant}": {
                "name": "Payment Refunded - Reverse Transaction",
                "description": "Triggered when payment is refunded",
                "trigger": "webhook",
                "steps": [
                    {
                        "id": "step_1",
                        "type": "action",
                        "action": "reverse_crypto_transfer",
                        "params": {
                            "wallet_address": "{{ trigger_data.wallet_address }}",
                            "amount": "{{ trigger_data.amount }}"
                        }
                    },
                    {
                        "id": "step_2",
                        "type": "action",
                        "action": "send_email",
                        "params": {
                            "to": "{{ trigger_data.customer_email }}",
                            "subject": "Refund Processed",
                            "template": "refund_confirmed"
                        }
                    },
                    {
                        "id": "step_3",
                        "type": "action",
                        "action": "log_event",
                        "params": {
                            "event_type": "refund",
                            "payment_id": "{{ trigger_data.payment_id }}",
                            "amount": "{{ trigger_data.amount }}"
                        }
                    }
                ]
            }
        }

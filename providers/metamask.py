"""
MetaMask Fiat-to-Crypto Provider
Integrates with MetaMask's native buy/ramp system and widget.

MetaMask supports fiat-to-crypto through:
- MetaMask Swaps (crypto-to-crypto, also supports fiat entry)
- MetaMask Buy Widget (native ramp providers)
- Direct API for partner integrations
"""

import json
import httpx
import hmac
import hashlib
from datetime import datetime
from typing import Optional, Dict, Any


class MetaMaskProvider:
    """
    Integrates with MetaMask's fiat-to-crypto infrastructure.

    Supports:
    - Direct MetaMask Widget embed (client-side)
    - MetaMask SDK integration (server-side)
    - Fiat entry with automatic conversion
    """

    def __init__(
        self,
        api_key: str,
        secret_key: Optional[str] = None,
        webhook_secret: Optional[str] = None,
        environment: str = "production",
    ):
        self.api_key = api_key
        self.secret_key = secret_key or ""
        self.webhook_secret = webhook_secret or ""
        self.environment = environment

        # MetaMask API endpoints
        self.base_url = "https://api.metamask.io" if environment == "production" else "https://staging-api.metamask.io"
        self.widget_url = "https://buy.metamask.io"

        self.client = httpx.AsyncClient(timeout=30)
        self.name = "metamask"

    async def create_order(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a fiat-to-crypto order via MetaMask.

        Args:
            payload: {
                "amount_fiat": 100,
                "fiat_currency": "USD",
                "crypto_currency": "ETH",
                "wallet_address": "0x...",
                "customer_email": "user@example.com",
                "customer_id": "cust_123",
            }

        Returns:
            {
                "order_id": "mm_order_xyz",
                "widget_url": "https://buy.metamask.io?order_id=...",
                "status": "pending",
                "expires_at": "2026-05-04T12:00:00Z",
                "checkout_url": "https://checkout.metamask.io/...",
            }
        """
        try:
            # Validate required fields
            amount = float(payload.get("amount_fiat", 0))
            fiat = payload.get("fiat_currency", "USD").upper()
            crypto = payload.get("crypto_currency", "ETH").upper()
            wallet = payload.get("wallet_address", "")
            email = payload.get("customer_email", "")

            if amount <= 0:
                return {"error": "Invalid amount"}
            if not wallet or not wallet.startswith("0x"):
                return {"error": "Invalid wallet address"}

            # Create order via MetaMask API
            order_payload = {
                "fiat_amount": amount,
                "fiat_currency": fiat,
                "crypto_currency": crypto,
                "destination_wallet": wallet,
                "customer_email": email,
                "partner_id": self.api_key,
                "redirect_url": payload.get("redirect_url", "https://localhost:8000/checkout/success"),
                "external_order_id": payload.get("payment_id", ""),
            }

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }

            response = await self.client.post(
                f"{self.base_url}/v1/orders",
                json=order_payload,
                headers=headers,
            )

            if response.status_code not in [200, 201]:
                return {
                    "error": f"MetaMask API error: {response.status_code}",
                    "details": response.text,
                }

            result = response.json()

            # Return normalized response
            return {
                "order_id": result.get("id") or result.get("order_id"),
                "widget_url": f"{self.widget_url}?order_id={result.get('id')}",
                "checkout_url": result.get("checkout_url") or f"{self.widget_url}?order_id={result.get('id')}",
                "status": "pending",
                "created_at": datetime.utcnow().isoformat(),
                "expires_at": result.get("expires_at"),
                "raw_response": result,
            }

        except Exception as e:
            return {"error": f"MetaMask order creation failed: {str(e)}"}

    async def get_status(self, order_id: str) -> Dict[str, Any]:
        """
        Check status of a MetaMask order.

        Returns:
            {
                "order_id": "mm_order_xyz",
                "status": "completed|pending|failed|expired",
                "fiat_amount": 100,
                "crypto_amount": 0.05,
                "transaction_hash": "0x...",
            }
        """
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
            }

            response = await self.client.get(
                f"{self.base_url}/v1/orders/{order_id}",
                headers=headers,
            )

            if response.status_code != 200:
                return {"error": f"Order not found", "order_id": order_id}

            result = response.json()

            # Normalize status
            status_map = {
                "completed": "completed",
                "success": "completed",
                "pending": "pending",
                "processing": "pending",
                "failed": "failed",
                "cancelled": "failed",
                "expired": "expired",
            }

            normalized_status = status_map.get(result.get("status", "").lower(), "pending")

            return {
                "order_id": order_id,
                "status": normalized_status,
                "fiat_amount": result.get("fiat_amount"),
                "fiat_currency": result.get("fiat_currency"),
                "crypto_amount": result.get("crypto_amount"),
                "crypto_currency": result.get("crypto_currency"),
                "wallet_address": result.get("destination_wallet"),
                "transaction_hash": result.get("transaction_hash"),
                "created_at": result.get("created_at"),
                "completed_at": result.get("completed_at"),
                "raw_response": result,
            }

        except Exception as e:
            return {"error": f"Failed to get status: {str(e)}", "order_id": order_id}

    async def handle_webhook(self, payload: Dict[str, Any], signature: str = "") -> Dict[str, Any]:
        """
        Handle incoming MetaMask webhook.

        MetaMask webhooks include:
        - order.completed
        - order.failed
        - order.expired
        """
        try:
            # Verify webhook signature
            if self.webhook_secret and signature:
                expected_sig = hmac.new(
                    self.webhook_secret.encode(),
                    json.dumps(payload, sort_keys=True).encode(),
                    hashlib.sha256,
                ).hexdigest()

                if not hmac.compare_digest(signature, expected_sig):
                    return {"error": "Invalid webhook signature"}

            # Extract order info
            order_id = payload.get("order_id") or payload.get("id")
            event_type = payload.get("event_type") or payload.get("type", "").split(".")[-1]

            # Map event to status
            event_map = {
                "completed": "completed",
                "success": "completed",
                "failed": "failed",
                "expired": "expired",
            }

            status = event_map.get(event_type.lower(), "pending")

            return {
                "order_id": order_id,
                "status": status,
                "event": event_type,
                "fiat_amount": payload.get("fiat_amount"),
                "crypto_amount": payload.get("crypto_amount"),
                "wallet_address": payload.get("destination_wallet"),
                "transaction_hash": payload.get("transaction_hash"),
                "timestamp": datetime.utcnow().isoformat(),
            }

        except Exception as e:
            return {"error": f"Webhook processing failed: {str(e)}"}

    async def get_supported_currencies(self) -> Dict[str, Any]:
        """Get supported fiat and crypto currencies."""
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
            }

            response = await self.client.get(
                f"{self.base_url}/v1/supported-currencies",
                headers=headers,
            )

            if response.status_code != 200:
                return {
                    "fiat": ["USD", "EUR", "GBP", "AUD", "CAD"],
                    "crypto": ["ETH", "BTC", "USDT", "USDC", "DAI"],
                }

            result = response.json()
            return {
                "fiat": result.get("fiat_currencies", []),
                "crypto": result.get("crypto_currencies", []),
            }

        except Exception:
            # Return defaults on error
            return {
                "fiat": ["USD", "EUR", "GBP", "AUD", "CAD"],
                "crypto": ["ETH", "BTC", "USDT", "USDC", "DAI"],
            }

    async def get_quotes(
        self,
        amount_fiat: float,
        fiat_currency: str,
        crypto_currency: str,
    ) -> Dict[str, Any]:
        """
        Get real-time quotes from MetaMask.

        Returns:
            {
                "fiat_amount": 100,
                "crypto_amount": 0.05,
                "rate": 2000,
                "fee_fiat": 5,
                "fee_percent": 5,
                "total_fiat": 105,
            }
        """
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
            }

            params = {
                "fiat_amount": amount_fiat,
                "fiat_currency": fiat_currency.upper(),
                "crypto_currency": crypto_currency.upper(),
            }

            response = await self.client.get(
                f"{self.base_url}/v1/quotes",
                params=params,
                headers=headers,
            )

            if response.status_code != 200:
                return {"error": "Failed to fetch quotes"}

            result = response.json()

            return {
                "fiat_amount": result.get("fiat_amount"),
                "crypto_amount": result.get("crypto_amount"),
                "rate": result.get("rate"),
                "fee_fiat": result.get("fee_amount"),
                "fee_percent": result.get("fee_percent", 5),
                "total_fiat": result.get("total_fiat"),
                "valid_until": result.get("valid_until"),
            }

        except Exception as e:
            return {"error": f"Quote retrieval failed: {str(e)}"}

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()

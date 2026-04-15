"""
Transak fiat-to-crypto provider integration.
Docs: https://docs.transak.com
KYC tiers:
  - No KYC: card payments < $200 (region-dependent)
  - KYC Level 1: email + name only
  - KYC Level 2: government ID (for higher limits)
"""
import hmac
import hashlib
import json
import urllib.parse
from config import TRANSAK_API_KEY, TRANSAK_SECRET, TRANSAK_ENV, BASE_URL


TRANSAK_BASE_URLS = {
    "STAGING":    "https://global-stg.transak.com",
    "PRODUCTION": "https://global.transak.com",
}

# Crypto currency codes as Transak expects them
CRYPTO_MAP = {
    "BTC":   "BTC",
    "ETH":   "ETH",
    "USDT":  "USDT",
    "USDC":  "USDC",
    "BNB":   "BNB",
    "SOL":   "SOL",
    "TRX":   "TRX",
    "MATIC": "MATIC",
}

# Network required for tokens — Transak rejects orders without it
NETWORK_MAP = {
    "USDT":  "ethereum",   # change to "tron" for TRC-20 wallets
    "USDC":  "ethereum",
    "BNB":   "bsc",
    "TRX":   "tron",
    "MATIC": "polygon",
    "ETH":   "ethereum",
    "BTC":   "bitcoin",
    "SOL":   "solana",
}


class TransakProvider:
    name = "transak"

    def build_widget_url(self, payment: dict) -> str:
        """
        Build the Transak checkout URL.
        Customer is redirected here to complete fiat→crypto purchase.
        """
        base = TRANSAK_BASE_URLS.get(TRANSAK_ENV, TRANSAK_BASE_URLS["STAGING"])

        crypto = payment["crypto_currency"]
        params = {
            "apiKey":                  TRANSAK_API_KEY,
            "defaultCryptoCurrency":   CRYPTO_MAP.get(crypto, "USDT"),
            "network":                 NETWORK_MAP.get(crypto, "ethereum"),
            "walletAddress":           payment["wallet_address"],
            "fiatCurrency":            payment["fiat_currency"],
            "defaultPaymentMethod":    "credit_debit_card",
            "redirectURL":             f"{BASE_URL}/pay/success/{payment['id']}",
            "partnerOrderId":          payment["id"],
            "disableWalletAddressForm": "true",
        }

        if payment.get("amount"):
            params["fiatAmount"] = str(payment["amount"])

        if payment.get("customer_email"):
            params["email"] = payment["customer_email"]

        if payment.get("customer_name"):
            name_parts = payment["customer_name"].strip().split()
            if name_parts:
                user_data = {"firstName": name_parts[0]}
                if len(name_parts) > 1:
                    user_data["lastName"] = " ".join(name_parts[1:])
                params["userData"] = json.dumps(user_data)

        if payment.get("link_id"):
            params["partnerCustomerId"] = payment["link_id"]

        query = urllib.parse.urlencode(params)
        return f"{base}?{query}"

    def verify_webhook(self, raw_body: bytes, signature: str) -> bool:
        """Verify Transak webhook HMAC signature."""
        if not TRANSAK_SECRET or TRANSAK_SECRET.startswith("YOUR_"):
            return True  # skip in dev/test
        computed = hmac.new(
            TRANSAK_SECRET.encode(),
            raw_body,
            hashlib.sha512,
        ).hexdigest()
        return hmac.compare_digest(computed, signature)

    def parse_webhook(self, payload: dict) -> dict | None:
        """
        Normalize Transak webhook into internal format.
        Returns dict with keys: payment_id, status, provider_tx_id, etc.
        """
        data = payload.get("data")
        order = data if isinstance(data, dict) else payload

        # Map Transak statuses to internal statuses
        status_map = {
            "AWAITING_PAYMENT_FROM_USER": "pending",
            "PAYMENT_DONE_MARKED_BY_USER": "processing",
            "PROCESSING": "processing",
            "PENDING_DELIVERY_FROM_TRANSAK": "processing",
            "ON_HOLD_PENDING_DELIVERY_FROM_TRANSAK": "processing",
            "COMPLETED": "completed",
            "FAILED": "failed",
            "REFUNDED": "refunded",
            "CANCELLED": "cancelled",
        }

        raw_status = order.get("status", "")
        return {
            "payment_id":       order.get("partnerOrderId"),
            "provider_order_id": order.get("id"),
            "provider_tx_id":   order.get("transactionHash"),
            "status":           status_map.get(raw_status, "pending"),
            "crypto_amount":    order.get("cryptoAmount"),
            "exchange_rate":    order.get("conversionPrice"),
            "fee_amount":       order.get("totalFeeInFiat"),
            "raw_status":       raw_status,
        }

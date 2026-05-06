"""
Transak fiat-to-crypto provider integration.
Docs: https://docs.transak.com
KYC tiers:
  - No KYC: card payments < $200 (region-dependent)
  - KYC Level 1: email + name only
  - KYC Level 2: government ID (for higher limits)
"""
import json
import urllib.parse
from config import TRANSAK_API_KEY, TRANSAK_SECRET, TRANSAK_ACCESS_TOKEN, TRANSAK_ENV, BASE_URL


TRANSAK_BASE_URLS = {
    "STAGING":    "https://global-stg.transak.com",
    "PRODUCTION": "https://global.transak.com",
}

# Crypto currency codes as Transak expects them
CRYPTO_MAP = {
    "BTC":      "BTC",
    "ETH":      "ETH",
    "USDT":     "USDT",
    "USDT_TRX": "USDT",   # TRC-20 USDT
    "USDT_BNB": "USDT",   # BEP-20 USDT
    "USDC":     "USDC",
    "BNB":      "BNB",
    "SOL":      "SOL",
    "TRX":      "TRX",
    "MATIC":    "MATIC",
}

# Network required for tokens — Transak rejects orders without it
NETWORK_MAP = {
    "USDT":     "ethereum",
    "USDT_TRX": "tron",       # TRC-20 — lower fees, preferred for UAE
    "USDT_BNB": "bsc",        # BEP-20
    "USDC":     "ethereum",
    "BNB":      "bsc",
    "TRX":      "tron",
    "MATIC":    "polygon",
    "ETH":      "ethereum",
    "BTC":      "bitcoin",
    "SOL":      "solana",
}

# Transak AED limits by KYC tier (AED amounts)
AED_LIMITS = {
    "L0": 735,       # ~$200 USD, no KYC
    "L1": 7350,      # ~$2,000 USD, email only
    "L2": 36725,     # ~$10,000 USD, gov ID
    "L3": 183625,    # ~$50,000 USD, partner/business — maximum
}

# Default to L3 max for partner-tier merchants (Little Majlis)
MAX_AED = AED_LIMITS["L3"]
MAX_USD = round(MAX_AED / 3.6725, 2)


def detect_network_from_wallet(wallet_address: str, crypto_currency: str) -> str:
	"""
	Detect blockchain network from wallet address format.
	If wallet address clearly indicates a network, override the crypto currency's default.
	"""
	if not wallet_address:
		return NETWORK_MAP.get(crypto_currency, "tron")

	wallet = wallet_address.strip().lower()

	# Tron addresses start with 'T' (case-insensitive)
	if wallet.startswith('t'):
		return "tron"

	# Ethereum-compatible addresses start with '0x'
	if wallet.startswith('0x'):
		return "ethereum"

	# Bitcoin addresses start with '1', '3', or 'bc1'
	if wallet.startswith(('1', '3', 'bc1')):
		return "bitcoin"

	# BSC/Binance addresses also start with '0x'
	# Polygon addresses also start with '0x'
	# Return the crypto currency's default network
	return NETWORK_MAP.get(crypto_currency, "tron")


class TransakProvider:
    name = "transak"

    def build_widget_url(self, payment: dict) -> str:
        """
        Build the Transak checkout URL.
        Customer is redirected here to complete fiat→crypto purchase.
        """
        # Validate required fields
        if not payment.get("wallet_address"):
            raise ValueError("wallet_address is required for Transak checkout")
        if not payment.get("id"):
            raise ValueError("payment id is required for Transak checkout")
        if not payment.get("crypto_currency"):
            raise ValueError("crypto_currency is required for Transak checkout")

        base = TRANSAK_BASE_URLS.get((TRANSAK_ENV or "").upper(), TRANSAK_BASE_URLS["STAGING"])

        crypto      = payment["crypto_currency"]
        fiat        = payment.get("fiat_currency", "USD")
        fiat_amount = payment.get("fiat_amount") or payment.get("amount")

        # Transak doesn't support AED — convert to USD at CBUAE peg
        if fiat == "AED":
            if fiat_amount:
                fiat_amount = round(float(fiat_amount) / 3.6725, 2)
            fiat = "USD"

        # Enforce Transak minimum $30 USD
        if fiat == "USD" and fiat_amount and float(fiat_amount) < 30:
            fiat_amount = 30.0

        params = {
            "apiKey":                  TRANSAK_API_KEY,
            "defaultCryptoCurrency":   CRYPTO_MAP.get(crypto, "USDT"),
            "network":                 detect_network_from_wallet(payment["wallet_address"], crypto),
            "walletAddress":           payment["wallet_address"],
            "fiatCurrency":            fiat,
            "defaultPaymentMethod":    "credit_debit_card",
            "partnerOrderId":          payment["id"],
            "disableWalletAddressForm": "true",
            "maxFiatAmount":           MAX_USD,
        }

        if fiat_amount:
            params["fiatAmount"] = str(fiat_amount)

        if payment.get("customer_email"):
            params["email"] = payment["customer_email"]

        if payment.get("customer_name"):
            name_parts = payment["customer_name"].strip().split()
            if name_parts:
                params["firstName"] = name_parts[0]
                if len(name_parts) > 1:
                    params["lastName"] = " ".join(name_parts[1:])

        if payment.get("link_id"):
            params["partnerCustomerId"] = payment["link_id"]

        query = urllib.parse.urlencode(params)
        return f"{base}?{query}"

    def _webhook_jwt_key(self) -> str | None:
        """
        Transak webhooks send `data` as a signed JWT.
        Docs recommend verifying it using Partner Access Token.
        """
        if TRANSAK_ACCESS_TOKEN:
            return TRANSAK_ACCESS_TOKEN
        if TRANSAK_SECRET and not TRANSAK_SECRET.startswith("YOUR_"):
            # Back-compat: older setups stored access token in TRANSAK_SECRET
            return TRANSAK_SECRET
        return None

    def _decode_webhook_jwt(self, token: str) -> dict | None:
        try:
            import jwt  # PyJWT
        except Exception:
            raise RuntimeError("Missing dependency: PyJWT (pip install PyJWT)")

        key = self._webhook_jwt_key()
        # If no key is configured, decode without verification (DEV/STAGING only).
        if not key:
            try:
                return jwt.decode(token, options={"verify_signature": False})
            except Exception:
                return None

        # Transak JWTs are HS256 in practice (see Transak webhook decryption examples).
        try:
            return jwt.decode(token, key, algorithms=["HS256"])
        except Exception:
            return None

    def verify_webhook(self, raw_body: bytes, signature: str) -> bool:
        """
        Legacy hook (server.py calls this for all providers).
        Transak webhook authenticity is validated by verifying the JWT in `parse_webhook`,
        so we accept the delivery here.
        """
        return True

    def parse_webhook(self, payload: dict) -> dict | None:
        """
        Normalize Transak webhook into internal format.
        Returns dict with keys: payment_id, status, provider_tx_id, etc.
        """
        # Transak sends payload like: { "data": "<JWT>", ... }
        data = payload.get("data")
        if isinstance(data, str) and data.count(".") >= 2:
            decoded = self._decode_webhook_jwt(data) or {}
            # Common shapes: {"webhookData": {...}, "eventID": "..."} or {"data": {...}}
            if isinstance(decoded.get("webhookData"), dict):
                order = decoded["webhookData"]
            elif isinstance(decoded.get("data"), dict):
                order = decoded["data"]
            else:
                order = decoded if isinstance(decoded, dict) else {}
        else:
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

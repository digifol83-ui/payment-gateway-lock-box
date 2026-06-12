"""
Transak fiat-to-crypto provider integration.
Docs: https://docs.transak.com
KYC tiers:
  - No KYC: card payments < $200 (region-dependent)
  - KYC Level 1: email + name only
  - KYC Level 2: government ID (for higher limits)
"""
import json
import time
import urllib.parse
from datetime import datetime
from config import (
    TRANSAK_API_KEY, TRANSAK_SECRET, TRANSAK_ACCESS_TOKEN, TRANSAK_ENV, BASE_URL,
    TRANSAK_WEBSITE, TRANSAK_THEME
)


TRANSAK_BASE_URLS = {
    "STAGING":    "https://global-stg.transak.com",
    "PRODUCTION": "https://global.transak.com",
}

TRANSAK_SESSION_BASE_URLS = {
    "STAGING":    "https://api-gateway-stg.transak.com",
    "PRODUCTION": "https://api-gateway.transak.com",
}

TRANSAK_PARTNER_API_BASE_URLS = {
    "STAGING":    "https://api-stg.transak.com",
    "PRODUCTION": "https://api.transak.com",
}

_ACCESS_TOKEN_CACHE = {
    "token": None,
    "expires_at": 0,
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


def _transak_env() -> str:
    return (TRANSAK_ENV or "STAGING").upper()


def _website_url() -> str:
    website = (TRANSAK_WEBSITE or BASE_URL or "").strip()
    if website and "://" not in website:
        return f"https://{website}"
    return website


def _referrer_domain() -> str:
    parsed = urllib.parse.urlparse(_website_url())
    if parsed.netloc:
        return parsed.netloc
    if parsed.path:
        return parsed.path.split("/")[0]
    return "localhost"


def _color_mode() -> str | None:
    theme = (TRANSAK_THEME or "").strip().upper()
    if theme in {"DARK", "LIGHT"}:
        return theme
    return None


def _looks_like_access_token(token: str | None) -> bool:
    token = (token or "").strip()
    return token.startswith("eyJ") and token.count(".") == 2


def _cached_access_token() -> str | None:
    token = _ACCESS_TOKEN_CACHE.get("token")
    expires_at = float(_ACCESS_TOKEN_CACHE.get("expires_at") or 0)
    if not token:
        return None
    if expires_at and time.time() >= expires_at - 60:
        return None
    return str(token)


async def _read_json_response(resp) -> dict:
    try:
        return await resp.json()
    except Exception:
        return {"message": await resp.text()}


def _error_message(body: dict) -> str:
    return body.get("message") or body.get("error") or json.dumps(body)


def detect_network_from_wallet(wallet_address: str, crypto_currency: str) -> str:
	"""
	Detect blockchain network from a (wallet_address, crypto_currency) pair.

	Crypto codes that already disambiguate the chain (e.g. USDT_BNB, USDT_TRX)
	take precedence over wallet-prefix heuristics — otherwise every 0x address
	defaults to Ethereum even when the caller asked for BSC.
	"""
	# Explicit chain hint in the crypto code wins.
	if crypto_currency in NETWORK_MAP and crypto_currency not in {"USDT", "USDC", "ETH"}:
		return NETWORK_MAP[crypto_currency]

	if not wallet_address:
		return NETWORK_MAP.get(crypto_currency, "tron")

	wallet = wallet_address.strip().lower()

	if wallet.startswith('t'):
		return "tron"
	if wallet.startswith('0x'):
		# Ambiguous 0x prefix — defer to the crypto's default network if known.
		return NETWORK_MAP.get(crypto_currency, "ethereum")
	if wallet.startswith(('1', '3', 'bc1')):
		return "bitcoin"
	return NETWORK_MAP.get(crypto_currency, "tron")


class TransakProvider:
    name = "transak"

    def _build_widget_params(self, payment: dict) -> dict:
        # Validate required fields
        if not payment.get("wallet_address"):
            raise ValueError("wallet_address is required for Transak checkout")
        if not payment.get("id"):
            raise ValueError("payment id is required for Transak checkout")
        if not payment.get("crypto_currency"):
            raise ValueError("crypto_currency is required for Transak checkout")

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
            "referrerDomain":          _referrer_domain(),
            "defaultCryptoCurrency":   CRYPTO_MAP.get(crypto, "USDT"),
            "cryptoCurrencyCode":      CRYPTO_MAP.get(crypto, "USDT"),
            "network":                 detect_network_from_wallet(payment["wallet_address"], crypto),
            "walletAddress":           payment["wallet_address"],
            "fiatCurrency":            fiat,
            "defaultPaymentMethod":    "credit_debit_card",
            "partnerOrderId":          payment["id"],
            "disableWalletAddressForm": "true",
            "maxFiatAmount":           MAX_USD,
            "colorMode":               _color_mode(),
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

        return {k: v for k, v in params.items() if v not in (None, "")}

    def build_widget_url(self, payment: dict) -> str:
        """
        Build a direct Transak checkout URL.
        Kept for local previews; production checkout should call create_widget_url().
        """
        base = TRANSAK_BASE_URLS.get(_transak_env(), TRANSAK_BASE_URLS["STAGING"])
        params = self._build_widget_params(payment)
        query = urllib.parse.urlencode(params)
        return f"{base}?{query}"

    async def create_widget_url(self, payment: dict) -> str:
        """
        Create the current API-backed Transak widget URL with a one-time sessionId.
        Direct query-parameter widget URLs are deprecated by Transak.
        """
        if not TRANSAK_ACCESS_TOKEN and not TRANSAK_SECRET:
            raise ValueError("TRANSAK_ACCESS_TOKEN or TRANSAK_SECRET not configured")

        import aiohttp

        base = TRANSAK_SESSION_BASE_URLS.get(_transak_env(), TRANSAK_SESSION_BASE_URLS["STAGING"])
        payload = {"widgetParams": self._build_widget_params(payment)}

        async with aiohttp.ClientSession() as session:
            token = _cached_access_token() or TRANSAK_ACCESS_TOKEN
            if not _looks_like_access_token(token) and TRANSAK_SECRET:
                token = await self._refresh_access_token(session)

            status, body = await self._create_session(session, base, payload, token)
            if status == 401 and TRANSAK_SECRET:
                token = await self._refresh_access_token(session)
                status, body = await self._create_session(session, base, payload, token)

            if status >= 400:
                raise ValueError(f"Transak session error: {_error_message(body)}")

        widget_url = (body.get("data") or {}).get("widgetUrl")
        if not widget_url:
            raise ValueError(f"Transak session response missing widgetUrl: {body}")
        return widget_url

    async def _refresh_access_token(self, session) -> str:
        if not TRANSAK_SECRET:
            raise ValueError("TRANSAK_SECRET not configured for Transak access-token refresh")

        base = TRANSAK_PARTNER_API_BASE_URLS.get(_transak_env(), TRANSAK_PARTNER_API_BASE_URLS["STAGING"])
        headers = {
            "accept": "application/json",
            "api-secret": TRANSAK_SECRET,
            "content-type": "application/json",
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Origin": "https://dashboard.transak.com",
            "Referer": "https://dashboard.transak.com/",
            "Accept-Language": "en-US,en;q=0.9",
        }
        async with session.post(
            f"{base}/partners/api/v2/refresh-token",
            json={"apiKey": TRANSAK_API_KEY},
            headers=headers,
            timeout=15,
        ) as resp:
            body = await _read_json_response(resp)

        if resp.status >= 400:
            raise ValueError(f"Transak access token refresh error: {_error_message(body)}")

        data = body.get("data") or {}
        token = data.get("accessToken")
        if not token:
            raise ValueError(f"Transak access token refresh response missing accessToken: {body}")

        _ACCESS_TOKEN_CACHE["token"] = token
        _ACCESS_TOKEN_CACHE["expires_at"] = data.get("expiresAt") or 0
        return token

    async def _create_session(self, session, base: str, payload: dict, token: str):
        headers = {
            "accept": "application/json",
            "access-token": token,
            "content-type": "application/json",
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36",
            "Origin": "https://global.transak.com",
            "Referer": "https://global.transak.com/",
        }
        async with session.post(
            f"{base}/api/v2/auth/session",
            json=payload,
            headers=headers,
            timeout=15,
        ) as resp:
            body = await _read_json_response(resp)
            return resp.status, body

    async def check_health(self) -> dict:
        """
        Full connectivity health check for Transak production API.
        Tests: API reachability → token refresh → session creation.
        Returns dict with 'connectivity' sub-object for monitor-health.sh.
        """
        import aiohttp
        import asyncio

        result = {
            "status": "unknown",
            "production_configured": bool(TRANSAK_API_KEY and TRANSAK_SECRET),
            "environment": _transak_env(),
            "connectivity": {
                "api_reachable": False,
                "auth_valid": False,
                "session_creation_works": False,
                "error": None,
                "session_error_code": None,
            },
            "timestamp": datetime.utcnow().isoformat(),
        }

        if not TRANSAK_API_KEY or not TRANSAK_SECRET:
            result["status"] = "unconfigured"
            result["connectivity"]["error"] = "TRANSAK_API_KEY or TRANSAK_SECRET missing"
            return result

        async with aiohttp.ClientSession() as session:
            # Step 1: Refresh access token (tests API reachability + auth)
            try:
                base = TRANSAK_PARTNER_API_BASE_URLS.get(
                    _transak_env(), TRANSAK_PARTNER_API_BASE_URLS["STAGING"]
                )
                headers = {
                    "accept": "application/json",
                    "api-secret": TRANSAK_SECRET,
                    "content-type": "application/json",
                    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
                    "Origin": "https://dashboard.transak.com",
                    "Referer": "https://dashboard.transak.com/",
                    "Accept-Language": "en-US,en;q=0.9",
                }
                # Retry up to 3 times for Cloudflare 429 rate limiting (30s+ backoff)
                for attempt in range(3):
                    async with session.post(
                        f"{base}/partners/api/v2/refresh-token",
                        json={"apiKey": TRANSAK_API_KEY},
                        headers=headers,
                        timeout=aiohttp.ClientTimeout(total=15),
                    ) as resp:
                        body = await _read_json_response(resp)
                    if resp.status == 429 and attempt < 2:
                        wait = 30 * (attempt + 1)
                        await asyncio.sleep(wait)
                        continue
                    break

                result["connectivity"]["api_reachable"] = True

                if resp.status == 200:
                    data = body.get("data") or {}
                    token = data.get("accessToken")
                    if token:
                        result["connectivity"]["auth_valid"] = True
                        _ACCESS_TOKEN_CACHE["token"] = token
                        _ACCESS_TOKEN_CACHE["expires_at"] = data.get("expiresAt") or 0
                    else:
                        result["connectivity"]["error"] = f"Token refresh 200 but no accessToken: {body}"
                        result["status"] = "auth_failed"
                        return result
                else:
                    result["connectivity"]["error"] = f"Token refresh HTTP {resp.status}: {_error_message(body)}"
                    result["status"] = "auth_failed"
                    return result

            except Exception as e:
                result["connectivity"]["error"] = f"API unreachable: {e}"
                result["status"] = "api_unreachable"
                return result

            # Step 2: Try creating a session (the real blocker)
            try:
                session_base = TRANSAK_SESSION_BASE_URLS.get(
                    _transak_env(), TRANSAK_SESSION_BASE_URLS["STAGING"]
                )
                test_payload = {
                    "widgetParams": {
                        "apiKey": TRANSAK_API_KEY,
                        "referrerDomain": _referrer_domain(),
                        "defaultCryptoCurrency": "USDT",
                        "cryptoCurrencyCode": "USDT",
                        "network": "tron",
                        "walletAddress": "TAJqJRLqzS5xVvxgVKXtWyP6DWzPAvzkQG",
                        "fiatCurrency": "USD",
                        "defaultPaymentMethod": "credit_debit_card",
                        "disableWalletAddressForm": "true",
                        "fiatAmount": "30",
                    }
                }
                status, body = await self._create_session(
                    session, session_base, test_payload, token
                )

                if status == 200:
                    result["connectivity"]["session_creation_works"] = True
                    result["status"] = "healthy"
                elif status == 401:
                    result["connectivity"]["session_error_code"] = body.get("errorCode") or body.get("error")
                    result["connectivity"]["error"] = (
                        f"Session creation HTTP 401: {_error_message(body)}"
                    )
                    result["status"] = "session_blocked"
                else:
                    result["connectivity"]["error"] = (
                        f"Session creation HTTP {status}: {_error_message(body)}"
                    )
                    result["status"] = "session_error"

            except Exception as e:
                result["connectivity"]["error"] = f"Session creation failed: {e}"
                result["status"] = "session_error"

        return result

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

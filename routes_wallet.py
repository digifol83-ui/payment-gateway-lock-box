"""
Direct-wallet payment routes for MetaMask / Trust Wallet.

Endpoints:
  GET  /api/wallet/chains                 - list supported chains + assets + merchant wallet
  GET  /api/wallet/price                  - live fiat->crypto conversion via CoinGecko
  POST /api/wallet/quote                  - one-shot quote (amount + breakdown)
  POST /api/payments/{id}/submit-tx       - user posts tx_hash after sending
  GET  /api/payments/{id}/verify          - server-side on-chain verification via RPC
  GET  /api/payments/{id}                 - payment status

No third-party API keys required.
"""
import os
import time
import secrets
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
import httpx

from database.migrations import AsyncDB
from wallet_chains import CHAINS, get_chain, resolve_asset
from telegram_notify import notify_payment_update

router = APIRouter()
logger = logging.getLogger(__name__)

# --- No-KYC amount caps (kept below KYC_FREE_LIMIT_USD = 100 in config.py) ----
NO_KYC_LIMITS = {
    "USD": 100.0, "EUR": 95.0,  "GBP": 80.0,
    "AED": 367.0, "AUD": 150.0, "CAD": 135.0,
}

# --- OTP store (in-memory, 10-minute TTL, attempt cap) ------------------------
_OTP: dict[str, dict] = {}  # email -> {code, expires_at, attempts, verified}
_OTP_TTL = 600   # 10 minutes
_OTP_MAX_ATTEMPTS = 5

# --- DB dep (mirrors server.py) -------------------------------------------------
async def get_db():
    from server import db_instance
    return db_instance

# --- Price cache (CoinGecko free tier: 30 calls/min) ---------------------------
_PRICE_CACHE: dict[str, tuple[float, float]] = {}  # key -> (price, fetched_at)
_PRICE_TTL = 30.0  # seconds

async def coingecko_price(coingecko_id: str, fiat: str = "usd") -> Optional[float]:
    fiat = fiat.lower()
    key = f"{coingecko_id}:{fiat}"
    now = time.time()
    cached = _PRICE_CACHE.get(key)
    if cached and (now - cached[1]) < _PRICE_TTL:
        return cached[0]

    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {"ids": coingecko_id, "vs_currencies": fiat}
    try:
        async with httpx.AsyncClient(timeout=8) as cli:
            r = await cli.get(url, params=params)
            r.raise_for_status()
            data = r.json()
            price = float(data.get(coingecko_id, {}).get(fiat, 0))
            if price > 0:
                _PRICE_CACHE[key] = (price, now)
                return price
    except Exception as e:
        logger.warning(f"coingecko_price_failed {coingecko_id}/{fiat}: {e}")
    return None

# --- RPC helpers ---------------------------------------------------------------
async def _rpc(rpc_url: str, method: str, params: list):
    async with httpx.AsyncClient(timeout=15) as cli:
        r = await cli.post(rpc_url, json={
            "jsonrpc": "2.0", "id": 1, "method": method, "params": params,
        })
        r.raise_for_status()
        data = r.json()
        if "error" in data:
            raise RuntimeError(data["error"])
        return data.get("result")

ERC20_TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"

async def verify_tx_onchain(chain_key: str, tx_hash: str, expected_to: str,
                            asset: str, min_amount: float) -> dict:
    """
    Verify a tx hash on-chain.
    Returns: {ok, status, confirmations, value, asset, error?}
    """
    chain = CHAINS.get(chain_key)
    if not chain:
        return {"ok": False, "error": f"unknown_chain:{chain_key}"}
    rpc = chain["rpc"]
    expected_to = expected_to.lower()
    asset_info = resolve_asset(chain_key, asset)
    if not asset_info:
        return {"ok": False, "error": f"unsupported_asset:{asset}@{chain_key}"}

    try:
        receipt = await _rpc(rpc, "eth_getTransactionReceipt", [tx_hash])
        if not receipt:
            return {"ok": False, "status": "pending"}
        if int(receipt.get("status", "0x0"), 16) != 1:
            return {"ok": False, "status": "failed"}

        # Confirmations
        latest = await _rpc(rpc, "eth_blockNumber", [])
        confirmations = max(0, int(latest, 16) - int(receipt["blockNumber"], 16))

        if asset_info["kind"] == "native":
            tx = await _rpc(rpc, "eth_getTransactionByHash", [tx_hash])
            if not tx:
                return {"ok": False, "error": "tx_not_found"}
            if (tx.get("to") or "").lower() != expected_to:
                return {"ok": False, "error": "wrong_recipient", "got": tx.get("to")}
            value_wei = int(tx.get("value", "0x0"), 16)
            value = value_wei / (10 ** 18)
            if value + 1e-9 < min_amount:
                return {"ok": False, "error": "amount_too_low", "got": value, "min": min_amount}
            return {"ok": True, "status": "confirmed", "confirmations": confirmations,
                    "value": value, "asset": asset}

        # ERC-20: find Transfer event in logs
        contract = asset_info["contract"].lower()
        decimals = asset_info["decimals"]
        topic_to = "0x" + expected_to[2:].rjust(64, "0")
        total = 0
        for log in receipt.get("logs", []):
            if (log.get("address") or "").lower() != contract:
                continue
            topics = log.get("topics", [])
            if len(topics) < 3 or topics[0] != ERC20_TRANSFER_TOPIC:
                continue
            if topics[2].lower() != topic_to:
                continue
            total += int(log.get("data", "0x0"), 16)
        value = total / (10 ** decimals)
        if value <= 0:
            return {"ok": False, "error": "no_transfer_to_recipient"}
        if value + 1e-9 < min_amount:
            return {"ok": False, "error": "amount_too_low", "got": value, "min": min_amount}
        return {"ok": True, "status": "confirmed", "confirmations": confirmations,
                "value": value, "asset": asset}
    except Exception as e:
        logger.exception(f"verify_tx_onchain failed: {e}")
        return {"ok": False, "error": str(e)}

# ------------------------------------------------------------------------------
@router.get("/api/wallet/chains")
async def list_chains():
    out = {}
    for key, c in CHAINS.items():
        out[key] = {
            "chain_id": c["chain_id"],
            "name": key,
            "explorer": c["explorer"],
            "native": c["native"],
            "tokens": list(c["tokens"].keys()),
            "merchant_wallet": c["merchant_wallet"],
        }
    return {"chains": out}

@router.get("/api/wallet/price")
async def get_price(crypto: str, fiat: str = "USD", chain: str = "bsc"):
    asset = resolve_asset(chain, crypto)
    if not asset:
        raise HTTPException(400, f"unsupported {crypto}@{chain}")
    price = await coingecko_price(asset["coingecko_id"], fiat.lower())
    if price is None:
        raise HTTPException(502, "price_feed_unavailable")
    return {"crypto": crypto.upper(), "fiat": fiat.upper(), "chain": chain,
            "price": price, "source": "coingecko"}

@router.post("/api/wallet/quote")
async def quote(payload: dict):
    fiat_amount = float(payload.get("amount") or 0)
    fiat = (payload.get("fiat") or "USD").upper()
    crypto = (payload.get("crypto") or "USDT").upper()
    chain = (payload.get("chain") or "bsc").lower()
    if fiat_amount <= 0:
        raise HTTPException(400, "amount must be > 0")
    asset = resolve_asset(chain, crypto)
    if not asset:
        raise HTTPException(400, f"unsupported {crypto}@{chain}")
    price = await coingecko_price(asset["coingecko_id"], fiat.lower())
    if not price:
        raise HTTPException(502, "price_feed_unavailable")
    chain_cfg = CHAINS[chain]
    fee_pct = 0.015  # BeastPay 1.5% routing fee on direct-wallet
    fee_fiat = round(fiat_amount * fee_pct, 2)
    total_fiat = round(fiat_amount + fee_fiat, 2)
    crypto_amount = round(total_fiat / price, 8)
    return {
        "amount_fiat": fiat_amount,
        "fee_fiat": fee_fiat,
        "total_fiat": total_fiat,
        "rate": price,
        "crypto_amount": crypto_amount,
        "crypto": crypto,
        "fiat": fiat,
        "chain": chain,
        "chain_id": chain_cfg["chain_id"],
        "merchant_wallet": chain_cfg["merchant_wallet"],
        "asset_kind": asset["kind"],
        "asset_contract": asset.get("contract"),
        "asset_decimals": asset["decimals"],
        "expires_in_sec": int(_PRICE_TTL),
    }

@router.post("/api/payments/{payment_id}/submit-tx")
async def submit_tx(payment_id: str, payload: dict, db: AsyncDB = Depends(get_db)):
    tx_hash = (payload.get("tx_hash") or "").strip()
    chain = (payload.get("chain") or "bsc").lower()
    if not tx_hash.startswith("0x") or len(tx_hash) != 66:
        raise HTTPException(400, "invalid tx_hash")
    if chain not in CHAINS:
        raise HTTPException(400, f"unsupported chain {chain}")

    row = await db.fetchone("SELECT * FROM payments WHERE id = ?", (payment_id,))
    if not row:
        raise HTTPException(404, "payment not found")

    await db.execute(
        "UPDATE payments SET tx_hash = ?, chain = ?, status = ?, updated_at = ? WHERE id = ?",
        (tx_hash, chain, "submitted", _now(), payment_id),
    )
    # Fire-and-forget verification on submit
    result = await _verify_payment(db, payment_id)
    return {"payment_id": payment_id, "tx_hash": tx_hash, "chain": chain,
            "explorer_url": CHAINS[chain]["explorer"] + tx_hash,
            "verification": result}

@router.get("/api/payments/{payment_id}/verify")
async def verify_payment(payment_id: str, db: AsyncDB = Depends(get_db)):
    return await _verify_payment(db, payment_id)

@router.get("/api/payments/{payment_id}")
async def get_payment(payment_id: str, db: AsyncDB = Depends(get_db)):
    row = await db.fetchone("SELECT * FROM payments WHERE id = ?", (payment_id,))
    if not row:
        raise HTTPException(404, "payment not found")
    return dict(row) if not isinstance(row, dict) else row

async def _verify_payment(db: AsyncDB, payment_id: str):
    row = await db.fetchone("SELECT * FROM payments WHERE id = ?", (payment_id,))
    if not row:
        raise HTTPException(404, "payment not found")
    rec = dict(row) if not isinstance(row, dict) else row
    tx_hash = rec.get("tx_hash")
    chain = (rec.get("chain") or "bsc").lower()
    if not tx_hash:
        return {"payment_id": payment_id, "status": rec.get("status"), "ok": False,
                "error": "no_tx_hash_submitted"}
    chain_cfg = CHAINS.get(chain)
    if not chain_cfg:
        return {"payment_id": payment_id, "ok": False, "error": f"unknown_chain:{chain}"}

    asset = (rec.get("crypto_currency") or "USDT").upper()
    fiat_amount = float(rec.get("amount") or 0)
    asset_info = resolve_asset(chain, asset)
    if not asset_info:
        return {"payment_id": payment_id, "ok": False, "error": f"unsupported_asset:{asset}@{chain}"}
    price = await coingecko_price(asset_info["coingecko_id"], (rec.get("fiat_currency") or "USD").lower())
    if not price:
        return {"payment_id": payment_id, "ok": False, "error": "price_feed_unavailable"}
    min_crypto = (fiat_amount * 0.97) / price  # 3% tolerance for slippage/price drift

    result = await verify_tx_onchain(chain, tx_hash, chain_cfg["merchant_wallet"], asset, min_crypto)
    new_status = rec.get("status")
    if result.get("ok") and result.get("confirmations", 0) >= 1:
        new_status = "paid"
    elif result.get("status") == "pending":
        new_status = "submitted"
    elif result.get("status") == "failed":
        new_status = "failed"

    if new_status != rec.get("status"):
        await db.execute(
            "UPDATE payments SET status = ?, updated_at = ? WHERE id = ?",
            (new_status, _now(), payment_id),
        )
        try:
            await notify_payment_update({**rec, "status": new_status, "tx_hash": tx_hash})
        except Exception as e:
            logger.warning(f"telegram_notify_failed: {e}")

    return {"payment_id": payment_id, "status": new_status,
            "explorer_url": chain_cfg["explorer"] + tx_hash, **result}

def _now():
    from datetime import datetime
    return datetime.utcnow()


# =============================================================================
# Email OTP — gates the card-to-crypto path. No KYC, just an email-of-record.
# =============================================================================
def _gen_otp() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


@router.post("/api/otp/send")
async def otp_send(payload: dict):
    email = (payload.get("email") or "").strip().lower()
    if "@" not in email or "." not in email.split("@")[-1]:
        raise HTTPException(400, "invalid email")
    code = _gen_otp()
    _OTP[email] = {"code": code, "expires_at": time.time() + _OTP_TTL,
                   "attempts": 0, "verified": False}
    try:
        from mailer import send_email
        send_email(
            to=email,
            subject=f"BeastPay verification code: {code}",
            body=(
                f"Your BeastPay verification code is: {code}\n\n"
                f"This code expires in 10 minutes. If you did not request it, ignore this email.\n"
            ),
        )
    except Exception as e:
        logger.exception(f"otp_send_mail_failed: {e}")
        # Keep the code in memory (dev fallback) but tell caller
        return {"sent": False, "error": "mail_failed", "detail": str(e)}
    return {"sent": True, "email": email, "ttl_sec": _OTP_TTL}


@router.post("/api/otp/verify")
async def otp_verify(payload: dict):
    email = (payload.get("email") or "").strip().lower()
    code = (payload.get("code") or "").strip()
    rec = _OTP.get(email)
    if not rec:
        raise HTTPException(404, "no_otp_pending")
    if time.time() > rec["expires_at"]:
        del _OTP[email]
        raise HTTPException(410, "otp_expired")
    if rec["attempts"] >= _OTP_MAX_ATTEMPTS:
        raise HTTPException(429, "too_many_attempts")
    rec["attempts"] += 1
    if code != rec["code"]:
        return {"verified": False, "remaining_attempts": _OTP_MAX_ATTEMPTS - rec["attempts"]}
    rec["verified"] = True
    return {"verified": True, "email": email}


def _otp_is_verified(email: str) -> bool:
    rec = _OTP.get((email or "").strip().lower())
    return bool(rec and rec.get("verified") and time.time() <= rec["expires_at"])


# =============================================================================
# Card-to-crypto via Transak. No PAN/CVV ever touches our backend; Transak
# operates the iframe, handles 3-D Secure (OTP from issuer bank), and settles
# crypto directly to the user's MetaMask / Trust Wallet address.
# =============================================================================
@router.get("/api/wallet/limits")
async def wallet_limits():
    return {
        "no_kyc": NO_KYC_LIMITS,
        "note": "Amounts at or below these caps stay in the no-KYC tier.",
    }


@router.post("/api/wallet/card-widget")
async def card_widget(payload: dict, db: AsyncDB = Depends(get_db)):
    """
    Create a Transak hosted widget URL for a card-to-crypto purchase that
    settles to a MetaMask or Trust Wallet address.

    Required: email (OTP-verified), wallet_address, amount, fiat, crypto, chain.
    """
    email = (payload.get("email") or "").strip().lower()
    if not _otp_is_verified(email):
        raise HTTPException(403, "otp_not_verified")

    wallet_address = (payload.get("wallet_address") or "").strip()
    if not (wallet_address.startswith("0x") and len(wallet_address) == 42):
        raise HTTPException(400, "invalid wallet_address")

    fiat = (payload.get("fiat") or "USD").upper()
    amount = float(payload.get("amount") or 0)
    if amount <= 0:
        raise HTTPException(400, "amount must be > 0")
    cap = NO_KYC_LIMITS.get(fiat, NO_KYC_LIMITS["USD"])
    if amount > cap:
        raise HTTPException(400, f"amount exceeds no-KYC cap of {cap} {fiat}")

    crypto = (payload.get("crypto") or "USDT").upper()
    chain = (payload.get("chain") or "bsc").lower()
    if chain not in CHAINS:
        raise HTTPException(400, f"unsupported chain {chain}")

    # Transak needs chain-aware crypto codes. Map (crypto, chain) -> Transak code.
    # Falls back to the raw asset code, which Transak treats as Ethereum mainnet.
    TRANSAK_CODE = {
        ("USDT", "bsc"):      "USDT_BNB",
        ("USDT", "ethereum"): "USDT",
        ("USDT", "polygon"):  "USDT",   # Transak treats with network override
        ("USDT", "arbitrum"): "USDT",
        ("USDC", "bsc"):      "USDC",
        ("USDC", "ethereum"): "USDC",
        ("USDC", "polygon"):  "USDC",
        ("USDC", "base"):     "USDC",
        ("USDC", "arbitrum"): "USDC",
        ("ETH",  "ethereum"): "ETH",
        ("ETH",  "arbitrum"): "ETH",
        ("ETH",  "base"):     "ETH",
        ("BNB",  "bsc"):      "BNB",
        ("MATIC","polygon"):  "MATIC",
    }
    transak_crypto = TRANSAK_CODE.get((crypto, chain), crypto)

    # Record payment row so /verify and webhooks can find it later
    import uuid
    pid = str(uuid.uuid4())
    now = _now()
    await db.execute(
        """INSERT INTO payments
           (id, merchant_id, amount, fiat_currency, crypto_currency, provider,
            wallet_address, customer_email, status, chain, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (pid, None, amount, fiat, crypto, "transak", wallet_address,
         email, "card_pending", chain, now, now),
    )

    transak_payload = {
        "id": pid,
        "wallet_address": wallet_address,
        "crypto_currency": transak_crypto,
        "fiat_currency": fiat,
        "fiat_amount": amount,
        "customer_email": email,
    }
    try:
        from providers import PROVIDERS
        widget_url = await PROVIDERS["transak"].create_widget_url(transak_payload)
    except Exception as e:
        logger.warning(f"transak_signed_widget_failed, using direct URL: {e}")
        # Direct query-param widget URL: deprecated by Transak but still renders
        # the hosted checkout. Acceptable for low-amount no-KYC flow.
        try:
            from providers import PROVIDERS
            widget_url = PROVIDERS["transak"].build_widget_url(transak_payload)
        except Exception as e2:
            raise HTTPException(502, f"transak_widget_unavailable: {e2}")

    return {
        "payment_id": pid,
        "widget_url": widget_url,
        "amount": amount,
        "fiat": fiat,
        "crypto": crypto,
        "chain": chain,
        "wallet_address": wallet_address,
        "no_kyc_cap": cap,
    }


# =============================================================================
# Multi-on-ramp aggregator. Same pattern as MetaMask's native Buy widget:
# show MoonPay, Transak, Mercuryo, Ramp side-by-side, each opens in a new
# window with prefilled URL parameters. No iframes (every on-ramp blocks
# embedding via X-Frame-Options / CSP).
# =============================================================================
def _onramp_urls(amount: float, fiat: str, crypto: str, chain: str,
                 wallet: str, pid: str, email: str) -> list[dict]:
    """Return prefilled hosted-widget URLs for each available on-ramp."""
    import urllib.parse as _u
    out = []

    # ---- Transak ----------------------------------------------------------
    # Chain-aware crypto codes for Transak
    transak_crypto_map = {
        ("USDT", "bsc"): ("USDT", "bsc"),
        ("USDT", "ethereum"): ("USDT", "ethereum"),
        ("USDT", "polygon"): ("USDT", "polygon"),
        ("USDC", "bsc"): ("USDC", "bsc"),
        ("USDC", "ethereum"): ("USDC", "ethereum"),
        ("USDC", "polygon"): ("USDC", "polygon"),
        ("USDC", "base"): ("USDC", "base"),
        ("ETH", "ethereum"): ("ETH", "ethereum"),
        ("ETH", "base"): ("ETH", "base"),
        ("BNB", "bsc"): ("BNB", "bsc"),
    }
    t_code, t_net = transak_crypto_map.get((crypto, chain), (crypto, chain))
    # Transak rejects AED — convert
    t_fiat, t_amount = fiat, amount
    if t_fiat == "AED":
        t_amount = round(amount / 3.6725, 2)
        t_fiat = "USD"
    # Transak min $30
    if t_fiat == "USD" and t_amount < 30:
        t_amount = 30.0
    transak_key = os.getenv("TRANSAK_API_KEY", "")
    if transak_key:
        params = {
            "apiKey": transak_key,
            "cryptoCurrencyCode": t_code,
            "network": t_net,
            "walletAddress": wallet,
            "fiatCurrency": t_fiat,
            "fiatAmount": str(t_amount),
            "defaultPaymentMethod": "credit_debit_card",
            "disableWalletAddressForm": "true",
            "partnerOrderId": pid,
            "email": email,
        }
        out.append({
            "id": "transak",
            "name": "Transak",
            "logo": "🟣",
            "url": "https://global.transak.com?" + _u.urlencode(params),
            "min_fiat": 30 if t_fiat == "USD" else None,
            "note": "Most coverage globally. Card + Apple Pay + Google Pay.",
        })

    # ---- MoonPay ----------------------------------------------------------
    moonpay_key = os.getenv("MOONPAY_API_KEY", "")
    if moonpay_key:
        is_sandbox = moonpay_key.startswith("pk_test_")
        host = "buy-sandbox.moonpay.com" if is_sandbox else "buy.moonpay.com"
        # MoonPay currency codes
        mp_code_map = {
            ("USDT", "bsc"): "usdt_bsc",
            ("USDT", "ethereum"): "usdt",
            ("USDT", "polygon"): "usdt_polygon",
            ("USDC", "ethereum"): "usdc",
            ("USDC", "polygon"): "usdc_polygon",
            ("USDC", "bsc"): "usdc_bsc",
            ("USDC", "base"): "usdc_base",
            ("ETH", "ethereum"): "eth",
            ("ETH", "base"): "eth_base",
            ("BNB", "bsc"): "bnb_bsc",
        }
        mp_code = mp_code_map.get((crypto, chain), crypto.lower())
        # MoonPay rejects AED — fall back to USD
        mp_fiat, mp_amount = fiat.lower(), amount
        if mp_fiat == "aed":
            mp_amount = round(amount / 3.6725, 2); mp_fiat = "usd"
        params = {
            "apiKey": moonpay_key,
            "currencyCode": mp_code,
            "walletAddress": wallet,
            "baseCurrencyAmount": str(mp_amount),
            "baseCurrencyCode": mp_fiat,
            "email": email,
            "externalTransactionId": pid,
        }
        out.append({
            "id": "moonpay",
            "name": "MoonPay" + (" (sandbox)" if is_sandbox else ""),
            "logo": "🌙",
            "url": f"https://{host}?{_u.urlencode(params)}",
            "min_fiat": 20 if mp_fiat == "usd" else None,
            "note": "Fast, Apple Pay supported. " +
                    ("Sandbox: test mode only — get pk_live_ for prod." if is_sandbox else ""),
        })

    # ---- Mercuryo (default widget, no API key required) -------------------
    mercuryo_net = {
        "bsc": "BINANCESMARTCHAIN", "ethereum": "ETHEREUM",
        "polygon": "POLYGON", "arbitrum": "ARBITRUM", "base": "BASE",
    }.get(chain)
    if mercuryo_net:
        merc_fiat, merc_amount = fiat, amount
        if merc_fiat == "AED":
            merc_amount = round(amount / 3.6725, 2); merc_fiat = "USD"
        params = {
            "type": "buy",
            "currency": crypto,
            "network": mercuryo_net,
            "fiat_currency": merc_fiat,
            "amount": str(merc_amount),
            "address": wallet,
            "merchant_transaction_id": pid,
            "email": email,
        }
        out.append({
            "id": "mercuryo",
            "name": "Mercuryo",
            "logo": "💜",
            "url": "https://exchange.mercuryo.io/?" + _u.urlencode(params),
            "min_fiat": 30 if merc_fiat == "USD" else None,
            "note": "Popular in Europe / UAE. No app login needed.",
        })

    # ---- Ramp Network (default widget, no API key required) ---------------
    ramp_asset = {
        "bsc": f"BSC_{crypto}",
        "ethereum": f"ETH_{crypto}" if crypto != "ETH" else "ETH_ETH",
        "polygon": f"MATIC_{crypto}",
        "arbitrum": f"ARBITRUM_{crypto}",
        "base": f"BASE_{crypto}",
    }.get(chain)
    if ramp_asset:
        ramp_fiat, ramp_amount = fiat, amount
        if ramp_fiat == "AED":
            ramp_amount = round(amount / 3.6725, 2); ramp_fiat = "USD"
        params = {
            "swapAsset": ramp_asset,
            "userAddress": wallet,
            "fiatValue": str(ramp_amount),
            "fiatCurrency": ramp_fiat,
            "userEmailAddress": email,
        }
        out.append({
            "id": "ramp",
            "name": "Ramp Network",
            "logo": "🔵",
            "url": "https://buy.ramp.network/?" + _u.urlencode(params),
            "min_fiat": None,
            "note": "Direct bank transfer also supported.",
        })

    return out


@router.get("/api/moonpay/state")
async def moonpay_state():
    """Current stage of the MoonPay auto-activation pipeline."""
    try:
        from moonpay_orchestrator import _state_read
        return _state_read()
    except Exception as e:
        return {"stage": "error", "error": str(e)}


@router.post("/api/moonpay/extract")
async def moonpay_extract(payload: dict):
    """Run Unsloth /extract-fields on arbitrary text. Returns parsed keys."""
    text = (payload.get("text") or "").strip()
    if not text:
        raise HTTPException(400, "text required")
    try:
        from moonpay_orchestrator import extract_keys_from_text
        return extract_keys_from_text(text)
    except Exception as e:
        logger.exception(f"moonpay_extract_failed: {e}")
        raise HTTPException(500, str(e))


@router.post("/api/moonpay/watch-once")
async def moonpay_watch_once(payload: dict, request: Request):
    """
    Single IMAP poll — fetches recent MoonPay emails, runs Unsloth extraction,
    deploys if a pk_live_ key is found. Admin-gated.
    """
    admin_key = os.getenv("ADMIN_API_KEY", "")
    provided = request.headers.get("X-Api-Key") or (payload.get("admin_key") if isinstance(payload, dict) else None)
    if not admin_key or provided != admin_key:
        raise HTTPException(401, "admin key required")
    try:
        import asyncio
        from moonpay_orchestrator import cmd_watch
        # cmd_watch with loop=False does a single pass and returns
        loop = asyncio.get_event_loop()
        rc = await loop.run_in_executor(None, lambda: cmd_watch(loop=False))
        return {"rc": rc, "ok": rc == 0}
    except Exception as e:
        logger.exception(f"moonpay_watch_failed: {e}")
        raise HTTPException(500, str(e))


@router.post("/api/wallet/onramps")
async def list_onramps(payload: dict, db: AsyncDB = Depends(get_db)):
    """OTP-gated. Returns all available on-ramps as a side-by-side picker."""
    email = (payload.get("email") or "").strip().lower()
    if not _otp_is_verified(email):
        raise HTTPException(403, "otp_not_verified")
    wallet_address = (payload.get("wallet_address") or "").strip()
    if not (wallet_address.startswith("0x") and len(wallet_address) == 42):
        raise HTTPException(400, "invalid wallet_address")
    fiat = (payload.get("fiat") or "USD").upper()
    amount = float(payload.get("amount") or 0)
    if amount <= 0:
        raise HTTPException(400, "amount must be > 0")
    cap = NO_KYC_LIMITS.get(fiat, NO_KYC_LIMITS["USD"])
    if amount > cap:
        raise HTTPException(400, f"amount exceeds no-KYC cap of {cap} {fiat}")
    crypto = (payload.get("crypto") or "USDT").upper()
    chain = (payload.get("chain") or "bsc").lower()
    if chain not in CHAINS:
        raise HTTPException(400, f"unsupported chain {chain}")

    import uuid
    pid = str(uuid.uuid4())
    now = _now()
    await db.execute(
        """INSERT INTO payments
           (id, merchant_id, amount, fiat_currency, crypto_currency, provider,
            wallet_address, customer_email, status, chain, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (pid, None, amount, fiat, crypto, "onramp", wallet_address,
         email, "onramp_pending", chain, now, now),
    )
    onramps = _onramp_urls(amount, fiat, crypto, chain, wallet_address, pid, email)
    return {
        "payment_id": pid,
        "amount": amount, "fiat": fiat, "crypto": crypto, "chain": chain,
        "wallet_address": wallet_address, "no_kyc_cap": cap,
        "onramps": onramps,
    }

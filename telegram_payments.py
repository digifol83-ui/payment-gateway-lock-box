"""Telegram Payments and non-Stripe gateway readiness checks."""
from __future__ import annotations

import asyncio
import secrets
import uuid
from datetime import datetime
from typing import Any

import httpx

import config
from providers import _is_production
from wallet_chains import CHAINS


TELEGRAM_API = "https://api.telegram.org"
INVOICE_PAYLOAD_PREFIX = "beastpay:"
TELEGRAM_API_ATTEMPTS = 3
TELEGRAM_TIMEOUT = httpx.Timeout(20.0, connect=10.0)


def _clean(value: str | None) -> str:
    return (value or "").strip()


def _is_set(value: str | None) -> bool:
    value = _clean(value)
    return bool(value and not value.startswith(("YOUR_", "REPLACE", "placeholder", "test_")))


def telegram_webhook_secret_valid(configured_secret: str | None, header_secret: str | None) -> bool:
    configured = _clean(configured_secret)
    if not configured:
        return True
    header = _clean(header_secret)
    return bool(header) and secrets.compare_digest(configured, header)


def _bot_token() -> str:
    return _clean(config.TELEGRAM_BOT_TOKEN)


def _payment_provider_token() -> str:
    return _clean(getattr(config, "TELEGRAM_PAYMENT_PROVIDER_TOKEN", "") or getattr(config, "STRIPE_PROVIDER_TOKEN", ""))


def _minor_units(amount: float, currency: str) -> int:
    currency = currency.upper()
    zero_decimal = {"BIF", "CLP", "DJF", "GNF", "JPY", "KMF", "KRW", "MGA", "PYG", "RWF", "UGX", "VND", "VUV", "XAF", "XOF", "XPF", "XTR"}
    decimals = 0 if currency in zero_decimal else 2
    return int(round(float(amount) * (10**decimals)))


def _result(
    provider_id: str,
    provider_type: str,
    *,
    configured: bool,
    ready: bool,
    status: str,
    detail: str,
    evidence: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "provider_id": provider_id,
        "provider_type": provider_type,
        "configured": configured,
        "ready_for_real_payment": ready,
        "status": status,
        "detail": detail,
        "evidence": evidence or {},
    }


async def _telegram_request(method: str, *, verb: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    token = _bot_token()
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not configured")

    url = f"{TELEGRAM_API}/bot{token}/{method}"
    resp = None
    for attempt in range(TELEGRAM_API_ATTEMPTS):
        try:
            async with httpx.AsyncClient(timeout=TELEGRAM_TIMEOUT) as client:
                if verb == "POST":
                    resp = await client.post(url, json=payload or {})
                else:
                    resp = await client.get(url)
            break
        except httpx.HTTPError as exc:
            if attempt == TELEGRAM_API_ATTEMPTS - 1:
                raise RuntimeError(str(exc).strip() or exc.__class__.__name__) from exc
            await asyncio.sleep(0.35 * (attempt + 1))

    if resp is None:
        raise RuntimeError("Telegram API request did not return a response")

    try:
        body = resp.json()
    except Exception:
        body = {"ok": False, "description": resp.text}
    if resp.status_code >= 400 or not body.get("ok"):
        raise RuntimeError(body.get("description") or f"Telegram API error {resp.status_code}")
    return body


async def _telegram_post(method: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    return await _telegram_request(method, verb="POST", payload=payload)


async def _telegram_get(method: str) -> dict[str, Any]:
    return await _telegram_request(method, verb="GET")


async def create_invoice_link(
    *,
    title: str,
    description: str,
    payload: str,
    amount: float,
    currency: str = "XTR",
    provider_token: str | None = None,
) -> str:
    """Create a Telegram invoice link without charging the customer."""
    currency = currency.upper()
    body: dict[str, Any] = {
        "title": title[:32],
        "description": description[:255],
        "payload": payload[:128],
        "currency": currency,
        "prices": [{"label": title[:32], "amount": _minor_units(amount, currency)}],
    }
    token = _clean(provider_token)
    if currency == "XTR":
        body["provider_token"] = token
    elif token or currency != "XTR":
        body["provider_token"] = token or _payment_provider_token()
    response = await _telegram_post("createInvoiceLink", body)
    return str(response["result"])


async def telegram_gateway_status(*, probe_invoice: bool = True) -> dict[str, Any]:
    bot_configured = _is_set(_bot_token())
    chat_configured = _is_set(config.TELEGRAM_CHAT_ID)
    provider_token_configured = _is_set(_payment_provider_token())
    evidence: dict[str, Any] = {
        "enabled": bool(config.TELEGRAM_ENABLED),
        "bot_token_present": bot_configured,
        "chat_id_present": chat_configured,
        "webhook_secret_present": _is_set(getattr(config, "TELEGRAM_WEBHOOK_SECRET", "")),
        "provider_token_present": provider_token_configured,
        "legacy_provider_token_supported": bool(getattr(config, "STRIPE_PROVIDER_TOKEN", "")),
    }

    if not bot_configured:
        return _result(
            "telegram",
            "telegram-payments",
            configured=False,
            ready=False,
            status="bot_not_configured",
            detail="Telegram bot token is not configured in this runtime.",
            evidence=evidence,
        )

    try:
        me = await _telegram_get("getMe")
        bot = me.get("result") or {}
        evidence["bot_username"] = bot.get("username")
    except Exception as exc:
        return _result(
            "telegram",
            "telegram-payments",
            configured=True,
            ready=False,
            status="bot_api_error",
            detail=f"Telegram getMe failed: {str(exc).strip() or exc.__class__.__name__}",
            evidence=evidence,
        )

    try:
        webhook = await _telegram_get("getWebhookInfo")
        info = webhook.get("result") or {}
        evidence["webhook_url_configured"] = bool(info.get("url"))
        evidence["pending_update_count"] = info.get("pending_update_count", 0)
        if info.get("last_error_message"):
            evidence["last_error_message"] = info.get("last_error_message")
    except Exception as exc:
        evidence["webhook_check_error"] = str(exc).strip() or exc.__class__.__name__

    invoice_modes: list[str] = []
    invoice_errors: list[str] = []
    if not probe_invoice:
        evidence["invoice_modes_verified"] = invoice_modes
        return _result(
            "telegram",
            "telegram-payments",
            configured=True,
            ready=False,
            status="bot_reachable",
            detail="Telegram bot is reachable; invoice probe was not requested.",
            evidence=evidence,
        )

    if probe_invoice:
        try:
            await create_invoice_link(
                title="BeastPay Stars",
                description="Telegram Stars readiness check",
                payload=f"{INVOICE_PAYLOAD_PREFIX}status:{uuid.uuid4()}",
                amount=1,
                currency="XTR",
            )
            invoice_modes.append("telegram_stars")
        except Exception as exc:
            invoice_errors.append(f"stars:{str(exc).strip() or exc.__class__.__name__}")

        if provider_token_configured:
            try:
                await create_invoice_link(
                    title="BeastPay Gateway",
                    description="Telegram payment provider readiness check",
                    payload=f"{INVOICE_PAYLOAD_PREFIX}status:{uuid.uuid4()}",
                    amount=1.0,
                    currency="USD",
                )
                invoice_modes.append("provider_token")
            except Exception as exc:
                invoice_errors.append(f"provider_token:{str(exc).strip() or exc.__class__.__name__}")

    evidence["invoice_modes_verified"] = invoice_modes
    if invoice_errors:
        evidence["invoice_errors"] = invoice_errors

    ready = bool(invoice_modes)
    status = "ready" if ready else "invoice_probe_failed"
    detail = (
        "Telegram bot is reachable and can create invoice links."
        if ready
        else "Telegram bot is reachable, but invoice link creation is not verified."
    )
    if ready and not provider_token_configured:
        detail += " Telegram Stars is available; no BotFather fiat provider token is configured."

    return _result(
        "telegram",
        "telegram-payments",
        configured=True,
        ready=ready,
        status=status,
        detail=detail,
        evidence=evidence,
    )


async def non_stripe_gateway_status() -> dict[str, Any]:
    checks = [
        await telegram_gateway_status(probe_invoice=True),
        await _direct_wallet_status(),
        await _nowpayments_status(),
        await _coinremitter_status(),
        _guardarian_status(),
        _plisio_status(),
    ]
    ready = [row["provider_id"] for row in checks if row["ready_for_real_payment"]]
    return {
        "checked_at": datetime.utcnow().isoformat(),
        "scope": "telegram_and_non_stripe_non_transak",
        "excluded": ["stripe", "transak"],
        "ready_for_real_payment": bool(ready),
        "ready_providers": ready,
        "blockers": [
            {"provider_id": row["provider_id"], "status": row["status"], "detail": row["detail"]}
            for row in checks
            if not row["ready_for_real_payment"]
        ],
        "checks": checks,
    }


async def _direct_wallet_status() -> dict[str, Any]:
    chains = {
        key: {
            "chain_id": cfg["chain_id"],
            "native": cfg["native"],
            "tokens": list(cfg["tokens"].keys()),
            "merchant_wallet_present": _is_set(cfg.get("merchant_wallet")),
        }
        for key, cfg in CHAINS.items()
    }
    ready = bool(chains and all(row["merchant_wallet_present"] for row in chains.values()))
    return _result(
        "direct_wallet",
        "crypto-direct",
        configured=ready,
        ready=ready,
        status="ready" if ready else "merchant_wallet_missing",
        detail=(
            "MetaMask and Trust Wallet direct crypto payment routes are available with on-chain verification."
            if ready
            else "One or more direct-wallet merchant addresses are missing."
        ),
        evidence={"chains": chains},
    )


async def _nowpayments_status() -> dict[str, Any]:
    configured = _is_production("nowpayments")
    if not configured:
        return _result(
            "nowpayments",
            "crypto-invoice",
            configured=False,
            ready=False,
            status="not_configured",
            detail="NOWPayments production API key is not configured in this runtime.",
        )
    try:
        from providers.nowpayments import NowPaymentsProvider

        currencies = await NowPaymentsProvider().get_currencies()
    except Exception as exc:
        return _result(
            "nowpayments",
            "crypto-invoice",
            configured=True,
            ready=False,
            status="api_error",
            detail=f"NOWPayments API probe failed: {str(exc).strip() or exc.__class__.__name__}",
        )
    return _result(
        "nowpayments",
        "crypto-invoice",
        configured=True,
        ready=True,
        status="ready",
        detail="NOWPayments production API responded to the currencies probe.",
        evidence={"currency_count": len(currencies)},
    )


async def _coinremitter_status() -> dict[str, Any]:
    configured = _is_production("coinremitter")
    if not configured:
        return _result(
            "coinremitter",
            "crypto-invoice",
            configured=False,
            ready=False,
            status="not_configured",
            detail="CoinRemitter API key/password are not configured in this runtime.",
        )
    try:
        from providers.coinremitter import CoinRemitterProvider

        balance = await CoinRemitterProvider().get_balance()
    except Exception as exc:
        return _result(
            "coinremitter",
            "crypto-invoice",
            configured=True,
            ready=False,
            status="api_error",
            detail=f"CoinRemitter balance probe failed: {str(exc).strip() or exc.__class__.__name__}",
        )
    return _result(
        "coinremitter",
        "crypto-invoice",
        configured=True,
        ready=True,
        status="ready",
        detail="CoinRemitter API responded to the wallet balance probe.",
        evidence={"response_flag": balance.get("flag") if isinstance(balance, dict) else None},
    )


def _guardarian_status() -> dict[str, Any]:
    configured = _is_production("guardarian")
    return _result(
        "guardarian",
        "fiat-to-crypto",
        configured=configured,
        ready=False,
        status="configured_no_safe_probe" if configured else "not_configured",
        detail=(
            "Guardarian credentials are configured, but readiness is not marked true until a safe quote/status probe is added."
            if configured
            else "Guardarian production API key is not configured in this runtime."
        ),
    )


def _plisio_status() -> dict[str, Any]:
    configured = _is_production("plisio")
    return _result(
        "plisio",
        "crypto-invoice",
        configured=configured,
        ready=False,
        status="adapter_not_implemented" if configured else "not_configured",
        detail=(
            "Plisio credentials are present, but the local provider adapter is still a stub."
            if configured
            else "Plisio API key is not configured in this runtime."
        ),
    )


async def handle_telegram_payment_update(update: dict[str, Any], db) -> dict[str, Any]:
    """Handle Telegram payment webhook updates: pre-checkout and successful payment."""
    pre_checkout = update.get("pre_checkout_query")
    if pre_checkout:
        query_id = pre_checkout.get("id")
        payload = pre_checkout.get("invoice_payload") or ""
        ok = payload.startswith(INVOICE_PAYLOAD_PREFIX)
        await _telegram_post(
            "answerPreCheckoutQuery",
            {
                "pre_checkout_query_id": query_id,
                "ok": ok,
                **({} if ok else {"error_message": "Unknown BeastPay invoice payload."}),
            },
        )
        return {"handled": True, "type": "pre_checkout_query", "accepted": ok}

    message = update.get("message") or update.get("edited_message") or {}
    successful = message.get("successful_payment")
    if not successful:
        return {"handled": False}

    invoice_payload = successful.get("invoice_payload") or ""
    payment_id = invoice_payload.removeprefix(INVOICE_PAYLOAD_PREFIX).split(":", 1)[0]
    if payment_id and payment_id != "status":
        await db.execute(
            "UPDATE payments SET status=?, provider_order_id=?, provider_tx_id=?, updated_at=? WHERE id=?",
            (
                "completed",
                successful.get("telegram_payment_charge_id"),
                successful.get("provider_payment_charge_id"),
                datetime.utcnow().isoformat(),
                payment_id,
            ),
        )
    return {
        "handled": True,
        "type": "successful_payment",
        "payment_id": payment_id or None,
        "currency": successful.get("currency"),
        "total_amount": successful.get("total_amount"),
    }

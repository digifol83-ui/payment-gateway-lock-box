"""Real payment readiness checks for provider-hosted checkout flows."""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any

import aiohttp

from config import MOONPAY_API_KEY, MOONPAY_ENV, STRIPE_SECRET_KEY
from providers import _is_production


STRIPE_API_BASE = "https://api.stripe.com/v1"
STRIPE_API_VERSION = "2026-02-25.clover"
TEST_WALLET_ADDRESS = "0x742d35Cc6634C0532925a3b844Bc454e4438f44e"


def _provider_result(
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
        "detail": _redact(str(detail)),
        "evidence": _redact_obj(evidence or {}),
    }


def _redact(value: str) -> str:
    value = re.sub(r"(sk|pk|rk)_(live|test)_[^,'\"\s}]+", r"\1_\2_REDACTED", value)
    value = re.sub(r"whsec_[^,'\"\s}]+", "whsec_REDACTED", value)
    value = re.sub(r"access-token['\"]?\s*[:=]\s*['\"]?[^,'\"\s}]+", "access-token=REDACTED", value, flags=re.I)
    value = re.sub(r"api-secret['\"]?\s*[:=]\s*['\"]?[^,'\"\s}]+", "api-secret=REDACTED", value, flags=re.I)
    value = re.sub(r"(apiKey=)[^&\s]+", r"\1REDACTED", value)
    value = re.sub(r"(sessionId=)[^&\s]+", r"\1REDACTED", value)
    return value


def _redact_obj(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _redact_obj(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_redact_obj(v) for v in value]
    if isinstance(value, str):
        return _redact(value)
    return value


def _stripe_error(body: dict[str, Any]) -> str:
    error = body.get("error")
    if isinstance(error, dict):
        return str(error.get("message") or error.get("code") or error)
    return str(body)


def _exception_detail(exc: Exception) -> str:
    text = str(exc).strip()
    return text or exc.__class__.__name__


async def check_stripe_real_payment() -> dict[str, Any]:
    configured = bool(STRIPE_SECRET_KEY and STRIPE_SECRET_KEY.startswith("sk_live_"))
    if not configured:
        return _provider_result(
            "stripe",
            "fiat-only",
            configured=False,
            ready=False,
            status="not_configured",
            detail="Stripe live secret key is not configured in this runtime.",
        )

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{STRIPE_API_BASE}/account",
                auth=aiohttp.BasicAuth(STRIPE_SECRET_KEY, ""),
                headers={"Stripe-Version": STRIPE_API_VERSION},
                timeout=15,
            ) as resp:
                try:
                    body = await resp.json()
                except Exception:
                    body = {"message": await resp.text()}
                if resp.status >= 400:
                    return _provider_result(
                        "stripe",
                        "fiat-only",
                        configured=True,
                        ready=False,
                        status="api_error",
                        detail=f"Stripe account API returned HTTP {resp.status}: {_stripe_error(body)}",
                        evidence={"http_status": resp.status},
                    )
    except Exception as exc:
        detail = _exception_detail(exc)
        return _provider_result(
            "stripe",
            "fiat-only",
            configured=True,
            ready=False,
            status="api_unreachable",
            detail=f"Could not reach Stripe account API: {detail}",
        )

    capabilities = body.get("capabilities") or {}
    requirements = body.get("requirements") or {}
    charges_enabled = bool(body.get("charges_enabled"))
    payouts_enabled = bool(body.get("payouts_enabled"))
    card_payments = capabilities.get("card_payments")
    transfers = capabilities.get("transfers")
    ready = bool(charges_enabled and card_payments == "active")
    status = "ready" if ready else "provider_review_pending"
    detail = (
        "Stripe charges and card payments are active."
        if ready
        else "Stripe live key works, but account capabilities are not ready for real card payments."
    )
    return _provider_result(
        "stripe",
        "fiat-only",
        configured=True,
        ready=ready,
        status=status,
        detail=detail,
        evidence={
            "account_id": body.get("id"),
            "country": body.get("country"),
            "charges_enabled": charges_enabled,
            "payouts_enabled": payouts_enabled,
            "card_payments": card_payments,
            "transfers": transfers,
            "currently_due_count": len(requirements.get("currently_due") or []),
        },
    )


async def check_transak_real_payment() -> dict[str, Any]:
    configured = _is_production("transak")
    if not configured:
        return _provider_result(
            "transak",
            "fiat-to-crypto",
            configured=False,
            ready=False,
            status="not_configured",
            detail="Transak production API key plus access token or refresh secret are not configured in this runtime.",
        )

    from providers.transak import TransakProvider

    payment = {
        "id": "real_status_probe",
        "amount": 50.0,
        "fiat_amount": 50.0,
        "fiat_currency": "USD",
        "crypto_currency": "USDT",
        "wallet_address": TEST_WALLET_ADDRESS,
        "customer_email": "status-check@example.invalid",
        "description": "BeastPay real payment readiness probe",
    }
    try:
        redirect_url = await TransakProvider().create_widget_url(payment)
    except Exception as exc:
        message = _exception_detail(exc)
        status = "provider_access_rejected" if "1002" in message or "Invalid or missing access-token" in message else "checkout_error"
        detail = (
            "Transak credentials can be loaded, but Create Widget URL is rejected by Transak partner access."
            if status == "provider_access_rejected"
            else f"Transak checkout probe failed: {message}"
        )
        return _provider_result(
            "transak",
            "fiat-to-crypto",
            configured=True,
            ready=False,
            status=status,
            detail=detail,
            evidence={"error": message},
        )

    return _provider_result(
        "transak",
        "fiat-to-crypto",
        configured=True,
        ready=True,
        status="ready",
        detail="Transak returned a provider-hosted checkout session URL.",
        evidence={"redirect_url_created": bool(redirect_url), "has_session_id": "sessionId=" in redirect_url},
    )


async def check_moonpay_real_payment() -> dict[str, Any]:
    configured = _is_production("moonpay")
    if not configured:
        return _provider_result(
            "moonpay",
            "fiat-to-crypto",
            configured=False,
            ready=False,
            status="not_configured",
            detail="MoonPay production credentials are not configured in this runtime.",
            evidence={"env": MOONPAY_ENV or "unset", "api_key_present": bool(MOONPAY_API_KEY)},
        )

    from providers.moonpay import MoonPayProvider

    payment = {
        "id": "real_status_probe",
        "amount": 50.0,
        "fiat_currency": "USD",
        "crypto_currency": "USDT",
        "wallet_address": TEST_WALLET_ADDRESS,
        "customer_email": "status-check@example.invalid",
    }
    try:
        redirect_url = MoonPayProvider().build_widget_url(payment)
    except Exception as exc:
        return _provider_result(
            "moonpay",
            "fiat-to-crypto",
            configured=True,
            ready=False,
            status="checkout_error",
            detail=f"MoonPay checkout URL generation failed: {exc}",
        )

    return _provider_result(
        "moonpay",
        "fiat-to-crypto",
        configured=True,
        ready=True,
        status="checkout_url_builds",
        detail="MoonPay production checkout URL can be generated locally; dashboard approval still needs provider-side confirmation.",
        evidence={"redirect_url_created": bool(redirect_url)},
    )


async def check_plisio_real_payment() -> dict[str, Any]:
    configured = _is_production("plisio")
    if not configured:
        return _provider_result(
            "plisio",
            "crypto-only",
            configured=False,
            ready=False,
            status="not_configured",
            detail="Plisio production API key is not configured in this runtime.",
        )

    import secrets
    from providers.plisio import PlisioProvider

    try:
        invoice = await PlisioProvider().create_invoice({
            "id": f"real_status_probe_{secrets.token_hex(6)}",
            "amount": 5.0,
            "fiat_currency": "USD",
            "crypto_currency": "USDT",
            "customer_email": "status-check@example.invalid",
            "description": "BeastPay real payment readiness probe",
        })
    except Exception as exc:
        message = _exception_detail(exc)
        return _provider_result(
            "plisio",
            "crypto-only",
            configured=True,
            ready=False,
            status="api_error",
            detail=f"Plisio invoice creation failed: {message}",
            evidence={"error": message},
        )

    if invoice.get("flag") == 1:
        data = invoice.get("data", {})
        return _provider_result(
            "plisio",
            "crypto-only",
            configured=True,
            ready=True,
            status="ready",
            detail="Plisio returned a real crypto invoice.",
            evidence={
                "txn_id": data.get("txn_id"),
                "invoice_url": data.get("invoice_url"),
            },
        )

    return _provider_result(
        "plisio",
        "crypto-only",
        configured=True,
        ready=False,
        status="invoice_failed",
        detail="Plisio responded but invoice flag != 1",
        evidence=invoice,
    )


async def real_payment_status() -> dict[str, Any]:
    checks = [
        await check_stripe_real_payment(),
        await check_transak_real_payment(),
        await check_moonpay_real_payment(),
        await check_plisio_real_payment(),
    ]
    ready = [row["provider_id"] for row in checks if row["ready_for_real_payment"]]
    blockers = [
        {
            "provider_id": row["provider_id"],
            "status": row["status"],
            "detail": row["detail"],
        }
        for row in checks
        if not row["ready_for_real_payment"]
    ]
    return {
        "checked_at": datetime.utcnow().isoformat(),
        "ready_for_real_payment": bool(ready),
        "ready_providers": ready,
        "blockers": blockers,
        "checks": checks,
    }

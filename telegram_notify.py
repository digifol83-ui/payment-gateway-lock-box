import logging
from datetime import datetime
from typing import Any, Dict, Optional

import httpx

from config import BASE_URL, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, TELEGRAM_ENABLED, settings

logger = logging.getLogger(__name__)


def _enabled() -> bool:
    if not TELEGRAM_ENABLED:
        return False
    if not (TELEGRAM_BOT_TOKEN or "").strip():
        return False
    if not (TELEGRAM_CHAT_ID or "").strip():
        return False
    return True


async def send_message(
    text: str,
    chat_id: Optional[str] = None,
    *,
    parse_mode: str = "HTML",
    disable_web_page_preview: bool = True,
) -> bool:
    if not _enabled():
        return False

    target_chat_id = (chat_id or TELEGRAM_CHAT_ID).strip()
    api = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

    payload = {
        "chat_id": target_chat_id,
        "text": text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": disable_web_page_preview,
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(f"{api}/sendMessage", json=payload)
            resp.raise_for_status()
            data = resp.json()
            return bool(data.get("ok"))
    except Exception as e:
        logger.warning("Telegram sendMessage failed: %s", e)
        return False


def _fmt_money(amount: Any, currency: str) -> str:
    try:
        return f"{float(amount):,.2f} {currency}"
    except Exception:
        return f"{amount} {currency}"


async def notify_new_payment(payment: Dict[str, Any]) -> bool:
    if not _enabled() or not getattr(settings, "TG_NOTIFY_NEW_PAYMENT", True):
        return False

    pid = payment.get("id") or payment.get("payment_id") or "<unknown>"
    amount = payment.get("amount")
    fiat = payment.get("fiat_currency") or ""
    crypto = payment.get("crypto_currency") or ""
    provider = payment.get("provider") or payment.get("provider_id") or "auto"
    status = payment.get("status") or "pending"
    email = payment.get("customer_email") or ""

    link = f"{BASE_URL.rstrip('/')}/admin/payments/{pid}"
    msg = (
        "🆕 <b>New payment</b>\n"
        f"ID: <code>{pid}</code>\n"
        f"Amount: <b>{_fmt_money(amount, fiat)}</b>\n"
        f"Crypto: <b>{crypto}</b>\n"
        f"Provider: <b>{provider}</b>\n"
        f"Status: <b>{status}</b>\n"
        + (f"Email: <code>{email}</code>\n" if email else "")
        + f"Time: <i>{datetime.utcnow().isoformat()}Z</i>\n"
        + f"Link: {link}"
    )
    return await send_message(msg)


async def notify_payment_update(
    payment: Dict[str, Any],
    new_status: str,
    *,
    extra: Optional[Dict[str, Any]] = None,
) -> bool:
    if not _enabled():
        return False

    status_lower = (new_status or "").strip().lower()
    if status_lower in {"completed", "succeeded", "success", "paid"}:
        if not getattr(settings, "TG_NOTIFY_COMPLETED", True):
            return False
    elif status_lower in {"failed", "canceled", "cancelled", "expired"}:
        if not getattr(settings, "TG_NOTIFY_FAILED", True):
            return False

    pid = payment.get("id") or payment.get("payment_id") or "<unknown>"
    amount = payment.get("amount")
    fiat = payment.get("fiat_currency") or ""
    crypto = payment.get("crypto_currency") or ""
    provider = payment.get("provider") or payment.get("provider_id") or "auto"
    email = payment.get("customer_email") or ""

    link = f"{BASE_URL.rstrip('/')}/admin/payments/{pid}"
    lines = [
        "🔔 <b>Payment update</b>",
        f"ID: <code>{pid}</code>",
        f"New status: <b>{new_status}</b>",
        f"Amount: <b>{_fmt_money(amount, fiat)}</b>",
        f"Crypto: <b>{crypto}</b>",
        f"Provider: <b>{provider}</b>",
    ]
    if email:
        lines.append(f"Email: <code>{email}</code>")
    if extra:
        for k, v in extra.items():
            if v is None:
                continue
            lines.append(f"{k}: <code>{v}</code>")
    lines.append(f"Time: <i>{datetime.utcnow().isoformat()}Z</i>")
    lines.append(f"Link: {link}")

    return await send_message("\n".join(lines))


async def notify_test() -> bool:
    if not _enabled():
        return False

    api = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{api}/getMe")
            resp.raise_for_status()
            data = resp.json()
            if not data.get("ok"):
                return False
    except Exception as e:
        logger.warning("Telegram getMe failed: %s", e)
        return False

    return await send_message("✅ Telegram notifications are configured and reachable.")


"""OTP delivery: SMTP first, Telegram fallback, always log."""
import asyncio
import logging
import smtplib
import ssl
from email.message import EmailMessage
from typing import Optional

from config import settings

logger = logging.getLogger(__name__)


def _smtp_configured() -> bool:
    return bool(
        getattr(settings, "SMTP_HOST", "")
        and getattr(settings, "SMTP_USERNAME", "")
        and getattr(settings, "SMTP_PASSWORD", "")
    )


def _send_smtp_sync(to_addr: str, subject: str, body: str) -> bool:
    host = settings.SMTP_HOST
    port = int(getattr(settings, "SMTP_PORT", 587) or 587)
    user = settings.SMTP_USERNAME
    pwd = settings.SMTP_PASSWORD
    from_addr = getattr(settings, "SMTP_FROM", user) or user

    msg = EmailMessage()
    msg["From"] = from_addr
    msg["To"] = to_addr
    msg["Subject"] = subject
    msg.set_content(body)

    context = ssl.create_default_context()
    try:
        if port == 465:
            with smtplib.SMTP_SSL(host, port, context=context, timeout=15) as s:
                s.login(user, pwd)
                s.send_message(msg)
        else:
            with smtplib.SMTP(host, port, timeout=15) as s:
                s.ehlo()
                s.starttls(context=context)
                s.ehlo()
                s.login(user, pwd)
                s.send_message(msg)
        return True
    except Exception as e:
        logger.warning("SMTP send to %s failed: %s", to_addr, e)
        return False


async def deliver_otp(to_email: str, code: str, purpose: str) -> dict:
    """Deliver OTP via SMTP (preferred) and/or Telegram. Always logs.

    Returns {"smtp": bool, "telegram": bool, "logged": True}.
    """
    subject = f"BeastPay OTP — {purpose}"
    body = (
        f"Your one-time code: {code}\n\n"
        f"Purpose: {purpose}\n"
        f"This code expires in 10 minutes. Do not share it.\n"
    )

    result = {"smtp": False, "telegram": False, "logged": True}

    if _smtp_configured():
        try:
            ok = await asyncio.get_event_loop().run_in_executor(
                None, _send_smtp_sync, to_email, subject, body
            )
            result["smtp"] = bool(ok)
        except Exception as e:
            logger.warning("OTP SMTP delivery error: %s", e)

    # Telegram fallback / dual channel for admin visibility
    try:
        from telegram_notify import send_message  # local import to avoid cycles
        tg_text = (
            f"<b>BeastPay OTP</b>\n"
            f"To: <code>{to_email}</code>\n"
            f"Purpose: {purpose}\n"
            f"Code: <code>{code}</code>"
        )
        result["telegram"] = await send_message(tg_text)
    except Exception as e:
        logger.warning("OTP telegram delivery error: %s", e)

    # Always log (last resort) — only at INFO so it lands in server logs but not stdout-spammed
    logger.info("OTP[%s] for %s: %s (smtp=%s tg=%s)",
                purpose, to_email, code, result["smtp"], result["telegram"])
    return result

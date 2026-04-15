"""
OTP / verification email monitor.
Ported from emailVerification.ts.
Polls an email inbox for gateway verification emails and auto-extracts OTP codes.
Supports: IMAP (generic), Gmail API (if configured).
"""
import asyncio
import imaplib
import email as email_lib
from email.header import decode_header
from datetime import datetime
from typing import Optional

from .gateway_registration import extract_otp_from_email, validate_otp_format
from config import (
    IMAP_HOST, IMAP_PORT, IMAP_USER, IMAP_PASSWORD, IMAP_ENABLED,
)


def _decode_header_value(value: str) -> str:
    parts = decode_header(value)
    decoded = []
    for part, encoding in parts:
        if isinstance(part, bytes):
            decoded.append(part.decode(encoding or "utf-8", errors="replace"))
        else:
            decoded.append(part)
    return " ".join(decoded)


def _fetch_recent_emails(
    mailbox: str = "INBOX",
    limit: int = 10,
) -> list[dict]:
    """Connect via IMAP and return the most recent emails as dicts."""
    if not IMAP_ENABLED:
        return []

    try:
        mail = imaplib.IMAP4_SSL(IMAP_HOST, IMAP_PORT)
        mail.login(IMAP_USER, IMAP_PASSWORD)
        mail.select(mailbox)

        _, data = mail.search(None, "ALL")
        ids = data[0].split()
        # Fetch last `limit` emails
        recent_ids = ids[-limit:] if len(ids) > limit else ids

        messages = []
        for uid in reversed(recent_ids):
            _, msg_data = mail.fetch(uid, "(RFC822)")
            raw = msg_data[0][1]
            msg = email_lib.message_from_bytes(raw)

            subject = _decode_header_value(msg.get("Subject", ""))
            from_addr = _decode_header_value(msg.get("From", ""))
            date_str = msg.get("Date", "")

            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        body += part.get_payload(decode=True).decode(errors="replace")
            else:
                body = msg.get_payload(decode=True).decode(errors="replace")

            messages.append({
                "from":    from_addr,
                "subject": subject,
                "body":    body,
                "date":    date_str,
            })

        mail.logout()
        return messages

    except Exception as e:
        print(f"[email_monitor] IMAP fetch error: {e}")
        return []


# Gateway sender domains for filtering
GATEWAY_SENDERS = {
    "moonpay":      ["moonpay.com"],
    "transak":      ["transak.com"],
    "simplex":      ["simplex.com"],
    "ramp_network": ["ramp.network"],
}


def _is_from_gateway(from_addr: str, gateway_name: str) -> bool:
    domains = GATEWAY_SENDERS.get(gateway_name, [])
    return any(d in from_addr.lower() for d in domains)


async def monitor_inbox_for_otp(
    merchant_email: str,
    gateway_name: str,
    timeout_seconds: int = 300,
    poll_interval: int = 10,
) -> Optional[str]:
    """
    Poll IMAP inbox for a verification email from the specified gateway.
    Returns the extracted OTP or None on timeout.
    """
    if not IMAP_ENABLED:
        print(f"[email_monitor] IMAP not configured — manual OTP entry required")
        return None

    print(f"[email_monitor] Watching inbox for {gateway_name} OTP (timeout {timeout_seconds}s)")
    start = asyncio.get_event_loop().time()

    while (asyncio.get_event_loop().time() - start) < timeout_seconds:
        emails = await asyncio.get_event_loop().run_in_executor(
            None, _fetch_recent_emails, "INBOX", 20
        )
        for msg in emails:
            if not _is_from_gateway(msg["from"], gateway_name):
                continue
            otp = extract_otp_from_email(msg["body"])
            if otp and validate_otp_format(otp):
                print(f"[email_monitor] OTP found for {gateway_name}: {otp}")
                return otp

        await asyncio.sleep(poll_interval)

    print(f"[email_monitor] Timeout waiting for {gateway_name} OTP")
    return None


def is_configured() -> dict:
    return {
        "enabled":   IMAP_ENABLED,
        "host":      IMAP_HOST or "NOT SET",
        "user":      IMAP_USER or "NOT SET",
        "port":      IMAP_PORT,
    }

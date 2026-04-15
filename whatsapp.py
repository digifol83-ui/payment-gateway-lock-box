"""
WhatsApp Cloud API notification module for BeastPay-OpenClaw.

Setup:
  1. Go to developers.facebook.com → My Apps → Create App → Business
  2. Add WhatsApp product → API Setup
  3. Copy Phone Number ID and generate a permanent access token
  4. Add your recipient number (must be verified in test mode)
  5. Set env vars:
       WHATSAPP_TOKEN=your_permanent_token
       WHATSAPP_PHONE_ID=123456789012345
       WHATSAPP_TO=911234567890        ← no + prefix, country code first

Docs: https://developers.facebook.com/docs/whatsapp/cloud-api
"""
import httpx
from datetime import datetime
from config import (
    WHATSAPP_TOKEN, WHATSAPP_PHONE_ID, WHATSAPP_TO, WHATSAPP_ENABLED,
    WA_NOTIFY_NEW_PAYMENT, WA_NOTIFY_COMPLETED, WA_NOTIFY_FAILED,
    WA_NOTIFY_NEW_LINK, BASE_URL,
)

_API_URL = "https://graph.facebook.com/v19.0/{phone_id}/messages"


async def send_message(text: str) -> bool:
    """Send a plain text WhatsApp message."""
    if not WHATSAPP_ENABLED:
        return False
    url = _API_URL.format(phone_id=WHATSAPP_PHONE_ID)
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": WHATSAPP_TO,
        "type": "text",
        "text": {"preview_url": False, "body": text},
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code != 200:
                print(f"[whatsapp] Send failed {resp.status_code}: {resp.text[:200]}")
                return False
        return True
    except Exception as e:
        print(f"[whatsapp] Error: {e}")
        return False


# ─── Notification builders ────────────────────────────────────────────────────

async def notify_new_payment(payment: dict):
    if not WA_NOTIFY_NEW_PAYMENT:
        return
    lines = [
        "💳 *New Payment Initiated*",
        f"Amount:   ${payment['amount']} {payment['fiat_currency']}",
        f"Crypto:   {payment['crypto_currency']}",
        f"Provider: {payment.get('provider','').capitalize()}",
        f"Customer: {payment.get('customer_email') or '—'}",
        f"ID:       {payment['id'][:16]}",
        f"Time:     {_now()}",
    ]
    await send_message("\n".join(lines))


async def notify_payment_update(payment: dict, new_status: str, extra: dict = None):
    if new_status == "completed" and not WA_NOTIFY_COMPLETED:
        return
    if new_status in ("failed", "cancelled") and not WA_NOTIFY_FAILED:
        return
    if new_status in ("pending", "processing"):
        return

    extra = extra or {}
    emoji = {"completed": "✅", "failed": "❌", "cancelled": "🚫", "refunded": "↩️"}.get(new_status, "ℹ️")
    lines = [
        f"{emoji} *Payment {new_status.upper()}*",
        f"Amount:   ${payment['amount']} {payment['fiat_currency']}",
        f"Crypto:   {payment['crypto_currency']}",
    ]
    if extra.get("crypto_amount"):
        lines.append(f"Received: {extra['crypto_amount']} {payment['crypto_currency']}")
    if extra.get("provider_tx_id"):
        lines.append(f"Tx Hash:  {str(extra['provider_tx_id'])[:24]}...")
    lines += [
        f"Customer: {payment.get('customer_email') or '—'}",
        f"ID:       {payment['id'][:16]}",
        f"Time:     {_now()}",
    ]
    await send_message("\n".join(lines))


async def notify_new_link(link: dict, payment_url: str):
    if not WA_NOTIFY_NEW_LINK:
        return
    amount_str = f"${link['amount']} {link['fiat_currency']}" if link.get("amount") else "Variable"
    lines = [
        "🔗 *New Payment Link Created*",
        f"Amount: {amount_str}",
        f"Crypto: {link.get('crypto_currency') or 'Customer choice'}",
        f"URL:    {payment_url}",
        f"Time:   {_now()}",
    ]
    await send_message("\n".join(lines))


async def notify_summary(stats: dict):
    lines = [
        f"📊 *BeastPay Daily Summary — {_today()}*",
        f"Total:      {stats['total_payments']}",
        f"Completed:  {stats['completed']}",
        f"Pending:    {stats['pending']}",
        f"Failed:     {stats['failed']}",
        f"Volume:     ${stats['total_volume_usd']:,.2f} USD",
        f"Conversion: {stats['conversion_rate']}%",
        f"Dashboard:  {BASE_URL}/admin",
    ]
    return await send_message("\n".join(lines))


async def notify_test() -> bool:
    return await send_message(
        f"🤖 *BeastPay WhatsApp Connected*\n"
        f"Notifications are live.\n"
        f"Time: {_now()}\n"
        f"Gateway: {BASE_URL}"
    )


def is_configured() -> dict:
    return {
        "enabled":            WHATSAPP_ENABLED,
        "phone_id":           f"{WHATSAPP_PHONE_ID[:6]}…" if WHATSAPP_PHONE_ID else "NOT SET",
        "to_number":          WHATSAPP_TO or "NOT SET",
        "notify_new_payment": WA_NOTIFY_NEW_PAYMENT,
        "notify_completed":   WA_NOTIFY_COMPLETED,
        "notify_failed":      WA_NOTIFY_FAILED,
        "notify_new_link":    WA_NOTIFY_NEW_LINK,
    }


def _now():
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

def _today():
    return datetime.utcnow().strftime("%Y-%m-%d")

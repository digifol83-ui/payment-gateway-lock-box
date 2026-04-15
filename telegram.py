"""
Telegram notification module for CryptoPay Gateway.

Setup:
  1. Message @BotFather → /newbot → copy the token
  2. Add bot to your group/channel → promote as admin (for channels)
  3. Get your CHAT_ID:
       - Personal: message @userinfobot
       - Group: add @RawDataBot, send a message, read the chat.id
       - Channel: use the @channel_username or numeric ID (prefix -100)
  4. Set env vars:
       TELEGRAM_BOT_TOKEN=123456:ABCdef...
       TELEGRAM_CHAT_ID=-100123456789
"""
import asyncio
import httpx
from datetime import datetime
from config import (
    TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, TELEGRAM_ENABLED,
    TG_NOTIFY_NEW_PAYMENT, TG_NOTIFY_COMPLETED,
    TG_NOTIFY_FAILED, TG_NOTIFY_NEW_LINK, TG_NOTIFY_DAILY_SUMMARY,
    BASE_URL,
)

_TG_API = "https://api.telegram.org/bot{token}/sendMessage"

# Emoji map for statuses
_STATUS_EMOJI = {
    "pending":    "⏳",
    "processing": "🔄",
    "completed":  "✅",
    "failed":     "❌",
    "cancelled":  "🚫",
    "refunded":   "↩️",
}

_PROVIDER_EMOJI = {
    "transak": "🟦",
    "moonpay": "🌙",
}


async def send_message(text: str, parse_mode: str = "HTML") -> bool:
    """Send a message to the configured Telegram chat. Returns True on success."""
    if not TELEGRAM_ENABLED:
        return False
    url = _TG_API.format(token=TELEGRAM_BOT_TOKEN)
    payload = {
        "chat_id":    TELEGRAM_CHAT_ID,
        "text":       text,
        "parse_mode": parse_mode,
        "disable_web_page_preview": True,
    }
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(url, json=payload)
            if resp.status_code != 200:
                print(f"[telegram] Send failed: {resp.text}")
                return False
        return True
    except Exception as e:
        print(f"[telegram] Error: {e}")
        return False


def send_sync(text: str) -> bool:
    """Synchronous wrapper — use only from sync contexts (PowerShell API endpoint)."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Schedule as fire-and-forget
            asyncio.ensure_future(send_message(text))
            return True
        return loop.run_until_complete(send_message(text))
    except RuntimeError:
        return asyncio.run(send_message(text))


# ─── Notification builders ────────────────────────────────────────────────────

async def notify_new_payment(payment: dict):
    """Fired when a customer initiates checkout (redirected to provider)."""
    if not TG_NOTIFY_NEW_PAYMENT:
        return
    emoji = _PROVIDER_EMOJI.get(payment.get("provider", ""), "💳")
    status_emoji = _STATUS_EMOJI.get(payment.get("status", "pending"), "⏳")
    text = (
        f"{emoji} <b>New Payment Initiated</b>\n\n"
        f"{status_emoji} Status:   <code>pending</code>\n"
        f"💵 Amount:   <b>${payment['amount']} {payment['fiat_currency']}</b>\n"
        f"🪙 Crypto:   <b>{payment['crypto_currency']}</b>\n"
        f"🏦 Provider: {payment.get('provider','').capitalize()}\n"
        f"📧 Customer: <code>{payment.get('customer_email') or '—'}</code>\n"
        f"🆔 ID:       <code>{payment['id'][:16]}</code>\n"
        f"🕐 Time:     {_now()}\n"
        f"\n<a href='{BASE_URL}/api/payments/{payment['id']}'>View Payment →</a>"
    )
    await send_message(text)


async def notify_payment_update(payment: dict, new_status: str, extra: dict = None):
    """Fired on every status change from provider webhook."""
    if new_status == "completed" and not TG_NOTIFY_COMPLETED:
        return
    if new_status in ("failed", "cancelled") and not TG_NOTIFY_FAILED:
        return
    if new_status in ("pending", "processing"):
        return  # skip intermediate states to reduce noise

    emoji = _STATUS_EMOJI.get(new_status, "ℹ️")
    extra = extra or {}

    lines = [
        f"{emoji} <b>Payment {new_status.upper()}</b>\n",
        f"💵 Amount:   <b>${payment['amount']} {payment['fiat_currency']}</b>",
        f"🪙 Crypto:   <b>{payment['crypto_currency']}</b>",
    ]
    if extra.get("crypto_amount"):
        lines.append(f"📦 Received: <b>{extra['crypto_amount']} {payment['crypto_currency']}</b>")
    if extra.get("exchange_rate"):
        lines.append(f"📈 Rate:     <code>{extra['exchange_rate']}</code>")
    if extra.get("provider_tx_id"):
        lines.append(f"🔗 Tx Hash:  <code>{extra['provider_tx_id'][:24]}…</code>")

    lines += [
        f"🏦 Provider: {payment.get('provider','').capitalize()}",
        f"📧 Customer: <code>{payment.get('customer_email') or '—'}</code>",
        f"🆔 ID:       <code>{payment['id'][:16]}</code>",
        f"🕐 Time:     {_now()}",
    ]

    if new_status == "completed":
        lines.insert(0, "")  # blank line after header
        lines.append(f"\n💰 Funds delivered to wallet ✓")

    await send_message("\n".join(lines))


async def notify_new_link(link: dict, payment_url: str):
    """Fired when a new payment link is created."""
    if not TG_NOTIFY_NEW_LINK:
        return
    amount_str = f"${link['amount']} {link['fiat_currency']}" if link.get("amount") else "Variable"
    crypto_str = link.get("crypto_currency") or "Customer's choice"
    reusable   = "♾️ Reusable" if link.get("is_reusable") else "1️⃣ One-time"
    text = (
        f"🔗 <b>New Payment Link Created</b>\n\n"
        f"💵 Amount:   <b>{amount_str}</b>\n"
        f"🪙 Crypto:   <b>{crypto_str}</b>\n"
        f"🔁 Type:     {reusable}\n"
        f"📝 Desc:     {link.get('description') or '—'}\n"
        f"🆔 Link ID:  <code>{link['id']}</code>\n"
        f"🕐 Created:  {_now()}\n"
        f"\n🌐 <a href='{payment_url}'>Open Payment Link →</a>"
    )
    await send_message(text)


async def notify_daily_summary(stats: dict):
    """Send a daily stats digest."""
    if not TG_NOTIFY_DAILY_SUMMARY:
        return
    conv = stats.get("conversion_rate", 0)
    bar_filled = int(conv / 10)
    bar = "█" * bar_filled + "░" * (10 - bar_filled)
    text = (
        f"📊 <b>Daily Gateway Summary</b> — {_today()}\n\n"
        f"💳 Total Payments:  <b>{stats['total_payments']}</b>\n"
        f"✅ Completed:       <b>{stats['completed']}</b>\n"
        f"⏳ Pending:         <b>{stats['pending']}</b>\n"
        f"❌ Failed:          <b>{stats['failed']}</b>\n"
        f"💰 Volume (USD):    <b>${stats['total_volume_usd']:,.2f}</b>\n"
        f"🔗 Active Links:    <b>{stats['active_links']}</b>\n\n"
        f"📈 Conversion Rate:\n"
        f"   [{bar}] {conv}%\n"
        f"\n<a href='{BASE_URL}/admin'>Open Admin Dashboard →</a>"
    )
    await send_message(text)


async def notify_test(chat_id_override: str = None) -> bool:
    """Send a test ping to verify bot connectivity."""
    text = (
        f"🤖 <b>CryptoPay Gateway — Bot Connected</b>\n\n"
        f"✓ Telegram notifications are active.\n"
        f"🕐 {_now()}\n"
        f"🌐 Gateway: <code>{BASE_URL}</code>"
    )
    if chat_id_override:
        # Temporarily override chat_id for this call
        url = _TG_API.format(token=TELEGRAM_BOT_TOKEN)
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(url, json={
                    "chat_id": chat_id_override,
                    "text": text,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": True,
                })
                return resp.status_code == 200
        except Exception:
            return False
    return await send_message(text)


# ─── Utilities ────────────────────────────────────────────────────────────────
def _now() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")

def _today() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d")

def is_configured() -> dict:
    return {
        "enabled":    TELEGRAM_ENABLED,
        "bot_token":  f"{TELEGRAM_BOT_TOKEN[:10]}…" if TELEGRAM_BOT_TOKEN else "NOT SET",
        "chat_id":    TELEGRAM_CHAT_ID or "NOT SET",
        "notify_new_payment":   TG_NOTIFY_NEW_PAYMENT,
        "notify_completed":     TG_NOTIFY_COMPLETED,
        "notify_failed":        TG_NOTIFY_FAILED,
        "notify_new_link":      TG_NOTIFY_NEW_LINK,
        "notify_daily_summary": TG_NOTIFY_DAILY_SUMMARY,
    }

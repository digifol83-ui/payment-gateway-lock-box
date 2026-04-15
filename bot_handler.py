"""
Telegram Bot Handler — receives incoming payment text, runs Lockbox parsing,
sends formatted results back to the user, and logs to the database.

Endpoint: POST /telegram/incoming  (receive updates from Telegram webhook)
"""
import re
import json
import httpx
from datetime import datetime

import database as db
import lockbox
from telegram import TELEGRAM_BOT_TOKEN, send_message

TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

# ─── Detect whether a message looks like payment data ─────────────────────────

_CARD_PATTERN = re.compile(r"\b(?:\d[ \-]?){15,18}\b")
_EXPIRY_PATTERN = re.compile(r"\b(0[1-9]|1[0-2])\s*[/\-]\s*(\d{2,4})\b")
_CVV_PATTERN = re.compile(r"\b(?:cvv|cvc|security code)[:\s]+(\d{3,4})\b", re.I)


def _looks_like_payment_data(text: str) -> bool:
    """Heuristic: has a card-number-like sequence AND expiry."""
    return bool(_CARD_PATTERN.search(text) and _EXPIRY_PATTERN.search(text))


# ─── Telegram send helpers ────────────────────────────────────────────────────

async def _reply(chat_id: int, text: str, parse_mode: str = "HTML"):
    async with httpx.AsyncClient(timeout=10) as client:
        await client.post(
            f"{TELEGRAM_API}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": parse_mode},
        )


# ─── Confidence bar helper ────────────────────────────────────────────────────

def _conf_bar(score: float) -> str:
    filled = round(score * 10)
    bar = "█" * filled + "░" * (10 - filled)
    return f"[{bar}] {score:.0%}"


# ─── Command handlers ─────────────────────────────────────────────────────────

async def _cmd_help(chat_id: int):
    await _reply(chat_id, (
        "🔐 <b>BeastPay Lockbox Bot</b>\n\n"
        "Send me any raw payment text and I'll parse + validate it.\n\n"
        "<b>Commands:</b>\n"
        "/parse &lt;text&gt; — force-parse the given text\n"
        "/transactions — last 10 parsed transactions\n"
        "/status — system status\n"
        "/help — this message\n\n"
        "<i>Or just paste card data directly!</i>"
    ))


async def _cmd_status(chat_id: int):
    from config import ANTHROPIC_API_KEY, TELEGRAM_ENABLED
    ai_ok = await lockbox.test_claude_connection()
    stats = db.get_lockbox_stats()
    await _reply(chat_id, (
        "📊 <b>Lockbox Status</b>\n\n"
        f"🤖 Claude AI: {'✅ Connected' if ai_ok else '❌ Not configured'}\n"
        f"📨 Telegram: {'✅ Active' if TELEGRAM_ENABLED else '❌ Disabled'}\n"
        f"🗃 Total parsed: {stats.get('total', 0)}\n"
        f"✅ Valid cards: {stats.get('valid', 0)}\n"
        f"❌ Invalid: {stats.get('invalid', 0)}\n"
    ))


async def _cmd_transactions(chat_id: int):
    txs = db.list_lockbox_transactions(limit=10)
    if not txs:
        await _reply(chat_id, "📭 No transactions yet.")
        return
    lines = ["📋 <b>Last 10 parsed transactions:</b>\n"]
    for t in txs:
        status_icon = "✅" if t["validation_status"] == "valid" else "❌"
        lines.append(
            f"{status_icon} <code>#{t['id']}</code> | {t['masked_card_number']} | "
            f"{t['cardholder_name']} | {t['created_at'][:16]}"
        )
    await _reply(chat_id, "\n".join(lines))


# ─── Core payment parse flow ──────────────────────────────────────────────────

async def _parse_and_respond(chat_id: int, raw_text: str, source: str = "telegram"):
    # Acknowledge
    await _reply(chat_id, "🔍 <i>Parsing payment data with Claude AI…</i>")

    try:
        # 1. AI parsing
        parsed = await lockbox.parse_payment_input(raw_text)
    except Exception as e:
        await _reply(chat_id, f"❌ <b>Parse failed:</b> {e}")
        return

    # 2. Validate
    validation = lockbox.validate_card_data({
        "cardNumber":     parsed.get("cardNumber", ""),
        "expiryDate":     parsed.get("expiryDate", ""),
        "cvv":            parsed.get("cvv", ""),
        "cardholderName": parsed.get("cardholderName", ""),
        "billingAddress": parsed.get("billingAddress", {}),
    })

    # 3. Mask & store
    masked = lockbox.mask_card_number(parsed.get("cardNumber", ""))
    addr = parsed.get("billingAddress", {})
    conf = parsed.get("confidence", {})

    tx = db.create_lockbox_transaction({
        "raw_input":         raw_text,
        "masked_card_number": masked,
        "card_number":       parsed.get("cardNumber", ""),
        "expiry_date":       parsed.get("expiryDate", ""),
        "cvv":               parsed.get("cvv", ""),
        "cardholder_name":   parsed.get("cardholderName", ""),
        "billing_street":    addr.get("street", ""),
        "billing_city":      addr.get("city", ""),
        "billing_state":     addr.get("state", ""),
        "billing_zip":       addr.get("zipCode", ""),
        "billing_country":   addr.get("country", ""),
        "validation_status": "valid" if validation["overall"]["isValid"] else "invalid",
        "validation_errors": json.dumps(validation["overall"]["errors"]),
        "confidence_scores": json.dumps(conf),
        "anomalies":         json.dumps(parsed.get("anomalies", [])),
        "ai_reasoning":      parsed.get("rawAiReasoning", ""),
        "source":            source,
    })

    # 4. Format response
    is_valid = validation["overall"]["isValid"]
    status_line = "✅ <b>VALID</b>" if is_valid else "❌ <b>INVALID</b>"
    errors_text = ""
    if not is_valid:
        err_list = validation["overall"]["errors"][:5]
        errors_text = "\n⚠️ " + "\n⚠️ ".join(err_list)

    anomalies = parsed.get("anomalies", [])
    anomaly_text = ""
    if anomalies:
        anomaly_text = "\n🔸 " + "\n🔸 ".join(anomalies[:3])

    tx_id = tx["id"] if tx else "N/A"
    msg = (
        f"🔐 <b>Lockbox Parse Result</b>  #{tx_id}\n"
        f"{'─' * 30}\n"
        f"{status_line}{errors_text}\n\n"
        f"💳 <b>Card:</b> <code>{masked}</code>\n"
        f"📅 <b>Expiry:</b> {parsed.get('expiryDate', '—')}\n"
        f"👤 <b>Name:</b> {parsed.get('cardholderName', '—')}\n"
        f"🏠 <b>Address:</b> {addr.get('street', '—')}, {addr.get('city', '—')}, "
        f"{addr.get('state', '—')} {addr.get('zipCode', '—')}, {addr.get('country', '—')}\n\n"
        f"<b>Confidence Scores:</b>\n"
        f"  Card:    {_conf_bar(conf.get('cardNumber', 0))}\n"
        f"  Expiry:  {_conf_bar(conf.get('expiryDate', 0))}\n"
        f"  CVV:     {_conf_bar(conf.get('cvv', 0))}\n"
        f"  Name:    {_conf_bar(conf.get('cardholderName', 0))}\n"
        f"  Address: {_conf_bar(conf.get('billingAddress', 0))}"
    )
    if anomaly_text:
        msg += f"\n\n<b>Anomalies:</b>{anomaly_text}"

    await _reply(chat_id, msg)


# ─── Main update dispatcher ───────────────────────────────────────────────────

async def handle_update(update: dict):
    """
    Called for each incoming Telegram update from the webhook.
    Dispatches commands or payment-data messages.
    """
    message = update.get("message") or update.get("edited_message")
    if not message:
        return

    chat_id = message["chat"]["id"]
    text = (message.get("text") or "").strip()

    if not text:
        return

    # ── Commands ──────────────────────────────────────────────────────────────
    if text.startswith("/help") or text == "/start":
        await _cmd_help(chat_id)
        return

    if text.startswith("/status"):
        await _cmd_status(chat_id)
        return

    if text.startswith("/transactions") or text.startswith("/history"):
        await _cmd_transactions(chat_id)
        return

    if text.startswith("/parse "):
        raw = text[7:].strip()
        if raw:
            await _parse_and_respond(chat_id, raw, source="telegram_cmd")
        else:
            await _reply(chat_id, "Usage: /parse &lt;payment text&gt;")
        return

    # ── Auto-detect payment data ──────────────────────────────────────────────
    if _looks_like_payment_data(text):
        await _parse_and_respond(chat_id, text, source="telegram_auto")
        return

    # ── Default fallback ──────────────────────────────────────────────────────
    await _reply(chat_id, (
        "👋 <b>BeastPay Lockbox</b>\n\n"
        "Send me payment card data to parse and validate it.\n"
        "Type /help to see all commands."
    ))

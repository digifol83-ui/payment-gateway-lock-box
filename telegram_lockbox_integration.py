#!/usr/bin/env python3
"""
Telegram Lockbox Integration - Card Verification in Telegram
Integrates advanced card verification into Telegram payment gateway
"""

import asyncio
import json
import httpx
import logging
from datetime import datetime
from typing import Optional, Dict
from enum import Enum

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import lockbox integration
try:
    from lockbox_integration import process_payment_with_verification
    from card_parser import parse_card_input
    from database import init_db
    LOCKBOX_AVAILABLE = True
except ImportError:
    LOCKBOX_AVAILABLE = False
    logger.warning("⚠️ Lockbox integration not available")

# Initialize database on import
try:
    init_db()
except Exception as e:
    logger.warning(f"Database initialization warning: {e}")


class VerificationStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    CHALLENGE = "challenge"
    DECLINED = "declined"
    ERROR = "error"


class TelegramLockboxBot:
    """Telegram bot with integrated card verification"""

    def __init__(
        self,
        bot_token: str,
        telegram_chat_id: str,
        admin_ids: list = None,
    ):
        self.bot_token = bot_token
        self.telegram_chat_id = telegram_chat_id
        self.admin_ids = admin_ids or []
        self.telegram_api = f"https://api.telegram.org/bot{bot_token}"
        self.http_timeout = httpx.Timeout(10.0, connect=5.0)
        self.verification_cache = {}  # Store recent verifications

    async def send_message(
        self,
        chat_id: str,
        text: str,
        parse_mode: str = "HTML",
        reply_markup: Optional[Dict] = None,
    ) -> bool:
        """Send message to Telegram chat"""
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup

        try:
            async with httpx.AsyncClient(timeout=self.http_timeout) as client:
                response = await client.post(
                    f"{self.telegram_api}/sendMessage",
                    json=payload,
                )
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            return False

    async def verify_card_telegram(
        self,
        raw_card_input: str,
        user_id: str,
        user_name: str = "User",
        ip_address: Optional[str] = None,
        transaction_country: str = "US",
        transaction_amount: float = 0.0,
        run_advanced: bool = True,
    ) -> Dict:
        """Verify card and send result to Telegram"""

        if not LOCKBOX_AVAILABLE:
            await self.send_message(
                self.telegram_chat_id,
                "❌ Card verification unavailable - Lockbox not configured",
            )
            return {"status": "error", "reason": "Lockbox not available"}

        try:
            # Run verification pipeline
            logger.info(f"🔐 Verifying card for {user_name} (ID: {user_id})")

            result = await process_payment_with_verification(
                raw_card_input=raw_card_input,
                ip_address=ip_address,
                device_id=f"telegram_{user_id}",
                region="US",
                db_path="payments.db",
                run_advanced_verification=run_advanced,
                transaction_country=transaction_country,
                transaction_amount=transaction_amount,
            )

            # Cache result
            self.verification_cache[user_id] = {
                "result": result,
                "timestamp": datetime.utcnow().isoformat(),
                "user": user_name,
            }

            # Send notification to admin
            await self._notify_admin_verification(
                user_id, user_name, result, run_advanced
            )

            return result

        except Exception as e:
            logger.error(f"Card verification error: {e}", exc_info=True)
            await self.send_message(
                self.telegram_chat_id,
                f"❌ <b>Verification Error</b>\n{str(e)[:200]}",
            )
            return {"status": "error", "reason": str(e)}

    async def _notify_admin_verification(
        self,
        user_id: str,
        user_name: str,
        result: Dict,
        advanced: bool = False,
    ) -> None:
        """Send verification result notification to admin"""

        recommendation = result.get("recommendation", "unknown").upper()
        fraud_score = result.get("fraud_score", "N/A")
        risk_level = result.get("risk_level", "unknown")
        masked_card = result.get("masked_card", "****")

        # Build notification message
        status_icon = {
            "approve": "✅",
            "challenge": "⚠️",
            "decline": "❌",
            "error": "❌",
        }.get(recommendation.lower(), "❓")

        message = f"""
{status_icon} <b>Card Verification Result</b>

👤 <b>User:</b> {user_name} (ID: {user_id})
🎴 <b>Card:</b> {masked_card}
📊 <b>Fraud Score:</b> {fraud_score}/99
⚠️ <b>Risk Level:</b> {risk_level}
🎯 <b>Recommendation:</b> <b>{recommendation}</b>

"""

        # Add advanced verification details if available
        if advanced and result.get("advanced_verification"):
            adv = result["advanced_verification"]
            message += f"""
🔬 <b>Advanced Verification:</b>
  • <b>Verified:</b> {'✅ YES' if adv.get('overall_verified') else '❌ NO'}
  • <b>Score:</b> {adv.get('verification_score', 0):.1f}/100
  • <b>Methods:</b>
"""
            for check_name, check_result in adv.get("checks", {}).items():
                status = "✓" if check_result.get("status") == "complete" else "✗"
                message += f"    {status} {check_name}\n"

        # Add pipeline steps
        message += f"\n<b>Pipeline Steps:</b>\n"
        for i, step in enumerate(result.get("steps", []), 1):
            status_icon_step = (
                "✓" if step.get("status") == "success"
                else "✗" if step.get("status") == "failed"
                else "→"
            )
            message += f"  {i}. {status_icon_step} {step.get('name', 'Unknown')}\n"

        # Add timestamp
        message += f"\n🕐 <b>Time:</b> {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}"

        await self.send_message(self.telegram_chat_id, message)

    async def send_verification_summary(self) -> None:
        """Send summary of recent verifications to Telegram"""

        if not self.verification_cache:
            await self.send_message(
                self.telegram_chat_id,
                "📊 <b>No verifications yet</b>",
            )
            return

        summary_message = "<b>🔐 Recent Card Verifications</b>\n\n"

        stats = {
            "total": len(self.verification_cache),
            "approved": 0,
            "challenged": 0,
            "declined": 0,
            "errors": 0,
        }

        for user_id, cache_entry in self.verification_cache.items():
            result = cache_entry["result"]
            rec = result.get("recommendation", "unknown").lower()

            if rec == "approve":
                stats["approved"] += 1
                icon = "✅"
            elif rec == "challenge":
                stats["challenged"] += 1
                icon = "⚠️"
            elif rec == "decline":
                stats["declined"] += 1
                icon = "❌"
            else:
                stats["errors"] += 1
                icon = "⚠️"

            user_name = cache_entry.get("user", "Unknown")
            fraud_score = result.get("fraud_score", "N/A")

            summary_message += f"{icon} {user_name}: Score {fraud_score}/99\n"

        summary_message += f"""
<b>Summary Statistics:</b>
  • Total Verifications: {stats['total']}
  • ✅ Approved: {stats['approved']}
  • ⚠️ Challenged: {stats['challenged']}
  • ❌ Declined: {stats['declined']}
  • ⚠️ Errors: {stats['errors']}

Approval Rate: {(stats['approved'] / stats['total'] * 100):.1f}% (if total > 0 else 0)
"""

        await self.send_message(self.telegram_chat_id, summary_message)

    async def handle_card_input_command(
        self,
        user_id: str,
        user_name: str,
        raw_input: str,
        ip_address: Optional[str] = None,
    ) -> None:
        """Handle card input from Telegram user"""

        # Send parsing notification
        await self.send_message(
            self.telegram_chat_id,
            f"🔍 <b>Parsing card data from {user_name}...</b>",
        )

        # Parse card
        parsed = parse_card_input(raw_input)

        if not parsed.get("success"):
            await self.send_message(
                self.telegram_chat_id,
                f"""❌ <b>Failed to parse card</b>
User: {user_name}
Error: {', '.join(parsed.get('anomalies', ['Unknown error']))}""",
            )
            return

        # Show parsed data
        parsed_message = f"✅ <b>Card Parsed Successfully</b>\n\n"
        for key, value in parsed["data"].items():
            confidence = parsed["confidence"].get(key, 0)
            parsed_message += f"  • {key}: {value} ({confidence:.0%})\n"

        await self.send_message(self.telegram_chat_id, parsed_message)

        # Run verification
        await self.verify_card_telegram(
            raw_card_input=raw_input,
            user_id=user_id,
            user_name=user_name,
            ip_address=ip_address,
            run_advanced=True,  # Always run advanced for Telegram
        )


# ─── Standalone Functions ──────────────────────────────────────────────────────


async def activate_lockbox_telegram(
    bot_token: str,
    telegram_chat_id: str,
    admin_ids: list = None,
) -> TelegramLockboxBot:
    """Activate Lockbox integration in Telegram bot"""

    logger.info("🚀 Activating Lockbox Integration in Telegram Bot...")

    bot = TelegramLockboxBot(
        bot_token=bot_token,
        telegram_chat_id=telegram_chat_id,
        admin_ids=admin_ids or [],
    )

    # Send activation message
    activation_msg = """
✅ <b>🔐 LOCKBOX INTEGRATION ACTIVATED</b>

<b>Features Enabled:</b>
  ✓ Card data parsing (any format)
  ✓ Stripe-style fraud detection (0-99 scoring)
  ✓ BIN lookup (card intelligence)
  ✓ Balance inquiry checks
  ✓ Network tokenization
  ✓ Identity verification (KYC)
  ✓ Network security signals

<b>Status:</b> ONLINE & READY

🎯 Send card data in any format:
  • Structured: "4111111111111111 12/27 123"
  • Unstructured: "my card is 4111... expires 12/27..."
  • Natural language: Fully supported

Ready to verify payments! 💳
"""

    await bot.send_message(telegram_chat_id, activation_msg)
    logger.info("✅ Lockbox Telegram Integration Ready!")

    return bot


# ─── CLI Testing ──────────────────────────────────────────────────────────────


if __name__ == "__main__":
    import os
    from dotenv import load_dotenv

    load_dotenv()

    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

    if not TELEGRAM_BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN not set in environment")
        exit(1)

    if not TELEGRAM_CHAT_ID:
        print("❌ TELEGRAM_CHAT_ID not set in environment")
        exit(1)

    async def test():
        # Activate bot
        bot = await activate_lockbox_telegram(
            bot_token=TELEGRAM_BOT_TOKEN,
            telegram_chat_id=TELEGRAM_CHAT_ID,
        )

        # Test card verification
        print("\n🧪 Testing card verification...")
        result = await bot.verify_card_telegram(
            raw_card_input="4111111111111111 12/27 123 John Doe 123 Main St New York NY 10001 US",
            user_id="test_user_123",
            user_name="Test User",
            transaction_amount=100.0,
            run_advanced=True,
        )

        print(f"✅ Verification result sent to Telegram")
        print(f"Recommendation: {result.get('recommendation', 'unknown').upper()}")

        # Send summary
        await bot.send_verification_summary()

    asyncio.run(test())

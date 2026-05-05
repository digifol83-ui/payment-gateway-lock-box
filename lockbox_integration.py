#!/usr/bin/env python3
"""
Lockbox Integration with Stripe-Style Card Verification
Integrates lockbox.py (Claude AI parsing) with card_verification.py (fraud detection)
"""

import asyncio
import json
import logging
import sqlite3
from typing import Optional, Dict, Tuple
from datetime import datetime

try:
    from card_parser import parse_card_input
    from card_verification import (
        complete_card_verification,
        record_verification_attempt,
        get_card_history,
        get_card_type,
        CardValidationResult,
        VerificationResult,
        RiskLevel
    )
    from advanced_card_verification import AdvancedCardVerifier
    from lockbox import mask_card_number
except ImportError as e:
    print(f"⚠️ Import error: {e}")

logger = logging.getLogger(__name__)


async def process_payment_with_verification(
    raw_card_input: str,
    ip_address: Optional[str] = None,
    device_id: Optional[str] = None,
    region: str = "US",
    db_path: str = "payments.db",
    run_advanced_verification: bool = False,
    transaction_country: str = "US",
    transaction_amount: float = 0.0
) -> Dict:
    """
    Complete payment processing flow with verification

    1. Parse raw card input using intelligent card parser
    2. Validate card format (Luhn, expiry, etc.)
    3. Check velocity/history
    4. Run fraud risk analysis
    5. (Optional) Run advanced verification (BIN lookup, balance, tokenization, KYC, network signals)
    6. Decide: approve, challenge (3DS), or decline
    7. Log attempt for future velocity checks
    """

    result = {
        "status": "pending",
        "timestamp": datetime.utcnow().isoformat(),
        "steps": []
    }

    try:
        # ─── STEP 1: Parse with Intelligent Card Parser ────
        result["steps"].append({
            "name": "Card Data Extraction",
            "status": "in_progress"
        })

        parsed_data = parse_card_input(raw_card_input)

        result["steps"][-1]["status"] = "success"
        result["steps"][-1]["confidence"] = parsed_data.get("confidence", {})
        result["steps"][-1]["anomalies"] = parsed_data.get("anomalies", [])

        # ─── STEP 2: Basic Format Validation ────
        result["steps"].append({
            "name": "Format Validation (Luhn, expiry, etc.)",
            "status": "in_progress"
        })

        # Check if parsing was successful and has required fields
        if not parsed_data.get("success"):
            result["steps"][-1]["status"] = "failed"
            result["steps"][-1]["errors"] = parsed_data.get("anomalies", ["No card data extracted"])
            result["status"] = "declined"
            result["reason"] = "Card format validation failed"
            result["recommendation"] = "decline"
            return result

        # Check for required fields
        required_fields = ["cardNumber", "expiryDate", "cvv"]
        missing = [f for f in required_fields if f not in parsed_data.get("data", {})]

        if missing:
            result["steps"][-1]["status"] = "failed"
            result["steps"][-1]["errors"] = [f"Missing required fields: {', '.join(missing)}"]
            result["status"] = "declined"
            result["reason"] = "Missing card details"
            result["recommendation"] = "decline"
            return result

        result["steps"][-1]["status"] = "success"

        # Map parsed data to expected format
        parsed_data_mapped = {
            "cardNumber": parsed_data["data"].get("cardNumber", ""),
            "expiryDate": parsed_data["data"].get("expiryDate", ""),
            "cvv": parsed_data["data"].get("cvv", ""),
            "cardholderName": parsed_data["data"].get("cardholderName", ""),
            "billingStreet": parsed_data["data"].get("billingStreet", ""),
            "billingCity": parsed_data["data"].get("billingCity", ""),
            "billingState": parsed_data["data"].get("billingState", ""),
            "billingZip": parsed_data["data"].get("billingZip", ""),
            "billingCountry": parsed_data["data"].get("billingCountry", "US"),
            "email": parsed_data["data"].get("email", ""),
        }

        # ─── STEP 3: Get Card History (Velocity Check) ────
        result["steps"].append({
            "name": "Velocity Check",
            "status": "in_progress"
        })

        card_number = parsed_data_mapped.get("cardNumber", "")
        user_history = get_card_history(db_path, card_number)

        result["steps"][-1]["status"] = "success"
        result["steps"][-1]["attempts_last_hour"] = user_history["attempts_last_hour"]
        result["steps"][-1]["attempts_last_24h"] = user_history["attempts_last_24h"]

        # ─── STEP 4: Complete Card Verification (Stripe-style) ────
        result["steps"].append({
            "name": "Complete Verification (Luhn, AVS, Pre-Auth, Fraud Scoring)",
            "status": "in_progress"
        })

        verification = await complete_card_verification(
            card_data=parsed_data_mapped,
            ip_address=ip_address,
            device_id=device_id,
            user_history=user_history,
            region=region
        )

        result["steps"][-1]["status"] = "success"
        result["steps"][-1]["fraud_score"] = verification.fraud_score.score
        result["steps"][-1]["risk_level"] = verification.fraud_score.risk_level
        result["steps"][-1]["fraud_signals"] = verification.fraud_score.signals

        # ─── STEP 5: (Optional) Advanced Verification ────
        advanced_result = None
        if run_advanced_verification and verification.recommendation != "decline":
            result["steps"].append({
                "name": "Advanced Verification (BIN, Balance, Token, KYC, Network Signals)",
                "status": "in_progress"
            })

            try:
                advanced_result = await AdvancedCardVerifier.full_advanced_verification(
                    card_number=card_number,
                    cardholder_name=parsed_data_mapped.get("cardholderName", ""),
                    card_type=get_card_type(card_number) or "credit",
                    transaction_amount=transaction_amount,
                    transaction_country=transaction_country,
                    user_country=region,
                    require_identity_verification=False
                )

                result["steps"][-1]["status"] = "success"
                result["steps"][-1]["advanced_verified"] = advanced_result["overall_verified"]
                result["steps"][-1]["verification_score"] = advanced_result["verification_score"]
                result["steps"][-1]["checks"] = {k: v.get("status", "complete") for k, v in advanced_result["checks"].items()}

                # If advanced verification fails, escalate recommendation
                if not advanced_result["overall_verified"]:
                    verification.recommendation = "challenge"

                result["advanced_verification"] = advanced_result

            except Exception as e:
                logger.warning(f"Advanced verification failed: {e}")
                result["steps"][-1]["status"] = "warning"
                result["steps"][-1]["error"] = str(e)

        # ─── STEP 6: Decide Action ────
        result["status"] = verification.recommendation  # "approve", "challenge", "decline"
        result["recommendation"] = verification.recommendation
        result["fraud_score"] = verification.fraud_score.score
        result["risk_level"] = verification.fraud_score.risk_level

        if verification.recommendation == "approve":
            result["action"] = "Process payment normally"
            result["auth_reference"] = verification.pre_auth.reference_id

        elif verification.recommendation == "challenge":
            result["action"] = "Require 3D Secure authentication"
            result["needs_3ds"] = True
            result["challenge_type"] = "3ds" if verification.fraud_score.needs_3ds else "otp"

        else:  # decline
            result["action"] = "Decline transaction"
            result["reason"] = verification.pre_auth.message if not verification.pre_auth.approved else "Fraud risk too high"

        # ─── STEP 7: Log Attempt ────
        result["steps"].append({
            "name": "Log Verification Attempt",
            "status": "in_progress"
        })

        try:
            record_verification_attempt(
                db_path=db_path,
                card_number=card_number,
                result=verification,
                ip_address=ip_address,
                device_id=device_id,
                region=region
            )
            result["steps"][-1]["status"] = "success"
        except Exception as e:
            logger.warning(f"Failed to log verification: {e}")
            result["steps"][-1]["status"] = "warning"
            result["steps"][-1]["error"] = str(e)

        # ─── Mask sensitive data before returning ────
        result["masked_card"] = mask_card_number(card_number)
        result["card_type"] = parsed_data.get("card_type", "unknown")
        result["avs_match"] = verification.avs_match

        return result

    except json.JSONDecodeError as e:
        logger.error(f"Claude AI response parsing failed: {e}")
        result["status"] = "error"
        result["error"] = f"AI parsing failed: {str(e)}"
        return result

    except Exception as e:
        logger.error(f"Payment processing error: {e}", exc_info=True)
        result["status"] = "error"
        result["error"] = str(e)
        return result


async def fast_verify_card(card_number: str, ip_address: Optional[str] = None) -> Dict:
    """Quick verification without full parsing"""

    verification = await complete_card_verification(
        card_data={"cardNumber": card_number},
        ip_address=ip_address,
        region="US"
    )

    return {
        "card_valid": verification.card_valid,
        "recommendation": verification.recommendation,
        "fraud_score": verification.fraud_score.score,
        "risk_level": verification.fraud_score.risk_level,
        "3ds_required": verification.fraud_score.needs_3ds
    }


# ═══════════════════════════════════════════════════════════════════════════════
# SERVER ENDPOINT INTEGRATION (for FastAPI)
# ═══════════════════════════════════════════════════════════════════════════════

def create_lockbox_routes(app, db_path: str = "payments.db"):
    """Add payment verification endpoints to FastAPI app"""

    @app.post("/api/verify-card")
    async def verify_card_endpoint(request: dict):
        """Verify card and return recommendation"""
        raw_input = request.get("raw_input")
        ip_address = request.get("ip_address")
        device_id = request.get("device_id")
        region = request.get("region", "US")

        if not raw_input:
            return {"error": "raw_input required"}, 400

        result = await process_payment_with_verification(
            raw_input,
            ip_address=ip_address,
            device_id=device_id,
            region=region,
            db_path=db_path
        )

        status_code = 200 if result["status"] != "error" else 400
        return result, status_code

    @app.post("/api/quick-verify")
    async def quick_verify_endpoint(request: dict):
        """Fast verification of card number"""
        card_number = request.get("card_number")
        ip_address = request.get("ip_address")

        if not card_number:
            return {"error": "card_number required"}, 400

        result = await fast_verify_card(card_number, ip_address)
        return result

    @app.get("/api/card-history/{card_hash}")
    async def card_history_endpoint(card_hash: str):
        """Get verification history for debugging (admin only)"""
        # In production: require admin auth
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.execute("""
                SELECT fraud_score, recommendation, timestamp FROM card_verification_log
                WHERE card_hash = ? ORDER BY timestamp DESC LIMIT 10
            """, (card_hash,))
            history = [
                {"score": row[0], "recommendation": row[1], "timestamp": row[2]}
                for row in cursor.fetchall()
            ]
            conn.close()
            return {"card_hash": card_hash, "history": history}
        except Exception as e:
            return {"error": str(e)}, 500

    logger.info("Lockbox verification routes registered")


# ═══════════════════════════════════════════════════════════════════════════════
# CLI TESTING
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys

    # Test cases
    test_inputs = [
        # Valid Visa
        {
            "name": "Valid Visa",
            "raw_input": "4532015112830366 12/25 123 John Doe 123 Main St New York NY 10001 US",
            "ip": "203.0.113.45",
            "device": "device_abc123"
        },
        # Suspicious (high velocity)
        {
            "name": "Suspicious (many attempts)",
            "raw_input": "4111111111111111 06/26 456 Jane Smith 456 Oak Ave LA CA 90001 US",
            "ip": "192.0.2.1",
            "device": "new_device_xyz"
        },
    ]

    async def run_tests():
        for test in test_inputs:
            print(f"\n{'='*70}")
            print(f"Test: {test['name']}")
            print('='*70)

            result = await process_payment_with_verification(
                test["raw_input"],
                ip_address=test.get("ip"),
                device_id=test.get("device"),
                region="US"
            )

            print(f"\n✅ Status: {result.get('status').upper()}")
            print(f"📊 Fraud Score: {result.get('fraud_score', 'N/A')}/99")
            print(f"⚠️  Risk Level: {result.get('risk_level', 'N/A')}")
            print(f"🎯 Recommendation: {result.get('recommendation', 'N/A').upper()}")
            print(f"🔐 3DS Required: {result.get('needs_3ds', False)}")

            if "fraud_signals" in result.get("steps", [{}])[-1]:
                print("\n🚨 Fraud Signals:")
                for signal in result["steps"][-1].get("fraud_signals", []):
                    print(f"   • {signal}")

            print(f"\n📝 Steps:")
            for step in result.get("steps", []):
                status_icon = "✓" if step["status"] == "success" else "✗" if step["status"] == "failed" else "→"
                print(f"   {status_icon} {step['name']}: {step['status']}")

    if "--test" in sys.argv:
        asyncio.run(run_tests())
    else:
        print("Lockbox verification integration module")
        print("Usage: python3 lockbox_integration.py --test")

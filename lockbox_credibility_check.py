#!/usr/bin/env python3
"""
BEAST Phase 1: Lockbox Card Credibility Assessment
Analyzes card validation data, anomalies, and confidence scores
"""

import sqlite3
import json
import sys
from datetime import datetime, timedelta
import re

class LockboxCredibilityAnalyzer:
    def __init__(self, db_path="payments.db"):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()

    def add_test_card(self, card_data: dict):
        """Insert test card data for validation."""
        self.cursor.execute("""
            INSERT INTO lockbox_transactions
            (raw_input, masked_card_number, card_number, expiry_date, cvv,
             cardholder_name, billing_street, billing_city, billing_state,
             billing_zip, billing_country, validation_status, confidence_scores,
             anomalies, ai_reasoning, source, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            card_data.get('raw_input', ''),
            card_data.get('masked_card', '****-****-****-' + card_data.get('card', '')[-4:]),
            card_data.get('card', ''),
            card_data.get('expiry', ''),
            card_data.get('cvv', ''),
            card_data.get('name', ''),
            card_data.get('street', ''),
            card_data.get('city', ''),
            card_data.get('state', ''),
            card_data.get('zip', ''),
            card_data.get('country', 'AE'),
            card_data.get('status', 'pending'),
            json.dumps(card_data.get('confidence_scores', {})),
            json.dumps(card_data.get('anomalies', [])),
            card_data.get('ai_reasoning', ''),
            card_data.get('source', 'manual'),
            datetime.now().isoformat(),
            datetime.now().isoformat()
        ))
        self.conn.commit()

    def validate_card_luhn(self, card_number: str) -> bool:
        """Validate card using Luhn algorithm."""
        card = card_number.replace('-', '').replace(' ', '')
        if not card.isdigit() or len(card) < 13:
            return False

        digits = [int(d) for d in card]
        checksum = 0
        for i, digit in enumerate(reversed(digits)):
            if i % 2 == 1:
                digit *= 2
                if digit > 9:
                    digit -= 9
            checksum += digit
        return checksum % 10 == 0

    def assess_card_credibility(self) -> dict:
        """Analyze all cards in lockbox and score credibility."""
        self.cursor.execute("""
            SELECT * FROM lockbox_transactions
            ORDER BY created_at DESC
        """)

        cards = self.cursor.fetchall()
        total = len(cards)

        credibility_report = {
            "timestamp": datetime.now().isoformat(),
            "total_cards": total,
            "by_status": {},
            "credibility_scores": [],
            "risk_flags": [],
            "summary": {}
        }

        # Group by validation status
        self.cursor.execute("""
            SELECT validation_status, COUNT(*) as count
            FROM lockbox_transactions
            GROUP BY validation_status
        """)

        for row in self.cursor.fetchall():
            credibility_report["by_status"][row['validation_status']] = row['count']

        # Analyze each card
        for card in cards:
            card_score = self._score_card(card)
            credibility_report["credibility_scores"].append(card_score)

            # Flag high-risk cards
            if card_score['credibility_score'] < 50:
                credibility_report["risk_flags"].append({
                    "card_id": card['id'],
                    "masked": card['masked_card_number'],
                    "reason": card_score['risks'],
                    "score": card_score['credibility_score']
                })

        # Calculate summary statistics
        if credibility_report["credibility_scores"]:
            scores = [c['credibility_score'] for c in credibility_report["credibility_scores"]]
            credibility_report["summary"] = {
                "avg_credibility": round(sum(scores) / len(scores), 2),
                "min_credibility": min(scores),
                "max_credibility": max(scores),
                "high_confidence": sum(1 for s in scores if s >= 80),
                "medium_confidence": sum(1 for s in scores if 50 <= s < 80),
                "low_confidence": sum(1 for s in scores if s < 50)
            }

        return credibility_report

    def _score_card(self, card: dict) -> dict:
        """Score individual card credibility (0-100)."""
        score = 100
        risks = []

        # Parse JSON fields
        try:
            confidence = json.loads(card['confidence_scores'] or '{}')
        except:
            confidence = {}

        try:
            anomalies = json.loads(card['anomalies'] or '[]')
        except:
            anomalies = []

        try:
            errors = json.loads(card['validation_errors'] or '[]')
        except:
            errors = []

        # 1. Luhn check (-20 if failed)
        if not self.validate_card_luhn(card['card_number']):
            score -= 20
            risks.append("Luhn validation failed")

        # 2. Expiry date validation (-15 if expired or invalid)
        try:
            exp_month, exp_year = card['expiry_date'].split('/')
            exp_date = datetime(2000 + int(exp_year), int(exp_month), 28)
            if exp_date < datetime.now():
                score -= 15
                risks.append("Card expired")
        except:
            score -= 10
            risks.append("Invalid expiry format")

        # 3. CVV length (-10 if invalid)
        if not (len(card['cvv']) in [3, 4]):
            score -= 10
            risks.append("Invalid CVV length")

        # 4. Cardholder name length (-5 if too short/long)
        name_len = len(card['cardholder_name'])
        if name_len < 3 or name_len > 50:
            score -= 5
            risks.append("Cardholder name length invalid")

        # 5. Confidence scores analysis
        if confidence:
            avg_confidence = sum(confidence.values()) / len(confidence) if confidence else 0
            if avg_confidence < 50:
                score -= int((100 - avg_confidence) / 2)
                risks.append(f"Low avg confidence: {avg_confidence:.0f}%")

        # 6. Anomaly detection (-20 per anomaly)
        if anomalies:
            score -= min(20 * len(anomalies), 30)
            risks.extend(anomalies)

        # 7. Validation errors (-15 per error)
        if errors:
            score -= min(15 * len(errors), 25)
            risks.extend(errors)

        # 8. Age of record (bonus if recent)
        try:
            created = datetime.fromisoformat(card['created_at'])
            age_hours = (datetime.now() - created).total_seconds() / 3600
            if age_hours < 24:
                score += 5  # Recent cards get slight bonus
        except:
            pass

        # Clamp score between 0-100
        score = max(0, min(100, score))

        return {
            "card_id": card['id'],
            "masked_card": card['masked_card_number'],
            "credibility_score": round(score, 2),
            "validation_status": card['validation_status'],
            "risks": risks,
            "confidence_avg": round(sum(confidence.values()) / len(confidence), 2) if confidence else 0,
            "anomaly_count": len(anomalies),
            "error_count": len(errors)
        }

    def print_report(self, report: dict):
        """Format and print credibility report."""
        print("\n" + "=" * 80)
        print("🔒 LOCKBOX CARD CREDIBILITY ASSESSMENT (Phase 1)")
        print("=" * 80)

        print(f"\n📊 Overall Status:")
        print(f"   Total Cards: {report['total_cards']}")
        print(f"   Timestamp: {report['timestamp']}")

        if report['by_status']:
            print(f"\n   By Validation Status:")
            for status, count in report['by_status'].items():
                print(f"      • {status}: {count}")

        if report['summary']:
            print(f"\n📈 Credibility Statistics:")
            print(f"   Average Score: {report['summary'].get('avg_credibility', 0)}/100")
            print(f"   Range: {report['summary'].get('min_credibility', 0)} - {report['summary'].get('max_credibility', 0)}")
            print(f"   High (≥80): {report['summary'].get('high_confidence', 0)}")
            print(f"   Medium (50-79): {report['summary'].get('medium_confidence', 0)}")
            print(f"   Low (<50): {report['summary'].get('low_confidence', 0)}")

        if report['credibility_scores']:
            print(f"\n🎯 Card Details:")
            for i, card in enumerate(report['credibility_scores'][:10], 1):
                status_icon = "✅" if card['credibility_score'] >= 80 else "⚠️ " if card['credibility_score'] >= 50 else "❌"
                print(f"\n   [{i}] {card['masked_card']}")
                print(f"       Score: {card['credibility_score']}/100 {status_icon}")
                print(f"       Status: {card['validation_status']}")
                print(f"       Confidence: {card['confidence_avg']}%")
                if card['risks']:
                    print(f"       Risks: {', '.join(card['risks'][:3])}")

        if report['risk_flags']:
            print(f"\n⚠️  HIGH RISK FLAGS ({len(report['risk_flags'])}):")
            for flag in report['risk_flags'][:5]:
                print(f"   • {flag['masked']} - Score: {flag['score']}/100")
                for reason in flag['reason'][:2]:
                    print(f"     - {reason}")

        print("\n" + "=" * 80)

    def close(self):
        """Close database connection."""
        self.conn.close()


def main():
    """Main Phase 1 diagnostic flow."""
    print("\n🚀 BEAST Payment Gateway - Phase 1 Foundation Check")
    print("-" * 80)

    analyzer = LockboxCredibilityAnalyzer()

    # Check database status
    try:
        analyzer.cursor.execute("SELECT COUNT(*) as count FROM lockbox_transactions")
        card_count = analyzer.cursor.fetchone()['count']
        print(f"✅ Database initialized | Lockbox records: {card_count}")
    except Exception as e:
        print(f"❌ Database error: {e}")
        sys.exit(1)

    # Add sample test cards if empty
    if card_count == 0:
        print("\n📝 Adding sample test cards for validation...")

        test_cards = [
            {
                "raw_input": "4532-1234-5678-9010",
                "card": "4532123456789010",
                "expiry": "12/26",
                "cvv": "123",
                "name": "John Doe",
                "street": "123 Main St",
                "city": "Dubai",
                "state": "AE",
                "zip": "00000",
                "country": "AE",
                "status": "valid",
                "confidence_scores": {"luhn": 95, "expiry": 100, "cvv": 90, "name": 85},
                "anomalies": [],
                "ai_reasoning": "Card data valid and complete"
            },
            {
                "raw_input": "5555-4444-3333-2222",
                "card": "5555444433332222",
                "expiry": "06/25",
                "cvv": "456",
                "name": "Jane Smith",
                "street": "456 Oak Ave",
                "city": "Abu Dhabi",
                "state": "AE",
                "zip": "11111",
                "country": "AE",
                "status": "pending",
                "confidence_scores": {"luhn": 70, "expiry": 60, "cvv": 75, "name": 80},
                "anomalies": ["Expiry date soon", "Low confidence on expiry"],
                "ai_reasoning": "Card valid but approaching expiry"
            },
            {
                "raw_input": "1234-5678-9012-3456",  # Invalid Luhn
                "card": "1234567890123456",
                "expiry": "13/99",  # Invalid month
                "cvv": "12",  # Too short
                "name": "X",  # Too short
                "street": "",
                "city": "Unknown",
                "state": "XX",
                "zip": "",
                "country": "XX",
                "status": "invalid",
                "confidence_scores": {"luhn": 10, "expiry": 0, "cvv": 20, "name": 15},
                "anomalies": ["Invalid Luhn", "Invalid expiry", "Short cardholder name"],
                "ai_reasoning": "Card validation failed on multiple checks"
            }
        ]

        for card in test_cards:
            analyzer.add_test_card(card)
            print(f"   ✓ Added: {card['name']}")

    # Run credibility assessment
    print("\n🔍 Analyzing lockbox card credibility...")
    report = analyzer.assess_card_credibility()
    analyzer.print_report(report)

    # Phase 1 Status
    print("\n✅ Phase 1 Foundation Status:")
    print("   • Database: READY")
    print("   • Lockbox Table: INITIALIZED")
    print(f"   • Card Records: {report['total_cards']}")
    print(f"   • Credibility Analysis: COMPLETE")
    print(f"   • Risk Assessment: {len(report['risk_flags'])} flags detected")

    analyzer.close()
    print("\n✨ Phase 1 Complete - Ready for Phase 2 (Subagent Architecture)")


if __name__ == "__main__":
    main()

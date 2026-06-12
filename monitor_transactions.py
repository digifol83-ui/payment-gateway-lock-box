#!/usr/bin/env python3
"""
Transaction Monitor & Diagnostics
Real-time view of payment volumes, status, and gateway health
"""
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

def get_db():
    """Connect to payments database"""
    db_path = Path("payments.db")
    if not db_path.exists():
        print("❌ payments.db not found")
        sys.exit(1)
    return sqlite3.connect(str(db_path))

def print_header(title: str):
    """Print a formatted header"""
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}\n")

def dashboard(days: int = 30):
    """Show transaction dashboard"""
    db = get_db()
    cursor = db.cursor()

    since = datetime.utcnow() - timedelta(days=days)
    since_str = since.isoformat()

    print_header(f"TRANSACTION DASHBOARD (Last {days} days)")

    # Volume by provider and status
    print("VOLUME BY PROVIDER & STATUS:\n")
    cursor.execute("""
        SELECT provider, status, COUNT(*) as count, SUM(amount) as total
        FROM payments
        WHERE created_at > ?
        GROUP BY provider, status
        ORDER BY provider, status
    """, (since_str,))

    results = cursor.fetchall()
    if not results:
        print("  (No transactions in this period)")
    else:
        by_provider = defaultdict(lambda: {"pending": 0, "failed": 0, "completed": 0, "total": 0})
        for provider, status, count, total in results:
            by_provider[provider][status] = count
            by_provider[provider]["total"] += total or 0

        print(f"{'Provider':<15} {'Pending':<10} {'Failed':<10} {'Completed':<12} {'Total USD':<12}")
        print("-" * 60)
        for provider in sorted(by_provider.keys()):
            stats = by_provider[provider]
            pending = stats.get("pending", 0)
            failed = stats.get("failed", 0)
            completed = stats.get("completed", 0)
            total = stats.get("total", 0)
            print(f"{provider:<15} {pending:<10} {failed:<10} {completed:<12} ${total:<11.2f}")

    # Stripe details
    print_header("STRIPE DIAGNOSTICS")

    cursor.execute("""
        SELECT id, amount, fiat_currency, crypto_currency, status, created_at, description
        FROM payments
        WHERE provider='stripe'
        ORDER BY created_at DESC
        LIMIT 10
    """)

    stripe_txs = cursor.fetchall()
    if stripe_txs:
        print(f"{'Status':<10} {'Amount':<10} {'Pair':<12} {'Date':<20}")
        print("-" * 55)
        for tx_id, amount, fiat, crypto, status, created, desc in stripe_txs:
            pair = f"{fiat}→{crypto}"
            date_short = created[:10] if created else "N/A"
            status_emoji = "❌" if status == "failed" else ("⏳" if status == "pending" else "✅")
            print(f"{status_emoji} {status:<8} ${amount:<9.2f} {pair:<12} {date_short}")

        # Failed transactions detail
        cursor.execute("""
            SELECT id, amount, webhook_data FROM payments
            WHERE provider='stripe' AND status='failed'
        """)

        failed = cursor.fetchall()
        if failed:
            print(f"\n{len(failed)} FAILED TRANSACTIONS:\n")
            for tx_id, amount, webhook_data in failed:
                print(f"  ID: {tx_id}")
                print(f"  Amount: ${amount}")
                if webhook_data:
                    print(f"  Error data: {webhook_data[:100]}...")
                print()

    # Pending transactions
    print_header("PENDING TRANSACTIONS (Awaiting Webhook)")

    cursor.execute("""
        SELECT id, provider, amount, fiat_currency, crypto_currency, created_at
        FROM payments
        WHERE status='pending'
        ORDER BY created_at DESC
    """)

    pending_txs = cursor.fetchall()
    if pending_txs:
        print(f"{'Provider':<12} {'Amount':<10} {'Pair':<12} {'Waiting Since'}")
        print("-" * 55)
        for tx_id, provider, amount, fiat, crypto, created in pending_txs:
            pair = f"{fiat}→{crypto}"
            print(f"{provider:<12} ${amount:<9.2f} {pair:<12} {created[:10]}")
    else:
        print("  (No pending transactions)")

    # Gateway registrations
    print_header("GATEWAY REGISTRATIONS")

    cursor.execute("""
        SELECT gateway_name, registration_status, account_status, verification_level
        FROM gateway_registrations
        ORDER BY updated_at DESC
    """)

    registrations = cursor.fetchall()
    if registrations:
        print(f"{'Gateway':<15} {'Status':<15} {'Account':<15} {'Verification'}")
        print("-" * 60)
        for gw, reg_status, acc_status, ver_level in registrations:
            print(f"{gw:<15} {reg_status:<15} {acc_status or 'N/A':<15} {ver_level or 0}")
    else:
        print("  (No registrations yet)")

    # Summary
    print_header("SUMMARY")

    cursor.execute("""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN status='completed' THEN 1 ELSE 0 END) as completed,
            SUM(CASE WHEN status='pending' THEN 1 ELSE 0 END) as pending,
            SUM(CASE WHEN status='failed' THEN 1 ELSE 0 END) as failed,
            SUM(amount) as total_usd
        FROM payments
        WHERE created_at > ?
    """, (since_str,))

    total, completed, pending, failed, total_usd = cursor.fetchone()
    print(f"Total Transactions: {total}")
    print(f"  ✅ Completed: {completed}")
    print(f"  ⏳ Pending: {pending}")
    print(f"  ❌ Failed: {failed}")
    print(f"Total Volume: ${total_usd or 0:.2f} USD")

    success_rate = (completed / total * 100) if total > 0 else 0
    print(f"Success Rate: {success_rate:.1f}%")

    db.close()

if __name__ == "__main__":
    try:
        days = int(sys.argv[1]) if len(sys.argv) > 1 else 30
        dashboard(days)
    except KeyboardInterrupt:
        print("\n\nCancelled")
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

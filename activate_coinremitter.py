#!/usr/bin/env python3
"""
CoinRemitter activation + smoke test.

Run after pasting COINREMITTER_API_KEY / COINREMITTER_API_PASSWORD into .env.
Verifies credentials by:
  1. Fetching wallet balance for the configured coin
  2. Creating a $30 USD test invoice (no payment required)
  3. Printing the hosted checkout URL for visual inspection

Usage:
    cd /home/kali/payment-gateway && python3 activate_coinremitter.py
"""
import asyncio
import json
import sys
import uuid

from providers.coinremitter import CoinRemitterProvider
from config import (
    COINREMITTER_API_KEY,
    COINREMITTER_API_PASSWORD,
    COINREMITTER_COIN,
    BASE_URL,
)


def _preflight() -> bool:
    if not COINREMITTER_API_KEY or COINREMITTER_API_KEY.startswith("YOUR_"):
        print("[FAIL] COINREMITTER_API_KEY missing in .env")
        print("       Get it from https://coinremitter.com/coins → select wallet → API tab")
        return False
    if not COINREMITTER_API_PASSWORD or COINREMITTER_API_PASSWORD.startswith("YOUR_"):
        print("[FAIL] COINREMITTER_API_PASSWORD missing in .env")
        print("       This is the WALLET PASSWORD set during wallet creation (not your account password)")
        return False
    return True


async def main():
    print("=" * 60)
    print("CoinRemitter Activation")
    print("=" * 60)
    print(f"Coin     : {COINREMITTER_COIN}")
    print(f"BASE_URL : {BASE_URL}")
    print(f"API key  : {COINREMITTER_API_KEY[:8]}...{COINREMITTER_API_KEY[-4:]}")
    print()

    if not _preflight():
        sys.exit(1)

    provider = CoinRemitterProvider()

    # Step 1 — balance check (also validates credentials)
    print("[1/2] Fetching wallet balance ...")
    try:
        balance = await provider.get_balance()
        if balance.get("flag") == 1:
            data = balance.get("data", {})
            print(f"      OK — balance: {data.get('balance', 'n/a')} {COINREMITTER_COIN}")
        else:
            print(f"      FAIL — {balance.get('msg', 'unknown error')}")
            print(f"      Full response: {json.dumps(balance, indent=2)}")
            sys.exit(2)
    except Exception as e:
        print(f"      ERROR — {type(e).__name__}: {e}")
        sys.exit(3)

    # Step 2 — create a $30 USD test invoice
    print("[2/2] Creating $30 USD test invoice ...")
    test_payment = {
        "id":              str(uuid.uuid4()),
        "amount":          30,
        "fiat_currency":   "USD",
        "crypto_currency": COINREMITTER_COIN,
        "description":     "BeastPay CoinRemitter smoke test",
        "link_id":         "test",
    }
    try:
        invoice = await provider.create_invoice(test_payment)
        if invoice.get("flag") == 1:
            data = invoice.get("data", {})
            print(f"      OK — invoice_id: {data.get('invoice_id')}")
            print(f"      Checkout URL : {data.get('url')}")
            print(f"      Pay address  : {data.get('address')}")
            print(f"      Amount       : {data.get('amount')} {COINREMITTER_COIN}")
            print()
            print("Open the checkout URL in a browser to verify the invoice loads.")
            print("(No need to actually pay — leaving it unpaid is fine; it expires in 1 hour.)")
        else:
            print(f"      FAIL — {invoice.get('msg', 'unknown error')}")
            print(f"      Full response: {json.dumps(invoice, indent=2)}")
            sys.exit(4)
    except Exception as e:
        print(f"      ERROR — {type(e).__name__}: {e}")
        sys.exit(5)

    print()
    print("CoinRemitter is LIVE. Restart uvicorn to pick up the credentials.")


if __name__ == "__main__":
    asyncio.run(main())

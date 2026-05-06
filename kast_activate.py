#!/usr/bin/env python3
"""
KAST Pay Provider Activation Script
Activates KAST (instant USDC settlement, 1.5% fee, $500 no-KYC limit)

Usage:
  python3 kast_activate.py API_KEY SECRET
  python3 kast_activate.py  (interactive)
"""

import sys
import os
from pathlib import Path
from dotenv import load_dotenv, set_key

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
load_dotenv()

ENV_FILE = Path(__file__).parent / ".env"

PROVIDER_INFO = {
    "name": "KAST Pay",
    "type": "fiat-to-crypto",
    "fee": "1.5%",
    "settlement": "5 min",
    "no_kyc_limit": "$500 USD",
    "email_kyc_limit": "$25k USD",
    "full_kyc_limit": "$100k USD",
    "currencies": "USD, EUR, GBP",
    "description": "Instant USDC settlement with zero-KYC up to $500, USD banking rails",
    "docs": "https://docs.kast.pay",
    "support": "api@kast.pay",
}

def print_header():
    print("\n" + "="*70)
    print(f"  {PROVIDER_INFO['name'].upper()} ACTIVATION")
    print("="*70)
    print(f"  Type:              {PROVIDER_INFO['type']}")
    print(f"  Fee:               {PROVIDER_INFO['fee']}")
    print(f"  Settlement:        {PROVIDER_INFO['settlement']}")
    print(f"  No-KYC Limit:      {PROVIDER_INFO['no_kyc_limit']}")
    print(f"  Email-KYC Limit:   {PROVIDER_INFO['email_kyc_limit']}")
    print(f"  Full-KYC Limit:    {PROVIDER_INFO['full_kyc_limit']}")
    print(f"  Currencies:        {PROVIDER_INFO['currencies']}")
    print(f"  Docs:              {PROVIDER_INFO['docs']}")
    print("="*70 + "\n")

def get_keys_interactive():
    """Prompt user for KAST API credentials."""
    print("Enter your KAST API credentials (get from https://dashboard.kast.pay)")
    api_key = input("  KAST_API_KEY: ").strip()
    if not api_key:
        print("  ❌ Activation cancelled")
        return None

    secret = input("  KAST_SECRET: ").strip()
    if not secret:
        print("  ❌ Activation cancelled")
        return None

    return {"api_key": api_key, "secret": secret}

def activate(api_key: str, secret: str):
    """Write KAST credentials to .env and validate."""
    print(f"\n📝 Writing credentials to {ENV_FILE}...")

    # Update .env file
    set_key(str(ENV_FILE), "KAST_API_KEY", api_key)
    set_key(str(ENV_FILE), "KAST_SECRET", secret)
    set_key(str(ENV_FILE), "KAST_ENV", "production")

    print("✅ Credentials written successfully")
    print(f"   KAST_API_KEY=***")
    print(f"   KAST_SECRET=***")
    print(f"   KAST_ENV=production")

    # Verify configuration
    print("\n🔍 Verifying configuration...")
    try:
        from config import KAST_API_KEY, KAST_ENV
        if KAST_API_KEY and KAST_ENV.lower() == "production":
            print("✅ KAST is now LIVE and ready to process transactions")
            print("\n📊 Next steps:")
            print("   1. Test with POST /v1/payments/create?provider=kast")
            print("   2. Monitor transactions at https://dashboard.kast.pay")
            print("   3. Set up webhook for payment confirmations")
            print("   4. Enable KAST in your checkout flow")
            return True
        else:
            print("⚠️  Configuration incomplete")
            return False
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return False

def main():
    print_header()

    if len(sys.argv) == 3:
        # Command line: kast_activate.py API_KEY SECRET
        api_key = sys.argv[1]
        secret = sys.argv[2]
    elif len(sys.argv) == 1:
        # Interactive
        creds = get_keys_interactive()
        if not creds:
            sys.exit(1)
        api_key = creds["api_key"]
        secret = creds["secret"]
    else:
        print(f"Usage: python3 kast_activate.py [API_KEY SECRET]")
        sys.exit(1)

    success = activate(api_key, secret)
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()

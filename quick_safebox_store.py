#!/usr/bin/env python3
"""
QUICK SAFEBOX STORAGE
Paste your Stripe API key → Automatically encrypted and stored
"""

import os
import sys
import getpass
from datetime import datetime
from pathlib import Path

def store_api_key_in_safebox(api_key: str) -> dict:
    """Store API key in SafeBox"""

    try:
        from subagents.ecosystem_bridge import EcosystemBridge, ApiCredential
        from cryptography.fernet import Fernet

        print()
        print("🔐 SAFEBOX STORAGE")
        print("=" * 70)

        # Ensure encryption key exists (do not print it to the console)
        key = os.getenv("CREDENTIAL_ENCRYPTION_KEY", "").strip()
        if not key:
            key = Fernet.generate_key().decode()
            os.environ["CREDENTIAL_ENCRYPTION_KEY"] = key

            # Persist locally with strict permissions (still sensitive)
            key_path = Path(".safebox_fernet.key")
            key_path.write_text(key + "\n", encoding="utf-8")
            try:
                os.chmod(key_path, 0o600)
            except Exception:
                pass

            print("🔑 Generated SafeBox encryption key (not shown).")
            print("   Saved to: .safebox_fernet.key (keep this file secret)")
            print("   Tip: You can also set CREDENTIAL_ENCRYPTION_KEY in your shell/.env")
            print()

        # Initialize bridge
        bridge = EcosystemBridge()

        # Create credential
        credential = ApiCredential(
            service_name="stripe",
            api_key=api_key,
            provider="stripe",
            endpoint="https://api.stripe.com",
            created_at=datetime.now().isoformat()
        )

        # Store in vault
        result = bridge.vault.store(credential)

        if result.get("status") == "stored":
            print("✅ SUCCESS!")
            print("=" * 70)
            print()
            print(f"✓ API key stored in SafeBox (encrypted)")
            print(f"  Service: stripe")
            print(f"  Key: {api_key[:4]}***{api_key[-4:]}")
            print(f"  Stored: {result.get('timestamp')}")
            print()

            # Show vault contents
            creds = bridge.vault.list_credentials()
            print(f"SafeBox Contents ({len(creds)} credential):")
            for c in creds:
                print(f"  • {c['service']}: {c['key_masked']}")
            print()

            return {
                "status": "success",
                "key_masked": f"{api_key[:4]}***{api_key[-4:]}",
                "encryption_key": key
            }
        else:
            print("✗ Failed to store")
            return {"status": "failed"}

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return {"status": "error", "error": str(e)}


def main():
    """Main"""
    print()
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 68 + "║")
    print("║" + "  💾 QUICK SAFEBOX STORAGE".center(68) + "║")
    print("║" + "  Paste Stripe API key → Store encrypted".center(68) + "║")
    print("║" + " " * 68 + "║")
    print("╚" + "=" * 68 + "╝")
    print()

    print("📌 TO GET YOUR STRIPE API KEY:")
    print("  1. Go to: https://dashboard.stripe.com/apikeys")
    print("  2. Click 'Reveal' next to Secret key")
    print("  3. Copy the full key (sk_live_...)")
    print()

    api_key = getpass.getpass("🔑 Paste your Stripe API key (input hidden): ").strip()

    if not api_key:
        print("✗ No key provided")
        return 1

    if not (api_key.startswith("sk_live_") or api_key.startswith("sk_test_")):
        print("⚠️  Warning: Key doesn't look like a Stripe secret key (sk_live_ / sk_test_)")
        confirm = input("Continue anyway? (y/n): ").strip().lower()
        if confirm != "y":
            print("Cancelled")
            return 1

    # Store in SafeBox
    result = store_api_key_in_safebox(api_key)

    if result["status"] == "success":
        print("=" * 70)
        print("🎉 Your API key is now secure in SafeBox!")
        print()
        return 0
    else:
        print("✗ Storage failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())

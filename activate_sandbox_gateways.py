#!/usr/bin/env python3
"""
Sandbox/Test Gateway Activation
Activates all payment gateways with sandbox/test credentials.
Perfect for development and testing.

Run: python3 activate_sandbox_gateways.py
"""

import sys, os, uuid, json, sqlite3
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

PROFILE_ID = "fd8179d9-a881-47d4-9a14-3438527ea6a7"
ENV_FILE = Path(__file__).parent / ".env"
DB_PATH = Path(__file__).parent / "payments.db"

# Test/Sandbox credentials for all gateways
SANDBOX_CREDENTIALS = {
    "transak": {
        "TRANSAK_API_KEY": "sk_test_transak_12345678901234567890",
        "TRANSAK_SECRET": "secret_test_transak_abcdefghijklmnop",
        "TRANSAK_ACCESS_TOKEN": "access_test_transak_xyz123456789",
        "TRANSAK_ENV": "staging",
    },
    "guardarian": {
        "GUARDARIAN_API_KEY": "test_key_guardarian_12345678901234567890",
        "GUARDARIAN_ENV": "sandbox",
    },
    "ziina": {
        "ZIINA_API_TOKEN": "test_token_ziina_abcdefghijklmnopqrstuvwxyz",
        "ZIINA_WEBHOOK_SECRET": "test_webhook_ziina_xyz123456789",
        "ZIINA_ENV": "sandbox",
    },
    "moonpay": {
        "MOONPAY_API_KEY": "test_key_moonpay_12345678901234567890",
        "MOONPAY_SECRET": "test_secret_moonpay_abcdefghijklmnop",
        "MOONPAY_ENV": "sandbox",
    },
    "nowpayments": {
        "NOWPAYMENTS_API_KEY": "test_key_nowpayments_12345678901234567890",
        "NOWPAYMENTS_ENV": "sandbox",
    },
}


def update_env_file():
    """Write sandbox credentials to .env file."""
    with open(ENV_FILE, "r") as f:
        lines = f.readlines()

    new_lines = []
    # Keep existing lines that aren't gateway-related
    for line in lines:
        skip = False
        for gateway_creds in SANDBOX_CREDENTIALS.values():
            if any(line.startswith(f"{key}=") for key in gateway_creds.keys()):
                skip = True
                break
        if not skip:
            new_lines.append(line)

    # Append sandbox credentials
    new_lines.append("\n# SANDBOX/TEST GATEWAYS (Development Only)\n")
    for gateway_name, creds in SANDBOX_CREDENTIALS.items():
        new_lines.append(f"\n# {gateway_name.upper()}\n")
        for key, value in creds.items():
            new_lines.append(f"{key}={value}\n")

    with open(ENV_FILE, "w") as f:
        f.writelines(new_lines)

    print(f"✓ Updated .env with sandbox credentials")


def store_credentials_in_db():
    """Encrypt and store all gateway credentials."""
    from verification.encryption import encrypt_credential
    from config import CREDENTIAL_ENCRYPTION_KEY

    enc_key = CREDENTIAL_ENCRYPTION_KEY
    now = datetime.utcnow().isoformat()

    conn = sqlite3.connect(DB_PATH)
    activated_count = 0

    for gateway_name, creds in SANDBOX_CREDENTIALS.items():
        try:
            # Prepare encrypted credentials
            enc_creds = {}
            for k, v in creds.items():
                if not k.endswith("_ENV"):
                    enc_creds[k] = encrypt_credential(v, enc_key)

            existing = conn.execute(
                "SELECT id FROM gateway_credentials WHERE merchant_profile_id=? AND gateway_name=?",
                (PROFILE_ID, gateway_name),
            ).fetchone()

            additional = json.dumps({
                "env": creds.get(f"{gateway_name.upper()}_ENV", "sandbox"),
                "mode": "TEST",
                "keys_masked": {k: "test_***" for k in enc_creds.keys()},
            })

            if existing:
                conn.execute(
                    """UPDATE gateway_credentials
                       SET encrypted_api_key=?, encrypted_secret=?, additional_data=?,
                           is_active=1, updated_at=?
                       WHERE id=?""",
                    (
                        json.dumps(enc_creds),
                        json.dumps(enc_creds),
                        additional,
                        now,
                        existing[0],
                    ),
                )
            else:
                cred_id = str(uuid.uuid4())
                conn.execute(
                    """INSERT INTO gateway_credentials
                       (id, merchant_profile_id, gateway_name,
                        encrypted_api_key, encrypted_secret, additional_data, is_active, created_at, updated_at)
                       VALUES (?,?,?,?,?,?,1,?,?)""",
                    (
                        cred_id,
                        PROFILE_ID,
                        gateway_name,
                        json.dumps(enc_creds),
                        json.dumps(enc_creds),
                        additional,
                        now,
                        now,
                    ),
                )

            # Update gateway_registrations
            conn.execute(
                """UPDATE gateway_registrations
                   SET registration_status='registered', account_status='test',
                       verification_level=1, error_message=NULL, updated_at=?
                   WHERE merchant_profile_id=? AND gateway_name=?""",
                (now, PROFILE_ID, gateway_name),
            )

            activated_count += 1
            print(f"  ✓ {gateway_name:15} → SANDBOX")

        except Exception as e:
            print(f"  ✗ {gateway_name:15} → ERROR: {e}")

    conn.commit()
    conn.close()

    return activated_count


def main():
    print("\n" + "="*60)
    print("  SANDBOX GATEWAY ACTIVATION")
    print("="*60)

    try:
        print("\n[1/2] Updating .env with test credentials...")
        update_env_file()

        print("[2/2] Storing encrypted credentials in database...")
        activated = store_credentials_in_db()

        print("\n" + "="*60)
        print(f"  ✅ ACTIVATION COMPLETE")
        print("="*60)
        print(f"\n  Gateways activated: {activated}/{len(SANDBOX_CREDENTIALS)}")
        print(f"\n  Test Gateways Ready:")
        print(f"  • Transak (Staging)")
        print(f"  • Guardarian (Sandbox)")
        print(f"  • Ziina (Sandbox)")
        print(f"  • MoonPay (Sandbox)")
        print(f"  • NOWPayments (Sandbox)")
        print(f"\n  ⚠️  WARNING: These are TEST credentials only!")
        print(f"  DO NOT use in production. Real payments will FAIL.")
        print(f"\n  Next: source .env && python3 -m uvicorn server:app")
        print("="*60 + "\n")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())

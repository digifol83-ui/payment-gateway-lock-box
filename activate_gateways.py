#!/usr/bin/env python3
"""
Multi-Gateway Activation Script
Activates multiple fiat-to-crypto providers at once.

Usage:
  python3 activate_gateways.py [--gateways transak,guardarian,ziina,moonpay,nowpayments]
  python3 activate_gateways.py --status
  python3 activate_gateways.py --all  (all available)
  python3 activate_gateways.py  (interactive)
"""

import sys, os, uuid, json, asyncio, sqlite3, secrets
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

PROFILE_ID = "fd8179d9-a881-47d4-9a14-3438527ea6a7"
ENV_FILE = Path(__file__).parent / ".env"
DB_PATH = Path(__file__).parent / "payments.db"

# Gateway metadata: (required_keys, description)
GATEWAYS = {
    "transak": {
        "keys": ["TRANSAK_API_KEY", "TRANSAK_SECRET", "TRANSAK_ACCESS_TOKEN"],
        "env_var": "TRANSAK_ENV",
        "desc": "Fiat→Crypto (UK, EU, US, India, Australia)",
    },
    "guardarian": {
        "keys": ["GUARDARIAN_API_KEY"],
        "env_var": "GUARDARIAN_ENV",
        "desc": "170+ countries, 1000+ cryptos, 30+ fiats",
    },
    "finchpay": {
        "keys": ["FINCHPAY_API_KEY", "FINCHPAY_SECRET_KEY"],
        "env_var": "FINCHPAY_ENV",
        "desc": "Fiat→Crypto (email-only KYC), backup provider",
    },
    "ziina": {
        "keys": ["ZIINA_API_TOKEN", "ZIINA_WEBHOOK_SECRET"],
        "env_var": "ZIINA_ENV",
        "desc": "UAE native AED payments (fast settlement)",
    },
    "stripe": {
        "keys": ["STRIPE_SECRET_KEY", "STRIPE_PUBLISHABLE_KEY", "STRIPE_WEBHOOK_SECRET"],
        "env_var": "STRIPE_ENV",
        "desc": "Card processor (use live keys for production)",
    },
    "moonpay": {
        "keys": ["MOONPAY_API_KEY", "MOONPAY_SECRET"],
        "env_var": "MOONPAY_ENV",
        "desc": "160+ countries, on/off-ramps",
    },
    "nowpayments": {
        "keys": ["NOWPAYMENTS_API_KEY"],
        "env_var": "NOWPAYMENTS_ENV",
        "desc": "Direct crypto payments (no KYC)",
    },
    "kast": {
        "keys": ["KAST_API_KEY", "KAST_SECRET"],
        "env_var": "KAST_ENV",
        "desc": "Instant USDC settlement (fast provider)",
    },
    "charge": {
        "keys": ["CHARGE_API_KEY", "CHARGE_SECRET"],
        "env_var": "CHARGE_ENV",
        "desc": "Card-to-crypto payment links (backup provider)",
    },
    "swapin": {
        "keys": ["SWAPIN_API_KEY", "SWAPIN_SECRET"],
        "env_var": "SWAPIN_ENV",
        "desc": "Fiat-to-crypto bridge (backup provider)",
    },
    "bleap": {
        "keys": ["BLEAP_API_KEY", "BLEAP_SECRET"],
        "env_var": "BLEAP_ENV",
        "desc": "Zero-fee USDC on-ramp (fast provider)",
    },
    "kyrrex": {
        "keys": ["KYRREX_API_KEY", "KYRREX_SECRET", "KYRREX_WEBHOOK_SECRET"],
        "env_var": "KYRREX_ENV",
        "desc": "Dubai-regulated fiat→crypto, AED native, 1.5% fee",
    },
    "banxa": {
        "keys": ["BANXA_API_KEY", "BANXA_SECRET", "BANXA_SUBDOMAIN"],
        "env_var": "BANXA_ENV",
        "desc": "Global on/off-ramp, 180+ countries, AED & USD, 2% fee",
    },
    "changelly": {
        "keys": ["CHANGELLY_API_KEY", "CHANGELLY_SECRET"],
        "env_var": "CHANGELLY_ENV",
        "desc": "Instant exchange, 500+ coins, card & bank, AED & USD, 1% fee",
    },
    "changenow": {
        "keys": ["CHANGENOW_API_KEY", "CHANGENOW_SECRET"],
        "env_var": "CHANGENOW_ENV",
        "desc": "Non-custodial, 1000+ coins, zero-KYC up to $1K, AED & USD, 0.5% fee",
    },
    "coinify": {
        "keys": ["COINIFY_API_KEY", "COINIFY_SECRET"],
        "env_var": "COINIFY_ENV",
        "desc": "Regulated EU processor, 100+ countries, AED & USD, 2.5% fee",
    },
}


def prompt_gateway_keys(gateway_name: str, gateway_info: dict) -> dict:
    """Prompt user for gateway API keys."""
    print(f"\n{'='*60}")
    print(f"  {gateway_name.upper()} — {gateway_info['desc']}")
    print(f"{'='*60}")

    keys_dict = {}
    for key_name in gateway_info["keys"]:
        value = input(f"  {key_name}: ").strip()
        if not value:
            print(f"    ❌ Skipping {gateway_name} (key not provided)")
            return None
        keys_dict[key_name] = value

    env_modes = ["production", "sandbox", "staging", "live", "test"]
    env_val = input(f"  {gateway_info['env_var']} ({'/'.join(env_modes)}) [production]: ").strip().lower() or "production"
    if env_val not in env_modes:
        env_val = "production"
    if env_val == "live":
        env_val = "production"

    keys_dict[gateway_info["env_var"]] = env_val
    return keys_dict


def update_env_file(gateway_name: str, keys_dict: dict):
    """Write gateway credentials to .env file."""
    if ENV_FILE.exists():
        with open(ENV_FILE, "r") as f:
            lines = f.readlines()
    else:
        lines = []

    new_lines = []
    for line in lines:
        is_this_gateway = any(
            line.startswith(f"{key}=") for key in keys_dict.keys()
        )
        if is_this_gateway:
            # Skip old value for this gateway
            continue
        new_lines.append(line)

    # Append new values
    new_lines.append("\n# " + gateway_name.upper() + "\n")
    for key, value in keys_dict.items():
        new_lines.append(f"{key}={value}\n")

    with open(ENV_FILE, "w") as f:
        f.writelines(new_lines)

    print(f"  ✓ Updated .env")


def ensure_encryption_key() -> str:
    """Ensure credentials are encrypted with a real 32-byte hex key."""
    from config import CREDENTIAL_ENCRYPTION_KEY

    key = (CREDENTIAL_ENCRYPTION_KEY or "").strip()
    is_hex_64 = len(key) == 64 and all(c in "0123456789abcdefABCDEF" for c in key)
    if is_hex_64:
        return key

    key = secrets.token_hex(32)
    update_env_file("SECURITY", {"CREDENTIAL_ENCRYPTION_KEY": key})
    print("  ✓ Generated CREDENTIAL_ENCRYPTION_KEY")
    return key


def store_credentials(gateway_name: str, keys_dict: dict):
    """Encrypt and store credentials in database."""
    from verification.encryption import encrypt_credential

    enc_key = ensure_encryption_key()
    now = datetime.utcnow().isoformat()

    # Prepare encrypted credentials (exclude env vars)
    enc_creds = {}
    for k, v in keys_dict.items():
        if k.endswith("_ENV"):
            continue
        enc_creds[k] = encrypt_credential(v, enc_key)

    conn = sqlite3.connect(DB_PATH)
    existing = conn.execute(
        "SELECT id FROM gateway_credentials WHERE merchant_profile_id=? AND gateway_name=?",
        (PROFILE_ID, gateway_name),
    ).fetchone()

    additional = json.dumps({
        "env": keys_dict.get(f"{gateway_name.upper()}_ENV", "sandbox"),
        "keys_masked": {k: v[:8] + "..." for k, v in keys_dict.items() if not k.endswith("_ENV")},
    })

    if existing:
        # Update existing
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
        # Create new
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
           SET registration_status='registered', account_status=?, verification_level=2,
               error_message=NULL, updated_at=?
           WHERE merchant_profile_id=? AND gateway_name=?""",
        (keys_dict.get(f"{gateway_name.upper()}_ENV", "sandbox"), now, PROFILE_ID, gateway_name),
    )

    conn.commit()
    conn.close()
    print(f"  ✓ Encrypted credentials in DB")


def print_status():
    """Show provider live/sandbox status without printing secrets."""
    from providers import provider_status_all

    print("\n" + "="*60)
    print("  GATEWAY STATUS")
    print("="*60)
    for row in provider_status_all():
        print(f"  {row['id']:15} {row['status']:16} {row['type']}")
    print("="*60 + "\n")


def main():
    print("\n" + "="*60)
    print("  MULTI-GATEWAY ACTIVATION — BeastPay")
    print("="*60)

    if "--status" in sys.argv or "status" in sys.argv:
        print_status()
        return

    # Determine which gateways to activate
    gateways_to_activate = []

    if "--all" in sys.argv:
        gateways_to_activate = list(GATEWAYS.keys())
    elif "--gateways" in sys.argv:
        idx = sys.argv.index("--gateways")
        gateways_to_activate = sys.argv[idx + 1].split(",")
    elif len(sys.argv) > 1:
        # Assume positional args are gateway names
        gateways_to_activate = sys.argv[1:]
    else:
        # Interactive mode
        print("\nAvailable gateways:")
        for i, (name, info) in enumerate(GATEWAYS.items(), 1):
            print(f"  [{i}] {name:15} — {info['desc']}")

        selection = input("\nEnter gateway names (comma-separated) or [all]: ").strip()
        if selection.lower() in ["all", "a", ""]:
            gateways_to_activate = list(GATEWAYS.keys())
        else:
            gateways_to_activate = [g.strip().lower() for g in selection.split(",")]

    # Filter to valid gateways
    gateways_to_activate = [g for g in gateways_to_activate if g in GATEWAYS]

    if not gateways_to_activate:
        print("  ❌ No valid gateways specified")
        return

    # Activate each gateway
    activated_count = 0
    for gateway_name in gateways_to_activate:
        gateway_info = GATEWAYS[gateway_name]

        keys_dict = prompt_gateway_keys(gateway_name, gateway_info)
        if not keys_dict:
            continue

        try:
            update_env_file(gateway_name, keys_dict)
            store_credentials(gateway_name, keys_dict)
            activated_count += 1
            print(f"  ✅ {gateway_name} activated")
        except Exception as e:
            print(f"  ❌ {gateway_name} failed: {e}")

    # Summary
    print(f"\n{'='*60}")
    print(f"  ACTIVATION COMPLETE")
    print(f"{'='*60}")
    print(f"  Gateways activated: {activated_count}/{len(gateways_to_activate)}")
    print(f"\n  Next: reload server with: source .env && python3 -m uvicorn server:app")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()

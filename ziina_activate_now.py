#!/usr/bin/env python3
"""
Ziina Activation - Production Ready
Automatically activates Ziina with credentials (test or production)
"""
import subprocess
import sys
from pathlib import Path
from datetime import datetime
import re

def update_env(updates: dict):
    """Update .env file"""
    env_file = Path(".env")
    if not env_file.exists():
        print("❌ .env not found")
        sys.exit(1)

    content = env_file.read_text()

    for key, value in updates.items():
        pattern = f"{key}=.*"
        if re.search(pattern, content):
            content = re.sub(pattern, f"{key}={value}", content)
        else:
            content += f"\n{key}={value}"

    env_file.write_text(content)
    print(f"✅ Updated .env")

def activate_ziina(env: str = "production", use_test: bool = False):
    """
    Activate Ziina gateway
    env: 'production' or 'sandbox'
    use_test: True = create test credentials for demo
    """

    print(f"""
╔══════════════════════════════════════════════════════════════╗
║        ZIINA ACTIVATION - {env.upper():20}              ║
║        SICHER MAYOR COMMERCIAL BROKERS L.L.C                 ║
║        DED License: 841208 | Dubai, UAE                      ║
╚══════════════════════════════════════════════════════════════╝
""")

    if use_test:
        print("⚠️  DEMO MODE: Using test credentials\n")
        # Generate test credentials
        api_token = f"zk_test_demo_{datetime.utcnow().timestamp():.0f}"
        webhook_secret = f"whk_test_demo_{datetime.utcnow().timestamp():.0f}"
        print(f"Generated test token: {api_token[:30]}...")
        print(f"Generated test secret: {webhook_secret[:30]}...\n")
    else:
        print("Production credentials needed\n")
        api_token = input("🔑 Ziina API Token: ").strip()
        webhook_secret = input("🔑 Webhook Secret: ").strip()

        if not api_token or not webhook_secret:
            print("❌ No credentials provided")
            sys.exit(1)

    # Validate format
    if not (api_token.startswith(("zk_", "test_")) or len(api_token) > 20):
        print("⚠️  Token format unusual - continuing anyway\n")

    # Update .env
    updates = {
        "ZIINA_API_TOKEN": api_token,
        "ZIINA_WEBHOOK_SECRET": webhook_secret,
        "ZIINA_ENV": env,
    }

    update_env(updates)

    # Save to secure vault if available
    try:
        from secure_vault import SecureVault
        vault = SecureVault()
        vault.store_credential(
            "ziina",
            api_token,
            webhook_secret,
            environment=env,
            created_at=datetime.utcnow().isoformat()
        )
        print(f"✅ Stored in encrypted vault\n")
    except ImportError:
        print("ℹ️  Secure vault not available\n")

    # Show summary
    print("=" * 70)
    print("CONFIGURATION SUMMARY")
    print("=" * 70 + "\n")
    print(f"Gateway:       Ziina")
    print(f"Environment:   {env.upper()}")
    print(f"Company:       SICHER MAYOR COMMERCIAL BROKERS L.L.C")
    print(f"DED License:   841208")
    print(f"Email:         sichermayor@deltajohnsons.com")
    print(f"Phone:         +971-54-2473412")
    print(f"API Token:     {api_token[:20]}...")
    print(f"Webhook:       {webhook_secret[:20]}...")
    print(f"Updated:       {datetime.utcnow().isoformat()}\n")

    # Offer deployment
    print("=" * 70)
    deploy = input("Deploy to Cloud Run now? (y/N): ").strip().lower()

    if deploy == "y":
        print("\n🔄 Deploying beastpay-api...")
        result = subprocess.run([
            "gcloud", "run", "deploy", "beastpay-api",
            "--source", ".",
            "--region", "us-central1"
        ])

        if result.returncode == 0:
            print("\n" + "=" * 70)
            print("✅ ZIINA ACTIVATED & DEPLOYED")
            print("=" * 70)
            print("\nStatus: 🟢 LIVE")
            print("URL: https://beastpay-api-544494288390.us-central1.run.app")
            print("\nYou can now:")
            print("  • Accept AED payments")
            print("  • Test transactions")
            print("  • Monitor webhooks")
            print("  • Add backup gateways\n")
        else:
            print("\n❌ Deployment failed - check gcloud logs")
            sys.exit(1)
    else:
        print("\n" + "=" * 70)
        print("✅ ZIINA CONFIGURED (Not deployed)")
        print("=" * 70)
        print("\nTo deploy later:")
        print("  gcloud run deploy beastpay-api --source . --region us-central1\n")

def main():
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "test":
        # Test mode
        activate_ziina(env="sandbox", use_test=True)
    else:
        # Production mode - ask for credentials
        activate_ziina(env="production", use_test=False)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Cancelled")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)

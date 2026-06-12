#!/usr/bin/env python3
"""
Ziina Production Activation Helper
Guides you through getting Ziina production credentials and updating .env
"""
import subprocess
import sys
import os
import re
from pathlib import Path

def read_env():
    """Read current .env file"""
    env_file = Path(".env")
    if not env_file.exists():
        print("❌ .env not found in current directory")
        sys.exit(1)
    with open(env_file) as f:
        return f.read()

def update_env(updates: dict):
    """Update .env with new values"""
    env_file = Path(".env")
    content = env_file.read_text()

    for key, value in updates.items():
        # Replace or add the line
        pattern = f"{key}=.*"
        if re.search(pattern, content):
            content = re.sub(pattern, f"{key}={value}", content)
        else:
            content += f"\n{key}={value}"

    env_file.write_text(content)
    print(f"✅ Updated .env with {len(updates)} keys")

def copy_to_clipboard(text: str):
    """Copy text to clipboard (works on Linux/Mac/WSL)"""
    try:
        if sys.platform == "darwin":
            subprocess.run(["pbcopy"], input=text.encode())
        elif sys.platform == "linux":
            subprocess.run(["xclip", "-selection", "clipboard"], input=text.encode())
        else:
            print(f"📋 Copy this manually: {text}")
            return
        print(f"✅ Copied to clipboard: {text[:50]}...")
    except Exception as e:
        print(f"⚠️  Could not copy (try manually): {e}")

def main():
    print("""
╔════════════════════════════════════════════════════════════════╗
║       Ziina Production Activation                              ║
║       UAE-native AED fiat-to-crypto gateway                    ║
╚════════════════════════════════════════════════════════════════╝
""")

    env_content = read_env()

    # Check current state
    if "ZIINA_ENV=production" in env_content:
        print("✅ Ziina is ALREADY in production mode")
        print("   (Check if you need to update the token/secret)")
    else:
        print("🔄 Ziina is currently in SANDBOX mode")

    print("\n📋 STEPS TO ACTIVATE ZIINA:\n")

    print("1. Log in to Ziina dashboard:")
    print("   🌐 https://dashboard.ziina.ae")
    dashboard_url = "https://dashboard.ziina.ae"
    copy_to_clipboard(dashboard_url)
    print()

    print("2. Navigate to: Settings → API Keys")
    print()

    print("3. Copy the following from 'Production' section:")
    print("   - API Token (starts with 'zk_' or similar)")
    print("   - Webhook Secret")
    print()

    # Get credentials from user
    print("=" * 60)
    api_token = input("📝 Paste Production API Token: ").strip()
    if not api_token:
        print("❌ No API token provided. Aborting.")
        sys.exit(1)

    webhook_secret = input("📝 Paste Production Webhook Secret: ").strip()
    if not webhook_secret:
        print("❌ No webhook secret provided. Aborting.")
        sys.exit(1)

    # Validate token format
    if not (api_token.startswith(("zk_", "live_", "prod_")) or len(api_token) > 20):
        print("⚠️  WARNING: Token doesn't look like a production Ziina token")
        confirm = input("Continue anyway? (y/N): ").strip().lower()
        if confirm != "y":
            sys.exit(0)

    print("\n" + "=" * 60)
    print("✅ Credentials look good!")
    print()

    # Prepare updates
    updates = {
        "ZIINA_API_TOKEN": api_token,
        "ZIINA_WEBHOOK_SECRET": webhook_secret,
        "ZIINA_ENV": "production",
    }

    print("Ready to update .env with:")
    for key, value in updates.items():
        display_value = f"{value[:20]}..." if len(value) > 20 else value
        print(f"  {key}={display_value}")
    print()

    # Confirm
    confirm = input("Update .env? (y/N): ").strip().lower()
    if confirm != "y":
        print("❌ Cancelled")
        sys.exit(0)

    update_env(updates)

    print("\n" + "=" * 60)
    print("🚀 NEXT STEPS:\n")
    print("1. Test locally:")
    print("   uvicorn server:app --reload\n")
    print("2. Deploy to Cloud Run:")
    print("   gcloud run deploy beastpay-api --source . --region us-central1\n")
    print("3. Verify in admin dashboard:")
    print("   GET https://beastpay-api-544494288390.us-central1.run.app/admin/providers\n")
    print("4. Test a small transaction in your app\n")
    print("✅ Ziina is now LIVE!")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Cancelled by user")
        sys.exit(0)

#!/usr/bin/env python3
"""
Transak Production Activation Helper
Guides you through pulling production keys and requesting AED support
"""
import subprocess
import sys
import os
import re
import webbrowser
from pathlib import Path

def read_env():
    """Read current .env file"""
    env_file = Path(".env")
    if not env_file.exists():
        print("❌ .env not found")
        sys.exit(1)
    return env_file.read_text()

def update_env(updates: dict):
    """Update .env with new values"""
    env_file = Path(".env")
    content = env_file.read_text()

    for key, value in updates.items():
        pattern = f"{key}=.*"
        if re.search(pattern, content):
            content = re.sub(pattern, f"{key}={value}", content)
        else:
            content += f"\n{key}={value}"

    env_file.write_text(content)
    print(f"✅ Updated .env with {len(updates)} keys")

def copy_to_clipboard(text: str):
    """Copy text to clipboard"""
    try:
        if sys.platform == "darwin":
            subprocess.run(["pbcopy"], input=text.encode())
        elif sys.platform == "linux":
            subprocess.run(["xclip", "-selection", "clipboard"], input=text.encode())
        else:
            print(f"📋 Copy manually: {text}")
            return
        print(f"✅ Copied: {text[:50]}...")
    except Exception as e:
        print(f"⚠️  Could not auto-copy: {e}")

def main():
    print("""
╔════════════════════════════════════════════════════════════════╗
║       Transak Production Activation                            ║
║       International fiat-to-crypto (AED not yet enabled)       ║
╚════════════════════════════════════════════════════════════════╝
""")

    env_content = read_env()

    # Check current state
    is_prod = "TRANSAK_ENV=production" in env_content
    if is_prod:
        print("✅ Transak is ALREADY in production mode\n")
    else:
        print("🔄 Transak is currently in STAGING mode\n")

    print("=" * 60)
    print("PART 1: GET PRODUCTION KEYS")
    print("=" * 60 + "\n")

    print("1️⃣  Open Transak dashboard:")
    print("   🌐 https://dashboard.transak.com/login\n")
    print("   Login email: sichermayor@deltajohnsons.com\n")

    # Offer to open browser
    try_open = input("Open browser? (y/N): ").strip().lower()
    if try_open == "y":
        webbrowser.open("https://dashboard.transak.com/login")
        print("✅ Browser opened")
    print()

    print("2️⃣  Navigate to: Settings → API → Production Keys")
    print("   (Make sure you're in PRODUCTION, not Staging)\n")

    print("3️⃣  Copy these values:")
    print("   • API Key (label: 'API Key' or 'API Secret')")
    print("   • Access Token (label: 'Access Token')\n")

    # Get credentials
    print("=" * 60)
    api_key = input("📝 Paste Production API Key: ").strip()
    if not api_key:
        print("❌ No API key provided")
        sys.exit(1)

    access_token = input("📝 Paste Production Access Token: ").strip()
    if not access_token:
        print("⚠️  Access token is optional (using API key as fallback)")
        access_token = api_key

    # Validate
    if api_key.startswith("sk_test_"):
        print("⚠️  ERROR: This looks like a TEST key, not PRODUCTION")
        print("   Make sure you copied from the 'Production' section")
        confirm = input("Use it anyway? (y/N): ").strip().lower()
        if confirm != "y":
            sys.exit(0)

    print("\n" + "=" * 60)
    print("PART 2: REQUEST AED SUPPORT")
    print("=" * 60 + "\n")

    print("⚠️  IMPORTANT: Transak doesn't support AED yet on your account\n")
    print("4️⃣  Request AED support via email:")
    print("   📧 To: partners@transak.com")
    print("   Subject: 'Enable AED support for merchant account'")
    print("   Body template:\n")

    aed_email = """Dear Transak Partners,

We would like to enable AED (United Arab Emirates Dirham) support for our merchant account
on Transak's platform. Our business operates in the UAE and AED is our primary settlement currency.

Business: SICHER MAYOR COMMERCIAL BROKERS L.L.C (DED License: 841208)
Dashboard Email: sichermayor@deltajohnsons.com

Please advise on:
1. Current availability of AED fiat currency for our account
2. Any additional KYC/compliance steps required
3. Timeline for enablement

Thank you,
Regards"""

    print(aed_email)
    print()

    email_copied = input("Copy email template to clipboard? (y/N): ").strip().lower()
    if email_copied == "y":
        copy_to_clipboard(aed_email)

    print("\n5️⃣  Open Transak Partners email:")
    email_link = "mailto:partners@transak.com?subject=Enable%20AED%20support"
    try:
        webbrowser.open(email_link)
        print("✅ Email client opened")
    except:
        print("📧 partners@transak.com")

    print("\n" + "=" * 60)
    print("PART 3: UPDATE .ENV AND DEPLOY")
    print("=" * 60 + "\n")

    updates = {
        "TRANSAK_API_KEY": api_key,
        "TRANSAK_ACCESS_TOKEN": access_token or api_key,
        "TRANSAK_ENV": "production",
    }

    print("Ready to update .env with:")
    for key, value in updates.items():
        display = f"{value[:20]}..." if len(value) > 20 else value
        print(f"  {key}={display}")
    print()

    confirm = input("Proceed? (y/N): ").strip().lower()
    if confirm != "y":
        print("❌ Cancelled")
        sys.exit(0)

    update_env(updates)

    print("\n" + "=" * 60)
    print("🚀 DEPLOYMENT")
    print("=" * 60 + "\n")

    print("Deploy to production:")
    print("  gcloud run deploy beastpay-api --source . --region us-central1\n")

    deploy_now = input("Deploy now? (y/N): ").strip().lower()
    if deploy_now == "y":
        print("\n🔄 Deploying...")
        result = subprocess.run([
            "gcloud", "run", "deploy", "beastpay-api",
            "--source", ".",
            "--region", "us-central1"
        ])
        if result.returncode == 0:
            print("\n✅ Deployment successful!")
        else:
            print("\n❌ Deployment failed")
            sys.exit(1)

    print("\n" + "=" * 60)
    print("✅ NEXT STEPS")
    print("=" * 60 + "\n")
    print("1. ✅ Production keys updated")
    print("2. ⏳ AED support request pending (1–3 business days)")
    print("3. 🧪 Test Transak checkout:")
    print("     https://beastpay-api-544494288390.us-central1.run.app/buy\n")
    print("4. 📊 Monitor in Transak dashboard for transactions")
    print("5. ⏳ Once AED is enabled, AED payments will work automatically")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Cancelled")
        sys.exit(0)

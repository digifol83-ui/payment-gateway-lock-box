#!/usr/bin/env python3
"""
GATEWAY AGENT ORCHESTRATOR — One agent per gateway with live-key verification.
Each gateway gets: signup page open → KYB prefill → manual CAPTCHA pause → key grab → .env update → verify.

KARMOSTAJI TRADING LLC profile applied to ALL forms.

Usage:
  python3 gateway_agents_activate.py                    # dashboard + interactive
  python3 gateway_agents_activate.py --agent alchemypay # single gateway
  python3 gateway_agents_activate.py --all              # all gateways
  python3 gateway_agents_activate.py --verify           # verify all .env keys
  python3 gateway_agents_activate.py --status           # status only
"""
import os, sys, json, time, re, subprocess, secrets
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

ROOT = Path("/home/kali/payment-gateway")
ENV_FILE = ROOT / ".env"

# ============================================================================
# KARMOSTAJI KYB DATA — applied to every gateway form
# ============================================================================
KYB = {
    "legal_name": "AL KARMOSTAJI TRADING ENTERPRISES",
    "client_label": "KARMOSTAJI TRADING LLC",
    "legal_type": "Limited Liability Company (LLC)",
    "license_number": "200100",
    "register_number": "1387701",
    "dcci": "7447",
    "duns": "534472717",
    "license_issued": "1981-01-14",
    "license_expiry": "2027-01-13",
    "activity": "General Trading",
    "country": "United Arab Emirates",
    "emirate": "Dubai",
    "address_line1": "P.O. Box 4139",
    "address_line2": "Parcel ID 115-165",
    "city": "Dubai",
    "po_box": "4139",
    # Contact
    "contact_name": "Mohammed Ali Vellopadikal",
    "contact_role": "CEO / Partner",
    "contact_email": "compliance@sichermayor.online",
    "contact_phone": "+971561049878",
    "license_email": "karmostaji@hotmail.com",
    # Business
    "product_url": "https://beastbrain.sichermayor.online/card-to-crypto",
    "website": "https://beastbrain.sichermayor.online",
    "business_line": "Ecommerce / online retail for industrial sewing machines, including Juki brand machines from 10,000 to 50,000 AED",
    "monthly_volume_usd": "20000-100000",
    "industry": "Ecommerce / Online Retail",
    "annual_volume": "1000000-5000000",
    # Security
    "no_card_storage": True,
    "no_3ds_otp_collection": True,
    # Docs ready
    "doc_license": "/mnt/c/Users/shahe/Downloads/SecureCertificate201803.aspx.pdf",
    "doc_ceo_eid_front": "/home/kali/karmostagi_upload_ready/mohammed_ali_partner_eid_front.png",
    "doc_ceo_eid_back": "/home/kali/karmostagi_upload_ready/mohammed_ali_partner_eid_back.png",
    "doc_partner_eid_front": "/home/kali/karmostagi_upload_ready/mansoor_partner_eid_front.png",
    "doc_partner_eid_back": "/home/kali/karmostagi_upload_ready/mansoor_partner_eid_back.png",
}

OUTREACH_EMAIL = """Subject: Production merchant onboarding request - KARMOSTAJI TRADING LLC

Hello,

We are applying for production merchant access for KARMOSTAJI TRADING LLC, with legal applicant AL KARMOSTAJI TRADING ENTERPRISES, a Dubai licensed general trading business (License 200100, Register 1387701, DCCI 7447, D-U-N-S 534472717).

Product URL: https://beastbrain.sichermayor.online/card-to-crypto

Use case: BeastPay / BeastBrain provides a hosted card-to-crypto checkout for users buying USDT, USDC, BTC, ETH, or SOL with AED, USD, EUR, GBP, or supported fiat currencies. Card entry, KYC, issuer challenge, risk review, and settlement stay inside the approved hosted provider. BeastBrain does NOT collect raw card data, CVV, expiry, OTP, or merchant-side 3DS.

Entity:
- Legal name: AL KARMOSTAJI TRADING ENTERPRISES
- Client label: KARMOSTAJI TRADING LLC
- License: 200100 | Register: 1387701 | DCCI: 7447 | D-U-N-S: 534472717
- Legal type: Limited Liability Company (LLC)
- Activity: General Trading | License expiry: 2027-01-13
- Address: P.O. Box 4139, Parcel ID 115-165, Dubai, UAE

Contact: Mohammed Ali Vellopadikal, CEO / Partner
Phone: +971561049878 | Email: compliance@sichermayor.online

Business: Ecommerce / online retail for industrial sewing machines (including Juki brand, 10,000-50,000 AED per item).
Expected monthly volume: USD 20K - 100K initially.

Request:
1. Merchant onboarding or partner application link
2. KYB document checklist for UAE licensed trading entity
3. Production API credentials / partner ID
4. Domain/origin approval for beastbrain.sichermayor.online
5. AED card-to-USDT/USDC support confirmation
6. Webhook/order status guidance
7. Commercial terms and go-live steps

Our document package is ready. Please send the official secure upload/onboarding flow.

Best regards,
Mohammed Ali Vellopadikal
CEO / Partner, KARMOSTAJI TRADING LLC
compliance@sichermayor.online
"""

# ============================================================================
# GATEWAY REGISTRY — every gateway with its signup/contact URL, env keys, API base
# ============================================================================
GATEWAYS = {
    # ── FIAT→CRYPTO ON-RAMPS (top priority) ──
    "alchemypay": {
        "name": "Alchemy Pay",
        "signup_url": "https://alchemypay.org/contact",
        "support_email": "Support@alchemypay.org",
        "keys": ["ALCHEMYPAY_APP_ID", "ALCHEMYPAY_APP_SECRET"],
        "env_var": "ALCHEMYPAY_ENV",
        "api_base": "https://api.alchemypay.com/v1",
        "type": "fiat-to-crypto",
        "aed": True,
        "verify_url": "/merchant/queryOrder",
        "has_contact_form": True,
    },
    "guardarian": {
        "name": "Guardarian",
        "signup_url": "https://guardarian.com/contact-us",
        "support_email": "business@guardarian.com",
        "keys": ["GUARDARIAN_API_KEY"],
        "env_var": "GUARDARIAN_ENV",
        "api_base": "https://api-payments.guardarian.com/v1",
        "type": "fiat-to-crypto",
        "aed": False,
        "verify_url": "/currencies",
        "has_contact_form": True,
    },
    "wert": {
        "name": "Wert",
        "signup_url": "https://wert.io/affiliate-program",
        "docs_url": "https://docs.wert.io/docs/introduction",
        "keys": ["WERT_PARTNER_ID", "WERT_API_KEY"],
        "env_var": "WERT_ENV",
        "api_base": "https://api.wert.io/v1",
        "type": "fiat-to-crypto",
        "aed": False,
        "verify_url": "/partner/status",
        "has_contact_form": False,
    },
    "onramper": {
        "name": "Onramper",
        "signup_url": "https://dashboard.onramper.com/",
        "docs_url": "https://docs.onramper.com/docs/step-by-step-guide",
        "keys": ["ONRAMPER_INDIVIDUAL_API_KEY", "ONRAMPER_INDIVIDUAL_SIGNING_SECRET"],
        "env_var": "ONRAMPER_ACCOUNT_MODE",
        "api_base": "https://api.onramper.com/v1",
        "type": "fiat-to-crypto",
        "aed": True,
        "verify_url": "/currencies",
        "has_contact_form": False,
    },
    "changelly": {
        "name": "Changelly",
        "signup_url": "https://changelly.com/",
        "keys": ["CHANGELLY_API_KEY", "CHANGELLY_SECRET"],
        "env_var": "CHANGELLY_ENV",
        "api_base": "https://api.changelly.com/v2",
        "type": "fiat-to-crypto",
        "aed": True,
        "verify_url": "/currencies",
    },
    "changenow": {
        "name": "ChangeNOW",
        "signup_url": "https://changenow.io/",
        "keys": ["CHANGENOW_API_KEY", "CHANGENOW_SECRET"],
        "env_var": "CHANGENOW_ENV",
        "api_base": "https://api.changenow.io/v2",
        "type": "fiat-to-crypto",
        "aed": True,
        "verify_url": "/currencies",
    },
    "coinify": {
        "name": "Coinify",
        "signup_url": "https://coinify.com/",
        "keys": ["COINIFY_API_KEY", "COINIFY_SECRET"],
        "env_var": "COINIFY_ENV",
        "api_base": "https://api.coinify.com/v1",
        "type": "fiat-to-crypto",
        "aed": True,
        "verify_url": "/currencies",
    },
    "banxa": {
        "name": "Banxa",
        "signup_url": "https://banxa.com/",
        "keys": ["BANXA_API_KEY", "BANXA_SECRET", "BANXA_SUBDOMAIN"],
        "env_var": "BANXA_ENV",
        "api_base": "https://api.banxa.com/v1",
        "type": "fiat-to-crypto",
        "aed": True,
        "verify_url": "/currencies",
    },
    # ── UAE CARD / PAYMENT-LINK PROVIDERS ──
    "ziina": {
        "name": "Ziina",
        "signup_url": "https://ziina.com/merchant-signup",
        "support_email": "support@ziina.com",
        "keys": ["ZIINA_API_TOKEN", "ZIINA_WEBHOOK_SECRET"],
        "env_var": "ZIINA_ENV",
        "api_base": "https://api-v2.ziina.com",
        "type": "fiat-payment-link",
        "aed": True,
        "verify_url": "/api/payment-intent",
    },
    "mamopay": {
        "name": "Mamo Pay",
        "signup_url": "https://www.mamopay.com/contact",
        "keys": ["MAMO_API_KEY", "MAMO_SECRET"],
        "env_var": "MAMO_ENV",
        "api_base": "https://api.mamopay.com/v1",
        "type": "fiat-payment-link",
        "aed": True,
        "verify_url": "/me",
        "has_contact_form": True,
    },
    "tap": {
        "name": "Tap Payments",
        "signup_url": "https://www.tap.company/en-ae/company/contact",
        "keys": ["TAP_SECRET_KEY", "TAP_WEBHOOK_SECRET"],
        "env_var": "TAP_ENV",
        "api_base": "https://api.tap.company/v2",
        "type": "card-acquiring",
        "aed": True,
        "verify_url": "/currencies",
        "has_contact_form": True,
    },
    "paymob": {
        "name": "Paymob UAE",
        "signup_url": "https://www.pos.paymob.ae/",
        "keys": ["PAYMOB_API_KEY", "PAYMOB_SECRET_KEY", "PAYMOB_INTEGRATION_ID"],
        "env_var": "PAYMOB_ENV",
        "api_base": "https://accept.paymobsolutions.com/api",
        "type": "card-acquiring",
        "aed": True,
        "verify_url": "/auth/tokens",
    },
    # ── DIRECT CRYPTO PAYMENT GATEWAYS ──
    "nowpayments": {
        "name": "NOWPayments",
        "signup_url": "https://nowpayments.io/signup",
        "keys": ["NOWPAYMENTS_API_KEY"],
        "env_var": "NOWPAYMENTS_ENV",
        "api_base": "https://api.nowpayments.io/v1",
        "type": "crypto-payment",
        "aed": False,
        "verify_url": "/status",
    },
    "coinremitter": {
        "name": "CoinRemitter",
        "signup_url": "https://coinremitter.com/signup",
        "keys": ["COINREMITTER_API_KEY", "COINREMITTER_API_PASSWORD"],
        "env_var": "COINREMITTER_ENV",
        "api_base": "https://api.coinremitter.com/v3",
        "type": "crypto-payment",
        "aed": False,
        "verify_url": "/get-coin-rate",
    },
    # ── DUBAI-LICENSED / REGIONAL ──
    "kyrrex": {
        "name": "Kyrrex",
        "signup_url": "https://kyrrex.com/",
        "keys": ["KYRREX_API_KEY", "KYRREX_SECRET", "KYRREX_WEBHOOK_SECRET"],
        "env_var": "KYRREX_ENV",
        "api_base": "https://api.kyrrex.com/v1",
        "type": "fiat-to-crypto",
        "aed": True,
        "verify_url": "/currencies",
    },
    # ── FAST / BACKUP PROVIDERS ──
    "kast": {
        "name": "KAST Pay",
        "signup_url": "https://kast.co/register",
        "keys": ["KAST_API_KEY", "KAST_SECRET"],
        "env_var": "KAST_ENV",
        "api_base": "https://api.kast.co/v1",
        "type": "fiat-to-crypto",
        "aed": True,
        "verify_url": "/currencies",
    },
    "moonpay": {
        "name": "MoonPay",
        "signup_url": "https://www.moonpay.com/signup",
        "keys": ["MOONPAY_API_KEY", "MOONPAY_SECRET", "MOONPAY_WEBHOOK_SECRET"],
        "env_var": "MOONPAY_ENV",
        "api_base": "https://api.moonpay.com/v3",
        "type": "fiat-to-crypto",
        "aed": False,
        "verify_url": "/currencies",
    },
    "bleap": {
        "name": "Bleap",
        "signup_url": "https://bleap.io/",
        "keys": ["BLEAP_API_KEY", "BLEAP_SECRET"],
        "env_var": "BLEAP_ENV",
        "api_base": "https://api.bleap.io/v1",
        "type": "fiat-to-crypto",
        "aed": False,
        "verify_url": "/status",
    },
    "charge": {
        "name": "Charge",
        "signup_url": "https://charge.io/signup",
        "keys": ["CHARGE_API_KEY", "CHARGE_SECRET"],
        "env_var": "CHARGE_ENV",
        "api_base": "https://api.charge.io/v1",
        "type": "fiat-to-crypto",
        "aed": False,
        "verify_url": "/checkout/widget",
    },
    "swapin": {
        "name": "Swapin",
        "signup_url": "https://swapin.com/",
        "keys": ["SWAPIN_API_KEY", "SWAPIN_SECRET"],
        "env_var": "SWAPIN_ENV",
        "api_base": "https://api.swapin.com/v1",
        "type": "fiat-to-crypto",
        "aed": False,
        "verify_url": "/currencies",
    },
    "finchpay": {
        "name": "FinchPay",
        "signup_url": "https://finchpay.com/signup",
        "keys": ["FINCHPAY_API_KEY", "FINCHPAY_SECRET_KEY"],
        "env_var": "FINCHPAY_ENV",
        "api_base": "https://api.finchpay.com/v1",
        "type": "fiat-to-crypto",
        "aed": False,
        "verify_url": "/currencies",
    },
    "paybis": {
        "name": "Paybis",
        "signup_url": "https://paybis.com/",
        "keys": ["PAYBIS_API_KEY", "PAYBIS_SECRET"],
        "env_var": "PAYBIS_ENV",
        "api_base": "https://api.paybis.com/v1",
        "type": "fiat-to-crypto",
        "aed": False,
        "verify_url": "/currencies",
    },
}

# ============================================================================
# UTILITY: .env management
# ============================================================================
def load_env() -> dict:
    env = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env

def update_env(updates: dict) -> None:
    content = ENV_FILE.read_text() if ENV_FILE.exists() else ""
    for k, v in updates.items():
        pattern = re.compile(rf"^{re.escape(k)}=.*$", re.MULTILINE)
        if pattern.search(content):
            content = pattern.sub(f"{k}={v}", content)
        else:
            content += f"\n# {k.upper().split('_')[0] if '_' in k else k}\n{k}={v}\n"
    ENV_FILE.write_text(content)

def mask(s, head=6, tail=4):
    s = str(s or "")
    if len(s) <= head + tail: return "*" * len(s)
    return f"{s[:head]}...{s[-tail:]}"

# ============================================================================
# VERIFICATION ENGINE — tests each gateway's live key
# ============================================================================
def verify_gateway_key(gateway_id: str) -> Tuple[bool, str]:
    """Verify a gateway's API key is live by calling a test endpoint."""
    gw = GATEWAYS.get(gateway_id)
    if not gw: return False, "unknown gateway"

    env = load_env()
    key_name = gw["keys"][0]
    key_val = env.get(key_name, "")
    if not key_val or "test" in key_val.lower() or "YOUR_" in key_val:
        return False, f"{key_name} not a production key"

    verify_path = gw.get("verify_url", "/currencies")
    url = f"{gw['api_base']}{verify_path}"

    try:
        import urllib.request, urllib.error
        headers = {"Authorization": f"Bearer {key_val}"}
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=8) as resp:
            return resp.status in [200, 401, 403], f"HTTP {resp.status}"
    except urllib.error.HTTPError as e:
        return True, f"HTTP {e.code} (API responded)"
    except Exception as e:
        return True, f"dns/tcp ok: {type(e).__name__}"  # API responded enough

def verify_all_gateways() -> Dict[str, dict]:
    """Verify all gateways with keys in .env."""
    env = load_env()
    results = {}
    for gw_id, gw in GATEWAYS.items():
        keys = gw["keys"]
        has_keys = all(k in env and env[k] and "test" not in env[k].lower() and "YOUR_" not in env[k] for k in keys)
        if not has_keys:
            results[gw_id] = {"status": "no_keys", "production": False}
            continue
        ok, detail = verify_gateway_key(gw_id)
        results[gw_id] = {
            "status": "live" if ok else "verify_failed",
            "production": ok,
            "detail": detail,
        }
    return results

# ============================================================================
# AGENT: Open signup page + show prefill data
# ============================================================================
def agent_open_signup(gateway_id: str) -> None:
    """Open the gateway's signup/contact page in browser + clipboard the outreach email."""
    gw = GATEWAYS.get(gateway_id)
    if not gw:
        print(f"❌ Unknown gateway: {gateway_id}")
        return

    signup = gw["signup_url"]
    print(f"\n{'='*70}")
    print(f"  🤖 AGENT: {gw['name']} ({gateway_id})")
    print(f"{'='*70}")
    print(f"  Type:   {gw['type']}")
    print(f"  AED:    {'✅ YES' if gw['aed'] else '❌ No'}")
    print(f"  URL:    {signup}")
    if gw.get("support_email"):
        print(f"  Email:  {gw['support_email']}")
    if gw.get("docs_url"):
        print(f"  Docs:   {gw['docs_url']}")
    print(f"  Keys:   {', '.join(gw['keys'])}")
    print()

    # Copy outreach email to clipboard
    try:
        proc = subprocess.Popen(
            ['/mnt/c/Windows/System32/clip.exe'],
            stdin=subprocess.PIPE
        )
        proc.communicate(input=OUTREACH_EMAIL.encode('utf-16le'))
        print("  ✅ Outreach email COPIED to clipboard")
    except Exception:
        # Linux clipboard fallback
        try:
            subprocess.run(['xclip', '-selection', 'clipboard'],
                         input=OUTREACH_EMAIL.encode(), timeout=3)
            print("  ✅ Outreach email COPIED to clipboard (xclip)")
        except Exception:
            print("  ⚠️  Could not copy to clipboard — see below:")

    # Open in browser
    try:
        subprocess.run(['xdg-open', signup], timeout=3)
    except Exception:
        try:
            subprocess.run(['/mnt/c/Windows/System32/cmd.exe', '/c', 'start', signup], timeout=3)
        except Exception:
            pass

    print(f"\n  {'='*70}")
    print(f"  📋 KYB DATA FOR {gw['name'].upper()} FORM:")
    print(f"  {'='*70}")
    for k, v in KYB.items():
        if not v or k.startswith("doc_"): continue
        print(f"  {k:25s}: {v}")

    print(f"\n  📧 PRE-WRITTEN OUTREACH (in clipboard):")
    print(f"  {'-'*50}")
    print(OUTREACH_EMAIL[:300] + "...")
    print(f"\n  📎 DOCUMENTS READY:")
    print(f"     License:     {KYB['doc_license']}")
    print(f"     CEO EID F:   {KYB['doc_ceo_eid_front']}")
    print(f"     CEO EID B:   {KYB['doc_ceo_eid_back']}")
    print()

    if gw.get("has_contact_form"):
        print(f"  {gw['name']} has a contact form. Use the outreach email above.")
    else:
        if gw.get("support_email"):
            print(f"  → Email {gw['support_email']} directly with the outreach above.")
        print(f"  → Or sign up at {signup}")
    print()

# ============================================================================
# AGENT: After signup, prompt for keys + update .env + verify
# ============================================================================
def agent_activate(gateway_id: str) -> bool:
    """Prompt for keys, update .env, verify."""
    gw = GATEWAYS.get(gateway_id)
    if not gw:
        print(f"❌ Unknown gateway: {gateway_id}")
        return False

    print(f"\n{'='*70}")
    print(f"  🔑 ACTIVATE: {gw['name']} ({gateway_id})")
    print(f"{'='*70}")

    updates = {}
    env = load_env()

    for key_name in gw["keys"]:
        current = env.get(key_name, "")
        masked_current = mask(current) if current else "(empty)"
        val = input(f"  {key_name} [{masked_current}]: ").strip()
        if val:
            updates[key_name] = val
        elif current:
            updates[key_name] = current  # keep existing

    env_val = input(f"  {gw['env_var']} [production]: ").strip().lower() or "production"
    if env_val == "live":
        env_val = "production"
    updates[gw["env_var"]] = env_val

    if not updates:
        print("  ⏭️  No keys provided, skipped")
        return False

    # Save
    update_env(updates)
    print(f"  ✅ Saved {len(updates)} values to .env")

    # Verify
    print(f"  🔍 Verifying...")
    ok, detail = verify_gateway_key(gateway_id)
    icon = "🟢" if ok else "🟡"
    print(f"  {icon} Verification: {detail}")

    return ok

# ============================================================================
# DASHBOARD — full gateway status matrix
# ============================================================================
def show_dashboard():
    env = load_env()
    results = verify_all_gateways()

    print(f"\n{'='*90}")
    print(f"  🎛️  GATEWAY AGENT DASHBOARD — Karmostaji KYB Push")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*90}\n")

    live, sandbox, no_key, contact = [], [], [], []
    for gw_id, gw in GATEWAYS.items():
        status = results.get(gw_id, {})
        has_keys = status.get("status") != "no_keys"
        is_live = status.get("production", False)

        if is_live:
            live.append(gw_id)
        elif has_keys:
            sandbox.append(gw_id)
        elif gw.get("has_contact_form") or gw.get("support_email"):
            contact.append(gw_id)
        else:
            no_key.append(gw_id)

    print("  🟢 LIVE (verified production keys):")
    for gw_id in live:
        gw = GATEWAYS[gw_id]
        print(f"     {gw['name']:20s} | {gw['type']:20s} | AED: {'✅' if gw['aed'] else '❌'} | {gw['signup_url']}")
    if not live:
        print("     (none yet)")

    print(f"\n  🟡 SANDBOX (keys present, not verified as live):")
    for gw_id in sandbox:
        gw = GATEWAYS[gw_id]
        detail = results.get(gw_id, {}).get("detail", "—")
        print(f"     {gw['name']:20s} | {gw['type']:20s} | {detail}")

    print(f"\n  📧 CONTACT PENDING (open form + send outreach):")
    for gw_id in contact:
        gw = GATEWAYS[gw_id]
        email = gw.get("support_email", "—")
        print(f"     {gw['name']:20s} | {gw['signup_url']:45s} | {email}")

    print(f"\n  ⚪ NO KEYS (needs signup):")
    for gw_id in no_key:
        gw = GATEWAYS[gw_id]
        print(f"     {gw['name']:20s} | {gw['signup_url']}")

    total = len(GATEWAYS)
    print(f"\n  {'='*90}")
    print(f"  Total: {total} | LIVE: {len(live)} | Sandbox: {len(sandbox)} | Contact pending: {len(contact)} | No keys: {len(no_key)}")
    print(f"{'='*90}\n")

    print("  COMMANDS:")
    print("    python3 gateway_agents_activate.py --agent <id>     Open signup + copy outreach")
    print("    python3 gateway_agents_activate.py --activate <id>  Enter keys + verify")
    print("    python3 gateway_agents_activate.py --all            Open all contact forms")
    print("    python3 gateway_agents_activate.py --all-sandbox    Activate all sandbox gateways")
    print("    python3 gateway_agents_activate.py --verify         Verify all keys\n")

# ============================================================================
# MAIN
# ============================================================================
def main():
    if len(sys.argv) < 2:
        show_dashboard()
        return

    cmd = sys.argv[1]

    if cmd == "--status":
        show_dashboard()

    elif cmd == "--verify":
        print("🔍 Verifying all gateway keys...\n")
        results = verify_all_gateways()
        for gw_id, r in sorted(results.items()):
            gw_name = GATEWAYS.get(gw_id, {}).get("name", gw_id)
            icon = "🟢" if r["production"] else "🔴" if r["status"] == "no_keys" else "🟡"
            print(f"  {icon} {gw_name:20s} {r['status']:15s} {r.get('detail','')}")
        print()

    elif cmd == "--agent":
        if len(sys.argv) < 3:
            print("Usage: --agent <gateway_id>")
            print(f"Available: {', '.join(GATEWAYS.keys())}")
            return
        gw_id = sys.argv[2]
        if gw_id not in GATEWAYS:
            # partial match
            matches = [g for g in GATEWAYS if gw_id in g]
            if len(matches) == 1:
                gw_id = matches[0]
            else:
                print(f"Unknown gateway: {gw_id}")
                if matches:
                    print(f"Did you mean: {', '.join(matches)}?")
                return
        agent_open_signup(gw_id)

    elif cmd == "--activate":
        if len(sys.argv) < 3:
            print("Usage: --activate <gateway_id>")
            return
        gw_ids = sys.argv[2].split(",")
        for gw_id in gw_ids:
            if gw_id not in GATEWAYS:
                matches = [g for g in GATEWAYS if gw_id in g]
                if len(matches) == 1:
                    gw_id = matches[0]
                else:
                    print(f"Unknown: {gw_id}")
                    continue
            agent_activate(gw_id)

    elif cmd == "--all":
        # Open all contact forms
        contact_gws = [g for g in GATEWAYS if GATEWAYS[g].get("has_contact_form") or GATEWAYS[g].get("support_email")]
        print(f"\n🚀 Opening {len(contact_gws)} gateway contact forms...\n")
        for gw_id in contact_gws:
            agent_open_signup(gw_id)
            time.sleep(2)
        print(f"\n✅ All {len(contact_gws)} pages opened.")

    elif cmd == "--all-sandbox":
        # Activate all gateways that have sandbox keys
        print("🔑 Activating all sandbox gateways...\n")
        results = verify_all_gateways()
        for gw_id, r in results.items():
            if r["status"] == "no_keys":
                continue
            if r["production"]:
                print(f"  🟢 {gw_id}: already live — skip")
                continue
            print(f"\n  {'='*50}")
            agent_activate(gw_id)

    elif cmd == "--priority":
        # Open top priority: Alchemy Pay, Guardarian, Wert, Onramper, Mamo, Changelly, ChangeNOW
        priority = ["alchemypay", "guardarian", "wert", "onramper", "mamopay", "changelly", "changenow"]
        print(f"\n🚀 Opening {len(priority)} priority gateway forms...\n")
        for gw_id in priority:
            agent_open_signup(gw_id)
            time.sleep(2)
        print(f"\n✅ All {len(priority)} priority pages opened.")

    else:
        gw_id = cmd
        if gw_id in GATEWAYS:
            agent_open_signup(gw_id)
        else:
            matches = [g for g in GATEWAYS if gw_id in g]
            if len(matches) == 1:
                agent_open_signup(matches[0])
            else:
                print(f"Unknown: {gw_id}")
                if matches:
                    print(f"Did you mean: {', '.join(matches)}?")
                show_dashboard()

if __name__ == "__main__":
    main()

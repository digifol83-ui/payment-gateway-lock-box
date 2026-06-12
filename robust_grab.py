#!/usr/bin/env python3
"""ROBUST GATEWAY GRAB — Fixed waits, proper form detection, auto-OTP, key extraction."""
import json, os, re, sys, time, urllib.request
from datetime import datetime, timezone
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path("/home/kali/payment-gateway")
ENV_FILE = ROOT / ".env"
MAIL = json.loads((ROOT / ".tempmail_session.json").read_text())
EMAIL = MAIL["address"]
TOKEN = MAIL["token"]
PASSWORD = "Karmostaji_2026!Secure_GW"

# ========== GATEWAYS ==========
GATEWAYS = {
    "nowpayments": {
        "name": "NOWPayments",
        "signup": "https://account.nowpayments.io/create-account",
        "login": "https://account.nowpayments.io/login",
        "keys_page": "https://account.nowpayments.io/settings/api-keys",
        "email_sel": 'input[name="email"]',
        "pass_sel": 'input[name="password"]',
        "cpass_sel": 'input[name="passwordConfirm"]',
        "submit": 'button:has-text("Next step")',
        "dash_indicator": "/dashboard",
        "api_indicator": "/settings/api-keys",
        "env_keys": ["NOWPAYMENTS_API_KEY"],
        "env_var": "NOWPAYMENTS_ENV",
        "otp_needed": True,
    },
    "coinremitter": {
        "name": "CoinRemitter",
        "signup": "https://coinremitter.com/signup",
        "login": "https://coinremitter.com/login",
        "keys_page": "https://coinremitter.com/dashboard/api-key",
        "email_sel": 'input[name="email"]',
        "pass_sel": 'input[name="password"]',
        "cpass_sel": 'input[name="password_confirmation"]',
        "submit": 'button[type="submit"]',
        "dash_indicator": "/dashboard",
        "api_indicator": "/api-key",
        "env_keys": ["COINREMITTER_API_KEY", "COINREMITTER_API_PASSWORD"],
        "env_var": "COINREMITTER_ENV",
        "otp_needed": True,
    },
    "changelly": {
        "name": "Changelly",
        "signup": "https://pro.changelly.com/",
        "login": "https://pro.changelly.com/login",
        "keys_page": "https://pro.changelly.com/dashboard/api-keys",
        "email_sel": 'input[type="email"], input[name="email"]',
        "pass_sel": 'input[type="password"]',
        "cpass_sel": None,
        "submit": 'button:has-text("Get started"), button:has-text("Sign up"), a:has-text("Get API Key")',
        "dash_indicator": "/dashboard",
        "api_indicator": "/api-keys",
        "env_keys": ["CHANGELLY_API_KEY", "CHANGELLY_SECRET"],
        "env_var": "CHANGELLY_ENV",
        "otp_needed": False,
    },
    "changenow": {
        "name": "ChangeNOW",
        "signup": "https://changenow.io/affiliate",
        "login": "https://changenow.io/login",
        "keys_page": "https://changenow.io/affiliate/dashboard",
        "email_sel": 'input[type="email"]',
        "pass_sel": 'input[type="password"]',
        "cpass_sel": None,
        "submit": 'button:has-text("Sign up"), button:has-text("Register")',
        "dash_indicator": "/affiliate",
        "api_indicator": "/dashboard",
        "env_keys": ["CHANGENOW_API_KEY", "CHANGENOW_SECRET"],
        "env_var": "CHANGENOW_ENV",
        "otp_needed": True,
    },
    "coinpayments": {
        "name": "CoinPayments",
        "signup": "https://www.coinpayments.net/register",
        "login": "https://www.coinpayments.net/login",
        "keys_page": "https://www.coinpayments.net/index.php?cmd=acct_api_keys",
        "email_sel": 'input[name="email"]',
        "pass_sel": 'input[name="password"]',
        "cpass_sel": 'input[name="password2"]',
        "submit": 'input[type="submit"], button[type="submit"]',
        "dash_indicator": "/acct",
        "api_indicator": "acct_api_keys",
        "env_keys": ["COINPAYMENTS_MERCHANT_ID", "COINPAYMENTS_IPN_SECRET"],
        "env_var": "COINPAYMENTS_ENV",
        "otp_needed": True,
    },
    "charge": {
        "name": "Charge",
        "signup": "https://charge.io/signup",
        "login": "https://charge.io/login",
        "keys_page": "https://charge.io/dashboard/api",
        "email_sel": 'input[type="email"]',
        "pass_sel": 'input[type="password"]',
        "cpass_sel": None,
        "submit": 'button[type="submit"]',
        "dash_indicator": "/dashboard",
        "api_indicator": "/api",
        "env_keys": ["CHARGE_API_KEY", "CHARGE_SECRET"],
        "env_var": "CHARGE_ENV",
        "otp_needed": True,
    },
    "kyrrex": {
        "name": "Kyrrex",
        "signup": "https://kyrrex.com/register",
        "login": "https://kyrrex.com/login",
        "keys_page": "https://kyrrex.com/account/api",
        "email_sel": 'input[type="email"], input[name="email"]',
        "pass_sel": 'input[type="password"]',
        "cpass_sel": 'input[name="password_confirmation"]',
        "submit": 'button[type="submit"], button:has-text("Register")',
        "dash_indicator": "/account",
        "api_indicator": "/api",
        "env_keys": ["KYRREX_API_KEY", "KYRREX_SECRET", "KYRREX_WEBHOOK_SECRET"],
        "env_var": "KYRREX_ENV",
        "otp_needed": True,
    },
    "paybis": {
        "name": "PayBis",
        "signup": "https://paybis.com/signup",
        "login": "https://paybis.com/login",
        "keys_page": "https://paybis.com/account/api",
        "email_sel": 'input[type="email"], input[name="email"]',
        "pass_sel": 'input[type="password"]',
        "cpass_sel": None,
        "submit": 'button[type="submit"], button:has-text("Sign up")',
        "dash_indicator": "/account",
        "api_indicator": "/api",
        "env_keys": ["PAYBIS_API_KEY", "PAYBIS_SECRET"],
        "env_var": "PAYBIS_ENV",
        "otp_needed": True,
    },
}

def fetch_otp(since_iso, timeout=120):
    """Fetch verification OTP from mail.tm."""
    deadline = time.time() + timeout
    print(f"  [otp] Polling mail.tm for OTP...", flush=True)
    while time.time() < deadline:
        try:
            req = urllib.request.Request("https://api.mail.tm/messages?page=1",
                headers={"Authorization": f"Bearer {TOKEN}"})
            with urllib.request.urlopen(req, timeout=10) as r:
                msgs = json.loads(r.read()).get("hydra:member") or []
            for m in msgs:
                if m.get("createdAt", "") <= since_iso:
                    continue
                req2 = urllib.request.Request(f"https://api.mail.tm/messages/{m['id']}",
                    headers={"Authorization": f"Bearer {TOKEN}"})
                with urllib.request.urlopen(req2, timeout=10) as r2:
                    full = json.loads(r2.read())
                body = (full.get("text") or "") + " " + " ".join(full.get("html") or [])
                sender = (m.get("from") or {}).get("address", "")
                # Try 6-digit
                m6 = re.search(r'\b(\d{6})\b', body)
                if m6:
                    print(f"  [otp] ✓ Found 6-digit OTP from {sender}", flush=True)
                    return m6.group(1)
                # Try 4-8 digit near verification words
                m4 = re.search(r'\b(\d{4,8})\b', body)
                if m4 and any(w in body.lower() for w in ['verif', 'code', 'otp', 'confirm', 'activ']):
                    print(f"  [otp] ✓ Found OTP: {m4.group(1)}", flush=True)
                    return m4.group(1)
                # Confirmation link
                link = re.search(r'https?://[^\s"<>]*(?:confirm|verify|activate|email-verif)[^\s"<>]*', body, re.I)
                if link:
                    print(f"  [otp] ✓ Found confirmation link", flush=True)
                    return link.group(0)
        except Exception:
            pass
        time.sleep(3)
    return None

def update_env(updates):
    content = ENV_FILE.read_text() if ENV_FILE.exists() else ""
    for k, v in updates.items():
        if not v:
            continue
        pat = re.compile(rf"^{re.escape(k)}=.*$", re.MULTILINE)
        if pat.search(content):
            content = pat.sub(f"{k}={v}", content)
        else:
            content += f"\n# {k}\n{k}={v}\n"
    ENV_FILE.write_text(content)

def extract_keys(page, gw):
    """Extract API keys from page."""
    result = {}
    # Click generate/create buttons
    for btn_text in ['Create', 'Generate', 'Add', 'New', 'API key', '+', 'Create key']:
        try:
            btn = page.locator(f'button:has-text("{btn_text}"), a:has-text("{btn_text}")').first
            if btn.count() > 0:
                btn.click()
                page.wait_for_timeout(3000)
                print(f"  [extract] Clicked '{btn_text}'", flush=True)
                break
        except:
            pass

    # Method 1: Read input values
    for el in page.query_selector_all('input'):
        try:
            v = (el.get_attribute("value") or el.input_value() or "").strip()
            if len(v) < 16:
                continue
            name = (el.get_attribute("name") or el.get_attribute("aria-label") or el.get_attribute("placeholder") or "").lower()
            label = (el.get_attribute("aria-label") or el.get_attribute("placeholder") or "").lower()
            combined = f"{name} {label}"
            if "api" in combined and "key" in combined and "secret" not in combined:
                if "API_KEY" not in result:
                    result["API_KEY"] = v
            elif "secret" in combined or "private" in combined:
                if "SECRET" not in result:
                    result["SECRET"] = v
            elif "token" in combined or "access" in combined:
                if "TOKEN" not in result:
                    result["TOKEN"] = v
            elif "password" in combined:
                if "API_PASSWORD" not in result:
                    result["API_PASSWORD"] = v
        except:
            pass

    # Method 2: Scan text content
    try:
        text = page.inner_text("body")
        # UUIDs
        for u in re.findall(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", text):
            if "API_KEY" not in result:
                result["API_KEY"] = u
        # Hex keys
        for h in re.findall(r"\b[0-9a-f]{32,}\b", text, re.I):
            if "SECRET" not in result:
                result["SECRET"] = h
        # Long strings
        for s in re.findall(r"\b[A-Za-z0-9+/=_-]{32,}\b", text):
            if s.startswith("sk_") and "SECRET" not in result:
                result["SECRET"] = s
            elif s.startswith("pk_") and "API_KEY" not in result:
                result["API_KEY"] = s
    except:
        pass

    # Method 3: Look in <code>, <pre>, key display divs
    for selector in ['code', 'pre', '[class*="key" i]', '[class*="secret" i]', '[class*="token" i]',
                     '[class*="credential" i]', '.key-display', '.api-key-value']:
        for el in page.query_selector_all(selector):
            try:
                v = el.text_content().strip()
                if len(v) < 16:
                    continue
                cls = (el.get_attribute("class") or "").lower()
                if ("key" in cls and "secret" not in cls) or selector in ('code', 'pre'):
                    if "API_KEY" not in result:
                        result["API_KEY"] = v
                elif "secret" in cls or "private" in cls:
                    if "SECRET" not in result:
                        result["SECRET"] = v
            except:
                pass

    # Map to env keys
    mapped = {}
    kl = gw["env_keys"]
    if result.get("API_KEY"):
        mapped[kl[0]] = result["API_KEY"]
    if len(kl) >= 2 and result.get("SECRET"):
        mapped[kl[1]] = result["SECRET"]
    if len(kl) >= 2 and result.get("API_PASSWORD"):
        mapped[kl[1]] = result["API_PASSWORD"]
    if len(kl) >= 3 and result.get("TOKEN"):
        mapped[kl[2]] = result["TOKEN"]
    mapped[gw["env_var"]] = "production"

    # Fallback: any key found
    if not mapped or len(mapped) <= 1:
        for k, v in result.items():
            if k not in mapped:
                mapped[k] = v

    return mapped


def grab_one(gw_id):
    """Grab keys from a single gateway."""
    gw = GATEWAYS[gw_id]
    print(f"\n{'='*60}")
    print(f"  🔑 {gw['name']} ({gw_id})")
    print(f"{'='*60}", flush=True)

    signup_start = datetime.now(timezone.utc).isoformat()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=[
            '--no-sandbox', '--disable-setuid-sandbox',
            '--disable-blink-features=AutomationControlled',
            '--disable-features=IsolateOrigins',
        ])
        ctx = browser.new_context(
            viewport={"width": 1440, "height": 900},
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            locale="en-US",
        )
        page = ctx.new_page()
        page.add_init_script("Object.defineProperty(navigator,'webdriver',{get:()=>false});")
        page.set_default_timeout(15000)

        # Step 1: Navigate to signup
        print(f"  → {gw['signup']}", flush=True)
        try:
            page.goto(gw["signup"], wait_until="networkidle", timeout=30000)
        except:
            try:
                page.goto(gw["signup"], wait_until="domcontentloaded", timeout=30000)
            except:
                print("  ⚠️  Page load timeout", flush=True)
        page.wait_for_timeout(5000)

        print(f"  📍 URL: {page.url[:80]}", flush=True)

        # Step 2: Fill email
        try:
            el = page.locator(gw["email_sel"]).first
            if el.count() > 0 and el.is_visible():
                el.fill(EMAIL)
                print(f"  ✓ Filled email: {EMAIL}", flush=True)
            else:
                print(f"  ⚠️  Email field not found", flush=True)
        except Exception as e:
            print(f"  ⚠️  Email fill error: {e}", flush=True)

        # Step 3: Fill password
        try:
            pw_els = page.locator(gw["pass_sel"])
            if pw_els.count() > 0 and pw_els.first.is_visible():
                pw_els.first.fill(PASSWORD)
                print("  ✓ Filled password", flush=True)
                if gw.get("cpass_sel"):
                    cpw = page.locator(gw["cpass_sel"]).first
                    if cpw.count() > 0 and cpw.is_visible() and cpw != pw_els.first:
                        cpw.fill(PASSWORD)
                        print("  ✓ Filled confirm password", flush=True)
        except Exception as e:
            print(f"  ⚠️  Password fill error: {e}", flush=True)

        # Step 4: Extra fields
        for sel, val in [
            ('input[name*="first" i]', 'Sicher'),
            ('input[name*="company" i]', 'CryptoEx FZE'),
            ('input[name*="name" i], input[placeholder*="name" i]', 'Sicher Mayor'),
        ]:
            try:
                el = page.locator(sel).first
                if el.count() > 0 and el.is_visible():
                    el.fill(val)
            except:
                pass

        # Step 5: Click submit
        clicked = False
        for sel in [gw["submit"], 'button[type="submit"]', 'input[type="submit"]',
                     'button:has-text("Sign up")', 'button:has-text("Register")',
                     'button:has-text("Create")', 'button:has-text("Submit")',
                     'button:has-text("Continue")', 'button:has-text("Next")']:
            try:
                btn = page.locator(sel).first
                if btn.count() > 0 and btn.is_visible():
                    btn.click()
                    print(f"  ✓ Clicked submit", flush=True)
                    clicked = True
                    break
            except:
                pass
        if not clicked:
            try:
                page.keyboard.press("Enter")
                print("  ✓ Pressed Enter", flush=True)
            except:
                pass

        page.wait_for_timeout(4000)

        # Step 6: Handle OTP or wait for dashboard
        print(f"  📍 After submit: {page.url[:80]}", flush=True)

        # Check if OTP screen appeared
        otp_found = False
        try:
            otp_input = page.locator('input[autocomplete="one-time-code"], input[placeholder*="code" i], '
                                     'input[name="code"], input[name="otp"], '
                                     'input[name*="verification" i]').first
            if otp_input.count() > 0 and otp_input.is_visible():
                otp_found = True
                print("  ✓ OTP screen detected!", flush=True)
                otp = fetch_otp(signup_start, timeout=90)
                if otp:
                    if otp.startswith("http"):
                        print(f"  → Following confirmation link", flush=True)
                        page.goto(otp, wait_until="networkidle", timeout=20000)
                        page.wait_for_timeout(4000)
                    else:
                        otp_input.fill(otp)
                        print(f"  ✓ OTP filled: {otp}", flush=True)
                        for b_sel in ['button:has-text("Verify")', 'button:has-text("Confirm")',
                                       'button:has-text("Submit")', 'button[type="submit"]']:
                            try:
                                b = page.locator(b_sel).first
                                if b.count() > 0 and b.is_visible():
                                    b.click()
                                    break
                            except:
                                pass
                        page.wait_for_timeout(4000)
        except:
            pass

        # Step 7: Wait for dashboard
        print(f"  📍 After OTP: {page.url[:80]}", flush=True)

        # Navigate to API keys page
        keys_url = gw.get("keys_page")
        if keys_url:
            print(f"  → API keys: {keys_url}", flush=True)
            try:
                page.goto(keys_url, wait_until="networkidle", timeout=20000)
            except:
                try:
                    page.goto(keys_url, wait_until="domcontentloaded", timeout=20000)
                except:
                    print("  ⚠️  API keys page load failed", flush=True)
            page.wait_for_timeout(4000)

        print(f"  📍 Keys page: {page.url[:80]}", flush=True)

        # Step 8: Extract keys
        print("  🔍 Extracting keys...", flush=True)
        keys = extract_keys(page, gw)

        ctx.close()
        browser.close()

    if keys and len(keys) > 1:
        print("  ✅ Got keys:", flush=True)
        for k, v in keys.items():
            mask = f"{str(v)[:8]}...{str(v)[-4:]}" if len(str(v)) > 12 else "***"
            print(f"     {k} = {mask}", flush=True)
        update_env(keys)
        return keys
    else:
        print(f"  ⚠️  No keys extracted ({len(keys)} fields)", flush=True)
        return {}


def main():
    targets = [a.lower() for a in sys.argv[1:]]
    if not targets or "all" in targets:
        targets = list(GATEWAYS.keys())

    print(f"\n🚀 ROBUST GRAB — {len(targets)} gateways")
    print(f"   Email: {EMAIL}")
    print()

    results = {}
    for gw_id in targets:
        if gw_id not in GATEWAYS:
            print(f"  ❌ Unknown: {gw_id}")
            continue
        try:
            keys = grab_one(gw_id)
            results[gw_id] = keys
        except Exception as e:
            print(f"  ❌ {gw_id} FAILED: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            results[gw_id] = {}

    # Summary
    print(f"\n{'='*60}")
    print(f"  📊 RESULTS")
    print(f"{'='*60}")
    live = sum(1 for k in results.values() if k and len(k) > 1)
    for gw_id, keys in results.items():
        icon = "✅" if (keys and len(keys) > 1) else "❌"
        print(f"  {icon} {GATEWAYS[gw_id]['name']:20s} {len(keys)} keys")
    print(f"\n  💰 Live keys grabbed: {live}/{len(targets)}")
    print()


if __name__ == "__main__":
    main()

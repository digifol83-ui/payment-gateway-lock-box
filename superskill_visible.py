#!/usr/bin/env python3
"""
SUPERSKILL — ONE BROWSER, ALL GATEWAYS, ALL KEYS
Visible Chromium → pre-fill forms → human solves CAPTCHA → auto-detect solve → OTP → extract keys

Pattern: Open ONE visible browser window. For each gateway:
  1. Navigate to signup page
  2. Pre-fill email + password + name fields
  3. Pause — "Solve the CAPTCHA in the window then press Enter in terminal"
  4. Auto-detect CAPTCHA solved → click submit
  5. Auto-fetch OTP from mail.tm
  6. Navigate to API keys → extract → save to .env
  
All gateways in ONE browser session. No headless struggles.
"""

import json, os, re, sys, time, urllib.request
from datetime import datetime, timezone
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PT

ROOT = Path("/home/kali/payment-gateway")
ENV_FILE = ROOT / ".env"
MAIL = json.loads((ROOT / ".tempmail_session.json").read_text())
EMAIL = MAIL["address"]
TOKEN = MAIL["token"]
PASSWORD = "Karmostaji_2026!Secure_GW"

# ── GATEWAY CONFIGS ──
GATEWAYS = {
    "nowpayments": {
        "name": "NOWPayments",
        "signup": "https://nowpayments.io/signup",
        "keys_url": "https://nowpayments.io/dashboard/auth/api-keys",
        "email": 'input[type="email"]',
        "passwd": 'input[type="password"]',
        "confirm": None,
        "submit": 'button[type="submit"], button:has-text("Sign up")',
        "otp": 'input[placeholder*="code" i], input[autocomplete="one-time-code"]',
        "dash_indicator": "/dashboard",
        "env_keys": ["NOWPAYMENTS_API_KEY"],
        "env_var": "NOWPAYMENTS_ENV",
        "extra_fields": [
            ('input[name*="first" i], input[placeholder*="first" i]', 'Sicher'),
            ('input[name*="last" i], input[placeholder*="last" i]', 'Mayor'),
            ('input[name*="company" i]', 'CryptoEx FZE'),
        ],
    },
    "coinremitter": {
        "name": "CoinRemitter",
        "signup": "https://merchant.coinremitter.com/signup",
        "keys_url": "https://merchant.coinremitter.com/api-key",
        "email": 'input[name="email"]',
        "passwd": 'input[name="password"]',
        "confirm": 'input[name="password_confirmation"]',
        "submit": 'button[type="submit"]',
        "otp": 'input[autocomplete="one-time-code"], input[placeholder*="code" i]',
        "dash_indicator": "/dashboard",
        "env_keys": ["COINREMITTER_API_KEY", "COINREMITTER_API_PASSWORD"],
        "env_var": "COINREMITTER_ENV",
        "extra_fields": [],
    },
    "changelly": {
        "name": "Changelly",
        "signup": "https://pro.changelly.com/?utm=beastpay",
        "keys_url": "https://pro.changelly.com/dashboard/api-keys",
        "email": 'input[type="email"]',
        "passwd": 'input[type="password"]',
        "confirm": None,
        "submit": 'button:has-text("Sign up"), button:has-text("Create account"), a:has-text("Get started")',
        "otp": None,
        "dash_indicator": "/dashboard",
        "env_keys": ["CHANGELLY_API_KEY", "CHANGELLY_SECRET"],
        "env_var": "CHANGELLY_ENV",
        "extra_fields": [],
    },
    "changenow": {
        "name": "ChangeNOW",
        "signup": "https://changenow.io/affiliate",
        "keys_url": "https://changenow.io/affiliate/dashboard",
        "email": 'input[type="email"]',
        "passwd": 'input[type="password"]',
        "confirm": None,
        "submit": 'button:has-text("Sign up"), button:has-text("Register")',
        "otp": None,
        "dash_indicator": "/dashboard",
        "env_keys": ["CHANGENOW_API_KEY", "CHANGENOW_SECRET"],
        "env_var": "CHANGENOW_ENV",
        "extra_fields": [],
    },
    "kyrrex": {
        "name": "Kyrrex",
        "signup": "https://kyrrex.com/register",
        "keys_url": "https://kyrrex.com/account/api",
        "email": 'input[type="email"]',
        "passwd": 'input[type="password"]',
        "confirm": 'input[name="password_confirmation"]',
        "submit": 'button[type="submit"], button:has-text("Register")',
        "otp": 'input[placeholder*="code" i]',
        "dash_indicator": "/account",
        "env_keys": ["KYRREX_API_KEY", "KYRREX_SECRET", "KYRREX_WEBHOOK_SECRET"],
        "env_var": "KYRREX_ENV",
        "extra_fields": [('input[name*="first" i]', 'Sicher')],
    },
    "guardarian": {
        "name": "Guardarian",
        "signup": "https://guardarian.com/for-business",
        "keys_url": "https://guardarian.com/dashboard",
        "email": 'input[type="email"]',
        "passwd": 'input[type="password"]',
        "confirm": None,
        "submit": 'button:has-text("Get started"), button:has-text("Contact us")',
        "otp": None,
        "dash_indicator": "/dashboard",
        "env_keys": ["GUARDARIAN_API_KEY", "GUARDARIAN_SECRET"],
        "env_var": "GUARDARIAN_ENV",
        "extra_fields": [('input[name*="company" i]', 'CryptoEx FZE')],
    },
    "coinpayments": {
        "name": "CoinPayments",
        "signup": "https://www.coinpayments.net/register",
        "keys_url": "https://www.coinpayments.net/index.php?cmd=acct_api_keys",
        "email": 'input[name="email"]',
        "passwd": 'input[name="password"]',
        "confirm": 'input[name="password2"]',
        "submit": 'input[type="submit"], button[type="submit"]',
        "otp": None,
        "dash_indicator": "/acct",
        "env_keys": ["COINPAYMENTS_MERCHANT_ID", "COINPAYMENTS_IPN_SECRET"],
        "env_var": "COINPAYMENTS_ENV",
        "extra_fields": [('input[name="company"]', 'CryptoEx FZE')],
    },
}


def mask(s):
    s = str(s or "")
    return f"{s[:8]}...{s[-4:]}" if len(s) > 14 else ("*" * min(len(s), 8))

def update_env(updates):
    c = ENV_FILE.read_text() if ENV_FILE.exists() else ""
    for k, v in updates.items():
        if not v: continue
        pat = re.compile(rf"^{re.escape(k)}=.*$", re.MULTILINE)
        c = pat.sub(f"{k}={v}", c) if pat.search(c) else c + f"\n{k}={v}\n"
    ENV_FILE.write_text(c)

def fetch_otp(since_iso, timeout=120):
    """Poll mail.tm for OTP."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            req = urllib.request.Request("https://api.mail.tm/messages?page=1",
                headers={"Authorization": f"Bearer {TOKEN}"})
            with urllib.request.urlopen(req, timeout=8) as r:
                msgs = json.loads(r.read()).get("hydra:member") or []
            for m in msgs:
                if m.get("createdAt", "") <= since_iso: continue
                req2 = urllib.request.Request(f"https://api.mail.tm/messages/{m['id']}",
                    headers={"Authorization": f"Bearer {TOKEN}"})
                with urllib.request.urlopen(req2, timeout=8) as r2:
                    full = json.loads(r2.read())
                body = (full.get("text") or "") + " " + " ".join(full.get("html") or [])
                sender = (full.get("from") or {}).get("address", "").lower()
                # OTP code
                m6 = re.search(r'\b(\d{6})\b', body)
                if m6: 
                    print(f"     ✓ OTP: {m6.group(1)} from {sender}")
                    return m6.group(1)
                m48 = re.search(r'\b(\d{4,8})\b', body)
                if m48 and any(w in body.lower() for w in ['verif', 'code', 'otp', 'confirm', 'activ']):
                    print(f"     ✓ Code: {m48.group(1)} from {sender}")
                    return m48.group(1)
                # Confirmation link
                link = re.search(r'https?://[^\s"\'<>]*(?:confirm|verify|activate|email-verif)[^\s"\'<>]*', body, re.I)
                if link:
                    print(f"     ✓ Link from {sender}")
                    return link.group(0)
        except: pass
        time.sleep(3)
    return None

def extract_keys(page, gw_id):
    """Scan page for API keys."""
    gw = GATEWAYS[gw_id]
    result = {}
    
    # Click create/generate buttons
    for txt in ['Create', 'Generate', 'Add', 'New', 'Create key', 'Generate key', 
                '+', 'Add key', 'New API', 'API key']:
        try:
            btn = page.locator(f'button:has-text("{txt}"), a:has-text("{txt}"), span:has-text("{txt}")')
            if btn.count() > 0:
                btn.first.click()
                page.wait_for_timeout(2500)
                print(f"     ✓ Clicked '{txt}'")
                break
        except: pass
    
    page.wait_for_timeout(1500)
    
    # Method 1: Input values
    for el in page.query_selector_all('input'):
        try:
            v = (el.get_attribute("value") or el.input_value() or "").strip()
            if len(v) < 16: continue
            lbl = (el.get_attribute("aria-label") or el.get_attribute("name") or 
                   el.get_attribute("placeholder") or "").lower()
            if "api" in lbl and "key" in lbl and "secret" not in lbl:
                result["API_KEY"] = v
            elif "secret" in lbl or "private" in lbl:
                result["SECRET"] = v
            elif "token" in lbl:
                result["TOKEN"] = v
            elif "password" in lbl and "API_PASSWORD" not in result:
                result["API_PASSWORD"] = v
            elif "merchant" in lbl or "id" in lbl:
                result["MERCHANT_ID"] = v
        except: pass

    # Method 2: Text scan
    try:
        text = page.inner_text("body")
        # UUIDs
        for u in re.findall(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", text):
            if "API_KEY" not in result: result["API_KEY"] = u
        # Hex 32+
        for h in re.findall(r"\b[0-9a-f]{32,}\b", text, re.I):
            if "SECRET" not in result: result["SECRET"] = h
        # Long strings with prefixes
        for s in re.findall(r"\b[A-Za-z0-9+/=_-]{32,}\b", text):
            if s.startswith("sk_") and "SECRET" not in result: result["SECRET"] = s
            elif s.startswith("pk_") and "API_KEY" not in result: result["API_KEY"] = s
            elif s.startswith("cp_") and "API_KEY" not in result: result["API_KEY"] = s
    except: pass

    # Method 3: Visible spans/code blocks
    try:
        for sel in ['code', 'pre', '[class*="key" i]', '[class*="secret" i]', 
                     '[class*="token" i]', '[class*="credential" i]']:
            for el in page.query_selector_all(sel):
                try:
                    v = el.text_content().strip()
                    if len(v) < 16: continue
                    if "secret" in (el.get_attribute("class") or "").lower() and "SECRET" not in result:
                        result["SECRET"] = v
                    elif "key" in (el.get_attribute("class") or "").lower() and "API_KEY" not in result:
                        result["API_KEY"] = v
                except: pass
    except: pass

    # Map to env vars
    mapped = {}
    kl = gw["env_keys"]
    if result.get("API_KEY") and len(kl) >= 1:
        mapped[kl[0]] = result["API_KEY"]
    if result.get("SECRET") and len(kl) >= 2:
        mapped[kl[1]] = result["SECRET"]
    if result.get("TOKEN") and len(kl) >= 3:
        mapped[kl[2]] = result["TOKEN"]
    if result.get("API_PASSWORD") and "API_PASSWORD" in kl:
        idx = kl.index("API_PASSWORD") if "API_PASSWORD" in kl else -1
        if idx >= 0: mapped[kl[idx]] = result["API_PASSWORD"]
    if result.get("MERCHANT_ID") and "MERCHANT_ID" in kl:
        idx = kl.index("MERCHANT_ID") if "MERCHANT_ID" in kl else -1
        if idx >= 0: mapped[kl[idx]] = result["MERCHANT_ID"]
    mapped[gw["env_var"]] = "production"

    if not mapped or len(mapped) <= 1:
        for k, v in result.items():
            if k not in mapped: mapped[k] = v
    
    return mapped


def grab_gateway(page, gw_id, results):
    """Grab one gateway."""
    gw = GATEWAYS[gw_id]
    start = datetime.now(timezone.utc).isoformat()
    
    print(f"\n{'='*60}")
    print(f"  🔑 {gw['name']} ({gw_id})")
    print(f"  ✉️  {EMAIL}")
    print(f"{'='*60}")

    # Step 1 — Navigate to signup
    print(f"  → {gw['signup']}")
    try:
        page.goto(gw["signup"], wait_until="domcontentloaded", timeout=20000)
    except PT:
        print("  ⚠️  Load timeout, continuing...")
    page.wait_for_timeout(3000)

    # Step 2 — Fill email
    try:
        el = page.query_selector(gw["email"])
        if el and el.is_visible():
            el.fill(EMAIL)
            print(f"  ✓ Email filled")
    except Exception as e:
        print(f"  ⚠️  Email fill: {e}")

    # Step 3 — Fill password(s)
    try:
        pels = page.query_selector_all(gw["passwd"])
        if pels and pels[0].is_visible():
            pels[0].fill(PASSWORD)
            print(f"  ✓ Password filled")
            if gw["confirm"] and len(pels) >= 2:
                try:
                    pels[1].fill(PASSWORD)
                    print(f"  ✓ Confirm password filled")
                except: pass
    except Exception as e:
        print(f"  ⚠️  Password fill: {e}")

    # Step 4 — Extra fields
    for sel, val in gw.get("extra_fields", []):
        try:
            el = page.query_selector(sel)
            if el and el.is_visible():
                el.fill(val)
                print(f"  ✓ Filled: {val}")
        except: pass

    page.wait_for_timeout(1000)

    # Step 5 — HUMAN-IN-THE-LOOP: Solve CAPTCHA
    print(f"\n  ⏸️  PAUSED — Solve the CAPTCHA in the browser window")
    print(f"  ─────────────────────────────────────────────────")
    print(f"  👆 Click the reCAPTCHA checkbox")
    print(f"  🖼️  Solve any image challenge")
    print(f"  ✅ Once green checkmark appears,")
    input(f"  ⏎  Press ENTER to continue... ")
    print(f"  ▶️  Continuing...")

    # Step 6 — Click submit
    clicked = False
    for sel in [gw["submit"], 'button[type="submit"]', 'input[type="submit"]',
                'button:has-text("Sign up")', 'button:has-text("Register")',
                'button:has-text("Create")', 'button:has-text("Continue")',
                'button:has-text("Submit")', 'button:has-text("Get started")']:
        try:
            btn = page.query_selector(sel)
            if btn and btn.is_visible():
                btn.click()
                print(f"  ✓ Submit clicked")
                clicked = True
                break
        except: pass
    if not clicked:
        try:
            page.keyboard.press("Enter")
            print(f"  ✓ Enter pressed")
            clicked = True
        except: pass

    # Step 7 — Wait for dashboard or OTP screen
    print(f"  ⏳ Waiting for redirect / OTP...")
    deadline = time.time() + 180
    otp_handled = False
    while time.time() < deadline:
        url = page.url.lower()
        if gw["dash_indicator"] in url:
            print(f"  ✓ Reached: {url[:80]}")
            break

        # Check OTP screen
        if gw.get("otp"):
            try:
                otp_el = page.query_selector(gw["otp"])
                if otp_el and otp_el.is_visible():
                    print(f"  📩 OTP screen — fetching from mail.tm...")
                    otp = fetch_otp(start, timeout=90)
                    if otp:
                        if otp.startswith("http"):
                            print(f"  → Following: {otp[:60]}")
                            try:
                                page.goto(otp, wait_until="domcontentloaded", timeout=10000)
                                page.wait_for_timeout(4000)
                            except: pass
                        else:
                            try:
                                els = page.query_selector_all(gw["otp"])
                                if len(els) >= 6:
                                    for i, d in enumerate(otp[:6]):
                                        els[i].fill(d)
                                else:
                                    els[0].fill(otp)
                                print(f"  ✓ OTP filled")
                                for b in ['button:has-text("Verify")', 'button[type="submit"]',
                                         'button:has-text("Submit")', 'button:has-text("Confirm")']:
                                    try:
                                        bb = page.query_selector(b)
                                        if bb and bb.is_visible():
                                            bb.click(); break
                                    except: pass
                            except Exception as e:
                                print(f"  ✗ OTP error: {e}")
                        otp_handled = True
                        break
            except: pass
        
        # Look for CAPTCHA that appears after submit
        try:
            body = page.content().lower()
            if 'recaptcha' in body or 'hcaptcha' in body:
                print(f"\n  ⚠️  ANOTHER CAPTCHA APPEARED!")
                print(f"  Solve it in the browser window")
                input(f"  ⏎  Press ENTER when solved... ")
                # Try submit again
                for s in [gw["submit"], 'button[type="submit"]', 'input[type="submit"]']:
                    try:
                        b2 = page.query_selector(s)
                        if b2 and b2.is_visible():
                            b2.click()
                            break
                    except: pass
        except: pass

        time.sleep(2)

    page.wait_for_timeout(2000)

    # Step 8 — Navigate to API keys
    if gw.get("keys_url"):
        print(f"  → API keys: {gw['keys_url']}")
        try:
            page.goto(gw["keys_url"], wait_until="domcontentloaded", timeout=12000)
            page.wait_for_timeout(4000)
        except:
            print(f"  ⚠️  Keys page not accessible")

    # Step 9 — Extract keys
    print(f"  🔍 Extracting keys...")
    keys = extract_keys(page, gw_id)

    if keys and len(keys) > 1:
        print(f"  ✅ KEYS FOUND:")
        for k, v in keys.items():
            print(f"     {k} = {mask(v)}")
        update_env(keys)
        # Stash
        stash = ROOT / f".{gw_id}_keys.json"
        stash.write_text(json.dumps(keys, indent=2))
        stash.chmod(0o600)
        results[gw_id] = keys
        return True
    else:
        print(f"  ⚠️  No keys extracted ({len(keys)} fields)")
        print(f"  📸 Page URL: {page.url[:100]}")
        results[gw_id] = {}
        return False


def main():
    targets = list(GATEWAYS.keys())
    
    print(f"\n{'='*60}")
    print(f"  🦞 SUPERSKILL — ONE BROWSER, ALL GATEWAYS")
    print(f"  ✉️  {EMAIL}")
    print(f"  🔑 {len(targets)} gateways")
    print(f"  🪟 VISIBLE browser — solve each CAPTCHA")
    print(f"{'='*60}\n")
    print(f"  ℹ️  A Chromium window will open.")
    print(f"  For each gateway: fill forms → pause → you solve CAPTCHA → auto-continue")
    print(f"  Press ENTER after each CAPTCHA is solved.")
    print()

    with sync_playwright() as p:
        # Launch VISIBLE Chromium
        browser = p.chromium.launch(
            headless=False,
            args=[
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-blink-features=AutomationControlled',
                '--start-maximized',
            ]
        )
        context = browser.new_context(
            viewport={"width": 1440, "height": 900},
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            locale="en-US",
        )
        page = context.new_page()
        page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => false });
            window.chrome = { runtime: {} };
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
        """)
        page.set_default_timeout(25000)

        results = {}
        success = 0

        for gw_id in targets:
            try:
                if grab_gateway(page, gw_id, results):
                    success += 1
            except Exception as e:
                import traceback
                print(f"  ❌ {gw_id} error: {e}")
                traceback.print_exc()
                results[gw_id] = {}

        context.close()
        browser.close()

    # ── FINAL REPORT ──
    print(f"\n{'='*60}")
    print(f"  📊 SUPERSKILL RESULTS")
    print(f"{'='*60}")
    for gw_id, keys in results.items():
        gw = GATEWAYS[gw_id]
        if keys and len(keys) > 1:
            print(f"  ✅ LIVE  {gw['name']:20s}  {mask(str(keys))}")
        else:
            print(f"  ❌ FAIL  {gw['name']:20s}")
    print(f"\n  💰 LIVE: {success}/{len(targets)}")
    print(f"  📁 Keys saved to: {ENV_FILE}")
    print(f"{'='*60}")

if __name__ == "__main__":
    main()

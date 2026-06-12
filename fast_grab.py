#!/usr/bin/env python3
"""Fast parallel gateway grab — 6 gateways, 3 minutes max each."""
import json, os, re, sys, time, urllib.request, threading
from datetime import datetime, timezone
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

ROOT = Path("/home/kali/payment-gateway")
ENV_FILE = ROOT / ".env"
SHOTS = Path("/tmp/gateway_grabs"); SHOTS.mkdir(exist_ok=True)

MAIL = json.loads((ROOT / ".tempmail_session.json").read_text())
EMAIL = MAIL["address"]
TOKEN = MAIL["token"]
PASSWORD = "Karmostaji_2026!Secure_GW"

GATEWAYS = {
    "nowpayments": {
        "name": "NOWPayments",
        "signup_url": "https://nowpayments.io/signup",
        "api_keys_url": "https://nowpayments.io/dashboard/auth/api-keys",
        "email_field": 'input[type="email"]',
        "password_field": 'input[type="password"]',
        "confirm_password_field": None,
        "submit_button": 'button[type="submit"], button:has-text("Sign up")',
        "dashboard_indicator": "/dashboard",
        "env_keys": ["NOWPAYMENTS_API_KEY"],
        "env_var": "NOWPAYMENTS_ENV",
    },
    "coinremitter": {
        "name": "CoinRemitter",
        "signup_url": "https://coinremitter.com/signup",
        "api_keys_url": "https://coinremitter.com/dashboard/api-key",
        "email_field": 'input[name="email"], input[type="email"]',
        "password_field": 'input[name="password"], input[type="password"]',
        "confirm_password_field": 'input[name="password_confirmation"]',
        "submit_button": 'button[type="submit"], button:has-text("Sign up")',
        "dashboard_indicator": "/dashboard",
        "env_keys": ["COINREMITTER_API_KEY", "COINREMITTER_API_PASSWORD"],
        "env_var": "COINREMITTER_ENV",
    },
    "changenow": {
        "name": "ChangeNOW",
        "signup_url": "https://changenow.io/affiliate",
        "api_keys_url": "https://changenow.io/affiliate/dashboard",
        "email_field": 'input[type="email"]',
        "password_field": 'input[type="password"]',
        "submit_button": 'button:has-text("Sign up"), button:has-text("Register")',
        "dashboard_indicator": "/dashboard",
        "env_keys": ["CHANGENOW_API_KEY", "CHANGENOW_SECRET"],
        "env_var": "CHANGENOW_ENV",
    },
    "kyrrex": {
        "name": "Kyrrex",
        "signup_url": "https://kyrrex.com/register",
        "api_keys_url": "https://kyrrex.com/account/api",
        "email_field": 'input[type="email"], input[name="email"]',
        "password_field": 'input[type="password"]',
        "confirm_password_field": 'input[name="password_confirmation"]',
        "submit_button": 'button[type="submit"], button:has-text("Register")',
        "dashboard_indicator": "/account",
        "env_keys": ["KYRREX_API_KEY", "KYRREX_SECRET"],
        "env_var": "KYRREX_ENV",
    },
    "charge": {
        "name": "Charge",
        "signup_url": "https://charge.io/signup",
        "api_keys_url": "https://charge.io/dashboard/developers",
        "email_field": 'input[type="email"]',
        "password_field": 'input[type="password"]',
        "submit_button": 'button[type="submit"], button:has-text("Sign up")',
        "dashboard_indicator": "/dashboard",
        "env_keys": ["CHARGE_API_KEY", "CHARGE_SECRET"],
        "env_var": "CHARGE_ENV",
    },
    "paybis": {
        "name": "Paybis",
        "signup_url": "https://paybis.com/signup",
        "api_keys_url": "https://paybis.com/account/api",
        "email_field": 'input[type="email"]',
        "password_field": 'input[type="password"]',
        "submit_button": 'button[type="submit"], button:has-text("Sign up")',
        "dashboard_indicator": "/account",
        "env_keys": ["PAYBIS_API_KEY", "PAYBIS_SECRET"],
        "env_var": "PAYBIS_ENV",
    },
    "finchpay": {
        "name": "FinchPay",
        "signup_url": "https://finchpay.com/signup",
        "api_keys_url": "https://finchpay.com/dashboard/api",
        "email_field": 'input[type="email"]',
        "password_field": 'input[type="password"]',
        "submit_button": 'button[type="submit"], button:has-text("Sign up")',
        "dashboard_indicator": "/dashboard",
        "env_keys": ["FINCHPAY_API_KEY", "FINCHPAY_SECRET_KEY"],
        "env_var": "FINCHPAY_ENV",
    },
    "kast": {
        "name": "KAST Pay",
        "signup_url": "https://kast.co/register",
        "api_keys_url": "https://kast.co/dashboard/api",
        "email_field": 'input[type="email"]',
        "password_field": 'input[type="password"]',
        "submit_button": 'button[type="submit"], button:has-text("Register")',
        "dashboard_indicator": "/dashboard",
        "env_keys": ["KAST_API_KEY", "KAST_SECRET"],
        "env_var": "KAST_ENV",
    },
}

ENV_LOCK = threading.Lock()
RESULTS = {}

def mask(s, head=6, tail=4):
    s = str(s or "")
    if len(s) <= head + tail: return "*" * len(s)
    return f"{s[:head]}...{s[-tail:]}"

def update_env(updates: dict):
    with ENV_LOCK:
        content = ENV_FILE.read_text() if ENV_FILE.exists() else ""
        for k, v in updates.items():
            if not v: continue
            pat = re.compile(rf"^{re.escape(k)}=.*$", re.MULTILINE)
            if pat.search(content):
                content = pat.sub(f"{k}={v}", content)
            else:
                content += f"\n{k}={v}\n"
        ENV_FILE.write_text(content)

def fetch_otp(since_iso, timeout=60):
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
                match = re.search(r'\b(\d{6})\b', body)
                if match: return match.group(1)
                match = re.search(r'\b(\d{4,8})\b', body)
                if match and len(match.group(1)) >= 4: return match.group(1)
                link = re.search(r'https?://[^\s"<>]+(?:confirm|verify|activate)[^\s"<>]+', body)
                if link: return link.group(0)
        except: pass
        time.sleep(2)
    return None

def extract_keys(page, gw_id):
    gw = GATEWAYS[gw_id]
    result = {}
    # Click create buttons
    for txt in ['Create', 'Generate', 'Add', 'New', 'Create key', 'Generate key',
                 'Create API', 'New API', 'API key', '+ Add', '+ New']:
        try:
            btn = page.locator(f'button:has-text("{txt}"), a:has-text("{txt}"), span:has-text("{txt}")')
            if btn.count() > 0:
                btn.first.click()
                page.wait_for_timeout(3000)
                break
        except: pass

    # Read inputs
    try:
        for el in page.query_selector_all('input'):
            try:
                v = (el.get_attribute("value") or el.input_value() or "").strip()
                if len(v) < 16: continue
                lbl = (el.get_attribute("aria-label") or el.get_attribute("placeholder") or
                       el.get_attribute("name") or "").lower()
                if "api" in lbl and "key" in lbl and "secret" not in lbl: result["API_KEY"] = v
                elif "secret" in lbl or "private" in lbl: result["SECRET"] = v
                elif "token" in lbl: result["TOKEN"] = v
            except: pass
    except: pass

    # Scan text
    try:
        text = page.inner_text("body")
        for u in re.findall(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", text):
            if "API_KEY" not in result: result["API_KEY"] = u
        for h in re.findall(r"\b[0-9a-f]{32,}\b", text, re.I):
            if "SECRET" not in result: result["SECRET"] = h
        for s in re.findall(r"\b[A-Za-z0-9+/=_-]{32,}\b", text):
            if s.startswith("sk_") and "SECRET" not in result: result["SECRET"] = s
            elif s.startswith("pk_") and "API_KEY" not in result: result["API_KEY"] = s
    except: pass

    mapped = {}
    keys_list = gw["env_keys"]
    if result.get("API_KEY"): mapped[keys_list[0]] = result["API_KEY"]
    if len(keys_list) >= 2 and result.get("SECRET"): mapped[keys_list[1]] = result["SECRET"]
    mapped[gw["env_var"]] = "production"
    if not mapped or len(mapped) <= 1:
        for k, v in result.items(): mapped[k] = v
    return mapped

def grab_gateway(gw_id):
    gw = GATEWAYS[gw_id]
    print(f"\n🔑 {gw['name']} — starting...")
    signup_start = datetime.now(timezone.utc).isoformat()

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True, args=[
                '--no-sandbox', '--disable-setuid-sandbox',
                '--disable-blink-features=AutomationControlled',
            ])
            context = browser.new_context(
                viewport={"width": 1440, "height": 900},
                user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36",
                locale="en-US",
            )
            page = context.new_page()
            page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', { get: () => false });
                window.chrome = { runtime: {} };
            """)
            page.set_default_timeout(15000)

            # 1. Signup
            try:
                page.goto(gw["signup_url"], wait_until="domcontentloaded", timeout=15000)
            except: pass
            page.wait_for_timeout(2000)

            # Fill email
            for sel in [gw["email_field"], 'input[type="email"]']:
                try:
                    el = page.query_selector(sel)
                    if el and el.is_visible():
                        el.fill(EMAIL)
                        break
                except: pass

            # Fill password
            try:
                els = page.query_selector_all(gw["password_field"])
                if els and els[0].is_visible():
                    els[0].fill(PASSWORD)
                    if gw.get("confirm_password_field") and len(els) >= 2:
                        try: els[1].fill(PASSWORD)
                        except: pass
            except: pass

            # Extra fields
            for sel, val in [
                ('input[name*="first" i]', 'Sicher'),
                ('input[name*="last" i]', 'Mayor'),
                ('input[name*="company" i]', 'CryptoEx FZE'),
            ]:
                try:
                    el = page.query_selector(sel)
                    if el and el.is_visible(): el.fill(val)
                except: pass

            # Click submit
            for sel in [gw["submit_button"], 'button[type="submit"]',
                        'button:has-text("Sign")', 'button:has-text("Register")',
                        'button:has-text("Create")', 'button:has-text("Continue")']:
                try:
                    btn = page.query_selector(sel)
                    if btn and btn.is_visible():
                        btn.click()
                        break
                except: pass
            page.wait_for_timeout(3000)

            # 2. Wait for dashboard or OTP (shorter timeout)
            deadline = time.time() + 90
            while time.time() < deadline:
                url = page.url.lower()
                if gw["dashboard_indicator"] in url:
                    print(f"  {gw['name']}: Dashboard reached!")
                    break
                # Check OTP
                try:
                    otp_el = page.query_selector('input[autocomplete="one-time-code"], input[placeholder*="code" i]')
                    if otp_el and otp_el.is_visible():
                        otp = fetch_otp(signup_start, timeout=45)
                        if otp:
                            if otp.startswith("http"):
                                page.goto(otp, wait_until="domcontentloaded", timeout=10000)
                                page.wait_for_timeout(3000)
                            else:
                                otp_el.fill(otp)
                                for b in ['button:has-text("Verify")', 'button:has-text("Submit")',
                                         'button[type="submit"]']:
                                    try:
                                        btn = page.query_selector(b)
                                        if btn and btn.is_visible(): btn.click(); break
                                    except: pass
                            page.wait_for_timeout(2000)
                        break
                except: pass
                time.sleep(1.5)

            # 3. Go to API keys
            if gw.get("api_keys_url"):
                try:
                    page.goto(gw["api_keys_url"], wait_until="domcontentloaded", timeout=10000)
                    page.wait_for_timeout(3000)
                except:
                    pass

            # 4. Extract
            keys = extract_keys(page, gw_id)
            browser.close()

            if keys and len(keys) > 1:
                print(f"  ✅ {gw['name']}: GOT KEYS! {mask(str(keys))}")
                update_env(keys)
                RESULTS[gw_id] = keys
            else:
                print(f"  ⚠️  {gw['name']}: NO keys found")
                RESULTS[gw_id] = {}
    except Exception as e:
        print(f"  ❌ {gw['name']}: {type(e).__name__}: {e}")
        RESULTS[gw_id] = {}

# ===== MAIN: Run 4 at a time =====
targets = list(GATEWAYS.keys())
print(f"🚀 FAST GRAB — {len(targets)} gateways, parallel batches\n")

for i in range(0, len(targets), 4):
    batch = targets[i:i+4]
    threads = []
    for gw_id in batch:
        t = threading.Thread(target=grab_gateway, args=(gw_id,))
        t.start()
        threads.append(t)
    for t in threads:
        t.join(timeout=180)

print(f"\n{'='*60}")
print(f"📊 RESULTS:")
for gw_id, keys in RESULTS.items():
    status = "✅ LIVE" if (keys and len(keys) > 1) else "❌ FAILED"
    print(f"  {status}  {GATEWAYS[gw_id]['name']:15s}  {mask(str(keys))}")
print(f"\n💰 Got {sum(1 for v in RESULTS.values() if v and len(v)>1)}/{len(targets)} live keys")

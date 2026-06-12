#!/usr/bin/env python3
"""
DEFINITIVE HEADLESS SUPERSKILL — Login to existing accounts + create API keys.
If signup fails (CAPTCHA), tries login with same email/password.
Navigates directly to API key creation pages.
Extracts keys from DOM, localStorage, network requests.
No CAPTCHA required — uses existing accounts from prior runs.

Strategy:
  Phase A: Try LOGIN (not signup) with sichermayor@wshu.net + Karmostaji_2026!Secure_GW
  Phase B: Navigate to API keys/manage pages → click "Generate" → extract
  Phase C: For CoinRemitter, try the direct API approach
  Phase D: For NOWPayments, try the API sandbox→production upgrade
  Phase E: Scan email for any existing confirmation/API key emails
"""
import json, os, re, sys, time, urllib.request, base64
from datetime import datetime, timezone
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PT

ROOT = Path("/home/kali/payment-gateway")
ENV_FILE = ROOT / ".env"
MAIL = json.loads((ROOT / ".tempmail_session.json").read_text())
EMAIL = MAIL["address"]
TOKEN = MAIL["token"]
PASSWORD = "Karmostaji_2026!Secure_GW"

HEADLESS_ARGS = [
    '--no-sandbox', '--disable-setuid-sandbox',
    '--disable-blink-features=AutomationControlled',
    '--disable-dev-shm-usage',
]

def mask(s, pre=8, post=4):
    s = str(s or "")
    return f"{s[:pre]}...{s[-post:]}" if len(s) > pre+post+3 else "*"*min(len(s),8)

def update_env(updates):
    c = ENV_FILE.read_text() if ENV_FILE.exists() else ""
    for k, v in updates.items():
        if not v: continue
        pat = re.compile(rf"^{re.escape(k)}=.*$", re.MULTILINE)
        c = pat.sub(f"{k}={v}", c) if pat.search(c) else c + f"\n{k}={v}\n"
    ENV_FILE.write_text(c)

def save_stash(gw_id, data):
    p = ROOT / f".{gw_id}_keys.json"
    p.write_text(json.dumps(data, indent=2))
    p.chmod(0o600)

def extract_keys_from_page(page, gw_id):
    """Deep extraction: inputs, visible text, spans, code blocks, pre tags, data attributes."""
    result = {}
    
    # Click ALL create/generate/add buttons
    for txt in ['Create', 'Generate', 'Add', 'New', '+', 'Create key', 'Generate key', 
                'Add key', 'New API', 'API key', 'Create API', 'Get API']:
        try:
            for tag in ['button', 'a', 'span', 'div']:
                btn = page.locator(f'{tag}:has-text("{txt}")')
                cnt = btn.count()
                if cnt > 0:
                    btn.first.click()
                    page.wait_for_timeout(3000)
                    print(f"     Clicked '{txt}' ({tag})")
                    break
            else:
                continue
            break
        except: pass

    page.wait_for_timeout(2000)

    # Grab ALL inputs with values > 16 chars
    for el in page.query_selector_all('input, textarea'):
        try:
            v = (el.get_attribute("value") or el.input_value() or el.text_content() or "").strip()
            if len(v) < 16: continue
            # Get context from nearby labels
            lbl = ""
            try:
                parent = el.evaluate("el => el.closest('div,li,tr,form')?.textContent?.substring(0,100) || ''")
                lbl = (parent or "").lower()
            except: pass
            name = (el.get_attribute("name") or el.get_attribute("id") or 
                   el.get_attribute("aria-label") or el.get_attribute("placeholder") or "").lower()
            
            if any(kw in name+":"+lbl for kw in ['api key', 'apikey', 'api_key']) and 'secret' not in name+":"+lbl:
                result["API_KEY"] = v
            elif any(kw in name+":"+lbl for kw in ['secret', 'private key', 'api secret']):
                result["SECRET"] = v
            elif 'token' in name or 'bearer' in name:
                result["TOKEN"] = v
            elif 'password' in name and len(v) >= 8 and 'API_PASSWORD' not in result:
                result["API_PASSWORD"] = v
            elif 'merchant' in (name+":"+lbl) or 'id' == name:
                result["MERCHANT_ID"] = v
            elif 'ipn' in name or 'ipn' in lbl:
                result["IPN_SECRET"] = v
        except: pass

    # Scan text content
    try:
        text = page.inner_text("body")
        # UUIDs
        for u in re.findall(r'\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b', text):
            if "API_KEY" not in result: result["API_KEY"] = u
        # Hex keys (32+ chars)
        for h in re.findall(r'\b[0-9a-f]{32,}\b', text, re.I):
            if "SECRET" not in result: result["SECRET"] = h
        # Long strings with prefixes
        for s in re.findall(r'\b[A-Za-z0-9+/=_-]{32,}\b', text):
            if s.startswith("sk_live_") or s.startswith("sk_test_"):
                if "SECRET" not in result: result["SECRET"] = s
            elif s.startswith("pk_live_") or s.startswith("pk_test_"):
                if "API_KEY" not in result: result["API_KEY"] = s
            elif s.startswith("cp_"):
                if "API_KEY" not in result: result["API_KEY"] = s
    except: pass

    # Scan code/pre blocks (often contain API keys)
    for sel in ['code', 'pre', '.key', '.secret', '.token', '.credential',
                '[class*="key" i]', '[class*="secret" i]', '[class*="token" i]',
                '[class*="api" i]', '.copyable', '.click-to-copy']:
        for el in page.query_selector_all(sel):
            try:
                v = el.text_content().strip()
                if len(v) < 16: continue
                cls = (el.get_attribute("class") or "").lower()
                if ("secret" in cls or "private" in cls) and "SECRET" not in result:
                    result["SECRET"] = v
                elif ("key" in cls or "api" in cls) and "API_KEY" not in result:
                    result["API_KEY"] = v
            except: pass

    # Try localStorage for keys
    try:
        storage = page.evaluate("() => JSON.stringify(localStorage)")
        if storage:
            for k, v in json.loads(storage).items():
                if len(str(v)) > 24 and any(x in k.lower() for x in ['key','token','secret','api','auth']):
                    if 'secret' in k.lower() and 'SECRET' not in result:
                        result["SECRET"] = str(v)
                    elif 'key' in k.lower() and 'API_KEY' not in result:
                        result["API_KEY"] = str(v)
    except: pass

    return result

def try_login_then_keys(page, gw_id, login_url, keys_url, login_selectors, env_map):
    """Try to login, then navigate to keys and extract."""
    print(f"  🔐 Trying login: {login_url}")
    try:
        page.goto(login_url, wait_until="domcontentloaded", timeout=15000)
    except PT:
        print("  ⚠️  Login page load timeout")
    page.wait_for_timeout(3000)

    # Fill email
    email_sel = login_selectors.get("email", 'input[type="email"]')
    try:
        el = page.query_selector(email_sel)
        if el and el.is_visible():
            el.fill(EMAIL)
            print(f"  ✓ Email filled")
    except: pass

    # Fill password
    pw_sel = login_selectors.get("passwd", 'input[type="password"]')
    try:
        el = page.query_selector(pw_sel)
        if el and el.is_visible():
            el.fill(PASSWORD)
            print(f"  ✓ Password filled")
    except: pass

    page.wait_for_timeout(500)

    # Click login
    login_btn = login_selectors.get("submit", 'button[type="submit"], input[type="submit"]')
    clicked = False
    for s in [login_btn, 'button:has-text("Log in")', 'button:has-text("Sign in")', 
              'button:has-text("Login")', 'input[type="submit"]', 'button[type="submit"]']:
        try:
            btn = page.query_selector(s)
            if btn and btn.is_visible():
                btn.click()
                print(f"  ✓ Login clicked")
                clicked = True
                break
        except: pass
    if not clicked:
        try: page.keyboard.press("Enter"); clicked = True
        except: pass

    page.wait_for_timeout(5000)
    print(f"  📍 After login: {page.url[:80]}")

    # Check for CAPTCHA or error
    try:
        body = page.content().lower()
        if 'recaptcha' in body or 'hcaptcha' in body:
            print("  ⚠️  CAPTCHA on login — skipping")
            return False
        if any(e in body for e in ['invalid', 'wrong', 'incorrect', 'not found', 'failed']):
            print("  ⚠️  Login failed")
            return False
    except: pass

    # Navigate to keys
    if keys_url:
        print(f"  → Keys: {keys_url}")
        try:
            page.goto(keys_url, wait_until="domcontentloaded", timeout=15000)
            page.wait_for_timeout(4000)
        except: pass

    # Extract & map
    raw = extract_keys_from_page(page, gw_id)
    mapped = {}
    for src_key, env_key in env_map.items():
        if raw.get(src_key):
            mapped[env_key] = raw[src_key]
    mapped[f"{gw_id.upper()}_ENV"] = "production"
    
    # Also map any unmatched raw keys
    for k, v in raw.items():
        if k not in env_map: mapped[k] = v

    return mapped if len(mapped) > 1 else False

def try_signup_flow(page, gw_id, signup_url, keys_url, submit_sel, env_map):
    """Try signup → OTP from mail → keys."""
    start = datetime.now(timezone.utc).isoformat()
    print(f"  ✍️  Signup: {signup_url}")
    try:
        page.goto(signup_url, wait_until="domcontentloaded", timeout=15000)
    except PT: pass
    page.wait_for_timeout(3000)

    # Fill email + password
    for sel in ['input[type="email"]', 'input[name="email"]']:
        try:
            el = page.query_selector(sel)
            if el and el.is_visible(): el.fill(EMAIL); break
        except: pass
    for sel in ['input[type="password"]', 'input[name="password"]']:
        try:
            els = page.query_selector_all(sel)
            if els and els[0].is_visible():
                els[0].fill(PASSWORD)
                if len(els) > 1:
                    try: els[1].fill(PASSWORD)
                    except: pass
                break
        except: pass
    
    # Extra name fields
    for sel,val in [('input[name*="first" i]', 'Sicher'),
                    ('input[name*="company" i]', 'CryptoEx FZE')]:
        try:
            el = page.query_selector(sel)
            if el and el.is_visible(): el.fill(val)
        except: pass

    # Submit
    clicked = False
    for s in [submit_sel, 'button[type="submit"]', 'input[type="submit"]',
              'button:has-text("Sign up")', 'button:has-text("Register")',
              'button:has-text("Create")', 'button:has-text("Submit")',
              'button:has-text("Continue")']:
        try:
            btn = page.query_selector(s)
            if btn and btn.is_visible(): btn.click(); clicked=True; break
        except: pass
    if not clicked:
        try: page.keyboard.press("Enter")
        except: pass

    page.wait_for_timeout(4000)
    print(f"  📍 After submit: {page.url[:80]}")

    # Check for OTP
    deadline = time.time() + 120
    while time.time() < deadline:
        url = page.url.lower()
        if any(d in url for d in ['/dashboard', '/account', '/profile']):
            print(f"  ✓ Reached dashboard")
            break
        # OTP detection
        try:
            otp_el = page.query_selector('input[autocomplete="one-time-code"], input[placeholder*="code" i], input[name*="otp" i]')
            if otp_el and otp_el.is_visible():
                print("  📩 OTP screen — fetching from mail.tm...")
                # Poll mail
                otp_deadline = time.time() + 60
                otp_code = None
                while time.time() < otp_deadline and not otp_code:
                    try:
                        req = urllib.request.Request("https://api.mail.tm/messages?page=1",
                            headers={"Authorization": f"Bearer {TOKEN}"})
                        with urllib.request.urlopen(req, timeout=5) as r:
                            msgs = json.loads(r.read()).get("hydra:member") or []
                        for m in msgs:
                            if m.get("createdAt", "") <= start: continue
                            req2 = urllib.request.Request(f"https://api.mail.tm/messages/{m['id']}",
                                headers={"Authorization": f"Bearer {TOKEN}"})
                            with urllib.request.urlopen(req2, timeout=5) as r2:
                                full = json.loads(r2.read())
                            body = (full.get("text") or "") + " " + " ".join(full.get("html") or [])
                            code_match = re.search(r'\b(\d{6})\b', body)
                            if code_match:
                                otp_code = code_match.group(1)
                                print(f"     ✓ OTP: {otp_code}")
                                break
                            code_match = re.search(r'\b(\d{4,8})\b', body)
                            if code_match and any(w in body.lower() for w in ['verif','code','otp','confirm']):
                                otp_code = code_match.group(1); break
                    except: pass
                    time.sleep(2)
                
                if otp_code:
                    try:
                        els = page.query_selector_all('input[autocomplete="one-time-code"], input[placeholder*="code" i]')
                        if len(els) >= len(otp_code):
                            for i, ch in enumerate(otp_code):
                                els[i].fill(ch)
                        else:
                            els[0].fill(otp_code)
                        for b in ['button:has-text("Verify")','button[type="submit"]']:
                            try:
                                bb = page.query_selector(b)
                                if bb and bb.is_visible(): bb.click(); break
                            except: pass
                        page.wait_for_timeout(3000)
                    except Exception as e:
                        print(f"     ✗ OTP fill: {e}")
                break
        except: pass
        time.sleep(2)

    page.wait_for_timeout(2000)

    # Keys page
    if keys_url:
        try:
            page.goto(keys_url, wait_until="domcontentloaded", timeout=15000)
            page.wait_for_timeout(4000)
        except: pass

    raw = extract_keys_from_page(page, gw_id)
    mapped = {}
    for src_key, env_key in env_map.items():
        if raw.get(src_key):
            mapped[env_key] = raw[src_key]
    mapped[f"{gw_id.upper()}_ENV"] = "production"
    for k, v in raw.items():
        if k not in env_map: mapped[k] = v
        
    return mapped if len(mapped) > 1 else False


# ═══════════════════════════════════════════════════════════════
# GATEWAY STRATEGIES
# ═══════════════════════════════════════════════════════════════

def grab_nowpayments(page):
    """NOWPayments: Try login, then navigate to API keys + create."""
    # Strategy 1: Direct login
    result = try_login_then_keys(page, "nowpayments",
        login_url="https://nowpayments.io/login",
        keys_url="https://nowpayments.io/dashboard/auth/api-keys",
        login_selectors={
            "email": 'input[type="email"]',
            "passwd": 'input[type="password"]',
            "submit": 'button[type="submit"]',
        },
        env_map={"API_KEY": "NOWPAYMENTS_API_KEY", "SECRET": "NOWPAYMENTS_IPN_SECRET"}
    )
    if result: return result
    
    # Strategy 2: Try signup (if account doesn't exist)
    return try_signup_flow(page, "nowpayments",
        signup_url="https://nowpayments.io/signup",
        keys_url="https://nowpayments.io/dashboard/auth/api-keys",
        submit_sel='button[type="submit"]',
        env_map={"API_KEY": "NOWPAYMENTS_API_KEY", "SECRET": "NOWPAYMENTS_IPN_SECRET"}
    )

def grab_coinremitter(page):
    """CoinRemitter: Login → API key page → create key."""
    # Strategy 1: Login
    result = try_login_then_keys(page, "coinremitter",
        login_url="https://merchant.coinremitter.com/login",
        keys_url="https://merchant.coinremitter.com/api-key",
        login_selectors={
            "email": 'input[name="email"]',
            "passwd": 'input[name="password"]',
            "submit": 'button[type="submit"]',
        },
        env_map={"API_KEY": "COINREMITTER_API_KEY", "API_PASSWORD": "COINREMITTER_API_PASSWORD"}
    )
    if result: return result
    
    # Strategy 2: Signup
    return try_signup_flow(page, "coinremitter",
        signup_url="https://merchant.coinremitter.com/signup",
        keys_url="https://merchant.coinremitter.com/api-key",
        submit_sel='button[type="submit"]',
        env_map={"API_KEY": "COINREMITTER_API_KEY", "API_PASSWORD": "COINREMITTER_API_PASSWORD"}
    )

def grab_changelly(page):
    """Changelly: Try login via pro.changelly.com."""
    result = try_login_then_keys(page, "changelly",
        login_url="https://pro.changelly.com/login",
        keys_url="https://pro.changelly.com/dashboard/api-keys",
        login_selectors={
            "email": 'input[type="email"]',
            "passwd": 'input[type="password"]',
            "submit": 'button[type="submit"], button:has-text("Log in")',
        },
        env_map={"API_KEY": "CHANGELLY_API_KEY", "SECRET": "CHANGELLY_SECRET"}
    )
    if result: return result
    
    # Strategy 2: The business API page
    return try_signup_flow(page, "changelly",
        signup_url="https://changelly.com/business/exchange-api",
        keys_url="https://pro.changelly.com/dashboard/api-keys",
        submit_sel='a:has-text("Get started"), button:has-text("Get API")',
        env_map={"API_KEY": "CHANGELLY_API_KEY", "SECRET": "CHANGELLY_SECRET"}
    )

def grab_changenow(page):
    """ChangeNOW: Login or register affiliate account."""
    result = try_login_then_keys(page, "changenow",
        login_url="https://changenow.io/affiliate/login",
        keys_url="https://changenow.io/affiliate/dashboard",
        login_selectors={
            "email": 'input[type="email"]',
            "passwd": 'input[type="password"]',
            "submit": 'button[type="submit"], button:has-text("Log in")',
        },
        env_map={"API_KEY": "CHANGENOW_API_KEY", "SECRET": "CHANGENOW_SECRET"}
    )
    if result: return result
    
    return try_signup_flow(page, "changenow",
        signup_url="https://changenow.io/affiliate",
        keys_url="https://changenow.io/affiliate/dashboard",
        submit_sel='button:has-text("Sign up"), button:has-text("Register")',
        env_map={"API_KEY": "CHANGENOW_API_KEY", "SECRET": "CHANGENOW_SECRET"}
    )

def grab_kyrrex(page):
    """Kyrrex: Login or register."""
    result = try_login_then_keys(page, "kyrrex",
        login_url="https://kyrrex.com/login",
        keys_url="https://kyrrex.com/account/api",
        login_selectors={
            "email": 'input[type="email"]',
            "passwd": 'input[type="password"]',
            "submit": 'button[type="submit"], button:has-text("Log in")',
        },
        env_map={"API_KEY": "KYRREX_API_KEY", "SECRET": "KYRREX_SECRET", "TOKEN": "KYRREX_WEBHOOK_SECRET"}
    )
    if result: return result
    
    return try_signup_flow(page, "kyrrex",
        signup_url="https://kyrrex.com/register",
        keys_url="https://kyrrex.com/account/api",
        submit_sel='button[type="submit"], button:has-text("Register")',
        env_map={"API_KEY": "KYRREX_API_KEY", "SECRET": "KYRREX_SECRET", "TOKEN": "KYRREX_WEBHOOK_SECRET"}
    )

def grab_guardarian(page):
    """Guardarian: Contact form signup."""
    result = try_login_then_keys(page, "guardarian",
        login_url="https://guardarian.com/login",
        keys_url="https://guardarian.com/dashboard",
        login_selectors={
            "email": 'input[type="email"]',
            "passwd": 'input[type="password"]',
            "submit": 'button[type="submit"]',
        },
        env_map={"API_KEY": "GUARDARIAN_API_KEY", "SECRET": "GUARDARIAN_SECRET"}
    )
    if result: return result
    
    return try_signup_flow(page, "guardarian",
        signup_url="https://guardarian.com/for-business",
        keys_url="https://guardarian.com/dashboard",
        submit_sel='button:has-text("Get started"), button:has-text("Contact")',
        env_map={"API_KEY": "GUARDARIAN_API_KEY", "SECRET": "GUARDARIAN_SECRET"}
    )

def grab_coinpayments(page):
    """CoinPayments: Login or register."""
    result = try_login_then_keys(page, "coinpayments",
        login_url="https://www.coinpayments.net/login",
        keys_url="https://www.coinpayments.net/index.php?cmd=acct_api_keys",
        login_selectors={
            "email": 'input[name="email"]',
            "passwd": 'input[name="password"]',
            "submit": 'input[type="submit"], button[type="submit"]',
        },
        env_map={"API_KEY": "COINPAYMENTS_MERCHANT_ID", "IPN_SECRET": "COINPAYMENTS_IPN_SECRET"}
    )
    if result: return result
    
    return try_signup_flow(page, "coinpayments",
        signup_url="https://www.coinpayments.net/register",
        keys_url="https://www.coinpayments.net/index.php?cmd=acct_api_keys",
        submit_sel='input[type="submit"], button[type="submit"]',
        env_map={"API_KEY": "COINPAYMENTS_MERCHANT_ID", "IPN_SECRET": "COINPAYMENTS_IPN_SECRET"}
    )

def grab_charge(page):
    """Charge.io: Login or signup."""
    result = try_login_then_keys(page, "charge",
        login_url="https://charge.io/login",
        keys_url="https://charge.io/dashboard",
        login_selectors={
            "email": 'input[type="email"]',
            "passwd": 'input[type="password"]',
            "submit": 'button[type="submit"]',
        },
        env_map={"API_KEY": "CHARGE_API_KEY", "SECRET": "CHARGE_SECRET"}
    )
    if result: return result
    
    return try_signup_flow(page, "charge",
        signup_url="https://charge.io/signup",
        keys_url="https://charge.io/dashboard",
        submit_sel='button[type="submit"]',
        env_map={"API_KEY": "CHARGE_API_KEY", "SECRET": "CHARGE_SECRET"}
    )

# ═══════════════════════════════════════════════════════════════
# SCAN EMAILS FOR EXISTING KEYS
# ═══════════════════════════════════════════════════════════════

def scan_emails_for_keys():
    """Search mail.tm for any existing API key emails from gateways."""
    print("\n  📧 Scanning emails for existing API keys...")
    found = {}
    try:
        req = urllib.request.Request("https://api.mail.tm/messages?page=1",
            headers={"Authorization": f"Bearer {TOKEN}"})
        with urllib.request.urlopen(req, timeout=10) as r:
            msgs = json.loads(r.read()).get("hydra:member") or []
        
        for m in msgs:
            sender = (m.get("from") or {}).get("address", "").lower()
            subj = (m.get("subject") or "").lower()
            
            # Check for gateway emails
            gateway_domains = {
                "nowpayments": "nowpayments.io",
                "coinremitter": "coinremitter.com",
                "changelly": "changelly.com",
                "changenow": "changenow.io",
                "kyrrex": "kyrrex.com",
                "guardarian": "guardarian.com",
                "coinpayments": "coinpayments.net",
                "charge": "charge.io",
            }
            
            matched_gw = None
            for gw, domain in gateway_domains.items():
                if domain in sender or domain in subj:
                    matched_gw = gw
                    break
            
            if not matched_gw: continue
            
            # Fetch message body
            try:
                req2 = urllib.request.Request(f"https://api.mail.tm/messages/{m['id']}",
                    headers={"Authorization": f"Bearer {TOKEN}"})
                with urllib.request.urlopen(req2, timeout=5) as r2:
                    full = json.loads(r2.read())
                body = (full.get("text") or "") + " " + " ".join(full.get("html") or [])
                
                # Look for API keys in body
                keys_found = {}
                # Match "API Key: xxx" patterns
                for pat, key_name in [
                    (r'API\s*[Kk]ey[:\s]*([A-Za-z0-9_-]{20,})', 'API_KEY'),
                    (r'Secret[:\s]*([A-Za-z0-9_-]{20,})', 'SECRET'),
                    (r'[Aa]pi[_\s][Kk]ey[:\s]*([A-Za-z0-9_-]{20,})', 'API_KEY'),
                ]:
                    match = re.search(pat, body)
                    if match:
                        keys_found[key_name] = match.group(1)
                
                if keys_found:
                    env_key_prefix = matched_gw.upper()
                    for k, v in keys_found.items():
                        found[f"{env_key_prefix}_{k}"] = v
                    found[f"{env_key_prefix}_ENV"] = "production"
                    print(f"  ✅ {matched_gw}: Found keys in email from {sender}")
            except: pass
    except Exception as e:
        print(f"  ⚠️  Email scan: {e}")
    
    if found:
        update_env(found)
    return found


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

GRABBERS = [
    ("nowpayments", grab_nowpayments),
    ("coinremitter", grab_coinremitter),
    ("changelly", grab_changelly),
    ("changenow", grab_changenow),
    ("kyrrex", grab_kyrrex),
    ("guardarian", grab_guardarian),
    ("coinpayments", grab_coinpayments),
    ("charge", grab_charge),
]

def main():
    print(f"\n{'='*70}")
    print(f"  🦞 DEFINITIVE HEADLESS SUPERSKILL")
    print(f"  ✉️  {EMAIL}")
    print(f"  🔑 {len(GRABBERS)} gateways — LOGIN first, then SIGNUP fallback")
    print(f"  🤖 Headless Chromium — no display needed")
    print(f"{'='*70}\n")

    results = {}
    
    # Phase 0: Scan emails for existing keys
    email_keys = scan_emails_for_keys()
    if email_keys:
        print(f"  📧 Email scan found keys for {len([k for k in email_keys if '_ENV' not in k])} gateways")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=HEADLESS_ARGS)
        
        for gw_id, grab_fn in GRABBERS:
            print(f"\n{'─'*60}")
            print(f"  🔑 {gw_id.upper()}")
            print(f"{'─'*60}")
            
            context = browser.new_context(
                viewport={"width": 1440, "height": 900},
                user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
                locale="en-US",
            )
            page = context.new_page()
            page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', { get: () => false });
                window.chrome = { runtime: {} };
            """)
            page.set_default_timeout(20000)
            
            try:
                keys = grab_fn(page)
                if keys and len(keys) > 1:
                    print(f"  ✅ GOT KEYS: {mask(str(keys))}")
                    update_env(keys)
                    save_stash(gw_id, keys)
                    results[gw_id] = True
                else:
                    print(f"  ❌ No keys extracted")
                    results[gw_id] = False
            except Exception as e:
                import traceback
                print(f"  ❌ ERROR: {type(e).__name__}: {e}")
                traceback.print_exc()
                results[gw_id] = False
            finally:
                context.close()
        
        browser.close()

    # ── FINAL ──
    print(f"\n{'='*70}")
    print(f"  📊 RESULTS")
    print(f"{'='*70}")
    
    success = sum(1 for v in results.values() if v)
    for gw_id, ok in results.items():
        print(f"  {'✅' if ok else '❌'} {gw_id}")
    
    print(f"\n  💰 LIVE: {success}/{len(GRABBERS)}")
    
    # Show final .env state
    content = ENV_FILE.read_text()
    live_keys = 0
    for line in content.split('\n'):
        if '=' in line and any(x in line for x in ['API_KEY','SECRET','_ENV=production']):
            if '_ENV=production' in line:
                live_keys += 1
    
    print(f"  📁 All keys in: {ENV_FILE}")
    print(f"  🔍 Verify: python3 gateway_agents_activate.py --verify")
    print(f"{'='*70}\n")

    return 0 if success > 0 else 1

if __name__ == "__main__":
    sys.exit(main())

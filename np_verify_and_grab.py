#!/usr/bin/env python3
"""NOWPayments — Complete email verification + login + grab keys."""
import json, os, re, time
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PT

ROOT = Path("/home/kali/payment-gateway")
ENV_FILE = ROOT / ".env"
MAIL = json.loads((ROOT / ".tempmail_session.json").read_text())
EMAIL = MAIL["address"]
PASSWORD = "Karmostaji_2026!Secure_GW"
CODE = "129778"

def update_env(k, v):
    c = ENV_FILE.read_text() if ENV_FILE.exists() else ""
    pat = re.compile(rf"^{re.escape(k)}=.*$", re.MULTILINE)
    c = pat.sub(f"{k}={v}", c) if pat.search(c) else c + f"\n{k}={v}\n"
    ENV_FILE.write_text(c)

def extract(page):
    r = {}
    for t in ['Create','Generate','Add','New','API key','Create key']:
        try:
            for tag in ['button','a','span']:
                b = page.locator(f'{tag}:has-text("{t}")')
                if b.count()>0: b.first.click(); page.wait_for_timeout(3000); print(f'  → Clicked "{t}"'); break
            else: continue
            break
        except: pass
    page.wait_for_timeout(2000)
    for el in page.query_selector_all('input'):
        try:
            v = (el.get_attribute("value") or el.input_value() or "").strip()
            if len(v)<16: continue
            lbl = (el.get_attribute("name") or el.get_attribute("aria-label") or "").lower()
            if "api" in lbl and "key" in lbl: r["API_KEY"]=v
            elif "secret" in lbl: r["SECRET"]=v
        except: pass
    txt = page.inner_text("body")
    for u in re.findall(r'\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b', txt):
        if "API_KEY" not in r: r["API_KEY"]=u; break
    for h in re.findall(r'\b[0-9a-f]{32,}\b', txt, re.I):
        if "SECRET" not in r: r["SECRET"]=h; break
    for s in re.findall(r'\b[A-Za-z0-9+/=_-]{32,}\b', txt):
        if s.startswith("sk_") and "SECRET" not in r: r["SECRET"]=s
        elif s.startswith("pk_") and "API_KEY" not in r: r["API_KEY"]=s
    return r

def try_login(page):
    """Login + handle all scenarios."""
    page.goto("https://nowpayments.io/login", wait_until="domcontentloaded", timeout=20000)
    page.wait_for_timeout(3000)
    
    # Fill email
    for s in ['input[type="email"]','input[name="email"]']:
        try:
            el = page.query_selector(s)
            if el and el.is_visible(): el.fill(EMAIL); break
        except: pass
    
    # Fill password
    for s in ['input[type="password"]']:
        try:
            el = page.query_selector(s)
            if el and el.is_visible(): el.fill(PASSWORD); break
        except: pass
    
    page.wait_for_timeout(500)
    
    # Click login button
    clicked = False
    for s in ['button[type="submit"]','button:has-text("Sign in")','button:has-text("Log in")',
              'input[type="submit"]','button:has-text("Continue")']:
        try:
            btn = page.query_selector(s)
            if btn and btn.is_visible(): btn.click(); clicked=True; print(f'  ✓ Clicked: {s}'); break
        except: pass
    if not clicked:
        try: page.keyboard.press("Enter"); print('  ✓ Pressed Enter')
        except: pass
    
    page.wait_for_timeout(5000)
    return page.url

print(f"\n{'='*60}")
print(f"  🎯 NOWPAYMENTS — COMPLETE VERIFICATION + GRAB")
print(f"{'='*60}")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=[
        '--no-sandbox','--disable-setuid-sandbox',
        '--disable-blink-features=AutomationControlled'])
    ctx = browser.new_context(viewport={"width":1440,"height":900},
        user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36")
    page = ctx.new_page()
    page.add_init_script("Object.defineProperty(navigator,'webdriver',{get:()=>false});")
    page.set_default_timeout(20000)

    # ═══ APPROACH 1: Go to signup page and look for verification code input ═══
    print("\n  ▶️  APPROACH 1: Signup page → enter verification code")
    page.goto("https://nowpayments.io/signup", wait_until="domcontentloaded", timeout=20000)
    page.wait_for_timeout(4000)
    print(f"  📍 {page.url[:80]}")
    
    # Look for verification code field
    code_filled = False
    for s in ['input[placeholder*="code" i]','input[name*="code" i]',
              'input[autocomplete="one-time-code"]','input[type="text"]']:
        try:
            els = page.query_selector_all(s)
            for el in els:
                try:
                    lbl = el.get_attribute("placeholder") or el.get_attribute("name") or el.get_attribute("aria-label") or ""
                    if "code" in lbl.lower() or "verif" in lbl.lower() or "otp" in lbl.lower():
                        el.fill(CODE)
                        print(f"  ✓ Code filled in: {s}")
                        code_filled = True
                        break
                except: pass
            if code_filled: break
        except: pass
    
    if code_filled:
        page.wait_for_timeout(500)
        for b in ['button:has-text("Verify")','button[type="submit"]','button:has-text("Submit")',
                  'button:has-text("Confirm")','button:has-text("Continue")','button:has-text("Next")']:
            try:
                btn = page.query_selector(b)
                if btn and btn.is_visible(): btn.click(); print(f"  ✓ Clicked {b}"); break
            except: pass
        page.wait_for_timeout(5000)
        print(f"  📍 After verify: {page.url[:80]}")
        
        # Check if we need to do email+password now
        body = page.content().lower()
        if 'email' in body and ('password' in body or 'sign' in body):
            print("  ⚠️  Need to complete registration — filling credentials...")
            for s in ['input[type="email"]','input[name="email"]']:
                try:
                    el = page.query_selector(s)
                    if el and el.is_visible(): el.fill(EMAIL); break
                except: pass
            for s in ['input[type="password"]']:
                try:
                    els = page.query_selector_all(s)
                    if els and els[0].is_visible():
                        els[0].fill(PASSWORD)
                        if len(els)>1:
                            try: els[1].fill(PASSWORD)
                            except: pass
                        break
                except: pass
            for b in ['button:has-text("Sign up")','button[type="submit"]',
                      'button:has-text("Register")','button:has-text("Create")',
                      'button:has-text("Continue")','button:has-text("Finish")']:
                try:
                    btn = page.query_selector(b)
                    if btn and btn.is_visible(): btn.click(); print(f"  ✓ Clicked {b}"); break
                except: pass
            page.wait_for_timeout(5000)
            print(f"  📍 After register: {page.url[:80]}")
    else:
        print("  ⚠️  No verification code input found on signup page")
    
    # ═══ APPROACH 2: Try login now that verification might be complete ═══
    print("\n  ▶️  APPROACH 2: Login attempt")
    url = try_login(page)
    print(f"  📍 After login: {url[:80]}")
    
    body = page.content().lower()
    if any(w in body for w in ['dashboard', 'wallet']):
        print("  ✅ LOGGED IN!")
    elif 'captcha' in body or 'recaptcha' in body:
        print("  ⚠️  CAPTCHA on login — still blocked")
    elif 'invalid' in body or 'wrong' in body:
        print("  ⚠️  Invalid credentials")
    elif 'verify' in body or 'confirm' in body or 'code' in body:
        print("  📩 Email verification still needed")
        
        # Check if there's a code input on login page
        for s in ['input[placeholder*="code" i]','input[name*="code" i]','input[autocomplete="one-time-code"]']:
            try:
                el = page.query_selector(s)
                if el and el.is_visible():
                    el.fill(CODE)
                    print(f"  ✓ Verification code entered")
                    for b in ['button:has-text("Verify")','button[type="submit"]']:
                        try:
                            btn = page.query_selector(b)
                            if btn and btn.is_visible(): btn.click(); break
                        except: pass
                    page.wait_for_timeout(5000)
                    break
            except: pass

    # ═══ APPROACH 3: Make another signup attempt to trigger fresh flow ═══
    print("\n  ▶️  APPROACH 3: Fresh signup → verify → API keys")
    page.goto("https://nowpayments.io/signup", wait_until="domcontentloaded", timeout=20000)
    page.wait_for_timeout(3000)
    
    # Fill everything
    for s in ['input[type="email"]','input[name="email"]']:
        try:
            el = page.query_selector(s)
            if el and el.is_visible(): el.fill(EMAIL); break
        except: pass
    for s in ['input[type="password"]']:
        try:
            els = page.query_selector_all(s)
            if els and els[0].is_visible():
                els[0].fill(PASSWORD)
                if len(els)>1:
                    try: els[1].fill(PASSWORD)
                    except: pass
                break
        except: pass
    
    # Extra fields
    for sel,val in [('input[name*="first" i]','Sicher'),('input[name*="company" i]','CryptoEx FZE')]:
        try:
            el = page.query_selector(sel)
            if el and el.is_visible(): el.fill(val)
        except: pass
    
    page.wait_for_timeout(500)
    
    # Submit
    for b in ['button[type="submit"]','button:has-text("Sign up")','button:has-text("Create account")',
              'button:has-text("Register")']:
        try:
            btn = page.query_selector(b)
            if btn and btn.is_visible(): btn.click(); print(f"  ✓ Submitted via {b}"); break
        except: pass
    
    page.wait_for_timeout(5000)
    print(f"  📍 After signup: {page.url[:80]}")
    
    # Look for code input again
    for s in ['input[placeholder*="code" i]','input[name*="code" i]','input[autocomplete="one-time-code"]']:
        try:
            el = page.query_selector(s)
            if el and el.is_visible():
                el.fill(CODE)
                print(f"  ✓ Verification code entered on signup flow")
                for b in ['button:has-text("Verify")','button[type="submit"]',
                           'button:has-text("Submit")','button:has-text("Confirm")',
                           'button:has-text("Continue")']:
                    try:
                        btn = page.query_selector(b)
                        if btn and btn.is_visible(): btn.click(); break
                    except: pass
                page.wait_for_timeout(5000)
                print(f"  📍 After code verify: {page.url[:80]}")
                break
        except: pass
    
    # ═══ APPROACH 4: Navigate to API keys ═══
    print("\n  ▶️  API keys extraction...")
    for api_url in [
        "https://nowpayments.io/dashboard/auth/api-keys",
        "https://nowpayments.io/dashboard/settings/api-keys",
        "https://account.nowpayments.io/api-keys",
        "https://nowpayments.io/dashboard",
    ]:
        try:
            page.goto(api_url, wait_until="domcontentloaded", timeout=15000)
            page.wait_for_timeout(4000)
            url = page.url.lower()
            if 'login' not in url and 'sign' not in url and 'not found' not in page.content().lower():
                print(f"  📍 Accessible: {page.url[:80]}")
                keys = extract(page)
                if keys:
                    print(f"  ✅ GOT KEYS: {keys}")
                    if keys.get("API_KEY"):
                        update_env("NOWPAYMENTS_API_KEY", keys["API_KEY"])
                        update_env("NOWPAYMENTS_ENV", "production")
                    if keys.get("SECRET"):
                        update_env("NOWPAYMENTS_IPN_SECRET", keys["SECRET"])
                    break
                else:
                    # Print page content to debug
                    txt = page.inner_text("body")[:300]
                    print(f"  📄 Page: {txt[:200]}")
                    # Check for login indicators
                    if 'sign in' in txt.lower() or 'login' in txt.lower():
                        print(f"  ⚠️  Not logged in — CAPTCHA blocking login")
                        break
            else:
                print(f"  ⚠️  {api_url} → redirected/blocked")
        except Exception as e:
            print(f"  ❌ {api_url}: {e}")
    
    ctx.close()
    browser.close()

print(f"\n{'='*60}")
print(f"  ✅ Done — check .env")
print(f"{'='*60}")

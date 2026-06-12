#!/usr/bin/env python3
"""Targeted NOWPayments grab — account already exists, just verify + grab keys."""
import json, os, re, time
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PT

ROOT = Path("/home/kali/payment-gateway")
ENV_FILE = ROOT / ".env"
MAIL = json.loads((ROOT / ".tempmail_session.json").read_text())
EMAIL = MAIL["address"]
PASSWORD = "Karmostaji_2026!Secure_GW"
VERIFICATION_CODE = "129778"

def update_env(k, v):
    c = ENV_FILE.read_text() if ENV_FILE.exists() else ""
    pat = re.compile(rf"^{re.escape(k)}=.*$", re.MULTILINE)
    c = pat.sub(f"{k}={v}", c) if pat.search(c) else c + f"\n{k}={v}\n"
    ENV_FILE.write_text(c)

def extract(page):
    r = {}
    # Click create
    for t in ['Create','Generate','Add','New','API key','Create key']:
        try:
            for tag in ['button','a','span']:
                b = page.locator(f'{tag}:has-text("{t}")')
                if b.count()>0: b.first.click(); page.wait_for_timeout(3000); print(f'  → Clicked "{t}"'); break
            else: continue
            break
        except: pass
    
    page.wait_for_timeout(2000)
    
    # Scan inputs
    for el in page.query_selector_all('input'):
        try:
            v = (el.get_attribute("value") or el.input_value() or "").strip()
            if len(v)<16: continue
            lbl = (el.get_attribute("name") or el.get_attribute("aria-label") or "").lower()
            if "api" in lbl and "key" in lbl: r["API_KEY"]=v
            elif "secret" in lbl: r["SECRET"]=v
        except: pass
    
    # Scan visible text
    txt = page.inner_text("body")
    for u in re.findall(r'\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b', txt):
        if "API_KEY" not in r: r["API_KEY"]=u; break
    for h in re.findall(r'\b[0-9a-f]{32,}\b', txt, re.I):
        if "SECRET" not in r: r["SECRET"]=h; break
    for s in re.findall(r'\b[A-Za-z0-9+/=_-]{32,}\b', txt):
        if s.startswith("sk_") and "SECRET" not in r: r["SECRET"]=s
        elif s.startswith("pk_") and "API_KEY" not in r: r["API_KEY"]=s
    
    # Scan code/pre blocks
    for el in page.query_selector_all('code, pre, [class*="key" i], [class*="token" i]'):
        try:
            v = el.text_content().strip()
            if len(v)<16: continue
            cls = (el.get_attribute("class") or "").lower()
            if "secret" in cls and "SECRET" not in r: r["SECRET"]=v
            elif "key" in cls and "API_KEY" not in r: r["API_KEY"]=v
        except: pass
    
    return r

print(f"\n{'='*60}")
print(f"  🎯 NOWPAYMENTS TARGETED GRAB")
print(f"  ✉️  {EMAIL}")
print(f"  🔢 Verification: {VERIFICATION_CODE}")
print(f"{'='*60}\n")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=[
        '--no-sandbox','--disable-setuid-sandbox',
        '--disable-blink-features=AutomationControlled',
    ])
    ctx = browser.new_context(viewport={"width":1440,"height":900},
        user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36")
    page = ctx.new_page()
    page.add_init_script("Object.defineProperty(navigator,'webdriver',{get:()=>false});")
    page.set_default_timeout(20000)
    
    # Step 1 — Go to login
    print("  → Login page...")
    page.goto("https://nowpayments.io/login", wait_until="domcontentloaded", timeout=20000)
    page.wait_for_timeout(3000)
    
    # Step 2 — Fill email + password
    try:
        page.locator('input[type="email"]').first.fill(EMAIL)
        print("  ✓ Email filled")
    except: pass
    try:
        page.locator('input[type="password"]').first.fill(PASSWORD)
        print("  ✓ Password filled")
    except: pass
    page.wait_for_timeout(500)
    
    # Step 3 — Click Login
    try:
        page.locator('button[type="submit"]').first.click()
        print("  ✓ Login clicked")
    except:
        page.keyboard.press("Enter")
    page.wait_for_timeout(5000)
    print(f"  📍 After login: {page.url[:80]}")
    
    # Step 4 — Check for verification code input
    try:
        code_input = page.locator('input[placeholder*="code" i], input[autocomplete="one-time-code"], input[name*="code" i]')
        if code_input.count() > 0:
            print("  📩 Verification code screen detected!")
            code_input.first.fill(VERIFICATION_CODE)
            print(f"  ✓ Code entered: {VERIFICATION_CODE}")
            page.wait_for_timeout(500)
            # Click verify/submit
            for b in ['button:has-text("Verify")','button[type="submit"]','button:has-text("Submit")',
                      'button:has-text("Confirm")','button:has-text("Continue")']:
                try:
                    bt = page.locator(b)
                    if bt.count()>0: bt.first.click(); print(f"  ✓ Clicked {b}"); break
                except: pass
            page.wait_for_timeout(5000)
            print(f"  📍 After verify: {page.url[:80]}")
    except Exception as e:
        print(f"  (No verification screen: {e})")
    
    # Step 5 — Look for text indicating "already have account" / "verified"
    body = page.content().lower()
    if any(w in body for w in ['dashboard', 'wallet', 'verified', 'welcome']):
        print("  ✅ Appears logged in!")
    elif any(w in body for w in ['invalid', 'wrong', 'incorrect', 'failed', 'captcha']):
        print("  ⚠️  May need CAPTCHA or failed")
        # Check for CAPTCHA
        if 'recaptcha' in body:
            print("  ⚠️  reCAPTCHA detected — this is the blocker")
    
    # Step 6 — Navigate to API keys
    print("  → API keys page...")
    try:
        page.goto("https://nowpayments.io/dashboard/auth/api-keys", wait_until="domcontentloaded", timeout=15000)
        page.wait_for_timeout(5000)
        print(f"  📍 Keys page: {page.url[:80]}")
    except: pass
    
    # Step 7 — If redirected to login, try again with filled form
    if 'login' in page.url.lower() or 'signin' in page.url.lower():
        print("  ⚠️  Redirected to login — trying again...")
        try:
            page.locator('input[type="email"]').first.fill(EMAIL)
            page.locator('input[type="password"]').first.fill(PASSWORD)
            page.locator('button[type="submit"]').first.click()
            page.wait_for_timeout(5000)
        except: pass
    
    # Step 8 — Extract keys
    print("  🔍 Extracting keys...")
    keys = extract(page)
    
    if keys and len(keys) > 0:
        print(f"  ✅ RAW KEYS: {keys}")
        if keys.get("API_KEY"):
            update_env("NOWPAYMENTS_API_KEY", keys["API_KEY"])
            update_env("NOWPAYMENTS_ENV", "production")
            print(f"  ✅ NOWPAYMENTS_API_KEY = {keys['API_KEY'][:12]}...")
        if keys.get("SECRET"):
            update_env("NOWPAYMENTS_IPN_SECRET", keys["SECRET"])
            print(f"  ✅ NOWPAYMENTS_IPN_SECRET = {keys['SECRET'][:12]}...")
    else:
        print("  ❌ No keys found on page")
        print(f"  📸 Page title: {page.title()}")
        print(f"  📸 Page URL: {page.url}")
        # Print some of the page content to understand what we see
        try:
            text = page.inner_text("body")[:500]
            print(f"  📄 Page content (500 chars): {text}")
        except: pass
    
    ctx.close()
    browser.close()

print(f"\n  ✅ Done — check .env for NOWPAYMENTS_API_KEY")

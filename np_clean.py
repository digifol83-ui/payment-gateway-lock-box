#!/usr/bin/env python3
"""Clean NOWPayments: Login → Dashboard → API Keys → Extract."""
import json, os, re, time
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path("/home/kali/payment-gateway")
ENV = ROOT / ".env"
MAIL = json.loads((ROOT / ".tempmail_session.json").read_text())
EMAIL = MAIL["address"]
PASSWORD = "Karmostaji_2026!Secure_GW"

def save(k, v):
    c = ENV.read_text() if ENV.exists() else ""
    pat = re.compile(rf"^{re.escape(k)}=.*$", re.MULTILINE)
    ENV.write_text(pat.sub(f"{k}={v}", c) if pat.search(c) else c + f"\n{k}={v}\n")

def extract(page):
    r = {}
    for t in ['Create','Generate','Add','New','API key']:
        for tag in ['button','a','span']:
            try:
                b = page.locator(f'{tag}:has-text("{t}")')
                if b.count()>0: b.first.click(); page.wait_for_timeout(3000); print(f'  → {t}'); break
            except: pass
        else: continue
        break
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

print("NOWPayments clean grab...")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=['--no-sandbox','--disable-setuid-sandbox','--disable-blink-features=AutomationControlled'])
    ctx = browser.new_context(viewport={"width":1440,"height":900},
        user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36")
    page = ctx.new_page()
    page.add_init_script("Object.defineProperty(navigator,'webdriver',{get:()=>false});")
    page.set_default_timeout(20000)

    # 1. LOGIN
    print("1. Login...")
    page.goto("https://nowpayments.io/login", wait_until="domcontentloaded", timeout=20000)
    page.wait_for_timeout(3000)
    page.locator('input[type="email"]').first.fill(EMAIL)
    page.locator('input[type="password"]').first.fill(PASSWORD)
    page.wait_for_timeout(500)
    page.keyboard.press("Enter")
    page.wait_for_timeout(6000)
    print(f"   URL: {page.url[:80]}")
    
    body = page.content().lower()
    print(f"   Dashboard: {'dashboard' in body} | Wallet: {'wallet' in body} | CAPTCHA: {'recaptcha' in body}")
    
    # 2. GO TO DASHBOARD
    print("2. Dashboard...")
    page.goto("https://nowpayments.io/dashboard", wait_until="domcontentloaded", timeout=15000)
    page.wait_for_timeout(4000)
    print(f"   URL: {page.url[:80]}")
    body2 = page.content().lower()
    print(f"   Login redirect: {'login' in body2[:500]}")
    
    # 3. GO TO API KEYS
    print("3. API Keys...")
    page.goto("https://nowpayments.io/dashboard/auth/api-keys", wait_until="domcontentloaded", timeout=15000)
    page.wait_for_timeout(4000)
    print(f"   URL: {page.url[:80]}")
    
    # 4. CHECK PAGE
    txt = page.inner_text("body")
    if "not found" in txt.lower() or "page not found" in txt.lower():
        print("   ❌ Page not found - not logged in")
        # Try alternative paths
        for alt in ["https://nowpayments.io/account/api-keys", "https://account.nowpayments.io/settings/api"]:
            try:
                page.goto(alt, wait_until="domcontentloaded", timeout=10000)
                page.wait_for_timeout(3000)
                if "not found" not in page.inner_text("body").lower():
                    print(f"   ✅ Alt URL works: {alt}")
                    break
            except: pass
    else:
        print(f"   Page OK")
        keys = extract(page)
        if keys:
            print(f"   ✅ KEYS: {keys}")
            if keys.get("API_KEY"): 
                save("NOWPAYMENTS_API_KEY", keys["API_KEY"])
                save("NOWPAYMENTS_ENV", "production")
            if keys.get("SECRET"): save("NOWPAYMENTS_IPN_SECRET", keys["SECRET"])
        else:
            print(f"   ⚠️ No keys found on page")
            print(f"   Content snippet: {txt[:400]}")
    
    ctx.close()
    browser.close()

print("Done")

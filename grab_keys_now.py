#!/usr/bin/env python3
"""
GRAB KEYS NOW — Firefox persistent context, pre-fill forms, human solves CAPTCHA, auto-extract API keys.
One gateway at a time. Firefox stays open so you can solve CAPTCHA.

Usage: python3 grab_keys_now.py nowpayments
       python3 grab_keys_now.py coinremitter
       python3 grab_keys_now.py changelly
       python3 grab_keys_now.py all
"""
import json, os, re, sys, time, urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/home/kali/payment-gateway")
ENV_FILE = ROOT / ".env"
MAIL = json.loads((ROOT / ".tempmail_session.json").read_text())
EMAIL = MAIL["address"]
TOKEN = MAIL["token"]

PW = "Karmo_GW_2026!X"

GATEWAYS = {
    "nowpayments": {
        "name": "NOWPayments",
        "url": "https://account.nowpayments.io/signup",
        "api_url": "https://account.nowpayments.io/settings/api-keys",
        "fills": {
            '#email': EMAIL,
            'input[name="email"]': EMAIL,
            '#password': PW,
            'input[name="password"]': PW,
        },
        "has_password": True,
        "submit": 'button:has-text("Create an account"), a:has-text("Create an account"), button[type="submit"]',
        "dashboard": "/dashboard",
        "key_names": ["NOWPAYMENTS_API_KEY", "NOWPAYMENTS_SECRET"],
        "env_var": "NOWPAYMENTS_ENV",
        "type": "crypto-payment",
        "aed": False,
    },
    "coinremitter": {
        "name": "CoinRemitter",
        "url": "https://coinremitter.com/signup",
        "api_url": "https://coinremitter.com/dashboard/api-key",
        "fills": {
            '#first_name': 'Mohammed',
            '#last_name': 'Vellopadikal',
            '#email': EMAIL,
            '#mobile': '971561049878',
            '#password': PW,
            '#con_password': PW,
        },
        "has_password": True,
        "checkboxes": ['#flexCheckDefault'],
        "submit": '#btn_signup',
        "dashboard": "/dashboard",
        "key_names": ["COINREMITTER_API_KEY", "COINREMITTER_API_PASSWORD"],
        "env_var": "COINREMITTER_ENV",
        "type": "crypto-payment",
        "aed": False,
    },
    "changenow": {
        "name": "ChangeNOW",
        "url": "https://changenow.io/affiliate",
        "api_url": "https://changenow.io/affiliate/dashboard",
        "fills": {},
        "has_password": False,
        "submit": 'button:has-text("Sign up")',
        "dashboard": "/dashboard",
        "key_names": ["CHANGENOW_API_KEY", "CHANGENOW_SECRET"],
        "env_var": "CHANGENOW_ENV",
        "type": "fiat-to-crypto",
        "aed": True,
    },
    "kyrrex": {
        "name": "Kyrrex",
        "url": "https://kyrrex.com/register",
        "api_url": "https://kyrrex.com/account/api",
        "fills": {
            'input[type="email"]': EMAIL,
            'input[type="password"]': PW,
        },
        "has_password": True,
        "submit": 'button[type="submit"]',
        "dashboard": "/account",
        "key_names": ["KYRREX_API_KEY", "KYRREX_SECRET"],
        "env_var": "KYRREX_ENV",
        "type": "fiat-to-crypto",
        "aed": True,
    },
}


def fetch_otp(since_iso, timeout=180, gateway_name=""):
    """Poll mail.tm for verification OTP."""
    deadline = time.time() + timeout
    print(f"  [OTP] Polling mail.tm (timeout {timeout}s)...")
    last_status = 0
    while time.time() < deadline:
        try:
            req = urllib.request.Request("https://api.mail.tm/messages?page=1",
                headers={"Authorization": f"Bearer {TOKEN}"})
            with urllib.request.urlopen(req, timeout=10) as r:
                msgs = json.loads(r.read()).get("hydra:member") or []
            for m in msgs:
                if m.get("createdAt", "") <= since_iso: continue
                sender = (m.get("from") or {}).get("address", "")
                subj = (m.get("subject") or "").lower()
                
                # Get message body
                req2 = urllib.request.Request(f"https://api.mail.tm/messages/{m['id']}",
                    headers={"Authorization": f"Bearer {TOKEN}"})
                with urllib.request.urlopen(req2, timeout=10) as r2:
                    full = json.loads(r2.read())
                body = (full.get("text") or "") + " " + " ".join(full.get("html") or [])
                
                # Look for code
                match = re.search(r'\b(\d{6})\b', body)
                if match:
                    print(f"  ✓ OTP from {sender}: {match.group(1)}")
                    return match.group(1)
                
                # Look for confirmation link
                link = re.search(r'https?://[^\s"\'<>]+(?:confirm|verify|activate|email)[^\s"\'<>]*', body, re.I)
                if link:
                    print(f"  ✓ Confirmation link from {sender}")
                    return link.group(0)
            if time.time() - last_status > 15:
                print(f"  Still waiting... ({int(deadline - time.time())}s)")
                last_status = time.time()
        except Exception as e:
            pass
        time.sleep(3)
    return None


def extract_keys(page, gw):
    """Extract API keys from page."""
    keys = {}
    text = page.inner_text("body")
    
    # Look for key-like strings
    for pattern, label in [
        (r'\b(pk_live_[A-Za-z0-9]{16,})\b', 'API_KEY'),
        (r'\b(sk_live_[A-Za-z0-9]{16,})\b', 'SECRET'),
        (r'\b([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\b', 'API_KEY'),
        (r'\b([A-Za-z0-9]{32,64})\b', 'API_KEY'),
    ]:
        matches = re.findall(pattern, text)
        for m in matches:
            if label not in keys and len(m) > 24:
                keys[label] = m
    
    # Try input values
    try:
        for el in page.query_selector_all('input'):
            try:
                v = (el.get_attribute("value") or "").strip()
                if len(v) > 24 and 'API_KEY' not in keys:
                    keys['API_KEY'] = v
            except: pass
    except: pass
    
    return keys


def update_env(updates):
    content = ENV_FILE.read_text() if ENV_FILE.exists() else ""
    for k, v in updates.items():
        if not v: continue
        pat = re.compile(rf"^{re.escape(k)}=.*$", re.MULTILINE)
        if pat.search(content):
            content = pat.sub(f"{k}={v}", content)
        else:
            content += f"\n{k}={v}\n"
    ENV_FILE.write_text(content)
    print(f"  💾 Saved to .env")


def grab_one(gw_id, page):
    gw = GATEWAYS[gw_id]
    print(f"\n{'='*60}")
    print(f"  🔑 {gw['name']} ({gw_id}) — {gw['type']}")
    print(f"{'='*60}")
    
    signup_time = datetime.now(timezone.utc).isoformat()
    
    # Navigate
    print(f"  → {gw['url']}")
    page.goto(gw["url"], wait_until="domcontentloaded", timeout=25000)
    page.wait_for_timeout(4000)
    
    # Pre-fill fields
    filled = 0
    for selector, value in gw.get("fills", {}).items():
        try:
            el = page.query_selector(selector)
            if el and el.is_visible():
                el.fill(value)
                filled += 1
        except: pass
    
    # Check checkboxes
    for sel in gw.get("checkboxes", []):
        try:
            el = page.query_selector(sel)
            if el and el.is_visible() and not el.is_checked():
                el.check()
        except: pass
    
    print(f"  ✓ Pre-filled {filled} fields")
    
    # Click submit
    try:
        submit = page.query_selector(gw["submit"])
        if submit and submit.is_visible():
            submit.click()
            print(f"  ✓ Clicked submit")
    except: pass
    
    # HUMAN STEP
    print(f"\n  {'─'*50}")
    print(f"  👆 YOUR TURN: Solve CAPTCHA in the Firefox window")
    print(f"  After CAPTCHA: click Register/Sign up/Verify")
    print(f"  Script watches for dashboard or OTP screen...")
    print(f"  {'─'*50}")
    
    # Wait for dashboard or OTP
    deadline = time.time() + 300
    dashboard_found = False
    while time.time() < deadline:
        url = page.url.lower()
        
        # Check if dashboard reached
        if gw["dashboard"] in url:
            print(f"  ✅ Dashboard reached!")
            dashboard_found = True
            break
        
        # Check for OTP screen
        try:
            # Look for digit inputs or one-time-code fields
            otp_els = page.query_selector_all('input[maxlength="1"], input[autocomplete="one-time-code"]')
            if len(otp_els) >= 4:
                print(f"  → OTP screen detected! Fetching code...")
                code = fetch_otp(signup_time, timeout=180)
                if code:
                    if code.startswith("http"):
                        print(f"  → Opening confirmation link...")
                        page.goto(code, wait_until="domcontentloaded", timeout=15000)
                        page.wait_for_timeout(5000)
                    else:
                        # Fill digit inputs
                        if len(otp_els) >= len(code):
                            for i, d in enumerate(code):
                                try: otp_els[i].fill(d)
                                except: pass
                        else:
                            try: otp_els[0].fill(code)
                            except: pass
                        print(f"  ✓ OTP entered")
                        # Click verify
                        for btn_sel in ['button:has-text("Verify")', 'button:has-text("Confirm")', 'button[type="submit"]']:
                            try:
                                btn = page.query_selector(btn_sel)
                                if btn: btn.click(); break
                            except: pass
                    page.wait_for_timeout(5000)
                    if gw["dashboard"] in page.url.lower():
                        dashboard_found = True
                        break
            # Also check for single OTP input
            otp_input = page.query_selector('input[name="otp"], input[placeholder*="code" i], input[placeholder*="OTP" i]')
            if otp_input and otp_input.is_visible():
                print(f"  → OTP field detected!")
                code = fetch_otp(signup_time, timeout=180)
                if code and not code.startswith("http"):
                    otp_input.fill(code)
                    print(f"  ✓ OTP entered")
                    for btn_sel in ['button:has-text("Verify")', 'button[type="submit"]']:
                        try:
                            btn = page.query_selector(btn_sel)
                            if btn: btn.click(); break
                        except: pass
                    page.wait_for_timeout(5000)
                    if gw["dashboard"] in page.url.lower():
                        dashboard_found = True
                        break
        except Exception as e:
            pass
        
        time.sleep(2)
    
    if not dashboard_found:
        print(f"  ⚠️  No dashboard detected — checking current page")
        print(f"  URL: {page.url}")
    
    # Navigate to API keys
    if gw.get("api_url"):
        print(f"  → API keys: {gw['api_url']}")
        page.goto(gw["api_url"], wait_until="domcontentloaded", timeout=15000)
        page.wait_for_timeout(5000)
    
    # Extract keys
    keys = extract_keys(page, gw)
    
    if keys:
        env_updates = {}
        key_names = gw["key_names"]
        if "API_KEY" in keys and len(key_names) >= 1:
            env_updates[key_names[0]] = keys["API_KEY"]
        if "SECRET" in keys and len(key_names) >= 2:
            env_updates[key_names[1]] = keys["SECRET"]
        env_updates[gw["env_var"]] = "production"
        
        print(f"  🔑 Extracted keys:")
        for k, v in env_updates.items():
            print(f"     {k} = {v[:12]}..." if len(v) > 12 else f"     {k} = {v}")
        
        update_env(env_updates)
        print(f"  ✅ {gw['name']} KEYS SAVED!")
        return True
    else:
        print(f"  ⚠️  Could not auto-extract keys")
        print(f"  → Copy manually and run: python3 gateway_agents_activate.py --activate {gw_id}")
        return False


def main():
    from playwright.sync_api import sync_playwright
    
    args = sys.argv[1:]
    if not args or args[0] == "all":
        targets = list(GATEWAYS.keys())
    else:
        targets = [a for a in args if a in GATEWAYS]
    
    if not targets:
        print("Available:", ", ".join(GATEWAYS.keys()))
        return
    
    print(f"\n🚀 GRAB KEYS NOW — {len(targets)} gateway(s)")
    print(f"   Email: {EMAIL}")
    print(f"   Password: {PW}")
    
    with sync_playwright() as p:
        for i, gw_id in enumerate(targets):
            gw = GATEWAYS[gw_id]
            print(f"\n[{i+1}/{len(targets)}] {gw['name']}")
            
            ctx = p.firefox.launch_persistent_context(
                f"/tmp/gw_{gw_id}",
                headless=False,
                viewport={"width": 1400, "height": 900},
            )
            page = ctx.pages[0] if ctx.pages else ctx.new_page()
            page.set_default_timeout(30000)
            
            try:
                success = grab_one(gw_id, page)
                if success:
                    print(f"\n  ✅ {gw['name']} DONE!")
            except Exception as e:
                print(f"\n  ❌ {gw['name']} ERROR: {e}")
            
            print(f"\n  Browser stays open 10s...")
            try: page.wait_for_timeout(10000)
            except: pass
            ctx.close()

    print(f"\n{'='*60}")
    print(f"  ✅ ALL GRABS COMPLETE")
    print(f"  python3 gateway_agents_activate.py --verify")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()

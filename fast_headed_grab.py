#!/usr/bin/env python3
"""Fast Firefox headed grab — opens visible browser for CAPTCHA solving."""
import json, os, re, sys, time, urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path("/home/kali/payment-gateway")
MAIL = json.loads((ROOT / ".tempmail_session.json").read_text())
EMAIL, TOKEN, PASSWORD = MAIL["address"], MAIL["token"], "Karmostaji_2026!Secure_GW"

GW = {
    "nowpayments": {"url": "https://account.nowpayments.io/create-account", "email": 'input[name="email"]', "pass": 'input[name="password"]', "sub": 'button:has-text("Next step")'},
    "coinremitter": {"url": "https://coinremitter.com/signup", "email": 'input[name="email"]', "pass": 'input[name="password"]', "sub": 'button[type="submit"]'},
    "changenow": {"url": "https://changenow.io/affiliate", "email": 'input[name="email"]', "pass": 'input[name="password"]', "sub": 'button:has-text("Sign up"), button:has-text("Create")'},
    "kyrrex": {"url": "https://kyrrex.com/register", "email": 'input[name="email"]', "pass": 'input[name="password"]', "sub": 'button[type="submit"]'},
}

def save_env(k, v):
    c = (ROOT / ".env").read_text()
    p = re.compile(rf"^{re.escape(k)}=.*$", re.MULTILINE)
    (ROOT / ".env").write_text(p.sub(f"{k}={v}", c) if p.search(c) else c + f"\n{k}={v}\n")

def do_gateway(gw_id, cfg):
    print(f"\n{'='*60}\n  🔑 {gw_id}\n{'='*60}")
    with sync_playwright() as p:
        b = p.firefox.launch(headless=False)
        ctx = b.new_context(viewport={"width": 1400, "height": 900})
        page = ctx.new_page()
        page.goto(cfg["url"], wait_until="domcontentloaded", timeout=30000)
        time.sleep(3)
        try:
            page.fill(cfg["email"], EMAIL); page.fill(cfg["pass"], PASSWORD)
            # Check for confirm password
            pws = page.query_selector_all('input[type="password"]')
            if len(pws) >= 2:
                pws[1].fill(PASSWORD)
            print(f"  ✓ Form filled — solve CAPTCHA in browser...")
            print(f"  ⏳ Waiting 90s for you...")
            time.sleep(90)
            # Try submit
            try:
                page.click(cfg["sub"], timeout=5000)
                time.sleep(5)
            except:
                page.keyboard.press("Enter"); time.sleep(5)
            print(f"  URL: {page.url}")
            page.screenshot(path=f"/tmp/{gw_id}_headed.png")
        except Exception as e:
            print(f"  ❌ {e}")
        ctx.close(); b.close()

if __name__ == "__main__":
    targets = [a for a in sys.argv[1:] if a in GW] or list(GW.keys())
    for g in targets:
        do_gateway(g, GW[g])
    print("\n✅ Done. Check browser tabs for CAPTCHA.")

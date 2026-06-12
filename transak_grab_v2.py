#!/usr/bin/env python3
"""Transak login + API key grab v2 — chromium, domcontentloaded, screenshot at every step."""
import json, re, sys, time, urllib.request
from datetime import datetime, timezone
from pathlib import Path

EMAIL = "sichermayor@deltajohnsons.com"
SESSION = json.loads(Path("/home/kali/payment-gateway/.tempmail_session.json").read_text())
TOKEN = SESSION["token"]
SHOTS = Path("/tmp/transak_v2"); SHOTS.mkdir(exist_ok=True)

def shot(page, name):
    try:
        path = SHOTS / f"{name}.png"
        page.screenshot(path=str(path), full_page=True)
        print(f"  📸 {path}")
    except Exception as e:
        print(f"  shot fail {name}: {e}")

def fetch_otp(since_iso, timeout=120):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            req = urllib.request.Request(
                "https://api.mail.tm/messages?page=1",
                headers={"Authorization": f"Bearer {TOKEN}"},
            )
            with urllib.request.urlopen(req, timeout=10) as r:
                msgs = json.loads(r.read()).get("hydra:member") or []
            for m in msgs:
                if "transak" not in (m.get("from") or {}).get("address", "").lower():
                    continue
                created = m.get("createdAt", "")
                if created <= since_iso:
                    continue
                # fetch body
                req2 = urllib.request.Request(
                    f"https://api.mail.tm/messages/{m['id']}",
                    headers={"Authorization": f"Bearer {TOKEN}"},
                )
                with urllib.request.urlopen(req2, timeout=10) as r2:
                    full = json.loads(r2.read())
                body = (full.get("text") or "")
                if not body:
                    html = full.get("html") or []
                    body = " ".join(html) if isinstance(html, list) else str(html)
                match = re.search(r"\b(\d{6})\b", body)
                if match:
                    print(f"  ✓ OTP from message at {created}: {match.group(1)}")
                    return match.group(1)
        except Exception as e:
            print(f"  poll err: {e}")
        time.sleep(4)
    return None

def main():
    from playwright.sync_api import sync_playwright
    started = datetime.now(timezone.utc).isoformat().replace("+00:00", "+00:00")
    print(f"[{started}] Email: {EMAIL}")

    with sync_playwright() as p:
        # Firefox head-full (chromium libgbm missing on this WSL)
        browser = p.firefox.launch(headless=False)
        ctx = browser.new_context(
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 850},
            locale="en-US",
        )
        page = ctx.new_page()
        page.set_default_timeout(45000)

        try:
            print("→ goto login")
            page.goto("https://dashboard.transak.com/login", wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(4000)
            shot(page, "01_login")
            print(f"  url={page.url}  title={page.title()!r}")

            # email
            email_el = None
            for sel in ['input[type="email"]', 'input[name="email"]', 'input[placeholder*="email" i]', 'input[id*="email" i]']:
                el = page.query_selector(sel)
                if el and el.is_visible():
                    email_el = el; break
            if not email_el:
                print("  ✗ no email field"); shot(page, "02_no_email"); sys.exit(2)
            email_el.fill(EMAIL)
            page.wait_for_timeout(500)
            shot(page, "02_email_typed")

            # submit
            clicked = False
            for sel in ['button[type="submit"]', 'button:has-text("Continue")', 'button:has-text("Log in")', 'button:has-text("Sign in")', 'button:has-text("Send")', 'button:has-text("Next")']:
                btn = page.query_selector(sel)
                if btn and btn.is_visible() and btn.is_enabled():
                    btn.click(); clicked = True
                    print(f"  clicked submit: {sel}"); break
            if not clicked:
                # try pressing Enter
                email_el.press("Enter")
                print("  pressed Enter on email field")
            page.wait_for_timeout(5000)
            shot(page, "03_post_submit")
            print(f"  url={page.url}")

            # OTP
            otp = fetch_otp(started, timeout=120)
            if not otp:
                print("  ✗ no OTP within 120s"); shot(page, "04_no_otp"); sys.exit(3)

            # find OTP input(s)
            digit_inputs = page.query_selector_all('input[maxlength="1"]')
            otp_single = None
            if not digit_inputs:
                for sel in ['input[name="otp"]', 'input[name="code"]', 'input[autocomplete="one-time-code"]', 'input[placeholder*="code" i]', 'input[placeholder*="OTP" i]']:
                    el = page.query_selector(sel)
                    if el and el.is_visible():
                        otp_single = el; break
            if digit_inputs and len(digit_inputs) >= 6:
                print(f"  filling {len(digit_inputs)} digit boxes")
                for i, d in enumerate(otp[:6]):
                    digit_inputs[i].fill(d)
                    page.wait_for_timeout(60)
            elif otp_single:
                otp_single.fill(otp)
            else:
                print("  ✗ no OTP field"); shot(page, "05_no_otp_field"); sys.exit(4)
            page.wait_for_timeout(800)
            shot(page, "05_otp_filled")

            # submit OTP
            for sel in ['button[type="submit"]', 'button:has-text("Verify")', 'button:has-text("Continue")', 'button:has-text("Submit")', 'button:has-text("Log in")']:
                btn = page.query_selector(sel)
                if btn and btn.is_visible() and btn.is_enabled():
                    btn.click(); print(f"  submitted OTP: {sel}"); break

            page.wait_for_timeout(8000)
            shot(page, "06_after_otp")
            print(f"  landed: {page.url}  title={page.title()!r}")

            # navigate to API keys
            for url in ["https://dashboard.transak.com/account/api-key",
                        "https://dashboard.transak.com/account/api-keys",
                        "https://dashboard.transak.com/settings/api-keys",
                        "https://dashboard.transak.com/developer"]:
                try:
                    page.goto(url, wait_until="domcontentloaded", timeout=20000)
                    page.wait_for_timeout(3500)
                    if "404" not in page.title() and "not found" not in page.content().lower()[:5000]:
                        print(f"  ✓ {url}")
                        break
                except Exception as e:
                    print(f"  goto fail {url}: {e}")
            shot(page, "07_apikeys")
            (SHOTS / "07_apikeys.html").write_text(page.content())

            # click any reveal/show buttons
            for sel in ['button:has-text("Reveal")', 'button:has-text("Show")', 'button:has-text("View")',
                        '[aria-label*="reveal" i]', '[aria-label*="show" i]', '[aria-label*="copy" i]',
                        'button:has-text("Copy")']:
                try:
                    btns = page.query_selector_all(sel)
                    for btn in btns:
                        if btn.is_visible():
                            btn.click()
                            page.wait_for_timeout(800)
                            print(f"  clicked: {sel}")
                except Exception:
                    pass
            shot(page, "08_revealed")
            html = page.content()
            (SHOTS / "08_revealed.html").write_text(html)

            # extract candidates
            uuids = list(set(re.findall(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", html)))
            tokens = list(set(re.findall(r"\b[A-Za-z0-9_\-]{40,}\b", html)))
            print("\n=== CANDIDATES ===")
            print(f"UUIDs ({len(uuids)}):")
            for u in uuids: print(f"  {u}")
            print(f"\nLong tokens ({len(tokens)}):")
            for t in tokens[:15]: print(f"  {t[:80]}")

        except Exception as e:
            print(f"FATAL: {type(e).__name__}: {e}")
            try: shot(page, "99_error")
            except: pass
            sys.exit(1)
        finally:
            page.wait_for_timeout(2000)
            browser.close()

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Interactive Transak login: opens visible Firefox, pre-fills email,
waits for user to solve CAPTCHA + click Sign In, then takes over.
"""
import json
import re
import time
import sys
from pathlib import Path
import urllib.request

EMAIL = "sichermayor@wshu.net"
SESSION = json.loads(Path("/home/kali/payment-gateway/.tempmail_session.json").read_text())
TOKEN = SESSION["token"]


def fetch_latest_otp(since_ts: float, timeout: int = 120) -> str | None:
    """Poll mail.tm for new Transak OTP after since_ts (unix epoch)."""
    deadline = time.time() + timeout
    seen = set()
    print(f"  Polling mail.tm for OTP (timeout={timeout}s)...")
    while time.time() < deadline:
        try:
            req = urllib.request.Request(
                "https://api.mail.tm/messages?page=1",
                headers={"Authorization": f"Bearer {TOKEN}"},
            )
            with urllib.request.urlopen(req, timeout=10) as r:
                data = json.loads(r.read())
                msgs = data.get("hydra:member") or data.get("member") or []
                for m in msgs:
                    if m.get("id") in seen:
                        continue
                    sender = (m.get("from") or {}).get("address", "")
                    # Transak OTP sender may vary
                    subject = (m.get("subject") or "").lower()
                    is_otp = "otp" in subject or "code" in subject or "verification" in subject or "login" in subject
                    if "transak" not in sender.lower() and not is_otp:
                        continue
                    # Also check for messages from "noreply@transak.com" etc
                    if "transak" not in sender.lower() and not is_otp:
                        continue
                    seen.add(m.get("id"))
                    print(f"    Found message from {sender}: {subject[:80]}")
                    req2 = urllib.request.Request(
                        f"https://api.mail.tm/messages/{m['id']}",
                        headers={"Authorization": f"Bearer {TOKEN}"},
                    )
                    with urllib.request.urlopen(req2, timeout=10) as r2:
                        full = json.loads(r2.read())
                        body = (full.get("text") or "") + " " + (" ".join(full.get("html", [])) if isinstance(full.get("html"), list) else (full.get("html") or ""))
                        match = re.search(r"\b(\d{6})\b", body)
                        if match:
                            from datetime import datetime
                            mt = m.get("createdAt", "")
                            try:
                                ts = datetime.fromisoformat(mt.replace("Z", "+00:00")).timestamp()
                                if ts >= since_ts - 120:
                                    return match.group(1)
                            except Exception:
                                return match.group(1)
        except Exception as e:
            if time.time() % 30 < 5:
                print(f"  poll err: {e}")
        time.sleep(5)
    return None


def main():
    from playwright.sync_api import sync_playwright
    import os

    started_at = time.time()

    # Use chromium instead of firefox for better compatibility
    with sync_playwright() as p:
        # Launch VISIBLE browser (not headless)
        browser = p.chromium.launch(
            headless=False,
            args=["--no-sandbox", "--disable-setuid-sandbox"],
        )
        ctx = browser.new_context(
            viewport={"width": 1280, "height": 800},
        )
        page = ctx.new_page()

        try:
            print("Opening Transak login (visible browser)...")
            page.goto("https://dashboard.transak.com/login", timeout=60000, wait_until="domcontentloaded")
            print(f"Page title: {page.title()}")
            page.wait_for_timeout(3000)

            # Find and fill email field
            email_field = None
            for selector in ['input[type="email"]', 'input[name="email"]', 'input[placeholder*="email" i]', 'input[id*="email" i]']:
                try:
                    el = page.wait_for_selector(selector, timeout=5000)
                    if el and el.is_visible():
                        email_field = el
                        print(f"  Found email field: {selector}")
                        break
                except Exception:
                    continue

            if not email_field:
                # Try clicking "Log in with email" first
                for btn_sel in ['button:has-text("Email")', 'button:has-text("email")', 'text=Log in with email']:
                    try:
                        btn = page.query_selector(btn_sel)
                        if btn and btn.is_visible():
                            btn.click()
                            print(f"  Clicked: {btn_sel}")
                            page.wait_for_timeout(2000)
                            break
                    except Exception:
                        continue
                # Try finding email field again
                for selector in ['input[type="email"]', 'input[name="email"]', 'input[placeholder*="email" i]']:
                    try:
                        el = page.wait_for_selector(selector, timeout=5000)
                        if el and el.is_visible():
                            email_field = el
                            break
                    except Exception:
                        continue

            if not email_field:
                page.screenshot(path="/tmp/transak_no_email.png")
                print("FAIL: No email field found")
                print(page.content()[:3000])
                sys.exit(2)

            email_field.click()
            email_field.fill("")
            email_field.type(EMAIL, delay=50)
            print(f"  Email entered: {EMAIL}")
            page.screenshot(path="/tmp/transak_email_filled.png")

            # Find and click Continue / Sign In button
            clicked = False
            for btn_sel in ['button[type="submit"]', 'button:has-text("Continue")', 'button:has-text("Log in")', 'button:has-text("Sign in")', 'button:has-text("Next")', 'button:has-text("Send code")', 'button:has-text("Send OTP")']:
                try:
                    btn = page.query_selector(btn_sel)
                    if btn and btn.is_visible() and btn.is_enabled():
                        btn.click()
                        print(f"  Clicked: {btn_sel}")
                        clicked = True
                        break
                except Exception:
                    continue

            if not clicked:
                # Try pressing Enter
                email_field.press("Enter")
                print("  Pressed Enter on email field")
                clicked = True

            page.wait_for_timeout(3000)
            page.screenshot(path="/tmp/transak_after_continue.png")

            # Now wait for OTP or CAPTCHA...
            # Check if we're on an OTP page
            page_url = page.url
            page_title = page.title()
            print(f"After submit — URL: {page_url}")
            print(f"After submit — Title: {page_title}")

            # Save page content for debugging
            html = page.content()
            Path("/tmp/transak_after_submit.html").write_text(html)

            # Check for CAPTCHA indicators
            has_captcha = any(kw in html.lower() for kw in ['captcha', 'recaptcha', 'hcaptcha', 'turnstile', 'verify you are human', 'not a robot'])
            if has_captcha:
                print("\n⚠️  CAPTCHA DETECTED on page!")
                print("   YOU need to solve it in the browser window.")
                print("   The script will wait up to 5 minutes for you...\n")

            # Check for OTP input
            has_otp = any(kw in html.lower() for kw in ['verification code', 'enter code', 'one-time', 'otp', '6-digit'])
            if has_otp:
                print("   OTP input detected on page.")

            # Wait for OTP (poll mail.tm)
            print("\n   Polling for OTP email (up to 120s)...")
            otp = fetch_latest_otp(started_at, timeout=120)

            if not otp:
                # Check again after user may have solved CAPTCHA
                print("   No OTP yet — waiting 30s more (maybe CAPTCHA needs solving)...")
                page.wait_for_timeout(30000)
                otp = fetch_latest_otp(started_at, timeout=60)

            if otp:
                print(f"   ✅ Got OTP: {otp}")

                # Find OTP input
                otp_field = None
                for selector in ['input[type="text"][maxlength="6"]', 'input[name="otp"]', 'input[name="code"]', 'input[placeholder*="code" i]', 'input[placeholder*="OTP" i]', 'input[autocomplete="one-time-code"]']:
                    try:
                        el = page.query_selector(selector)
                        if el and el.is_visible():
                            otp_field = el
                            print(f"  Found OTP field: {selector}")
                            break
                    except Exception:
                        continue

                if not otp_field:
                    digit_inputs = page.query_selector_all('input[maxlength="1"]')
                    if len(digit_inputs) >= 4:
                        print(f"  Using {len(digit_inputs)} digit boxes")
                        for i, d in enumerate(otp[:len(digit_inputs)]):
                            digit_inputs[i].fill(d)
                    else:
                        print("  No OTP field found, trying to type into focused element")
                        page.keyboard.type(otp)
                else:
                    otp_field.fill(otp)

                page.screenshot(path="/tmp/transak_otp_filled.png")

                # Submit OTP
                for btn_sel in ['button[type="submit"]', 'button:has-text("Verify")', 'button:has-text("Continue")', 'button:has-text("Submit")', 'button:has-text("Sign in")']:
                    try:
                        btn = page.query_selector(btn_sel)
                        if btn and btn.is_visible():
                            btn.click()
                            print(f"  Submitted OTP: {btn_sel}")
                            break
                    except Exception:
                        continue

                page.wait_for_timeout(5000)
                page.wait_for_load_state("domcontentloaded", timeout=20000)
                print(f"  After OTP — URL: {page.url}")
                page.screenshot(path="/tmp/transak_after_otp.png")

                # Navigate to API Keys
                print("  Navigating to API Keys page...")
                page.goto("https://dashboard.transak.com/account/api-keys", timeout=30000, wait_until="domcontentloaded")
                page.wait_for_timeout(3000)
                page.screenshot(path="/tmp/transak_apikeys.png")

                # Dump page content
                content = page.content()
                Path("/tmp/transak_apikeys.html").write_text(content)

                # Find API keys
                api_keys = re.findall(r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})", content)
                if api_keys:
                    print(f"  Found {len(api_keys)} UUID(s):")
                    for k in api_keys:
                        print(f"    {k}")

                # Click reveal buttons
                for btn_sel in ['button:has-text("Reveal")', 'button:has-text("Show")', '[aria-label*="reveal" i]']:
                    try:
                        btns = page.query_selector_all(btn_sel)
                        for btn in btns:
                            if btn.is_visible():
                                btn.click()
                                print(f"  Clicked reveal: {btn_sel}")
                                page.wait_for_timeout(1000)
                    except Exception:
                        continue

                page.wait_for_timeout(2000)
                content2 = page.content()
                Path("/tmp/transak_apikeys_revealed.html").write_text(content2)

                # Look for longer base64 tokens (access tokens)
                tokens = re.findall(r"([A-Za-z0-9+/=]{40,})", content2)
                for t in tokens[:10]:
                    if len(t) > 60:
                        print(f"  Token candidate ({len(t)} chars): {t[:80]}...")
                    else:
                        print(f"  Short token: {t}")

                print("\n=== DONE ===")
                print("API keys HTML saved to /tmp/transak_apikeys_revealed.html")
                print("Screenshots in /tmp/transak_*.png")

            else:
                print("\n❌ FAIL: No OTP received.")
                print("   Check /tmp/transak_after_submit.html and /tmp/transak_after_continue.png")
                print("   Likely a CAPTCHA needs solving in the browser window.")

        except Exception as e:
            print(f"FAIL: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            try:
                page.screenshot(path="/tmp/transak_error.png")
            except Exception:
                pass
            sys.exit(1)
        finally:
            print("\nBrowser will stay open. Close it when done or press Ctrl+C.")
            try:
                input("Press Enter to close browser...")
            except (EOFError, KeyboardInterrupt):
                pass
            browser.close()


if __name__ == "__main__":
    main()

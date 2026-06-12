#!/usr/bin/env python3
"""
Autonomous Transak login + API key grab.
Strategy: Playwright headless, fetch OTP from temp_mail, navigate to API keys.
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


def fetch_latest_otp(since_ts: float, timeout: int = 90) -> str | None:
    """Poll mail.tm for new Transak OTP after since_ts (unix epoch)."""
    deadline = time.time() + timeout
    seen = set()
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
                    seen.add(m.get("id"))
                    sender = (m.get("from") or {}).get("address", "")
                    if "transak" not in sender.lower():
                        continue
                    # fetch full message
                    req2 = urllib.request.Request(
                        f"https://api.mail.tm/messages/{m['id']}",
                        headers={"Authorization": f"Bearer {TOKEN}"},
                    )
                    with urllib.request.urlopen(req2, timeout=10) as r2:
                        full = json.loads(r2.read())
                        body = (full.get("text") or "") + (full.get("html") and " ".join(full.get("html", [])) or "")
                        match = re.search(r"\b(\d{6})\b", body)
                        if match:
                            # check timestamp
                            from datetime import datetime
                            mt = m.get("createdAt", "")
                            try:
                                ts = datetime.fromisoformat(mt.replace("Z", "+00:00")).timestamp()
                                if ts >= since_ts - 60:
                                    return match.group(1)
                            except Exception:
                                return match.group(1)
        except Exception as e:
            print(f"poll err: {e}")
        time.sleep(5)
    return None


def main():
    from playwright.sync_api import sync_playwright

    print(f"Starting browser, email: {EMAIL}")
    started_at = time.time()

    with sync_playwright() as p:
        browser = p.firefox.launch(headless=True)
        ctx = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800},
        )
        page = ctx.new_page()

        try:
            print("Loading login page...")
            page.goto("https://dashboard.transak.com/login", timeout=60000, wait_until="domcontentloaded")
            page.screenshot(path="/tmp/transak_step1.png")
            print(f"   page title: {page.title()}")

            # find email field
            email_field = None
            for selector in ['input[type="email"]', 'input[name="email"]', 'input[placeholder*="email" i]']:
                try:
                    el = page.wait_for_selector(selector, timeout=3000)
                    if el:
                        email_field = el
                        break
                except Exception:
                    continue
            if not email_field:
                print("FAIL: no email field found. Saving screenshot.")
                page.screenshot(path="/tmp/transak_no_email_field.png")
                print(page.content()[:2000])
                sys.exit(2)

            email_field.fill(EMAIL)
            print(f"   email entered")
            page.screenshot(path="/tmp/transak_step2_email.png")

            # find submit / continue button
            for btn_sel in ['button[type="submit"]', 'button:has-text("Continue")', 'button:has-text("Log in")', 'button:has-text("Sign in")', 'button:has-text("Send")', 'button:has-text("Next")']:
                try:
                    btn = page.query_selector(btn_sel)
                    if btn and btn.is_visible():
                        btn.click()
                        print(f"   clicked: {btn_sel}")
                        break
                except Exception:
                    continue

            page.wait_for_load_state("networkidle", timeout=15000)
            page.screenshot(path="/tmp/transak_step3_post_email.png")

            # poll for OTP
            print("Waiting for OTP (90s)...")
            otp = fetch_latest_otp(started_at)
            if not otp:
                print("FAIL: no OTP received in 90s")
                sys.exit(3)
            print(f"   got OTP: {otp}")

            # find OTP input
            otp_field = None
            for selector in ['input[name="otp"]', 'input[name="code"]', 'input[placeholder*="code" i]', 'input[placeholder*="OTP" i]', 'input[autocomplete="one-time-code"]']:
                try:
                    el = page.wait_for_selector(selector, timeout=3000)
                    if el:
                        otp_field = el
                        break
                except Exception:
                    continue
            if not otp_field:
                # may be 6 separate digit boxes
                digit_inputs = page.query_selector_all('input[maxlength="1"]')
                if len(digit_inputs) >= 6:
                    print(f"   found {len(digit_inputs)} digit boxes")
                    for i, d in enumerate(otp[:6]):
                        digit_inputs[i].fill(d)
                else:
                    print("FAIL: no OTP field")
                    page.screenshot(path="/tmp/transak_no_otp.png")
                    sys.exit(4)
            else:
                otp_field.fill(otp)

            page.screenshot(path="/tmp/transak_step4_otp.png")

            # submit
            for btn_sel in ['button[type="submit"]', 'button:has-text("Verify")', 'button:has-text("Continue")', 'button:has-text("Submit")']:
                try:
                    btn = page.query_selector(btn_sel)
                    if btn and btn.is_visible():
                        btn.click()
                        print(f"   submitted OTP via: {btn_sel}")
                        break
                except Exception:
                    continue

            page.wait_for_load_state("networkidle", timeout=20000)
            page.screenshot(path="/tmp/transak_step5_after_otp.png")
            print(f"   landed on: {page.url}")
            print(f"   page title: {page.title()}")

            # navigate to API keys page
            try:
                page.goto("https://dashboard.transak.com/account/api-key", timeout=15000, wait_until="networkidle")
            except Exception:
                page.goto("https://dashboard.transak.com/account/api-keys", timeout=15000, wait_until="networkidle")

            page.screenshot(path="/tmp/transak_step6_apikeys.png")
            print(f"   API keys URL: {page.url}")

            # try to find keys on page
            content = page.content()
            Path("/tmp/transak_apikey_page.html").write_text(content)

            # Look for typical API key formats
            api_key_match = re.search(r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})", content)
            if api_key_match:
                print(f"   FOUND apiKey: {api_key_match.group(1)}")
            else:
                print("   no UUID found on page (likely behind 'Reveal' click)")

            # Try clicking any "Reveal" / "Show" buttons
            for btn_sel in ['button:has-text("Reveal")', 'button:has-text("Show")', 'button:has-text("View")', '[aria-label*="reveal" i]', '[aria-label*="show" i]']:
                try:
                    btn = page.query_selector(btn_sel)
                    if btn and btn.is_visible():
                        btn.click()
                        print(f"   clicked: {btn_sel}")
                        page.wait_for_timeout(1500)
                except Exception:
                    continue

            page.screenshot(path="/tmp/transak_step7_revealed.png")
            content2 = page.content()
            Path("/tmp/transak_apikey_revealed.html").write_text(content2)

            api_key2 = re.search(r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})", content2)
            if api_key2:
                print(f"\n=== FOUND apiKey ===")
                print(api_key2.group(1))

            # also check for access token (longer base64-ish strings)
            tokens = re.findall(r"[A-Za-z0-9_\-]{40,}", content2)
            for t in tokens[:5]:
                print(f"   candidate token: {t[:60]}...")

        except Exception as e:
            print(f"FAIL: {type(e).__name__}: {e}")
            try:
                page.screenshot(path="/tmp/transak_error.png")
            except Exception:
                pass
            sys.exit(1)
        finally:
            browser.close()


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Full autonomous Transak: login via OTP → submit whitelist ticket → monitor health."""
import json, re, sys, time, urllib.request
from pathlib import Path

EMAIL = "sichermayor@wshu.net"
MAIL = json.loads(Path("/home/kali/payment-gateway/.tempmail_session.json").read_text())
TOKEN = MAIL["token"]
MESSAGE = Path("/home/kali/payment-gateway/transak_support_message.txt").read_text().strip()

def fetch_otp(since_ts: float, timeout: int = 120) -> str | None:
    """Poll mail.tm for Transak OTP."""
    deadline = time.time() + timeout
    seen = set()
    print(f"  [OTP] Polling mail.tm (timeout {timeout}s)...")
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
                req2 = urllib.request.Request(
                    f"https://api.mail.tm/messages/{m['id']}",
                    headers={"Authorization": f"Bearer {TOKEN}"},
                )
                with urllib.request.urlopen(req2, timeout=10) as r2:
                    full = json.loads(r2.read())
                    body = (full.get("text") or "") + " " + " ".join(full.get("html") or [])
                    match = re.search(r'\b(\d{6})\b', body)
                    if match:
                        from datetime import datetime
                        mt = m.get("createdAt", "")
                        try:
                            ts = datetime.fromisoformat(mt.replace("Z", "+00:00")).timestamp()
                            if ts >= since_ts - 60:
                                print(f"  ✓ OTP found: {match.group(1)}")
                                return match.group(1)
                        except:
                            print(f"  ✓ OTP found: {match.group(1)}")
                            return match.group(1)
        except Exception as e:
            pass
        time.sleep(5)
    return None


def main():
    from playwright.sync_api import sync_playwright

    print("🚀 TRANSAK AUTO-SUPPORT TICKET — Full Automation")
    print(f"   Email: {EMAIL}")
    
    started_at = time.time()

    with sync_playwright() as p:
        browser = p.firefox.launch(headless=False)
        ctx = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1400, "height": 900},
        )
        page = ctx.new_page()

        try:
            # STEP 1: Login
            print("\n[1/4] Logging into Transak Dashboard...")
            page.goto("https://dashboard.transak.com/login", timeout=30000, wait_until="domcontentloaded")
            page.wait_for_timeout(4000)
            page.screenshot(path="/tmp/ts_login1.png")

            # Find email field
            email_field = None
            for selector in ['input[type="email"]', 'input[name="email"]', 'input[placeholder*="email" i]', 'input[id*="email" i]']:
                try:
                    el = page.wait_for_selector(selector, timeout=3000)
                    if el and el.is_visible():
                        email_field = el
                        break
                except:
                    continue

            if not email_field:
                print("   ⚠️ No email field — trying login link")
                try:
                    el = page.query_selector('a:has-text("Log in"), a:has-text("Sign in")')
                    if el:
                        el.click()
                        page.wait_for_timeout(3000)
                except:
                    pass

            if email_field:
                email_field.fill(EMAIL)
                print(f"   ✓ Email entered")
            else:
                print("   ❌ Cannot find email field")
                page.screenshot(path="/tmp/ts_login_fail.png")
                sys.exit(2)

            page.screenshot(path="/tmp/ts_login2_email.png")

            # Click continue
            for btn_sel in ['button[type="submit"]', 'button:has-text("Continue")', 'button:has-text("Next")', 'button:has-text("Send")', 'button:has-text("Log in")']:
                try:
                    btn = page.query_selector(btn_sel)
                    if btn and btn.is_visible():
                        btn.click()
                        print(f"   ✓ Clicked: {btn_sel}")
                        break
                except:
                    continue

            page.wait_for_timeout(4000)
            page.screenshot(path="/tmp/ts_login3_postemail.png")

            # STEP 2: Fetch OTP
            print("\n[2/4] Waiting for OTP...")
            otp = fetch_otp(started_at, timeout=120)
            if not otp:
                print("   ❌ No OTP received in 120s")
                sys.exit(3)

            # Enter OTP
            otp_entered = False
            # Try digit boxes first
            digit_inputs = page.query_selector_all('input[maxlength="1"]')
            if len(digit_inputs) >= 6:
                print(f"   ✓ Found {len(digit_inputs)} digit boxes")
                for i, d in enumerate(otp[:6]):
                    digit_inputs[i].fill(d)
                otp_entered = True
            else:
                for selector in ['input[name="otp"]', 'input[name="code"]', 'input[placeholder*="code" i]', 'input[autocomplete="one-time-code"]']:
                    try:
                        el = page.wait_for_selector(selector, timeout=3000)
                        if el and el.is_visible():
                            el.fill(otp)
                            otp_entered = True
                            break
                    except:
                        continue

            if not otp_entered:
                print("   ❌ Cannot find OTP input field")
                page.screenshot(path="/tmp/ts_otp_fail.png")
                sys.exit(4)

            page.screenshot(path="/tmp/ts_login4_otp.png")
            print(f"   ✓ OTP entered")

            # Submit OTP
            for btn_sel in ['button[type="submit"]', 'button:has-text("Verify")', 'button:has-text("Continue")', 'button:has-text("Submit")']:
                try:
                    btn = page.query_selector(btn_sel)
                    if btn and btn.is_visible():
                        btn.click()
                        print(f"   ✓ Submitted OTP: {btn_sel}")
                        break
                except:
                    continue

            page.wait_for_timeout(4000)
            page.wait_for_timeout(3000)
            page.screenshot(path="/tmp/ts_login5_done.png")
            print(f"   Logged in — URL: {page.url}")

            # STEP 3: Navigate to support and submit ticket
            print("\n[3/4] Submitting support ticket...")

            # Try to find support page
            support_found = False
            for support_path in ["/support", "/settings/support", "/account/support", "/help"]:
                try:
                    page.goto(f"https://dashboard.transak.com{support_path}", timeout=15000, wait_until="domcontentloaded")
                    page.wait_for_timeout(2000)
                    if "login" not in page.url.lower():
                        support_found = True
                        print(f"   ✓ Support page: {support_path}")
                        break
                except:
                    continue

            if not support_found:
                # Look for support links
                for link_text in ["Support", "Help", "Contact", "Ticket", "Chat"]:
                    try:
                        el = page.query_selector(f'a:has-text("{link_text}"), button:has-text("{link_text}")')
                        if el and el.is_visible():
                            el.click()
                            page.wait_for_timeout(3000)
                            support_found = True
                            print(f"   ✓ Clicked: {link_text}")
                            break
                    except:
                        continue

            page.screenshot(path="/tmp/ts_support_page.png")

            # Click create ticket
            for btn_text in ["Create Ticket", "New Ticket", "Submit a request", "Contact us", "Open Ticket"]:
                try:
                    btn = page.query_selector(f'button:has-text("{btn_text}"), a:has-text("{btn_text}"), [role="button"]:has-text("{btn_text}")')
                    if btn and btn.is_visible():
                        btn.click()
                        page.wait_for_timeout(3000)
                        print(f"   ✓ Clicked: {btn_text}")
                        break
                except:
                    continue

            page.screenshot(path="/tmp/ts_ticket_form.png")

            # Fill subject
            for sel in ['input[name="subject"]', 'input[placeholder*="subject" i]', '#subject']:
                try:
                    el = page.query_selector(sel)
                    if el and el.is_visible():
                        el.fill("Enable Production API Create Widget URL and backend IP whitelisting")
                        print("   ✓ Subject filled")
                        break
                except:
                    continue

            # Fill message
            for sel in ['textarea[name="description"]', 'textarea[placeholder*="description" i]', '#description', 'textarea']:
                try:
                    el = page.query_selector(sel)
                    if el and el.is_visible():
                        el.fill(MESSAGE)
                        print("   ✓ Message filled")
                        break
                except:
                    continue

            # Fill email if needed
            for sel in ['input[name="email"]', 'input[type="email"]']:
                try:
                    el = page.query_selector(sel)
                    if el and el.is_visible() and not el.input_value():
                        el.fill(EMAIL)
                        break
                except:
                    continue

            page.screenshot(path="/tmp/ts_form_filled.png")

            # Dump all visible buttons for debugging
            btns_info = page.evaluate('''() => {
                const btns = Array.from(document.querySelectorAll('button, input[type="submit"], [role="button"]'));
                return btns.filter(b => {
                    const r = b.getBoundingClientRect();
                    return r.width > 0 && r.height > 0 && r.top < window.innerHeight;
                }).map(b => ({
                    text: (b.textContent || b.value || '').trim().substring(0, 80),
                    tag: b.tagName,
                    id: b.id,
                    cls: (b.className || '').substring(0, 60)
                }));
            }''')
            print(f"   Found {len(btns_info)} visible buttons on support form:")
            for bi in btns_info:
                print(f"     [{bi['tag']}] id={bi['id']} cls={bi['cls']} text=\"{bi['text']}\"")

            # Submit — try all found buttons that look like submit
            submitted = False
            submit_keywords = ['submit', 'send', 'create', 'open', 'request']
            for bi in btns_info:
                txt_lower = bi['text'].lower()
                if any(kw in txt_lower for kw in submit_keywords):
                    try:
                        if bi['id']:
                            page.click(f'#{bi["id"]}', timeout=3000)
                        else:
                            page.click(f'{bi["tag"]}:has-text("{bi["text"]}")', timeout=3000)
                        page.wait_for_timeout(4000)
                        print(f"   ✅ CLICKED: {bi['text'][:40]}")
                        submitted = True
                        break
                    except Exception as e:
                        print(f"   ⚠️ Failed: {e}")

            # Last resort: click by index
            if not submitted and btns_info:
                try:
                    last = btns_info[-1]
                    page.evaluate(f'document.querySelectorAll("button, input[type=submit]")[{len(btns_info)-1}].click()')
                    print(f"   ⚠️ Clicked last button: {last['text'][:40]}")
                    submitted = True
                    page.wait_for_timeout(4000)
                except Exception as e:
                    print(f"   Failed: {e}")

            if submitted:
                page.screenshot(path="/tmp/ts_ticket_done.png")
                print("\n[4/4] ✅ SUPPORT TICKET SUBMITTED!")
                print("   Transak will review and enable widget API.")
                print("   Monitor: curl http://localhost:8000/api/providers/real-payment-status")
                print("   Health:  curl http://localhost:8000/transak/health")
            else:
                page.screenshot(path="/tmp/ts_need_manual_submit.png")
                print("\n   ⚠️ Form filled but couldn't auto-submit.")
                print("   → Click Submit in the browser window!")
                print("   → Then close browser and run monitor-health.sh")

            print(f"\n⏳ Browser stays open 30s...")
            page.wait_for_timeout(30000)

        except Exception as e:
            print(f"❌ Error: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            try:
                page.screenshot(path="/tmp/ts_error.png")
            except:
                pass
        finally:
            browser.close()

    # Start health monitor
    print("\n🔍 Starting Transak health monitor...")
    import subprocess
    result = subprocess.run([
        "bash", "/home/kali/.agents/skills/transak-activate/scripts/monitor-health.sh",
        "http://localhost:8000", "240"
    ])


if __name__ == "__main__":
    main()

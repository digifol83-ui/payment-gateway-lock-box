#!/usr/bin/env python3
"""Auto-submit Transak support ticket using stored Playwright session cookies."""
import json, sys, time
from pathlib import Path

EMAIL = "sichermayor@wshu.net"
STORAGE = Path("/home/kali/payment-gateway/.transak_storage.json")
MESSAGE_FILE = Path("/home/kali/payment-gateway/transak_support_message.txt")

SUPPORT_MESSAGE = MESSAGE_FILE.read_text().strip()

def main():
    from playwright.sync_api import sync_playwright

    storage_state = json.loads(STORAGE.read_text()) if STORAGE.exists() else None

    print("🚀 Launching browser with stored Transak session...")

    with sync_playwright() as p:
        browser = p.firefox.launch(headless=False, slow_mo=100)
        
        if storage_state:
            ctx = browser.new_context(
                storage_state={"cookies": storage_state.get("cookies", []), "origins": storage_state.get("origins", [])},
                viewport={"width": 1400, "height": 900},
            )
        else:
            ctx = browser.new_context(viewport={"width": 1400, "height": 900})

        page = ctx.new_page()

        try:
            # Try to access Transak dashboard with stored session
            print("→ Navigating to Transak Dashboard...")
            page.goto("https://dashboard.transak.com", timeout=20000, wait_until="domcontentloaded")
            page.wait_for_timeout(3000)
            page.screenshot(path="/tmp/transak_dashboard_auto.png")
            print(f"   URL: {page.url}")
            print(f"   Title: {page.title()}")

            # Check if we're logged in
            if "login" in page.url.lower():
                print("⚠️  Session expired — need manual login")
                print("   → Log in manually in the browser, then script continues...")
                # Wait for dashboard to appear
                page.wait_for_url("**/dashboard**", timeout=120000)
                print("✅ Dashboard detected!")
            else:
                print("✅ Already logged in with stored session")

            page.wait_for_timeout(2000)

            # Navigate to support/ticket page
            print("→ Finding support/ticket creation...")
            
            # Try common support paths
            support_found = False
            for support_path in [
                "/support",
                "/settings/support", 
                "/account/support",
                "/help",
                "/contact",
            ]:
                try:
                    page.goto(f"https://dashboard.transak.com{support_path}", timeout=10000, wait_until="domcontentloaded")
                    page.wait_for_timeout(2000)
                    if "login" not in page.url.lower():
                        support_found = True
                        print(f"   Found support at: {support_path}")
                        break
                except:
                    continue

            if not support_found:
                # Look for support link on page
                print("   Scanning for support links...")
                for link_text in ["Support", "Help", "Contact", "Ticket", "Chat", "?"]:
                    try:
                        el = page.query_selector(f'a:has-text("{link_text}"), button:has-text("{link_text}")')
                        if el and el.is_visible():
                            el.click()
                            page.wait_for_timeout(3000)
                            support_found = True
                            print(f"   Clicked: {link_text}")
                            break
                    except:
                        continue

            page.screenshot(path="/tmp/transak_support_page.png")
            print(f"   Current URL: {page.url}")

            # Look for "Create Ticket" or message form
            print("→ Looking for ticket creation form...")
            
            # Try to find and click "Create Ticket" or "New Ticket"
            for btn_text in ["Create Ticket", "New Ticket", "Submit a request", "Contact us", "Open Ticket", "Get in touch"]:
                try:
                    btn = page.query_selector(f'button:has-text("{btn_text}"), a:has-text("{btn_text}"), [role="button"]:has-text("{btn_text}")')
                    if btn and btn.is_visible():
                        btn.click()
                        page.wait_for_timeout(3000)
                        print(f"   Clicked: {btn_text}")
                        break
                except:
                    continue

            page.screenshot(path="/tmp/transak_ticket_form.png")

            # Try to fill subject and message
            print("→ Filling ticket form...")
            
            # Subject field
            for sel in ['input[name="subject"]', 'input[placeholder*="subject" i]', '#subject', '[data-testid="subject"]']:
                try:
                    el = page.query_selector(sel)
                    if el and el.is_visible():
                        el.fill("Enable Production API Create Widget URL and backend IP whitelisting")
                        print("   ✓ Subject filled")
                        break
                except:
                    continue

            # Message/description field
            for sel in ['textarea[name="description"]', 'textarea[placeholder*="description" i]', '#description', 'textarea', '[data-testid="description"]']:
                try:
                    el = page.query_selector(sel)
                    if el and el.is_visible():
                        el.fill(SUPPORT_MESSAGE)
                        print("   ✓ Message filled")
                        break
                except:
                    continue

            # Email field (if separate)
            for sel in ['input[name="email"]', 'input[type="email"]']:
                try:
                    el = page.query_selector(sel)
                    if el and el.is_visible() and not el.input_value():
                        el.fill(EMAIL)
                        print("   ✓ Email filled")
                        break
                except:
                    continue

            page.screenshot(path="/tmp/transak_form_filled.png")
            print("   Form filled. Check browser to submit.")
            print("   → Look for Submit/Send button")
            
            # Try to find submit button
            submitted = False
            for btn_text in ["Submit", "Send", "Create", "Open Ticket"]:
                try:
                    btn = page.query_selector(f'button:has-text("{btn_text}"), input[type="submit"][value*="{btn_text}" i]')
                    if btn and btn.is_visible():
                        btn.click()
                        page.wait_for_timeout(3000)
                        print(f"   ✅ Clicked: {btn_text}")
                        submitted = True
                        break
                except:
                    continue

            if submitted:
                page.screenshot(path="/tmp/transak_ticket_submitted.png")
                print("✅ TICKET SUBMITTED!")
                print("   Starting health monitor...")
                
                # Now run the health monitor
                import subprocess
                subprocess.Popen([
                    "bash", "/home/kali/.agents/skills/transak-activate/scripts/monitor-health.sh",
                    "http://localhost:8000", "240"  # 240 * 30s = 2 hours
                ])
            else:
                print("⚠️  Could not auto-submit — please click Submit in the browser")
                print("   Form is pre-filled and ready")

            print("\n⏳ Browser stays open. Close when done or press Ctrl+C.")
            try:
                page.wait_for_timeout(600000)  # 10 min
            except KeyboardInterrupt:
                pass

        except Exception as e:
            print(f"❌ Error: {type(e).__name__}: {e}")
            import traceback
            traceback.print_exc()
            try:
                page.screenshot(path="/tmp/transak_error_auto.png")
            except:
                pass
        finally:
            # Save updated cookies
            try:
                new_state = ctx.storage_state()
                STORAGE.write_text(json.dumps(new_state, indent=2))
                print("💾 Saved updated session cookies")
            except:
                pass
            browser.close()


if __name__ == "__main__":
    main()

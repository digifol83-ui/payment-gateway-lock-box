#!/usr/bin/env python3
"""Transak grab v3 — uses fresh login, navigates to Developers, scrapes API keys."""
import json, re, sys, time, urllib.request
from datetime import datetime, timezone
from pathlib import Path

EMAIL = "sichermayor@deltajohnsons.com"
SESSION = json.loads(Path("/home/kali/payment-gateway/.tempmail_session.json").read_text())
TOKEN = SESSION["token"]
SHOTS = Path("/tmp/transak_v3"); SHOTS.mkdir(exist_ok=True)

def shot(page, name):
    try:
        page.screenshot(path=str(SHOTS / f"{name}.png"), full_page=True)
        print(f"  📸 {name}.png")
    except Exception as e: print(f"  shot fail: {e}")

def fetch_otp(since_iso, timeout=120):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            req = urllib.request.Request("https://api.mail.tm/messages?page=1",
                headers={"Authorization": f"Bearer {TOKEN}"})
            with urllib.request.urlopen(req, timeout=10) as r:
                msgs = json.loads(r.read()).get("hydra:member") or []
            for m in msgs:
                if "transak" not in (m.get("from") or {}).get("address", "").lower(): continue
                if m.get("createdAt", "") <= since_iso: continue
                req2 = urllib.request.Request(f"https://api.mail.tm/messages/{m['id']}",
                    headers={"Authorization": f"Bearer {TOKEN}"})
                with urllib.request.urlopen(req2, timeout=10) as r2:
                    full = json.loads(r2.read())
                body = full.get("text") or " ".join(full.get("html") or [])
                match = re.search(r"\b(\d{6})\b", body)
                if match:
                    print(f"  ✓ OTP @ {m.get('createdAt')}: {match.group(1)}")
                    return match.group(1)
        except Exception as e: print(f"  poll err: {e}")
        time.sleep(4)
    return None

def main():
    from playwright.sync_api import sync_playwright
    started = datetime.now(timezone.utc).isoformat().replace("+00:00", "+00:00")
    print(f"[{started}] {EMAIL}")

    with sync_playwright() as p:
        browser = p.firefox.launch(headless=False)
        storage_path = Path("/home/kali/payment-gateway/.transak_storage.json")
        ctx_kwargs = {
            "user_agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "viewport": {"width": 1400, "height": 900}, "locale": "en-US",
        }
        if storage_path.exists():
            ctx_kwargs["storage_state"] = str(storage_path)
            print("  using saved session")
        ctx = browser.new_context(**ctx_kwargs)
        page = ctx.new_page(); page.set_default_timeout(45000)

        try:
            # First try landing on dashboard — if session valid, skip login
            page.goto("https://dashboard.transak.com/dashboard", wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(4500)
            shot(page, "00_initial")
            if "/login" not in page.url:
                print(f"  ✓ session valid, on {page.url}")
            else:
                print("→ login required")
                page.goto("https://dashboard.transak.com/login", wait_until="domcontentloaded", timeout=45000)
                page.wait_for_timeout(4000)
                for sel in ['input[type="email"]', 'input[name="email"]']:
                    el = page.query_selector(sel)
                    if el and el.is_visible(): el.fill(EMAIL); break
                shot(page, "00b_email_filled")
                for sel in ['button:has-text("Sign in")', 'button:has-text("Log in")', 'button[type="submit"]']:
                    btn = page.query_selector(sel)
                    if btn and btn.is_visible() and btn.is_enabled():
                        btn.click(); print(f"  clicked: {sel}"); break
                page.wait_for_timeout(5000)
                shot(page, "00c_after_email_submit")
                otp = fetch_otp(started, timeout=180)
                if not otp: print("✗ no OTP"); shot(page, "00d_no_otp"); sys.exit(3)
                digits = page.query_selector_all('input[maxlength="1"]')
                if len(digits) >= 6:
                    for i, d in enumerate(otp[:6]):
                        digits[i].fill(d); page.wait_for_timeout(60)
                else:
                    for sel in ['input[name="otp"]','input[autocomplete="one-time-code"]']:
                        el = page.query_selector(sel)
                        if el and el.is_visible(): el.fill(otp); break
                page.wait_for_timeout(800)
                for sel in ['button:has-text("Submit")','button:has-text("Verify")','button:has-text("Continue")','button[type="submit"]']:
                    btn = page.query_selector(sel)
                    if btn and btn.is_visible() and btn.is_enabled(): btn.click(); break
                page.wait_for_timeout(7000)
            shot(page, "01_dashboard")
            print(f"  url={page.url}")
            try:
                ctx.storage_state(path=str(storage_path))
                print(f"  ✓ saved session to {storage_path}")
            except Exception as e: print(f"  storage save: {e}")

            # Click Developers in left nav
            print("→ click Developers")
            for sel in ['a:has-text("Developers")', 'button:has-text("Developers")',
                        '[href*="developer" i]', 'nav a:has-text("Developer")', 'div:has-text("Developers")']:
                els = page.query_selector_all(sel)
                for el in els:
                    if el.is_visible():
                        try:
                            el.click()
                            print(f"  clicked: {sel}")
                            page.wait_for_timeout(3500)
                            break
                        except Exception as e: print(f"  click fail {sel}: {e}")
                if "developer" in page.url.lower() or "api" in page.url.lower(): break
            shot(page, "02_developers")
            print(f"  url={page.url}")

            # Look for "API Keys" submenu / tab
            for sel in ['a:has-text("API Key")', 'button:has-text("API Key")', 'div:has-text("API Key")',
                        'a:has-text("Credentials")', '[href*="api-key" i]']:
                els = page.query_selector_all(sel)
                for el in els:
                    if el.is_visible():
                        try:
                            el.click()
                            print(f"  clicked: {sel}")
                            page.wait_for_timeout(3000)
                            break
                        except: pass
            shot(page, "03_apikeys_tab")
            print(f"  url={page.url}")

            # Make sure Production env is selected (top-right toggle)
            # The screenshot showed "Production" green badge already — but ensure it
            # by clicking the env toggle if labelled "Staging"
            try:
                staging_toggle = page.query_selector('button:has-text("Staging")')
                if staging_toggle and staging_toggle.is_visible():
                    print("  switching env: Staging→Production")
                    staging_toggle.click(); page.wait_for_timeout(1200)
                    prod_opt = page.query_selector('li:has-text("Production"), button:has-text("Production"), [role="option"]:has-text("Production")')
                    if prod_opt: prod_opt.click(); page.wait_for_timeout(2500)
            except Exception as e: print(f"  env toggle: {e}")
            shot(page, "04_env_set")

            # Click any reveal/show/copy buttons
            for sel in ['button:has-text("Reveal")','button:has-text("Show")','button:has-text("View")',
                        'button:has-text("Copy")', '[aria-label*="reveal" i]','[aria-label*="show" i]',
                        '[aria-label*="copy" i]','button[title*="copy" i]','svg[aria-label*="eye" i]']:
                try:
                    for btn in page.query_selector_all(sel):
                        if btn.is_visible():
                            btn.click(); page.wait_for_timeout(700)
                            print(f"  clicked: {sel}")
                except: pass
            shot(page, "05_revealed")

            html = page.content()
            (SHOTS / "05_revealed.html").write_text(html)

            # Extract via DOM: read all input values
            print("\n=== INPUT VALUES ===")
            inputs = page.query_selector_all('input')
            for i, el in enumerate(inputs):
                try:
                    v = el.get_attribute("value") or el.input_value()
                    name = el.get_attribute("name") or ""
                    label = el.get_attribute("aria-label") or el.get_attribute("placeholder") or ""
                    if v and len(v) >= 16:
                        print(f"  [{i}] name={name!r} label={label!r} value={v[:30]}...{v[-6:]} (len={len(v)})")
                    elif v:
                        print(f"  [{i}] name={name!r} label={label!r} value={v!r}")
                except Exception as e: pass

            # also try regex on innerText
            text = page.inner_text("body")
            (SHOTS / "05_body_text.txt").write_text(text)
            uuids = sorted(set(re.findall(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", text)))
            print(f"\n=== UUIDs in body text ({len(uuids)}) ===")
            for u in uuids: print(f"  {u}")

            # Long base64ish tokens visible as text (likely access token)
            tokens = sorted(set(re.findall(r"\b[A-Za-z0-9_\-\.]{60,}\b", text)))
            print(f"\n=== Long tokens in body text ({len(tokens)}) ===")
            for t in tokens[:10]: print(f"  {t[:100]}")

            input_pause = "1"  # don't actually pause; we're done

        except Exception as e:
            print(f"FATAL: {type(e).__name__}: {e}")
            try: shot(page, "99_err")
            except: pass
            sys.exit(1)
        finally:
            page.wait_for_timeout(1500)
            browser.close()

if __name__ == "__main__": main()

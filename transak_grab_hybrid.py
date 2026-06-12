#!/usr/bin/env python3
"""
Transak hybrid grab — human solves the CAPTCHA, script does everything else.

Flow:
  1. Opens Firefox visibly (WSLg → Windows desktop)
  2. Pre-fills email
  3. Waits for human to solve CAPTCHA + click Sign in
  4. Detects OTP screen, fetches OTP from mail.tm, autofills
  5. Submits, lands on dashboard
  6. Saves storage state to .transak_storage.json (so future runs skip login)
  7. Navigates to Developers → API Keys, switches to Production env
  8. Extracts API key, secret, access token via DOM input.value
  9. Updates .env, prints summary, optionally exits

Re-running: if .transak_storage.json exists and is valid, skips steps 1–6.
"""
import json, os, re, sys, time, urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/home/kali/payment-gateway")
SESSION = json.loads((ROOT / ".tempmail_session.json").read_text())
EMAIL = SESSION.get("address") or "sichermayor@wshu.net"
TOKEN = SESSION["token"]
SHOTS = Path("/tmp/transak_hybrid"); SHOTS.mkdir(exist_ok=True)
STORAGE = ROOT / ".transak_storage.json"
ENV = ROOT / ".env"


def mask_secret(value, head=6, tail=4):
    value = str(value or "")
    if not value:
        return ""
    if len(value) <= head + tail:
        return "*" * len(value)
    return f"{value[:head]}...{value[-tail:]}"


def shot(page, name):
    try:
        page.screenshot(path=str(SHOTS / f"{name}.png"), full_page=True)
    except Exception: pass


def fetch_otp(since_iso, timeout=240):
    deadline = time.time() + timeout
    print(f"  [otp] polling mail.tm for new code (timeout {timeout}s)...")
    last_status = 0
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
                    print(f"  [otp] ✓ got code at {m.get('createdAt')}: ******")
                    return match.group(1)
        except Exception as e: print(f"  [otp] poll err: {e}")
        if time.time() - last_status > 15:
            print(f"  [otp] still waiting... ({int(deadline - time.time())}s left)")
            last_status = time.time()
        time.sleep(3)
    return None


def update_env(updates: dict):
    content = ENV.read_text()
    for k, v in updates.items():
        pat = re.compile(rf"^{re.escape(k)}=.*$", re.MULTILINE)
        if pat.search(content):
            content = pat.sub(f"{k}={v}", content)
        else:
            content += f"\n{k}={v}"
    ENV.write_text(content)
    print(f"  [env] updated {len(updates)} keys in .env")


def fill_input(page, selector, text):
    try:
        el = page.query_selector(selector)
        if el and el.is_visible():
            el.fill(text); return True
    except Exception: pass
    return False


def click_first_visible(page, selectors):
    for sel in selectors:
        try:
            for el in page.query_selector_all(sel):
                if el.is_visible() and el.is_enabled():
                    el.click(); return sel
        except Exception: continue
    return None


def is_logged_in(page) -> bool:
    """Check whether we're on a dashboard page, not login."""
    url = page.url
    return "/login" not in url and ("dashboard" in url or "/account" in url or "/developer" in url or "/orders" in url)


def otp_screen_visible(page) -> bool:
    """Return true when Transak is asking for the email verification code."""
    digit_inputs = page.query_selector_all('input[maxlength="1"]')
    if len(digit_inputs) >= 6 and all(d.is_visible() for d in digit_inputs[:6]):
        return True
    for sel in [
        'input[name="otp"]',
        'input[name="code"]',
        'input[autocomplete="one-time-code"]',
        'input[placeholder*="code" i]',
        'input[placeholder*="OTP" i]',
    ]:
        el = page.query_selector(sel)
        if el and el.is_visible():
            return True
    return False


def main():
    from playwright.sync_api import sync_playwright

    PROFILE_DIR = "/tmp/transak_profile"
    Path(PROFILE_DIR).mkdir(exist_ok=True)
    with sync_playwright() as p:
        print(f"\n[{datetime.now().isoformat()}] Launching Firefox (persistent profile)")
        ctx = p.firefox.launch_persistent_context(
            user_data_dir=PROFILE_DIR,
            headless=False,
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1400, "height": 900}, locale="en-US",
        )
        browser = ctx.browser  # may be None for persistent context — that's OK
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.set_default_timeout(60000)

        try:
            # Try to land directly on dashboard — if session valid, skip login
            print("→ goto dashboard")
            page.goto("https://dashboard.transak.com/dashboard", wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(5000)
            shot(page, "01_initial")

            if is_logged_in(page):
                print(f"  ✓ session valid: {page.url}")
            else:
                print("\n" + "="*70)
                print("  ACTION REQUIRED IN BROWSER WINDOW")
                print("  1. Email is pre-filled.")
                print("  2. Solve the CAPTCHA (select the images).")
                print("  3. Click 'Sign in'.")
                print("  Script will take over when the OTP screen appears.")
                print("="*70 + "\n")

                page.goto("https://dashboard.transak.com/login", wait_until="domcontentloaded", timeout=45000)
                page.wait_for_timeout(3000)

                # pre-fill email
                filled = False
                for sel in ['input[type="email"]', 'input[name="email"]', 'input[placeholder*="email" i]']:
                    if fill_input(page, sel, EMAIL): filled = True; break
                print(f"  email pre-filled: {filled}")
                shot(page, "02_email_prefilled")

                email_submit_iso = datetime.now(timezone.utc).isoformat()
                clicked = click_first_visible(page, [
                    'button:has-text("Sign in")',
                    'button:has-text("Log in")',
                    'button:has-text("Continue")',
                    'button[type="submit"]',
                ])
                last_submit_click = time.time()
                print(f"  clicked sign-in: {clicked}")
                page.wait_for_timeout(5000)

                # wait for the user to solve CAPTCHA + click Sign in
                # detect by: OTP input appearing OR URL change OR digit-input boxes appearing
                print("  waiting up to 5 min for OTP screen...")
                otp_screen_started = None
                deadline = time.time() + 300
                while time.time() < deadline:
                    try:
                        if is_logged_in(page):
                            print("  ✓ logged in (no OTP needed)"); break
                        if otp_screen_visible(page):
                            otp_screen_started = email_submit_iso
                            print("  ✓ OTP screen detected"); break
                        # If an invisible reCAPTCHA challenge was completed, the sign-in
                        # button may need one more click before Transak sends the OTP.
                        if time.time() - last_submit_click > 20:
                            clicked = click_first_visible(page, [
                                'button:has-text("Sign in")',
                                'button:has-text("Log in")',
                                'button:has-text("Continue")',
                                'button[type="submit"]',
                            ])
                            if clicked:
                                email_submit_iso = datetime.now(timezone.utc).isoformat()
                                last_submit_click = time.time()
                                print(f"  re-clicked sign-in: {clicked}")
                    except Exception: pass
                    time.sleep(2)

                if not is_logged_in(page) and otp_screen_started:
                    shot(page, "03_otp_screen")
                    otp = fetch_otp(otp_screen_started, timeout=180)
                    if not otp:
                        print("  ✗ no OTP within 180s"); shot(page, "03b_no_otp"); sys.exit(3)
                    digits = page.query_selector_all('input[maxlength="1"]')
                    if len(digits) >= 6:
                        for i, d in enumerate(otp[:6]):
                            digits[i].fill(d); page.wait_for_timeout(60)
                    else:
                        for sel in ['input[name="otp"]','input[autocomplete="one-time-code"]']:
                            if fill_input(page, sel, otp): break
                    page.wait_for_timeout(700)
                    shot(page, "04_otp_filled")
                    sel = click_first_visible(page, ['button:has-text("Submit")','button:has-text("Verify")',
                                                    'button:has-text("Continue")','button[type="submit"]'])
                    print(f"  submitted OTP via: {sel}")
                    page.wait_for_timeout(8000)

                shot(page, "05_post_login")
                print(f"  url={page.url}")
                if not is_logged_in(page):
                    print("  ✗ login didn't complete"); sys.exit(4)

                # save session for future runs
                try:
                    ctx.storage_state(path=str(STORAGE))
                    print(f"  ✓ saved session → {STORAGE.name}")
                except Exception as e: print(f"  storage save err: {e}")

            # === Now navigate to Developers / API Keys ===
            print("\n→ navigate to Developers")
            sel = click_first_visible(page, ['nav a:has-text("Developers")', 'a:has-text("Developers")',
                                             'button:has-text("Developers")', '[href*="developer" i]'])
            if sel:
                print(f"  clicked: {sel}")
                page.wait_for_timeout(4000)
            else:
                # fallback: direct navigation
                print("  no nav link found, trying direct URLs")
                for url in ["https://dashboard.transak.com/developers",
                            "https://dashboard.transak.com/account/api-key",
                            "https://dashboard.transak.com/account/api-keys",
                            "https://dashboard.transak.com/settings/api-keys"]:
                    try:
                        page.goto(url, wait_until="domcontentloaded", timeout=20000)
                        page.wait_for_timeout(3500)
                        if "404" not in page.title():
                            print(f"  ✓ {url}"); break
                    except Exception as e: print(f"  fail {url}: {e}")
            shot(page, "06_developers")
            print(f"  url={page.url}")

            # ensure Production env is selected (top-right)
            try:
                staging = page.query_selector('button:has-text("Staging")')
                if staging and staging.is_visible():
                    print("  switching env Staging→Production")
                    staging.click(); page.wait_for_timeout(1500)
                    prod = page.query_selector('[role="option"]:has-text("Production"), li:has-text("Production"), button:has-text("Production")')
                    if prod: prod.click(); page.wait_for_timeout(3000)
            except Exception as e: print(f"  env toggle err: {e}")

            # navigate to API Key sub-tab if present
            for sel in ['a:has-text("API Key")', 'button:has-text("API Key")', 'div[role="tab"]:has-text("API Key")',
                        'a:has-text("Credentials")']:
                try:
                    el = page.query_selector(sel)
                    if el and el.is_visible():
                        el.click(); print(f"  clicked tab: {sel}"); page.wait_for_timeout(3000); break
                except Exception: pass
            shot(page, "07_api_key_tab")

            # click any reveal/show/copy/eye icons
            for sel in ['button:has-text("Reveal")','button:has-text("Show")','button:has-text("View")',
                        'button:has-text("Copy")','[aria-label*="reveal" i]','[aria-label*="show" i]',
                        '[aria-label*="copy" i]','[aria-label*="eye" i]','button[title*="copy" i]',
                        'svg[aria-label*="eye" i]', 'svg[data-icon*="eye" i]']:
                try:
                    for btn in page.query_selector_all(sel):
                        if btn.is_visible():
                            btn.click(); page.wait_for_timeout(700)
                except Exception: pass
            page.wait_for_timeout(2000)
            shot(page, "08_revealed")
            (SHOTS / "08_revealed.html").write_text(page.content())

            # === EXTRACT ===
            print("\n=== EXTRACTING ===")
            # method 1: read every input.value
            candidates = []
            for el in page.query_selector_all('input'):
                try:
                    v = el.get_attribute("value") or el.input_value() or ""
                    if not v or len(v) < 16: continue
                    name = el.get_attribute("name") or ""
                    label = el.get_attribute("aria-label") or el.get_attribute("placeholder") or ""
                    candidates.append({"name": name, "label": label, "value": v})
                except Exception: pass
            print(f"  found {len(candidates)} input candidates with value≥16 chars")
            for c in candidates:
                v = c["value"]
                disp = mask_secret(v, 8, 6)
                print(f"   • name={c['name']!r} label={c['label']!r} value={disp} (len={len(v)})")

            # method 2: regex on body text (after reveals)
            text = page.inner_text("body")
            (SHOTS / "08_body.txt").write_text(text)
            uuids = sorted(set(re.findall(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", text)))
            jwts = sorted(set(re.findall(r"\beyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-\.]{20,}\b", text)))
            long_tokens = sorted(set(t for t in re.findall(r"\b[A-Za-z0-9_\-]{40,}\b", text)
                                     if not t.startswith("hs-") and "interactives" not in t and "anchor" not in t))
            body_lines = [line.strip() for line in text.splitlines() if line.strip()]
            dashboard_api_secret = None
            try:
                secret_idx = body_lines.index("API SECRET")
                candidate_idx = secret_idx + 2 if body_lines[secret_idx + 1].lower() == "refresh" else secret_idx + 1
                candidate = body_lines[candidate_idx]
                if re.fullmatch(r"[A-Za-z0-9+/=_-]{16,}", candidate):
                    dashboard_api_secret = candidate
            except Exception:
                dashboard_api_secret = None
            print(f"  uuids: {uuids}")
            print(f"  jwts:  {[j[:50]+'...' for j in jwts]}")
            print(f"  long_tokens (filtered): {[mask_secret(t, 10, 6) for t in long_tokens[:10]]}")

            # === heuristic mapping ===
            mapping = {}
            for c in candidates:
                hint = (c["name"] + " " + c["label"]).lower()
                v = c["value"]
                if "api" in hint and "key" in hint and "TRANSAK_API_KEY" not in mapping:
                    mapping["TRANSAK_API_KEY"] = v
                elif ("secret" in hint or "private" in hint) and "TRANSAK_SECRET" not in mapping:
                    mapping["TRANSAK_SECRET"] = v
                elif ("access" in hint or "token" in hint or "bearer" in hint) and "TRANSAK_ACCESS_TOKEN" not in mapping:
                    mapping["TRANSAK_ACCESS_TOKEN"] = v
            # backstops
            if "TRANSAK_API_KEY" not in mapping and uuids: mapping["TRANSAK_API_KEY"] = uuids[0]
            if "TRANSAK_ACCESS_TOKEN" not in mapping and jwts: mapping["TRANSAK_ACCESS_TOKEN"] = jwts[0]
            if "TRANSAK_SECRET" not in mapping and dashboard_api_secret:
                mapping["TRANSAK_SECRET"] = dashboard_api_secret

            print("\n=== PROPOSED .env UPDATES ===")
            for k, v in mapping.items():
                disp = mask_secret(v, 8, 6)
                print(f"  {k} = {disp}")

            if mapping:
                # write a stash file so the next step can update .env
                pending = ROOT / ".transak_keys_pending.json"
                pending.write_text(json.dumps(mapping, indent=2))
                pending.chmod(0o600)
                print(f"\n  ✓ stashed → .transak_keys_pending.json")
                print(f"  After review, run: python3 -c \"import json,os,re; d=json.load(open('.transak_keys_pending.json')); ...\"")
            else:
                print("  ✗ no values matched — inspect /tmp/transak_hybrid/08_*.png")

            # leave window open briefly so user can see
            print("\n  Browser stays open 30s for verification...")
            time.sleep(30)

        except Exception as e:
            print(f"FATAL: {type(e).__name__}: {e}")
            try: shot(page, "99_err")
            except: pass
            sys.exit(1)
        finally:
            try: ctx.close()
            except Exception: pass

if __name__ == "__main__": main()

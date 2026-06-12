#!/usr/bin/env python3
"""
ChangeNOW API Key Grab — standalone login + verification + key extraction.
Handles both PRO trading accounts and Affiliate/Business accounts (where API keys live).

Usage:
    python3 grab_changenow.py              # headless (default)
    python3 grab_changenow.py --headed     # visible browser for CAPTCHA
    python3 grab_changenow.py --fresh      # ignore cached auth, re-login
    python3 grab_changenow.py --cooldown   # wait 5min for rate limit then login
"""
import json, os, re, sys, time, urllib.request
from datetime import datetime, timezone
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PT

ROOT = Path("/home/kali/payment-gateway")
ENV_FILE = ROOT / ".env"
AUTH_FILE = ROOT / ".changenow_auth.json"
AFF_AUTH_FILE = ROOT / ".changenow_affiliate_auth.json"
MAIL = json.loads((ROOT / ".tempmail_session.json").read_text())
EMAIL = MAIL["address"]
TOKEN = MAIL["token"]
PASSWORD = "Karmostaji_2026!Secure_GW"
COOLDOWN_SECONDS = 300

CHANGENOW_CONFIG = {
    "homepage": "https://changenow.io",
    "login_url": "https://changenow.io/login",
    "affiliate_signup_url": "https://changenow.io/affiliate",
    "api_urls": [
        "https://changenow.io/affiliate/dashboard",
        "https://changenow.io/affiliate/settings",
        "https://changenow.io/pro/settings",
        "https://changenow.io/pro/settings/api",
    ],
    "env_keys": ["CHANGENOW_API_KEY", "CHANGENOW_SECRET"],
    "env_var": "CHANGENOW_ENV",
}


# ============================================================================
# UTILITIES
# ============================================================================
def mask(s, pre=6, post=4):
    s = str(s or "")
    if len(s) <= pre + post:
        return "*" * len(s)
    return f"{s[:pre]}...{s[-post:]}"


def update_env(updates: dict):
    content = ENV_FILE.read_text() if ENV_FILE.exists() else ""
    for k, v in updates.items():
        if not v:
            continue
        pat = re.compile(rf"^{re.escape(k)}=.*$", re.MULTILINE)
        if pat.search(content):
            content = pat.sub(f"{k}={v}", content)
        else:
            content += f"\n# CHANGENOW\n{k}={v}\n"
    ENV_FILE.write_text(content)
    print(f"  [env] Updated {len(updates)} keys")


def fetch_otp(since_iso: str = "", timeout: int = 60, allow_older: bool = False) -> str | None:
    """Poll mail.tm for a ChangeNOW verification code."""
    deadline = time.time() + timeout
    print(f"  [otp] Polling mail.tm (timeout {timeout}s, older={allow_older})...")
    while time.time() < deadline:
        try:
            req = urllib.request.Request(
                "https://api.mail.tm/messages?page=1",
                headers={"Authorization": f"Bearer {TOKEN}"},
            )
            with urllib.request.urlopen(req, timeout=10) as r:
                msgs = json.loads(r.read()).get("hydra:member") or []
            for m in msgs:
                created = m.get("createdAt", "")
                if since_iso and not allow_older and created <= since_iso:
                    continue
                sender = (m.get("from") or {}).get("address", "").lower()
                if "changenow" not in sender:
                    continue
                req2 = urllib.request.Request(
                    f"https://api.mail.tm/messages/{m['id']}",
                    headers={"Authorization": f"Bearer {TOKEN}"},
                )
                with urllib.request.urlopen(req2, timeout=10) as r2:
                    full = json.loads(r2.read())
                body = (full.get("text") or "") + " " + " ".join(full.get("html") or [])
                match = re.search(r"\b(\d{6})\b", body)
                if match:
                    print(f"  [otp] ✓ Found code from {sender}: {match.group(1)}")
                    return match.group(1)
                link = re.search(r'https?://[^\s"\'<>]*(?:confirm|verify|activate)[^\s"\'<>]*', body, re.I)
                if link:
                    print(f"  [otp] ✓ Found confirmation link from {sender}")
                    return link.group(0)
        except Exception:
            pass
        time.sleep(3)
    print("  [otp] ⚠️  Timed out waiting for code")
    return None


# ============================================================================
# VERIFICATION HANDLING
# ============================================================================
def handle_verification(page, signup_start_iso: str) -> bool:
    """Detect and handle email verification on any ChangeNOW page. Returns True if verified."""
    try:
        body = page.inner_text("body").lower()
    except Exception:
        return False

    if "confirm" not in body or "code" not in body:
        return False

    print("\n  ✅ On verification page!")
    # Click "Resend code" for fresh code
    try:
        page.locator('button:has-text("Resend code")').first.click(timeout=5000)
        page.wait_for_timeout(4000)
        print("  Resend clicked")
    except Exception:
        pass

    # Try: wait for fresh email (up to 60s)
    code = fetch_otp(since_iso=datetime.now(timezone.utc).isoformat(), timeout=40, allow_older=False)
    if not code:
        # Fallback: use any recent code
        code = fetch_otp(since_iso=signup_start_iso, timeout=10, allow_older=True)

    if not code or code.startswith("http"):
        return False

    # Fill code with locator.fill() (triggers React events properly)
    for code_sel in [
        'input[name="confirmation-code"]',
        'input[placeholder*="code" i]',
        'input[autocomplete="one-time-code"]',
    ]:
        try:
            code_input = page.locator(code_sel)
            if code_input.is_visible(timeout=3000):
                code_input.fill(code)
                print(f"  ✓ Code filled: {code}")
                break
        except Exception:
            continue
    else:
        # JS fallback
        page.evaluate(f"""(code) => {{
            for (const inp of document.querySelectorAll('input')) {{
                const n = (inp.name || inp.placeholder || '').toLowerCase();
                if (inp.offsetParent && (n.includes('code') || n.includes('confirm') || inp.type === 'number')) {{
                    inp.focus();
                    inp.value = code;
                    inp.dispatchEvent(new Event('input', {{bubbles: true}}));
                    inp.dispatchEvent(new Event('change', {{bubbles: true}}));
                    return;
                }}
            }}
        }}""", code)
        print(f"  ✓ Code filled (JS fallback)")

    time.sleep(1)
    # Click submit
    for btn_sel in ['button:has-text("Submit")', 'button:has-text("Verify")', 'button:has-text("Confirm")']:
        try:
            btn = page.locator(btn_sel).first
            if btn.is_visible(timeout=2000):
                btn.click()
                print(f"  ✓ Submit clicked: {btn_sel}")
                page.wait_for_timeout(10000)
                return True
        except Exception:
            pass

    page.keyboard.press("Enter")
    page.wait_for_timeout(8000)
    return True


# ============================================================================
# KEY EXTRACTION
# ============================================================================
def extract_keys_from_page(page) -> dict:
    """Scan the current page for API keys using multiple strategies."""
    result = {}

    # Click "Create API key" / "Generate" buttons
    for btn_text in ["Create API key", "Generate", "Add key", "New key", "Create key", "API key"]:
        try:
            submitted = page.evaluate(f"""(text) => {{
                const els = document.querySelectorAll('button, a, span, div[role="button"]');
                for (const el of els) {{
                    const t = (el.textContent || '').trim();
                    if (t.toLowerCase().includes(text.toLowerCase()) && el.offsetParent) {{
                        el.click();
                        return 'clicked: ' + t;
                    }}
                }}
                return 'not found';
            }}""", btn_text)
            if "clicked" in submitted:
                print(f"  [extract] Clicked '{btn_text}': {submitted}")
                page.wait_for_timeout(3000)
                break
        except Exception:
            pass

    # Strategy: Read input values
    try:
        keys_found = page.evaluate("""() => {
            const results = {};
            const inputs = document.querySelectorAll('input');
            for (const inp of inputs) {
                const val = (inp.value || '').trim();
                if (val.length < 16) continue;
                const label = (
                    (inp.getAttribute('aria-label') || '') +
                    (inp.getAttribute('placeholder') || '') +
                    (inp.getAttribute('name') || '') +
                    (inp.id || '')
                ).toLowerCase();
                if (label.includes('secret') || label.includes('private')) {
                    if (!results.secret) results.secret = val;
                } else if (label.includes('key') || label.includes('api') || label.includes('token')) {
                    if (!results.key) results.key = val;
                }
            }
            return results;
        }""")
        if keys_found:
            result.update(keys_found)
            print(f"  [extract] Found via inputs: {list(keys_found.keys())}")
    except Exception:
        pass

    # Strategy: Scan visible text for patterns
    try:
        text = page.inner_text("body")
        uuids = re.findall(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", text)
        hex_keys = re.findall(r"\b[0-9a-f]{32,}\b", text, re.I)
        tokens = re.findall(r"\b[A-Za-z0-9+/=_-]{32,}\b", text)
        for u in uuids:
            if "key" not in result:
                result["key"] = u
        for h in hex_keys:
            if "secret" not in result:
                result["secret"] = h
        for t in tokens:
            if t.startswith("sk_") and "secret" not in result:
                result["secret"] = t
            elif t.startswith("pk_") and "key" not in result:
                result["key"] = t
    except Exception:
        pass

    # Strategy: Look for key display elements
    try:
        extras = page.evaluate("""() => {
            const results = {};
            for (const sel of ['code', 'pre', '[class*="key"]', '[class*="secret"]',
                               '[class*="token"]', '[class*="credential"]', '.key-display']) {
                const els = document.querySelectorAll(sel);
                for (const el of els) {
                    const text = (el.textContent || '').trim();
                    if (text.length >= 16 && text.length < 200) {
                        const cls = (el.className || '').toLowerCase();
                        if (cls.includes('secret') && !results.secret) results.secret = text;
                        else if ((cls.includes('key') || cls.includes('api')) && !results.key) results.key = text;
                    }
                }
            }
            return results;
        }""")
        if extras:
            result.update(extras)
    except Exception:
        pass

    return result


def try_navigate_to_keys(page) -> bool:
    """Navigate through known ChangeNOW API key pages."""
    for api_url in CHANGENOW_CONFIG["api_urls"]:
        try:
            print(f"  [nav] Trying: {api_url}")
            page.goto(api_url, wait_until="domcontentloaded", timeout=15000)
            page.wait_for_timeout(4000)
            url = page.url.lower()
            if "/login" not in url and "/signup" not in url and "/register" not in url:
                print(f"  [nav] ✓ Landed at: {page.url[:100]}")
                print(f"  [nav]   Title: {page.title()}")
                return True
            else:
                print(f"  [nav] Redirected to login — not authenticated")
        except Exception as e:
            print(f"  [nav] ✗ Failed: {e}")
    return False


def save_keys_result(keys: dict) -> dict:
    """Map extracted keys to env variable names and save."""
    mapped = {}
    if keys.get("key"):
        mapped["CHANGENOW_API_KEY"] = keys["key"]
    if keys.get("secret"):
        mapped["CHANGENOW_SECRET"] = keys["secret"]
    mapped["CHANGENOW_ENV"] = "production"

    update_env(mapped)
    stash_path = ROOT / ".changenow_keys.json"
    stash_path.write_text(json.dumps(keys, indent=2))
    stash_path.chmod(0o600)
    print(f"  💾 Stashed: .changenow_keys.json")
    return mapped


# ============================================================================
# LOGIN FLOW
# ============================================================================
def login_changenow(page, headed: bool = False) -> bool:
    """Login to ChangeNOW PRO account. Returns True if dashboard reached."""
    cfg = CHANGENOW_CONFIG
    signup_start = datetime.now(timezone.utc).isoformat()

    # Step 1: Go to login page
    print(f"  → Loading {cfg['login_url']}")
    try:
        page.goto(cfg["login_url"], wait_until="domcontentloaded", timeout=30000)
    except PT:
        print("  ⚠️  Page load timeout, continuing...")
    page.wait_for_timeout(4000)
    print(f"  URL: {page.url[:100]}")

    # Step 2: Click Log In tab (SPA reveals form on click)
    print("  → Clicking Log In tab...")
    try:
        tab_btn = page.locator('button:has-text("Log In"):visible').first
        tab_btn.click(timeout=5000)
        page.wait_for_timeout(4000)
        print("  ✓ Clicked Log In tab")
    except Exception as e:
        print(f"  ⚠️  Tab click failed: {e}")

    # Step 3: Fill form with locator.fill() (triggers React events)
    try:
        email_input = page.locator('input[name="email"]')
        if email_input.is_visible(timeout=5000):
            email_input.fill(EMAIL)
            print(f"  ✓ Email: {EMAIL}")
    except Exception as e:
        print(f"  ⚠️  Email: {e}")

    try:
        pass_input = page.locator('input[name="password"]')
        if pass_input.is_visible(timeout=3000):
            pass_input.fill(PASSWORD)
            print("  ✓ Password")
    except Exception as e:
        print(f"  ⚠️  Password: {e}")

    # Step 4: Submit
    try:
        page.locator('button:has-text("Log In")').first.click(timeout=5000)
        print("  ✓ Submit clicked")
    except Exception:
        try:
            page.keyboard.press("Enter")
            print("  Pressed Enter")
        except Exception:
            pass

    page.wait_for_timeout(8000)
    print(f"  After login URL: {page.url[:100]}")

    # Step 5: Handle verification if needed
    handle_verification(page, signup_start)

    # Step 6: Check if we're actually logged in
    page.wait_for_timeout(5000)
    url = page.url.lower()
    auth_indicators = ["/pro/", "/balance", "/dashboard", "/account", "/affiliate"]
    is_authenticated = any(ind in url for ind in auth_indicators)

    if not is_authenticated:
        try:
            body = page.inner_text("body").lower()
            form_gone = "confirm" not in body or "code" not in body
            on_auth_or_login = "/authorization" in url or "/login" in url
            if form_gone and on_auth_or_login:
                print("  → Trying to reach dashboard after verification...")
                try:
                    page.goto("https://changenow.io/pro/balance",
                              wait_until="domcontentloaded", timeout=15000)
                    page.wait_for_timeout(5000)
                    url = page.url.lower()
                    is_authenticated = any(ind in url for ind in auth_indicators)
                except Exception:
                    pass
        except Exception:
            pass

    if is_authenticated:
        print(f"\n  🎉 LOGGED IN! URL: {page.url[:100]}")
        return True

    # Check cookies as last resort
    try:
        cookies = page.context.cookies()
        has_auth = any(c["name"] in ("cn_at", "cn_rt", "cn_sid") for c in cookies)
        if has_auth:
            print("  ℹ️  Have auth cookies")
            return True
    except Exception:
        pass

    print(f"  ⚠️  Not authenticated. URL: {page.url[:100]}")
    return False


# ============================================================================
# AFFILIATE/BUSINESS ACCOUNT FLOW
# ============================================================================
def signup_affiliate(page, headed: bool = False) -> bool:
    """Sign up for ChangeNOW business account (provides API keys)."""
    print(f"\n  {'─'*50}")
    print(f"  📋 Affiliate/Business Account Signup")
    print(f"  {'─'*50}")
    signup_start = datetime.now(timezone.utc).isoformat()

    try:
        page.goto(CHANGENOW_CONFIG["affiliate_signup_url"],
                  wait_until="domcontentloaded", timeout=20000)
    except PT:
        print("  ⚠️  Page load timeout, continuing...")
    page.wait_for_timeout(5000)

    # Fill initial form (email + password)
    try:
        page.locator('input[name="email"]').fill(EMAIL)
        print(f"  ✓ Email: {EMAIL}")
    except Exception:
        pass
    try:
        page.locator('input[name="password"]').fill(PASSWORD)
        print("  ✓ Password")
    except Exception:
        pass

    # Click Create account to reveal full form
    for sel in ['button:has-text("Create account")', 'button:has-text("Sign up")']:
        try:
            btn = page.locator(sel).first
            if btn.is_visible(timeout=3000):
                btn.click()
                print(f"  ✓ Clicked '{sel}'")
                page.wait_for_timeout(4000)
                break
        except Exception:
            pass

    # Fill confirm password if present
    for sel in ['input[name="password_confirmation"]', 'input[placeholder*="repeat" i]']:
        try:
            el = page.locator(sel).first
            if el.is_visible(timeout=2000):
                el.fill(PASSWORD)
                print("  ✓ Confirm password")
                break
        except Exception:
            pass

    # Accept terms checkboxes
    try:
        for label_text in ['agree to the', 'accept the', 'terms of use',
                          'privacy policy', 'partner agreement']:
            label = page.locator(f'label:has-text("{label_text}")')
            if label.count() > 0:
                cb_id = label.first.get_attribute('for') or ''
                if cb_id:
                    cb = page.locator(f'#{cb_id}')
                    if cb.count() > 0 and not cb.first.is_checked():
                        label.first.click()
                        print(f"  ✓ Accepted: {label_text}")
                        page.wait_for_timeout(200)
                else:
                    label.first.click()
                    print(f"  ✓ Clicked: {label_text}")
                    page.wait_for_timeout(200)
    except Exception as e:
        print(f"  ⚠️  Terms: {e}")

    # CAPTCHA handling
    captcha_handled = False
    for sel in ['button:has-text("Verifying")', 'iframe[src*="turnstile"]',
                'iframe[src*="recaptcha"]', 'iframe[src*="hcaptcha"]']:
        try:
            if page.locator(sel).first.is_visible(timeout=3000):
                print(f"  [captcha] Found: {sel}")
                if headed:
                    print("  ⏸️  Please solve CAPTCHA in browser window (120s timeout)")
                    deadline = time.time() + 120
                    while time.time() < deadline:
                        time.sleep(3)
                        try:
                            if not page.locator(sel).first.is_visible():
                                print("  [captcha] ✅ Solved!")
                                captcha_handled = True
                                break
                        except Exception:
                            captcha_handled = True
                            break
                else:
                    page.locator(sel).first.click()
                    page.wait_for_timeout(4000)
                    captcha_handled = True
                break
        except Exception:
            pass
    if not captcha_handled:
        print("  [captcha] No CAPTCHA detected on form")

    # Final submit
    for sel in ['button:has-text("Sign up")', 'button:has-text("Create account")',
                'button[type="submit"]']:
        try:
            btn = page.locator(sel).first
            if btn.is_visible(timeout=3000):
                btn.click()
                print(f"  ✓ Submit: {sel}")
                page.wait_for_timeout(8000)
                break
        except Exception:
            pass

    print(f"  After signup: {page.url[:100]}")

    # Handle verification
    handle_verification(page, signup_start)

    # Save auth
    try:
        page.context.storage_state(path=str(AFF_AUTH_FILE))
        AFF_AUTH_FILE.chmod(0o600)
        print("  💾 Affiliate auth saved")
    except Exception:
        pass

    # Check if we're on a dashboard
    url = page.url.lower()
    is_dashboard = any(ind in url for ind in
                       ["/affiliate/dashboard", "/dashboard", "/affiliate/statistics"])
    if is_dashboard or ("affiliate" in url and "signup" not in url and "login" not in url):
        print("  ✅ Affiliate account ready!")
        return True

    # Try logging in if signup redirected to login
    if "/affiliate" in url:
        print("  → Trying affiliate login...")
        try:
            for tab_text in ["i have an account", "log in", "sign in"]:
                try:
                    tab = page.locator(f'button:has-text("{tab_text}")').first
                    if tab.is_visible(timeout=3000):
                        tab.click()
                        page.wait_for_timeout(3000)
                        break
                except Exception:
                    pass
            page.locator('input[name="email"]').fill(EMAIL)
            page.locator('input[name="password"]').fill(PASSWORD)
            page.locator('button:has-text("Log in")').first.click(timeout=5000)
            page.wait_for_timeout(10000)
            print(f"  After login: {page.url[:100]}")

            handle_verification(page, signup_start)
            try:
                page.context.storage_state(path=str(AFF_AUTH_FILE))
                AFF_AUTH_FILE.chmod(0o600)
            except Exception:
                pass
            url = page.url.lower()
            if any(ind in url for ind in ["/affiliate/dashboard", "/dashboard"]):
                return True
        except Exception as e:
            print(f"  ⚠️  Affiliate login error: {e}")

    return False


# ============================================================================
# MAIN
# ============================================================================
def grab_changenow(headed: bool = False, fresh: bool = False, cooldown: bool = False):
    """Main grab flow for ChangeNOW."""
    print(f"\n{'='*60}")
    print(f"  🔑 ChangeNOW API Key Grab")
    print(f"  Email: {EMAIL}")
    flags = ["HEADED" if headed else "HEADLESS"]
    if fresh:
        flags.append("FRESH")
    if cooldown:
        flags.append(f"COOLDOWN ({COOLDOWN_SECONDS}s)")
    print(f"  Mode: {' + '.join(flags)}")
    print(f"{'='*60}\n")

    if cooldown:
        print(f"  ⏳ Cooling down {COOLDOWN_SECONDS}s for rate limits...")
        for i in range(COOLDOWN_SECONDS, 0, -10):
            print(f"     {i}s remaining...")
            time.sleep(10)
        print("  ✓ Cooldown complete")

    with sync_playwright() as p:
        launch_args = ["--no-sandbox", "--disable-blink-features=AutomationControlled"]
        if not headed:
            launch_args.append("--disable-setuid-sandbox")

        browser = p.chromium.launch(headless=not headed, args=launch_args)

        # Load cached auth if available
        storage_state = None
        if not fresh and AUTH_FILE.exists():
            try:
                storage_state = str(AUTH_FILE)
                print("  📂 Loading cached auth state...")
            except Exception:
                pass

        context = browser.new_context(
            viewport={"width": 1440, "height": 900},
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36",
            locale="en-US",
            timezone_id="Asia/Dubai",
            storage_state=storage_state,
        )
        page = context.new_page()
        page.add_init_script("Object.defineProperty(navigator, 'webdriver', { get: () => false });")
        page.set_default_timeout(30000)

        try:
            # Check cached auth
            logged_in = False
            if storage_state:
                print("  → Checking cached auth...")
                try:
                    page.goto("https://changenow.io/pro/balance",
                              wait_until="domcontentloaded", timeout=15000)
                    page.wait_for_timeout(5000)
                    body = page.inner_text("body").lower()
                    if "/pro/balance" in page.url.lower() and "assets" in body:
                        print("  ✅ Cached auth valid")
                        logged_in = True
                    else:
                        print(f"  ⚠️  Auth expired ({page.url[:80]})")
                except Exception:
                    print("  ⚠️  Auth check failed")

            # Phase 1: Login if needed
            if not logged_in:
                logged_in = login_changenow(page, headed=headed)

            if not logged_in:
                print("\n  ❌ Login unsuccessful")
                if headed:
                    input("  Press Enter to close...")
                return {}

            # Save auth
            try:
                context.storage_state(path=str(AUTH_FILE))
                AUTH_FILE.chmod(0o600)
                print("  💾 Auth saved")
            except Exception:
                pass

            # Phase 2: Navigate to API keys
            try_navigate_to_keys(page)

            # Phase 3: Extract keys
            print("\n  🔍 Extracting keys...")
            keys = extract_keys_from_page(page)

            if keys and len(keys) >= 1:
                print("  ✅ Found keys (PRO account):")
                for k, v in keys.items():
                    print(f"     {k}: {mask(v)}")
                return save_keys_result(keys)

            # Phase 4: Try affiliate signup
            print("  ℹ️  No keys found via PRO — trying affiliate signup...")
            aff_success = signup_affiliate(page, headed=headed)

            if aff_success:
                try_navigate_to_keys(page)
                print("\n  🔍 Extracting keys from affiliate...")
                keys = extract_keys_from_page(page)
                if keys and len(keys) >= 1:
                    print("  ✅ Found keys (affiliate):")
                    for k, v in keys.items():
                        print(f"     {k}: {mask(v)}")
                    return save_keys_result(keys)

            # Debug: print body snippets
            print("\n  ⚠️  No API keys found")
            try:
                text = page.inner_text("body")
                for line in text.split("\n"):
                    line = line.strip()
                    if line and any(kw in line.lower() for kw in
                                   ["api key", "api_key", "secret", "token", "affiliate id"]):
                        print(f"  🔑 {line[:120]}")
            except Exception:
                pass

            return {}

        except Exception as e:
            import traceback
            print(f"  ❌ Error: {type(e).__name__}: {e}")
            traceback.print_exc()
            return {}
        finally:
            context.close()
            browser.close()


if __name__ == "__main__":
    headed = "--headed" in sys.argv
    fresh = "--fresh" in sys.argv
    cooldown = "--cooldown" in sys.argv
    result = grab_changenow(headed=headed, fresh=fresh, cooldown=cooldown)

    print(f"\n{'='*60}")
    if result:
        print("  ✅ ChangeNOW keys saved to .env")
        print(f"  Verify: cd payment-gateway && python3 gateway_agents_activate.py --verify")
    else:
        print("  ⚠️  No keys obtained — suggestions:")
        if not headed:
            print("     - Try with --headed for manual CAPTCHA solving")
        print("     - Try with --cooldown if rate limited")
        print("     - Try with --fresh to force re-login")
    print(f"{'='*60}")

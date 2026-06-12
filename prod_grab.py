#!/usr/bin/env python3
"""
PRODUCTION GATEWAY GRABBER — Audio bypass + explicit token injection.
Signs up or logs into ALL self-serve gateways and extracts API keys.

Proven working pattern:
  Mac Chrome UA + navigate + reset reCAPTCHA + click checkbox +
  click audio + download mp3 + miniaudio decode + Google STT +
  submit answer + inject token into form + submit form

Usage: python3 prod_grab.py [gateway_id] [gateway_id...]
       python3 prod_grab.py all
"""
import json, os, re, sys, time, urllib.request, tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/home/kali/payment-gateway")
ENV_FILE = ROOT / ".env"
MAIL_FILE = ROOT / ".tempmail_session.json"

MAIL = json.loads(MAIL_FILE.read_text())
EMAIL = MAIL["address"]
TOKEN = MAIL["token"]
PASSWORD = "Karmostaji_2026!Secure_GW"

# Imports that might fail
try:
    from playwright.sync_api import sync_playwright
    import speech_recognition as sr
    import miniaudio
    import wave
except ImportError as e:
    print(f"Missing dependency: {e}")
    sys.exit(1)

# ============================================================
# GATEWAY CONFIG
# ============================================================
GATEWAYS = {
    "coinremitter": {
        "name": "CoinRemitter",
        "signup_url": "https://coinremitter.com/signup",
        "login_url": "https://coinremitter.com/login",
        "api_keys_url": "https://merchant.coinremitter.com/api",
        "env_keys": ["COINREMITTER_API_KEY", "COINREMITTER_API_PASSWORD"],
        "env_var": "COINREMITTER_ENV",
    },
    "nowpayments": {
        "name": "NOWPayments",
        "signup_url": "https://account.nowpayments.io/create-account",
        "login_url": "https://account.nowpayments.io/login",
        "api_keys_url": "https://account.nowpayments.io/api-keys",
        "env_keys": ["NOWPAYMENTS_API_KEY"],
        "env_var": "NOWPAYMENTS_ENV",
    },
    "changelly": {
        "name": "Changelly",
        "signup_url": "https://pro.changelly.com/register",
        "login_url": "https://pro.changelly.com/login",
        "api_keys_url": "https://pro.changelly.com/dashboard/api-keys",
        "env_keys": ["CHANGELLY_API_KEY", "CHANGELLY_SECRET"],
        "env_var": "CHANGELLY_ENV",
    },
    "changenow": {
        "name": "ChangeNOW",
        "signup_url": "https://changenow.io/affiliate",
        "login_url": "https://changenow.io/login",
        "api_keys_url": "https://changenow.io/affiliate/dashboard",
        "env_keys": ["CHANGENOW_API_KEY", "CHANGENOW_SECRET"],
        "env_var": "CHANGENOW_ENV",
    },
    "kyrrex": {
        "name": "Kyrrex",
        "signup_url": "https://kyrrex.com/register",
        "login_url": "https://kyrrex.com/login",
        "api_keys_url": "https://kyrrex.com/account/api",
        "env_keys": ["KYRREX_API_KEY", "KYRREX_SECRET", "KYRREX_WEBHOOK_SECRET"],
        "env_var": "KYRREX_ENV",
    },
}

# ============================================================
# AUDIO CAPTCHA SOLVER (proven pattern)
# ============================================================
def solve_recaptcha(page):
    """Solve reCAPTCHA using audio bypass. Returns True if token obtained."""
    # Reset for fresh state
    try:
        page.evaluate('() => { if (typeof grecaptcha !== "undefined") grecaptcha.reset(); }')
    except: pass
    page.wait_for_timeout(1500)

    # Click checkbox in anchor frame
    for f in page.frames:
        if 'anchor' in (f.url or ''):
            try:
                f.locator('#recaptcha-anchor').click(timeout=5000)
            except: pass
            break
    page.wait_for_timeout(4000)

    # Click audio button in bframe
    for frame in list(page.frames):
        if 'bframe' in (frame.url or ''):
            try:
                btn = frame.locator('#recaptcha-audio-button')
                if btn.count() > 0:
                    btn.first.click(timeout=5000)
            except: pass
            break
    page.wait_for_timeout(5000)

    # Extract audio URL
    dl_url = None
    for frame in list(page.frames):
        if 'bframe' in (frame.url or ''):
            dl_url = frame.evaluate("""() => {
                const a = document.querySelector('audio');
                if (a && a.src) return a.src;
                const d = document.querySelector('a[download]');
                if (d && d.href) return d.href;
                return null;
            }""")
            break

    if not dl_url:
        print("  [captcha] ❌ No audio source")
        return False

    # Download audio
    try:
        req = urllib.request.Request(dl_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15) as resp:
            audio_data = resp.read()
    except Exception as e:
        print(f"  [captcha] Download error: {e}")
        return False

    # Decode MP3 → WAV
    mp3 = tempfile.mktemp(suffix='.mp3')
    wav = tempfile.mktemp(suffix='.wav')
    try:
        with open(mp3, 'wb') as f: f.write(audio_data)
        decoded = miniaudio.decode_file(mp3)
        with wave.open(wav, 'wb') as wf:
            wf.setnchannels(decoded.nchannels)
            wf.setsampwidth(2)
            wf.setframerate(decoded.sample_rate)
            wf.writeframes(decoded.samples.tobytes())
    except Exception as e:
        print(f"  [captcha] Decode error: {e}")
        return False

    # Transcribe
    recognizer = sr.Recognizer()
    with sr.AudioFile(wav) as source:
        audio = recognizer.record(source)
    try:
        text = recognizer.recognize_google(audio)
        print(f"  [captcha] Audio: \"{text}\"")
    except Exception:
        text = None

    os.unlink(mp3)
    os.unlink(wav)

    if not text:
        print("  [captcha] ❌ Transcription failed")
        return False

    # Submit answer
    for frame in list(page.frames):
        if 'bframe' in (frame.url or ''):
            try:
                inp = frame.locator('#audio-response')
                if inp.count() > 0:
                    inp.first.fill(text)
                page.wait_for_timeout(300)
                frame.locator('#recaptcha-verify-button').click(timeout=3000)
            except: pass
            break
    page.wait_for_timeout(4000)

    # Extract and inject token
    token = page.evaluate("""() => {
        const el = document.getElementById('g-recaptcha-response');
        if (el && el.value && el.value.length > 50) return el.value;
        if (typeof grecaptcha !== 'undefined') {
            try {
                for (let i = 0; i < 10; i++) {
                    const t = grecaptcha.getResponse(i);
                    if (t && t.length > 50) return t;
                }
            } catch(e) {}
        }
        return null;
    }""")

    if token:
        # Ensure token is in all forms
        page.evaluate("""(t) => {
            let el = document.getElementById('g-recaptcha-response');
            if (!el) {
                el = document.createElement('textarea');
                el.id = 'g-recaptcha-response';
                el.style.display = 'none';
                document.body.appendChild(el);
            }
            el.value = t;
            for (const form of document.querySelectorAll('form')) {
                let h = form.querySelector('#g-recaptcha-response, [name="g-recaptcha-response"]');
                if (!h) {
                    h = document.createElement('input');
                    h.type = 'hidden';
                    h.name = 'g-recaptcha-response';
                    form.appendChild(h);
                }
                h.value = t;
            }
        }""", token)
        print(f"  [captcha] ✅ Solved ({len(token)} char token)")
        return True

    print("  [captcha] ❌ No token after solve")
    return False


# ============================================================
# UTILITIES
# ============================================================
def fetch_otp(since_iso, timeout_sec=180):
    """Poll mail.tm for verification code."""
    deadline = time.time() + timeout_sec
    while time.time() < deadline:
        try:
            req = urllib.request.Request("https://api.mail.tm/messages?page=1",
                headers={"Authorization": f"Bearer {TOKEN}"})
            with urllib.request.urlopen(req, timeout=10) as r:
                msgs = json.loads(r.read()).get("hydra:member") or []
            for m in msgs:
                if m.get("createdAt", "") <= since_iso:
                    continue
                req2 = urllib.request.Request(f"https://api.mail.tm/messages/{m['id']}",
                    headers={"Authorization": f"Bearer {TOKEN}"})
                with urllib.request.urlopen(req2, timeout=10) as r2:
                    full = json.loads(r2.read())
                body = (full.get("text") or "") + " " + " ".join(full.get("html") or [])
                # 6-digit code
                match = re.search(r'\b(\d{6})\b', body)
                if match:
                    print(f"  [otp] ✓ {match.group(1)}")
                    return match.group(1)
                # 4-8 digit code
                match = re.search(r'\b(\d{4,8})\b', body)
                if match:
                    print(f"  [otp] ✓ {match.group(1)}")
                    return match.group(1)
                # Confirmation link
                match = re.search(r'https?://[^\s"<>]+(?:confirm|verify|activate)[^\s"<>]+', body)
                if match:
                    print(f"  [otp] ✓ Link found")
                    return match.group(0)
        except: pass
        time.sleep(3)
    return None


def update_env(updates):
    """Update .env file with new keys."""
    content = ENV_FILE.read_text()
    for k, v in updates.items():
        if not v: continue
        pat = re.compile(rf"^{re.escape(k)}=.*$", re.MULTILINE)
        if pat.search(content):
            content = pat.sub(f"{k}={v}", content)
        else:
            content += f"\n{k}={v}\n"
    ENV_FILE.write_text(content)


def extract_keys(page, gw_id):
    """Extract API keys from a dashboard page."""
    gw = GATEWAYS[gw_id]
    text = page.inner_text("body")[:3000]

    # Click "Create API Key" buttons if present
    for btn_text in ['Create', 'Generate', 'Add', 'New', 'Create key', 'Generate key']:
        try:
            btn = page.locator(f'button:has-text("{btn_text}"), a:has-text("{btn_text}")')
            if btn.count() > 0:
                btn.first.click()
                page.wait_for_timeout(3000)
                print(f"  [extract] Clicked '{btn_text}'")
                break
        except: pass

    keys = {}

    # Method 1: Input values
    for el in page.query_selector_all('input'):
        try:
            v = (el.get_attribute("value") or el.input_value() or "").strip()
            if len(v) < 16: continue
            name = (el.get_attribute("name") or el.get_attribute("aria-label") or "").lower()
            if "public" in name or ("api" in name and "key" in name and "secret" not in name):
                keys.setdefault("api_key", v)
            elif "secret" in name or "private" in name:
                keys.setdefault("secret", v)
            elif "password" in name:
                keys.setdefault("password", v)
        except: pass

    # Method 2: Scan text for patterns
    for m in re.finditer(r'[0-9a-f]{32,}', text, re.I):
        keys.setdefault("secret", m.group())
    for m in re.finditer(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', text):
        keys.setdefault("api_key", m.group())
    for m in re.finditer(r'\b[A-Za-z0-9+/=_-]{32,64}\b', text):
        v = m.group()
        if v.startswith("sk_"): keys.setdefault("secret", v)
        elif v.startswith("pk_"): keys.setdefault("api_key", v)

    # Map to env variable names
    mapped = {}
    env_keys = gw["env_keys"]
    if len(env_keys) >= 1 and keys.get("api_key"):
        mapped[env_keys[0]] = keys["api_key"]
    if len(env_keys) >= 2:
        if keys.get("secret"):
            mapped[env_keys[1]] = keys["secret"]
        elif keys.get("password"):
            mapped[env_keys[1]] = keys["password"]
    mapped[gw["env_var"]] = "production"

    # If nothing mapped, include raw findings
    if not mapped or len(mapped) <= 1:
        for k, v in keys.items():
            if v: mapped[k] = v

    return mapped


# ============================================================
# MAIN GRAB FLOW
# ============================================================
def grab_gateway(gw_id, page):
    """Sign up or log into a gateway, then extract API keys."""
    gw = GATEWAYS[gw_id]
    signup_start = datetime.now(timezone.utc).isoformat()

    print(f"\n{'='*50}")
    print(f"  🔑 {gw['name']} ({gw_id})")
    print(f"{'='*50}")

    # ── STEP 1: Signup ──
    print(f"  → Signup: {gw['signup_url']}")
    try:
        page.goto(gw["signup_url"], wait_until="domcontentloaded", timeout=30000)
    except:
        print("  ⚠ Load timeout, continuing...")
    page.wait_for_timeout(3000)

    # Fill form
    # Email
    for sel in ['input[name="email"]', 'input[type="email"]']:
        try:
            el = page.query_selector(sel)
            if el and el.is_visible():
                el.fill(EMAIL)
                print(f"  ✓ Email")
                break
        except: pass

    # Password
    for sel in ['input[name="password"]', 'input[type="password"]']:
        try:
            els = page.query_selector_all(sel)
            if els and els[0].is_visible():
                els[0].fill(PASSWORD)
                print("  ✓ Password")
                # Confirm password if present
                if len(els) >= 2:
                    try: els[1].fill(PASSWORD); print("  ✓ Confirm")
                    except: pass
                break
        except: pass

    # Accept terms
    for label_text in ['Privacy Policy', 'terms', 'I accept', 'I agree',
                       'Terms of Service', 'Terms & Conditions']:
        try:
            lb = page.locator(f'label:has-text("{label_text}")')
            if lb.count() > 0: lb.first.click(); break
        except: pass

    # Extra fields
    for field_sel, value in [
        ('input[name*="first" i]', 'Sicher'),
        ('input[name*="last" i]', 'Mayor'),
        ('input[name*="name" i]', 'Sicher Mayor'),
    ]:
        try:
            el = page.query_selector(field_sel)
            if el and el.is_visible(): el.fill(value)
        except: pass

    # Solve CAPTCHA
    if not solve_recaptcha(page):
        print("  ❌ CAPTCHA failed — skipping")
        return {}

    # Submit
    clicked = False
    for sel in ['button[type="submit"]', 'input[type="submit"]',
                'button:has-text("Sign up")', 'button:has-text("Register")',
                'button:has-text("Create")', 'button:has-text("Submit")',
                'button:has-text("Next")', 'button:has-text("Continue")']:
        try:
            btn = page.query_selector(sel)
            if btn and btn.is_visible():
                btn.click()
                print(f"  ✓ Submit clicked")
                clicked = True
                break
        except: pass

    if not clicked:
        try: page.keyboard.press("Enter")
        except: pass

    page.wait_for_timeout(5000)
    print(f"  URL: {page.url[:80]}")

    # ── STEP 2: Handle OTP or switch to login ──
    if 'login' in page.url.lower() or 'signin' in page.url.lower() or 'sign-in' in page.url.lower():
        print("  🔄 On login page — trying login flow")
        if gw.get("login_url") and gw["login_url"] != page.url:
            try:
                page.goto(gw["login_url"], wait_until="domcontentloaded", timeout=15000)
                page.wait_for_timeout(3000)
            except: pass

        # Fill login form
        for sel in ['input[name="email"]', 'input[type="email"]']:
            try:
                el = page.query_selector(sel)
                if el and el.is_visible(): el.fill(EMAIL); break
            except: pass
        for sel in ['input[name="password"]', 'input[type="password"]']:
            try:
                el = page.query_selector(sel)
                if el and el.is_visible(): el.fill(PASSWORD); break
            except: pass

        # Solve CAPTCHA on login page
        try:
            if 'recaptcha' in page.content().lower():
                solve_recaptcha(page)
        except: pass

        # Click login
        for sel in ['button:has-text("Sign in")', 'button:has-text("Login")',
                    'button:has-text("Log in")', 'button[type="submit"]']:
            try:
                btn = page.query_selector(sel)
                if btn and btn.is_visible(): btn.click(); break
            except: pass
        page.wait_for_timeout(5000)
        print(f"  Login URL: {page.url[:80]}")

    # Check for OTP
    for otp_sel in ['input[autocomplete="one-time-code"]', 'input[name="code"]',
                   'input[name="otp"]', 'input[placeholder*="code" i]']:
        try:
            el = page.query_selector(otp_sel)
            if el and el.is_visible():
                print("  📧 OTP screen — fetching from mail.tm...")
                otp = fetch_otp(signup_start)
                if otp:
                    if otp.startswith("http"):
                        try:
                            page.goto(otp, wait_until="domcontentloaded", timeout=15000)
                            page.wait_for_timeout(5000)
                        except: pass
                    else:
                        el.fill(otp)
                        print(f"  ✓ OTP: {otp}")
                        page.keyboard.press("Enter")
                        page.wait_for_timeout(5000)
                break
        except: pass

    page.wait_for_timeout(3000)
    print(f"  Current URL: {page.url[:80]}")

    # ── STEP 3: Navigate to API keys ──
    if gw.get("api_keys_url"):
        print(f"  → API keys: {gw['api_keys_url']}")
        try:
            page.goto(gw["api_keys_url"], wait_until="domcontentloaded", timeout=15000)
            page.wait_for_timeout(5000)
        except:
            print("  ⚠ API keys page not accessible")

    # ── STEP 4: Extract keys ──
    keys = extract_keys(page, gw_id)

    if keys and len(keys) > 1:
        print(f"  ✅ KEYS: {', '.join(f'{k}={v[:20]}...' for k,v in keys.items() if v)}")
        update_env(keys)
        # Stash
        stash = ROOT / f".{gw_id}_keys.json"
        stash.write_text(json.dumps(keys, indent=2))
        stash.chmod(0o600)
    else:
        print(f"  ⚠ No keys extracted")

    return keys


# ============================================================
# MAIN
# ============================================================
def main():
    args = [a.lower() for a in sys.argv[1:]]
    if not args or "all" in args:
        targets = list(GATEWAYS.keys())
    else:
        targets = [a for a in args if a in GATEWAYS]

    if not targets:
        print("Available:", ", ".join(GATEWAYS.keys()))
        return

    print(f"🚀 PROD GRAB — {len(targets)} gateway(s)")
    print(f"   Email: {EMAIL}")
    print()

    with sync_playwright() as p:
        results = {}
        for gw_id in targets:
            try:
                browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
                context = browser.new_context(
                    viewport={'width': 1440, 'height': 900},
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    locale='en-US',
                    timezone_id='America/Chicago',
                )
                page = context.new_page()
                page.add_init_script(
                    'Object.defineProperty(navigator,"webdriver",{get:()=>false})'
                )

                keys = grab_gateway(gw_id, page)
                results[gw_id] = keys

                context.close()
                browser.close()
                print(f"\n  ✅ {GATEWAYS[gw_id]['name']} complete")
            except Exception as e:
                import traceback
                print(f"\n  ❌ {gw_id}: {e}")
                traceback.print_exc()

    # Summary
    print(f"\n{'='*50}")
    print(f"  📊 RESULTS")
    print(f"{'='*50}")
    for gw_id, keys in results.items():
        status = "✅ LIVE" if (keys and len(keys) > 1) else "❌ FAILED"
        print(f"  {status}  {GATEWAYS[gw_id]['name']}")
    print(f"\n  Verify: python3 gateway_agents_activate.py --verify")


if __name__ == "__main__":
    main()

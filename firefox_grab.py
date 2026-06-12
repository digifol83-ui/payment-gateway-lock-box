#!/usr/bin/env python3
"""
Firefox-based gateway key grab — better reCAPTCHA stealth than Chromium.
Uses Firefox Playwright + audio CAPTCHA bypass.

Usage: python3 firefox_grab.py coinremitter
       python3 firefox_grab.py all
"""
import json, os, re, sys, time, urllib.request, tempfile, base64
from datetime import datetime, timezone
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path("/home/kali/payment-gateway")
ENV_FILE = ROOT / ".env"
MAIL_SESSION_FILE = ROOT / ".tempmail_session.json"

MAIL = json.loads(MAIL_SESSION_FILE.read_text())
EMAIL = MAIL["address"]
TOKEN = MAIL["token"]
PASSWORD = "Karmostaji_2026!Secure_GW"

GATEWAYS = {
    "coinremitter": {
        "name": "CoinRemitter",
        "signup_url": "https://coinremitter.com/signup",
        "login_url": "https://coinremitter.com/login",
        "api_keys_url": "https://coinremitter.com/dashboard/api-key",
        "email_field": 'input[name="email"], input[type="email"]',
        "password_field": 'input[name="password"], input[type="password"]',
        "confirm_password_field": 'input[name="password_confirmation"]',
        "submit_button": 'button[type="submit"], button:has-text("Sign up")',
        "env_keys": ["COINREMITTER_API_KEY", "COINREMITTER_API_PASSWORD"],
        "env_var": "COINREMITTER_ENV",
    },
    "nowpayments": {
        "name": "NOWPayments",
        "signup_url": "https://account.nowpayments.io/create-account",
        "login_url": "https://account.nowpayments.io/login",
        "api_keys_url": "https://account.nowpayments.io/api-keys",
        "email_field": 'input[name="email"]',
        "password_field": 'input[name="password"]',
        "confirm_password_field": 'input[name="passwordConfirm"]',
        "submit_button": 'button:has-text("Next step")',
        "env_keys": ["NOWPAYMENTS_API_KEY"],
        "env_var": "NOWPAYMENTS_ENV",
    },
    "changelly": {
        "name": "Changelly",
        "signup_url": "https://pro.changelly.com/register",
        "login_url": "https://pro.changelly.com/login",
        "api_keys_url": "https://pro.changelly.com/dashboard/api-keys",
        "email_field": 'input[type="email"]',
        "password_field": 'input[type="password"]',
        "confirm_password_field": None,
        "submit_button": 'button:has-text("Sign up"), button:has-text("Register")',
        "env_keys": ["CHANGELLY_API_KEY", "CHANGELLY_SECRET"],
        "env_var": "CHANGELLY_ENV",
    },
    "changenow": {
        "name": "ChangeNOW",
        "signup_url": "https://changenow.io/affiliate",
        "login_url": "https://changenow.io/login",
        "api_keys_url": "https://changenow.io/affiliate/dashboard",
        "email_field": 'input[type="email"]',
        "password_field": 'input[type="password"]',
        "confirm_password_field": None,
        "submit_button": 'button:has-text("Sign up"), button:has-text("Register")',
        "env_keys": ["CHANGENOW_API_KEY", "CHANGENOW_SECRET"],
        "env_var": "CHANGENOW_ENV",
    },
    "kyrrex": {
        "name": "Kyrrex",
        "signup_url": "https://kyrrex.com/register",
        "login_url": "https://kyrrex.com/login",
        "api_keys_url": "https://kyrrex.com/account/api",
        "email_field": 'input[type="email"]',
        "password_field": 'input[type="password"]',
        "confirm_password_field": 'input[name="password_confirmation"]',
        "submit_button": 'button[type="submit"], button:has-text("Register")',
        "env_keys": ["KYRREX_API_KEY", "KYRREX_SECRET", "KYRREX_WEBHOOK_SECRET"],
        "env_var": "KYRREX_ENV",
    },
    "guardarian": {
        "name": "Guardarian",
        "signup_url": "https://guardarian.com/contact-us",
        "login_url": None,
        "api_keys_url": None,
        "email_field": 'input[type="email"]',
        "password_field": 'input[type="password"]',
        "confirm_password_field": None,
        "submit_button": 'button:has-text("Send"), button:has-text("Submit")',
        "env_keys": ["GUARDARIAN_API_KEY", "GUARDARIAN_SECRET"],
        "env_var": "GUARDARIAN_ENV",
    },
}


def fetch_otp(since_iso, timeout=240, subject_filter=None):
    deadline = time.time() + timeout
    print(f"  [otp] Polling mail.tm for OTP...")
    while time.time() < deadline:
        try:
            req = urllib.request.Request("https://api.mail.tm/messages?page=1",
                headers={"Authorization": f"Bearer {TOKEN}"})
            with urllib.request.urlopen(req, timeout=10) as r:
                msgs = json.loads(r.read()).get("hydra:member") or []
            for m in msgs:
                if m.get("createdAt", "") <= since_iso:
                    continue
                subj = (m.get("subject") or "").lower()
                if subject_filter and not any(w in subj for w in subject_filter):
                    continue
                req2 = urllib.request.Request(f"https://api.mail.tm/messages/{m['id']}",
                    headers={"Authorization": f"Bearer {TOKEN}"})
                with urllib.request.urlopen(req2, timeout=10) as r2:
                    full = json.loads(r2.read())
                body = (full.get("text") or "") + " " + " ".join(full.get("html") or [])
                match = re.search(r'\b(\d{6})\b', body)
                if match:
                    print(f"  [otp] ✓ OTP: {match.group(1)}")
                    return match.group(1)
                match = re.search(r'\b(\d{4,8})\b', body)
                if match:
                    print(f"  [otp] ✓ Code: {match.group(1)}")
                    return match.group(1)
                link_match = re.search(r'https?://[^\s"<>]+(?:confirm|verify|activate)[^\s"<>]+', body)
                if link_match:
                    print(f"  [otp] ✓ Link found")
                    return link_match.group(0)
        except Exception:
            pass
        time.sleep(3)
    return None


def solve_recaptcha_audio(page, timeout=120):
    """Solve reCAPTCHA using audio challenge via Firefox."""
    print("  [captcha] reCAPTCHA detected — audio bypass via Firefox...")
    deadline = time.time() + timeout

    # Wait for bframe
    for _ in range(15):
        for f in page.frames:
            if 'bframe' in (f.url or '') or 'api2' in (f.url or ''):
                break
        else:
            page.wait_for_timeout(2000)
            continue
        break

    # Click audio button
    for attempt in range(3):
        for frame in list(page.frames):
            if 'bframe' not in (frame.url or ''):
                continue
            try:
                audio_btn = frame.locator('#recaptcha-audio-button')
                if audio_btn.count() > 0 and audio_btn.first.is_visible():
                    audio_btn.first.click(timeout=5000)
                    print(f"  [captcha] Audio button clicked (attempt {attempt+1})")
                    page.wait_for_timeout(4000)
                    break
            except Exception:
                continue
        else:
            continue
        break

    # Get audio download link or audio element src
    dl_url = None
    for frame in list(page.frames):
        if 'bframe' not in (frame.url or '') and 'api2' not in (frame.url or ''):
            continue
        try:
            # Method 1: download link
            for sel in ['a.rc-audiochallenge-tdownload-link', 'a[download]',
                       'a[href*="audio"]']:
                dl = frame.locator(sel)
                if dl.count() > 0:
                    dl_url = dl.first.get_attribute('href')
                    if dl_url:
                        print(f"  [captcha] Found download link")
                        break
            if dl_url:
                break

            # Method 2: audio/src element
            url = frame.evaluate("""() => {
                const a = document.querySelector('audio');
                if (a && a.src) return a.src;
                const s = document.querySelector('source');
                if (s && s.src) return s.src;
                return null;
            }""")
            if url:
                dl_url = url
                print(f"  [captcha] Found audio/src")
                break
        except Exception:
            continue

    if not dl_url:
        print("  [captcha] ⚠️  No audio source found")
        return False

    # Download and decode
    try:
        req = urllib.request.Request(dl_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15) as resp:
            audio_data = resp.read()
        print(f"  [captcha] Downloaded {len(audio_data)}B audio")
    except Exception as e:
        print(f"  [captcha] Download failed: {e}")
        return False

    # Transcribe
    text = transcribe_audio(audio_data)
    if not text:
        print("  [captcha] ⚠️  Transcription failed")
        return False
    print(f"  [captcha] Transcription: \"{text}\"")

    # Submit answer
    for frame in list(page.frames):
        if 'bframe' not in (frame.url or '') and 'api2' not in (frame.url or ''):
            continue
        try:
            inp = frame.locator('#audio-response')
            if inp.count() > 0 and inp.first.is_visible():
                inp.first.fill(text)
                page.wait_for_timeout(500)
                verify = frame.locator('#recaptcha-verify-button')
                if verify.count() > 0:
                    verify.first.click()
                    print("  [captcha] ✓ Submitted answer")
                    page.wait_for_timeout(3000)
                break
        except Exception as e:
            print(f"  [captcha] Submit error: {e}")

    # Check if solved
    page.wait_for_timeout(2000)
    try:
        resp = page.evaluate("""() => {
            const el = document.getElementById('g-recaptcha-response');
            return el ? el.value : null;
        }""")
        if resp and len(resp) > 50:
            print("  [captcha] ✅ reCAPTCHA solved!")
            return True
    except Exception:
        pass

    for frame in list(page.frames):
        try:
            if frame.locator('.recaptcha-checkbox-checked').count() > 0:
                print("  [captcha] ✅ reCAPTCHA solved (checkbox)!")
                return True
        except Exception:
            pass

    return False


def transcribe_audio(audio_data):
    """Decode audio and transcribe using Google Speech Recognition."""
    import speech_recognition as sr, miniaudio, wave

    mp3_path = tempfile.mktemp(suffix='.mp3')
    wav_path = tempfile.mktemp(suffix='.wav')

    try:
        with open(mp3_path, 'wb') as f:
            f.write(audio_data)

        # Decode MP3 to WAV
        decoded = miniaudio.decode_file(mp3_path)
        with wave.open(wav_path, 'wb') as wf:
            wf.setnchannels(decoded.nchannels)
            wf.setsampwidth(2)
            wf.setframerate(decoded.sample_rate)
            wf.writeframes(decoded.samples.tobytes())

        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_path) as source:
            audio = recognizer.record(source)

        try:
            return recognizer.recognize_google(audio)
        except sr.UnknownValueError:
            try:
                return recognizer.recognize_sphinx(audio)
            except Exception:
                pass
    except Exception as e:
        print(f"  [captcha] Transcribe error: {e}")
    finally:
        for p in [mp3_path, wav_path]:
            try: os.unlink(p)
            except: pass
    return None


def detect_captcha_and_solve(page, timeout=120):
    """Detect CAPTCHA type and solve it."""
    page.wait_for_timeout(2000)
    try:
        body = page.content().lower()
    except Exception:
        body = ""

    if 'recaptcha' in body or 'g-recaptcha' in body:
        print("  [captcha] Detected: reCAPTCHA")
        return solve_recaptcha_audio(page, timeout)

    if 'hcaptcha' in body or 'h-captcha' in body:
        print("  [captcha] Detected: hCaptcha (clicking checkbox)")
        try:
            for frame in page.frames:
                if "hcaptcha" in frame.url:
                    frame.locator('#checkbox').click(timeout=5000)
                    page.wait_for_timeout(3000)
                    return True
        except Exception:
            pass
        return False

    print("  [captcha] No CAPTCHA detected")
    return True


def detect_account_exists(page) -> bool:
    try:
        body = page.content().lower()
        indicators = ['already registered', 'already exists', 'account already',
                     'email already', 'already have an account', 'already in use']
        for ind in indicators:
            if ind in body:
                print(f"  [detect] Account exists: '{ind}'")
                return True
        if '/login' in page.url.lower() or '/signin' in page.url.lower():
            return True
    except Exception:
        pass
    return False


def do_login(page, gw_id, gw):
    login_url = gw.get("login_url")
    if not login_url:
        return False
    print(f"  [login] → {login_url}")
    try:
        page.goto(login_url, wait_until="domcontentloaded", timeout=30000)
    except Exception:
        pass
    page.wait_for_timeout(3000)

    # Fill email
    for sel in [gw["email_field"], 'input[type="email"]', 'input[name="email"]']:
        try:
            el = page.query_selector(sel)
            if el and el.is_visible():
                el.fill(EMAIL)
                print("  [login] ✓ Filled email")
                break
        except Exception:
            pass

    # Fill password
    try:
        els = page.query_selector_all(gw.get("password_field", 'input[type="password"]'))
        if els and els[0].is_visible():
            els[0].fill(PASSWORD)
            print("  [login] ✓ Filled password")
    except Exception:
        pass

    detect_captcha_and_solve(page)

    # Click login
    for sel in ['button:has-text("Log in")', 'button:has-text("Login")',
                'button:has-text("Sign in")', 'button[type="submit"]']:
        try:
            btn = page.query_selector(sel)
            if btn and btn.is_visible():
                btn.click()
                print(f"  [login] ✓ Clicked login")
                break
        except Exception:
            pass

    page.wait_for_timeout(4000)
    return True


def extract_keys_from_page(page, gw_id):
    gw = GATEWAYS[gw_id]
    result = {}

    # Click create/generate buttons
    for btn_text in ['Create', 'Generate', 'Add', 'New', 'Create key', 'Generate key',
                      'Create API', 'New API']:
        try:
            btn = page.locator(f'button:has-text("{btn_text}"), a:has-text("{btn_text}")')
            if btn.count() > 0:
                btn.first.click()
                page.wait_for_timeout(3000)
                print(f"  [extract] Clicked '{btn_text}'")
                break
        except Exception:
            pass

    # Scan inputs
    try:
        for el in page.query_selector_all('input'):
            try:
                v = (el.get_attribute("value") or el.input_value() or "").strip()
                if len(v) < 16:
                    continue
                label = (el.get_attribute("aria-label") or el.get_attribute("placeholder") or
                        el.get_attribute("name") or "").lower()
                if "api" in label and "key" in label and "secret" not in label:
                    result.setdefault("API_KEY", v)
                elif "secret" in label or "private" in label:
                    result.setdefault("SECRET", v)
                elif "password" in label and "api" not in label:
                    result.setdefault("API_PASSWORD", v)
            except Exception:
                pass
    except Exception:
        pass

    # Scan text
    try:
        text = page.inner_text("body")
        # UUID-style keys
        for u in re.findall(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", text):
            result.setdefault("API_KEY", u)
        # Hex keys 32+ chars
        for h in re.findall(r"\b[0-9a-f]{32,}\b", text, re.I):
            result.setdefault("SECRET" if "secret" not in result else "API_PASSWORD", h)
        # sk_ / pk_ keys
        for s in re.findall(r"\b[A-Za-z0-9+/=_-]{32,}\b", text):
            if s.startswith("sk_") and "SECRET" not in result:
                result["SECRET"] = s
            elif s.startswith("pk_") and "API_KEY" not in result:
                result["API_KEY"] = s
    except Exception:
        pass

    # Map to env keys
    mapped = {}
    keys_list = gw["env_keys"]
    if len(keys_list) >= 1 and result.get("API_KEY"):
        mapped[keys_list[0]] = result["API_KEY"]
    if len(keys_list) >= 2:
        if result.get("SECRET"):
            mapped[keys_list[1]] = result["SECRET"]
        elif result.get("API_PASSWORD"):
            mapped[keys_list[1]] = result["API_PASSWORD"]
    mapped[gw["env_var"]] = "production"

    return mapped


def update_env(updates: dict):
    content = ENV_FILE.read_text() if ENV_FILE.exists() else ""
    for k, v in updates.items():
        if not v:
            continue
        pat = re.compile(rf"^{re.escape(k)}=.*$", re.MULTILINE)
        if pat.search(content):
            content = pat.sub(f"{k}={v}", content)
        else:
            # Find the section for this gateway and add after
            section = k.split('_')[0].upper()
            content += f"\n# {section}\n{k}={v}\n"
    ENV_FILE.write_text(content)
    print(f"  [env] Updated {len(updates)} keys")


def grab_gateway(gw_id, page, force_login=False):
    gw = GATEWAYS[gw_id]
    print(f"\n{'='*60}")
    print(f"  🔑 GRABBING: {gw['name']} ({gw_id}) via Firefox")
    print(f"{'='*60}")

    signup_start = datetime.now(timezone.utc).isoformat()

    if force_login and gw.get("login_url"):
        do_login(page, gw_id, gw)
    else:
        # Navigate to signup
        print(f"  → {gw['signup_url']}")
        try:
            page.goto(gw["signup_url"], wait_until="domcontentloaded", timeout=30000)
        except Exception:
            print("  ⚠️  Load timeout, continuing...")
        page.wait_for_timeout(4000)

        # Fill email
        for sel in [gw["email_field"], 'input[type="email"]', 'input[name="email"]']:
            try:
                el = page.query_selector(sel)
                if el and el.is_visible():
                    el.fill(EMAIL)
                    print(f"  ✓ Filled email: {EMAIL}")
                    break
            except Exception:
                pass

        # Fill password
        if gw.get("password_field"):
            try:
                els = page.query_selector_all(gw["password_field"])
                if els and els[0].is_visible():
                    els[0].fill(PASSWORD)
                    print("  ✓ Filled password")
                    if gw.get("confirm_password_field") and len(els) >= 2:
                        try:
                            els[1].fill(PASSWORD)
                            print("  ✓ Filled confirm password")
                        except Exception:
                            pass
            except Exception:
                pass

        # Accept terms
        for label_text in ['accept the Terms', 'I accept', 'I agree',
                          'Terms of Service', 'Privacy Policy', 'terms']:
            try:
                label = page.locator(f'label:has-text("{label_text}")')
                if label.count() > 0:
                    label.first.click()
                    print(f"  ✓ Accepted: {label_text}")
                    page.wait_for_timeout(200)
            except Exception:
                pass

        # Extra fields
        for field_sel, value in [
            ('input[name*="first" i]', 'Sicher'),
            ('input[name*="last" i]', 'Mayor'),
            ('input[name*="name" i]', 'Sicher Mayor'),
        ]:
            try:
                el = page.query_selector(field_sel)
                if el and el.is_visible():
                    el.fill(value)
            except Exception:
                pass

        # CAPTCHA
        detect_captcha_and_solve(page)

        # Submit
        for sel in [gw["submit_button"], 'button[type="submit"]',
                    'button:has-text("Sign up")', 'button:has-text("Register")',
                    'button:has-text("Create")', 'button:has-text("Submit")']:
            try:
                btn = page.query_selector(sel)
                if btn and btn.is_visible():
                    btn.click()
                    print("  ✓ Clicked submit")
                    break
            except Exception:
                pass

        page.wait_for_timeout(3000)

        # Post-submit CAPTCHA
        try:
            if 'recaptcha' in page.content().lower():
                detect_captcha_and_solve(page)
        except Exception:
            pass

        # Check if account exists
        if detect_account_exists(page):
            print("  🔄 Account exists — switching to login")
            if gw.get("login_url"):
                do_login(page, gw_id, gw)

        # Wait for OTP or dashboard
        current_url = page.url.lower()
        dash_indicator = gw.get("dashboard_indicator", "/dashboard")
        if dash_indicator not in current_url:
            print("  ⏳ Waiting for OTP/dashboard...")
            deadline = time.time() + 300
            while time.time() < deadline:
                url = page.url.lower()
                if dash_indicator in url or "account" in url:
                    print(f"  ✓ Dashboard: {url}")
                    break

                # Check for OTP fields
                try:
                    for otp_sel in ['input[autocomplete="one-time-code"]',
                                   'input[name="code"]', 'input[name="otp"]',
                                   'input[placeholder*="code" i]']:
                        otp_el = page.query_selector(otp_sel)
                        if otp_el and otp_el.is_visible():
                            print("  ✓ OTP screen — fetching from mail.tm...")
                            otp = fetch_otp(signup_start, timeout=180,
                                          subject_filter=["verify", "confirm", "code", gw["name"].lower()[:5]])
                            if otp:
                                if otp.startswith("http"):
                                    try:
                                        page.goto(otp, wait_until="domcontentloaded", timeout=15000)
                                        page.wait_for_timeout(5000)
                                    except Exception:
                                        pass
                                else:
                                    otp_el.fill(otp)
                                    print(f"  ✓ OTP filled")
                                    try:
                                        for b_sel in ['button:has-text("Verify")', 'button:has-text("Submit")',
                                                     'button:has-text("Confirm")', 'button[type="submit"]']:
                                            btn = page.query_selector(b_sel)
                                            if btn and btn.is_visible():
                                                btn.click()
                                                break
                                    except Exception:
                                        pass
                            break
                except Exception:
                    pass

                # Check for CAPTCHAs
                try:
                    if 'recaptcha' in page.content().lower():
                        detect_captcha_and_solve(page, timeout=30)
                except Exception:
                    pass

                time.sleep(2)

        page.wait_for_timeout(3000)

    # Navigate to API keys
    if gw.get("api_keys_url"):
        print(f"  → API keys: {gw['api_keys_url']}")
        try:
            page.goto(gw["api_keys_url"], wait_until="domcontentloaded", timeout=15000)
            page.wait_for_timeout(5000)
        except Exception:
            print("  ⚠️  API keys page not accessible")

    # Extract keys
    print("  🔍 Extracting keys...")
    keys = extract_keys_from_page(page, gw_id)

    if keys and len(keys) > 1:
        print("  ✅ Found keys:")
        for k, v in keys.items():
            masked = f"{v[:6]}...{v[-4:]}" if len(str(v)) > 10 else v
            print(f"     {k} = {masked}")
        update_env(keys)
    else:
        print(f"  ⚠️  Could not auto-extract keys")
        print(f"  Manual: python3 gateway_agents_activate.py --activate {gw_id}")

    return keys


def main():
    args = [a.lower() for a in sys.argv[1:]]
    if not args or "all" in args:
        targets = list(GATEWAYS.keys())
    else:
        targets = [a for a in args if a in GATEWAYS]
    if not targets:
        print("Available:", ", ".join(GATEWAYS.keys()))
        return

    print(f"\n🦊 FIREFOX GRAB — {len(targets)} gateway(s)")
    print(f"   Email: {EMAIL}")
    print(f"   Headless: Firefox")
    print()

    with sync_playwright() as p:
        results = {}
        for gw_id in targets:
            try:
                browser = p.firefox.launch(headless=True)
                context = browser.new_context(
                    viewport={"width": 1440, "height": 900},
                    user_agent="Mozilla/5.0 (X11; Linux x86_64; rv:125.0) Gecko/20100101 Firefox/125.0",
                    locale="en-US",
                    timezone_id="Asia/Dubai",
                )
                page = context.new_page()

                keys = grab_gateway(gw_id, page)
                results[gw_id] = keys
                context.close()
                browser.close()
                print(f"\n  ✅ {GATEWAYS[gw_id]['name']} complete\n")
            except Exception as e:
                import traceback
                print(f"  ❌ {gw_id} failed: {e}")
                traceback.print_exc()

    print(f"\n{'='*60}")
    print(f"  📊 SUMMARY")
    print(f"{'='*60}")
    for gw_id, keys in results.items():
        status = "✅ LIVE" if (keys and len(keys) > 1) else "❌ FAILED"
        print(f"  {status}  {GATEWAYS[gw_id]['name']}")
    print(f"\n  Verify: python3 gateway_agents_activate.py --verify")


if __name__ == "__main__":
    main()

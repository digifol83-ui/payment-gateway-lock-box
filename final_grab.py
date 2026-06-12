#!/usr/bin/env python3
"""
FINAL GRAB — Firefox headless + audio bypass + explicit token injection.
Hits ALL empty gateways. Firefox stealth > Chromium for reCAPTCHA.
"""
import json, os, re, sys, time, urllib.request, tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/home/kali/payment-gateway")
ENV_FILE = ROOT / ".env"
MAIL = json.loads((ROOT / ".tempmail_session.json").read_text())
EMAIL = MAIL["address"]
TOKEN = MAIL["token"]
PASSWORD = "Karmostaji_2026!Secure_GW"

from playwright.sync_api import sync_playwright
import speech_recognition as sr
import miniaudio, wave

GATEWAYS = {
    "coinremitter": {
        "name": "CoinRemitter",
        "signup": "https://coinremitter.com/signup",
        "login": "https://coinremitter.com/login",
        "apikeys": "https://merchant.coinremitter.com/wallets",
        "env_keys": ["COINREMITTER_API_KEY", "COINREMITTER_API_PASSWORD"],
        "env": "COINREMITTER_ENV",
    },
    "nowpayments": {
        "name": "NOWPayments",
        "signup": "https://account.nowpayments.io/create-account",
        "login": "https://account.nowpayments.io/login", 
        "apikeys": "https://account.nowpayments.io/api-keys",
        "env_keys": ["NOWPAYMENTS_API_KEY"],
        "env": "NOWPAYMENTS_ENV",
    },
    "kyrrex": {
        "name": "Kyrrex",
        "signup": "https://kyrrex.com/register",
        "login": "https://kyrrex.com/login",
        "apikeys": "https://kyrrex.com/account/api",
        "env_keys": ["KYRREX_API_KEY", "KYRREX_SECRET"],
        "env": "KYRREX_ENV",
    },
}


def update_env(updates):
    c = ENV_FILE.read_text()
    for k, v in updates.items():
        if not v: continue
        p = re.compile(rf"^{re.escape(k)}=.*$", re.MULTILINE)
        c = p.sub(f"{k}={v}", c) if p.search(c) else c + f"\n{k}={v}\n"
    ENV_FILE.write_text(c)


def fetch_otp(since, timeout=180):
    dl = time.time() + timeout
    while time.time() < dl:
        try:
            req = urllib.request.Request("https://api.mail.tm/messages?page=1",
                headers={"Authorization": f"Bearer {TOKEN}"})
            with urllib.request.urlopen(req, timeout=10) as r:
                msgs = json.loads(r.read()).get("hydra:member") or []
            for m in msgs:
                if m.get("createdAt","") <= since: continue
                req2 = urllib.request.Request(f"https://api.mail.tm/messages/{m['id']}",
                    headers={"Authorization": f"Bearer {TOKEN}"})
                with urllib.request.urlopen(req2, timeout=10) as r2:
                    full = json.loads(r2.read())
                body = (full.get("text") or "") + " " + " ".join(full.get("html") or [])
                m6 = re.search(r'\b(\d{6})\b', body)
                if m6: return m6.group(1)
                m4 = re.search(r'\b(\d{4,8})\b', body)
                if m4: return m4.group(1)
                link = re.search(r'https?://[^\s"<>]+(?:confirm|verify|activate)[^\s"<>]+', body)
                if link: return link.group(0)
        except: pass
        time.sleep(3)
    return None


def solve_captcha(page):
    """Firefox audio bypass — proven more stealthy than Chromium."""
    try:
        page.evaluate('() => { if (typeof grecaptcha !== "undefined") grecaptcha.reset(); }')
    except: pass
    page.wait_for_timeout(1000)

    # Click the reCAPTCHA checkbox
    for f in page.frames:
        if 'anchor' in (f.url or ''):
            try:
                f.locator('#recaptcha-anchor').click(timeout=5000)
            except: pass
            break
    page.wait_for_timeout(4000)

    # Click audio button
    for frame in list(page.frames):
        if 'bframe' in (frame.url or ''):
            try:
                btn = frame.locator('#recaptcha-audio-button')
                if btn.count() > 0:
                    btn.first.click(timeout=5000)
            except: pass
            break
    page.wait_for_timeout(5000)

    # Get audio URL
    dl_url = None
    for frame in list(page.frames):
        if 'bframe' in (frame.url or ''):
            dl_url = frame.evaluate("""() => {
                const a = document.querySelector('audio');
                if (a && a.src) return a.src;
                const d = document.querySelector('a[download]');
                if (d && d.href) return d.href;
                // Also try all links
                for (const el of document.querySelectorAll('a')) {
                    if (el.href && el.href.includes('audio')) return el.href;
                }
                return null;
            }""")
            break

    if not dl_url:
        return False

    # Download audio
    try:
        req = urllib.request.Request(dl_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=15) as resp:
            audio_data = resp.read()
    except:
        return False

    # Decode MP3 -> WAV
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
    except:
        return False

    # Transcribe
    r = sr.Recognizer()
    with sr.AudioFile(wav) as src:
        audio = r.record(src)
    try:
        text = r.recognize_google(audio)
        print(f"      🔊 \"{text}\"")
    except:
        text = None

    os.unlink(mp3)
    os.unlink(wav)

    if not text:
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

    # Wait for token generation
    page.wait_for_timeout(5000)

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
        page.evaluate("""t => {
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
        return True

    return False


def fill_form(page):
    """Fill signup form with standard fields."""
    for sel in ['input[name="email"]', 'input[type="email"]']:
        try:
            el = page.query_selector(sel)
            if el and el.is_visible():
                el.fill(EMAIL)
                break
        except: pass

    pw_fields = page.query_selector_all('input[type="password"]')
    if pw_fields:
        try: pw_fields[0].fill(PASSWORD)
        except: pass
        if len(pw_fields) >= 2:
            try: pw_fields[1].fill(PASSWORD)
            except: pass

    # Accept terms
    for label in ['Privacy Policy', 'I accept', 'I agree', 'Terms of Service',
                  'Terms & Conditions', 'terms']:
        try:
            lb = page.locator(f'label:has-text("{label}")')
            if lb.count() > 0:
                lb.first.click()
                break
        except: pass


def click_submit(page):
    for sel in ['button[type="submit"]', 'input[type="submit"]',
                'button:has-text("Sign up")', 'button:has-text("Register")',
                'button:has-text("Create")', 'button:has-text("Next")']:
        try:
            btn = page.query_selector(sel)
            if btn and btn.is_visible():
                btn.click()
                return True
        except: pass
    return False


def click_login(page):
    for sel in ['button:has-text("Sign in")', 'button:has-text("Login")',
                'button:has-text("Log in")', 'button[type="submit"]']:
        try:
            btn = page.query_selector(sel)
            if btn and btn.is_visible():
                btn.click()
                return True
        except: pass
    return False


def extract_keys(page, gw_id):
    gw = GATEWAYS[gw_id]
    text = page.inner_text("body")[:3000]

    # Click create buttons
    for t in ['Create', 'Generate', 'Add', 'New', 'Create key', 'Generate key']:
        try:
            btn = page.locator(f'button:has-text("{t}"), a:has-text("{t}")')
            if btn.count() > 0:
                btn.first.click()
                page.wait_for_timeout(3000)
                break
        except: pass

    keys = {}
    # Scan inputs
    for el in page.query_selector_all('input'):
        try:
            v = (el.get_attribute("value") or el.input_value() or "").strip()
            if len(v) < 16: continue
            name = (el.get_attribute("name") or "").lower()
            if "public" in name or ("api" in name and "key" in name):
                keys["api_key"] = v
            elif "secret" in name or "private" in name:
                keys["secret"] = v
            elif "password" in name:
                keys["password"] = v
        except: pass

    # Scan text
    for m in re.finditer(r'[0-9a-f]{32,}', text, re.I):
        keys.setdefault("secret", m.group())
    for m in re.finditer(r'[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', text):
        keys.setdefault("api_key", m.group())
    for m in re.finditer(r'\b[A-Za-z0-9+/=_-]{32,64}\b', text):
        v = m.group()
        if v.startswith("sk_"): keys.setdefault("secret", v)
        elif v.startswith("pk_"): keys.setdefault("api_key", v)

    mapped = {}
    ek = gw["env_keys"]
    if len(ek) >= 1 and keys.get("api_key"):
        mapped[ek[0]] = keys["api_key"]
    if len(ek) >= 2:
        mapped[ek[1]] = keys.get("secret") or keys.get("password") or ""
    mapped[gw["env"]] = "production"

    return mapped if len(mapped) > 1 else {}


def grab_one(gw_id, page):
    gw = GATEWAYS[gw_id]
    start = datetime.now(timezone.utc).isoformat()

    print(f"\n  {'='*50}")
    print(f"  🔑 {gw['name']}")
    print(f"  {'='*50}")

    # STEP 1: Signup
    print(f"  → {gw['signup']}")
    try:
        page.goto(gw["signup"], wait_until="domcontentloaded", timeout=30000)
    except:
        pass
    page.wait_for_timeout(4000)

    fill_form(page)
    print("  ✓ Form filled")

    # Check for CAPTCHA
    body = page.content().lower()
    has_captcha = 'recaptcha' in body or 'g-recaptcha' in body

    if has_captcha:
        print("  🔐 Solving reCAPTCHA...")
        if not solve_captcha(page):
            print("  ❌ CAPTCHA failed")
            return {}
        print("  ✓ CAPTCHA solved")

    if not click_submit(page):
        page.keyboard.press("Enter")
    page.wait_for_timeout(6000)
    print(f"  📍 {page.url[:80]}")

    # STEP 2: Handle response
    url = page.url.lower()
    if 'login' in url or 'signin' in url or 'sign-in' in url:
        print("  → Switching to login...")
        if gw["login"] != page.url:
            try:
                page.goto(gw["login"], wait_until="domcontentloaded", timeout=15000)
                page.wait_for_timeout(3000)
            except: pass

        # Fill login
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

        if has_captcha:
            solve_captcha(page)

        click_login(page)
        page.wait_for_timeout(6000)
        print(f"  📍 Login: {page.url[:80]}")

    # Check for OTP
    for otp_sel in ['input[autocomplete="one-time-code"]', 'input[name="code"]',
                   'input[name="otp"]', 'input[placeholder*="code" i]']:
        try:
            el = page.query_selector(otp_sel)
            if el and el.is_visible():
                print("  📧 OTP screen → fetching from mail.tm...")
                otp = fetch_otp(start)
                if otp:
                    if otp.startswith("http"):
                        page.goto(otp, timeout=15000)
                        page.wait_for_timeout(5000)
                    else:
                        el.fill(otp)
                        print(f"  ✓ OTP: {otp}")
                        page.keyboard.press("Enter")
                        page.wait_for_timeout(5000)
                break
        except: pass

    # STEP 3: Navigate to API keys
    if gw.get("apikeys"):
        print(f"  → API keys: {gw['apikeys']}")
        try:
            page.goto(gw["apikeys"], wait_until="domcontentloaded", timeout=15000)
            page.wait_for_timeout(5000)
        except:
            pass

    # STEP 4: Extract
    keys = extract_keys(page, gw_id)
    if keys and len(keys) > 1:
        print(f"  ✅ KEYS: {', '.join(f'{k}={v[:20]}...' for k,v in keys.items() if v)}")
        update_env(keys)
    else:
        print(f"  ⚠ No keys extracted")
        # Save screenshot for debugging
        page.screenshot(path=f"/tmp/{gw_id}_final.png")

    return keys


def main():
    args = [a.lower() for a in sys.argv[1:]]
    targets = [a for a in args if a in GATEWAYS] if args and "all" not in args else list(GATEWAYS.keys())
    if not targets:
        print("Available:", ", ".join(GATEWAYS.keys()))
        return

    print(f"\n🦊 FIREFOX FINAL GRAB — {len(targets)} gateways")
    print(f"   {EMAIL}")

    results = {}
    with sync_playwright() as p:
        for gw_id in targets:
            try:
                browser = p.firefox.launch(headless=True)
                ctx = browser.new_context(
                    viewport={'width': 1440, 'height': 900},
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:125.0) Gecko/20100101 Firefox/125.0',
                    locale='en-US',
                    timezone_id='America/Chicago',
                )
                page = ctx.new_page()
                results[gw_id] = grab_one(gw_id, page)
                ctx.close()
                browser.close()
            except Exception as e:
                print(f"  ❌ {gw_id}: {e}")
                import traceback; traceback.print_exc()

    print(f"\n{'='*50}")
    print(f"  📊 RESULTS")
    print(f"{'='*50}")
    for gw_id, keys in results.items():
        s = "✅ LIVE" if (keys and len(keys) > 1) else "❌ FAILED"
        print(f"  {s}  {GATEWAYS[gw_id]['name']}")
    print(f"\n  Verify: python3 gateway_agents_activate.py --verify")


if __name__ == "__main__":
    main()

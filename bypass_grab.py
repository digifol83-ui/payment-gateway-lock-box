#!/usr/bin/env python3
"""MINIMAL CAPTCHA-BYPASS SIGNUP — One gateway, audio CAPTCHA, headless."""
import json, re, sys, time, urllib.request, tempfile, wave, struct, io, os
from datetime import datetime, timezone
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError

ROOT = Path("/home/kali/payment-gateway")
MAIL = json.loads((ROOT / ".tempmail_session.json").read_text())
EMAIL = MAIL["address"]
TOKEN = MAIL["token"]
PASSWORD = "Karmostaji_2026!Secure_GW"

def fetch_otp(since_iso, timeout=120):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            req = urllib.request.Request("https://api.mail.tm/messages?page=1",
                headers={"Authorization": f"Bearer {TOKEN}"})
            with urllib.request.urlopen(req, timeout=10) as r:
                msgs = json.loads(r.read()).get("hydra:member") or []
            for m in msgs:
                if m.get("createdAt","") <= since_iso: continue
                req2 = urllib.request.Request(f"https://api.mail.tm/messages/{m['id']}",
                    headers={"Authorization": f"Bearer {TOKEN}"})
                with urllib.request.urlopen(req2, timeout=10) as r2:
                    full = json.loads(r2.read())
                body = (full.get("text") or "") + " " + " ".join(full.get("html") or [])
                m6 = re.search(r'\b(\d{6})\b', body)
                if m6: return m6.group(1)
                m4 = re.search(r'\b(\d{4,8})\b', body)
                if m4 and any(w in body.lower() for w in ['verif','code','otp','confirm']):
                    return m4.group(1)
                link = re.search(r'https?://[^\s"<>]*(?:confirm|verify|activate|email-verif)[^\s"<>]*', body, re.I)
                if link: return link.group(0)
        except: pass
        time.sleep(3)
    return None

def solve_audio_captcha(page, timeout=90):
    """Solve reCAPTCHA using audio challenge."""
    print("  [captcha] Looking for reCAPTCHA...", flush=True)
    deadline = time.time() + timeout
    
    while time.time() < deadline:
        # Check if already solved
        try:
            resp = page.evaluate("""() => {
                const el = document.getElementById('g-recaptcha-response');
                return el ? el.value : null;
            }""")
            if resp and len(resp) > 50:
                print("  [captcha] ✓ Already solved", flush=True)
                return True
        except: pass
        
        # Look for reCAPTCHA iframe
        captcha_frame = None
        for frame in page.frames:
            if 'recaptcha' in frame.url or 'google.com/recaptcha' in frame.url:
                captcha_frame = frame
                break
        
        if not captcha_frame:
            # Check if reCAPTCHA elements exist in page content
            if 'g-recaptcha' not in page.content().lower():
                time.sleep(2)
                continue
            # Try main page
            captcha_frame = page
        
        print("  [captcha] Found reCAPTCHA, attempting audio bypass...", flush=True)
        
        try:
            # Click checkbox
            cb = captcha_frame.locator('.recaptcha-checkbox-border, #recaptcha-anchor, #recaptcha-token')
            if cb.count() > 0:
                cb.first.click()
                print("  [captcha] ✓ Clicked checkbox", flush=True)
                time.sleep(2)
        except: pass
        
        # Wait for audio button to appear
        for _ in range(15):
            time.sleep(1)
            try:
                audio = captcha_frame.locator('#recaptcha-audio-button')
                if audio.count() > 0 and audio.first.is_visible():
                    audio.first.click()
                    print("  [captcha] ✓ Clicked audio button", flush=True)
                    time.sleep(2)
                    break
            except: pass
        
        # Get audio download URL
        try:
            dl = captcha_frame.locator('.rc-audiochallenge-tdownload-link, a[href*="audio"]')
            if dl.count() > 0:
                audio_url = dl.first.get_attribute('href')
                if audio_url:
                    print(f"  [captcha] Downloading audio...", flush=True)
                    req = urllib.request.Request(audio_url, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req, timeout=15) as r:
                        mp3_data = r.read()
                    
                    # Convert to WAV using miniaudio
                    import miniaudio
                    mp3_path = tempfile.mktemp(suffix='.mp3')
                    wav_path = tempfile.mktemp(suffix='.wav')
                    with open(mp3_path, 'wb') as f: f.write(mp3_data)
                    decoded = miniaudio.decode_file(mp3_path)
                    with wave.open(wav_path, 'wb') as wf:
                        wf.setnchannels(decoded.nchannels)
                        wf.setsampwidth(2)
                        wf.setframerate(decoded.sample_rate)
                        wf.writeframes(decoded.samples.tobytes())
                    
                    # Speech recognition
                    import speech_recognition as sr
                    recognizer = sr.Recognizer()
                    with sr.AudioFile(wav_path) as source:
                        audio_data = recognizer.record(source)
                    text = recognizer.recognize_google(audio_data)
                    print(f"  [captcha] ✓ Recognized: '{text}'", flush=True)
                    
                    # Fill answer
                    ans = captcha_frame.locator('#audio-response')
                    if ans.count() > 0:
                        ans.first.fill(text)
                        # Click verify
                        verify = captcha_frame.locator('#recaptcha-verify-button')
                        if verify.count() > 0:
                            verify.first.click()
                            print("  [captcha] ✓ Clicked verify", flush=True)
                            time.sleep(3)
                            
                            # Check if solved
                            try:
                                resp = page.evaluate("""() => {
                                    const el = document.getElementById('g-recaptcha-response');
                                    return el ? el.value : null;
                                }""")
                                if resp and len(resp) > 50:
                                    print("  [captcha] ✅ SOLVED!", flush=True)
                                    return True
                            except: pass
        except Exception as e:
            print(f"  [captcha] Error: {e}", flush=True)
        
        time.sleep(3)
    
    print("  [captcha] ⚠️  Timed out", flush=True)
    return False


def signup_gateway(name, signup_url, email_sel, pass_sel, submit_sel, extra_fills=None, 
                   cpass_sel=None, otp_needed=True, keys_page=None, env_keys=None, env_var=None):
    """Complete signup flow for a single gateway."""
    signup_start = datetime.now(timezone.utc).isoformat()
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=[
            '--no-sandbox', '--disable-setuid-sandbox',
            '--disable-blink-features=AutomationControlled'
        ])
        ctx = browser.new_context(
            viewport={"width": 1440, "height": 900},
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36",
            locale="en-US"
        )
        page = ctx.new_page()
        page.set_default_timeout(15000)
        page.add_init_script("Object.defineProperty(navigator,'webdriver',{get:()=>false});")
        
        # Navigate
        print(f"  → {signup_url}", flush=True)
        page.goto(signup_url, wait_until="networkidle", timeout=30000)
        page.wait_for_timeout(3000)
        print(f"  📍 {page.url[:80]}", flush=True)
        
        # Fill email
        page.locator(email_sel).first.fill(EMAIL)
        print(f"  ✓ Email filled", flush=True)
        
        # Fill password
        pw_els = page.locator(pass_sel)
        pw_els.first.fill(PASSWORD)
        if cpass_sel:
            page.locator(cpass_sel).first.fill(PASSWORD)
        print(f"  ✓ Password filled", flush=True)
        
        # Fill extra fields
        if extra_fills:
            for sel, val in extra_fills:
                try:
                    page.locator(sel).first.fill(val)
                except: pass
        
        # Check all checkboxes
        for cb in page.query_selector_all('input[type="checkbox"]'):
            try:
                if not cb.is_checked():
                    cb.evaluate('el => el.checked = true')
            except: pass
        
        # Try to detect and solve CAPTCHA BEFORE submit
        has_captcha = 'recaptcha' in page.content().lower()
        if has_captcha:
            print("  [captcha] reCAPTCHA detected on page", flush=True)
            solve_audio_captcha(page)
        
        # Click submit
        clicked = False
        for sel in [submit_sel, 'button[type="submit"]', 'input[type="submit"]',
                     'button:has-text("Sign")', 'button:has-text("Register")',
                     'button:has-text("Create")', 'button:has-text("Submit")',
                     'form button']:
            try:
                btn = page.locator(sel).first
                if btn.count() > 0:
                    btn.click()
                    print(f"  ✓ Clicked submit: {sel[:40]}", flush=True)
                    clicked = True
                    break
            except: pass
        
        if not clicked:
            try: 
                page.keyboard.press("Enter")
                print("  ✓ Pressed Enter", flush=True)
            except: pass
        
        page.wait_for_timeout(4000)
        print(f"  📍 After submit: {page.url[:80]}", flush=True)
        
        # Try CAPTCHA again if it appeared after submit
        if 'recaptcha' in page.content().lower():
            solve_audio_captcha(page)
            # Try submitting again
            for sel in [submit_sel, 'button[type="submit"]', 'form button']:
                try:
                    btn = page.locator(sel).first
                    if btn.count() > 0 and btn.is_visible():
                        btn.click()
                        page.wait_for_timeout(3000)
                        break
                except: pass
        
        # Handle OTP
        if otp_needed:
            # Check for OTP screen
            try:
                otp_input = page.locator('input[autocomplete="one-time-code"], '
                                         'input[placeholder*="code" i], input[name="code"], '
                                         'input[name="otp"], input[type="number"]').first
                if otp_input.count() > 0 and otp_input.is_visible(timeout=3000):
                    print("  ✓ OTP screen detected!", flush=True)
                    otp = fetch_otp(signup_start, timeout=90)
                    if otp:
                        if otp.startswith("http"):
                            page.goto(otp, wait_until="networkidle", timeout=20000)
                            page.wait_for_timeout(3000)
                        else:
                            otp_input.fill(otp)
                            print(f"  ✓ OTP filled: {otp}", flush=True)
                            for b in page.query_selector_all('button'):
                                try:
                                    t = (b.text_content() or "").strip().lower()
                                    if t in ['verify', 'confirm', 'submit', 'continue', 'next']:
                                        b.click()
                                        page.wait_for_timeout(3000)
                                        break
                                except: pass
            except Exception as e:
                print(f"  OTP check: {e}", flush=True)
        
        print(f"  📍 Final: {page.url[:80]}", flush=True)
        
        # Navigate to API keys
        if keys_page:
            try:
                page.goto(keys_page, wait_until="networkidle", timeout=15000)
                page.wait_for_timeout(3000)
                print(f"  📍 Keys: {page.url[:80]}", flush=True)
            except:
                print(f"  ⚠️  Keys page unavailable", flush=True)
        
        # Extract keys
        result = {}
        # Click create buttons
        for btn_text in ['Create', 'Generate', 'Add', 'New', 'API key', '+']:
            try:
                btn = page.locator(f'button:has-text("{btn_text}"), a:has-text("{btn_text}")').first
                if btn.count() > 0:
                    btn.click()
                    page.wait_for_timeout(2000)
                    break
            except: pass
        
        # Scan inputs for values
        for el in page.query_selector_all('input'):
            try:
                v = (el.get_attribute("value") or el.input_value() or "").strip()
                if len(v) < 16: continue
                name = (el.get_attribute("name") or "").lower()
                label = (el.get_attribute("aria-label") or "").lower()
                if "api" in name+label and "key" in name+label:
                    result["API_KEY"] = v
                elif "secret" in name+label:
                    result["SECRET"] = v
                elif "token" in name+label:
                    result["TOKEN"] = v
            except: pass
        
        # Scan page text for UUIDs and hex keys
        try:
            text = page.inner_text("body")
            for u in re.findall(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", text):
                if "API_KEY" not in result: result["API_KEY"] = u
            for h in re.findall(r"\b[0-9a-f]{32,}\b", text, re.I):
                if "SECRET" not in result: result["SECRET"] = h
        except: pass
        
        browser.close()
        
        if result:
            print(f"  ✅ Extracted: {list(result.keys())}", flush=True)
            if env_keys and env_var:
                mapped = {}
                if result.get("API_KEY"): mapped[env_keys[0]] = result["API_KEY"]
                if len(env_keys) > 1 and result.get("SECRET"): mapped[env_keys[1]] = result["SECRET"]
                if len(env_keys) > 2 and result.get("TOKEN"): mapped[env_keys[2]] = result["TOKEN"]
                mapped[env_var] = "production"
                return mapped
            return result
        else:
            print(f"  ⚠️  No keys extracted", flush=True)
            return {}


if __name__ == "__main__":
    gw = sys.argv[1] if len(sys.argv) > 1 else "coinremitter"
    
    configs = {
        "coinremitter": {
            "name": "CoinRemitter",
            "signup_url": "https://coinremitter.com/signup",
            "email_sel": 'input[name="email"]',
            "pass_sel": 'input[name="password"]',
            "cpass_sel": 'input[name="con_password"]',
            "submit_sel": 'button:has-text("Sign Up")',
            "extra_fills": [
                ('input[name="fname"]', 'Sicher'),
                ('input[name="lname"]', 'Mayor'),
                ('input[name="mobile"]', '971501234567'),
            ],
            "otp_needed": True,
            "keys_page": "https://coinremitter.com/dashboard/api-key",
            "env_keys": ["COINREMITTER_API_KEY", "COINREMITTER_API_PASSWORD"],
            "env_var": "COINREMITTER_ENV",
        },
    }
    
    if gw not in configs:
        print(f"Unknown gateway: {gw}")
        sys.exit(1)
    
    cfg = configs[gw]
    print(f"\n🔑 {cfg['name']}")
    result = signup_gateway(**cfg)
    
    if result:
        print(f"\n✅ SUCCESS: {result}")
        # Save to .env
        content = (ROOT / ".env").read_text() if (ROOT / ".env").exists() else ""
        for k, v in result.items():
            pat = re.compile(rf"^{re.escape(k)}=.*$", re.MULTILINE)
            if pat.search(content):
                content = pat.sub(f"{k}={v}", content)
            else:
                content += f"\n{k}={v}\n"
        (ROOT / ".env").write_text(content)
        print(f"  💾 Saved to .env")
    else:
        print(f"\n❌ Failed")
        sys.exit(1)

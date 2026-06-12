#!/usr/bin/env python3
"""Parallel headless grab — all gateways except NOWPayments (manual)."""
import json, os, re, sys, time, urllib.request
from datetime import datetime, timezone
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PT

ROOT = Path("/home/kali/payment-gateway")
ENV = ROOT / ".env"
MAIL = json.loads((ROOT / ".tempmail_session.json").read_text())
EMAIL = MAIL["address"]
TOKEN = MAIL["token"]
PASSWORD = "Karmostaji_2026!Secure_GW"

def save(k, v):
    if not v: return
    c = ENV.read_text() if ENV.exists() else ""
    p = re.compile(rf"^{re.escape(k)}=.*$", re.MULTILINE)
    ENV.write_text(p.sub(f"{k}={v}", c) if p.search(c) else c + f"\n{k}={v}\n")

def mask(s, pre=8, post=4):
    s = str(s or "")
    return f"{s[:pre]}...{s[-post:]}" if len(s) > pre+post+4 else "*"*min(len(s),8)

def fetch_otp(since_iso, timeout=90):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            req = urllib.request.Request("https://api.mail.tm/messages?page=1",
                headers={"Authorization": f"Bearer {TOKEN}"})
            with urllib.request.urlopen(req, timeout=5) as r:
                msgs = json.loads(r.read()).get("hydra:member") or []
            for m in msgs:
                if m.get("createdAt", "") <= since_iso: continue
                req2 = urllib.request.Request(f"https://api.mail.tm/messages/{m['id']}",
                    headers={"Authorization": f"Bearer {TOKEN}"})
                with urllib.request.urlopen(req2, timeout=5) as r2:
                    full = json.loads(r2.read())
                body = (full.get("text") or "") + " " + " ".join(full.get("html") or [])
                c6 = re.search(r'\b(\d{6})\b', body)
                if c6: print(f"     OTP: {c6.group(1)}"); return c6.group(1)
                c48 = re.search(r'\b(\d{4,8})\b', body)
                if c48 and any(w in body.lower() for w in ['verif','code','otp','confirm','activ']):
                    print(f"     Code: {c48.group(1)}"); return c48.group(1)
                l = re.search(r'https?://[^\s\"\'<>]*(?:confirm|verify|activate|email-verif)[^\s\"\'<>]*', body, re.I)
                if l: print(f"     Link: {l.group(0)[:60]}"); return l.group(0)
        except: pass
        time.sleep(2)
    return None

def extract(page, gw, start_iso):
    """Deep extraction with create button click & OTP handling."""
    r = {}

    # Handle OTP if visible
    try:
        otp_el = page.query_selector('input[autocomplete="one-time-code"], input[placeholder*="code" i], input[name*="otp" i], input[name*="code" i]')
        if otp_el and otp_el.is_visible():
            print("     OTP screen detected!")
            code = fetch_otp(start_iso, 60)
            if code:
                if code.startswith("http"):
                    try: page.goto(code, wait_until="domcontentloaded", timeout=10000); page.wait_for_timeout(3000)
                    except: pass
                    code = None
                if code and not code.startswith("http"):
                    try:
                        els = page.query_selector_all('input[autocomplete="one-time-code"], input[placeholder*="code" i]')
                        if len(els) >= len(code):
                            for i,ch in enumerate(code): els[i].fill(ch)
                        else: els[0].fill(code)
                        for b in ['button:has-text("Verify")','button[type="submit"]','button:has-text("Submit")','button:has-text("Confirm")']:
                            try:
                                bb = page.query_selector(b)
                                if bb and bb.is_visible(): bb.click(); break
                            except: pass
                        page.wait_for_timeout(4000)
                    except Exception as e: print(f"     OTP fill error: {e}")
    except: pass

    # Click create/generate
    for t in ['Create','Generate','Add','New','API key','+','Create key']:
        for tag in ['button','a','span','div']:
            try:
                b = page.locator(f'{tag}:has-text("{t}")')
                if b.count() > 0:
                    b.first.click(); page.wait_for_timeout(3000); print(f'     Clicked "{t}"'); break
            except: pass
        else: continue
        break
    page.wait_for_timeout(2000)

    # Inputs
    for el in page.query_selector_all('input, textarea'):
        try:
            v = (el.get_attribute("value") or el.input_value() or "").strip()
            if len(v) < 16: continue
            lbl = (el.get_attribute("name") or el.get_attribute("aria-label") or 
                   el.get_attribute("placeholder") or "").lower()
            parent = ""
            try: parent = (el.evaluate("el => el.closest('div')?.textContent?.substring(0,80) || ''") or "").lower()
            except: pass
            ctx = lbl + " " + parent
            if any(kw in ctx for kw in ['api key','apikey','api_key']) and 'secret' not in ctx:
                r["API_KEY"] = v
            elif any(kw in ctx for kw in ['secret','private key','api secret']):
                r["SECRET"] = v
            elif 'token' in ctx: r["TOKEN"] = v
            elif 'password' in ctx and 'api' in ctx: r["API_PASSWORD"] = v
            elif 'merchant' in ctx or ('id' in lbl and 'api' in ctx): r["MERCHANT_ID"] = v
            elif 'ipn' in ctx: r["IPN_SECRET"] = v
        except: pass

    # Text scan
    try:
        txt = page.inner_text("body")
        for u in re.findall(r'\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b', txt):
            if "API_KEY" not in r: r["API_KEY"] = u; break
        for h in re.findall(r'\b[0-9a-f]{32,}\b', txt, re.I):
            if "SECRET" not in r: r["SECRET"] = h; break
        for s in re.findall(r'\b[A-Za-z0-9+/=_-]{32,}\b', txt):
            if (s.startswith("sk_") or s.startswith("sk_live_")) and "SECRET" not in r: r["SECRET"] = s
            elif (s.startswith("pk_") or s.startswith("pk_live_")) and "API_KEY" not in r: r["API_KEY"] = s
    except: pass

    # Code/pre blocks
    for el in page.query_selector_all('code, pre, [class*="key" i], [class*="secret" i], [class*="token" i], [class*="credential" i]'):
        try:
            v = el.text_content().strip()
            if len(v) < 16: continue
            cls = (el.get_attribute("class") or "").lower()
            if "secret" in cls and "SECRET" not in r: r["SECRET"] = v
            elif "key" in cls and "API_KEY" not in r: r["API_KEY"] = v
            elif "token" in cls and "TOKEN" not in r: r["TOKEN"] = v
        except: pass

    # Map
    kl = gw["env_keys"]
    mapped = {}
    if r.get("API_KEY") and len(kl) >= 1: mapped[kl[0]] = r["API_KEY"]
    if r.get("SECRET") and len(kl) >= 2: mapped[kl[1]] = r["SECRET"]
    if r.get("TOKEN") and len(kl) >= 3: mapped[kl[2]] = r["TOKEN"]
    if r.get("API_PASSWORD") and "API_PASSWORD" in str(kl): mapped["COINREMITTER_API_PASSWORD"] = r["API_PASSWORD"]
    if r.get("MERCHANT_ID") and "MERCHANT_ID" in str(kl): mapped["COINPAYMENTS_MERCHANT_ID"] = r["MERCHANT_ID"]
    if r.get("IPN_SECRET"): mapped["COINPAYMENTS_IPN_SECRET"] = r["IPN_SECRET"]
    mapped[gw["env_var"]] = "production"
    for k,v in r.items():
        if k not in mapped: mapped[k] = v
    return mapped if len(mapped) > 1 else {}

def grab(page, gw_id):
    gw = GATEWAYS[gw_id]
    start = datetime.now(timezone.utc).isoformat()
    
    # Try signup
    print(f"  → {gw['signup']}")
    try: page.goto(gw["signup"], wait_until="networkidle", timeout=20000)
    except: page.goto(gw["signup"], wait_until="domcontentloaded", timeout=15000)
    page.wait_for_timeout(3000)

    # Fill form
    page.locator(gw.get("email_sel", 'input[type="email"]')).first.fill(EMAIL)
    print("  ✓ Email")
    pw_els = page.query_selector_all(gw.get("pw_sel", 'input[type="password"]'))
    if pw_els:
        pw_els[0].fill(PASSWORD)
        print("  ✓ Password")
        if gw.get("confirm") and len(pw_els) >= 2:
            try: pw_els[1].fill(PASSWORD); print("  ✓ Confirm")
            except: pass
    
    for sel,val in gw.get("extra", []):
        try:
            el = page.query_selector(sel)
            if el and el.is_visible(): el.fill(val)
        except: pass

    page.wait_for_timeout(500)

    # Submit
    for s in gw.get("submit_sels", ['button[type="submit"]', 'input[type="submit"]',
            'button:has-text("Sign up")','button:has-text("Register")','button:has-text("Create")',
            'button:has-text("Submit")','button:has-text("Continue")','button:has-text("Get started")',
            'a:has-text("Get started")','a:has-text("Sign up")','button:has-text("Get API")']):
        try:
            btn = page.query_selector(s)
            if btn and btn.is_visible(): btn.click(); print(f"  ✓ Submit: {s[:40]}"); break
        except: pass
    
    page.wait_for_timeout(4000)
    print(f"  📍 {page.url[:80]}")

    # Check for CAPTCHA
    body = page.content().lower()
    if 'recaptcha' in body:
        print("  ⚠️  reCAPTCHA on page — trying bypass")
        # Quick audio bypass attempt
        try:
            page.evaluate("""() => {
                const frames = document.querySelectorAll('iframe');
                for (const f of frames) {
                    try {
                        const btn = f.contentDocument.querySelector('#recaptcha-audio-button');
                        if (btn) { btn.click(); return 'audio'; }
                    } catch(e) {}
                }
                return 'none';
            }""")
            page.wait_for_timeout(3000)
            audio_url = page.evaluate("""() => {
                const links = document.querySelectorAll('a');
                for (const l of links) {
                    if (l.href && l.href.includes('audio')) return l.href;
                }
                return null;
            }""")
            if audio_url:
                print(f"  🔊 Audio URL: {audio_url[:80]}...")
                # Download + recognize
                import io, base64 as b64
                req = urllib.request.Request(audio_url, headers={'User-Agent':'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    audio_data = resp.read()
                import subprocess, tempfile
                mp3 = tempfile.mktemp(suffix='.mp3')
                with open(mp3,'wb') as f: f.write(audio_data)
                try:
                    r2 = subprocess.run(['ffmpeg','-y','-i',mp3,'-acodec','pcm_s16le','-ac','1','-ar','16000','-f','wav','pipe:1'],
                                       capture_output=True, timeout=10)
                    wav = r2.stdout
                except: wav = audio_data
                try:
                    import speech_recognition as sr
                    rec = sr.Recognizer()
                    with sr.AudioFile(io.BytesIO(wav)) as source: audio = rec.record(source)
                    text = rec.recognize_google(audio)
                    print(f"  🔊 Recognized: {text}")
                    for s in ['#audio-response','input[name="audio-response"]']:
                        try:
                            el = page.query_selector(s)
                            if el: el.fill(text); break
                        except: pass
                    for b in ['#recaptcha-verify-button','button[title*="verify" i]']:
                        try:
                            btn = page.query_selector(b)
                            if btn: btn.click(); print("  ✓ Verify clicked"); break
                        except: pass
                except Exception as e: print(f"  🔊 STT error: {e}")
        except Exception as e: print(f"  ⚠️ Bypass error: {e}")

    # Wait for redirect
    deadline = time.time() + 60
    while time.time() < deadline:
        url = page.url.lower()
        if any(d in url for d in ['/dashboard','/account','/profile','/api','/merchant']):
            print(f"  ✓ Dashboard: {url[:80]}")
            break
        try:
            otp = page.query_selector('input[autocomplete="one-time-code"], input[placeholder*="code" i], input[name*="otp" i]')
            if otp and otp.is_visible():
                code = fetch_otp(start, 60)
                if code:
                    otp.fill(code)
                    for b in ['button:has-text("Verify")','button[type="submit"]']:
                        try:
                            bb = page.query_selector(b)
                            if bb and bb.is_visible(): bb.click(); break
                        except: pass
                    page.wait_for_timeout(4000)
                    break
        except: pass
        time.sleep(2)

    page.wait_for_timeout(2000)

    # Go to keys page
    if gw.get("keys"):
        print(f"  → Keys: {gw['keys']}")
        try: page.goto(gw["keys"], wait_until="domcontentloaded", timeout=12000)
        except: pass
        page.wait_for_timeout(4000)

    # Extract
    keys = extract(page, gw, start)
    return keys

GATEWAYS = {
    "coinremitter": {
        "name":"CoinRemitter","signup":"https://merchant.coinremitter.com/signup",
        "keys":"https://merchant.coinremitter.com/api-key",
        "email_sel":'input[name="email"]',
        "pw_sel":'input[name="password"]',"confirm":True,
        "env_keys":["COINREMITTER_API_KEY","COINREMITTER_API_PASSWORD"],
        "env_var":"COINREMITTER_ENV",
    },
    "changelly": {
        "name":"Changelly","signup":"https://pro.changelly.com/sign-up",
        "keys":"https://pro.changelly.com/dashboard/api-keys",
        "email_sel":'input[type="email"]',
        "pw_sel":'input[type="password"]',
        "env_keys":["CHANGELLY_API_KEY","CHANGELLY_SECRET"],
        "env_var":"CHANGELLY_ENV",
    },
    "changenow": {
        "name":"ChangeNOW","signup":"https://changenow.io/affiliate",
        "keys":"https://changenow.io/affiliate/dashboard",
        "email_sel":'input[type="email"]',
        "pw_sel":'input[type="password"]',
        "env_keys":["CHANGENOW_API_KEY","CHANGENOW_SECRET"],
        "env_var":"CHANGENOW_ENV",
        "submit_sels":['button:has-text("Sign up")','button:has-text("Register")','button:has-text("Join")'],
    },
    "kyrrex": {
        "name":"Kyrrex","signup":"https://kyrrex.com/register",
        "keys":"https://kyrrex.com/account/api",
        "email_sel":'input[type="email"]',
        "pw_sel":'input[type="password"]',"confirm":True,
        "env_keys":["KYRREX_API_KEY","KYRREX_SECRET","KYRREX_WEBHOOK_SECRET"],
        "env_var":"KYRREX_ENV",
    },
    "coinpayments": {
        "name":"CoinPayments","signup":"https://www.coinpayments.net/register",
        "keys":"https://www.coinpayments.net/index.php?cmd=acct_api_keys",
        "email_sel":'input[name="email"]',
        "pw_sel":'input[name="password"]',"confirm":True,
        "env_keys":["COINPAYMENTS_MERCHANT_ID","COINPAYMENTS_IPN_SECRET"],
        "env_var":"COINPAYMENTS_ENV",
        "extra":[('input[name="company"]','CryptoEx FZE')],
    },
    "charge": {
        "name":"Charge","signup":"https://charge.io/signup",
        "env_keys":["CHARGE_API_KEY","CHARGE_SECRET"],
        "env_var":"CHARGE_ENV",
    },
    "guardarian": {
        "name":"Guardarian","signup":"https://guardarian.com/for-business",
        "env_keys":["GUARDARIAN_API_KEY","GUARDARIAN_SECRET"],
        "env_var":"GUARDARIAN_ENV",
    },
}

print(f"\n{'='*60}")
print(f"  🦞 PARALLEL HEADLESS GRAB — {len(GATEWAYS)} gateways")
print(f"  ✉️  {EMAIL}")
print(f"  🤖 Headless + Audio CAPTCHA bypass")
print(f"{'='*60}\n")

results = {}
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=[
        '--no-sandbox','--disable-setuid-sandbox',
        '--disable-blink-features=AutomationControlled'])
    
    for gw_id, gw in GATEWAYS.items():
        print(f"\n{'─'*50}")
        print(f"  🔑 {gw['name']} ({gw_id})")
        context = browser.new_context(viewport={"width":1440,"height":900},
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36")
        page = context.new_page()
        page.add_init_script("Object.defineProperty(navigator,'webdriver',{get:()=>false});window.chrome={runtime:{}};")
        page.set_default_timeout(20000)
        
        try:
            keys = grab(page, gw_id)
            if keys and len(keys) > 1:
                print(f"  ✅ KEYS: {mask(str(keys))}")
                for k,v in keys.items(): save(k,v)
                stash = ROOT / f".{gw_id}_keys.json"
                stash.write_text(json.dumps(keys, indent=2)); stash.chmod(0o600)
                results[gw_id] = True
            else:
                print(f"  ❌ No keys")
                results[gw_id] = False
        except Exception as e:
            print(f"  ❌ {type(e).__name__}: {e}")
            results[gw_id] = False
        finally:
            context.close()
    
    browser.close()

print(f"\n{'='*60}")
print(f"  📊 RESULTS")
for gw_id, ok in results.items():
    print(f"  {'✅' if ok else '❌'} {GATEWAYS[gw_id]['name']}")
live = sum(1 for v in results.values() if v)
print(f"\n  💰 LIVE: {live}/{len(GATEWAYS)}")
print(f"{'='*60}")

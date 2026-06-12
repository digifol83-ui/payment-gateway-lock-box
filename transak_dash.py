#!/usr/bin/env python3
"""Log into Transak dashboard and check API key settings / permissions."""
from playwright.sync_api import sync_playwright
import json, time, re, urllib.request, tempfile, os
import speech_recognition as sr, miniaudio, wave
from datetime import datetime, timezone

EMAIL = 'sichermayor@wshu.net'
MAIL = json.loads(open('/home/kali/payment-gateway/.tempmail_session.json').read())

def solve_audio(page):
    try: page.evaluate('()=>{if(typeof grecaptcha!=="undefined")grecaptcha.reset()}')
    except: pass
    page.wait_for_timeout(1000)
    for f in page.frames:
        if 'anchor' in (f.url or ''):
            try: f.locator('#recaptcha-anchor').click(timeout=5000)
            except: pass
            break
    page.wait_for_timeout(4000)
    for frame in list(page.frames):
        if 'bframe' in (frame.url or ''):
            try:
                btn = frame.locator('#recaptcha-audio-button')
                if btn.count() > 0: btn.first.click(timeout=5000)
            except: pass
            break
    page.wait_for_timeout(5000)
    dl_url = None
    for frame in list(page.frames):
        if 'bframe' in (frame.url or ''):
            dl_url = frame.evaluate('()=>{const a=document.querySelector("audio");if(a&&a.src)return a.src;const d=document.querySelector("a[download]");if(d&&d.href)return d.href;return null}')
    if not dl_url: return False
    req = urllib.request.Request(dl_url, headers={'User-Agent':'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=15) as resp: audio_data = resp.read()
    mp3=tempfile.mktemp(suffix='.mp3'); wav=tempfile.mktemp(suffix='.wav')
    with open(mp3,'wb') as f: f.write(audio_data)
    decoded=miniaudio.decode_file(mp3)
    with wave.open(wav,'wb') as wf:
        wf.setnchannels(decoded.nchannels); wf.setsampwidth(2)
        wf.setframerate(decoded.sample_rate); wf.writeframes(decoded.samples.tobytes())
    r=sr.Recognizer()
    with sr.AudioFile(wav) as src: audio=r.record(src)
    try: text=r.recognize_google(audio)
    except: text=None
    os.unlink(mp3); os.unlink(wav)
    if not text: return False
    print(f'  Audio: "{text}"')
    for frame in list(page.frames):
        if 'bframe' in (frame.url or ''):
            try:
                inp=frame.locator('#audio-response')
                if inp.count()>0: inp.first.fill(text)
                page.wait_for_timeout(300)
                frame.locator('#recaptcha-verify-button').click(timeout=3000)
            except: pass
            break
    page.wait_for_timeout(4000)
    token = page.evaluate('''()=>{
        const el=document.getElementById('g-recaptcha-response');
        if(el&&el.value&&el.value.length>50)return el.value;
        if(typeof grecaptcha!=='undefined'){try{for(let i=0;i<10;i++){const t=grecaptcha.getResponse(i);if(t&&t.length>50)return t}}catch(e){}}
        return null;
    }''')
    if token:
        page.evaluate('t=>{let el=document.getElementById("g-recaptcha-response");if(!el){el=document.createElement("textarea");el.id="g-recaptcha-response";el.style.display="none";document.body.appendChild(el)}el.value=t;for(const f of document.querySelectorAll("form")){let h=f.querySelector("[name=g-recaptcha-response]");if(!h){h=document.createElement("input");h.type="hidden";h.name="g-recaptcha-response";f.appendChild(h)}h.value=t}}', token)
        return True
    return False

def get_otp(since):
    TOKEN = MAIL['token']
    dl = time.time() + 120
    while time.time() < dl:
        try:
            req = urllib.request.Request('https://api.mail.tm/messages?page=1',
                headers={'Authorization': f'Bearer {TOKEN}'})
            with urllib.request.urlopen(req, timeout=10) as r:
                msgs = json.loads(r.read()).get('hydra:member') or []
            for m in msgs:
                if m.get('createdAt','') <= since: continue
                req2 = urllib.request.Request(f'https://api.mail.tm/messages/{m["id"]}',
                    headers={'Authorization': f'Bearer {TOKEN}'})
                with urllib.request.urlopen(req2, timeout=10) as r2:
                    full = json.loads(r2.read())
                body = (full.get('text') or '') + ' ' + ' '.join(full.get('html') or [])
                m6 = re.search(r'\b(\d{6})\b', body)
                if m6: return m6.group(1)
        except: pass
        time.sleep(3)
    return None

with sync_playwright() as p:
    browser = p.firefox.launch(headless=True)
    ctx = browser.new_context(viewport={'width':1440,'height':900},
        user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:125.0) Gecko/20100101 Firefox/125.0',
        locale='en-US')
    page = ctx.new_page()

    print('🔑 Transak Dashboard Login...')
    page.goto('https://dashboard.transak.com/login', wait_until='domcontentloaded', timeout=30000)
    page.wait_for_timeout(4000)

    page.fill('input[name="email"]', EMAIL)
    print(f'Email: {EMAIL}')

    if 'recaptcha' in page.content().lower():
        print('Solving CAPTCHA...')
        if not solve_audio(page):
            print('❌ CAPTCHA failed - trying without')
        else:
            print('✓ CAPTCHA done')

    for sel in ['button:has-text("Continue")', 'button[type="submit"]']:
        btn = page.query_selector(sel)
        if btn and btn.is_visible(): btn.click(); print('Clicked Continue'); break

    page.wait_for_timeout(6000)
    print(f'URL: {page.url}')
    text = page.inner_text('body')[:400]
    print(f'Body: {text[:250]}')

    # Check for OTP
    if 'code' in text.lower() or 'otp' in text.lower() or 'verif' in text.lower():
        start = datetime.now(timezone.utc).isoformat()
        print('OTP screen - fetching from mail...')
        otp = get_otp(start)
        if otp:
            print(f'OTP: {otp}')
            for sel in ['input[name="code"]', 'input[placeholder*="code" i]', 'input[type="text"]']:
                try:
                    el = page.query_selector(sel)
                    if el and el.is_visible(): el.fill(otp); break
                except: pass
            page.keyboard.press('Enter')
            page.wait_for_timeout(5000)

    print(f'Final URL: {page.url}')

    # If logged in, look for API keys / settings
    if 'dashboard' in page.url.lower() and 'login' not in page.url.lower():
        print('\n✅ LOGGED INTO TRANSAK DASHBOARD!')

        # Look for API keys / settings navigation
        nav = page.evaluate('''() => {
            const items = [];
            for (const el of document.querySelectorAll('a, button, [role="button"], .nav-item, .sidebar-item, li')) {
                const t = el.textContent.trim().slice(0, 60);
                const h = el.href || '';
                if (t && t.length > 2 && t.length < 60) items.push(t + (h ? ' | ' + h.slice(0,80) : ''));
            }
            return [...new Set(items)].slice(0, 40);
        }''')
        print('Navigation:')
        for item in nav:
            print(f'  {item}')

        # Try to find API key management
        for url in ['https://dashboard.transak.com/settings',
                     'https://dashboard.transak.com/api-keys',
                     'https://dashboard.transak.com/developers',
                     'https://dashboard.transak.com/integration']:
            try:
                page.goto(url, wait_until='domcontentloaded', timeout=10000)
                page.wait_for_timeout(3000)
                text = page.inner_text('body')[:300]
                if 'api' in text.lower() or 'key' in text.lower() or 'secret' in text.lower():
                    print(f'\n✅ API settings at: {url}')
                    print(f'   {text[:200]}')
                    page.screenshot(path='/tmp/transak_api_settings.png')
                    break
            except: pass

        page.screenshot(path='/tmp/transak_dashboard.png')
    else:
        print('\n⚠ Login failed or needs manual verification')
        page.screenshot(path='/tmp/transak_login_result.png')

    browser.close()

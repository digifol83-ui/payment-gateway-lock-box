#!/usr/bin/env python3
"""Diagnostic: dump everything inside reCAPTCHA frames on NOWPayments signup."""
import time, json
from playwright.sync_api import sync_playwright

EMAIL = "sichermayor@wshu.net"
PASSWORD = "Karmostaji_2026!Secure_GW"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
    context = browser.new_context(
        viewport={"width": 1440, "height": 900},
        user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36",
    )
    page = context.new_page()
    page.set_default_timeout(15000)

    print("1. Navigating to NOWPayments signup...")
    page.goto("https://account.nowpayments.io/create-account", wait_until="domcontentloaded")
    page.wait_for_timeout(4000)

    print("2. Filling email...")
    page.fill('input[name="email"]', EMAIL)
    page.fill('input[name="password"]', PASSWORD)
    page.fill('input[name="passwordConfirm"]', PASSWORD)
    page.wait_for_timeout(500)

    print("3. Accepting terms...")
    try:
        for label in page.locator('label').all():
            text = (label.text_content() or "").strip()
            if any(w in text.lower() for w in ['accept', 'agree', 'terms', 'i have read']):
                label.click()
                print(f"   Clicked: {text[:60]}")
                page.wait_for_timeout(200)
    except Exception as e:
        print(f"   Terms error: {e}")

    print("4. Clicking Next step...")
    page.click('button:has-text("Next step")')
    page.wait_for_timeout(5000)

    print("\n=== RECHAPTCHA DIAGNOSTIC ===\n")

    # Dump all frames
    all_frames = page.frames
    print(f"Total frames: {len(all_frames)}")
    for i, f in enumerate(all_frames):
        print(f"\n  Frame {i}: url={f.url[:120]}")

        if 'recaptcha' in f.url.lower() or 'google.com' in f.url:
            print(f"  *** RECHAPTCHA FRAME ***")
            # Dump all elements in this frame
            try:
                # Get all elements with their attributes
                html = f.evaluate("""() => {
                    const all = document.querySelectorAll('*');
                    const out = [];
                    for (const el of all) {
                        const tag = el.tagName.toLowerCase();
                        const attrs = {};
                        for (const a of el.attributes) {
                            attrs[a.name] = a.value;
                        }
                        const text = (el.textContent || '').trim().substring(0, 100);
                        out.push({tag, id: el.id, class: el.className, attrs, text});
                    }
                    return out;
                }""")

                for el in html:
                    tag = el['tag']
                    eid = el['id']
                    cls = el['class']
                    attrs = el['attrs']
                    text = el['text']

                    # Focus on interesting elements
                    interesting = ('audio' in tag or 'source' in tag or
                                   'download' in (cls or '') or 'audio' in (cls or '') or
                                   'button' in tag or 'input' in tag or
                                   'response' in (eid or '') or 'audio' in (eid or '') or
                                   'verify' in (eid or '') or 'challenge' in (eid or ''))

                    if interesting:
                        print(f"    <{tag}> id={eid} class={cls}")
                        for k, v in attrs.items():
                            if k not in ('id', 'class'):
                                vshort = str(v)[:120]
                                print(f"      {k}={vshort}")
                        if text:
                            print(f"      text='{text}'")

                # Also get audio-specific info
                audio_info = f.evaluate("""() => {
                    const audios = document.querySelectorAll('audio, source');
                    const result = [];
                    for (const a of audios) {
                        result.push({
                            tag: a.tagName,
                            src: a.src || a.getAttribute('src'),
                            currentSrc: a.currentSrc || null,
                            readyState: a.readyState,
                            networkState: a.networkState,
                            duration: a.duration,
                            error: a.error ? a.error.message : null
                        });
                    }
                    // Also check for blob URLs in the page
                    const allSrc = [];
                    document.querySelectorAll('[src]').forEach(el => allSrc.push(el.getAttribute('src')));
                    document.querySelectorAll('[href]').forEach(el => {
                        const h = el.getAttribute('href');
                        if (h && h.includes('audio')) allSrc.push(h);
                    });
                    return {audios: result, relevantUrls: allSrc.filter(u => u && u.length > 5)};
                }""")
                print(f"\n    Audio elements: {json.dumps(audio_info['audios'], indent=4)}")
                print(f"    Relevant URLs: {json.dumps(audio_info['relevantUrls'], indent=4)}")

            except Exception as e:
                print(f"    Error inspecting frame: {e}")

    # Also check page-level
    print("\n=== PAGE-LEVEL CHECK ===")
    body = page.content()
    has_recaptcha = 'recaptcha' in body.lower()
    has_challenge = 'audio' in body.lower() or 'visual' in body.lower()
    print(f"reCAPTCHA in body: {has_recaptcha}")
    print(f"Challenge visible: {has_challenge}")

    # Try to find reCAPTCHA site key
    site_keys = page.evaluate("""() => {
        const keys = [];
        document.querySelectorAll('[data-sitekey]').forEach(el => keys.push(el.getAttribute('data-sitekey')));
        // Also check scripts
        const scripts = document.querySelectorAll('script');
        for (const s of scripts) {
            const t = s.textContent || '';
            const m = t.match(/['\"]sitekey['\"]\\s*:\\s*['\"]([^'\"]+)['\"]/);
            if (m) keys.push(m[1]);
        }
        return keys;
    }""")
    print(f"Site keys found: {site_keys}")

    # Take screenshot
    page.screenshot(path="/tmp/recaptcha_diag.png")
    print(f"\nScreenshot: /tmp/recaptcha_diag.png")

    browser.close()

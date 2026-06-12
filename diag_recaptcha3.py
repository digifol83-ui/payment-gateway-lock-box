#!/usr/bin/env python3
"""Diagnostic v3: Network interception + long poll for reCAPTCHA audio."""
import time, json, re, io
from playwright.sync_api import sync_playwright

EMAIL = "sichermayor@wshu.net"
PASSWORD = "Karmostaji_2026!Secure_GW"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=['--no-sandbox',
        '--disable-blink-features=AutomationControlled'])
    context = browser.new_context(
        viewport={"width": 1440, "height": 900},
        user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/125.0.0.0 Safari/537.36",
    )
    page = context.new_page()
    page.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', { get: () => false });
    """)
    page.set_default_timeout(30000)

    # Collect ALL network requests
    all_requests = []
    captured_bodies = []

    def on_request(request):
        url = request.url
        if 'recaptcha' in url or 'google.com/recaptcha' in url:
            all_requests.append({
                'method': request.method,
                'url': url[:200],
                'headers': dict(request.headers),
                'postData': (request.post_data or '')[:200]
            })

    def on_response(response):
        url = response.url
        if 'recaptcha' in url or 'google.com/recaptcha' in url:
            try:
                ct = response.headers.get('content-type', '')
                body = response.body()
                all_requests.append({
                    'type': 'RESPONSE',
                    'url': url[:200],
                    'status': response.status,
                    'contentType': ct,
                    'bodyLen': len(body) if body else 0,
                    'bodyPreview': (body[:500] if body else b'').hex() if body else ''
                })
                if body and len(body) > 200:
                    captured_bodies.append({'url': url[:200], 'len': len(body), 'ct': ct, 'body': body})
            except Exception as e:
                all_requests.append({'type': 'RESPONSE_ERR', 'url': url[:200], 'error': str(e)})

    page.on('request', on_request)
    page.on('response', on_response)

    print("1. Navigating to NOWPayments signup...")
    page.goto("https://account.nowpayments.io/create-account", wait_until="domcontentloaded")
    page.wait_for_timeout(4000)

    print("2. Fill form + accept terms + Next step...")
    page.fill('input[name="email"]', EMAIL)
    page.fill('input[name="password"]', PASSWORD)
    page.fill('input[name="passwordConfirm"]', PASSWORD)
    for label in page.locator('label').all():
        text = (label.text_content() or "").strip()
        if any(w in text.lower() for w in ['accept', 'agree', 'terms']):
            label.click()
            page.wait_for_timeout(200)
    page.click('button:has-text("Next step")')
    page.wait_for_timeout(3000)

    # Find challenge frame and click audio
    print("\n3. Looking for challenge frame + audio button...")
    bframe = None
    for frame in page.frames:
        if 'bframe' in (frame.url or ''):
            bframe = frame
            print(f"   Found bframe: {frame.url[:120]}")
            break

    if bframe:
        print("4. Clicking audio button in bframe...")
        try:
            ab = bframe.locator('#recaptcha-audio-button')
            if ab.count() > 0:
                ab.first.click()
                print("   ✓ Clicked audio button")
        except Exception as e:
            print(f"   Error: {e}")

    # Poll the iframe for 20 seconds, checking every 1s
    print("\n5. Polling iframe for audio elements (20s)...")
    for i in range(20):
        page.wait_for_timeout(1000)
        if bframe:
            try:
                state = bframe.evaluate("""() => {
                    const audios = document.querySelectorAll('audio, source');
                    const links = document.querySelectorAll('a[href]');
                    const allSrcs = [];
                    document.querySelectorAll('[src]').forEach(el => {
                        const s = el.getAttribute('src');
                        if (s) allSrcs.push(s.substring(0, 150));
                    });
                    return {
                        audioCount: audios.length,
                        audioSrcs: Array.from(audios).map(a => a.src?.substring(0,120) || 'no-src'),
                        linkCount: links.length,
                        downloadLinks: Array.from(links)
                            .filter(l => l.href?.includes('audio') || l.textContent?.includes('download'))
                            .map(l => ({href: l.href?.substring(0,150), text: l.textContent?.trim()})),
                        allSrcs: allSrcs.slice(0,5),
                        bodyLen: document.body.innerHTML.length
                    };
                }""")
                if state['audioCount'] > 0 or state['downloadLinks']:
                    print(f"   [{i}s] FOUND: {json.dumps(state)}")
                    break
                elif i % 3 == 0:
                    print(f"   [{i}s] audioCount={state['audioCount']} links={state['linkCount']} bodyLen={state['bodyLen']}")
            except Exception as e:
                print(f"   [{i}s] Error: {e}")

    # Dump all captured requests
    print(f"\n6. Network summary ({len(all_requests)} reCAPTCHA requests):")
    for r in all_requests:
        if r.get('type') == 'RESPONSE':
            print(f"   RESP {r['status']} {r['contentType'][:40]} body={r['bodyLen']}B  {r['url'][:100]}")
        elif 'type' not in r:
            print(f"   REQ {r['method']}  {r['url'][:100]}")

    # Check captured bodies for audio
    print(f"\n7. Captured bodies ({len(captured_bodies)}):")
    for cb in captured_bodies:
        b = cb['body']
        is_audio = b[:4] == b'\xff\xfb' or b[:3] == b'ID3' or b[:2] == b'\xff\xe0'
        print(f"   {cb['len']}B ct={cb['ct'][:40]} audio={is_audio} url={cb['url'][:100]}")
        if is_audio:
            with open('/tmp/captured_audio.mp3', 'wb') as f:
                f.write(b)
            print(f"   >>> SAVED to /tmp/captured_audio.mp3")

    # Final check: try JS to force audio URL extraction
    print("\n8. JS deep extraction attempt...")
    if bframe:
        try:
            deep = bframe.evaluate("""() => {
                const result = {};
                // Check all variables in window
                for (const k of Object.keys(window)) {
                    const v = window[k];
                    if (typeof v === 'string' && v.length > 20) {
                        if (v.includes('audio') || v.includes('mp3') || v.includes('.wav')) {
                            result[k] = v.substring(0, 200);
                        }
                    }
                }
                // Check data attributes
                document.querySelectorAll('[data-*]').forEach(el => {
                    for (const a of el.attributes) {
                        if (a.value && a.value.length > 10 && (a.value.includes('audio') || a.value.includes('mp3'))) {
                            result['attr_' + a.name] = a.value.substring(0, 200);
                        }
                    }
                });
                // Check inline scripts
                document.querySelectorAll('script').forEach(s => {
                    const t = s.textContent || '';
                    const m = t.match(/(https?:[^"'\\s]*audio[^"'\\s]*)/i);
                    if (m) result['script_url'] = m[1];
                });
                return result;
            }""")
            print(f"   Deep extraction: {json.dumps(deep)}")
        except Exception as e:
            print(f"   Deep extraction error: {e}")

    page.screenshot(path="/tmp/recaptcha_diag3.png")
    print(f"\nDone. Screenshot: /tmp/recaptcha_diag3.png")
    browser.close()

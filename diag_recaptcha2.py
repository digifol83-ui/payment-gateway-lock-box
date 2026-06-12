#!/usr/bin/env python3
"""Diagnostic v2: Force reCAPTCHA challenge, dump audio mechanism, test blob URLs."""
import time, json, base64
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

    print("1. Navigating to NOWPayments signup...")
    page.goto("https://account.nowpayments.io/create-account", wait_until="domcontentloaded")
    page.wait_for_timeout(4000)

    print("2. Filling email/pw...")
    page.fill('input[name="email"]', EMAIL)
    page.fill('input[name="password"]', PASSWORD)
    page.fill('input[name="passwordConfirm"]', PASSWORD)

    print("3. Accepting terms...")
    for label in page.locator('label').all():
        text = (label.text_content() or "").strip()
        if any(w in text.lower() for w in ['accept', 'agree', 'terms']):
            label.click()
            print(f"   ✓ {text[:60]}")
            page.wait_for_timeout(200)

    print("4. Clicking Next step...")
    page.click('button:has-text("Next step")')
    page.wait_for_timeout(3000)

    # Check if reCAPTCHA anchor is loaded and try to force challenge
    print("\n5. Inspecting reCAPTCHA state...")

    # Try to force grecaptcha.execute
    recaptcha_state = page.evaluate("""() => {
        try {
            if (typeof grecaptcha !== 'undefined') {
                return {
                    hasGrecaptcha: true,
                    renderCount: grecaptcha.render ? 'function' : 'not function',
                };
            }
        } catch(e) {}
        // Find reCAPTCHA widget
        const widgets = document.querySelectorAll('.g-recaptcha, [data-sitekey]');
        const result = {widgets: widgets.length};
        for (const w of widgets) {
            result.sitekey = w.getAttribute('data-sitekey');
            result.widgetId = w.getAttribute('data-widget-id');
        }
        // Check if hidden token field has value
        const token = document.getElementById('g-recaptcha-response');
        if (token) result.tokenLen = token.value.length;
        return result;
    }""")
    print(f"   reCAPTCHA state: {json.dumps(recaptcha_state)}")

    # Find the anchor frame and click it to trigger challenge
    print("\n6. Finding anchor frame and clicking to trigger challenge...")
    anchor_frame = None
    for frame in page.frames:
        if 'recaptcha/api2/anchor' in frame.url:
            anchor_frame = frame
            print(f"   Found anchor frame: {frame.url[:100]}")

    if anchor_frame:
        try:
            # Click the checkbox area to trigger challenge
            chk = anchor_frame.locator('#recaptcha-anchor, .recaptcha-checkbox-border, .recaptcha-checkbox')
            if chk.count() > 0:
                chk.first.click()
                print("   ✓ Clicked recaptcha anchor")
            else:
                print("   ⚠️  No checkbox element found")
                # Dump anchor frame elements
                dump = anchor_frame.evaluate("""() => {
                    return document.body.innerHTML.substring(0, 2000);
                }""")
                print(f"   Anchor HTML: {dump[:500]}")
        except Exception as e:
            print(f"   Error clicking: {e}")

    # Wait for challenge frame to appear
    print("\n7. Waiting for challenge frame...")
    for i in range(10):
        page.wait_for_timeout(2000)
        frames = page.frames
        challenge_frames = [f for f in frames if 'recaptcha/api2/bframe' in (f.url or '') or
                            ('recaptcha' in (f.url or '') and 'anchor' not in (f.url or ''))]
        if challenge_frames:
            print(f"   ✓ Challenge frame appeared after {i*2}s!")
            break
        print(f"   ...frame count: {len(frames)} (no challenge yet)")
        # Check for different frame URL patterns
        for f in frames:
            url = f.url or ''
            if 'google.com' in url and 'anchor' not in url:
                print(f"   Noted frame: {url[:100]}")

    # Fully inspect challenge frame
    print("\n8. Full challenge frame inspection...")
    for i, f in enumerate(page.frames):
        url = f.url or ''
        if 'recaptcha' in url.lower():
            print(f"\n   === Frame {i}: {url[:120]} ===")
            try:
                # Get ALL elements
                all_els = f.evaluate("""() => {
                    const all = document.querySelectorAll('*');
                    return Array.from(all).map(el => ({
                        tag: el.tagName.toLowerCase(),
                        id: el.id || '',
                        cls: el.className || '',
                        attrs: Object.fromEntries(
                            Array.from(el.attributes)
                                .filter(a => !['id','class','style'].includes(a.name))
                                .map(a => [a.name, String(a.value).substring(0, 200)])
                        ),
                        text: (el.textContent || '').trim().substring(0, 80),
                        childCount: el.children.length
                    }));
                }""")
                for el in all_els[:80]:  # limit output
                    tag, eid, cls = el['tag'], el['id'], el['cls']
                    if tag in ('audio','source','a','button','input','div') and (
                        'audio' in cls.lower() or 'audio' in eid.lower() or
                        'download' in cls.lower() or 'download' in eid.lower() or
                        'button' in tag or 'input' in tag or
                        tag in ('audio','source')
                    ):
                        print(f"     <{tag}> id={eid} class={cls[:60]}")
                        for k,v in el['attrs'].items():
                            print(f"       {k}={v}")
            except Exception as e:
                print(f"     Error: {e}")

    # Try to trigger audio challenge
    print("\n9. Clicking audio challenge button...")
    clicked_audio = False
    for frame in page.frames:
        try:
            ab = frame.locator('#recaptcha-audio-button')
            if ab.count() > 0 and ab.first.is_visible():
                ab.first.click()
                print("   ✓ Clicked audio button!")
                clicked_audio = True
                page.wait_for_timeout(4000)
                break
        except: pass

    if not clicked_audio:
        print("   ⚠️  No audio button found")
        # Check what buttons exist
        for frame in page.frames:
            url = frame.url or ''
            if 'recaptcha' in url:
                buttons = frame.evaluate("""() => {
                    return Array.from(document.querySelectorAll('button, [role="button"]')).map(b => ({
                        id: b.id, class: b.className, text: b.textContent?.trim()?.substring(0,40)
                    }));
                }""")
                print(f"   Buttons in frame: {json.dumps(buttons)}")

    # After audio challenge, inspect again
    print("\n10. Post-audio-click inspection...")
    page.wait_for_timeout(3000)
    for frame in page.frames:
        url = frame.url or ''
        if 'recaptcha' in url.lower():
            print(f"\n   Frame: {url[:120]}")
            try:
                # Get audio/download elements
                audio_els = frame.evaluate("""() => {
                    const result = {};
                    // Audio elements
                    const audios = document.querySelectorAll('audio, source');
                    result.audios = Array.from(audios).map(a => ({
                        tag: a.tagName, src: a.src, currentSrc: a.currentSrc,
                        readyState: a.readyState, duration: a.duration
                    }));
                    // Download links
                    const links = document.querySelectorAll('a[href]');
                    result.downloadLinks = Array.from(links)
                        .filter(l => l.href && (l.href.includes('audio') || l.textContent.includes('download')))
                        .map(l => ({href: l.href.substring(0, 200), text: l.textContent.trim()}));
                    // All hrefs
                    result.allHrefs = Array.from(links).map(l => l.href).slice(0, 10);
                    // All src attrs
                    const srcs = [];
                    document.querySelectorAll('[src]').forEach(el => srcs.push(el.getAttribute('src')?.substring(0,120)));
                    result.allSrcs = srcs.slice(0, 10);
                    // Inline scripts/data
                    const scripts = Array.from(document.querySelectorAll('script')).map(s => s.textContent?.substring(0,200));
                    result.scripts = scripts.filter(s => s && (s.includes('audio') || s.includes('mp3') || s.includes('payload')));
                    return result;
                }""")
                print(json.dumps(audio_els, indent=6)[:3000])
            except Exception as e:
                print(f"   Error: {e}")

    # Final screenshot
    page.screenshot(path="/tmp/recaptcha_diag2.png")
    print(f"\nScreenshot: /tmp/recaptcha_diag2.png")
    print(f"\nURL: {page.url}")

    browser.close()

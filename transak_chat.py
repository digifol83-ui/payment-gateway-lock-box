#!/usr/bin/env python3
"""Send Transak whitelist request via Intercom chat."""
from playwright.sync_api import sync_playwright
import time

MSG = ('Hi, please enable API-based Create Widget URL for Production partner '
       '75b192bd. Whitelist IP 34.55.54.52 (Cloud Run us-central1). '
       'Domain: beastpay-api-544494288390.us-central1.run.app. '
       'Token refresh works, session returns errorCode 1002. Thanks!')

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, args=['--no-sandbox'])
    ctx = browser.new_context(viewport={'width': 1440, 'height': 900},
        user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36')
    page = ctx.new_page()

    page.goto('https://support.transak.com/en/', wait_until='domcontentloaded', timeout=20000)
    page.wait_for_timeout(8000)

    # Boot Intercom with email pre-set
    page.evaluate("""() => {
        var s = document.createElement('script');
        s.innerHTML = JSON.stringify({app_id: 'ayaezmi3', email: 'sichermayor@wshu.net', name: 'Sicher Mayor'});
        window.intercomSettings = {app_id: 'ayaezmi3', email: 'sichermayor@wshu.net', name: 'Sicher Mayor'};
        if (window.Intercom) {
            Intercom('boot', {app_id: 'ayaezmi3', email: 'sichermayor@wshu.net', name: 'Sicher Mayor'});
        }
    }""")
    page.wait_for_timeout(5000)

    # Show messenger with pre-filled message
    page.evaluate('msg => { if(window.Intercom) Intercom("showNewMessage", msg); }', MSG)
    page.wait_for_timeout(10000)

    # List all non-blank frames
    print('Frames:')
    for f in page.frames:
        url = f.url or ''
        name = f.name or ''
        if url != 'about:blank':
            print(f'  {name}: {url[:150]}')

    # Find Intercom frame and send
    for f in page.frames:
        url = f.url or ''
        name = f.name or ''
        if 'intercom' in url.lower() or 'intercom' in name.lower():
            print(f'\nIntercom frame: {url[:150]}')
            if url and url != 'about:blank' and 'intercom' in url.lower():
                try:
                    f.locator('textarea').first.click(timeout=5000)
                    f.locator('textarea').first.fill(MSG)
                    f.locator('textarea').first.press('Enter')
                    print('SENT!')
                    page.wait_for_timeout(5000)
                except Exception as e:
                    print(f'Error: {e}')
            break

    page.screenshot(path='/tmp/transak_final.png')
    browser.close()

print('\nDone')

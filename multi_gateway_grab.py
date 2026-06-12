#!/usr/bin/env python3
"""
MULTI-GATEWAY KEY GRAB — Headless + stealth + auto CAPTCHA solving.
Signs up for ALL self-serve crypto gateways and grabs production keys.

Pattern: headless Chromium with stealth → pre-fill email/password → auto-solve reCAPTCHA/hCaptcha →
         grab OTP from mail.tm → navigate to API keys → extract → save .env

Usage: python3 multi_gateway_grab.py changelly
       python3 multi_gateway_grab.py all
       python3 multi_gateway_grab.py nowpayments coinremitter changelly changenow kyrrex
"""
import json, os, re, sys, time, urllib.request, io, base64, random, math
from datetime import datetime, timezone
from pathlib import Path
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

# ── Anti-detection: human-like delays ──
def _human_delay(min_ms=200, max_ms=800):
    """Random delay to mimic human interaction."""
    time.sleep(random.uniform(min_ms, max_ms) / 1000.0)

def _human_type(page, selector, text, delay_ms=80):
    """Type like a human — one character at a time with variable delay."""
    el = page.query_selector(selector)
    if el and el.is_visible():
        el.click()
        _human_delay(200, 500)
        for char in text:
            el.press(char)
            time.sleep(random.uniform(30, delay_ms) / 1000.0)
        return True
    return False

ROOT = Path("/home/kali/payment-gateway")
ENV_FILE = ROOT / ".env"
MAIL_SESSION_FILE = ROOT / ".tempmail_session.json"
SHOTS = Path("/tmp/gateway_grabs"); SHOTS.mkdir(exist_ok=True)

# Load mail.tm session
MAIL = json.loads(MAIL_SESSION_FILE.read_text())
EMAIL = MAIL["address"]
TOKEN = MAIL["token"]

PASSWORD = "Karmostaji_2026!Secure_GW"

# ============================================================================
# GATEWAY SIGNUP CONFIGS
# ============================================================================
GATEWAYS = {
    "nowpayments": {
        "name": "NOWPayments",
        "signup_url": "https://account.nowpayments.io/create-account",
        "login_url": "https://account.nowpayments.io/login",
        "api_keys_url": "https://account.nowpayments.io/api-keys",
        "email_field": 'input[name="email"]',
        "password_field": 'input[name="password"]',
        "confirm_password_field": 'input[name="passwordConfirm"]',
        "submit_button": 'button:has-text("Next step")',
        "otp_screen_selector": 'input[placeholder*="code" i], input[autocomplete="one-time-code"], input[name="code"]',
        "dashboard_indicator": "/dashboard",
        "env_keys": ["NOWPAYMENTS_API_KEY"],
        "env_var": "NOWPAYMENTS_ENV",
        "has_self_serve": True, "has_api_keys_page": True,
    },
    "coinremitter": {
        "name": "CoinRemitter",
        "signup_url": "https://coinremitter.com/signup",
        "login_url": "https://coinremitter.com/login",
        "api_keys_url": "https://coinremitter.com/dashboard/api-key",
        "email_field": 'input[name="email"], input[type="email"]',
        "password_field": 'input[name="password"], input[type="password"]',
        "confirm_password_field": 'input[name="password_confirmation"], input[placeholder*="confirm" i]',
        "submit_button": 'button[type="submit"], button:has-text("Sign up"), input[type="submit"]',
        "otp_screen_selector": 'input[placeholder*="code" i], input[name="otp"]',
        "dashboard_indicator": "/dashboard",
        "env_keys": ["COINREMITTER_API_KEY", "COINREMITTER_API_PASSWORD"],
        "env_var": "COINREMITTER_ENV",
        "has_self_serve": True, "has_api_keys_page": True,
    },
    "changelly": {
        "name": "Changelly",
        "signup_url": "https://pro.changelly.com/register",
        "login_url": "https://pro.changelly.com/login",
        "api_keys_url": "https://pro.changelly.com/dashboard/api-keys",
        "email_field": 'input[type="email"], input[name="email"]',
        "password_field": 'input[type="password"]',
        "confirm_password_field": None,
        "submit_button": 'button:has-text("Sign up"), button:has-text("Register"), button[type="submit"]',
        "otp_needed": False,
        "dashboard_indicator": "/dashboard",
        "env_keys": ["CHANGELLY_API_KEY", "CHANGELLY_SECRET"],
        "env_var": "CHANGELLY_ENV",
        "has_self_serve": True, "has_api_keys_page": True,
    },
    "changenow": {
        "name": "ChangeNOW",
        "signup_url": "https://changenow.io/affiliate",
        "login_url": "https://changenow.io/login",
        "api_keys_url": "https://changenow.io/affiliate/dashboard",
        "email_field": 'input[type="email"]',
        "password_field": 'input[type="password"]',
        "confirm_password_field": None,
        "submit_button": 'button:has-text("Sign up"), button:has-text("Register"), a:has-text("Affiliate")',
        "dashboard_indicator": "/dashboard",
        "env_keys": ["CHANGENOW_API_KEY", "CHANGENOW_SECRET"],
        "env_var": "CHANGENOW_ENV",
        "has_self_serve": True, "has_api_keys_page": True,
    },
    "kyrrex": {
        "name": "Kyrrex",
        "signup_url": "https://kyrrex.com/register",
        "login_url": "https://kyrrex.com/login",
        "api_keys_url": "https://kyrrex.com/account/api",
        "email_field": 'input[type="email"], input[name="email"]',
        "password_field": 'input[type="password"]',
        "confirm_password_field": 'input[name="password_confirmation"]',
        "submit_button": 'button[type="submit"], button:has-text("Register"), button:has-text("Sign up")',
        "dashboard_indicator": "/account",
        "env_keys": ["KYRREX_API_KEY", "KYRREX_SECRET", "KYRREX_WEBHOOK_SECRET"],
        "env_var": "KYRREX_ENV",
        "has_self_serve": True, "has_api_keys_page": True,
    },
    "guardarian": {
        "name": "Guardarian",
        "signup_url": "https://guardarian.com/contact-us",
        "login_url": None,
        "api_keys_url": None,
        "email_field": 'input[type="email"]',
        "password_field": 'input[type="password"]',
        "confirm_password_field": None,
        "submit_button": 'button:has-text("Send"), button:has-text("Submit"), button:has-text("Contact"), button[type="submit"]',
        "dashboard_indicator": "/dashboard",
        "env_keys": ["GUARDARIAN_API_KEY", "GUARDARIAN_SECRET"],
        "env_var": "GUARDARIAN_ENV",
        "otp_needed": False, "has_self_serve": False, "has_api_keys_page": False,
    },
}


# ============================================================================
# RECAPTCHA AUDIO BYPASS (route-level interception + blob URL + DOM polling)
# ============================================================================

# Global for route-level payload capture
_payload_captured = None

def _route_payload_handler(route):
    """Intercept recaptcha/api2/payload — capture response body directly."""
    global _payload_captured
    try:
        response = route.fetch()
        body = response.body()
        if body and len(body) > 500:
            _payload_captured = body
            print(f"  [captcha] Route-level capture: {len(body)}B from payload endpoint")
        route.fulfill(response=response)
    except Exception:
        route.continue_()


def _extract_audio_via_blob(frame):
    """Extract audio blob from within an iframe using fetch + base64 encode."""
    try:
        result = frame.evaluate("""async () => {
            // Try <audio> element first
            const audio = document.querySelector('audio');
            if (audio && audio.src && audio.src.startsWith('blob:')) {
                const resp = await fetch(audio.src);
                const blob = await resp.blob();
                const buf = await blob.arrayBuffer();
                const bytes = new Uint8Array(buf);
                let binary = '';
                for (let i = 0; i < bytes.length; i++) binary += String.fromCharCode(bytes[i]);
                return btoa(binary);
            }
            // Try <source> inside audio
            const source = document.querySelector('audio source, source[src]');
            if (source && source.src && source.src.startsWith('blob:')) {
                const resp = await fetch(source.src);
                const buf = await resp.arrayBuffer();
                const bytes = new Uint8Array(buf);
                let binary = '';
                for (let i = 0; i < bytes.length; i++) binary += String.fromCharCode(bytes[i]);
                return btoa(binary);
            }
            return null;
        }""")
        if result:
            return base64.b64decode(result)
    except Exception as e:
        print(f"  [captcha] Blob extraction error: {e}")
    return None


def _poll_for_audio_elements(page, bframe_url_prefix, timeout=15):
    """
    After clicking audio, poll page.frames for the new bframe and extract audio.
    Returns (audio_data_bytes, source_description) or (None, None).
    """
    deadline = time.time() + timeout
    while time.time() < deadline:
        # Re-scan frames (bframe URL changes after audio click)
        for frame in list(page.frames):
            url = frame.url or ""
            if 'recaptcha' not in url.lower():
                continue
            try:
                # Strategy 1: Download link
                for sel in ['a.rc-audiochallenge-tdownload-link',
                           'a[download]', 'a[href*="audio"]',
                           '.rc-audiochallenge-tdownload-link']:
                    el = frame.locator(sel).first
                    if el.count() > 0:
                        href = el.get_attribute('href')
                        if href:
                            if href.startswith('http'):
                                req = urllib.request.Request(href, headers={'User-Agent': 'Mozilla/5.0'})
                                with urllib.request.urlopen(req, timeout=15) as resp:
                                    return resp.read(), f"download-link({sel})"
                            elif href.startswith('data:audio'):
                                b64 = href.split(',', 1)[1] if ',' in href else href
                                return base64.b64decode(b64), f"data-uri({sel})"

                # Strategy 2: <audio> element with http(s) src
                result = frame.evaluate("""() => {
                    const a = document.querySelector('audio');
                    if (a && a.src && a.src.startsWith('http')) return a.src;
                    const s = document.querySelector('source');
                    if (s && s.src && s.src.startsWith('http')) return s.src;
                    return null;
                }""")
                if result:
                    req = urllib.request.Request(result, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req, timeout=15) as resp:
                        return resp.read(), f"audio-src({result[:60]})"

                # Strategy 3: Blob URL audio/src
                blob_data = _extract_audio_via_blob(frame)
                if blob_data and len(blob_data) > 500:
                    return blob_data, "blob-url"

                # Strategy 4: Shadow DOM / deeper search
                shadow_result = frame.evaluate("""() => {
                    // Walk all elements including shadow roots
                    function walk(el) {
                        if (el.tagName === 'AUDIO' && el.src) return el.src;
                        if (el.tagName === 'SOURCE' && el.src) return el.src;
                        if (el.shadowRoot) {
                            for (const child of el.shadowRoot.children) {
                                const r = walk(child);
                                if (r) return r;
                            }
                        }
                        for (const child of el.children) {
                            const r = walk(child);
                            if (r) return r;
                        }
                        return null;
                    }
                    return walk(document.body);
                }""")
                if shadow_result:
                    if shadow_result.startswith('http'):
                        req = urllib.request.Request(shadow_result, headers={'User-Agent': 'Mozilla/5.0'})
                        with urllib.request.urlopen(req, timeout=15) as resp:
                            return resp.read(), f"shadow-dom({shadow_result[:60]})"
                    elif shadow_result.startswith('blob:'):
                        blob_data = _extract_audio_via_blob(frame)
                        if blob_data and len(blob_data) > 500:
                            return blob_data, "shadow-blob"

            except Exception:
                continue

        # Check route-level capture
        global _payload_captured
        if _payload_captured:
            data = _payload_captured
            _payload_captured = None
            return data, "route-interception"

        page.wait_for_timeout(1000)

    return None, None


def _get_bframe_info(page):
    """Safely get challenge info from current bframe. Returns dict or None."""
    for frame in list(page.frames):
        if 'bframe' not in (frame.url or ''):
            continue
        try:
            return frame.evaluate("""() => {
                const r = {};
                const desc = document.querySelector('.rc-imageselect-desc-no-canonical, .rc-imageselect-desc-wrapper');
                r.desc = desc ? desc.textContent.trim() : null;
                r.isVisual = !!document.getElementById('rc-imageselect');
                r.isError = !!document.querySelector('.rc-doscaptcha-header');
                r.isAudio = !!document.querySelector('.rc-audiochallenge');
                r.hasVerify = !!document.getElementById('recaptcha-verify-button');
                r.hasReload = !!document.getElementById('recaptcha-reload-button');
                r.hasAudioBtn = !!document.getElementById('recaptcha-audio-button');
                r.tileCount = document.querySelectorAll('.rc-imageselect-tile').length;
                return r;
            }""")
        except Exception:
            return None
    return None


def _bframe_click(page, selector, timeout=5000):
    """Click an element in the bframe. Always re-scans frames first."""
    for frame in list(page.frames):
        if 'bframe' not in (frame.url or ''):
            continue
        try:
            el = frame.locator(selector)
            if el.count() > 0:
                el.first.click(timeout=timeout)
                return True
        except Exception:
            continue
    return False


def _bframe_click_tile(page, tile_idx):
    """Click a single tile in the visual challenge."""
    for frame in list(page.frames):
        if 'bframe' not in (frame.url or ''):
            continue
        try:
            tile = frame.locator(f'td[id="{tile_idx}"]')
            if tile.count() > 0:
                tile.first.click(timeout=3000)
                time.sleep(random.uniform(0.15, 0.4))
                return True
        except Exception:
            continue
    return False


def _solve_visual_challenge(page, timeout=90):
    """
    Solve reCAPTCHA visual challenge via pattern-based guessing.
    Never holds stale frame references — always re-scans after any interaction.
    """
    print("  [captcha] Visual challenge solver...")
    deadline = time.time() + timeout

    for attempt in range(12):
        if time.time() > deadline:
            break
        if _check_recaptcha_solved(page):
            print("  [captcha] ✅ Solved during visual solver")
            return True

        info = _get_bframe_info(page)
        if not info:
            page.wait_for_timeout(2000)
            continue

        # Handle rate-limit
        if info.get('isError'):
            print("  [captcha] Rate-limited — resetting widget...")
            _reset_recaptcha(page)
            page.wait_for_timeout(5000)
            continue

        # Not a visual challenge — try to make it one via reload or audio
        if not info.get('isVisual'):
            if info.get('hasAudioBtn'):
                print("  [captcha] Has audio button — clicking...")
                _bframe_click(page, '#recaptcha-audio-button')
                page.wait_for_timeout(5000)
            elif info.get('hasReload'):
                _bframe_click(page, '#recaptcha-reload-button')
                page.wait_for_timeout(4000)
            else:
                page.wait_for_timeout(2000)
            continue

        desc = info.get('desc', '') or ''
        tile_count = info.get('tileCount', 0)
        print(f"  [captcha] Visual: '{desc[:80]}' ({tile_count} tiles) [attempt {attempt+1}]")

        if tile_count == 0:
            page.wait_for_timeout(2000)
            continue

        # Strategy 0: Image analysis — download tiles and analyze with PIL
        keywords = _extract_challenge_keywords(desc)
        if keywords:
            print(f"  [captcha] Keywords: {keywords}")
        # Get bframe for tile analysis (search all frames recursively)
        bframe = None
        def find_bframe(frames, depth=0):
            for f in list(frames):
                url = (f.url or '').lower()
                if 'bframe' in url or 'recaptcha/api2' in url:
                    return f
                if depth < 2:
                    child_frames = f.child_frames if hasattr(f, 'child_frames') else []
                    result = find_bframe(child_frames, depth+1)
                    if result:
                        return result
            return None
        bframe = find_bframe(page.frames)
        if bframe:
            print(f"  [captcha] Found bframe: {bframe.url[:80] if bframe.url else 'no url'}")
        else:
            print(f"  [captcha] No bframe found in {len(page.frames)} frames")
        if bframe:
            analysis = _analyze_tiles(bframe, tile_count, keywords)
            if analysis and analysis.get('clicks'):
                clicks = analysis['clicks']
                print(f"  [captcha] Analysis suggests tiles: {clicks}")
                for tile_idx in clicks:
                    _bframe_click_tile(page, tile_idx)
                page.wait_for_timeout(400)
                _bframe_click(page, '#recaptcha-verify-button')
                page.wait_for_timeout(2500)
                if _check_recaptcha_solved(page):
                    print(f"  [captcha] ✅ Solved via image analysis!")
                    return True
                new_info = _get_bframe_info(page)
                if new_info and not new_info.get('isVisual'):
                    continue

        # Strategy 1: Try skip (only for true "none" challenges — when there are NO matches)
        # Heuristic: if the phrase "if there are none" or "none left" appears, try skip first
        skip_tried = False
        if 'if there are none' in desc.lower() or 'click skip' in desc.lower():
            skip_tried = True
            print("  [captcha] Trying skip (no tiles)...")
            _bframe_click(page, '#recaptcha-verify-button')
            page.wait_for_timeout(2500)
            if _check_recaptcha_solved(page):
                return True
            # Check if skip worked (challenge changed from visual)
            new_info = _get_bframe_info(page)
            if new_info and not new_info.get('isVisual'):
                continue  # Challenge changed — next iteration handles it

        # Strategy 2: Try various tile patterns + verify
        patterns_9 = [
            [0, 4, 8],        # diagonal
            [2, 4, 6],        # anti-diagonal  
            [0, 3, 6],        # left column
            [1, 2, 4, 5, 7, 8],  # most tiles except corners
            [0, 1, 2, 3],     # top row
            [0, 3],            # just 2
            [1, 4, 7],        # middle column
            list(range(tile_count)),  # all
        ]
        patterns_16 = [
            [0, 4, 8, 12], [3, 7, 11, 15],
            [5, 6, 9, 10], [0, 1, 4, 5],
        ]
        patterns = patterns_9 if tile_count <= 9 else patterns_16

        found_something = False
        for pat_idx, pattern in enumerate(patterns):
            if time.time() > deadline:
                break
            valid = [t for t in pattern if t < tile_count]
            if not valid:
                continue

            for tile_idx in valid:
                _bframe_click_tile(page, tile_idx)
            page.wait_for_timeout(400)
            _bframe_click(page, '#recaptcha-verify-button')
            page.wait_for_timeout(2500)

            if _check_recaptcha_solved(page):
                print(f"  [captcha] ✅ Solved after pattern {pat_idx}")
                return True

            # Check result
            new_info = _get_bframe_info(page)
            if not new_info:
                break
            if new_info.get('isError'):
                print(f"  [captcha] Rate-limited during pattern {pat_idx}")
                _reset_recaptcha(page)
                page.wait_for_timeout(5000)
                break
            if not new_info.get('isVisual'):
                # Visual challenge disappeared — might be solved or new type
                print(f"  [captcha] Challenge changed after pattern {pat_idx}")
                found_something = True
                break

        if found_something:
            continue

        # Reload for fresh challenge
        print(f"  [captcha] Reloading for new challenge...")
        _bframe_click(page, '#recaptcha-reload-button')
        page.wait_for_timeout(4000)

    return _check_recaptcha_solved(page)


def _extract_challenge_keywords(desc):
    """Extract target object keywords from challenge description."""
    if not desc:
        return []
    desc_lower = desc.lower()
    # Common reCAPTCHA challenge subjects
    known_keywords = [
        'bicycle', 'bicycles', 'motorcycle', 'motorcycles', 'car', 'cars',
        'bus', 'buses', 'truck', 'trucks', 'traffic light', 'traffic lights',
        'fire hydrant', 'fire hydrants', 'crosswalk', 'crosswalks',
        'stairs', 'stair', 'bridge', 'bridges', 'boat', 'boats',
        'store', 'stores', 'sign', 'signs', 'chimney', 'chimneys',
        'parking meter', 'sidewalk', 'palm', 'tree', 'trees',
        'mountain', 'hill', 'street', 'road', 'house', 'building',
    ]
    found = []
    for kw in known_keywords:
        if kw in desc_lower:
            found.append(kw)
    return found


def _analyze_tiles(bframe, tile_count, keywords):
    """
    Analyze tile images to determine which ones likely contain the target object.
    Uses payload captures from route interception (raw tile image data).
    """
    try:
        # Get tile positions from bframe DOM
        tile_info = bframe.evaluate("""() => {
            let tiles = [];
            const cells = document.querySelectorAll('td.rc-imageselect-tile');
            cells.forEach((td, i) => {
                // Get background image URL from the nested div
                const div = td.querySelector('div');
                const bg = div ? (div.style.backgroundImage || getComputedStyle(div).backgroundImage) : '';
                const match = bg.match(/url\(["']?([^"')]+)["']?\)/);
                tiles.push({idx: i, bgUrl: match ? match[1] : ''});
            });
            return tiles;
        }""")

        print(f"  [captcha] Tile DOM analysis: found {len(tile_info) if tile_info else 0} tiles")

        if not tile_info or len(tile_info) == 0:
            # Fallback: try any img elements
            tile_urls = bframe.evaluate("""() => {
                let tiles = [];
                document.querySelectorAll('img').forEach((img, i) => {
                    if (img.src && img.src.length > 10) tiles.push({idx: i, bgUrl: img.src});
                });
                return tiles;
            }""")
            if tile_urls and len(tile_urls) > 0:
                tile_info = tile_urls
                print(f"  [captcha] Fallback: found {len(tile_info)} img elements")

        if not tile_info or len(tile_info) == 0:
            # Use payload captures collected by route handler
            print(f"  [captcha] No DOM tiles — cannot analyze")
            return None

        # Extract unique URLs from tile_info
        unique_urls = list(set(t.get('bgUrl', '') for t in tile_info if t.get('bgUrl', '')))
        print(f"  [captcha] Unique tile URLs: {len(unique_urls)}")

        # Download each unique tile and do basic color analysis
        tile_data = {}
        for url in unique_urls[:min(20, len(unique_urls))]:
            try:
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    img_bytes = resp.read()
                # Basic analysis: average color, edge detection, etc.
                try:
                    from PIL import Image
                    img = Image.open(io.BytesIO(img_bytes))
                    img_rgb = img.convert('RGB')
                    pixels = list(img_rgb.getdata())
                    total = len(pixels)
                    avg_r = sum(p[0] for p in pixels) / total
                    avg_g = sum(p[1] for p in pixels) / total
                    avg_b = sum(p[2] for p in pixels) / total
                    # Calculate variance (high variance = more detail = likely contains object)
                    variance = sum((p[0]-avg_r)**2 + (p[1]-avg_g)**2 + (p[2]-avg_b)**2 for p in pixels) / total
                    tile_data[url] = {'avg': (round(avg_r), round(avg_g), round(avg_b)), 'variance': round(variance), 'size': len(img_bytes)}
                    print(f"  [captcha]   Tile {url[-40:]}: avg=({round(avg_r)},{round(avg_g)},{round(avg_b)}) var={variance:.0f}")
                except ImportError:
                    tile_data[url] = {'size': len(img_bytes)}
            except Exception:
                continue

        if not tile_data:
            return None

        # Determine which tiles to click based on analysis
        # Strategy: sort tiles by variance (higher = more detail = more likely contains object)
        # Select tiles with variance above median, or top N tiles
        if tile_data:
            if all('variance' in td for td in tile_data.values()):
                variances = [td['variance'] for td in tile_data.values()]
                median_var = sorted(variances)[len(variances)//2]
                threshold = max(median_var * 0.8, 500)  # Lower threshold for better recall
                clicks = []
                for t in tile_info:
                    src = t.get('bgUrl', '')
                    idx = t.get('idx', -1)
                    if src in tile_data and idx >= 0:
                        td = tile_data[src]
                        if td['variance'] > threshold:
                            clicks.append(idx)
                if clicks:
                    print(f"  [captcha] Selected {len(clicks)} tiles (threshold={threshold:.0f}, median={median_var:.0f})")
                    return {'clicks': clicks[:8]}
                else:
                    # Fallback: click all tiles
                    all_idx = [t.get('idx', -1) for t in tile_info if t.get('idx', -1) >= 0]
                    if all_idx:
                        print(f"  [captcha] No tiles above threshold — clicking all {len(all_idx)}")
                        return {'clicks': all_idx[:8]}

            if all('size' in td for td in tile_data.values()):
                sizes = [td['size'] for td in tile_data.values()]
                median_size = sorted(sizes)[len(sizes)//2]
                clicks = []
                for t in tile_info:
                    src = t.get('bgUrl', '')
                    if src in tile_data and t.get('idx', -1) >= 0:
                        if tile_data[src]['size'] > median_size * 0.9:
                            clicks.append(t['idx'])
                if clicks:
                    return {'clicks': clicks[:8]}

    except Exception as e:
        print(f"  [captcha] Tile analysis error: {e}")

    return None


def _click_tiles(bframe, tile_indices):
    """Click specified tiles in the reCAPTCHA visual challenge."""
    for idx in tile_indices:
        try:
            # Try multiple selectors for the tile
            for sel in [f'td[id="{idx}"]', f'#{idx}', f'.rc-imageselect-tile[id="{idx}"]']:
                tile = bframe.locator(sel)
                if tile.count() > 0:
                    tile.first.click()
                    time.sleep(random.uniform(0.2, 0.6))
                    break
        except Exception:
            pass


def _check_recaptcha_solved(page):
    """Check if reCAPTCHA has been solved."""
    try:
        resp = page.evaluate("""() => {
            const el = document.getElementById('g-recaptcha-response');
            return el ? el.value : null;
        }""")
        if resp and len(resp) > 50:
            return True
    except Exception:
        pass
    for frame in list(page.frames):
        try:
            if frame.locator('.recaptcha-checkbox-checked').count() > 0:
                return True
        except Exception:
            pass
    return False


def _reset_recaptcha(page):
    """Reset reCAPTCHA widget to clear rate-limit state."""
    try:
        page.evaluate("""() => {
            if (typeof grecaptcha !== 'undefined' && grecaptcha.reset) {
                grecaptcha.reset();
            }
        }""")
        print("  [captcha] Reset reCAPTCHA widget")
    except Exception:
        pass


def solve_recaptcha_audio(page, timeout=120):
    """
    Solve reCAPTCHA v2 — visual-first heuristic solver.
    Always re-scans frames after every interaction.
    """
    print("  [captcha] Detected reCAPTCHA — solving...")
    deadline = time.time() + timeout

    # Install route-level interception for audio payload (backup)
    global _payload_captured
    _payload_captured = None
    route_installed = False
    try:
        page.route("**/recaptcha/api2/payload*", _route_payload_handler)
        route_installed = True
    except Exception:
        pass

    # Wait for bframe to appear
    for _ in range(15):
        if _get_bframe_info(page) is not None:
            break
        page.wait_for_timeout(2000)

    # Primary: visual challenge solver
    if _solve_visual_challenge(page, timeout=max(30, deadline - time.time())):
        return True

    # Fallback: audio mode (likely rate-limited)
    info = _get_bframe_info(page)
    if info and info.get('hasAudioBtn') and not info.get('isError'):
        print("  [captcha] Visual failed — trying audio mode...")
        _bframe_click(page, '#recaptcha-audio-button')
        page.wait_for_timeout(6000)

        info = _get_bframe_info(page)
        if info and info.get('isAudio'):
            audio_data, source = _poll_for_audio_elements(page, 'bframe', timeout=12)
            if audio_data:
                text = _decode_and_transcribe(audio_data)
                if text and _submit_audio_response(page, text):
                    if _check_recaptcha_solved(page):
                        return True
        elif info and info.get('isError'):
            print("  [captcha] Audio blocked by Google")

    if route_installed:
        try:
            page.unroute("**/recaptcha/api2/payload*", _route_payload_handler)
        except Exception:
            pass

    if _check_recaptcha_solved(page):
        print("  [captcha] ✅ reCAPTCHA solved!")
        return True

    print("  [captcha] ⚠️  Solver exhausted — CAPTCHA unsolved")
    return False


def _submit_audio_response(page, text):
    """Fill audio response and click verify. Returns True if submitted."""
    page.wait_for_timeout(1000)
    for frame in list(page.frames):
        try:
            inp = frame.locator('#audio-response')
            if inp.count() > 0 and inp.first.is_visible():
                inp.first.fill(text)
                print(f"  [captcha] ✓ Filled answer: {text}")
                page.wait_for_timeout(500)
                verify = frame.locator('#recaptcha-verify-button')
                if verify.count() > 0:
                    verify.first.click()
                    page.wait_for_timeout(2500)
                return True
        except Exception:
            continue
    return False


def _decode_and_transcribe(audio_data):
    """Decode audio bytes and transcribe via Google Speech Recognition. Returns text or None."""
    import tempfile, subprocess, io as io_mod
    try:
        import speech_recognition as sr
    except ImportError:
        print("  [captcha] speech_recognition not installed — trying raw approach")
        return _transcribe_raw(audio_data)

    mp3_path = tempfile.mktemp(suffix='.mp3')
    wav_path = tempfile.mktemp(suffix='.wav')

    try:
        with open(mp3_path, 'wb') as f:
            f.write(audio_data)

        wav_data = None
        # Try miniaudio first
        try:
            import miniaudio
            decoded = miniaudio.decode_file(mp3_path)
            import wave
            with wave.open(wav_path, 'wb') as wf:
                wf.setnchannels(decoded.nchannels)
                wf.setsampwidth(2)
                wf.setframerate(decoded.sample_rate)
                wf.writeframes(decoded.samples.tobytes())
            with open(wav_path, 'rb') as f:
                wav_data = f.read()
        except Exception as me:
            print(f"  [captcha] miniaudio: {me}, trying ffmpeg...")

        if not wav_data:
            try:
                subprocess.run(['ffmpeg', '-y', '-i', mp3_path, '-acodec', 'pcm_s16le',
                               '-ac', '1', '-ar', '16000', wav_path],
                               capture_output=True, timeout=15)
                with open(wav_path, 'rb') as f:
                    wav_data = f.read()
            except Exception:
                wav_data = None

        if not wav_data:
            audio_file = io_mod.BytesIO(audio_data)
        else:
            audio_file = io_mod.BytesIO(wav_data)
            print(f"  [captcha] ✓ Audio decoded ({len(wav_data)} bytes)")

        recognizer = sr.Recognizer()
        with sr.AudioFile(audio_file) as source:
            audio = recognizer.record(source)

        try:
            text = recognizer.recognize_google(audio)
            return text
        except sr.UnknownValueError:
            try:
                return recognizer.recognize_sphinx(audio)
            except Exception:
                pass
    except Exception as e:
        print(f"  [captcha] Decode/transcribe error: {e}")
    finally:
        for p in [mp3_path, wav_path]:
            try:
                os.unlink(p)
            except Exception:
                pass

    return _transcribe_raw(audio_data)


def _transcribe_raw(audio_data):
    """Fallback: send raw audio to Google's speech API."""
    try:
        encoded = base64.b64encode(audio_data).decode()
        req = urllib.request.Request(
            'https://www.google.com/speech-api/v2/recognize?output=json&lang=en-us&key=AIzaSyBOti4mM-6x9WDnZIjIeyEU21OpBXqWBgw',
            data=audio_data,
            headers={'Content-Type': 'audio/l16; rate=16000'}
        )
        with urllib.request.urlopen(req, timeout=15) as r:
            result = r.read().decode()
            nums = re.findall(r'"transcript":"([^"]+)"', result)
            if nums:
                return nums[0].strip()
    except Exception as e:
        print(f"  [captcha] Raw STT error: {e}")
    return None


def _solve_recaptcha_capsolver(page, timeout=120):
    """Solve reCAPTCHA v2/v3 using Capsolver API (paid service, ~$0.50/1000 solves)."""
    api_key = os.environ.get('CAPSOLVER_API_KEY', '').strip()
    if not api_key:
        return None  # Not configured

    try:
        import capsolver
    except ImportError:
        print("  [capsolver] Package not installed. Run: pip3 install capsolver")
        return None

    print("  [capsolver] Solving with Capsolver API...")

    # Extract sitekey from page
    sitekey = None
    try:
        sitekey = page.evaluate("""() => {
            // Check DOM
            const el = document.querySelector('[data-sitekey]');
            if (el) return el.getAttribute('data-sitekey');
            // Check grecaptcha config
            if (typeof ___grecaptcha_cfg !== 'undefined') {
                for (const cid in ___grecaptcha_cfg.clients || {}) {
                    const cfg = ___grecaptcha_cfg.clients[cid];
                    if (cfg.O && cfg.O.O && cfg.O.O.sitekey) return cfg.O.O.sitekey;
                }
            }
            // Check scripts
            const scripts = document.querySelectorAll('script[src*="recaptcha"]');
            for (const s of scripts) {
                const m = s.src.match(/[?&]k=([^&]+)/);
                if (m) return m[1];
            }
            return null;
        }""")
    except Exception:
        pass

    if not sitekey:
        print("  [capsolver] Could not extract sitekey")
        return None

    print(f"  [capsolver] Sitekey: {sitekey}")
    page_url = page.url

    capsolver.api_key = api_key

    try:
        result = capsolver.solve({
            "type": "ReCaptchaV2TaskProxyless",
            "websiteURL": page_url,
            "websiteKey": sitekey,
        })
        token = result.get('gRecaptchaResponse') or result.get('token') or ''
    except Exception as e:
        print(f"  [capsolver] Solve error: {e}")
        return None

    if not token or len(token) < 100:
        print(f"  [capsolver] Invalid token received: {token[:50] if token else 'none'}")
        return None

    print(f"  [capsolver] ✓ Token received ({len(token)} chars)")

    # Inject token and fire callback
    try:
        page.evaluate(f"""(token) => {{
            const el = document.getElementById('g-recaptcha-response');
            if (el) el.value = token;
            if (typeof ___grecaptcha_cfg !== 'undefined') {{
                for (const cid in ___grecaptcha_cfg.clients || {{}}) {{
                    const client = ___grecaptcha_cfg.clients[cid];
                    if (client.callback) {{
                        client.callback(token);
                        return;
                    }}
                }}
            }}
            // Fallback: dispatch events on the recaptcha element
            const widgets = document.querySelectorAll('.g-recaptcha, [data-sitekey]');
            widgets.forEach(w => {{
                w.dispatchEvent(new Event('submit', {{ bubbles: true }}));
            }});
        }}""", token)
        print("  [capsolver] ✓ Token injected + callback fired")
        page.wait_for_timeout(2000)
        return True
    except Exception as e:
        print(f"  [capsolver] Token injection error: {e}")
        return None


def detect_and_solve_captcha(page, timeout=60, headed=False):
    """Detect and solve any CAPTCHA on the page."""
    if headed:
        return detect_and_pause_for_captcha(page, "unknown", timeout)
    print("  [captcha] Scanning for CAPTCHA...")
    page.wait_for_timeout(2000)

    try:
        body = page.content().lower()
    except:
        body = ""

    # reCAPTCHA
    if 'recaptcha' in body or 'g-recaptcha' in body:
        print("  [captcha] Detected: reCAPTCHA")
        # Try Capsolver first if API key is set
        capsolver_result = _solve_recaptcha_capsolver(page, timeout)
        if capsolver_result is True:
            return True
        elif capsolver_result is False:
            pass  # Capsolver failed, fall through
        # Fall back to free audio/visual bypass
        return solve_recaptcha_audio(page, timeout)

    # hCaptcha
    if 'hcaptcha' in body or 'h-captcha' in body:
        print("  [captcha] Detected: hCaptcha")
        return _solve_hcaptcha(page, timeout)

    # Cloudflare Turnstile
    if 'turnstile' in body or 'challenges.cloudflare.com' in body:
        print("  [captcha] Detected: Cloudflare Turnstile — attempting click")
        try:
            page.locator('iframe[src*="turnstile"]').first.click()
            page.wait_for_timeout(3000)
            return True
        except: pass

    print("  [captcha] No CAPTCHA detected on page")
    return True  # No CAPTCHA = success


def _solve_hcaptcha(page, timeout=90):
    """Try to bypass hCaptcha."""
    print("  [captcha] hCaptcha bypass not yet fully automated — trying checkbox click")
    try:
        for frame in page.frames:
            if "hcaptcha" in frame.url:
                cb = frame.locator('#checkbox')
                if cb.count() > 0:
                    cb.first.click()
                    page.wait_for_timeout(3000)
                    return True
    except: pass
    return False


# ============================================================================
# UTILITIES
# ============================================================================
def fetch_otp(since_iso, timeout=240, subject_filter=None):
    """Poll mail.tm for new verification emails."""
    deadline = time.time() + timeout
    print(f"  [otp] Polling mail.tm for OTP (timeout {timeout}s)...")
    last_status = 0
    while time.time() < deadline:
        try:
            req = urllib.request.Request("https://api.mail.tm/messages?page=1",
                headers={"Authorization": f"Bearer {TOKEN}"})
            with urllib.request.urlopen(req, timeout=10) as r:
                msgs = json.loads(r.read()).get("hydra:member") or []
            for m in msgs:
                subj = (m.get("subject") or "").lower()
                sender = (m.get("from") or {}).get("address", "").lower()
                if m.get("createdAt", "") <= since_iso:
                    continue
                if subject_filter and not any(w in subj for w in subject_filter):
                    continue
                req2 = urllib.request.Request(f"https://api.mail.tm/messages/{m['id']}",
                    headers={"Authorization": f"Bearer {TOKEN}"})
                with urllib.request.urlopen(req2, timeout=10) as r2:
                    full = json.loads(r2.read())
                body = (full.get("text") or "") + " " + " ".join(full.get("html") or [])
                # Try 6-digit code
                match = re.search(r'\b(\d{6})\b', body)
                if match:
                    print(f"  [otp] ✓ 6-digit OTP from {sender}: {match.group(1)}")
                    return match.group(1)
                # Try 4-8 digit
                match = re.search(r'\b(\d{4,8})\b', body)
                if match:
                    print(f"  [otp] ✓ {len(match.group(1))}-digit code: {match.group(1)}")
                    return match.group(1)
                # Try confirmation link
                link_match = re.search(r'https?://[^\s"<>]+(?:confirm|verify|activate)[^\s"<>]+', body)
                if link_match:
                    print(f"  [otp] ✓ Confirmation link from {sender}")
                    return link_match.group(0)
                # Any useful link
                link_match = re.search(r'https?://[^\s"<>]{10,}', body)
                if link_match:
                    url = link_match.group(0).rstrip('.')
                    if 'pixel' not in url and 'track' not in url:
                        print(f"  [otp] ✓ Link from {sender}: {url[:80]}...")
                        return url
        except Exception as e:
            pass
        if time.time() - last_status > 15:
            print(f"  [otp] Still waiting... ({int(deadline - time.time())}s left)")
            last_status = time.time()
        time.sleep(3)
    return None


def mask(s, head=6, tail=4):
    s = str(s or "")
    if len(s) <= head + tail: return "*" * len(s)
    return f"{s[:head]}...{s[-tail:]}"


def update_env(updates: dict):
    content = ENV_FILE.read_text() if ENV_FILE.exists() else ""
    for k, v in updates.items():
        if not v: continue
        pat = re.compile(rf"^{re.escape(k)}=.*$", re.MULTILINE)
        if pat.search(content):
            content = pat.sub(f"{k}={v}", content)
        else:
            content += f"\n# {k.split('_')[0].upper()}\n{k}={v}\n"
    ENV_FILE.write_text(content)
    print(f"  [env] Updated {len(updates)} keys")


def shot(page, name: str):
    try:
        page.screenshot(path=str(SHOTS / f"{name}.png"), full_page=True)
    except: pass


def extract_keys_from_page(page, gw_id: str) -> dict:
    """Universal key extractor: scan inputs, text content, and spans for API keys."""
    gw = GATEWAYS[gw_id]
    result = {}

    # Click "Create API Key" / "Generate" buttons first
    for btn_text in ['Create', 'Generate', 'Add', 'New', 'Create key', 'Generate key', 'Add key',
                      'Create API', 'New API', 'API key']:
        try:
            btn = page.locator(f'button:has-text("{btn_text}"), a:has-text("{btn_text}")')
            if btn.count() > 0:
                btn.first.click()
                page.wait_for_timeout(3000)
                print(f"  [extract] Clicked '{btn_text}' button")
                break
        except: pass

    # Method 1: Read input values
    try:
        for el in page.query_selector_all('input'):
            try:
                v = (el.get_attribute("value") or el.input_value() or "").strip()
                if len(v) < 16: continue
                label = (el.get_attribute("aria-label") or el.get_attribute("placeholder") or
                        el.get_attribute("name") or "").lower()
                if "api" in label and "key" in label and "secret" not in label:
                    if "API_KEY" not in result: result["API_KEY"] = v
                elif ("secret" in label or "private" in label):
                    if "SECRET" not in result: result["SECRET"] = v
                elif "token" in label:
                    if "TOKEN" not in result: result["TOKEN"] = v
                elif "password" in label:
                    if "SECRET" not in result: result["SECRET"] = v
            except: pass
    except: pass

    # Method 2: Scan visible text
    try:
        text = page.inner_text("body")
        uuids = re.findall(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", text)
        hex_keys = re.findall(r"\b[0-9a-f]{32,}\b", text, re.I)
        long_strs = re.findall(r"\b[A-Za-z0-9+/=_-]{32,}\b", text)

        for u in uuids:
            if "API_KEY" not in result: result["API_KEY"] = u
        for h in hex_keys:
            if "SECRET" not in result: result["SECRET"] = h
        for s in long_strs:
            if s.startswith("sk_") and "SECRET" not in result:
                result["SECRET"] = s
            elif s.startswith("pk_") and "API_KEY" not in result:
                result["API_KEY"] = s
    except: pass

    # Method 3: Look in spans/divs/code blocks
    try:
        for cls in ['api-key', 'secret-key', 'key-value', 'credential', 'key', 'token']:
            for el in page.query_selector_all(f'[class*="{cls}" i], code, pre, .key-display'):
                try:
                    v = el.text_content().strip()
                    if len(v) < 16: continue
                    if "key" in cls and "secret" not in cls and "API_KEY" not in result:
                        result["API_KEY"] = v
                    elif ("secret" in cls or "private" in cls) and "SECRET" not in result:
                        result["SECRET"] = v
                except: pass
    except: pass

    # Map to env names
    mapped = {}
    keys_list = gw["env_keys"]
    if len(keys_list) >= 1 and result.get("API_KEY"):
        mapped[keys_list[0]] = result["API_KEY"]
    if len(keys_list) >= 2 and result.get("SECRET"):
        mapped[keys_list[1]] = result["SECRET"]
    mapped[gw["env_var"]] = "production"

    if not mapped or len(mapped) <= 1:
        for k, v in result.items():
            if k not in mapped: mapped[k] = v

    return mapped


# ============================================================================
# STEALTH SETUP
# ============================================================================
def setup_stealth_context(browser):
    """Create a context with anti-detection measures."""
    context = browser.new_context(
        viewport={"width": 1440, "height": 900},
        user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        locale="en-US",
        timezone_id="Asia/Dubai",
    )

    page = context.new_page()
    page.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', { get: () => false });
        Object.defineProperty(navigator, 'languages', { get: () => ['en-US', 'en'] });
    """)
    page.set_default_timeout(30000)

    return context, page


# ============================================================================
# MANUAL CAPTCHA PAUSE (headed mode)
# ============================================================================
def detect_and_pause_for_captcha(page, gw_id: str, timeout=120):
    """Detect CAPTCHA and pause for manual solving by the user."""
    print("  [captcha] Scanning for CAPTCHA...")
    page.wait_for_timeout(2000)

    try:
        body = page.content().lower()
    except:
        body = ""

    captcha_type = None
    if 'recaptcha' in body or 'g-recaptcha' in body:
        captcha_type = "reCAPTCHA"
    elif 'hcaptcha' in body or 'h-captcha' in body:
        captcha_type = "hCaptcha"
    elif 'turnstile' in body or 'challenges.cloudflare.com' in body:
        captcha_type = "Cloudflare Turnstile"

    if captcha_type:
        print(f"\n  {'='*60}")
        print(f"  ⏸️  {captcha_type} DETECTED — PLEASE SOLVE MANUALLY")
        print(f"  The browser window is open. Solve the CAPTCHA now.")
        print(f"  Waiting for CAPTCHA to be solved...")
        print(f"  {'='*60}\n")
        deadline = time.time() + timeout
        while time.time() < deadline:
            time.sleep(2)
            try:
                body = page.content().lower()
                # Check if reCAPTCHA is solved
                if 'recaptcha' in body or 'g-recaptcha' in body:
                    solved = page.evaluate("""() => {
                        const el = document.getElementById('g-recaptcha-response');
                        return el ? el.value : null;
                    }""")
                    if solved and len(solved) > 50:
                        print("  [captcha] ✅ reCAPTCHA solved!")
                        return True
                    # Check for green checkmark
                    try:
                        for frame in page.frames:
                            checked = frame.locator('.recaptcha-checkbox-checked')
                            if checked.count() > 0:
                                print("  [captcha] ✅ reCAPTCHA solved (green check)!")
                                return True
                    except: pass
                elif 'hcaptcha' in body:
                    try:
                        for frame in page.frames:
                            if "hcaptcha" in frame.url:
                                checked = frame.locator('#checkbox.checkbox-checked, .checkbox-checked')
                                if checked.count() > 0:
                                    print("  [captcha] ✅ hCaptcha solved!")
                                    return True
                    except: pass
                elif 'turnstile' in body:
                    # Turnstile may auto-pass or require interaction
                    if 'challenges.cloudflare.com' not in body:
                        print("  [captcha] ✅ Turnstile passed!")
                        return True
                else:
                    # CAPTCHA element disappeared = solved
                    print("  [captcha] ✅ CAPTCHA element gone — solved!")
                    return True
            except: pass
            if time.time() % 20 < 2:
                remaining = int(deadline - time.time())
                print(f"  [captcha] Still waiting... ({remaining}s remaining)")
        print("  [captcha] ⚠️  CAPTCHA wait timed out")
        return False
    else:
        print("  [captcha] No CAPTCHA detected on page")
        return True


# ============================================================================
# LOGIN FLOW — for gateways where account already exists
# ============================================================================
def do_login(page, gw_id: str, gw: dict, headed: bool = False) -> bool:
    """Log into an existing account. Returns True if dashboard reached."""
    login_url = gw.get("login_url")
    if not login_url:
        print(f"  [login] No login URL configured for {gw_id}")
        return False

    print(f"  [login] Switching to login flow → {login_url}")
    try:
        page.goto(login_url, wait_until="networkidle", timeout=30000)
    except PlaywrightTimeout:
        print("  [login] Login page load timeout, continuing...")
    page.wait_for_timeout(4000)
    shot(page, f"{gw_id}_login_01_page")

    # Fill email
    email_filled = False
    for sel in [gw["email_field"], 'input[type="email"]', 'input[name="email"]']:
        try:
            el = page.query_selector(sel)
            if el and el.is_visible():
                el.fill(EMAIL)
                print(f"  [login] ✓ Filled email")
                email_filled = True
                break
        except: pass

    # Fill password
    try:
        els = page.query_selector_all(gw.get("password_field", 'input[type="password"]'))
        if len(els) >= 1 and els[0].is_visible():
            els[0].fill(PASSWORD)
            print("  [login] ✓ Filled password")
    except: pass

    shot(page, f"{gw_id}_login_02_filled")

    # Solve CAPTCHA on login page
    detect_and_solve_captcha(page, timeout=60, headed=headed)

    # Click login/submit
    clicked = False
    for sel in ['button:has-text("Log in")', 'button:has-text("Login")',
                'button:has-text("Sign in")', 'button:has-text("Sign In")',
                'button[type="submit"]', 'input[type="submit"]',
                'button:has-text("Next step")', 'button:has-text("Continue")',
                'button:has-text("Submit")']:
        try:
            btn = page.query_selector(sel)
            if btn and btn.is_visible():
                btn.click()
                print(f"  [login] ✓ Clicked '{sel}'")
                clicked = True
                break
        except: pass

    if not clicked:
        try:
            page.keyboard.press("Enter")
            print("  [login] Pressed Enter")
        except: pass

    page.wait_for_timeout(3000)

    # Check for CAPTCHA that appeared after login submit
    try:
        body = page.content().lower()
        if 'recaptcha' in body or 'hcaptcha' in body:
            print("  [login] CAPTCHA appeared after login submit — solving...")
            detect_and_solve_captcha(page, timeout=60, headed=headed)
            page.wait_for_timeout(2000)
    except: pass

    page.wait_for_timeout(4000)

    # Check for 2FA / OTP on login
    try:
        body = page.content().lower()
        if any(w in body for w in ['2fa', 'two-factor', 'authenticator', 'otp', 'verification code',
                                      'one-time', 'security code']):
            print("  [login] 2FA/OTP screen detected — checking mail.tm...")
            login_start = datetime.now(timezone.utc).isoformat()
            otp = fetch_otp(login_start, timeout=120,
                           subject_filter=["code", "verify", "login", "2fa", gw["name"].lower()[:5]])
            if otp:
                if otp.startswith("http"):
                    try:
                        page.goto(otp, wait_until="networkidle", timeout=15000)
                        page.wait_for_timeout(3000)
                    except: pass
                else:
                    for otp_sel in ['input[autocomplete="one-time-code"]', 'input[name="code"]',
                                   'input[name="otp"]', 'input[placeholder*="code" i]',
                                   'input[type="text"]']:
                        try:
                            el = page.query_selector(otp_sel)
                            if el and el.is_visible():
                                el.fill(otp)
                                print(f"  [login] ✓ Filled OTP: {otp}")
                                page.keyboard.press("Enter")
                                page.wait_for_timeout(3000)
                                break
                        except: pass
    except: pass

    page.wait_for_timeout(4000)
    shot(page, f"{gw_id}_login_03_post")

    # Check if we reached dashboard
    url = page.url.lower()
    dash_indicator = gw.get("dashboard_indicator", "/dashboard")
    # URLs that indicate we're still on login/signup pages (not dashboard)
    fail_indicators = ['/sign-in', '/login', '/signup', '/register', '/create-account']
    is_fail = any(fi in url for fi in fail_indicators)
    
    if not is_fail and (dash_indicator in url or "account" in url or "settings" in url or "profile" in url):
        print(f"  [login] ✅ Login successful → {url}")
        return True

    # Wait a bit more
    deadline = time.time() + 30
    while time.time() < deadline:
        url = page.url.lower()
        is_fail = any(fi in url for fi in fail_indicators)
        if not is_fail and (dash_indicator in url or "account" in url or "settings" in url):
            print(f"  [login] ✅ Dashboard reached: {url}")
            return True
        time.sleep(2)

    print(f"  [login] ⚠️  Not sure if login succeeded (URL: {url})")
    return (not is_fail) and (dash_indicator in url or "account" in url or "settings" in url)


def detect_account_exists(page) -> bool:
    """Check if page indicates account already registered."""
    try:
        body = page.content().lower()
        indicators = [
            'already registered', 'already exists', 'account already',
            'email already', 'already have an account', 'user already',
            'already taken', 'email is already', 'account with this email',
            'log in instead', 'login instead', 'sign in instead',
            'already in use', 'email address is already',
        ]
        for ind in indicators:
            if ind in body:
                print(f"  [detect] Account exists indicator: '{ind}'")
                return True

        # Also check for redirect to login page
        url = page.url.lower()
        if '/login' in url or '/signin' in url or 'sign-in' in url:
            print(f"  [detect] Redirected to login: {url}")
            return True
    except:
        pass
    return False


# ============================================================================
# MAIN GRAB FLOW
# ============================================================================
def grab_gateway(gw_id: str, page, force_login: bool = False, headed: bool = False) -> dict:
    """Main headless grab flow for one gateway."""
    gw = GATEWAYS[gw_id]

    print(f"\n{'='*70}")
    print(f"  🔑 GRABBING: {gw['name']} ({gw_id})")
    print(f"{'='*70}")

    signup_start = datetime.now(timezone.utc).isoformat()

    # If --login flag, go straight to login
    if force_login and gw.get("login_url"):
        print(f"  🔄 Force login mode — skipping signup")
        do_login(page, gw_id, gw, headed=headed)
    else:
        # Step 1: Navigate to signup
        print(f"  → {gw['signup_url']}")
        try:
            page.goto(gw["signup_url"], wait_until="networkidle", timeout=30000)
        except PlaywrightTimeout:
            print("  ⚠️  Initial load timeout, continuing...")
        page.wait_for_timeout(4000)
        shot(page, f"{gw_id}_01_signup")

        # Step 2: Fill email
        email_filled = False
        for sel in [gw["email_field"], 'input[type="email"]', 'input[name="email"]']:
            try:
                el = page.query_selector(sel)
                if el and el.is_visible():
                    el.fill(EMAIL)
                    print(f"  ✓ Filled email: {EMAIL}")
                    email_filled = True
                    break
            except: pass
        if not email_filled:
            print("  ⚠️  Could not find email field")

        # Step 3: Fill password
        if gw.get("password_field"):
            try:
                els = page.query_selector_all(gw["password_field"])
                if len(els) >= 1 and els[0].is_visible():
                    els[0].fill(PASSWORD)
                    print("  ✓ Filled password")
                    if gw.get("confirm_password_field") and len(els) >= 2:
                        try:
                            els[1].fill(PASSWORD)
                            print("  ✓ Filled confirm password")
                        except: pass
            except: pass

        # Step 4.5: Check consent checkboxes (Terms of Service, etc.)
        try:
            # Click labels associated with terms/agreement checkboxes
            for label_text in ['accept the Terms', 'I accept', 'I agree', 'Terms of Service',
                              'Privacy Policy', 'terms', 'agree']:
                label = page.locator(f'label:has-text("{label_text}")')
                if label.count() > 0:
                    # Check if the associated checkbox is unchecked
                    cb_id = label.first.get_attribute('for') or ''
                    if cb_id:
                        cb = page.locator(f'#{cb_id}')
                        if cb.count() > 0 and not cb.first.is_checked():
                            label.first.click()
                            print(f"  ✓ Accepted: {label_text}")
                            page.wait_for_timeout(200)
                    else:
                        label.first.click()
                        print(f"  ✓ Clicked label: {label_text}")
                        page.wait_for_timeout(200)
        except Exception as e:
            print(f"  ⚠️  Terms acceptance: {e}")

        # Step 5: Fill any other fields (first name, last name, company)
        for field_sel, value in [
            ('input[name*="first" i], input[placeholder*="first" i]', 'Sicher'),
            ('input[name*="last" i], input[placeholder*="last" i]', 'Mayor'),
            ('input[name*="company" i], input[placeholder*="company" i]', 'CryptoEx FZE'),
            ('input[name*="name" i], input[placeholder*="name" i]', 'Sicher Mayor'),
            ('input[name*="phone" i], input[placeholder*="phone" i]', '971501234567'),
        ]:
            try:
                el = page.query_selector(field_sel)
                if el and el.is_visible():
                    el.fill(value)
                    print(f"  ✓ Filled extra field: {value}")
            except: pass

        shot(page, f"{gw_id}_02_prefill")

        # Step 5: Detect and solve CAPTCHA (audio bypass via miniaudio)
        captcha_ok = detect_and_solve_captcha(page, timeout=90, headed=headed)

        # Step 6: Click submit
        submit_clicked = False
        for sel in [gw["submit_button"], 'button[type="submit"]', 'input[type="submit"]',
                    'button:has-text("Sign up")', 'button:has-text("Register")',
                    'button:has-text("Create")', 'button:has-text("Submit")',
                    'button:has-text("Continue")', 'button:has-text("Next")',
                    'a:has-text("Sign up")', 'a:has-text("Register")']:
            try:
                btn = page.query_selector(sel)
                if btn and btn.is_visible():
                    btn.click()
                    print(f"  ✓ Clicked submit")
                    submit_clicked = True
                    break
            except: pass

        if not submit_clicked:
            print("  ⚠️  Could not click submit — trying enter key")
            try: page.keyboard.press("Enter")
            except: pass

        page.wait_for_timeout(3000)

        # Check for CAPTCHA that appeared after submit (invisible reCAPTCHA)
        try:
            body = page.content().lower()
            if 'recaptcha' in body or 'hcaptcha' in body:
                print("  [captcha] CAPTCHA appeared after submit — solving...")
                detect_and_solve_captcha(page, timeout=60, headed=headed)
                page.wait_for_timeout(2000)
        except: pass

        # Check if account already exists → switch to login
        if detect_account_exists(page):
            print("  🔄 Account already exists — switching to login flow")
            if gw.get("login_url"):
                do_login(page, gw_id, gw, headed=headed)

        # Step 7: Wait for OTP or dashboard
        current_url = page.url.lower()
        already_logged_in = gw["dashboard_indicator"] in current_url or "account" in current_url or "settings" in current_url

        if not already_logged_in:
            print("  ⏳ Waiting for OTP screen or dashboard...")
            deadline = time.time() + 300
            while time.time() < deadline:
                url = page.url.lower()
                if gw["dashboard_indicator"] in url:
                    print(f"  ✓ Dashboard reached: {url}")
                    break

                # Check for OTP screen
                try:
                    otp_sel = gw.get("otp_screen_selector", 'input[autocomplete="one-time-code"]')
                    otp_el = page.query_selector(otp_sel)
                    if otp_el and otp_el.is_visible():
                        print("  ✓ OTP screen detected! Fetching from mail.tm...")
                        otp = fetch_otp(signup_start, timeout=180,
                                       subject_filter=["verify", "confirm", "code", gw["name"].lower()[:5]])
                        if otp:
                            if otp.startswith("http"):
                                print(f"  → Following confirmation link")
                                try:
                                    page.goto(otp, wait_until="networkidle", timeout=15000)
                                    page.wait_for_timeout(5000)
                                except: pass
                            else:
                                try:
                                    els = page.query_selector_all(otp_sel)
                                    if len(els) >= 6:
                                        for i, d in enumerate(otp[:6]):
                                            els[i].fill(d)
                                    else:
                                        els[0].fill(otp)
                                    print(f"  ✓ OTP filled")
                                    for b_sel in ['button:has-text("Verify")', 'button:has-text("Submit")',
                                                 'button:has-text("Confirm")', 'button[type="submit"]']:
                                        try:
                                            btn = page.query_selector(b_sel)
                                            if btn and btn.is_visible():
                                                btn.click()
                                                break
                                        except: pass
                                except Exception as e:
                                    print(f"  ✗ OTP fill error: {e}")
                        break
                except: pass

                # Check for CAPTCHAs that appeared after submit
                if time.time() % 15 < 2:
                    try:
                        if 'recaptcha' in page.content().lower():
                            detect_and_solve_captcha(page, timeout=30, headed=headed)
                    except: pass

                time.sleep(2)

            shot(page, f"{gw_id}_03_post_login")
        print(f"  📍 URL: {page.url}")
        page.wait_for_timeout(3000)

        # Post-signup sanity: if still on signup/login page, try login
        current_url = page.url.lower()
        still_on_signup = any(w in current_url for w in ['/create-account', '/signup', '/register', '/login', '/sign-in', '/signin'])
        if still_on_signup and gw.get("login_url"):
            print("  🔄 Still on signup page after submit — trying login instead")
            do_login(page, gw_id, gw, headed=headed)

    # Step 8: Navigate to API keys page
    if gw.get("api_keys_url"):
        print(f"  → Navigating to API keys: {gw['api_keys_url']}")
        try:
            page.goto(gw["api_keys_url"], wait_until="networkidle", timeout=15000)
            page.wait_for_timeout(5000)
        except:
            print("  ⚠️  API keys page not accessible, trying current page")
        shot(page, f"{gw_id}_04_api_keys")

    # Step 9: Extract keys
    print("  🔍 Extracting keys...")
    keys = extract_keys_from_page(page, gw_id)

    if keys and len(keys) > 1:
        print("  ✅ Found keys:")
        for k, v in keys.items():
            print(f"     {k} = {mask(v)}")

        update_env(keys)

        stash = ROOT / f".{gw_id}_keys.json"
        stash.write_text(json.dumps(keys, indent=2))
        stash.chmod(0o600)
        print(f"  💾 Stashed: .{gw_id}_keys.json")
    else:
        print(f"  ⚠️  Could not extract keys automatically")
        print(f"  Manual fix: python3 gateway_agents_activate.py --activate {gw_id}")
        shot(page, f"{gw_id}_05_no_keys")

    return keys

# ============================================================================
# MAIN
# ============================================================================

def main():
    args = [a.lower() for a in sys.argv[1:]]

    # Check for flags
    force_login = False
    headed_mode = False
    for flag in ["--login", "--headed"]:
        if flag in args:
            if flag == "--login":
                force_login = True
            elif flag == "--headed":
                headed_mode = True
            args.remove(flag)

    if not args or "all" in args:
        targets = list(GATEWAYS.keys())
    else:
        targets = [a for a in args if a in GATEWAYS]

    if not targets:
        print("Available:", ", ".join(GATEWAYS.keys()))
        return

    print(f"\n🚀 MULTI-GATEWAY GRAB — {len(targets)} gateway(s)")
    print(f"   Email: {EMAIL}")
    mode_parts = []
    if headed_mode: mode_parts.append("HEADED (visible browser)")
    else: mode_parts.append("HEADLESS")
    if force_login: mode_parts.append("LOGIN")
    else: mode_parts.append("signup first")
    print(f"   Mode: {' + '.join(mode_parts)}")
    print(f"   CAPTCHA: {'Manual (user solves in browser)' if headed_mode else 'Auto-bypass enabled'}")
    print()

    with sync_playwright() as p:
        results = {}

        for gw_id in targets:
            try:
                if headed_mode:
                    browser = p.chromium.launch(
                        headless=False,
                        args=['--no-sandbox', '--disable-blink-features=AutomationControlled'],
                    )
                    context = browser.new_context(
                        viewport={"width": 1440, "height": 900},
                        user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
                        locale="en-US", timezone_id="Asia/Dubai",
                    )
                    page = context.new_page()
                    page.set_default_timeout(30000)
                else:
                    browser = p.chromium.launch(
                        headless=True,
                        args=['--no-sandbox', '--disable-setuid-sandbox',
                              '--disable-blink-features=AutomationControlled'],
                    )
                    context, page = setup_stealth_context(browser)

                keys = grab_gateway(gw_id, page, force_login=force_login, headed=headed_mode)
                results[gw_id] = keys

                context.close()
                browser.close()

                print(f"\n  ✅ {GATEWAYS[gw_id]['name']} grab complete\n")
            except Exception as e:
                import traceback
                print(f"  ❌ {gw_id} failed: {type(e).__name__}: {e}")
                traceback.print_exc()
                try:
                    shot(page, f"{gw_id}_99_error")
                    context.close()
                    browser.close()
                except: pass

    # Summary
    print(f"\n{'='*70}")
    print(f"  📊 SUMMARY")
    print(f"{'='*70}")
    for gw_id, keys in results.items():
        status = "✅ LIVE" if (keys and len(keys) > 1) else "❌ FAILED"
        print(f"  {status}  {GATEWAYS[gw_id]['name']:20s}  {mask(str(keys))}")
    print(f"\n  Check .env for new keys")
    print(f"  Verify: python3 gateway_agents_activate.py --verify")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()

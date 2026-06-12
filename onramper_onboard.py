#!/usr/bin/env python3
"""Complete Onramper onboarding: signup → check Gmail IMAP → set password → dashboard

Email: homoeokurikkal0@gmail.com
IMAP: reads SMTP_USERNAME / SMTP_PASSWORD from .env (Gmail app password required)
"""
from playwright.sync_api import sync_playwright
import email, imaplib, json, os, re, socket, time
from email.header import decode_header
from datetime import datetime, timezone, timedelta

ENV_PATH = os.path.join(os.path.dirname(__file__), ".env")

# ── Onramper account (already created & active) ──
EMAIL = "homoeokurikkal0@gmail.com"
PASSWORD = "Qwerty@1239895"
# Testing API Key: pk_test_01KS8WZQB3570H0RDCNJ8JYX8E
# Signing Secret:   ba0f9ac3c70e76daf81547751334a408a95e239f876f75f8e5a63391dcdb77f7
# Production Key:   PENDING (support@onramper.com ticket submitted 2026-06-06)

# ── env loader ──────────────────────────────────────────────────
def load_env(path):
    try:
        with open(path, "r", encoding="utf-8") as handle:
            for raw_line in handle:
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                if key in {"SMTP_USERNAME", "SMTP_PASSWORD"}:
                    os.environ.setdefault(key, value.strip().strip('"').strip("'"))
    except FileNotFoundError:
        pass

def decode_val(value):
    parts = []
    for part, enc in decode_header(value or ""):
        if isinstance(part, bytes):
            parts.append(part.decode(enc or "utf-8", "replace"))
        else:
            parts.append(part)
    return "".join(parts)

def imap_quote(value):
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'

# ── email waiter (Gmail IMAP) ───────────────────────────────────
def wait_for_email(since_iso, timeout=180):
    """Poll Gmail IMAP for an Onramper confirmation link sent since *since_iso*."""
    load_env(ENV_PATH)
    imap_user = os.environ.get("SMTP_USERNAME", "")
    imap_pass = os.environ.get("SMTP_PASSWORD", "")

    if not imap_user or not imap_pass:
        print("   ⚠ No SMTP_USERNAME / SMTP_PASSWORD in .env → cannot read email")
        print(f"   Check inbox manually: {EMAIL}")
        return None

    socket.setdefaulttimeout(45)
    client = imaplib.IMAP4_SSL("imap.gmail.com", 993)
    client.login(imap_user, imap_pass)
    deadline = time.time() + timeout

    # Build a Gmail raw search: after the signup date, plus Onramper keywords
    since_date = (datetime.fromisoformat(since_iso) - timedelta(hours=1)).strftime("%Y/%m/%d")
    raw_query = f'after:{since_date} (onramper OR dashboard.onramper.com)'

    print(f"   IMAP user: {imap_user}")
    print(f"   Search:    {raw_query}")

    seen_ids = set()

    while time.time() < deadline:
        try:
            client.select("INBOX", readonly=True)
            typ, data = client.uid("SEARCH", "X-GM-RAW", imap_quote(raw_query))
            if typ != "OK" or not data or not data[0]:
                time.sleep(5)
                continue

            uids = data[0].split()
            for uid_b in reversed(uids):
                uid = uid_b.decode()
                if uid in seen_ids:
                    continue
                seen_ids.add(uid)

                _, fetched = client.uid("FETCH", uid, "(BODY.PEEK[])")
                if not fetched or not isinstance(fetched[0], tuple):
                    continue
                msg = email.message_from_bytes(fetched[0][1])
                subj = (decode_val(msg.get("Subject")) or "").lower()
                frm = decode_val(msg.get("From")) or ""
                date_str = decode_val(msg.get("Date")) or ""
                print(f"   Email: [{date_str[:25]}] {frm[:50]} | {subj[:80]}")

                # Extract body text
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        ctype = part.get_content_type()
                        if ctype in ("text/plain", "text/html"):
                            payload = part.get_payload(decode=True)
                            if payload:
                                body += payload.decode("utf-8", "replace") + " "
                else:
                    payload = msg.get_payload(decode=True)
                    if payload:
                        body = payload.decode("utf-8", "replace")

                link = re.search(r'https?://[^\s"<>]+confirmation[^\s"<>]+', body)
                if link:
                    client.logout()
                    return link.group(0)
            time.sleep(5)
        except Exception as e:
            print(f"   IMAP error: {e}")
            time.sleep(5)

    try:
        client.logout()
    except:
        pass
    return None

# ── main flow ───────────────────────────────────────────────────
with sync_playwright() as p:
    browser = p.firefox.launch(headless=True)
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    page = ctx.new_page()

    # STEP 1: Sign up
    print("1. Signing up...")
    signup_ts = datetime.now(timezone.utc).isoformat()
    page.goto("https://dashboard.onramper.com/users/sign_up", wait_until="domcontentloaded", timeout=15000)
    page.wait_for_timeout(3000)

    page.fill('input[name="user[first_name]"]', "Sicher")
    page.fill('input[name="user[last_name]"]', "Mayor")
    page.fill('input[name="user[email]"]', EMAIL)
    try:
        cb = page.locator('input[type="checkbox"]')
        if cb.count() > 0 and not cb.first.is_checked():
            cb.first.click()
    except:
        pass
    page.locator('input[type="submit"]').click(timeout=5000)
    page.wait_for_timeout(5000)
    print(f"   → {page.url}")

    # STEP 2: Get confirmation link from Gmail IMAP
    print("2. Waiting for confirmation email...")
    conf_url = wait_for_email(signup_ts)
    if not conf_url:
        print("   ❌ No confirmation email")
        browser.close()
        exit(1)
    print(f"   ✓ {conf_url[:120]}")

    # STEP 3: Click confirmation link
    print("3. Confirming email...")
    page.goto(conf_url, wait_until="domcontentloaded", timeout=15000)
    page.wait_for_timeout(5000)
    print(f"   → {page.url}")
    text = page.inner_text("body")[:400]
    print(f"   {text[:200]}")

    # STEP 4: Set password
    if "password" in text.lower():
        print("4. Setting password...")
        pw_fields = page.query_selector_all('input[type="password"]')
        if len(pw_fields) >= 2:
            pw_fields[0].fill(PASSWORD)
            pw_fields[1].fill(PASSWORD)
            page.locator('input[type="submit"]').click(timeout=5000)
            page.wait_for_timeout(8000)
            print(f"   → {page.url}")
        else:
            print(f"   ⚠ Found {len(pw_fields)} password fields")
    else:
        print("   ℹ No password screen — may already be logged in")

    # STEP 5: Check if we're in the dashboard
    text = page.inner_text("body")[:600]
    if "sign_in" in page.url or "sign_up" in page.url:
        print("5. Need to log in manually...")
        page.goto("https://dashboard.onramper.com/users/sign_in", wait_until="domcontentloaded", timeout=15000)
        page.wait_for_timeout(3000)
        page.fill('input[name="user[email]"]', EMAIL)
        page.fill('input[name="user[password]"]', PASSWORD)
        page.locator('input[type="submit"]').click(timeout=5000)
        page.wait_for_timeout(8000)
        print(f"   Login → {page.url}")
    else:
        print(f"5. In dashboard: {page.url}")

    # FINAL: Show what we see
    text = page.inner_text("body")[:600]
    print(f"\nFINAL PAGE: {page.url}")
    print(f"{text[:500]}")

    # Look for API keys / projects / request live keys
    nav = page.evaluate("""() => {
        const r = [];
        for (const el of document.querySelectorAll('a, button, h1, h2, h3')) {
            const t = el.textContent.trim().slice(0, 70);
            const h = el.href || '';
            if (t.length > 2 && t.length < 70) r.push(t + (h ? ' | ' + h.slice(0, 80) : ''));
        }
        return [...new Set(r)].slice(0, 35);
    }""")

    if any(
        kw in item.lower()
        for item in nav
        for kw in ("api", "key", "project", "live")
    ):
        print("\n✅ FOUND API/PROJECT LINKS:")
        for item in nav:
            if any(kw in item.lower() for kw in ("api", "key", "project", "live")):
                print(f"  ⭐ {item}")
    else:
        print("\nDashboard content:")
        for item in nav:
            print(f"  {item}")

    page.screenshot(path="/tmp/onramper_complete.png")
    browser.close()
    print("\n✅ Done")

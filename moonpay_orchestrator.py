#!/usr/bin/env python3
"""
MoonPay auto-activation orchestrator (OpenClaw + Unsloth)

Pipeline:
  1. signup   — open the MoonPay business signup page in browser, drop SICHER
                MAYOR INVESTMENTS LLC data onto the clipboard for fast paste,
                list KYB docs from the GCS bucket.
  2. watch    — IMAP-poll the Gmail inbox for MoonPay emails; when one with
                production credentials lands, extract the live key.
  3. extract  — call the Unsloth flexible-schema endpoint (Gemini) to pull
                pk_live_… and whsec_… out of an arbitrary email body.
  4. deploy   — gcloud run services update beastpay-api with the new key.
  5. run      — chain steps 2→3→4 forever until a live key is found and
                deployed; reports status via Telegram + log file.

The human-review step at MoonPay (1–5 business days) cannot be automated.
Everything around it can.

Usage:
  python3 moonpay_orchestrator.py signup
  python3 moonpay_orchestrator.py watch
  python3 moonpay_orchestrator.py extract  < /path/to/email.txt
  python3 moonpay_orchestrator.py deploy pk_live_abc whsec_xyz
  python3 moonpay_orchestrator.py run
"""
from __future__ import annotations
import os
import re
import sys
import json
import time
import email
import imaplib
import logging
import subprocess
import urllib.parse
import webbrowser
from email.header import decode_header
from datetime import datetime, timedelta

import requests

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("moonpay")

# Try to load .env if present (CLI use)
try:
    from dotenv import load_dotenv  # noqa: F401
    load_dotenv()
except Exception:
    pass

# ---------------------------------------------------------------------------
SICHER_MAYOR = {
    # Source: memory/sicher_mayor_investments_new_entity.md
    "company_name": "SICHER MAYOR INVESTMENTS L.L.C",
    "registration_number": "1324297",
    "ded_license": "DED-1324297",
    "country": "United Arab Emirates",
    "city": "Dubai",
    "company_type": "LLC",
    "ubo_first_name": "Shajahan",
    "ubo_last_name": "Pisharikkattukandiyil",
    "company_email": os.getenv("TRANSAK_EMAIL") or "sichermayor@wshu.net",
    "support_email": "digifol83@gmail.com",
    "website": "https://beastpay-api-544494288390.us-central1.run.app",
}

GCS_BUCKET = "beastpay-kyb-cs-poc-lym2gfaa9781su2yqiz25fq"
GCS_DOCS_PREFIX = "uploads/"

MOONPAY_SIGNUP_URL = "https://buy.moonpay.com/sign-up?utm_source=beastpay"
MOONPAY_DASHBOARD = "https://dashboard.moonpay.com"

UNSLOTH_URL = os.getenv("UNSLOTH_KYC_URL", "https://unsloth-kyc-544494288390.us-central1.run.app")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "933545457")

IMAP_HOST = "imap.gmail.com"
IMAP_USER = os.getenv("SMTP_USERNAME", "digifol83@gmail.com")
IMAP_PASS = os.getenv("SMTP_PASSWORD", "")

STATE_FILE = "/tmp/moonpay_orchestrator.json"

# ---------------------------------------------------------------------------
def _state_read() -> dict:
    try:
        with open(STATE_FILE) as f:
            return json.load(f)
    except Exception:
        return {"stage": "init"}


def _state_write(d: dict) -> None:
    d["updated_at"] = datetime.utcnow().isoformat()
    with open(STATE_FILE, "w") as f:
        json.dump(d, f, indent=2)


def _telegram(msg: str) -> None:
    if not TELEGRAM_BOT_TOKEN:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
            json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"},
            timeout=8,
        )
    except Exception:
        pass


# ---------------------------------------------------------------------------
# 1. Signup — open browser, populate clipboard, list GCS docs
# ---------------------------------------------------------------------------
def cmd_signup() -> int:
    print("\n=== MoonPay Business Signup ===\n")
    print(f"Company:         {SICHER_MAYOR['company_name']}")
    print(f"DED licence:     {SICHER_MAYOR['ded_license']}")
    print(f"Reg number:      {SICHER_MAYOR['registration_number']}")
    print(f"UBO:             {SICHER_MAYOR['ubo_first_name']} {SICHER_MAYOR['ubo_last_name']}")
    print(f"Country / City:  {SICHER_MAYOR['country']} / {SICHER_MAYOR['city']}")
    print(f"Company email:   {SICHER_MAYOR['company_email']}")
    print(f"Support email:   {SICHER_MAYOR['support_email']}")
    print(f"Website:         {SICHER_MAYOR['website']}")
    print()

    # Build clipboard chunks the user can paste sequentially.
    clipboard_chunks = [
        SICHER_MAYOR["company_name"],
        SICHER_MAYOR["registration_number"],
        SICHER_MAYOR["ded_license"],
        SICHER_MAYOR["company_email"],
        SICHER_MAYOR["website"],
        f"{SICHER_MAYOR['ubo_first_name']} {SICHER_MAYOR['ubo_last_name']}",
    ]
    try:
        # Best-effort clipboard set — wl-copy (Wayland), xclip (X), pbcopy (mac)
        first = clipboard_chunks[0]
        for cmd in (["wl-copy"], ["xclip", "-selection", "clipboard"], ["pbcopy"]):
            try:
                subprocess.run(cmd, input=first.encode(), check=True, timeout=2)
                print(f"📋 Clipboard primed with: {first!r}")
                break
            except Exception:
                continue
    except Exception:
        pass

    # List KYB docs from GCS (for upload prompts)
    print("\n📂 KYB documents available in GCS:")
    try:
        out = subprocess.check_output(
            ["gsutil", "ls", f"gs://{GCS_BUCKET}/{GCS_DOCS_PREFIX}"],
            text=True, timeout=15,
        )
        for line in out.strip().splitlines():
            print(f"  {line}")
    except subprocess.CalledProcessError:
        print("  (could not list GCS bucket — check gcloud auth)")
    except Exception as e:
        print(f"  (skipped: {e})")

    print(f"\n🌐 Opening: {MOONPAY_SIGNUP_URL}")
    try:
        webbrowser.open(MOONPAY_SIGNUP_URL)
    except Exception:
        pass

    print("\n👉 Complete the form in your browser. SICHER MAYOR data above.")
    print("👉 When approved, MoonPay emails the pk_live_ key to:", IMAP_USER)
    print("👉 Then run:  python3 moonpay_orchestrator.py watch")

    _state_write({"stage": "signup_submitted", "company": SICHER_MAYOR["company_name"]})
    _telegram(f"🟡 MoonPay signup opened for {SICHER_MAYOR['company_name']} — awaiting approval email at {IMAP_USER}.")
    return 0


# ---------------------------------------------------------------------------
# 3. Extract — call Unsloth /extract-fields for arbitrary text
# ---------------------------------------------------------------------------
KEY_FIELDS = {
    "publishable_key":    "MoonPay publishable API key starting with pk_live_",
    "webhook_secret":     "MoonPay webhook signing secret starting with whsec_ or wh_",
    "dashboard_url":      "URL to the MoonPay merchant dashboard",
    "support_contact":    "MoonPay support email or contact mentioned in the message",
}


def extract_keys_from_text(text: str) -> dict:
    """Try Unsloth /extract-fields first; fall back to regex if it errors."""
    out = {"publishable_key": None, "webhook_secret": None,
           "dashboard_url": None, "support_contact": None, "source": None}

    # Unsloth path (LLM via research-api/Gemini)
    try:
        r = requests.post(
            f"{UNSLOTH_URL}/extract-fields",
            json={"text": text, "fields": KEY_FIELDS},
            timeout=45,
        )
        if r.ok:
            data = r.json().get("data", {})
            for k in out:
                if k in data and data[k]:
                    out[k] = data[k]
            out["source"] = "unsloth-kyc"
    except Exception as e:
        log.warning(f"unsloth-kyc extract failed: {e}")

    # Regex fallback / cross-check (always run; LLMs occasionally swap keys)
    pk = re.search(r"pk_live_[A-Za-z0-9_]{16,}", text)
    if pk:
        out["publishable_key"] = pk.group(0)
    wh = re.search(r"(?:whsec|wh_live)_[A-Za-z0-9_-]{16,}", text)
    if wh:
        out["webhook_secret"] = wh.group(0)
    if not out["source"]:
        out["source"] = "regex"
    return out


def cmd_extract() -> int:
    text = sys.stdin.read()
    if not text.strip():
        print("Pipe email text on stdin.", file=sys.stderr)
        return 2
    result = extract_keys_from_text(text)
    print(json.dumps(result, indent=2))
    return 0 if result.get("publishable_key") else 1


# ---------------------------------------------------------------------------
# 2. Watch — IMAP poll Gmail for MoonPay emails
# ---------------------------------------------------------------------------
def _imap_fetch_recent_moonpay(days_back: int = 7) -> list[tuple[str, str]]:
    """Return [(subject, body), …] from MoonPay sender within window."""
    if not IMAP_PASS:
        raise RuntimeError("SMTP_PASSWORD not set — needed for Gmail IMAP")
    M = imaplib.IMAP4_SSL(IMAP_HOST)
    M.login(IMAP_USER, IMAP_PASS)
    M.select("INBOX")
    since = (datetime.utcnow() - timedelta(days=days_back)).strftime("%d-%b-%Y")
    typ, data = M.search(None, f'(SINCE {since} FROM "moonpay.com")')
    out = []
    if typ == "OK":
        for num in data[0].split():
            try:
                typ, fetch = M.fetch(num, "(RFC822)")
                msg = email.message_from_bytes(fetch[0][1])
                subj_raw = msg.get("Subject") or ""
                subj = "".join(
                    (p.decode(enc or "utf-8", errors="replace") if isinstance(p, bytes) else p)
                    for p, enc in decode_header(subj_raw)
                )
                body = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        ctype = part.get_content_type()
                        if ctype in ("text/plain", "text/html"):
                            payload = part.get_payload(decode=True) or b""
                            body += payload.decode(part.get_content_charset() or "utf-8",
                                                   errors="replace") + "\n"
                else:
                    payload = msg.get_payload(decode=True) or b""
                    body = payload.decode(msg.get_content_charset() or "utf-8",
                                          errors="replace")
                out.append((subj, body))
            except Exception as e:
                log.warning(f"fetch_failed_for_msg {num}: {e}")
    M.logout()
    return out


def cmd_watch(loop: bool = True) -> int:
    log.info("watching gmail for moonpay emails (Ctrl-C to stop)")
    while True:
        try:
            msgs = _imap_fetch_recent_moonpay(days_back=14)
            log.info(f"found {len(msgs)} moonpay messages")
            for subj, body in msgs:
                if "pk_live_" in body or "pk_live_" in subj:
                    log.info(f"approval candidate: {subj!r}")
                    keys = extract_keys_from_text(subj + "\n\n" + body)
                    if keys.get("publishable_key"):
                        _state_write({"stage": "key_found", "subject": subj, **keys})
                        _telegram(
                            f"🟢 MoonPay live key found in inbox!\n"
                            f"Subject: {subj}\n"
                            f"Key: `{keys['publishable_key'][:14]}…`\n"
                            f"Source: {keys.get('source')}\n"
                            f"Auto-deploying…"
                        )
                        return cmd_deploy(keys["publishable_key"],
                                          keys.get("webhook_secret") or "")
        except Exception as e:
            log.exception(f"watch_iteration_failed: {e}")
        if not loop:
            break
        time.sleep(300)  # 5 minutes — Gmail rate-friendly
    return 0


# ---------------------------------------------------------------------------
# 4. Deploy — push new key to Cloud Run
# ---------------------------------------------------------------------------
def cmd_deploy(pk_live: str, webhook_secret: str = "") -> int:
    if not pk_live.startswith("pk_live_"):
        log.error(f"refusing to deploy non-live key: {pk_live[:14]}")
        return 2
    log.info(f"deploying MOONPAY_API_KEY={pk_live[:14]}… to beastpay-api")
    env_pairs = [f"MOONPAY_API_KEY={pk_live}", "MOONPAY_ENV=production"]
    if webhook_secret:
        env_pairs.append(f"MOONPAY_WEBHOOK_SECRET={webhook_secret}")
    cmd = [
        "gcloud", "run", "services", "update", "beastpay-api",
        "--region", "us-central1",
        f"--update-env-vars={','.join(env_pairs)}",
        "--quiet",
    ]
    try:
        out = subprocess.check_output(cmd, stderr=subprocess.STDOUT,
                                      text=True, timeout=600)
        log.info("deploy ok")
        rev = re.search(r"revision \[([^\]]+)\]", out)
        revision = rev.group(1) if rev else "unknown"
        _state_write({"stage": "deployed", "publishable_key_prefix": pk_live[:14],
                      "revision": revision})
        _telegram(f"✅ MoonPay LIVE on `{revision}`. Picker now offers production MoonPay.")
        print(f"deployed revision: {revision}")
        return 0
    except subprocess.CalledProcessError as e:
        log.error(f"gcloud deploy failed: {e.output}")
        _telegram(f"❌ MoonPay deploy failed: {e.output[:300]}")
        return 1


# ---------------------------------------------------------------------------
# 5. run — chain watch → extract → deploy
# ---------------------------------------------------------------------------
def cmd_run() -> int:
    state = _state_read()
    log.info(f"current state: {state.get('stage')}")
    if state.get("stage") == "deployed":
        log.info("already deployed; nothing to do")
        return 0
    return cmd_watch(loop=True)


# ---------------------------------------------------------------------------
def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    cmd = sys.argv[1]
    if cmd == "signup":
        return cmd_signup()
    if cmd == "watch":
        return cmd_watch(loop=False)
    if cmd == "extract":
        return cmd_extract()
    if cmd == "deploy":
        if len(sys.argv) < 3:
            print("Usage: deploy <pk_live_…> [whsec_…]", file=sys.stderr); return 2
        return cmd_deploy(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "")
    if cmd == "run":
        return cmd_run()
    if cmd == "state":
        print(json.dumps(_state_read(), indent=2)); return 0
    print(__doc__); return 2


if __name__ == "__main__":
    sys.exit(main())

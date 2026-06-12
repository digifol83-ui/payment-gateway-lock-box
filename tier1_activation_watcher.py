#!/usr/bin/env python3
"""
Watch temp-mail inbox for Tier 1 gateway API keys and auto-activate.
Monitors: NOWPayments, Plisio, CoinRemitter
Runs activate_live.sh for each as keys arrive.
"""
import json
import re
import time
import subprocess
from pathlib import Path
import urllib.request
import sys

EMAIL = "sichermayor@deltajohnsons.com"
SESSION_FILE = Path("/home/kali/payment-gateway/.tempmail_session.json")

# Gateway patterns: (gateway_name, key_pattern, regex_group)
GATEWAYS = {
    'nowpayments': {
        'from_pattern': 'nowpayments',
        'key_pattern': r'API[_-]?Key[:\s]*([a-f0-9]{32,})',
        'activated': False,
    },
    'plisio': {
        'from_pattern': 'plisio',
        'key_pattern': r'Secret[_-]?Key[:\s]*([a-f0-9]{32,})',
        'activated': False,
    },
    'coinremitter': {
        'from_pattern': 'coinremitter',
        'key_pattern': r'API[_-]?Key[:\s]*([a-f0-9]{32,})',
        'activated': False,
    },
}


def get_token():
    if not SESSION_FILE.exists():
        print("❌ .tempmail_session.json not found. Run temp_mail_listener.py first.")
        sys.exit(1)
    return json.loads(SESSION_FILE.read_text()).get("token")


def fetch_messages(token: str) -> list:
    try:
        req = urllib.request.Request(
            "https://api.mail.tm/messages?page=1",
            headers={"Authorization": f"Bearer {token}"},
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read())
            return data.get("hydra:member") or data.get("member") or []
    except Exception as e:
        print(f"⚠️  fetch_messages error: {e}")
        return []


def get_message_body(token: str, msg_id: str) -> str:
    try:
        req = urllib.request.Request(
            f"https://api.mail.tm/messages/{msg_id}",
            headers={"Authorization": f"Bearer {token}"},
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            full = json.loads(r.read())
            text = full.get("text") or ""
            html = full.get("html") or []
            return text + " ".join(html)
    except Exception:
        return ""


def extract_key(body: str, pattern: str) -> str | None:
    match = re.search(pattern, body, re.IGNORECASE)
    return match.group(1) if match else None


def activate_gateway(gateway: str, api_key: str) -> bool:
    """Run activate_live.sh <gateway> <key>"""
    try:
        result = subprocess.run(
            ["bash", "activate_live.sh", gateway, api_key],
            cwd="/home/kali/payment-gateway",
            capture_output=True,
            timeout=30,
        )
        if result.returncode == 0:
            print(f"✅ {gateway.upper()} activated with key: {api_key[:16]}...")
            return True
        else:
            print(f"❌ {gateway.upper()} activation failed: {result.stderr.decode()}")
            return False
    except Exception as e:
        print(f"❌ {gateway.upper()} activation error: {e}")
        return False


def main():
    print("\n" + "=" * 70)
    print("🔍 TIER 1 GATEWAY ACTIVATION WATCHER")
    print("=" * 70)
    print(f"📧 Email: {EMAIL}")
    print(f"⏱️  Watching for: NOWPayments, Plisio, CoinRemitter")
    print(f"🔗 Ctrl+C to stop\n")

    token = get_token()
    seen_msg_ids = set()
    last_check = time.time()

    while True:
        try:
            messages = fetch_messages(token)
            now = time.time()

            for msg in messages:
                msg_id = msg.get("id")
                if msg_id in seen_msg_ids:
                    continue

                seen_msg_ids.add(msg_id)
                sender = (msg.get("from") or {}).get("address", "").lower()
                subject = (msg.get("subject") or "").lower()
                created_at = msg.get("createdAt", "")

                # Skip if older than 2 minutes
                try:
                    from datetime import datetime
                    ts = datetime.fromisoformat(created_at.replace("Z", "+00:00")).timestamp()
                    if now - ts > 120:
                        continue
                except:
                    pass

                body = get_message_body(token, msg_id)

                # Check each gateway
                for gw_name, gw_cfg in GATEWAYS.items():
                    if gw_cfg['activated']:
                        continue

                    if gw_cfg['from_pattern'] in sender or gw_cfg['from_pattern'] in subject:
                        api_key = extract_key(body, gw_cfg['key_pattern'])
                        if api_key:
                            print(f"\n🎉 Found {gw_name.upper()} API key in {sender}")
                            print(f"   Subject: {subject}")
                            if activate_gateway(gw_name, api_key):
                                gw_cfg['activated'] = True
                            print()

            # Check if all activated
            if all(cfg['activated'] for cfg in GATEWAYS.values()):
                print("\n✅ All Tier 1 gateways activated!")
                return

            time.sleep(10)

        except KeyboardInterrupt:
            print("\n\n⏹️  Stopped.")
            break
        except Exception as e:
            print(f"⚠️  Error: {e}")
            time.sleep(10)


if __name__ == "__main__":
    main()

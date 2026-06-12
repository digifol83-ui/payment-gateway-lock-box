#!/usr/bin/env python3
"""
TEMP MAIL OTP LISTENER — mail.tm REST API integration

Creates a temporary email at @deltajohnsons.com (looks like a real company),
then polls for incoming OTP/verification emails.

Usage:
  python3 temp_mail_listener.py            # create account
  python3 temp_mail_listener.py status     # check messages
  python3 temp_mail_listener.py watch      # poll continuously
"""
import os
import sys
import json
import time
import secrets
import re
import urllib.request
import urllib.error
from pathlib import Path

ROOT = Path('/home/kali/payment-gateway')
SESSION_FILE = ROOT / '.tempmail_session.json'
API = 'https://api.mail.tm'


def http(method, path, headers=None, data=None):
    url = f'{API}{path}'
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(
        url, data=body, method=method,
        headers={'Content-Type': 'application/json', **(headers or {})}
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            text = resp.read().decode()
            return resp.status, json.loads(text) if text else {}
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode()) if e.code != 204 else {}


def get_domain():
    status, body = http('GET', '/domains')
    domains = body.get('hydra:member', [])
    if not domains:
        return None
    return domains[0]['domain']


def create_account(username):
    domain = get_domain()
    if not domain:
        return None
    address = f'{username}@{domain}'
    password = secrets.token_urlsafe(16)

    status, body = http('POST', '/accounts', data={
        'address': address,
        'password': password,
    })
    if status not in (200, 201):
        return {'error': f'HTTP {status}: {body}'}

    # Get auth token
    status, body = http('POST', '/token', data={
        'address': address,
        'password': password,
    })
    if status not in (200, 201):
        return {'error': f'Token HTTP {status}: {body}'}

    return {
        'address': address,
        'password': password,
        'token': body.get('token'),
        'account_id': body.get('id'),
        'domain': domain,
    }


def list_messages(token):
    status, body = http('GET', '/messages',
                        headers={'Authorization': f'Bearer {token}'})
    if status != 200:
        return []
    return body.get('hydra:member', [])


def get_message(token, msg_id):
    status, body = http('GET', f'/messages/{msg_id}',
                        headers={'Authorization': f'Bearer {token}'})
    return body if status == 200 else None


def extract_otp(text):
    if not text:
        return None
    patterns = [
        r'(?:code|OTP|verify|verification|PIN)[:\s]+(\d{4,8})',
        r'\b(\d{6})\b',
        r'\b(\d{4,8})\b',
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return m.group(1)
    return None


def status_cmd():
    if not SESSION_FILE.exists():
        print('❌ No session. Run without args first.')
        return

    sess = json.loads(SESSION_FILE.read_text())
    print()
    print('=' * 70)
    print(f'📧  ACTIVE: {sess["address"]}')
    print('=' * 70)
    print()

    msgs = list_messages(sess['token'])
    if not msgs:
        print('   📭 No messages yet')
        print('   Re-run: python3 temp_mail_listener.py status')
        return

    print(f'   📬 {len(msgs)} message(s):')
    for i, m in enumerate(msgs, 1):
        full = get_message(sess['token'], m['id'])
        print(f'\n   --- {i} ---')
        print(f'   From:    {m.get("from", {}).get("address", "?")}')
        print(f'   Subject: {m.get("subject", "?")}')
        if full:
            text = full.get('text', '') or full.get('html', [''])[0] if full.get('html') else ''
            otp = extract_otp(text)
            if otp:
                print(f'   🔐 OTP/CODE: {otp}')
            print(f'   Body: {text[:400]}')


def watch_cmd():
    if not SESSION_FILE.exists():
        print('❌ Run without args first to create session')
        return
    sess = json.loads(SESSION_FILE.read_text())
    print(f'\n👀 Watching {sess["address"]} (poll 10s, Ctrl-C to stop)')
    seen = set()
    while True:
        try:
            msgs = list_messages(sess['token'])
            for m in msgs:
                if m['id'] in seen:
                    continue
                seen.add(m['id'])
                full = get_message(sess['token'], m['id'])
                print()
                print(f'📬 NEW EMAIL!')
                print(f'   From:    {m.get("from", {}).get("address", "?")}')
                print(f'   Subject: {m.get("subject", "?")}')
                if full:
                    text = full.get('text', '')
                    otp = extract_otp(text)
                    if otp:
                        print(f'   🔐 OTP DETECTED: {otp}')
                    print(f'   Body: {text[:500]}')
            time.sleep(10)
        except KeyboardInterrupt:
            print('\n👋 Stopped.')
            break
        except Exception as e:
            print(f'   poll err: {e}')
            time.sleep(15)


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'create'

    if cmd == 'status':
        status_cmd()
    elif cmd == 'watch':
        watch_cmd()
    else:
        # Create
        username = sys.argv[2] if len(sys.argv) > 2 else 'sichermayor'
        print(f'\n📧 Creating temp mailbox: {username}@deltajohnsons.com ...')
        result = create_account(username)
        if not result or 'error' in result:
            # Try with random suffix
            username = f'{username}{secrets.token_hex(2)}'
            print(f'   Retrying: {username}@...')
            result = create_account(username)

        if not result or 'error' in result:
            print(f'   ❌ Error: {result}')
            return

        SESSION_FILE.write_text(json.dumps(result, indent=2))
        print()
        print('=' * 70)
        print('✅  TEMPORARY EMAIL READY')
        print('=' * 70)
        print()
        print(f'   📨  USE: {result["address"]}')
        print()
        print('=' * 70)
        print()
        print('🎯 NEXT STEPS:')
        print()
        print(f'   1. Sign up Transak: https://dashboard.transak.com/signup')
        print(f'   2. Email field: {result["address"]}')
        print(f'   3. Submit')
        print(f'   4. Check inbox: python3 temp_mail_listener.py status')
        print(f'   5. Watch live:   python3 temp_mail_listener.py watch')
        print()
        print(f'   Web UI (backup): https://mail.tm')
        print(f'   Login: {result["address"]}')
        print(f'   Password: {result["password"]}')
        print()


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
DROPMAIL OTP LISTENER — One-time Transak Email Bypass

Creates a DropMail temporary email, suggests an address to use for Transak
signup, then polls for incoming OTP/verification emails.

Usage:
  python3 dropmail_otp_listener.py            # create session + start listening
  python3 dropmail_otp_listener.py status     # check session messages
"""
import os
import sys
import json
import time
import secrets
import urllib.request
from pathlib import Path

ROOT = Path('/home/kali/payment-gateway')
SESSION_FILE = ROOT / '.dropmail_session.json'
API = 'https://dropmail.me/api/graphql'


def gql(token, query):
    data = json.dumps({'query': query}).encode()
    req = urllib.request.Request(
        f'{API}/{token}',
        data=data,
        headers={'Content-Type': 'application/json'}
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())


def best_domain_addr(addresses):
    """Pick the most professional-looking address"""
    priority = ['pickmemail.com', 'mailtowin.com', 'maximail.vip', 'maximail.fyi']
    by_domain = {a['address'].split('@')[1]: a['address'] for a in addresses}
    for d in priority:
        if d in by_domain:
            return by_domain[d]
    return addresses[0]['address']


def create_session():
    """Create a new DropMail session and pick the best email"""
    # Try multiple sessions to find a professional-looking domain
    best = None
    attempts = []

    for _ in range(6):
        token = secrets.token_urlsafe(16)
        try:
            result = gql(token, 'mutation { introduceSession { id, expiresAt, addresses { address } } }')
            sess = result.get('data', {}).get('introduceSession')
            if sess:
                for a in sess['addresses']:
                    domain = a['address'].split('@')[1]
                    attempts.append((token, sess, a['address'], domain))
        except Exception:
            continue

    # Sort by domain priority (less disposable-looking first)
    priority = {'pickmemail.com': 0, 'mailtowin.com': 1, 'maximail.vip': 2, 'maximail.fyi': 3}
    attempts.sort(key=lambda x: priority.get(x[3], 99))

    if not attempts:
        print('❌ Could not create DropMail session')
        return None

    best_token, best_sess, best_addr, best_domain = attempts[0]

    payload = {
        'token': best_token,
        'session_id': best_sess['id'],
        'expires_at': best_sess['expiresAt'],
        'address': best_addr,
        'domain': best_domain,
    }

    SESSION_FILE.write_text(json.dumps(payload, indent=2))
    return payload


def poll_messages(token, session_id):
    """Get all messages for a session"""
    query = (
        'query { session(id: "' + session_id + '") '
        '{ mails { headerSubject text fromAddr toAddr } } }'
    )
    result = gql(token, query)
    return result.get('data', {}).get('session', {}).get('mails', [])


def extract_otp(text):
    """Try to extract OTP/verification code from email text"""
    import re
    if not text:
        return None
    # Common patterns: 4-8 digit codes
    patterns = [
        r'(?:code|OTP|verify|verification)[:\s]+(\d{4,8})',
        r'\b(\d{6})\b',
        r'\b(\d{4,8})\b',
    ]
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            return m.group(1)
    return None


def status():
    """Show current session and any received emails"""
    if not SESSION_FILE.exists():
        print('No active session. Run without args to create one.')
        return

    sess = json.loads(SESSION_FILE.read_text())
    print(f'\n📧 Active DropMail session:')
    print(f'   Address:    {sess["address"]}')
    print(f'   Expires:    {sess["expires_at"]}')
    print(f'   Domain:     @{sess["domain"]}')

    print(f'\n📨 Polling for messages...')
    try:
        mails = poll_messages(sess['token'], sess['session_id'])
        if not mails:
            print('   (no messages yet)')
            print(f'   Re-run: python3 dropmail_otp_listener.py status')
            return

        print(f'\n   {len(mails)} message(s) received:')
        for i, m in enumerate(mails, 1):
            print(f'\n   --- Message {i} ---')
            print(f'   From:    {m.get("fromAddr")}')
            print(f'   Subject: {m.get("headerSubject")}')
            text = m.get('text', '')
            otp = extract_otp(text)
            if otp:
                print(f'   🔐 OTP/CODE: {otp}')
            print(f'   Body: {text[:300]}')
    except Exception as e:
        print(f'   ❌ Error: {e}')


def watch():
    """Poll continuously until OTP arrives"""
    if not SESSION_FILE.exists():
        print('Run without "watch" first to create session')
        return
    sess = json.loads(SESSION_FILE.read_text())
    print(f'\n👀 Watching {sess["address"]} for incoming emails...')
    print(f'   (poll every 10s, ctrl-c to stop)')
    seen_count = 0
    while True:
        try:
            mails = poll_messages(sess['token'], sess['session_id'])
            if len(mails) > seen_count:
                for m in mails[seen_count:]:
                    print()
                    print(f'📬 NEW EMAIL!')
                    print(f'   From: {m.get("fromAddr")}')
                    print(f'   Subject: {m.get("headerSubject")}')
                    text = m.get('text', '')
                    otp = extract_otp(text)
                    if otp:
                        print(f'   🔐 OTP DETECTED: {otp}')
                    else:
                        print(f'   Body: {text[:500]}')
                seen_count = len(mails)
            time.sleep(10)
        except KeyboardInterrupt:
            print('\n👋 Stopped watching.')
            break
        except Exception as e:
            print(f'   poll error: {e}')
            time.sleep(15)


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'create'

    if cmd == 'status':
        status()
    elif cmd == 'watch':
        watch()
    else:
        print('\n📧 Creating DropMail session...')
        sess = create_session()
        if not sess:
            return
        print()
        print('=' * 70)
        print('✅ TEMPORARY EMAIL READY')
        print('=' * 70)
        print()
        print(f'   📨 USE THIS EMAIL:  {sess["address"]}')
        print(f'   ⏰ Expires:         {sess["expires_at"]}')
        print()
        print('=' * 70)
        print()
        print('🎯 NEXT STEPS:')
        print()
        print(f'   1. Sign up Transak: https://dashboard.transak.com/signup')
        print(f'   2. Use email: {sess["address"]}')
        print(f'   3. Submit form')
        print()
        print(f'   4. CHECK FOR OTP/VERIFY EMAIL:')
        print(f'      python3 dropmail_otp_listener.py status')
        print()
        print(f'   5. WATCH LIVE:')
        print(f'      python3 dropmail_otp_listener.py watch')
        print()
        print('   ⚠️  If Transak rejects this email, we fall back to RoyalHost.')
        print()


if __name__ == '__main__':
    main()

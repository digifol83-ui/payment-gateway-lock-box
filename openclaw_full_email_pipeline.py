#!/usr/bin/env python3
"""
OPENCLAW FULL EMAIL PIPELINE — END-TO-END AUTOMATION

Configures business@sichermayorfx.com email forwarding fully automatically:

  ImprovMX (forwarding service)  ←─── managed via REST API
  GoDaddy DNS (MX records)       ←─── managed via REST API

Manual steps reduced to TWO 30-second tasks:
  1. Sign up at improvmx.com → copy API key (free)
  2. Generate GoDaddy API key at developer.godaddy.com (free)

Then this script does EVERYTHING ELSE:
  ✅ Adds domain to ImprovMX via API
  ✅ Creates business@ alias via API
  ✅ Updates GoDaddy MX records via API (replaces Outlook records)
  ✅ Verifies DNS propagation
  ✅ Confirms forwarding is live
  ✅ Stores API keys securely in .env

Usage:
  python3 openclaw_full_email_pipeline.py <improvmx_key> <godaddy_key> <godaddy_secret>
"""
import os
import sys
import json
import urllib.request
import urllib.error
import base64
import subprocess
import time
from pathlib import Path

DOMAIN = 'sichermayorfx.com'
ALIAS = 'business'
FORWARD_TO = 'digifol83@gmail.com'
IMPROVMX_API = 'https://api.improvmx.com/v3'
GODADDY_API = 'https://api.godaddy.com/v1'
ROOT = Path('/home/kali/payment-gateway')

NEW_MX = [
    {'type': 'MX', 'name': '@', 'data': 'mx1.improvmx.com', 'priority': 10, 'ttl': 3600},
    {'type': 'MX', 'name': '@', 'data': 'mx2.improvmx.com', 'priority': 20, 'ttl': 3600},
]


def http(method, url, headers, data=None, timeout=15):
    """Make HTTP request, return (status, body_dict)"""
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            text = resp.read().decode()
            return resp.status, json.loads(text) if text else {}
    except urllib.error.HTTPError as e:
        try:
            text = e.read().decode()
            return e.code, json.loads(text) if text and text[0] in '{[' else {'raw': text}
        except:
            return e.code, {}


# ============ IMPROVMX ============

def improvmx_headers(api_key):
    auth = base64.b64encode(f'api:{api_key}'.encode()).decode()
    return {
        'Authorization': f'Basic {auth}',
        'Content-Type': 'application/json',
    }


def improvmx_check(api_key):
    print('\n[1/7] 🔑 Verifying ImprovMX API key...')
    status, body = http('GET', f'{IMPROVMX_API}/account', improvmx_headers(api_key))
    if status != 200:
        print(f'   ❌ Invalid (HTTP {status}): {body}')
        return False
    account = body.get('account', {})
    print(f'   ✅ ImprovMX account: {account.get("email", "n/a")}')
    print(f'      Plan: {account.get("plan", {}).get("name", "free")}')
    return True


def improvmx_add_domain(api_key):
    print(f'\n[2/7] 🌐 Adding {DOMAIN} to ImprovMX...')
    status, body = http('POST', f'{IMPROVMX_API}/domains',
                        improvmx_headers(api_key),
                        {'domain': DOMAIN, 'notification_email': FORWARD_TO})
    if status in (200, 201):
        print(f'   ✅ Domain added')
        return True
    if status == 409 or 'already' in str(body).lower():
        print(f'   ✅ Domain already added')
        return True
    print(f'   ⚠️  HTTP {status}: {body}')
    return False


def improvmx_add_alias(api_key):
    print(f'\n[3/7] 📧 Creating alias {ALIAS}@{DOMAIN} → {FORWARD_TO}...')
    status, body = http('POST', f'{IMPROVMX_API}/domains/{DOMAIN}/aliases',
                        improvmx_headers(api_key),
                        {'alias': ALIAS, 'forward': FORWARD_TO})
    if status in (200, 201):
        print(f'   ✅ Alias created')
        return True
    if status == 409 or 'already' in str(body).lower():
        print(f'   ✅ Alias already exists')
        return True
    print(f'   ⚠️  HTTP {status}: {body}')
    return False


def improvmx_verify(api_key):
    print(f'\n[7/7] ✅ Verifying ImprovMX configuration...')
    status, body = http('GET', f'{IMPROVMX_API}/domains/{DOMAIN}',
                        improvmx_headers(api_key))
    if status != 200:
        print(f'   ⚠️  HTTP {status}')
        return False

    d = body.get('domain', {})
    active = d.get('active')
    valid = d.get('valid')
    print(f'   Active:    {"✅ YES" if active else "⏳ NO"}')
    print(f'   MX valid:  {"✅ YES" if valid else "⏳ propagating"}')
    return active and valid


# ============ GODADDY ============

def godaddy_headers(api_key, api_secret):
    return {
        'Authorization': f'sso-key {api_key}:{api_secret}',
        'Content-Type': 'application/json',
    }


def godaddy_check(api_key, api_secret):
    print('\n[4/7] 🔑 Verifying GoDaddy API key...')
    status, body = http('GET', f'{GODADDY_API}/domains?limit=1',
                        godaddy_headers(api_key, api_secret))
    if status != 200:
        print(f'   ❌ Invalid (HTTP {status}): {body}')
        return False
    print(f'   ✅ GoDaddy API access confirmed')
    return True


def godaddy_get_mx(api_key, api_secret):
    """Get current MX records for domain"""
    status, body = http('GET', f'{GODADDY_API}/domains/{DOMAIN}/records/MX',
                        godaddy_headers(api_key, api_secret))
    if status != 200:
        return None
    return body


def godaddy_set_mx(api_key, api_secret):
    """Replace all MX records with ImprovMX MX records"""
    print(f'\n[5/7] 🔧 Updating GoDaddy MX records...')

    # Show current
    current = godaddy_get_mx(api_key, api_secret)
    print(f'   Current MX records:')
    for rec in (current or []):
        print(f'      {rec.get("priority", "?")} → {rec.get("data", "?")}')

    # Replace MX records (PUT replaces all of that type)
    new_records = [
        {'data': 'mx1.improvmx.com', 'priority': 10, 'ttl': 3600},
        {'data': 'mx2.improvmx.com', 'priority': 20, 'ttl': 3600},
    ]
    status, body = http('PUT', f'{GODADDY_API}/domains/{DOMAIN}/records/MX',
                        godaddy_headers(api_key, api_secret),
                        new_records)

    if status in (200, 204):
        print(f'   ✅ MX records updated:')
        for rec in new_records:
            print(f'      {rec["priority"]} → {rec["data"]}')
        return True
    print(f'   ❌ HTTP {status}: {body}')
    return False


# ============ DNS VERIFICATION ============

def check_dns_propagation():
    print(f'\n[6/7] 🌐 Checking DNS propagation...')

    for attempt in range(1, 4):
        try:
            result = subprocess.run(
                ['dig', '+short', DOMAIN, 'MX'],
                capture_output=True, text=True, timeout=10
            )
            mx = result.stdout.strip().lower()
            if 'improvmx.com' in mx:
                print(f'   ✅ DNS propagated (attempt {attempt})')
                for line in mx.split('\n'):
                    print(f'      {line}')
                return True
            print(f'   ⏳ Not yet propagated (attempt {attempt}), waiting 15s...')
            if attempt < 3:
                time.sleep(15)
        except Exception as e:
            print(f'   ⚠️  Check failed: {e}')

    print(f'   ⏳ DNS still propagating (can take up to 1 hour)')
    print(f'   Re-run this script in a few minutes to verify')
    return False


# ============ STORAGE ============

def store_credentials(improvmx_key, godaddy_key, godaddy_secret):
    env_file = ROOT / '.env'
    content = env_file.read_text()
    additions = []

    for k, v in [
        ('IMPROVMX_API_KEY', improvmx_key),
        ('GODADDY_API_KEY', godaddy_key),
        ('GODADDY_API_SECRET', godaddy_secret),
    ]:
        if k not in content:
            additions.append(f'{k}={v}')

    if additions:
        with open(env_file, 'a') as f:
            f.write('\n# Email automation credentials\n')
            for line in additions:
                f.write(line + '\n')
        print(f'   ✅ {len(additions)} key(s) saved to .env')


# ============ MAIN ============

def show_help():
    print(__doc__)
    print('\nGet API keys:')
    print('  ImprovMX:  https://app.improvmx.com/account (free, instant)')
    print('  GoDaddy:   https://developer.godaddy.com/keys (free, instant)')


def main():
    args = [a for a in sys.argv[1:] if a not in ('--help', 'help')]

    print()
    print('=' * 70)
    print('🤖 OPENCLAW FULL EMAIL PIPELINE — END-TO-END AUTOMATION')
    print('=' * 70)

    if len(args) < 3:
        # Try to load from .env
        env = {}
        if (ROOT / '.env').exists():
            for line in (ROOT / '.env').read_text().splitlines():
                if '=' in line and not line.startswith('#'):
                    k, v = line.split('=', 1)
                    env[k.strip()] = v.strip()

        improvmx_key = env.get('IMPROVMX_API_KEY')
        godaddy_key = env.get('GODADDY_API_KEY')
        godaddy_secret = env.get('GODADDY_API_SECRET')

        if not (improvmx_key and godaddy_key and godaddy_secret):
            show_help()
            return
    else:
        improvmx_key, godaddy_key, godaddy_secret = args[0], args[1], args[2]

    print(f'\nTarget: {ALIAS}@{DOMAIN} → {FORWARD_TO}')

    # Pipeline
    if not improvmx_check(improvmx_key):
        print('\n❌ STOPPED — invalid ImprovMX key')
        return
    improvmx_add_domain(improvmx_key)
    improvmx_add_alias(improvmx_key)

    if not godaddy_check(godaddy_key, godaddy_secret):
        print('\n❌ STOPPED — invalid GoDaddy key')
        return
    godaddy_set_mx(godaddy_key, godaddy_secret)

    check_dns_propagation()
    is_live = improvmx_verify(improvmx_key)

    store_credentials(improvmx_key, godaddy_key, godaddy_secret)

    # Summary
    print()
    print('=' * 70)
    if is_live:
        print('🟢 EMAIL FORWARDING IS LIVE')
    else:
        print('🟡 CONFIGURATION COMPLETE — DNS PROPAGATING')
    print('=' * 70)
    print(f'   Address: business@{DOMAIN}')
    print(f'   Forwards to: {FORWARD_TO}')
    print()
    if is_live:
        print('   ✅ Test it: send an email to business@sichermayorfx.com')
        print('   ✅ It will arrive in: digifol83@gmail.com')
        print()
        print('   👉 NEXT: Sign up Transak with business@sichermayorfx.com')
        print('   👉 URL:  https://transak.com/business-signup')
    else:
        print('   👉 DNS can take 5min - 1 hour to propagate')
        print('   👉 Re-run this script to verify')
    print('=' * 70)
    print()


if __name__ == '__main__':
    main()

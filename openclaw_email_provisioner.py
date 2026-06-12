#!/usr/bin/env python3
"""
OPENCLAW EMAIL PROVISIONER
Automated business email setup via ImprovMX API.

This is the "full potential" of OpenClaw email automation:
- Programmatically configures email forwarding via REST API
- Sets up business@sichermayorfx.com → digifol83@gmail.com
- Verifies MX records
- Reports DNS state and next actions

Manual steps required (cannot be automated):
1. Sign up at improvmx.com (30 seconds - free, no payment)
2. Get API key from dashboard
3. Update GoDaddy DNS (2 MX records)

Once API key is provided, this script does everything else.
"""
import os
import sys
import json
import urllib.request
import urllib.error
import base64
import subprocess
from pathlib import Path

DOMAIN = 'sichermayorfx.com'
ALIAS = 'business'
FORWARD_TO = 'digifol83@gmail.com'
API_BASE = 'https://api.improvmx.com/v3'
ROOT = Path('/home/kali/payment-gateway')


def api_request(method, path, api_key, data=None):
    """Make authenticated request to ImprovMX API"""
    url = f'{API_BASE}{path}'
    auth = base64.b64encode(f'api:{api_key}'.encode()).decode()
    headers = {
        'Authorization': f'Basic {auth}',
        'Content-Type': 'application/json',
    }

    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        try:
            err_body = e.read().decode()
            return {'error': True, 'status': e.code, 'body': err_body}
        except:
            return {'error': True, 'status': e.code}
    except Exception as e:
        return {'error': True, 'message': str(e)}


def step_1_verify_account(api_key):
    """Verify API key works"""
    print('\n[1/5] 🔑 Verifying ImprovMX API key...')
    result = api_request('GET', '/account', api_key)
    if result.get('error'):
        print(f'   ❌ API key invalid: {result}')
        return False
    print(f'   ✅ Account verified')
    if 'account' in result:
        print(f'      Email: {result["account"].get("email", "n/a")}')
        plan = result['account'].get('plan') or {}
        print(f'      Plan:  {plan.get("name", "free")}')
    return True


def step_2_add_domain(api_key):
    """Add sichermayorfx.com to ImprovMX"""
    print(f'\n[2/5] 🌐 Adding domain {DOMAIN}...')
    result = api_request('POST', '/domains', api_key, {
        'domain': DOMAIN,
        'notification_email': FORWARD_TO,
    })

    if result.get('error') and result.get('status') == 409:
        print(f'   ✅ Domain already added')
        return True
    if result.get('error'):
        print(f'   ⚠️  Could not add domain: {result.get("body", result)}')
        return False
    print(f'   ✅ Domain added: {DOMAIN}')
    return True


def step_3_add_alias(api_key):
    """Add business@sichermayorfx.com → digifol83@gmail.com"""
    print(f'\n[3/5] 📧 Adding alias {ALIAS}@{DOMAIN} → {FORWARD_TO}...')
    result = api_request('POST', f'/domains/{DOMAIN}/aliases', api_key, {
        'alias': ALIAS,
        'forward': FORWARD_TO,
    })

    if result.get('error') and result.get('status') == 409:
        print(f'   ✅ Alias already exists')
        return True
    if result.get('error'):
        print(f'   ⚠️  Could not add alias: {result.get("body", result)}')
        return False
    print(f'   ✅ Alias active: {ALIAS}@{DOMAIN} → {FORWARD_TO}')
    return True


def step_4_check_mx_records(api_key):
    """Check if MX records are correctly pointing to ImprovMX"""
    print(f'\n[4/5] 🔍 Checking DNS for MX records...')

    try:
        result = subprocess.run(
            ['dig', '+short', DOMAIN, 'MX'],
            capture_output=True, text=True, timeout=10
        )
        mx_records = result.stdout.strip().lower()

        if 'improvmx.com' in mx_records:
            print(f'   ✅ MX records correctly point to ImprovMX')
            return True
        else:
            print(f'   ⚠️  MX records NOT pointing to ImprovMX yet')
            print(f'   Current: {mx_records or "(none)"}')
            print()
            print('   👉 ADD THESE MX RECORDS IN GODADDY:')
            print('      ┌─────────┬──────────────────────┬──────┐')
            print('      │ Type    │ Value                │ Priority │')
            print('      ├─────────┼──────────────────────┼──────┤')
            print('      │ MX      │ mx1.improvmx.com     │ 10   │')
            print('      │ MX      │ mx2.improvmx.com     │ 20   │')
            print('      └─────────┴──────────────────────┴──────┘')
            print()
            print(f'   GoDaddy DNS panel: https://dcc.godaddy.com/manage/{DOMAIN}/dns')
            print('   IMPORTANT: Delete existing Outlook MX records first.')
            return False
    except Exception as e:
        print(f'   ❌ DNS check failed: {e}')
        return False


def step_5_verify_via_api(api_key):
    """Use ImprovMX API to verify domain configuration"""
    print(f'\n[5/5] ✅ Verifying via ImprovMX API...')
    result = api_request('GET', f'/domains/{DOMAIN}', api_key)

    if result.get('error'):
        print(f'   ⚠️  Could not verify: {result}')
        return False

    domain_data = result.get('domain', {})
    active = domain_data.get('active')
    mx_valid = domain_data.get('valid')

    print(f'   Active:    {"✅" if active else "⏳"}')
    print(f'   MX valid:  {"✅" if mx_valid else "⏳ (DNS propagating)"}')

    if active and mx_valid:
        print()
        print('   🟢 EMAIL FORWARDING IS LIVE')
        print(f'   Test it: send email to business@{DOMAIN}')
        print(f'   It will appear in: {FORWARD_TO}')
        return True
    return False


def store_api_key(api_key):
    """Save ImprovMX API key to .env"""
    env_file = ROOT / '.env'
    content = env_file.read_text()
    if 'IMPROVMX_API_KEY' not in content:
        content += f'\n# Email forwarding\nIMPROVMX_API_KEY={api_key}\n'
        env_file.write_text(content)
        print(f'   ✅ API key saved to .env')


def get_api_key():
    """Get API key from args or env"""
    if len(sys.argv) > 1 and sys.argv[1] not in ['help', '--help']:
        return sys.argv[1]

    # Check .env
    env_file = ROOT / '.env'
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line.startswith('IMPROVMX_API_KEY='):
                return line.split('=', 1)[1].strip()
    return None


def show_help():
    print(__doc__)
    print()
    print('Usage:')
    print('  python3 openclaw_email_provisioner.py <improvmx_api_key>')
    print('  python3 openclaw_email_provisioner.py  (uses IMPROVMX_API_KEY from .env)')
    print()
    print('To get API key:')
    print('  1. Sign up free: https://improvmx.com (30 seconds, no credit card)')
    print('  2. Go to: https://app.improvmx.com/account')
    print('  3. Copy API key (starts with "sh_")')
    print('  4. Run: python3 openclaw_email_provisioner.py sh_xxxxxxxxxxxxxxxxxxx')


def main():
    print()
    print('=' * 70)
    print('🤖 OPENCLAW EMAIL PROVISIONER — FULL AUTOMATION')
    print('=' * 70)

    api_key = get_api_key()
    if not api_key:
        show_help()
        return

    print(f'\nTarget: {ALIAS}@{DOMAIN} → {FORWARD_TO}')
    print(f'API:    {API_BASE}')

    # Step 1: Verify
    if not step_1_verify_account(api_key):
        print('\n❌ STOPPED — invalid API key')
        return

    # Step 2: Add domain
    step_2_add_domain(api_key)

    # Step 3: Add alias
    step_3_add_alias(api_key)

    # Step 4: Check MX
    mx_ok = step_4_check_mx_records(api_key)

    # Step 5: Verify
    if mx_ok:
        step_5_verify_via_api(api_key)

    # Store key
    store_api_key(api_key)

    # Summary
    print()
    print('=' * 70)
    print('📋 SUMMARY')
    print('=' * 70)
    print(f'   Domain alias: business@{DOMAIN}')
    print(f'   Forwards to:  {FORWARD_TO}')
    print(f'   Status:       {"🟢 LIVE" if mx_ok else "⏳ Awaiting DNS update"}')

    if not mx_ok:
        print()
        print('   👉 NEXT: Add 2 MX records in GoDaddy (see above)')
        print('   👉 THEN: Re-run this script to verify')
    else:
        print()
        print('   👉 NEXT: Sign up Transak with business@' + DOMAIN)
        print('   👉 URL:  https://transak.com/business-signup')

    print('=' * 70)
    print()


if __name__ == '__main__':
    main()

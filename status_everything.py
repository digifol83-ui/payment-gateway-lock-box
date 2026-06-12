#!/usr/bin/env python3
"""
UNIFIED STATUS COMMAND
Shows complete state of BeastPay activation: Stripe, gateways, email, DNS, next actions.

Usage: python3 status_everything.py
"""
import os
import sys
import json
import urllib.request
import urllib.error
import base64
import subprocess
import asyncio
from pathlib import Path

ROOT = Path('/home/kali/payment-gateway')

def load_env():
    env = {}
    with open(ROOT / '.env') as f:
        for line in f:
            if '=' in line and not line.startswith('#'):
                k, v = line.split('=', 1)
                env[k.strip()] = v.strip()
    return env

def banner(title):
    print()
    print('=' * 70)
    print(f'  {title}')
    print('=' * 70)

def check_stripe(env):
    banner('💳 STRIPE')
    sk = env.get('STRIPE_SECRET_KEY', '')
    if not sk or 'YOUR_' in sk:
        print('❌ Stripe keys not configured')
        return
    try:
        auth = base64.b64encode(f'{sk}:'.encode()).decode()
        req = urllib.request.Request(
            'https://api.stripe.com/v1/account',
            headers={'Authorization': f'Basic {auth}'}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            acc = json.loads(resp.read())
        charges = acc.get('charges_enabled')
        payouts = acc.get('payouts_enabled')
        caps = acc.get('capabilities', {})
        currently_due = acc.get('requirements', {}).get('currently_due', [])
        print(f'   Account:          {acc.get("id")}')
        print(f'   Country:          {acc.get("country")}')
        print(f'   Charges:          {"✅ ENABLED" if charges else "⏳ Pending review"}')
        print(f'   Payouts:          {"✅ ENABLED" if payouts else "⏳ Pending review"}')
        print(f'   Card payments:    {caps.get("card_payments", "n/a")}')
        print(f'   Currently due:    {len(currently_due)} items')
        if currently_due:
            for r in currently_due[:3]:
                print(f'      - {r}')
        if charges:
            print('   🟢 LIVE — accepting real card payments')
        else:
            print('   🟡 Live keys present, account in Stripe team review')
    except urllib.error.HTTPError as e:
        print(f'   ❌ Stripe API error: {e.code}')
    except Exception as e:
        print(f'   ❌ Error: {e}')

def check_gateways():
    banner('🌐 GATEWAYS')
    sys.path.insert(0, str(ROOT))
    try:
        from providers import provider_status_all
        providers = provider_status_all()
        live = []
        sandbox = []
        for p in providers:
            if p.get('production'):
                live.append(p['id'])
            else:
                sandbox.append(p['id'])
        print(f'   ✅ LIVE     ({len(live)}):  {", ".join(live) if live else "(none)"}')
        print(f'   ⏳ SANDBOX  ({len(sandbox)}): {", ".join(sandbox)}')
    except Exception as e:
        print(f'   ❌ Could not load provider status: {e}')

def check_real_payment_status():
    banner('💸 REAL PAYMENT READINESS')
    sys.path.insert(0, str(ROOT))
    try:
        from real_payment_status import real_payment_status

        report = asyncio.run(real_payment_status())
    except Exception as e:
        print(f'   ❌ Could not run real payment checks: {e}')
        return

    if report.get('ready_for_real_payment'):
        print(f'   🟢 Ready providers: {", ".join(report.get("ready_providers", []))}')
    else:
        print('   🔴 No verified real-payment provider is ready right now')

    for row in report.get('checks', []):
        icon = '✅' if row.get('ready_for_real_payment') else '❌'
        provider = row.get('provider_id', 'unknown')
        status = row.get('status', 'unknown')
        detail = row.get('detail', '')
        print(f'   {icon} {provider:10} {status:28} {detail}')

def check_dns():
    banner('🌐 DOMAIN & DNS (sichermayorfx.com)')
    try:
        result = subprocess.run(
            ['dig', '+short', 'sichermayorfx.com'],
            capture_output=True, text=True, timeout=5
        )
        ip = result.stdout.strip()
        print(f'   A record:    {ip if ip else "(none)"}')

        result = subprocess.run(
            ['dig', '+short', 'sichermayorfx.com', 'MX'],
            capture_output=True, text=True, timeout=5
        )
        mx = result.stdout.strip()
        print(f'   MX records:')
        for line in mx.split('\n') if mx else []:
            print(f'      {line}')

        if 'zoho' in mx.lower():
            print('   🟢 Zoho Mail configured')
        elif 'google' in mx.lower():
            print('   🟢 Google Workspace configured')
        elif 'outlook' in mx.lower() or 'protection.outlook' in mx.lower():
            print('   🟡 Outlook (current) — change to Zoho or Google for business@')
        else:
            print('   ❌ No business email MX records found')
    except Exception as e:
        print(f'   ❌ DNS check error: {e}')

def check_files():
    banner('📂 INFRASTRUCTURE FILES')
    files = {
        'gateway_provisioner_skill.py':   'Gateway activation engine',
        'routes_openclaw.py':              'OpenClaw REST API',
        'google_cloud_integration.py':     'Google Cloud bridge',
        'instant_activate_transak.sh':     'One-shot Transak activator',
        'activate_any_gateway.py':         'Multi-gateway activator',
        'activation_checklist.py':         'Progress tracker',
        'FAST_PATH_FREE_EMAIL.md':         'Zoho Mail guide (5min)',
        'LIVE_CHECKOUT_LINKS.md':          'Stripe checkout URLs',
    }
    for fname, desc in files.items():
        exists = (ROOT / fname).exists()
        icon = '✅' if exists else '❌'
        print(f'   {icon} {fname:35} {desc}')

def check_encryption(env):
    banner('🔐 CREDENTIAL ENCRYPTION')
    key = env.get('CREDENTIAL_ENCRYPTION_KEY', '')
    if 'YOUR_64_HEX' in key or not key:
        print('   ❌ Encryption key NOT configured (placeholder still)')
    elif len(key) == 64:
        print(f'   ✅ Encryption key set (64 hex chars)')
    else:
        print(f'   ⚠️  Key set but wrong length ({len(key)} chars, expected 64)')

def show_next_action(env):
    banner('🎯 NEXT ACTION')

    sk = env.get('STRIPE_SECRET_KEY', '')
    transak = env.get('TRANSAK_API_KEY', '')

    has_stripe = sk and 'YOUR_' not in sk and 'sk_live' in sk
    has_transak = transak and 'YOUR_' not in transak and 'test' not in transak

    # Check email setup
    try:
        result = subprocess.run(['dig', '+short', 'sichermayorfx.com', 'MX'],
                              capture_output=True, text=True, timeout=5)
        has_business_email = 'zoho' in result.stdout.lower() or 'google' in result.stdout.lower()
    except:
        has_business_email = False

    if not has_business_email:
        print('   👉 Set up business@sichermayorfx.com (Zoho Mail FREE — 5-7 min)')
        print('      → Read: FAST_PATH_FREE_EMAIL.md')
        print('      → Visit: https://www.zoho.com/mail/zohomail-pricing.html')
    elif not has_transak:
        print('   👉 Sign up for Transak Business with business@sichermayorfx.com')
        print('      → Visit: https://transak.com/business-signup')
        print('      → Use company: SICHER MAYOR INVESTMENTS LLC')
        print('      → Wait 2-4 hours for approval')
    else:
        print('   👉 Activate Transak: ./instant_activate_transak.sh <key> <secret>')

    print()

def main():
    print()
    print('🚀 BEASTPAY UNIFIED STATUS')
    print('   ' + os.popen('date').read().strip())

    env = load_env()
    check_stripe(env)
    check_gateways()
    check_real_payment_status()
    check_dns()
    check_encryption(env)
    check_files()
    show_next_action(env)

    print('=' * 70)
    print('  Run: python3 status_everything.py  (anytime)')
    print('=' * 70)
    print()

if __name__ == '__main__':
    main()

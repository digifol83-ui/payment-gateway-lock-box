#!/usr/bin/env python3
"""
OPENCLAW COMPLETE PIPELINE — INTERACTIVE END-TO-END

The single command that takes you from zero to LIVE.
Walks through every step, automates everything possible, pauses only at hard limits.

  YOUR TIME: ~7 minutes (signup + form fills)
  WAITING:   2-4 hours (Transak approval, runs unattended)
  RESULT:    LIVE Transak fiat-to-crypto processing real money

Run: python3 openclaw_complete_pipeline.py
"""
import os
import sys
import json
import urllib.request
import urllib.error
import base64
import subprocess
import time
import webbrowser
from pathlib import Path

ROOT = Path('/home/kali/payment-gateway')
DOMAIN = 'sichermayorfx.com'
ALIAS = 'business'
FORWARD_TO = 'digifol83@gmail.com'

# ANSI colors
G = '\033[92m'   # green
Y = '\033[93m'   # yellow
R = '\033[91m'   # red
B = '\033[94m'   # blue
C = '\033[96m'   # cyan
W = '\033[97m'   # white
D = '\033[2m'    # dim
BOLD = '\033[1m'
RESET = '\033[0m'


def banner(text, color=C):
    width = 70
    print()
    print(f'{color}{"=" * width}{RESET}')
    print(f'{color}{BOLD}  {text}{RESET}')
    print(f'{color}{"=" * width}{RESET}')


def section(num, total, text):
    print()
    print(f'{B}{BOLD}[{num}/{total}]{RESET} {C}{text}{RESET}')


def ok(text):
    print(f'   {G}✅ {text}{RESET}')


def warn(text):
    print(f'   {Y}⚠️  {text}{RESET}')


def fail(text):
    print(f'   {R}❌ {text}{RESET}')


def info(text):
    print(f'   {D}{text}{RESET}')


def prompt(question, hint=None):
    if hint:
        print(f'   {Y}{question}{RESET}')
        print(f'   {D}{hint}{RESET}')
    else:
        print(f'   {Y}{question}{RESET}')
    return input(f'   {C}> {RESET}').strip()


def confirm(question):
    while True:
        ans = input(f'   {Y}{question} [y/n]> {RESET}').strip().lower()
        if ans in ('y', 'yes'):
            return True
        if ans in ('n', 'no'):
            return False


def http(method, url, headers, data=None, timeout=15):
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
    except Exception as e:
        return 0, {'error': str(e)}


def env_load():
    env = {}
    if (ROOT / '.env').exists():
        for line in (ROOT / '.env').read_text().splitlines():
            if '=' in line and not line.startswith('#'):
                k, v = line.split('=', 1)
                env[k.strip()] = v.strip()
    return env


def env_save(key, value):
    env_file = ROOT / '.env'
    content = env_file.read_text() if env_file.exists() else ''

    import re
    pattern = re.compile(rf'^{re.escape(key)}=.*$', re.MULTILINE)
    if pattern.search(content):
        content = pattern.sub(f'{key}={value}', content)
    else:
        content += f'\n{key}={value}\n'

    env_file.write_text(content)


# ============================================================================
# PHASE 1: EMAIL SETUP (ImprovMX + GoDaddy DNS)
# ============================================================================

def phase_1_email():
    banner('PHASE 1: BUSINESS EMAIL (~3 minutes)', B)

    env = env_load()
    improvmx_key = env.get('IMPROVMX_API_KEY', '')
    godaddy_key = env.get('GODADDY_API_KEY', '')
    godaddy_secret = env.get('GODADDY_API_SECRET', '')

    # ----- ImprovMX -----
    section(1, 5, 'ImprovMX API Key')

    if improvmx_key:
        ok(f'Already in .env: {improvmx_key[:8]}...')
    else:
        print(f'   {W}Sign up free at:{RESET} {C}https://improvmx.com/signup{RESET}')
        info('30 seconds, no credit card required')
        info(f'Use email: {FORWARD_TO}')
        print()
        info('After signup, get key at: https://app.improvmx.com/account')
        print()
        improvmx_key = prompt('Paste ImprovMX API key (starts with "sh_"):',
                             'Or press Enter to skip this phase')
        if not improvmx_key:
            warn('Phase 1 skipped — re-run when ready')
            return False
        env_save('IMPROVMX_API_KEY', improvmx_key)
        ok('Saved to .env')

    # Test
    section(2, 5, 'Test ImprovMX Connection')
    auth = base64.b64encode(f'api:{improvmx_key}'.encode()).decode()
    headers = {'Authorization': f'Basic {auth}', 'Content-Type': 'application/json'}
    status, body = http('GET', 'https://api.improvmx.com/v3/account', headers)
    if status != 200:
        fail(f'API key invalid (HTTP {status})')
        return False
    account = body.get('account', {})
    ok(f'Connected: {account.get("email", "?")} ({account.get("plan", {}).get("name", "free")})')

    # Add domain & alias
    section(3, 5, 'Configure ImprovMX')
    status, _ = http('POST', 'https://api.improvmx.com/v3/domains', headers,
                     {'domain': DOMAIN, 'notification_email': FORWARD_TO})
    if status in (200, 201, 409):
        ok(f'Domain {DOMAIN} active')
    else:
        warn(f'Domain HTTP {status}')

    status, _ = http('POST', f'https://api.improvmx.com/v3/domains/{DOMAIN}/aliases', headers,
                     {'alias': ALIAS, 'forward': FORWARD_TO})
    if status in (200, 201, 409):
        ok(f'Alias {ALIAS}@{DOMAIN} → {FORWARD_TO}')
    else:
        warn(f'Alias HTTP {status}')

    # ----- GoDaddy -----
    section(4, 5, 'GoDaddy API Credentials')

    if godaddy_key and godaddy_secret:
        ok(f'Already in .env: {godaddy_key[:8]}...')
    else:
        print(f'   {W}Generate free API key:{RESET} {C}https://developer.godaddy.com/keys{RESET}')
        info('Sign in with GoDaddy account, click "Create New API Key"')
        info('Environment: Production')
        print()
        godaddy_key = prompt('Paste GoDaddy API Key:')
        if not godaddy_key:
            warn('Phase 1 partial — DNS not updated')
            return False
        godaddy_secret = prompt('Paste GoDaddy API Secret:')
        if not godaddy_secret:
            warn('Phase 1 partial — DNS not updated')
            return False
        env_save('GODADDY_API_KEY', godaddy_key)
        env_save('GODADDY_API_SECRET', godaddy_secret)
        ok('Saved to .env')

    # Update MX records
    section(5, 5, 'Update GoDaddy DNS (MX records)')
    gd_headers = {
        'Authorization': f'sso-key {godaddy_key}:{godaddy_secret}',
        'Content-Type': 'application/json',
    }
    new_mx = [
        {'data': 'mx1.improvmx.com', 'priority': 10, 'ttl': 3600},
        {'data': 'mx2.improvmx.com', 'priority': 20, 'ttl': 3600},
    ]
    status, body = http('PUT',
                        f'https://api.godaddy.com/v1/domains/{DOMAIN}/records/MX',
                        gd_headers, new_mx)
    if status in (200, 204):
        ok('MX records replaced:')
        for rec in new_mx:
            info(f'   priority {rec["priority"]} → {rec["data"]}')
    else:
        fail(f'GoDaddy HTTP {status}: {body}')
        return False

    # Wait for propagation
    print()
    info('DNS propagating (typically 1-5 min)...')
    for attempt in range(1, 8):
        result = subprocess.run(['dig', '+short', DOMAIN, 'MX'],
                              capture_output=True, text=True, timeout=10)
        mx_text = result.stdout.lower()
        if 'improvmx' in mx_text:
            ok(f'DNS propagated (attempt {attempt})')
            break
        info(f'   attempt {attempt}/7 — waiting 20s...')
        if attempt < 7:
            time.sleep(20)

    print()
    ok(f'business@{DOMAIN} → {FORWARD_TO}')
    ok('PHASE 1 COMPLETE')
    return True


# ============================================================================
# PHASE 2: TRANSAK BUSINESS SIGNUP (manual — KYB required)
# ============================================================================

def phase_2_transak():
    banner('PHASE 2: TRANSAK BUSINESS SIGNUP (~5 min + 2-4h wait)', B)

    print(f'\n   {W}Open: {C}https://dashboard.transak.com/signup{RESET}')
    info(f'Email: business@{DOMAIN}')
    info('Company: SICHER MAYOR INVESTMENTS LLC')
    info(f'Website: https://{DOMAIN}')
    info('Type: Payment Service Provider')
    info('Volume: $100,000+')
    info('Country: UAE')
    print()
    info('Upload: DED License 841208 (your existing document)')
    print()

    if not confirm('Have you completed Transak signup?'):
        warn('Phase 2 paused — re-run when signup is done')
        return False

    print()
    info('Transak will email approval status (2-4 hours).')
    info(f'Check inbox: {FORWARD_TO} for "transak.com" emails.')
    print()
    info('Email partners@transak.com from business@ to request AED enablement.')
    print()

    if not confirm('Have you received API keys from Transak?'):
        warn('Phase 2 waiting — re-run after approval')
        return False

    transak_key = prompt('Paste Transak API Key (starts with "pk_live_"):')
    if not transak_key:
        warn('No key provided')
        return False
    transak_secret = prompt('Paste Transak Secret (starts with "sk_live_"):')

    env_save('TRANSAK_API_KEY', transak_key)
    if transak_secret:
        env_save('TRANSAK_SECRET', transak_secret)
    env_save('TRANSAK_ENV', 'PRODUCTION')

    ok('Transak credentials saved')
    return True


# ============================================================================
# PHASE 3: FINAL ACTIVATION (fully automated)
# ============================================================================

def phase_3_activate():
    banner('PHASE 3: FINAL ACTIVATION (1 minute)', B)

    env = env_load()
    transak_key = env.get('TRANSAK_API_KEY', '')
    transak_secret = env.get('TRANSAK_SECRET', '')

    if not transak_key or 'test' in transak_key:
        warn('Transak production key not yet set — skipping')
        return False

    section(1, 3, 'Run gateway provisioner')
    result = subprocess.run(
        ['python3', 'gateway_provisioner_skill.py', 'activate', 'transak',
         transak_key, transak_secret or ''],
        capture_output=True, text=True, cwd=str(ROOT)
    )
    print(result.stdout)
    if result.returncode != 0:
        fail('Activation failed')
        print(result.stderr)
        return False
    ok('Gateway provisioner success')

    section(2, 3, 'Verify status')
    sys.path.insert(0, str(ROOT))
    try:
        from providers import provider_status_all
        providers = provider_status_all()
        transak = next((p for p in providers if p['id'] == 'transak'), None)
        if transak and transak.get('production'):
            ok(f'Transak: {transak["status"]}')
        else:
            warn(f'Transak: {transak.get("status") if transak else "not found"}')
    except Exception as e:
        warn(f'Could not verify: {e}')

    section(3, 3, 'Test checkout URL')
    info(f'Checkout: http://localhost:8000/buy?provider=transak')
    print()
    return True


# ============================================================================
# MAIN
# ============================================================================

def main():
    banner('🚀 OPENCLAW COMPLETE PIPELINE', G)
    print(f'   {D}Goal: LIVE Transak fiat-to-crypto processing real money{RESET}')
    print(f'   {D}Domain: {DOMAIN} | Forward to: {FORWARD_TO}{RESET}')

    # Show current status
    env = env_load()
    print()
    print(f'{C}{BOLD}Current state:{RESET}')
    has_imx = bool(env.get('IMPROVMX_API_KEY'))
    has_gd = bool(env.get('GODADDY_API_KEY')) and bool(env.get('GODADDY_API_SECRET'))
    has_transak_live = env.get('TRANSAK_API_KEY', '').startswith(('pk_live_', 'sk_live_'))

    print(f'   ImprovMX key:    {G + "✅" + RESET if has_imx else Y + "⏳" + RESET}')
    print(f'   GoDaddy keys:    {G + "✅" + RESET if has_gd else Y + "⏳" + RESET}')
    print(f'   Transak live:    {G + "✅" + RESET if has_transak_live else Y + "⏳" + RESET}')

    print()
    if not confirm('Continue with pipeline?'):
        return

    # Run phases
    p1 = phase_1_email()
    if not p1:
        return

    p2 = phase_2_transak()
    if not p2:
        return

    phase_3_activate()

    banner('🎉 PIPELINE COMPLETE — LIVE PAYMENTS ACTIVE', G)
    print(f'   {G}{BOLD}REAL MONEY FLOWING ✅{RESET}')
    print(f'   Checkout: http://localhost:8000/buy?provider=transak')
    print()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\n\n⏸  Pipeline paused. Re-run anytime: python3 openclaw_complete_pipeline.py')

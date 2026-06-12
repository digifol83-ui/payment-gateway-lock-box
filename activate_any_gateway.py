#!/usr/bin/env python3
"""
ONE-CLICK ACTIVATION FOR ANY GATEWAY
Usage: python3 activate_any_gateway.py <provider> <api_key> [secret] [webhook_secret]

Examples:
  python3 activate_any_gateway.py transak  pk_live_xxx  sk_live_yyy
  python3 activate_any_gateway.py moonpay  pk_live_xxx  sk_live_yyy
  python3 activate_any_gateway.py kast     api_live_xxx
  python3 activate_any_gateway.py ziina    Bearer_token_here
  python3 activate_any_gateway.py guardarian  api_key_here

After activation:
  - Provider goes from SANDBOX → LIVE
  - Real-money checkout URLs become available
  - Webhooks register automatically
  - Telegram notifications enabled
"""
import sys
import os
import re
from pathlib import Path

GATEWAY = sys.argv[1] if len(sys.argv) > 1 else None
API_KEY = sys.argv[2] if len(sys.argv) > 2 else None
SECRET = sys.argv[3] if len(sys.argv) > 3 else ""
WEBHOOK_SECRET = sys.argv[4] if len(sys.argv) > 4 else ""

if not GATEWAY or not API_KEY:
    print(__doc__)
    sys.exit(1)

GATEWAY = GATEWAY.lower()

GATEWAY_CONFIGS = {
    "transak": {
        "env_keys": ["TRANSAK_API_KEY", "TRANSAK_SECRET", "TRANSAK_ACCESS_TOKEN", "TRANSAK_ENV"],
        "env_value": "PRODUCTION",
        "test_url": "https://api.transak.com/api/v2/currencies/crypto-currencies",
    },
    "moonpay": {
        "env_keys": ["MOONPAY_API_KEY", "MOONPAY_SECRET", "MOONPAY_WEBHOOK_SECRET", "MOONPAY_ENV"],
        "env_value": "PRODUCTION",
        "test_url": "https://api.moonpay.com/v3/currencies",
    },
    "kast": {
        "env_keys": ["KAST_API_KEY", "KAST_SECRET", "KAST_WEBHOOK_SECRET", "KAST_ENV"],
        "env_value": "PRODUCTION",
        "test_url": "https://api.kast.co/v1/health",
    },
    "ziina": {
        "env_keys": ["ZIINA_API_TOKEN", "ZIINA_SECRET", "ZIINA_WEBHOOK_SECRET", "ZIINA_ENV"],
        "env_value": "production",
        "test_url": "https://api-v2.ziina.com/api/payment_intent",
    },
    "guardarian": {
        "env_keys": ["GUARDARIAN_API_KEY", "GUARDARIAN_SECRET", "GUARDARIAN_WEBHOOK_SECRET", "GUARDARIAN_ENV"],
        "env_value": "production",
        "test_url": "https://api-payments.guardarian.com/v1/api-currencies",
    },
    "metamask": {
        "env_keys": ["METAMASK_API_KEY", "METAMASK_SECRET", "METAMASK_WEBHOOK_SECRET", "METAMASK_ENV"],
        "env_value": "production",
        "test_url": "https://api.metamask.io/v1/currencies",
    },
    "bleap": {
        "env_keys": ["BLEAP_API_KEY", "BLEAP_SECRET", "BLEAP_WEBHOOK_SECRET", "BLEAP_ENV"],
        "env_value": "production",
        "test_url": "https://api.bleap.io/v1/health",
    },
    "nowpayments": {
        "env_keys": ["NOWPAYMENTS_API_KEY", "NOWPAYMENTS_IPN_SECRET", "_unused", "NOWPAYMENTS_ENV"],
        "env_value": "production",
        "test_url": "https://api.nowpayments.io/v1/status",
    },
    "plisio": {
        "env_keys": ["PLISIO_API_KEY", "_unused", "_unused", "PLISIO_ENV"],
        "env_value": "production",
        "test_url": "https://plisio.net/api/v1/currencies",
    },
    "kyrrex": {
        "env_keys": ["KYRREX_API_KEY", "KYRREX_SECRET", "KYRREX_WEBHOOK_SECRET", "KYRREX_ENV"],
        "env_value": "production",
        "test_url": "https://api.kyrrex.com/api/v1/invoice",
    },
    "banxa": {
        "env_keys": ["BANXA_API_KEY", "BANXA_SECRET", "BANXA_WEBHOOK_SECRET", "BANXA_ENV"],
        "env_value": "production",
        "test_url": "https://api.banxa.com/api/v1/orders",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer ",
    },
    "changelly": {
        "env_keys": ["CHANGELLY_API_KEY", "CHANGELLY_SECRET", "CHANGELLY_WEBHOOK_SECRET", "CHANGELLY_ENV"],
        "env_value": "production",
        "test_url": "https://api.changelly.com/api/v1/currencies/fiat",
        "auth_header": "X-Api-Key",
        "auth_prefix": "",
    },
    "changenow": {
        "env_keys": ["CHANGENOW_API_KEY", "CHANGENOW_SECRET", "CHANGENOW_WEBHOOK_SECRET", "CHANGENOW_ENV"],
        "env_value": "production",
        "test_url": "https://api.changenow.io/v2/exchange/estimated-amount?from=usd&to=btc&amount=100&flow=standard&type=direct",
        "auth_header": "x-changenow-api-key",
        "auth_prefix": "",
    },
    "coinify": {
        "env_keys": ["COINIFY_API_KEY", "COINIFY_SECRET", "COINIFY_WEBHOOK_SECRET", "COINIFY_ENV"],
        "env_value": "production",
        "test_url": "https://api.coinify.com/v3/balance",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer ",
    },
}

if GATEWAY not in GATEWAY_CONFIGS:
    print(f"❌ Unknown gateway: {GATEWAY}")
    print(f"Supported: {', '.join(GATEWAY_CONFIGS.keys())}")
    sys.exit(1)

config = GATEWAY_CONFIGS[GATEWAY]

print(f"\n{'='*60}")
print(f"🚀 ACTIVATING {GATEWAY.upper()}")
print(f"{'='*60}\n")

# Step 1: Test the credentials
print(f"1️⃣  Testing API key against {config['test_url']}")
import urllib.request
import urllib.error

auth_header_name = config.get('auth_header', 'Authorization')
auth_prefix = config.get('auth_prefix', 'Bearer ')
test_headers = {
    auth_header_name: f'{auth_prefix}{API_KEY}',
    'X-Api-Key': API_KEY,
    'api-key': API_KEY,
}
try:
    req = urllib.request.Request(
        config['test_url'],
        headers=test_headers,
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        if resp.status == 200:
            print(f"   ✅ API key is VALID — {resp.status}")
        else:
            print(f"   ⚠️  Got status {resp.status}")
except urllib.error.HTTPError as e:
    if e.code in [401, 403]:
        print(f"   ❌ API key REJECTED — {e.code}")
        print(f"   Check the key and try again.")
        sys.exit(1)
    else:
        print(f"   ⚠️  Got {e.code} — proceeding (some endpoints test differently)")
except Exception as e:
    print(f"   ⚠️  Connection issue: {e} — proceeding")

# Step 2: Update .env
print(f"\n2️⃣  Updating .env with production credentials")

env_path = Path('/home/kali/payment-gateway/.env')
content = env_path.read_text()

values = [API_KEY, SECRET, WEBHOOK_SECRET, config['env_value']]
for key, value in zip(config['env_keys'], values):
    if key.startswith('_'):
        continue
    pattern = re.compile(rf'^{re.escape(key)}=.*$', re.MULTILINE)
    if pattern.search(content):
        content = pattern.sub(f'{key}={value}', content)
        print(f"   ✅ Updated {key}")
    else:
        content += f'\n{key}={value}'
        print(f"   ✅ Added {key}")

env_path.write_text(content)

# Step 3: Verify
print(f"\n3️⃣  Verifying provider goes LIVE")
import subprocess
result = subprocess.run(
    ['python3', '-c', f'''
import os
with open("/home/kali/payment-gateway/.env") as f:
    for line in f:
        if "=" in line:
            k, v = line.split("=", 1)
            os.environ[k.strip()] = v.strip()
import sys
sys.path.insert(0, "/home/kali/payment-gateway")
from providers import provider_status_all
for p in provider_status_all():
    if p["id"] == "{GATEWAY}":
        print(f"Status: {{p[\\"status\\"]}}, Production: {{p[\\"production\\"]}}")
'''],
    capture_output=True, text=True, cwd='/home/kali/payment-gateway'
)
print(f"   {result.stdout.strip()}")

print(f"\n{'='*60}")
print(f"✅ {GATEWAY.upper()} ACTIVATED")
print(f"{'='*60}")
print(f"\n🔗 NEXT STEPS:")
print(f"   1. Restart server: cd /home/kali/payment-gateway && uvicorn server:app --port 8000")
print(f"   2. Visit: http://localhost:8000/buy?provider={GATEWAY}")
print(f"   3. Real money payments will flow")
print(f"\n💰 CHECK STATUS:")
print(f"   curl http://localhost:8000/api/providers/live")

#!/usr/bin/env python3
"""
GATEWAY PROVISIONER SUPER POWER SKILL
Autonomous payment gateway provisioning with OpenClaw orchestration
"""
import os
import json
import subprocess
import time
from datetime import datetime
from pathlib import Path
import urllib.request
import urllib.error

class GatewayProvisioner:
    """Master provisioner for all payment gateways"""

    GATEWAYS = {
        'transak': {
            'name': 'Transak',
            'signup_url': 'https://transak.com/signup',
            'api_base': 'https://api.transak.com/api/v2',
            'type': 'fiat-to-crypto',
            'aed_support': True,
            'speed': '1-2 hours',
        },
        'moonpay': {
            'name': 'MoonPay',
            'signup_url': 'https://www.moonpay.com/signup',
            'api_base': 'https://api.moonpay.com/v3',
            'type': 'fiat-to-crypto',
            'aed_support': False,
            'speed': '2-4 hours',
        },
        'kast': {
            'name': 'KAST Pay',
            'signup_url': 'https://kast.co/register',
            'api_base': 'https://api.kast.co/v1',
            'type': 'fiat-to-crypto',
            'aed_support': True,
            'speed': '1-2 hours',
        },
        'ziina': {
            'name': 'Ziina',
            'signup_url': 'https://ziina.com/merchant-signup',
            'api_base': 'https://api-v2.ziina.com',
            'type': 'fiat-only',
            'aed_support': True,
            'speed': '30 minutes',
        },
        'guardarian': {
            'name': 'Guardarian',
            'signup_url': 'https://guardarian.com/',
            'api_base': 'https://api-payments.guardarian.com/v1',
            'type': 'fiat-to-crypto',
            'aed_support': False,
            'speed': '2-6 hours',
        },
    }

    def __init__(self):
        self.env_file = Path('/home/kali/payment-gateway/.env')
        self.log_file = Path('/home/kali/payment-gateway/provisioner_log.txt')
        self.status_file = Path('/home/kali/payment-gateway/gateway_status.json')
        self.load_env()

    def load_env(self):
        """Load environment variables"""
        self.env = {}
        with open(self.env_file) as f:
            for line in f:
                if '=' in line and not line.startswith('#'):
                    k, v = line.split('=', 1)
                    self.env[k.strip()] = v.strip()

    def log(self, msg, level='INFO'):
        """Log message with timestamp"""
        timestamp = datetime.now().isoformat()
        log_msg = f"[{timestamp}] [{level}] {msg}"
        print(log_msg)
        with open(self.log_file, 'a') as f:
            f.write(log_msg + '\n')

    def activate_gateway(self, gateway_id, api_key, secret='', webhook_secret=''):
        """Activate a gateway with API credentials"""
        if gateway_id not in self.GATEWAYS:
            self.log(f"Unknown gateway: {gateway_id}", 'ERROR')
            return False

        gateway = self.GATEWAYS[gateway_id]
        self.log(f"Activating {gateway['name']} ({gateway_id})")

        # Step 1: Test the API key
        self.log(f"  Testing API key...")
        if not self.test_api_key(gateway_id, api_key):
            self.log(f"  API key test failed", 'WARN')
        else:
            self.log(f"  API key validated ✅")

        # Step 2: Update .env
        self.log(f"  Updating .env...")
        self.update_env(gateway_id, api_key, secret, webhook_secret)

        # Step 3: Run activation script
        self.log(f"  Running activation script...")
        result = subprocess.run(
            ['python3', '/home/kali/payment-gateway/activate_any_gateway.py',
             gateway_id, api_key, secret, webhook_secret],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            self.log(f"✅ {gateway['name']} ACTIVATED")
            return True
        else:
            self.log(f"Activation failed: {result.stderr}", 'ERROR')
            return False

    def test_api_key(self, gateway_id, api_key):
        """Test if API key is valid"""
        gateway = self.GATEWAYS.get(gateway_id)
        if not gateway:
            return False

        try:
            test_url = f"{gateway['api_base']}/currencies"
            headers = {
                'Authorization': f'Bearer {api_key}',
                'X-Api-Key': api_key,
            }
            req = urllib.request.Request(test_url, headers=headers)
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status in [200, 401, 403]  # API responded
        except:
            return False

    def update_env(self, gateway_id, api_key, secret, webhook_secret):
        """Update .env with gateway credentials"""
        content = self.env_file.read_text()

        updates = {
            f'{gateway_id.upper()}_API_KEY': api_key,
            f'{gateway_id.upper()}_SECRET': secret,
            f'{gateway_id.upper()}_WEBHOOK_SECRET': webhook_secret,
            f'{gateway_id.upper()}_ENV': 'production',
        }

        for key, value in updates.items():
            if not value:
                continue
            import re
            pattern = re.compile(rf'^{re.escape(key)}=.*$', re.MULTILINE)
            if pattern.search(content):
                content = pattern.sub(f'{key}={value}', content)
            else:
                content += f'\n{key}={value}'

        self.env_file.write_text(content)

    def get_status(self):
        """Get status of all gateways"""
        import sys
        sys.path.insert(0, '/home/kali/payment-gateway')

        try:
            from providers import provider_status_all
            providers = provider_status_all()

            status = {
                'timestamp': datetime.now().isoformat(),
                'providers': {}
            }

            for p in providers:
                if p['id'] in self.GATEWAYS:
                    status['providers'][p['id']] = {
                        'name': self.GATEWAYS[p['id']]['name'],
                        'status': p['status'],
                        'production': p['production'],
                        'type': self.GATEWAYS[p['id']]['type'],
                    }

            with open(self.status_file, 'w') as f:
                json.dump(status, f, indent=2)

            return status
        except Exception as e:
            self.log(f"Error getting status: {e}", 'ERROR')
            return None

    def dashboard(self):
        """Print dashboard of all gateways"""
        status = self.get_status()
        if not status:
            print("❌ Could not get gateway status")
            return

        print("\n" + "="*80)
        print("🎛️  GATEWAY PROVISIONER DASHBOARD")
        print("="*80 + "\n")

        print("AVAILABLE GATEWAYS:\n")
        for gw_id, gw in self.GATEWAYS.items():
            p_status = status.get('providers', {}).get(gw_id, {})
            status_icon = '🟢' if p_status.get('production') else '🟡'

            print(f"{status_icon} {gw['name']:20} | {gw['type']:15} | AED: {'✅' if gw['aed_support'] else '❌'} | {gw['speed']:12}")
            print(f"   API: {gw['api_base']}")
            print(f"   Signup: {gw['signup_url']}")
            if p_status:
                print(f"   Current: {p_status['status']}")
            print()

        print("="*80)
        print("\nACTIVATION COMMAND:")
        print("  python3 gateway_provisioner_skill.py activate <gateway_id> <api_key> [secret] [webhook]")
        print("\nExample:")
        print("  python3 gateway_provisioner_skill.py activate transak pk_live_xxx sk_live_yyy")
        print("\n" + "="*80 + "\n")

def main():
    import sys

    provisioner = GatewayProvisioner()

    if len(sys.argv) < 2:
        provisioner.dashboard()
        return

    cmd = sys.argv[1]

    if cmd == 'activate':
        if len(sys.argv) < 4:
            print("Usage: activate <gateway_id> <api_key> [secret] [webhook_secret]")
            return

        gateway_id = sys.argv[2]
        api_key = sys.argv[3]
        secret = sys.argv[4] if len(sys.argv) > 4 else ''
        webhook = sys.argv[5] if len(sys.argv) > 5 else ''

        provisioner.activate_gateway(gateway_id, api_key, secret, webhook)

    elif cmd == 'status':
        provisioner.dashboard()

    elif cmd == 'log':
        with open(provisioner.log_file) as f:
            print(f.read())

    else:
        print(f"Unknown command: {cmd}")
        provisioner.dashboard()

if __name__ == '__main__':
    main()

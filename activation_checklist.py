#!/usr/bin/env python3
"""
ACTIVATION CHECKLIST & STATUS TRACKER
Tracks progress toward live Transak payment processing
"""
import os
import json
from pathlib import Path
from datetime import datetime

class ActivationChecklist:
    """Tracks completion of business email + gateway activation steps"""

    CHECKLIST_FILE = Path('/home/kali/payment-gateway/.activation_checklist.json')

    STEPS = {
        'email': {
            'name': '📧 Business Email Setup',
            'substeps': [
                'Visit https://workspace.google.com',
                'Create Business Starter account ($6/month)',
                'Verify sichermayorfx.com domain (add MX records)',
                'Create business@sichermayorfx.com email',
                'Enable email forwarding (optional)',
            ]
        },
        'google_cloud': {
            'name': '☁️  Google Cloud Setup',
            'substeps': [
                'Verify logged in to Google Cloud (ullaakcrypto@gmail.com)',
                'Create/verify GCP project',
                'Enable Gmail API',
                'Create OAuth2 credentials',
            ]
        },
        'transak': {
            'name': '🚀 Transak Business Signup',
            'substeps': [
                'Visit https://transak.com/business-signup',
                'Fill form with business@sichermayorfx.com',
                'Enter company: SICHER MAYOR INVESTMENTS LLC',
                'Upload DED License 841208',
                'Submit application',
                'Wait 2-4 hours for initial review',
                'Email partners@transak.com for AED enablement',
                'Copy API key and secret from dashboard',
            ]
        },
        'activation': {
            'name': '⚡ Final Activation',
            'substeps': [
                'Run: python3 gateway_provisioner_skill.py activate transak <pk_live_xxx> <sk_live_yyy>',
                'Verify TRANSAK_ENV=production in .env',
                'Check dashboard: python3 gateway_provisioner_skill.py status',
                'Visit http://localhost:8000/buy?provider=transak',
                '✅ LIVE PAYMENTS ACTIVE',
            ]
        }
    }

    def __init__(self):
        self.load_checklist()

    def load_checklist(self):
        """Load existing checklist or create new"""
        if self.CHECKLIST_FILE.exists():
            with open(self.CHECKLIST_FILE) as f:
                self.data = json.load(f)
        else:
            self.data = {
                'started': datetime.now().isoformat(),
                'steps': {k: {'completed': False, 'timestamp': None} for k in self.STEPS.keys()}
            }
            self.save()

    def save(self):
        """Save checklist to disk"""
        with open(self.CHECKLIST_FILE, 'w') as f:
            json.dump(self.data, f, indent=2)

    def mark_complete(self, step_key):
        """Mark a step as complete"""
        if step_key in self.STEPS:
            self.data['steps'][step_key]['completed'] = True
            self.data['steps'][step_key]['timestamp'] = datetime.now().isoformat()
            self.save()
            print(f"✅ {self.STEPS[step_key]['name']} marked complete")
        else:
            print(f"❌ Unknown step: {step_key}")

    def show_status(self):
        """Display current progress"""
        print("\n" + "="*80)
        print("🚀 BEASTPAY ACTIVATION CHECKLIST")
        print("="*80 + "\n")

        completed = sum(1 for s in self.data['steps'].values() if s['completed'])
        total = len(self.data['steps'])

        print(f"Progress: {completed}/{total} sections complete ({int(completed/total*100)}%)\n")

        for step_key, step_config in self.STEPS.items():
            is_done = self.data['steps'][step_key]['completed']
            status_icon = '✅' if is_done else '⏳'
            timestamp = self.data['steps'][step_key]['timestamp']
            time_str = f" ({timestamp.split('T')[0]})" if timestamp else ""

            print(f"{status_icon} {step_config['name']}{time_str}")
            for i, substep in enumerate(step_config['substeps'], 1):
                print(f"   [{i}] {substep}")
            print()

        print("="*80 + "\n")

        next_step = next((k for k, v in self.data['steps'].items() if not v['completed']), None)
        if next_step:
            print(f"👉 NEXT: {self.STEPS[next_step]['name']}")
        else:
            print("🎉 ALL STEPS COMPLETE - READY FOR ACTIVATION")
        print()

    def verify_prerequisites(self):
        """Check if all prerequisites are met for activation"""
        print("\n📋 PRE-ACTIVATION VERIFICATION\n")

        checks = {
            'gateway_provisioner.py': Path('/home/kali/payment-gateway/gateway_provisioner_skill.py'),
            'routes_openclaw.py': Path('/home/kali/payment-gateway/routes_openclaw.py'),
            'google_cloud_integration.py': Path('/home/kali/payment-gateway/google_cloud_integration.py'),
            '.env file': Path('/home/kali/payment-gateway/.env'),
            'activation guide': Path('/home/kali/payment-gateway/GOOGLE_WORKSPACE_SETUP.md'),
        }

        for name, path in checks.items():
            status = "✅" if path.exists() else "❌"
            print(f"{status} {name}")

        # Check .env for Stripe keys (should be live)
        try:
            with open('/home/kali/payment-gateway/.env') as f:
                env_text = f.read()
                stripe_live = 'sk_live_' in env_text and 'pk_live_' in env_text
                status = "✅" if stripe_live else "❌"
                print(f"{status} Stripe live keys configured")
        except:
            print("❌ Could not check .env")

        print()

    def get_activation_command(self):
        """Generate activation command template"""
        print("\n⚡ ACTIVATION COMMAND TEMPLATE\n")
        print("Once you have API keys from Transak dashboard:\n")
        print("python3 gateway_provisioner_skill.py activate transak \\")
        print("  <YOUR_API_KEY_FROM_TRANSAK_DASHBOARD> \\")
        print("  <YOUR_SECRET_FROM_TRANSAK_DASHBOARD>\n")
        print("Example:")
        print("python3 gateway_provisioner_skill.py activate transak \\")
        print("  pk_live_1234567890abcdef \\")
        print("  sk_live_abcdefg1234567890\n")

def main():
    import sys
    checklist = ActivationChecklist()

    if len(sys.argv) < 2:
        checklist.show_status()
        print("\nUsage:")
        print("  python3 activation_checklist.py status           - Show current progress")
        print("  python3 activation_checklist.py verify           - Verify prerequisites")
        print("  python3 activation_checklist.py mark <step>      - Mark step complete")
        print("  python3 activation_checklist.py command          - Show activation command")
        print("\nSteps: email, google_cloud, transak, activation")
        return

    cmd = sys.argv[1]

    if cmd == 'status':
        checklist.show_status()
    elif cmd == 'verify':
        checklist.verify_prerequisites()
    elif cmd == 'mark':
        if len(sys.argv) < 3:
            print("Usage: mark <step_name>")
            return
        checklist.mark_complete(sys.argv[2])
        checklist.show_status()
    elif cmd == 'command':
        checklist.get_activation_command()
    else:
        print(f"Unknown command: {cmd}")

if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
Plisio signup clipboard filler.
Fields: email, password (2x), then navigate to API keys.
"""
import subprocess
import sys

G = '\033[92m'; Y = '\033[93m'; C = '\033[96m'; R = '\033[91m'
W = '\033[97m'; D = '\033[2m'; B = '\033[94m'; BOLD = '\033[1m'; RESET = '\033[0m'


def copy_to_clipboard(text: str) -> bool:
    try:
        proc = subprocess.Popen(
            ['/mnt/c/Windows/System32/clip.exe'],
            stdin=subprocess.PIPE
        )
        proc.communicate(input=text.encode('utf-16le'))
        return proc.returncode == 0
    except Exception as e:
        print(f'{R}clipboard error: {e}{RESET}')
        return False


FIELDS = [
    ('section', '═══ PLISIO SIGNUP ═══', None),
    ('Email', 'sichermayor@deltajohnsons.com', None),
    ('Password', 'BeastPay_PL_2026!Secure', None),
    ('Confirm Password', 'BeastPay_PL_2026!Secure', None),
    ('section', '═══ AFTER SIGNUP ═══', None),
    ('Navigate to', 'https://plisio.net/account/settings', None),
    ('section', '═══ COPY API KEY ═══', None),
    ('API Key location', 'Settings → API Keys (under "Secret key")', None),
]


def main():
    print()
    print(f'{C}{BOLD}{"=" * 60}{RESET}')
    print(f'{C}{BOLD}  🚀  PLISIO SIGNUP HELPER{RESET}')
    print(f'{C}{BOLD}{"=" * 60}{RESET}')
    print()
    print(f'{Y}STEPS:{RESET}')
    print(f'   1. Open https://plisio.net/registration in browser')
    print(f'   2. Click email field')
    print(f'   3. Press Enter here → value copied to clipboard')
    print(f'   4. Ctrl+V in browser → Tab to next field')
    print(f'   5. Press Enter here for next field')
    print(f'   6. After signup, navigate to API Keys and copy key')
    print()
    input(f'{C}Press Enter to start...{RESET}')

    for i, (label, value, _) in enumerate(FIELDS):
        if label == 'section':
            print()
            print(f'{B}{BOLD}{value}{RESET}')
            print()
            continue

        print(f'{D}[{i+1}/{len(FIELDS)}]{RESET} {C}{label}{RESET}')
        print(f'   {W}{value}{RESET}')

        if 'password' not in label.lower() and 'navigate' not in label.lower() and 'location' not in label.lower():
            if copy_to_clipboard(value):
                print(f'   {G}✅ Copied — Ctrl+V{RESET}')
            else:
                print(f'   {R}❌ Could not copy{RESET}')

        cmd = input(f'{D}   [Enter=next | skip | quit]: {RESET}').strip().lower()
        if cmd == 'quit':
            return
        elif cmd == 'skip':
            print(f'   {D}skipped{RESET}')

    print()
    print(f'{G}{BOLD}{"=" * 60}{RESET}')
    print(f'{G}{BOLD}  ✅ SIGNUP COMPLETE — copy API key from dashboard{RESET}')
    print(f'{G}{BOLD}{"=" * 60}{RESET}')
    print()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print(f'\n{Y}Interrupted.{RESET}\n')

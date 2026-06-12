#!/usr/bin/env python3
"""
KYB CLIPBOARD FILLER — semi-auto form fill via Windows clipboard

Walks through every Transak KYB form field in order. For each one:
- Shows label + value
- Auto-copies value to Windows clipboard (via clip.exe)
- You: paste with Ctrl+V into the form, hit Tab → press Enter here for next field

Result: Fill ~50 fields in 2-3 minutes. No typing.

Usage: python3 kyb_clipboard_filler.py
"""
import subprocess
import sys
import os

# ANSI colors
G = '\033[92m'; Y = '\033[93m'; C = '\033[96m'; R = '\033[91m'
W = '\033[97m'; D = '\033[2m'; B = '\033[94m'; BOLD = '\033[1m'; RESET = '\033[0m'


def copy_to_clipboard(text: str) -> bool:
    """Copy text to Windows clipboard via clip.exe (works in WSL)"""
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


def show_files(category: str):
    """Print which file paths to upload for a category"""
    files = {
        'trade_license': [
            '/home/kali/payment-gateway/uploads/6e22de07-2958-4011-b0d1-813d8f7f196a.jpeg',
        ],
        'memorandum': [
            '/home/kali/payment-gateway/uploads/27002671-4b58-44a3-832a-b00c5c2e9836.jpeg',
            '/home/kali/payment-gateway/uploads/19f07f6b-5b5d-452e-8a8e-12d6e66d0b1a.jpeg',
            '/home/kali/payment-gateway/uploads/d34b1c65-cb03-4f56-b2c3-bb5b338dac2b.jpeg',
            '/home/kali/payment-gateway/uploads/935cba1d-7c04-48ee-8506-1d8d3359f10a.jpeg',
            '/home/kali/payment-gateway/uploads/85d2e6c3-4a9e-4b9f-a747-7b24cb5b4c83.jpeg',
            '/home/kali/payment-gateway/uploads/65d5acb6-0d14-4dda-82fa-b01047f8caff.jpeg',
            '/home/kali/payment-gateway/uploads/63026a1a-c945-4420-b4f1-e63fc7b77c55.jpeg',
        ],
        'partners_list': [
            '/home/kali/payment-gateway/uploads/1f7379b9-e486-4329-adc7-4d692690da61.jpeg',
        ],
        'commercial_register': [
            '/home/kali/payment-gateway/uploads/bccbc4b5-7d7e-41ff-ab12-da100ef020fe.jpeg',
        ],
        'chamber_membership': [
            '/home/kali/payment-gateway/uploads/57172d26-f8e7-401f-8e3b-68a3ef762f0f.jpeg',
        ],
        'director_passport': [
            '/home/kali/payment-gateway/uploads/SHAJAHAN_passport_S0124841.jpeg',
        ],
        'director_eid_front': [
            '/home/kali/payment-gateway/uploads/SHAJAHAN_EID_front_v2.png',
        ],
        'director_eid_back': [
            '/home/kali/payment-gateway/uploads/SHAJAHAN_EID_back.png',
        ],
        'poa': [
            '/home/kali/payment-gateway/uploads/shaheer_poa.pdf',
        ],
    }
    paths = files.get(category, [])
    if not paths:
        print(f'   {Y}No file mapping for {category}{RESET}')
        return
    print(f'   {C}📁 Upload these files:{RESET}')
    for p in paths:
        # Convert to Windows path for easy copy from File Explorer
        win_path = p.replace('/home/kali/', r'\\wsl$\kali\home\kali\\').replace('/', '\\')
        exists = '✓' if os.path.exists(p) else '✗'
        print(f'      {exists} {p}')


# (label, value, optional_file_category)
FIELDS = [
    # ---- Phase 1: Sign-up basics ----
    ('section', '═══ COMPANY DETAILS ═══', None),
    ('Legal company name', 'SICHER MAYOR COMMERCIAL BROKERS L.L.C', None),
    ('Trade name', 'SICHER MAYOR COMMERCIAL BROKERS L.L.C', None),
    ('Legal form', 'Limited Liability Company (LLC)', None),
    ('Country of incorporation', 'United Arab Emirates', None),
    ('State / Emirate', 'Dubai', None),
    ('Date of incorporation', '23/06/2019', None),
    ('Trade license number', '841208', None),
    ('Commercial register number', '1427976', None),
    ('Chamber of Commerce membership', '323179', None),
    ('License issuing authority', 'Department of Economy and Tourism, Government of Dubai', None),
    ('License issue date', '23/06/2025', None),
    ('License expiry date', '24/06/2026', None),
    ('Business activity', 'Commercial Brokers / Payment Service Provider', None),
    ('Industry', 'Financial Services', None),
    ('Paid-up capital', '300000', None),
    ('Capital currency', 'AED', None),
    ('Number of shares', '300', None),

    ('section', '═══ ADDRESS ═══', None),
    ('Address line 1', 'Office #209, Al Rostamani Real Estate Building', None),
    ('Address line 2', 'Deira, Dubai International Airport', None),
    ('District / Area', 'Al Qarhood (Garhoud)', None),
    ('City', 'Dubai', None),
    ('Postal code / P.O. Box', '44297', None),
    ('Country', 'United Arab Emirates', None),

    ('section', '═══ CONTACT ═══', None),
    ('Company email', 'sichermayor@deltajohnsons.com', None),
    ('Phone', '+971542473412', None),
    ('Website', 'https://sichermayor.com', None),

    ('section', '═══ DIRECTOR (100% OWNER) ═══', None),
    ('Director full name', 'SHAJAHAN POTHANCHERRY ALAVI POTHANCHERRY', None),
    ('Director first name', 'SHAJAHAN', None),
    ('Director last name', 'POTHANCHERRY ALAVI POTHANCHERRY', None),
    ('Director nationality', 'India', None),
    ('Director date of birth', '22/04/1989', None),
    ('Director place of birth', 'Tirur, Kerala, India', None),
    ('Director passport number', 'S0124841', None),
    ('Director passport issue date', '09/03/2018', None),
    ('Director passport expiry', '08/03/2028', None),
    ('Director Emirates ID', '784-1989-9348860-4', None),
    ('Director EID expiry', '06/05/2027', None),
    ('Director country of residence', 'United Arab Emirates', None),
    ('Director city', 'Dubai', None),
    ('Director ownership %', '100', None),
    ('Director role/title', 'Manager / Sole Director', None),
    ('Director PEP status', 'No', None),

    ('section', '═══ AUTHORIZED SIGNATORY (POA) ═══', None),
    ('Signatory name', 'SHAHEER KORIKALMANGIRI PUTHEEDATH ABDULLAH KORIKALMANGIRI', None),
    ('Signatory Emirates ID', '784-1990-6574817-2', None),
    ('Signatory authority basis', 'Power of Attorney', None),
    ('POA number', '1/2024/229537', None),
    ('POA issue date', '12/03/2024', None),
    ('POA notary', 'Aisha Jasem Mohammed Hassan Ali, Dubai Courts Notary Public', None),

    ('section', '═══ BUSINESS QUESTIONS ═══', None),
    ('Business type', 'Payment Service Provider / Crypto-Fiat Gateway', None),
    ('Years in operation', '6', None),
    ('Expected monthly volume USD', '100000', None),
    ('Target customer base', 'B2C and B2B in UAE / GCC / Global', None),
    ('Target crypto assets', 'BTC, ETH, USDT, USDC, BNB', None),
    ('Source of funds', 'Operating revenue, partner capital, customer deposits', None),
    ('Use case', 'Fiat-to-crypto on-ramp for UAE customers; merchant payment processing in AED', None),
    ('Why Transak', 'AED currency support; UAE-compliant on-ramp; established regulatory framework', None),

    ('section', '═══ LONG TEXT BOXES ═══', None),
    ('Business description',
     'SICHER MAYOR COMMERCIAL BROKERS L.L.C is a UAE-licensed payment service provider operating since 2019 under DED License 841208. We facilitate fiat-to-crypto on-ramps for retail and corporate clients in the UAE and GCC region, with focus on AED-denominated transactions. Our infrastructure integrates licensed crypto exchanges and acquirers to provide compliant, regulated payment rails for digital asset access.',
     None),
    ('Compliance program',
     'Three-tier KYC/AML structure: Tier 1 (under USD limit) — no KYC; Tier 2 (mid-tier) — email + phone verification; Tier 3 (above threshold) — full Sumsub document KYC. All transactions logged, ID-verified above thresholds, AML monitoring via internal risk engine. Director: Shajahan Pothancherry.',
     None),
    ('Risk profile',
     'Customer base primarily UAE residents and GCC nationals with verified identity. Funds sourced from local UAE bank accounts via licensed acquirers. No high-risk geographies (no Iran, North Korea, Syria, etc.).',
     None),

    ('section', '═══ DOCUMENT UPLOADS ═══', None),
    ('Trade License upload', '[FILE]', 'trade_license'),
    ('Memorandum of Association upload', '[FILES]', 'memorandum'),
    ('Share Register / Partners List upload', '[FILE]', 'partners_list'),
    ('Commercial Register upload', '[FILE]', 'commercial_register'),
    ('Chamber Membership upload', '[FILE]', 'chamber_membership'),
    ('Director Passport upload', '[FILE]', 'director_passport'),
    ('Director Emirates ID front upload', '[FILE]', 'director_eid_front'),
    ('Director Emirates ID back upload', '[FILE]', 'director_eid_back'),
    ('Power of Attorney upload', '[FILE]', 'poa'),
]


def main():
    print()
    print(f'{C}{BOLD}{"=" * 70}{RESET}')
    print(f'{C}{BOLD}  🤖  KYB CLIPBOARD FILLER{RESET}')
    print(f'{C}{BOLD}{"=" * 70}{RESET}')
    print(f'{D}  Form: https://forms.transak.com/kyb{RESET}')
    print(f'{D}  Total fields: {sum(1 for f in FIELDS if f[0] != "section")}{RESET}')
    print()
    print(f'{Y}HOW TO USE:{RESET}')
    print(f'   1. Open Transak KYB form in browser')
    print(f'   2. Click first field on form')
    print(f'   3. Press {G}Enter{RESET} here → value copied to clipboard')
    print(f'   4. {G}Ctrl+V{RESET} in browser → {G}Tab{RESET} to next field')
    print(f'   5. Press {G}Enter{RESET} here for next value')
    print(f'   6. Type {Y}skip{RESET} if a field doesn\'t apply')
    print(f'   7. Type {Y}back{RESET} to redo previous field')
    print(f'   8. Type {Y}quit{RESET} to exit')
    print()
    input(f'{C}Press Enter to start...{RESET}')

    # --from N skips to that non-section field index (1-based)
    start_at = 1
    if '--from' in sys.argv:
        idx = sys.argv.index('--from')
        if idx + 1 < len(sys.argv):
            try:
                start_at = max(1, int(sys.argv[idx + 1]))
            except ValueError:
                pass

    i = 0
    total = len(FIELDS)
    if start_at > 1:
        seen = 0
        for k, f in enumerate(FIELDS):
            if f[0] != 'section':
                seen += 1
                if seen == start_at:
                    i = k
                    print(f'{Y}Resuming at field {start_at}{RESET}')
                    break
    while i < total:
        label, value, file_cat = FIELDS[i]

        if label == 'section':
            print()
            print(f'{B}{BOLD}{value}{RESET}')
            print()
            i += 1
            continue

        # Show field
        print()
        non_section_count = sum(1 for f in FIELDS[:i+1] if f[0] != "section")
        non_section_total = sum(1 for f in FIELDS if f[0] != "section")
        print(f'{D}[{non_section_count}/{non_section_total}]{RESET} {C}{label}{RESET}')

        if file_cat:
            show_files(file_cat)
        else:
            print(f'   {W}{value}{RESET}')

            # Copy to clipboard
            if copy_to_clipboard(value):
                print(f'   {G}✅ Copied to clipboard — paste with Ctrl+V{RESET}')
            else:
                print(f'   {R}❌ Could not copy. Manual: {value}{RESET}')

        # Wait for input
        cmd = input(f'{D}   [Enter=next | skip | back | quit]: {RESET}').strip().lower()
        if cmd == 'quit':
            print(f'\n{Y}Stopped at field {non_section_count}/{non_section_total}{RESET}\n')
            return
        elif cmd == 'back':
            # Go back to previous non-section field
            i -= 1
            while i > 0 and FIELDS[i][0] == 'section':
                i -= 1
            continue
        elif cmd == 'skip':
            print(f'   {D}skipped{RESET}')

        i += 1

    print()
    print(f'{G}{BOLD}{"=" * 70}{RESET}')
    print(f'{G}{BOLD}  ✅ ALL FIELDS DONE — submit the form{RESET}')
    print(f'{G}{BOLD}{"=" * 70}{RESET}')
    print()
    print(f'   {C}Now watching email: python3 temp_mail_listener.py watch{RESET}')
    print()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print(f'\n{Y}Interrupted.{RESET}\n')

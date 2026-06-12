#!/usr/bin/env python3
"""Live key collector — paste API keys, auto-save & verify."""
import os, re, sys, time, urllib.request, urllib.error

ENV_FILE = "/home/kali/payment-gateway/.env"
GATEWAY_MAP = {
    "nowpayments": {"key": "NOWPAYMENTS_API_KEY", "env": "NOWPAYMENTS_ENV", "verify": "https://api.nowpayments.io/v1/status"},
    "coinremitter": {"key": "COINREMITTER_API_KEY", "env": "COINREMITTER_ENV", "verify": "https://api.coinremitter.com/v3/get-coin-rate", "extra": {"COINREMITTER_COIN": "BTC"}},
    "changenow": {"key": "CHANGENOW_API_KEY", "env": "CHANGENOW_ENV", "verify": "https://api.changenow.io/v2/currencies"},
    "changelly": {"key": "CHANGELLY_API_KEY", "env": "CHANGELLY_ENV", "verify": "https://api.changelly.com/v2"},
    "kyrrex": {"key": "KYRREX_API_KEY", "env": "KYRREX_ENV", "verify": "https://api.kyrrex.com/v1/currencies"},
    "guardarian": {"key": "GUARDARIAN_API_KEY", "env": "GUARDARIAN_ENV", "verify": "https://api-payments.guardarian.com/v1/currencies"},
    "charge": {"key": "CHARGE_API_KEY", "env": "CHARGE_ENV", "verify": "https://api.charge.io/v1/checkout/widget"},
    "paybis": {"key": "PAYBIS_API_KEY", "env": "PAYBIS_ENV", "verify": "https://api.paybis.com/v1/currencies"},
    "finchpay": {"key": "FINCHPAY_API_KEY", "env": "FINCHPAY_ENV", "verify": "https://api.finchpay.com/v1/currencies"},
    "kast": {"key": "KAST_API_KEY", "env": "KAST_ENV", "verify": "https://api.kast.co/v1/currencies"},
    "moonpay": {"key": "MOONPAY_API_KEY", "env": "MOONPAY_ENV", "verify": "https://api.moonpay.com/v3/currencies"},
    "ziina": {"key": "ZIINA_API_TOKEN", "env": "ZIINA_ENV", "verify": "https://api-v2.ziina.com/api/payment-intent"},
}

def mask(s):
    s = str(s or "")
    return f"{s[:6]}...{s[-4:]}" if len(s) > 10 else "*" * len(s)

def verify(name, key):
    gw = GATEWAY_MAP.get(name)
    if not gw: return "unknown"
    try:
        req = urllib.request.Request(gw["verify"], headers={"x-api-key": key, "Authorization": f"Bearer {key}"})
        with urllib.request.urlopen(req, timeout=8) as r:
            return f"LIVE ✅ (HTTP {r.status})"
    except urllib.error.HTTPError as e:
        return f"RESPONDING (HTTP {e.code})"
    except Exception as e:
        return f"UNREACHABLE ❌ ({type(e).__name__})"

print("=" * 60)
print("  LIVE KEY COLLECTOR — Paste keys, I verify & save")
print("=" * 60)
print()
print("  TABS OPEN: nowpayments | coinremitter | changelly | changenow")
print("             kyrrex | guardarian | charge | paybis | finchpay")
print("             kast | moonpay | ziina | onramper")
print()
print("  SIGNUP EMAIL:    sichermayor@wshu.net")
print("  SIGNUP PASSWORD: Karmostaji_2026!Secure_GW")
print("  COMPANY:         CryptoEx FZE")
print("  NAME:            Sicher Mayor")
print()
print("  COMMANDS:")
print("    ADD <gateway> <api_key>        — save & verify")
print("    ADD <gateway> <key> <secret>  — save API key + secret")
print("    STATUS                          — show all keys")
print("    VERIFY                          — verify all live keys")
print("    DONE                            — exit")
print()

count = 0
while True:
    try:
        cmd = input(">> ").strip()
    except (EOFError, KeyboardInterrupt):
        break
    if not cmd:
        continue

    parts = cmd.split()
    action = parts[0].lower()

    if action == "done":
        break
    elif action == "status":
        print()
        for name, gw in GATEWAY_MAP.items():
            env = {}
            if os.path.exists(ENV_FILE):
                for line in open(ENV_FILE):
                    if "=" in line and not line.startswith("#"):
                        k, v = line.split("=", 1)
                        env[k.strip()] = v.strip()
            key = env.get(gw["key"], "")
            if key and not key.startswith("test_") and not key.startswith("YOUR_"):
                print(f"  ✅ {name:15s} | {mask(key)}")
            else:
                print(f"  ⏳ {name:15s} | (no key)")
        print()
    elif action == "verify":
        print()
        env = {}
        if os.path.exists(ENV_FILE):
            for line in open(ENV_FILE):
                if "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    env[k.strip()] = v.strip()
        live = 0
        for name, gw in GATEWAY_MAP.items():
            key = env.get(gw["key"], "")
            if not key or key.startswith("test_") or key.startswith("YOUR_"):
                print(f"  ⏭️  {name:15s} — no key")
                continue
            status = verify(name, key)
            if "LIVE" in status or "RESPONDING" in status:
                live += 1
            print(f"  {'✅' if 'LIVE' in status or 'RESPONDING' in status else '❌'} {name:15s} — {status}")
        print(f"\n  🎯 {live} live gateways")
        print()
    elif action == "add" and len(parts) >= 3:
        name = parts[1].lower()
        key_val = parts[2]
        secret_val = parts[3] if len(parts) > 3 else None

        if name not in GATEWAY_MAP:
            print(f"  ❌ Unknown gateway: {name}")
            print(f"  Known: {', '.join(GATEWAY_MAP.keys())}")
            continue

        gw = GATEWAY_MAP[name]
        updates = {gw["key"]: key_val, gw["env"]: "production"}
        if secret_val:
            # Find secret key name
            sk = gw["key"].replace("API_KEY", "SECRET").replace("API_TOKEN", "WEBHOOK_SECRET")
            updates[sk] = secret_val
        if "extra" in gw:
            updates.update(gw["extra"])

        # Write to .env
        content = ""
        if os.path.exists(ENV_FILE):
            content = open(ENV_FILE).read()
        for k, v in updates.items():
            pat = re.compile(rf"^{re.escape(k)}=.*$", re.MULTILINE)
            if pat.search(content):
                content = pat.sub(f"{k}={v}", content)
            else:
                content += f"\n{k}={v}\n"
        with open(ENV_FILE, "w") as f:
            f.write(content)

        # Verify
        status = verify(name, key_val)
        if "LIVE" in status or "RESPONDING" in status:
            count += 1
        print(f"  ✅ {name}: {mask(key_val)} — {status}")
        print(f"  💾 Saved to .env")
        print(f"  🎯 {count} live so far (target: 7)")
        if count >= 7:
            print(f"\n  🎉 GOAL REACHED! {count} live keys!")
        print()
    else:
        print("  Usage: ADD <gateway> <api_key> [secret]")
        print(f"  Gateways: {', '.join(GATEWAY_MAP.keys())}")

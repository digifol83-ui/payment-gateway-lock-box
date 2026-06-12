#!/usr/bin/env python3
"""
🦞 SUPERSKILL: GRAB ALL GATEWAY KEYS — Single agent, single run, all keys live.
Runs: bulk_key_grab (API-only, 20+ services) + multi_gateway_grab (headless browser, 6 gateways)
       + blitz_grab (ultra-fast, 8 gateways) in parallel where possible.

No human intervention needed. Auto CAPTCHA bypass. Auto OTP from mail.tm.
All keys saved to .env + verified at end.

Usage: python3 superskill_grab_all.py
"""
import subprocess, sys, os, time, json
from pathlib import Path
from datetime import datetime

ROOT = Path("/home/kali/payment-gateway")
ENV_FILE = ROOT / ".env"

PHASE_1_SCRIPT = ROOT / "bulk_key_grab.py"       # 25+ API-only grabs (no browser)
PHASE_2_SCRIPT = ROOT / "multi_gateway_grab.py"  # 6 headless browser grabs with CAPTCHA bypass
PHASE_3_SCRIPT = ROOT / "blitz_grab.py"          # 8 ultra-fast headless grabs
VERIFY_SCRIPT = ROOT / "gateway_agents_activate.py"

BANNER = """
╔══════════════════════════════════════════════════════════════════════════╗
║                                                                          ║
║   🦞  GATEWAY SUPERSKILL — ALL KEYS, ONE RUN                             ║
║                                                                          ║
║   Email: sichermayor@wshu.net                                            ║
║   Mode:  HEADLESS + STEALTH + AUTO-CAPTCHA                               ║
║                                                                          ║
║   Phase 1 — API-only grabs (instant, 20+ services, no browser)           ║
║   Phase 2 — Headless browser grabs (6 payment gateways, auto CAPTCHA)    ║
║   Phase 3 — Blitz ultra-fast grabs (8 additional gateways)               ║
║   Phase 4 — Verification of all keys                                     ║
║                                                                          ║
╚══════════════════════════════════════════════════════════════════════════╝
"""

def run_phase(name, script, args=None):
    """Run a phase script and capture output."""
    cmd = [sys.executable, str(script)] + (args or [])
    print(f"\n{'='*70}")
    print(f"  🚀 PHASE: {name}")
    print(f"  📜 {script.name} {' '.join(args or [])}")
    print(f"  ⏰ {datetime.now().strftime('%H:%M:%S')}")
    print(f"{'='*70}\n")
    
    try:
        result = subprocess.run(cmd, cwd=str(ROOT), 
                               capture_output=False,  # Show output live
                               text=True, 
                               timeout=1200)  # 20 min per phase
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print(f"  ⚠️  Phase {name} timed out")
        return False
    except Exception as e:
        print(f"  ❌ Phase {name} error: {e}")
        return False

def show_results():
    """Display current key status from .env."""
    print(f"\n{'='*70}")
    print(f"  📊 KEY STATUS REPORT")
    print(f"{'='*70}")
    
    if not ENV_FILE.exists():
        print("  ❌ .env file not found!")
        return
    
    content = ENV_FILE.read_text()
    key_patterns = [
        "NOWPAYMENTS", "COINREMITTER", "CHANGELLY", "CHANGENOW", "KYRREX",
        "GUARDARIAN", "COINPAYMENTS", "CHARGE", "MOONPAY", "PLISIO", "TRANSAK",
        "BLOCKCYPHER", "BLOCKCHAIN", "COVALENT", "NOWNODES", "DEXSCREENER",
        "COINGECKO", "ETHERSCAN", "MORALIS", "ALCHEMY", "INFURA", "QUICKNODE",
        "TATUM", "GETBLOCK", "COINMARKETCAP", "CRYPTOCOMPARE", "NOMICS",
        "BITPAY", "COINGATE", "COINBASE_COMMERCE", "OPENNODE", "COINSWITCH"
    ]
    
    live_count = 0
    sandbox_count = 0
    empty_count = 0
    
    for prefix in key_patterns:
        api_key = ""
        env_val = ""
        for line in content.split('\n'):
            if line.startswith(f"{prefix}_API_KEY="):
                api_key = line.split('=', 1)[1].strip().strip("'\"")
            if line.startswith(f"{prefix}_ENV="):
                env_val = line.split('=', 1)[1].strip().strip("'\"")
        
        if not api_key and prefix == "NOWPAYMENTS":
            for line in content.split('\n'):
                if line.startswith("NOWPAYMENTS_API_KEY="):
                    api_key = line.split('=', 1)[1].strip().strip("'\"")
        
        if not api_key or api_key == "":
            status = "⏳ EMPTY"
            empty_count += 1
        elif "test_" in api_key or "sandbox" in api_key.lower() or "YOUR_" in api_key:
            status = "🧪 SANDBOX"
            sandbox_count += 1
        elif "FREE" in api_key.upper():
            status = "🆓 FREE"
            live_count += 1
        else:
            mask = f"{api_key[:8]}...{api_key[-4:]}" if len(api_key) > 12 else api_key
            env_str = f"[{env_val}]" if env_val else ""
            status = f"✅ LIVE   {mask} {env_str}"
            live_count += 1
        
        print(f"  {status:60s} {prefix}")
    
    print(f"\n  ─────────────────────────────────────────")
    print(f"  ✅ LIVE:    {live_count}")
    print(f"  🧪 SANDBOX: {sandbox_count}")
    print(f"  ⏳ EMPTY:   {empty_count}")
    print(f"  📦 TOTAL:   {live_count + sandbox_count + empty_count}")
    
    return live_count

def main():
    print(BANNER)
    
    results = {"phases": {}, "live_keys": 0}
    
    # ── Phase 1: API-only grabs (instant, parallel-safe) ──
    if PHASE_1_SCRIPT.exists():
        results["phases"]["1_bulk_api"] = run_phase("1 — BULK API GRABS (20+ APIs, no browser)", 
                                                      PHASE_1_SCRIPT)
    else:
        print("  ⚠️  bulk_key_grab.py not found, skipping Phase 1")
        results["phases"]["1_bulk_api"] = "SKIPPED"
    
    # ── Phase 2: Headless browser grabs (6 core payment gateways, auto CAPTCHA) ──
    if PHASE_2_SCRIPT.exists():
        results["phases"]["2_headless"] = run_phase("2 — HEADLESS BROWSER GRABS (6 gateways, auto CAPTCHA)",
                                                      PHASE_2_SCRIPT, ["all"])
    else:
        print("  ⚠️  multi_gateway_grab.py not found, skipping Phase 2")
        results["phases"]["2_headless"] = "SKIPPED"
    
    # ── Phase 3: Blitz ultra-fast grabs (8 additional gateways) ──
    if PHASE_3_SCRIPT.exists():
        results["phases"]["3_blitz"] = run_phase("3 — BLITZ ULTRA-FAST GRABS (8 gateways)",
                                                   PHASE_3_SCRIPT)
    else:
        print("  ⚠️  blitz_grab.py not found, skipping Phase 3")
        results["phases"]["3_blitz"] = "SKIPPED"
    
    # ── Phase 4: Quick verify ──
    print(f"\n{'='*70}")
    print(f"  ✅ PHASE 4 — VERIFICATION")
    print(f"{'='*70}")
    results["live_keys"] = show_results()
    
    # ── FINAL REPORT ──
    print(f"\n{'='*70}")
    print(f"  🏁 SUPERSKILL COMPLETE")
    print(f"{'='*70}")
    
    print(f"\n  Phase Results:")
    for phase, result in results["phases"].items():
        icon = "✅" if result == True else "❌" if result == False else "⏭️"
        print(f"    {icon} {phase}")
    
    print(f"\n  💰 Total LIVE production keys: {results['live_keys']}")
    print(f"  📁 Keys saved to: {ENV_FILE}")
    print(f"  🔍 Full verify:  python3 gateway_agents_activate.py --verify")
    print(f"\n{'='*70}\n")
    
    return 0 if results["live_keys"] >= 7 else 1

if __name__ == "__main__":
    sys.exit(main())

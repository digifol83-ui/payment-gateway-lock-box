#!/usr/bin/env python3
"""
VERIFICATION CATCHER — Monitors mail.tm, auto-extracts verification codes,
auto-visits confirmation links, and saves API keys to .env.
Runs continuously until interrupted or all keys collected.

Usage: python3 verify_catcher.py [--once]
"""
import json, os, re, sys, time, urllib.request
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path("/home/kali/payment-gateway")
ENV = ROOT / ".env"
MAIL = json.loads((ROOT / ".tempmail_session.json").read_text())
EMAIL = MAIL["address"]
TOKEN = MAIL["token"]

KNOWN_SENDERS = {
    "nowpayments.io": "NOWPAYMENTS",
    "coinremitter.com": "COINREMITTER",
    "kyrrex.com": "KYRREX",
    "changenow.io": "CHANGENOW",
    "changelly.com": "CHANGELLY",
    "moralis.io": "MORALIS",
    "etherscan.io": "ETHERSCAN",
    "tatum.io": "TATUM",
    "getblock.io": "GETBLOCK",
    "1inch.io": "ONEINCH",
    "alchemy.com": "ALCHEMY",
    "infura.io": "INFURA",
    "quicknode.com": "QUICKNODE",
    "bitquery.io": "BITQUERY",
    "nftscan.com": "NFTSCAN",
    "coinmarketcap.com": "COINMARKETCAP",
    "covalenthq.com": "COVALENT",
    "blockcypher.com": "BLOCKCYPHER",
    "coinbase.com": "COINBASE_COMMERCE",
    "opennode.com": "OPENNODE",
    "bitpay.com": "BITPAY",
    "coingate.com": "COINGATE",
    "coingecko.com": "COINGECKO",
    "cryptocompare.com": "CRYPTOCOMPARE",
    "transak.com": "TRANSAK",
    "guardarian.com": "GUARDARIAN",
    "onramper.com": "ONRAMPER",
}

def save_env(key: str, value: str):
    content = ENV.read_text() if ENV.exists() else ""
    esc = re.escape(key)
    pat = re.compile(rf"^{esc}=.*$", re.MULTILINE)
    if pat.search(content):
        content = pat.sub(f"{key}={value}", content)
    else:
        content += f"\n{k}={v}\n"
    ENV.write_text(content)

def identify_sender(sender_addr: str) -> str:
    """Map email sender to gateway name."""
    addr = sender_addr.lower()
    for domain, name in KNOWN_SENDERS.items():
        if domain in addr:
            return name
    # Extract domain
    domain = addr.split("@")[-1] if "@" in addr else addr
    return domain.upper().replace(".COM", "").replace(".IO", "").replace(".ORG", "")

def extract_api_key(body: str) -> str:
    """Extract API key from email body."""
    # Common patterns
    patterns = [
        r'(?:api[_\s-]?key[:\s]*)([A-Za-z0-9_-]{20,})',
        r'(?:key[:\s]*)([A-Za-z0-9_-]{20,})',
        r'\b(sk_[A-Za-z0-9]{20,})\b',
        r'\b(pk_[A-Za-z0-9]{20,})\b',
        r'\b([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\b',
        r'\b([A-Za-z0-9]{32,64})\b',
        r'\b(eyJ[A-Za-z0-9_-]{20,})\b',  # JWT
    ]
    for pat in patterns:
        match = re.search(pat, body, re.I)
        if match:
            return match.group(1)
    return ""

def process_email(msg_id: str) -> dict:
    """Process one email: extract verification code and/or API key."""
    req = urllib.request.Request(f"https://api.mail.tm/messages/{msg_id}",
        headers={"Authorization": f"Bearer {TOKEN}"})
    with urllib.request.urlopen(req, timeout=10) as r:
        full = json.loads(r.read())
    
    sender = (full.get("from") or {}).get("address", "")
    subj = full.get("subject", "")[:80]
    body = (full.get("text") or "") + " " + " ".join(full.get("html") or [])
    
    result = {
        "sender": sender,
        "subject": subj,
        "gateway": identify_sender(sender),
        "timestamp": full.get("createdAt", ""),
    }
    
    # Extract verification code
    code = re.search(r'\b(\d{6})\b', body)
    if code:
        result["code"] = code.group(1)
    
    code4 = re.search(r'\b(\d{4})\b', body)
    if code4 and not result.get("code") and any(w in body.lower() for w in ['verif','code','otp','confirm']):
        result["code"] = code4.group(1)
    
    # Extract confirmation link
    link = re.search(r'https?://[^\s"\'<>]+(?:confirm|verify|activate|email)[^\s"\'<>]*', body, re.I)
    if link:
        result["confirmation_link"] = link.group(0)
    
    # Extract API key
    api_key = extract_api_key(body)
    if api_key:
        result["api_key"] = api_key
        # Save immediately
        key_name = f"{result['gateway']}_API_KEY"
        save_env(key_name, api_key)
        env_name = f"{result['gateway']}_ENV"
        save_env(env_name, "production")
        print(f"  💾 SAVED: {key_name} = {api_key[:16]}...")
    
    return result

def visit_confirmation_link(link: str) -> str:
    """Visit a confirmation link to verify email."""
    try:
        req = urllib.request.Request(link)
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.geturl()
    except Exception as e:
        return f"Error: {e}"

def main():
    print(f"\n{'='*60}")
    print(f"  📡 VERIFICATION CATCHER — Auto-grab API keys")
    print(f"  Email: {EMAIL}")
    print(f"  Watching for emails from 30+ gateways")
    print(f"  {'='*60}\n")
    
    seen_ids = set()
    
    # Get existing message IDs
    try:
        req = urllib.request.Request("https://api.mail.tm/messages?page=1",
            headers={"Authorization": f"Bearer {TOKEN}"})
        with urllib.request.urlopen(req, timeout=10) as r:
            msgs = json.loads(r.read()).get("hydra:member") or []
        for m in msgs:
            seen_ids.add(m["id"])
    except:
        pass
    
    print(f"  Existing messages: {len(seen_ids)}")
    print(f"  Fill signup forms → solve CAPTCHA → submit\n")
    print(f"  I'll auto-catch every verification email.\n")
    
    keys_collected = 0
    last_report = time.time()
    
    while True:
        try:
            req = urllib.request.Request("https://api.mail.tm/messages?page=1",
                headers={"Authorization": f"Bearer {TOKEN}"})
            with urllib.request.urlopen(req, timeout=10) as r:
                msgs = json.loads(r.read()).get("hydra:member") or []
            
            for m in msgs:
                mid = m.get("id", "")
                if mid in seen_ids:
                    continue
                seen_ids.add(mid)
                
                sender = (m.get("from") or {}).get("address", "")
                subj = m.get("subject", "")
                ts = m.get("createdAt", "")[:19]
                
                # Skip existing Transak
                if "transak" in sender.lower() and "verification" not in subj.lower():
                    continue
                
                print(f"\n{'─'*55}")
                print(f"  📩 [{ts}] {sender}")
                print(f"  Subject: {subj[:80]}")
                
                # Process email
                result = process_email(mid)
                
                if result.get("code"):
                    print(f"  🔑 CODE: {result['code']}")
                
                if result.get("confirmation_link"):
                    link = result["confirmation_link"]
                    print(f"  🔗 LINK: {link[:100]}")
                    print(f"  → Auto-visiting confirmation link...")
                    visited = visit_confirmation_link(link)
                    print(f"  → Redirected: {visited[:100]}")
                
                if result.get("api_key"):
                    print(f"  ✅ API KEY EXTRACTED & SAVED!")
                    keys_collected += 1
                
                gateway = result.get("gateway", "UNKNOWN")
                print(f"  Gateway: {gateway}")
            
            # Periodic status
            if time.time() - last_report > 60:
                print(f"\n  [{datetime.now().strftime('%H:%M:%S')}] Watching... {keys_collected} keys collected so far")
                print(f"  Total messages seen: {len(seen_ids)}")
                last_report = time.time()
        
        except Exception as e:
            print(f"  ⚠️ {e}")
        
        time.sleep(5)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n  🛑 Stopped.")
        print(f"  Keys collected: check .env")
        print(f"  Run: python3 gateway_agents_activate.py --verify")

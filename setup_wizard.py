#!/usr/bin/env python3
"""
BeastPay OpenClaw — Credentials Setup Wizard
Walks through every missing API key, validates what it can, writes .env.

Run: python3 setup_wizard.py
"""
import os
import re
import sys
import httpx
import secrets
from pathlib import Path

ENV_FILE = Path(__file__).parent / ".env"

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Prompt, Confirm
    from rich import box
    from rich.table import Table
    console = Console()
    USE_RICH = True
except ImportError:
    USE_RICH = False

def p(msg, style=""):
    if USE_RICH:
        console.print(msg)
    else:
        print(re.sub(r'\[.*?\]', '', msg))

def ask(label, default="", password=False):
    if USE_RICH:
        return Prompt.ask(f"  {label}", default=default, password=password) or default
    val = input(f"  {label} [{default}]: ").strip()
    return val or default

def confirm(label, default=True):
    if USE_RICH:
        return Confirm.ask(f"  {label}", default=default)
    ans = input(f"  {label} [{'Y/n' if default else 'y/N'}]: ").strip().lower()
    return (ans in ("y","yes")) if ans else default

def banner():
    if USE_RICH:
        console.clear()
        console.print(Panel(
            "[bold cyan]BeastPay OpenClaw — Setup Wizard[/]\n"
            "[dim]Configure all API keys and write .env[/]",
            border_style="cyan", width=60
        ))
    else:
        print("\n=== BeastPay Setup Wizard ===\n")


# ─── Read existing .env values ───────────────────────────────────────────────
def read_env() -> dict:
    values = {}
    if not ENV_FILE.exists():
        return values
    for line in ENV_FILE.read_text().splitlines():
        line = line.strip()
        if line.startswith("export "):
            line = line[7:]
        m = re.match(r'^([A-Z_]+)="?([^"]*)"?$', line)
        if m:
            values[m.group(1)] = m.group(2)
    return values


def write_env_key(key: str, value: str):
    """Update a single key in .env in-place."""
    content = ENV_FILE.read_text()
    pattern = rf'(export {key}=)"[^"]*"'
    replacement = f'export {key}="{value}"'
    if re.search(pattern, content):
        content = re.sub(pattern, replacement, content)
    else:
        content += f'\nexport {key}="{value}"\n'
    ENV_FILE.write_text(content)


# ─── Validators ──────────────────────────────────────────────────────────────
def check_telegram(token: str, chat_id: str) -> bool:
    try:
        r = httpx.get(f"https://api.telegram.org/bot{token}/getMe", timeout=5)
        return r.status_code == 200 and r.json().get("ok")
    except Exception:
        return False

def check_anthropic(key: str) -> bool:
    try:
        r = httpx.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json={"model": "claude-haiku-4-5-20251001", "max_tokens": 5, "messages": [{"role": "user", "content": "hi"}]},
            timeout=8,
        )
        return r.status_code == 200
    except Exception:
        return False

def check_nowpayments(key: str, env: str) -> bool:
    base = "https://api-sandbox.nowpayments.io/v1" if env == "sandbox" else "https://api.nowpayments.io/v1"
    try:
        r = httpx.get(f"{base}/status", headers={"x-api-key": key}, timeout=8)
        return r.status_code == 200
    except Exception:
        return False

def check_stripe(key: str) -> bool:
    try:
        r = httpx.get(
            "https://api.stripe.com/v1/balance",
            auth=(key, ""),
            headers={"Stripe-Version": "2023-10-16"},
            timeout=8,
        )
        return r.status_code == 200
    except Exception:
        return False


# ─── Sections ────────────────────────────────────────────────────────────────
def section(title):
    if USE_RICH:
        console.rule(f"[bold cyan]{title}[/]")
    else:
        print(f"\n── {title} ──")


def wizard_security(env: dict) -> dict:
    section("Security Keys")
    changes = {}

    # Admin key
    current_admin = env.get("ADMIN_API_KEY", "")
    if not current_admin or current_admin == "admin-secret-change-me":
        new_key = "bp_admin_" + secrets.token_hex(20)
        p(f"  [green]Generated new ADMIN_API_KEY:[/] {new_key}")
        changes["ADMIN_API_KEY"] = new_key
    else:
        p(f"  [dim]ADMIN_API_KEY already set.[/]")

    # Encryption key
    current_enc = env.get("CREDENTIAL_ENCRYPTION_KEY", "")
    if not current_enc or len(current_enc) < 20:
        new_enc = secrets.token_hex(32)
        p(f"  [green]Generated CREDENTIAL_ENCRYPTION_KEY:[/] {new_enc[:16]}…")
        changes["CREDENTIAL_ENCRYPTION_KEY"] = new_enc
    else:
        p(f"  [dim]CREDENTIAL_ENCRYPTION_KEY already set.[/]")

    return changes


def wizard_telegram(env: dict) -> dict:
    section("Telegram Bot")
    changes = {}
    token   = env.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = env.get("TELEGRAM_CHAT_ID", "")

    p(f"  Current token:   [dim]{'set' if token else 'NOT SET'}[/]")
    p(f"  Current chat ID: [dim]{chat_id or 'NOT SET'}[/]")

    if confirm("Configure Telegram?", default=not bool(token)):
        token   = ask("Bot token (from @BotFather)", default=token)
        chat_id = ask("Chat ID (@Watchpipe = 933545457)", default=chat_id or "933545457")
        with (console.status("Validating…") if USE_RICH else open(os.devnull)):
            ok = check_telegram(token, chat_id)
        p(f"  {'[green]✓ Valid[/]' if ok else '[red]✗ Could not validate — saved anyway[/]'}")
        changes["TELEGRAM_BOT_TOKEN"] = token
        changes["TELEGRAM_CHAT_ID"]   = chat_id

    return changes


def wizard_anthropic(env: dict) -> dict:
    section("Anthropic / Claude AI (Lockbox)")
    changes = {}
    key = env.get("ANTHROPIC_API_KEY", "")
    p(f"  Current key: [dim]{'set (' + key[:12] + '…)' if key else 'NOT SET'}[/]")

    if not key or confirm("Update Anthropic API key?", default=False):
        key = ask("Anthropic API key (sk-ant-…)", default=key, password=True)
        if key:
            with (console.status("Validating…") if USE_RICH else open(os.devnull)):
                ok = check_anthropic(key)
            p(f"  {'[green]✓ Connected to Claude[/]' if ok else '[red]✗ Could not validate[/]'}")
            changes["ANTHROPIC_API_KEY"] = key

    return changes


def wizard_nowpayments(env: dict) -> dict:
    section("NOWPayments (Crypto — no KYC)")
    changes = {}
    key    = env.get("NOWPAYMENTS_API_KEY", "")
    secret = env.get("NOWPAYMENTS_IPN_SECRET", "")
    np_env = env.get("NOWPAYMENTS_ENV", "sandbox")
    p(f"  Current key: [dim]{'set' if key else 'NOT SET'}[/]")

    if confirm("Configure NOWPayments?", default=not bool(key)):
        p("  [dim]Sign up free at nowpayments.io → API Keys[/]")
        key    = ask("API Key", default=key, password=True)
        secret = ask("IPN Secret", default=secret, password=True)
        np_env = ask("Environment (sandbox/production)", default=np_env)
        if key:
            with (console.status("Validating…") if USE_RICH else open(os.devnull)):
                ok = check_nowpayments(key, np_env)
            p(f"  {'[green]✓ NOWPayments connected[/]' if ok else '[yellow]⚠ Could not validate — saved anyway[/]'}")
        changes["NOWPAYMENTS_API_KEY"]    = key
        changes["NOWPAYMENTS_IPN_SECRET"] = secret
        changes["NOWPAYMENTS_ENV"]        = np_env

    return changes


def wizard_stripe(env: dict) -> dict:
    section("Stripe")
    changes = {}
    sk = env.get("STRIPE_SECRET_KEY", "")
    pk = env.get("STRIPE_PUBLISHABLE_KEY", "")
    wh = env.get("STRIPE_WEBHOOK_SECRET", "")
    p(f"  Secret key: [dim]{'set' if sk and not sk.startswith('sk_placeholder') else 'NOT SET'}[/]")

    if confirm("Configure Stripe?", default=not bool(sk and not sk.startswith("sk_placeholder"))):
        p("  [dim]dashboard.stripe.com → Developers → API Keys[/]")
        sk = ask("Secret key (sk_test_… or sk_live_…)", default=sk, password=True)
        pk = ask("Publishable key (pk_…)", default=pk)
        wh = ask("Webhook secret (whsec_…)", default=wh, password=True)
        if sk:
            with (console.status("Validating…") if USE_RICH else open(os.devnull)):
                ok = check_stripe(sk)
            p(f"  {'[green]✓ Stripe connected[/]' if ok else '[yellow]⚠ Could not validate[/]'}")
        mode = "test" if "test" in sk else "live"
        changes["STRIPE_SECRET_KEY"]      = sk
        changes["STRIPE_PUBLISHABLE_KEY"] = pk
        changes["STRIPE_WEBHOOK_SECRET"]  = wh
        changes["STRIPE_ENV"]             = mode

    return changes


def wizard_transak(env: dict) -> dict:
    section("Transak")
    changes = {}
    key = env.get("TRANSAK_API_KEY","")
    if key and key != "YOUR_TRANSAK_API_KEY":
        p("  [dim]Transak already configured.[/]"); return changes
    if confirm("Configure Transak?", default=False):
        p("  [dim]dashboard.transak.com → Integrations → API Keys[/]")
        changes["TRANSAK_API_KEY"]  = ask("API Key", password=True)
        changes["TRANSAK_ACCESS_TOKEN"] = ask("Partner Access Token (for webhook JWT verification)", password=True)
        changes["TRANSAK_SECRET"]   = ""  # legacy
        changes["TRANSAK_ENV"]      = ask("Environment (STAGING/PRODUCTION)", default="STAGING")
    return changes


def wizard_moonpay(env: dict) -> dict:
    section("MoonPay")
    changes = {}
    key = env.get("MOONPAY_API_KEY","")
    if key and key != "YOUR_MOONPAY_API_KEY":
        p("  [dim]MoonPay already configured.[/]"); return changes
    if confirm("Configure MoonPay?", default=False):
        p("  [dim]dashboard.moonpay.com → Developers → API Keys[/]")
        changes["MOONPAY_API_KEY"]  = ask("API Key", password=True)
        changes["MOONPAY_SECRET"]   = ask("Secret", password=True)
        changes["MOONPAY_ENV"]      = ask("Environment (sandbox/production)", default="sandbox")
    return changes


def wizard_whatsapp(env: dict) -> dict:
    section("WhatsApp Cloud API")
    changes = {}
    token = env.get("WHATSAPP_TOKEN","")
    p(f"  Current token: [dim]{'set' if token else 'NOT SET'}[/]")
    if confirm("Configure WhatsApp?", default=not bool(token)):
        p("  [dim]Meta Business → WhatsApp → API Setup[/]")
        changes["WHATSAPP_TOKEN"]    = ask("Permanent access token", password=True)
        changes["WHATSAPP_PHONE_ID"] = ask("Phone Number ID")
        changes["WHATSAPP_TO"]       = ask("Recipient number (no +, e.g. 911234567890)")
    return changes


def wizard_sumsub(env: dict) -> dict:
    section("Sumsub KYC")
    changes = {}
    tok = env.get("SUMSUB_APP_TOKEN","")
    p(f"  Current token: [dim]{'set' if tok else 'NOT SET'}[/]")
    if confirm("Configure Sumsub?", default=not bool(tok)):
        p("  [dim]dashboard.sumsub.com → Developers → App tokens[/]")
        changes["SUMSUB_APP_TOKEN"]  = ask("App token", password=True)
        changes["SUMSUB_SECRET_KEY"] = ask("Secret key", password=True)
        changes["SUMSUB_LEVEL_NAME"] = ask("KYC level name", default=env.get("SUMSUB_LEVEL_NAME","basic-kyc-level"))
    return changes


def wizard_opencorporates(env: dict) -> dict:
    section("OpenCorporates (Company Lookup)")
    changes = {}
    tok = env.get("OPENCORPORATES_API_TOKEN","")
    p(f"  Current token: [dim]{'set' if tok else 'NOT SET'}[/]")
    if confirm("Configure OpenCorporates?", default=not bool(tok)):
        p("  [dim]opencorporates.com → Account → API Token[/]")
        changes["OPENCORPORATES_API_TOKEN"] = ask("API Token", password=True)
    return changes


def wizard_imap(env: dict) -> dict:
    section("IMAP Email (OTP auto-extraction)")
    changes = {}
    host = env.get("IMAP_HOST","")
    p(f"  Current host: [dim]{host or 'NOT SET'}[/]")
    if confirm("Configure IMAP for OTP auto-extraction?", default=not bool(host)):
        p("  [dim]Gmail: enable 2FA → App Passwords → create one for 'Mail'[/]")
        changes["IMAP_HOST"]     = ask("IMAP host", default="imap.gmail.com")
        changes["IMAP_PORT"]     = ask("IMAP port", default="993")
        changes["IMAP_USER"]     = ask("Email address")
        changes["IMAP_PASSWORD"] = ask("App password", password=True)
    return changes


# ─── Main ────────────────────────────────────────────────────────────────────
def main():
    banner()
    env = read_env()

    all_changes = {}
    for wizard in [
        wizard_security,
        wizard_telegram,
        wizard_anthropic,
        wizard_nowpayments,
        wizard_stripe,
        wizard_transak,
        wizard_moonpay,
        wizard_whatsapp,
        wizard_sumsub,
        wizard_opencorporates,
        wizard_imap,
    ]:
        try:
            changes = wizard(env)
            all_changes.update(changes)
            env.update(changes)
        except KeyboardInterrupt:
            p("\n  [dim]Skipped.[/]")
            continue

    if not all_changes:
        p("\n  [dim]Nothing changed.[/]")
        return

    section("Summary")
    if USE_RICH:
        t = Table(box=box.SIMPLE)
        t.add_column("Key", style="bold")
        t.add_column("Value")
        for k, v in all_changes.items():
            masked = v[:4] + "…" + v[-4:] if len(v) > 12 else "****"
            t.add_row(k, masked)
        console.print(t)

    if confirm(f"Write {len(all_changes)} change(s) to .env?", default=True):
        for k, v in all_changes.items():
            write_env_key(k, v)
        p(f"\n  [green]✓ .env updated with {len(all_changes)} key(s).[/]")
        p("  [dim]Restart the server: source .env && uvicorn server:app --host 0.0.0.0 --port 8000[/]")
    else:
        p("  [yellow]Aborted — no changes written.[/]")


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, EOFError):
        print("\n  Cancelled.")

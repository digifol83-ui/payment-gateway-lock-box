#!/usr/bin/env python3
"""
BeastPay OpenClaw — Terminal UI
Run: source .env && python3 tui.py
"""
import os
import sys
import json
import csv
import time
import httpx
from datetime import datetime
from io import StringIO

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.columns import Columns
from rich.text import Text
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.live import Live
from rich.layout import Layout
from rich.align import Align
from rich import box

# ─── Config ──────────────────────────────────────────────────────────────────
BASE_URL  = os.getenv("BASE_URL", "http://localhost:8000")
ADMIN_KEY = os.getenv("ADMIN_API_KEY", "admin-secret-change-me")
HEADERS   = {"X-Api-Key": ADMIN_KEY, "Content-Type": "application/json"}

console = Console()


# ─── API ─────────────────────────────────────────────────────────────────────
def api(method: str, path: str, **kwargs) -> dict | list | None:
    try:
        with httpx.Client(timeout=10, headers=HEADERS) as client:
            resp = client.request(method, f"{BASE_URL}{path}", **kwargs)
        if resp.status_code in (200, 201):
            return resp.json()
        console.print(f"  [red]API {resp.status_code}:[/] {resp.text[:120]}")
        return None
    except httpx.ConnectError:
        console.print("  [red]Server offline.[/] Start: [bold]source .env && uvicorn server:app --host 0.0.0.0 --port 8000[/]")
        return None
    except Exception as e:
        console.print(f"  [red]Error:[/] {e}")
        return None


def health() -> bool:
    try:
        r = httpx.get(f"{BASE_URL}/health", timeout=2)
        return r.status_code == 200
    except Exception:
        return False


# ─── Helpers ─────────────────────────────────────────────────────────────────
STATUS_COLOR = {
    "pending":    "yellow",
    "processing": "cyan",
    "completed":  "green",
    "failed":     "red",
    "refunded":   "magenta",
    "verified":   "green",
    "active":     "green",
}

def sc(status: str) -> str:
    c = STATUS_COLOR.get(str(status).lower(), "white")
    return f"[{c}]{status}[/{c}]"

def ts(iso: str) -> str:
    try:
        return datetime.fromisoformat(iso).strftime("%m/%d %H:%M")
    except Exception:
        return iso or "—"

def pause():
    console.print()
    Prompt.ask("  [dim]Press Enter to continue[/]", default="")


# ─── Banner ───────────────────────────────────────────────────────────────────
BANNER = r"""
 ██████╗ ███████╗ █████╗ ███████╗████████╗██████╗  █████╗ ██╗   ██╗
 ██╔══██╗██╔════╝██╔══██╗██╔════╝╚══██╔══╝██╔══██╗██╔══██╗╚██╗ ██╔╝
 ██████╔╝█████╗  ███████║███████╗   ██║   ██████╔╝███████║ ╚████╔╝
 ██╔══██╗██╔══╝  ██╔══██║╚════██║   ██║   ██╔═══╝ ██╔══██║  ╚██╔╝
 ██████╔╝███████╗██║  ██║███████║   ██║   ██║     ██║  ██║   ██║
 ╚═════╝ ╚══════╝╚═╝  ╚═╝╚══════╝   ╚═╝   ╚═╝     ╚═╝  ╚═╝   ╚═╝
"""

def draw_banner():
    console.clear()
    online = health()
    dot = "[green]● ONLINE[/]" if online else "[red]● OFFLINE[/]"
    console.print(Text(BANNER, style="bold cyan"), justify="left")
    console.print(f"  [dim]by OpenClaw  ·  @Openclawbeastpay_bot[/]  |  [dim]{BASE_URL}[/]  {dot}")
    console.rule(style="dim")


# ─── Main Menu ────────────────────────────────────────────────────────────────
MENU = [
    ("1", "Dashboard / Stats",          "cyan"),
    ("2", "Payment Links",              "cyan"),
    ("3", "Create Payment Link",        "cyan"),
    ("4", "All Payments",              "cyan"),
    ("5", "Check Payment",             "cyan"),
    ("6", "Filter Payments by Status", "cyan"),
    ("7", "Add Merchant",              "cyan"),
    ("8", "Export CSV",               "cyan"),
    ("9", "Health Check",             "cyan"),
    ("V", "Merchant Verification",    "magenta"),
    ("T", "Telegram",                 "blue"),
    ("W", "WhatsApp",                 "blue"),
    ("N", "NOWPayments",              "blue"),
    ("K", "KYC / Sumsub",            "blue"),
    ("L", "Lockbox (Card Parser)",    "blue"),
    ("H", "Lockbox History",          "blue"),
    ("S", "Stripe",                   "blue"),
    ("C", "Stored Credentials",       "blue"),
    ("Q", "Quit",                     "dim"),
]

def draw_menu():
    table = Table(box=box.ROUNDED, border_style="dim", show_header=False, padding=(0, 2))
    table.add_column(width=4)
    table.add_column()
    for key, label, color in MENU:
        table.add_row(f"[bold {color}][{key}][/]", f"[{color}]{label}[/]")
    console.print(Panel(table, title="[bold]MAIN MENU[/]", border_style="cyan", width=44))


# ─── Screens ─────────────────────────────────────────────────────────────────

def screen_dashboard():
    draw_banner()
    console.print(Panel("[bold]Dashboard[/]", border_style="cyan"))
    stats  = api("GET", "/api/stats") or {}
    vstats = api("GET", "/api/verification/stats") or {}

    t = Table(box=box.SIMPLE, show_header=False, padding=(0, 3))
    t.add_column(style="dim")
    t.add_column(style="bold")
    t.add_row("Total Payments",  str(stats.get("total_payments", 0)))
    t.add_row("Completed",       f"[green]{stats.get('completed', 0)}[/]")
    t.add_row("Pending",         f"[yellow]{stats.get('pending', 0)}[/]")
    t.add_row("Failed",          f"[red]{stats.get('failed', 0)}[/]")
    t.add_row("Volume (USD)",    f"[bold green]${stats.get('total_volume_usd', 0):,.2f}[/]")
    t.add_row("Conversion Rate", f"{stats.get('conversion_rate', 0)}%")
    t.add_row("Active Links",    str(stats.get("active_links", 0)))

    v = Table(box=box.SIMPLE, show_header=False, padding=(0, 3))
    v.add_column(style="dim")
    v.add_column(style="bold")
    v.add_row("Merchants",       str(vstats.get("total_merchants", 0)))
    v.add_row("Verified",        f"[green]{vstats.get('verified', 0)}[/]")
    v.add_row("Pending KYC",     f"[yellow]{vstats.get('pending', 0)}[/]")
    v.add_row("GW Registrations",str(vstats.get("gateway_registrations_total", 0)))
    v.add_row("GW Verified",     f"[green]{vstats.get('gateway_registrations_verified', 0)}[/]")

    console.print(Columns([
        Panel(t, title="Payments", border_style="green"),
        Panel(v, title="Verification", border_style="magenta"),
    ]))
    pause()


def screen_links():
    draw_banner()
    console.print(Panel("[bold]Payment Links[/]", border_style="cyan"))
    links = api("GET", "/api/links") or []
    if not links:
        console.print("  [dim]No links found.[/]")
        pause(); return

    t = Table(box=box.SIMPLE_HEAVY, show_lines=True)
    t.add_column("ID",          style="dim", width=18)
    t.add_column("Amount",      justify="right")
    t.add_column("Crypto")
    t.add_column("Wallet",      width=20)
    t.add_column("Uses",        justify="right")
    t.add_column("Active")
    t.add_column("Created")

    for l in links[:30]:
        amt = f"${l['amount']:.2f} {l['fiat_currency']}" if l.get("amount") else "[dim]open[/]"
        wallet = (l.get("wallet_address") or "")[:18] + "…"
        t.add_row(
            l["id"],
            amt,
            l.get("crypto_currency") or "—",
            wallet,
            str(l.get("use_count", 0)),
            "[green]●[/]" if l.get("is_active") else "[red]●[/]",
            ts(l.get("created_at", "")),
        )
    console.print(t)
    pause()


def screen_create_link():
    draw_banner()
    console.print(Panel("[bold]Create Payment Link[/]", border_style="cyan"))
    wallet  = Prompt.ask("  Wallet address")
    amount_s = Prompt.ask("  Amount (leave blank for open)", default="")
    fiat    = Prompt.ask("  Fiat currency", default="USD")
    crypto  = Prompt.ask("  Crypto", default="USDT")
    desc    = Prompt.ask("  Description", default="")

    payload = {
        "wallet_address":  wallet,
        "fiat_currency":   fiat,
        "crypto_currency": crypto,
        "description":     desc,
        "is_reusable":     True,
    }
    if amount_s:
        payload["amount"] = float(amount_s)

    with console.status("Creating link…"):
        result = api("POST", "/api/links", json=payload)

    if result:
        console.print(Panel(
            f"[green]Link created![/]\n\n"
            f"[bold]ID:[/]  {result['id']}\n"
            f"[bold]URL:[/] {result.get('payment_url', '')}",
            border_style="green"
        ))
    pause()


def screen_payments():
    draw_banner()
    console.print(Panel("[bold]All Payments[/]", border_style="cyan"))
    payments = api("GET", "/api/payments?limit=50") or []
    if not payments:
        console.print("  [dim]No payments yet.[/]")
        pause(); return

    t = Table(box=box.SIMPLE_HEAVY, show_lines=True)
    t.add_column("ID",       width=10, style="dim")
    t.add_column("Amount",   justify="right")
    t.add_column("Provider")
    t.add_column("Status")
    t.add_column("Email",    width=22)
    t.add_column("Created")

    for p in payments:
        pid = p["id"][:8] + "…"
        amt = f"${p['amount']:.2f} {p['fiat_currency']}"
        t.add_row(
            pid, amt,
            p.get("provider", "—"),
            sc(p.get("status", "")),
            p.get("customer_email") or "—",
            ts(p.get("created_at", "")),
        )
    console.print(t)
    pause()


def screen_check_payment():
    draw_banner()
    console.print(Panel("[bold]Check Payment[/]", border_style="cyan"))
    pid = Prompt.ask("  Payment ID")
    p = api("GET", f"/api/payments/{pid}")
    if not p:
        pause(); return

    t = Table(box=box.SIMPLE, show_header=False, padding=(0, 3))
    t.add_column(style="dim")
    t.add_column()
    for k, v in p.items():
        if v is not None:
            val = sc(str(v)) if k == "status" else str(v)
            t.add_row(k, val)
    console.print(Panel(t, title=f"Payment {pid[:12]}…", border_style="cyan"))
    pause()


def screen_filter_payments():
    draw_banner()
    console.print(Panel("[bold]Filter Payments[/]", border_style="cyan"))
    status = Prompt.ask("  Status", choices=["pending","processing","completed","failed","refunded"], default="completed")
    payments = api("GET", f"/api/payments?status={status}&limit=50") or []

    t = Table(box=box.SIMPLE_HEAVY, title=f"{status.upper()} payments")
    t.add_column("ID", width=10, style="dim")
    t.add_column("Amount", justify="right")
    t.add_column("Provider")
    t.add_column("Email", width=22)
    t.add_column("Created")

    for p in payments:
        t.add_row(
            p["id"][:8] + "…",
            f"${p['amount']:.2f} {p['fiat_currency']}",
            p.get("provider", "—"),
            p.get("customer_email") or "—",
            ts(p.get("created_at", "")),
        )
    console.print(t)
    pause()


def screen_add_merchant():
    draw_banner()
    console.print(Panel("[bold]Add Merchant[/]", border_style="cyan"))
    name    = Prompt.ask("  Company / Merchant name")
    email   = Prompt.ask("  Email")
    webhook = Prompt.ask("  Webhook URL (optional)", default="")

    payload = {"name": name, "email": email}
    if webhook:
        payload["webhook_url"] = webhook

    with console.status("Creating merchant…"):
        result = api("POST", "/api/merchants", json=payload)

    if result:
        console.print(Panel(
            f"[green]Merchant created![/]\n\n"
            f"[bold]ID:[/]      {result.get('id')}\n"
            f"[bold]API Key:[/] [yellow]{result.get('api_key')}[/]",
            border_style="green"
        ))
    pause()


def screen_export_csv():
    draw_banner()
    console.print(Panel("[bold]Export Payments to CSV[/]", border_style="cyan"))
    payments = api("GET", "/api/payments?limit=1000") or []
    if not payments:
        console.print("  [dim]No payments to export.[/]")
        pause(); return

    fname = f"payments_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    fpath = os.path.join(os.path.dirname(__file__), fname)
    with open(fpath, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=payments[0].keys())
        writer.writeheader()
        writer.writerows(payments)

    console.print(f"\n  [green]Exported {len(payments)} rows →[/] {fpath}")
    pause()


def screen_health():
    draw_banner()
    console.print(Panel("[bold]Health Check[/]", border_style="cyan"))
    checks = [
        ("Core server",    "/health",                    "GET"),
        ("Telegram",       "/api/telegram/status",       "GET"),
        ("WhatsApp",       "/api/whatsapp/status",       "GET"),
        ("NOWPayments",    "/api/nowpayments/status",    "GET"),
        ("Stripe",         "/api/stripe/status",         "GET"),
        ("KYC / Sumsub",  "/api/kyc/config",            "GET"),
        ("Lockbox AI",    "/api/lockbox/status",        "GET"),
        ("Verification",   "/api/verification/status",   "GET"),
    ]

    t = Table(box=box.SIMPLE, show_header=True)
    t.add_column("Service",  style="bold")
    t.add_column("Status")
    t.add_column("Detail",   style="dim")

    for name, path, method in checks:
        data = api(method, path)
        if data is None:
            t.add_row(name, "[red]● FAIL[/]", "No response")
        else:
            enabled = data.get("enabled", True)
            if isinstance(enabled, bool):
                dot = "[green]● OK[/]" if enabled else "[yellow]● OFF[/]"
            else:
                dot = "[green]● OK[/]"
            detail = ""
            for k in ("api_key","token","env","mode","model"):
                if k in data:
                    detail = f"{k}: {data[k]}"
                    break
            t.add_row(name, dot, detail)

    console.print(t)
    pause()


# ─── Verification screens ─────────────────────────────────────────────────────

def screen_verification():
    while True:
        draw_banner()
        console.print(Panel("[bold magenta]Merchant Verification — Module 3[/]", border_style="magenta"))
        t = Table(box=box.ROUNDED, border_style="dim", show_header=False, padding=(0,2))
        t.add_column(width=4)
        t.add_column()
        rows = [
            ("1","Onboard New Merchant"),
            ("2","List All Profiles"),
            ("3","View Profile + Gateway Status"),
            ("4","Run Company Lookup"),
            ("5","Parse Document (AI)"),
            ("6","Register with Gateways"),
            ("7","Submit OTP"),
            ("8","Save API Credentials"),
            ("9","Verification Stats"),
            ("D","View Docs / Extracted Data"),
            ("I","Initiate KYC (Sumsub)"),
            ("B","Back"),
        ]
        for k, l in rows:
            t.add_row(f"[bold magenta][{k}][/]", l)
        console.print(Panel(t, title="Verification Menu", border_style="magenta", width=44))

        choice = Prompt.ask("  Choice").strip().upper()
        if choice == "B":
            break
        elif choice == "1":
            _v_onboard()
        elif choice == "2":
            _v_list_profiles()
        elif choice == "3":
            _v_view_profile()
        elif choice == "4":
            _v_company_lookup()
        elif choice == "5":
            _v_parse_doc()
        elif choice == "6":
            _v_register_gateways()
        elif choice == "7":
            _v_submit_otp()
        elif choice == "8":
            _v_save_creds()
        elif choice == "9":
            _v_stats()
        elif choice == "D":
            screen_verification_docs()
        elif choice == "I":
            screen_kyc_initiate()


def _v_onboard():
    draw_banner()
    console.print(Panel("[bold]Onboard New Merchant[/]", border_style="magenta"))
    company  = Prompt.ask("  Company name")
    country  = Prompt.ask("  Country (ISO-2, e.g. GB/US/AE/IN/SG)")
    email    = Prompt.ask("  Business email")
    reg_num  = Prompt.ask("  Registration number (optional)", default="")
    biz_type = Prompt.ask("  Business type (optional)", default="")
    website  = Prompt.ask("  Website (optional)", default="")

    payload = {
        "company_name":   company,
        "country":        country.upper(),
        "business_email": email,
    }
    if reg_num:  payload["registration_number"] = reg_num
    if biz_type: payload["business_type"] = biz_type
    if website:  payload["website"] = website

    with console.status("Submitting + starting company lookup…"):
        result = api("POST", "/api/verification/onboard", json=payload)

    if result:
        console.print(Panel(
            f"[green]Onboarded![/]\n\n"
            f"[bold]Profile ID:[/] [yellow]{result['merchant_profile_id']}[/]\n"
            f"[bold]Status:[/]     {result['status']}\n\n"
            f"[dim]{result['message']}[/]",
            border_style="green"
        ))
    pause()


def _v_list_profiles():
    draw_banner()
    profiles = api("GET", "/api/verification/profiles") or []
    if not profiles:
        console.print("  [dim]No merchant profiles yet.[/]")
        pause(); return

    t = Table(box=box.SIMPLE_HEAVY, show_lines=True)
    t.add_column("ID",      width=12, style="dim")
    t.add_column("Company")
    t.add_column("Country")
    t.add_column("Status")
    t.add_column("Phase", justify="right")
    t.add_column("Created")

    for p in profiles:
        t.add_row(
            p["id"][:10] + "…",
            p["company_name"],
            p["country"],
            sc(p.get("onboarding_status","")),
            str(p.get("current_phase", 0)),
            ts(p.get("created_at","")),
        )
    console.print(t)
    pause()


def _v_view_profile():
    draw_banner()
    pid = Prompt.ask("  Profile ID")
    with console.status("Fetching…"):
        data = api("GET", f"/api/verification/profile/{pid}")
    if not data:
        pause(); return

    info = Table(box=box.SIMPLE, show_header=False, padding=(0,2))
    info.add_column(style="dim")
    info.add_column()
    for k in ("company_name","country","business_email","registration_number",
              "business_type","website","onboarding_status","current_phase"):
        v = data.get(k)
        if v is not None:
            val = sc(str(v)) if k=="onboarding_status" else str(v)
            info.add_row(k, val)
    console.print(Panel(info, title="Profile", border_style="magenta"))

    # Company data
    cd = data.get("company_data") or {}
    if cd:
        ct = Table(box=box.SIMPLE, show_header=False, padding=(0,2))
        ct.add_column(style="dim")
        ct.add_column()
        for k, v in cd.items():
            if v:
                ct.add_row(k, str(v)[:80])
        console.print(Panel(ct, title="OpenCorporates Data", border_style="cyan"))

    # Gateway registrations
    regs = data.get("gateway_registrations") or []
    if regs:
        gt = Table(box=box.SIMPLE_HEAVY)
        gt.add_column("Gateway")
        gt.add_column("Status")
        gt.add_column("GW Merchant ID")
        gt.add_column("OTP Required")
        gt.add_column("Attempts", justify="right")
        for r in regs:
            gt.add_row(
                r.get("gateway_name",""),
                sc(r.get("registration_status","")),
                r.get("gateway_merchant_id") or "—",
                "[yellow]Yes[/]" if r.get("requires_otp") else "No",
                str(r.get("attempt_count",0)),
            )
        console.print(Panel(gt, title="Gateway Registrations", border_style="blue"))

    pause()


def _v_company_lookup():
    draw_banner()
    pid     = Prompt.ask("  Profile ID")
    company = Prompt.ask("  Company name")
    country = Prompt.ask("  Country (ISO-2)")
    reg_num = Prompt.ask("  Registration number (optional)", default="")

    params = f"profile_id={pid}&company_name={company}&country={country}"
    if reg_num:
        params += f"&registration_number={reg_num}"

    with console.status("Searching OpenCorporates…"):
        result = api("POST", f"/api/verification/company-lookup?{params}")

    if result:
        t = Table(box=box.SIMPLE, show_header=False, padding=(0,2))
        t.add_column(style="dim")
        t.add_column()
        for k, v in result.items():
            if v:
                t.add_row(k, str(v)[:80])
        console.print(Panel(t, title="[green]Company Found[/]", border_style="green"))
    pause()


def _v_parse_doc():
    draw_banner()
    console.print(Panel("[bold]AI Document Parser[/]", border_style="magenta"))
    pid      = Prompt.ask("  Profile ID")
    doc_type = Prompt.ask("  Document type", choices=["MOA","AOA","business_license","registration_certificate","incorporation_document","other"])
    doc_name = Prompt.ask("  Document name", default="document.pdf")
    console.print("  [dim]Paste document text below (type END on a new line to finish):[/]")
    lines = []
    while True:
        line = input()
        if line.strip() == "END":
            break
        lines.append(line)
    doc_text = "\n".join(lines)

    with console.status("Parsing with Claude AI…"):
        result = api("POST", "/api/verification/parse-document", json={
            "merchant_profile_id": pid,
            "document_text":       doc_text,
            "document_type":       doc_type,
            "document_name":       doc_name,
        })

    if result:
        t = Table(box=box.SIMPLE, show_header=False, padding=(0,2))
        t.add_column(style="dim")
        t.add_column()
        d = result.get("extracted_data", {})
        for k, v in d.items():
            if v:
                t.add_row(k, str(v)[:80])
        t.add_row("confidence", f"[bold]{d.get('confidence',0)}%[/]")
        t.add_row("valid", "[green]Yes[/]" if result.get("is_valid") else "[red]No[/]")
        console.print(Panel(t, title="Extracted Data", border_style="magenta"))
    pause()


def _v_register_gateways():
    draw_banner()
    pid = Prompt.ask("  Profile ID")
    console.print("  [dim]Gateways: moonpay, transak, simplex, ramp_network[/]")
    gw_input = Prompt.ask("  Gateways (comma-separated, blank = all)", default="")
    gateways = [g.strip() for g in gw_input.split(",") if g.strip()] or ["moonpay","transak","simplex","ramp_network"]

    with console.status(f"Registering with {', '.join(gateways)}…"):
        result = api("POST", "/api/verification/register-gateways", json={
            "merchant_profile_id": pid,
            "gateways":            gateways,
        })

    if result:
        console.print(Panel(
            f"[green]Registration submitted![/]\n\n"
            f"[bold]Status:[/] {result['status']}\n"
            f"[dim]{result['message']}[/]",
            border_style="green"
        ))
    pause()


def _v_submit_otp():
    draw_banner()
    reg_id = Prompt.ask("  Gateway Registration ID")
    otp    = Prompt.ask("  OTP code")
    with console.status("Submitting OTP…"):
        result = api("POST", "/api/verification/submit-otp", json={"registration_id": reg_id, "otp": otp})
    if result:
        ok = result.get("success")
        console.print(f"\n  {'[green]OTP verified!' if ok else '[red]OTP failed.'}")
    pause()


def _v_save_creds():
    draw_banner()
    pid     = Prompt.ask("  Profile ID")
    gateway = Prompt.ask("  Gateway", choices=["moonpay","transak","simplex","ramp_network","stripe","nowpayments"])
    api_key = Prompt.ask("  API Key", password=True)
    secret  = Prompt.ask("  API Secret (optional)", password=True, default="")
    webhook = Prompt.ask("  Webhook Secret (optional)", password=True, default="")

    payload = {"merchant_profile_id": pid, "gateway_name": gateway, "api_key": api_key}
    if secret:  payload["api_secret"] = secret
    if webhook: payload["webhook_secret"] = webhook

    with console.status("Encrypting and saving…"):
        result = api("POST", "/api/verification/credentials", json=payload)

    if result:
        console.print(Panel(
            f"[green]Credentials saved (AES-256-GCM)[/]\n\n"
            f"[bold]Gateway:[/]     {result['gateway']}\n"
            f"[bold]Masked Key:[/]  [dim]{result['masked_api_key']}[/]",
            border_style="green"
        ))
    pause()


def _v_stats():
    draw_banner()
    stats = api("GET", "/api/verification/stats") or {}
    t = Table(box=box.SIMPLE, show_header=False, padding=(0,3))
    t.add_column(style="dim")
    t.add_column(style="bold")
    labels = {
        "total_merchants":               "Total Merchants",
        "verified":                      "Verified",
        "pending":                       "Pending",
        "failed":                        "Failed",
        "gateway_registrations_total":   "GW Registrations",
        "gateway_registrations_verified":"GW Verified",
    }
    for k, label in labels.items():
        v = stats.get(k, 0)
        color = "green" if "verified" in k or k=="verified" else ("red" if "failed" in k else "white")
        t.add_row(label, f"[{color}]{v}[/]")
    console.print(Panel(t, title="Verification Stats", border_style="magenta"))
    pause()


# ─── Notification screens ─────────────────────────────────────────────────────

def screen_telegram():
    draw_banner()
    data = api("GET", "/api/telegram/status") or {}
    t = Table(box=box.SIMPLE, show_header=False, padding=(0,2))
    t.add_column(style="dim"); t.add_column()
    for k, v in data.items():
        t.add_row(k, str(v))
    console.print(Panel(t, title="Telegram Status", border_style="blue"))

    if Confirm.ask("  Send test message?", default=False):
        with console.status("Sending…"):
            r = api("POST", "/api/telegram/test")
        if r and r.get("sent"):
            console.print("  [green]Test message sent![/]")
        else:
            console.print("  [red]Failed — check TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID[/]")
    pause()


def screen_whatsapp():
    draw_banner()
    data = api("GET", "/api/whatsapp/status") or {}
    t = Table(box=box.SIMPLE, show_header=False, padding=(0,2))
    t.add_column(style="dim"); t.add_column()
    for k, v in data.items():
        t.add_row(k, str(v))
    console.print(Panel(t, title="WhatsApp Status", border_style="blue"))

    if Confirm.ask("  Send test message?", default=False):
        with console.status("Sending…"):
            r = api("POST", "/api/whatsapp/test")
        if r and r.get("sent"):
            console.print("  [green]Test message sent![/]")
        else:
            console.print("  [red]Failed — check WHATSAPP_TOKEN + WHATSAPP_PHONE_ID + WHATSAPP_TO[/]")
    pause()


def screen_nowpayments():
    draw_banner()
    data = api("GET", "/api/nowpayments/status") or {}
    t = Table(box=box.SIMPLE, show_header=False, padding=(0,2))
    t.add_column(style="dim"); t.add_column()
    for k, v in data.items():
        t.add_row(k, str(v))
    console.print(Panel(t, title="NOWPayments Status", border_style="blue"))

    if Confirm.ask("  Fetch supported currencies (top 20)?", default=False):
        with console.status("Fetching…"):
            coins = api("GET", "/api/nowpayments/currencies")
        if coins:
            console.print(f"  [green]{coins['count']} currencies.[/] First 20: {', '.join(coins['currencies'][:20])}")
    pause()


def screen_kyc():
    draw_banner()
    data = api("GET", "/api/kyc/config") or {}
    t = Table(box=box.SIMPLE, show_header=False, padding=(0,2))
    t.add_column(style="dim"); t.add_column()
    for k, v in data.items():
        t.add_row(k, str(v))
    console.print(Panel(t, title="KYC / Sumsub Config", border_style="blue"))

    if Confirm.ask("  List recent KYC records?", default=False):
        records = api("GET", "/api/kyc/records") or []
        if records:
            rt = Table(box=box.SIMPLE)
            rt.add_column("Email"); rt.add_column("Status"); rt.add_column("Created")
            for r in records[:20]:
                rt.add_row(r.get("customer_email",""), sc(r.get("kyc_status","")), ts(r.get("created_at","")))
            console.print(rt)
    pause()


def screen_stripe():
    draw_banner()
    data = api("GET", "/api/stripe/status") or {}
    t = Table(box=box.SIMPLE, show_header=False, padding=(0,2))
    t.add_column(style="dim"); t.add_column()
    for k, v in data.items():
        t.add_row(k, str(v))
    console.print(Panel(t, title="Stripe Status", border_style="blue"))

    if data.get("enabled") and Confirm.ask("  Test Stripe connection?", default=False):
        with console.status("Testing…"):
            r = api("POST", "/api/stripe/test")
        if r and r.get("connected"):
            console.print(f"  [green]Connected![/] Balance: {r.get('balance')} ({r.get('mode')} mode)")
        else:
            console.print("  [red]Failed — check STRIPE_SECRET_KEY[/]")
    pause()


def screen_credentials():
    draw_banner()
    console.print(Panel("[bold]Stored Gateway Credentials[/]", border_style="blue"))
    pid = Prompt.ask("  Merchant Profile ID")
    creds = api("GET", f"/api/verification/credentials/{pid}") or []
    if not creds:
        console.print("  [dim]No credentials stored for this profile.[/]")
        pause(); return

    t = Table(box=box.SIMPLE_HEAVY, show_lines=True)
    t.add_column("Gateway")
    t.add_column("API Key (masked)")
    t.add_column("Has Secret")
    t.add_column("Has Webhook")
    t.add_column("Active")
    for c in creds:
        t.add_row(
            c.get("gateway",""),
            c.get("api_key") or "—",
            "[green]Yes[/]" if c.get("has_secret") else "No",
            "[green]Yes[/]" if c.get("has_webhook") else "No",
            "[green]●[/]" if c.get("is_active") else "[red]●[/]",
        )
    console.print(t)
    pause()


def screen_lockbox_history():
    draw_banner()
    console.print(Panel("[bold]Lockbox Transaction History[/]", border_style="blue"))
    data = api("GET", "/api/lockbox/transactions?limit=30&offset=0") or {}
    txs  = data.get("transactions", []) if isinstance(data, dict) else []
    total = data.get("total", len(txs)) if isinstance(data, dict) else len(txs)

    console.print(f"  [dim]Total: {total}[/]\n")
    if not txs:
        console.print("  [dim]No transactions yet.[/]")
        pause(); return

    t = Table(box=box.SIMPLE_HEAVY, show_lines=True)
    t.add_column("#",      width=5, justify="right")
    t.add_column("Card",   width=22)
    t.add_column("Name",   width=20)
    t.add_column("Status")
    t.add_column("Source", width=14)
    t.add_column("Created")
    for tx in txs:
        t.add_row(
            str(tx.get("id","")),
            tx.get("masked_card_number",""),
            tx.get("cardholder_name","")[:18],
            sc(tx.get("validation_status","")),
            tx.get("source",""),
            ts(tx.get("created_at","")),
        )
    console.print(t)
    pause()


def screen_kyc_initiate():
    draw_banner()
    console.print(Panel("[bold]Initiate KYC (Sumsub)[/]", border_style="blue"))
    email      = Prompt.ask("  Customer email")
    payment_id = Prompt.ask("  Payment ID (optional)", default="")

    payload = {"customer_email": email}
    if payment_id:
        payload["payment_id"] = payment_id

    with console.status("Creating Sumsub applicant…"):
        result = api("POST", "/api/kyc/initiate", json=payload)

    if result:
        if result.get("already_verified"):
            console.print("  [green]Already KYC verified![/]")
        else:
            console.print(Panel(
                f"[green]KYC initiated![/]\n\n"
                f"[bold]Applicant ID:[/] {result.get('applicant_id')}\n"
                f"[bold]SDK Token:[/]    [dim]{str(result.get('sdk_token',''))[:40]}…[/]\n"
                f"[bold]WebSDK URL:[/]   {result.get('websdk_url')}",
                border_style="green"
            ))
    pause()


def screen_verification_docs():
    draw_banner()
    pid = Prompt.ask("  Merchant Profile ID")
    with console.status("Fetching…"):
        data = api("GET", f"/api/verification/profile/{pid}")
    if not data:
        pause(); return

    # Pull extracted_company_data from DB via admin stats
    console.print(Panel(f"[bold]Documents for profile {pid[:12]}…[/]", border_style="magenta"))
    profile = data
    cd = {}
    try:
        import json as _j
        cd = _j.loads(profile.get("company_data") or "{}")
    except Exception:
        pass

    if cd:
        t = Table(box=box.SIMPLE, show_header=False, padding=(0,2))
        t.add_column(style="dim"); t.add_column()
        for k, v in cd.items():
            if v:
                t.add_row(k, str(v)[:80])
        console.print(Panel(t, title="OpenCorporates Data", border_style="cyan"))
    else:
        console.print("  [dim]No company data retrieved yet.[/]")

    regs = data.get("gateway_registrations") or []
    if regs:
        gt = Table(box=box.SIMPLE_HEAVY, title="Gateway Registrations")
        gt.add_column("Gateway"); gt.add_column("Status"); gt.add_column("GW Merchant ID"); gt.add_column("Error")
        for r in regs:
            gt.add_row(
                r.get("gateway_name",""),
                sc(r.get("registration_status","")),
                r.get("gateway_merchant_id") or "—",
                (r.get("error_message") or "")[:40],
            )
        console.print(gt)
    pause()


def screen_lockbox():
    draw_banner()
    data = api("GET", "/api/lockbox/status") or {}
    stats = data.get("stats", {})
    t = Table(box=box.SIMPLE, show_header=False, padding=(0,2))
    t.add_column(style="dim"); t.add_column()
    t.add_row("Claude AI online", "[green]Yes[/]" if data.get("claude_online") else "[red]No[/]")
    t.add_row("Total parsed",   str(stats.get("total",0)))
    t.add_row("Valid",          f"[green]{stats.get('valid',0)}[/]")
    t.add_row("Invalid",        f"[red]{stats.get('invalid',0)}[/]")
    console.print(Panel(t, title="Lockbox AI Parser", border_style="blue"))

    if Confirm.ask("  Parse card data now?", default=False):
        text = Prompt.ask("  Paste raw card data")
        with console.status("Parsing with Claude…"):
            result = api("POST", "/api/lockbox/parse", json={"rawInput": text, "source": "tui"})
        if result and result.get("success"):
            p = result["parsed"]
            console.print(Panel(
                f"[bold]Card:[/]   {p.get('cardNumber')}\n"
                f"[bold]Expiry:[/] {p.get('expiryDate')}\n"
                f"[bold]Name:[/]   {p.get('cardholderName')}\n"
                f"[bold]Valid:[/]  {'[green]Yes' if result['validation']['overall']['isValid'] else '[red]No'}[/]",
                border_style="blue"
            ))
    pause()


# ─── Main Loop ────────────────────────────────────────────────────────────────
DISPATCH = {
    "1": screen_dashboard,
    "2": screen_links,
    "3": screen_create_link,
    "4": screen_payments,
    "5": screen_check_payment,
    "6": screen_filter_payments,
    "7": screen_add_merchant,
    "8": screen_export_csv,
    "9": screen_health,
    "V": screen_verification,
    "T": screen_telegram,
    "W": screen_whatsapp,
    "N": screen_nowpayments,
    "K": screen_kyc,
    "L": screen_lockbox,
    "H": screen_lockbox_history,
    "S": screen_stripe,
    "C": screen_credentials,
}

def main():
    while True:
        draw_banner()
        draw_menu()
        try:
            choice = Prompt.ask("\n  Choice").strip().upper()
        except (KeyboardInterrupt, EOFError):
            choice = "Q"

        if choice == "Q":
            console.print("\n  [dim]Goodbye.[/]\n")
            sys.exit(0)

        fn = DISPATCH.get(choice)
        if fn:
            fn()
        else:
            console.print(f"  [red]Unknown option:[/] {choice}")
            time.sleep(0.6)


if __name__ == "__main__":
    main()

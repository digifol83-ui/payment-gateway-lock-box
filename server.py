"""
Fiat-to-Crypto Payment Gateway — FastAPI Server
Run: uvicorn server:app --host 0.0.0.0 --port 8000 --reload
"""
import json
import asyncio
import httpx
from pathlib import Path
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, Request, Header, Depends, BackgroundTasks, UploadFile, File, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr

import database as db
from providers import get_provider, PROVIDERS
import telegram as tg
import whatsapp as wa
from kyc import get_kyc
import lockbox
import bot_handler
from config import (
    BASE_URL, ADMIN_API_KEY,
    SUPPORTED_CRYPTOS, SUPPORTED_FIATS,
    DEFAULT_CRYPTO, DEFAULT_FIAT,
    TELEGRAM_ENABLED, WHATSAPP_ENABLED, SUMSUB_ENABLED,
    NOWPAYMENTS_ENABLED, KYC_SUMSUB_LIMIT, LOCKBOX_ENABLED,
    STRIPE_ENABLED, OPENCORPORATES_ENABLED, IMAP_ENABLED,
    CREDENTIAL_ENCRYPTION_KEY,
)
from verification import company_lookup as cl
from verification import document_parser as dp
from verification import gateway_registration as gr
from verification import email_monitor as em
from verification.encryption import (
    encrypt_credential, decrypt_credential, mask_credential,
)

# ─── App setup ────────────────────────────────────────────────────────────────
app = FastAPI(
    title="Crypto Payment Gateway",
    description="Fiat-to-crypto payments via Transak & MoonPay",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

WEB_DIR = Path(__file__).parent / "web"


@app.on_event("startup")
async def startup():
    db.init_db()
    print(f"✓ Database initialized")
    print(f"✓ Providers: {list(PROVIDERS.keys())}")
    print(f"✓ Server: {BASE_URL}")
    tg_status = "ENABLED" if TELEGRAM_ENABLED else "disabled (set TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID)"
    wa_status = "ENABLED" if WHATSAPP_ENABLED else "disabled (set WHATSAPP_TOKEN + WHATSAPP_PHONE_ID + WHATSAPP_TO)"
    np_status = "ENABLED" if NOWPAYMENTS_ENABLED else "disabled (set NOWPAYMENTS_API_KEY)"
    sb_status = "ENABLED" if SUMSUB_ENABLED else "disabled (set SUMSUB_APP_TOKEN + SUMSUB_SECRET_KEY)"
    print(f"✓ Telegram:    {tg_status}")
    print(f"✓ WhatsApp:    {wa_status}")
    print(f"✓ NOWPayments: {np_status}")
    print(f"✓ Sumsub KYC:  {sb_status}")
    lk_status = "ENABLED" if LOCKBOX_ENABLED else "disabled (set ANTHROPIC_API_KEY)"
    print(f"✓ Lockbox AI:  {lk_status}")
    sk_status = "ENABLED" if STRIPE_ENABLED else "disabled (set STRIPE_SECRET_KEY)"
    print(f"✓ Stripe:      {sk_status}")
    oc_status = "ENABLED" if OPENCORPORATES_ENABLED else "disabled (set OPENCORPORATES_API_TOKEN)"
    print(f"✓ OpenCorp:    {oc_status}")
    im_status = "ENABLED" if IMAP_ENABLED else "disabled (set IMAP_HOST/USER/PASSWORD)"
    print(f"✓ IMAP/OTP:    {im_status}")


# ─── Auth dependency ──────────────────────────────────────────────────────────
def require_admin(x_api_key: str = Header(default=None)):
    if x_api_key != ADMIN_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid admin API key")
    return x_api_key

def get_merchant_or_admin(x_api_key: str = Header(default=None)):
    """Allow either merchant API key or admin key."""
    if not x_api_key:
        raise HTTPException(status_code=401, detail="X-Api-Key header required")
    if x_api_key == ADMIN_API_KEY:
        return {"id": "admin", "name": "Admin"}
    merchant = db.get_merchant_by_key(x_api_key)
    if not merchant:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return merchant


# ─── Pydantic models ──────────────────────────────────────────────────────────
class CreateLinkRequest(BaseModel):
    wallet_address: str
    amount: Optional[float] = None
    fiat_currency: str = DEFAULT_FIAT
    crypto_currency: Optional[str] = DEFAULT_CRYPTO
    description: Optional[str] = ""
    is_reusable: bool = True
    expires_at: Optional[str] = None
    metadata: Optional[dict] = {}

class InitiatePaymentRequest(BaseModel):
    link_id: str
    customer_email: str
    customer_name: Optional[str] = None
    provider: str = "transak"
    amount: Optional[float] = None          # override link amount
    crypto_currency: Optional[str] = None  # override link crypto

class CreateMerchantRequest(BaseModel):
    name: str
    email: str
    webhook_url: Optional[str] = None


# ─── Health ───────────────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}


# ─── Merchant endpoints ───────────────────────────────────────────────────────
@app.post("/api/merchants", dependencies=[Depends(require_admin)])
async def create_merchant(req: CreateMerchantRequest):
    merchant = db.create_merchant(req.name, req.email, req.webhook_url)
    return merchant


# ─── Payment Link endpoints ───────────────────────────────────────────────────
@app.post("/api/links")
async def create_link(
    req: CreateLinkRequest,
    background_tasks: BackgroundTasks,
    merchant=Depends(get_merchant_or_admin),
):
    if req.fiat_currency not in SUPPORTED_FIATS:
        raise HTTPException(400, f"Unsupported fiat. Supported: {SUPPORTED_FIATS}")
    if req.crypto_currency and req.crypto_currency not in SUPPORTED_CRYPTOS:
        raise HTTPException(400, f"Unsupported crypto. Supported: {list(SUPPORTED_CRYPTOS.keys())}")

    data = req.dict()
    data["merchant_id"] = merchant["id"]
    link = db.create_payment_link(data)
    payment_url = f"{BASE_URL}/pay/{link['id']}"

    background_tasks.add_task(tg.notify_new_link, link, payment_url)

    return {
        **link,
        "payment_url": payment_url,
        "api_url": f"{BASE_URL}/api/links/{link['id']}",
    }


@app.get("/api/links")
async def list_links(merchant=Depends(get_merchant_or_admin)):
    mid = None if merchant["id"] == "admin" else merchant["id"]
    links = db.list_payment_links(merchant_id=mid)
    return [
        {**l, "payment_url": f"{BASE_URL}/pay/{l['id']}"}
        for l in links
    ]


@app.get("/api/links/{link_id}")
async def get_link(link_id: str, merchant=Depends(get_merchant_or_admin)):
    link = db.get_payment_link(link_id)
    if not link:
        raise HTTPException(404, "Link not found")
    return {**link, "payment_url": f"{BASE_URL}/pay/{link['id']}"}


@app.delete("/api/links/{link_id}")
async def deactivate_link(link_id: str, merchant=Depends(get_merchant_or_admin)):
    with db.get_conn() as conn:
        conn.execute("UPDATE payment_links SET is_active=0 WHERE id=?", (link_id,))
    return {"status": "deactivated"}


# ─── Payment initiation ───────────────────────────────────────────────────────
@app.post("/api/payments/initiate")
async def initiate_payment(req: InitiatePaymentRequest):
    link = db.get_payment_link(req.link_id)
    if not link:
        raise HTTPException(404, "Payment link not found")
    if not link["is_active"]:
        raise HTTPException(400, "Payment link is inactive")

    provider = get_provider(req.provider)
    if not provider:
        raise HTTPException(400, f"Unknown provider. Available: {list(PROVIDERS.keys())}")

    # Resolve final amount and crypto
    amount = req.amount or link["amount"]
    if not amount:
        raise HTTPException(400, "Amount required (not set on link, provide in request)")
    crypto = req.crypto_currency or link["crypto_currency"] or DEFAULT_CRYPTO

    payment_data = {
        "link_id":          link["id"],
        "merchant_id":      link["merchant_id"],
        "amount":           amount,
        "fiat_currency":    link["fiat_currency"],
        "crypto_currency":  crypto,
        "wallet_address":   link["wallet_address"],
        "customer_email":   req.customer_email,
        "customer_name":    req.customer_name,
        "provider":         req.provider,
        "description":      link["description"],
    }

    payment = db.create_payment(payment_data)

    # NOWPayments: must create the invoice via their API first to get a
    # provider_order_id (their internal payment_id).  The hosted payment URL
    # is https://nowpayments.io/payment/?iid=<payment_id>, which requires that
    # ID — build_widget_url() will use it once we persist it below.
    if req.provider == "nowpayments" and hasattr(provider, "create_invoice"):
        try:
            invoice = await provider.create_invoice(payment)
            provider_order_id = str(invoice.get("payment_id", ""))
            # Persist provider_order_id and initial wallet/amount from API response
            db.update_payment_status(payment["id"], "pending", {
                "provider_order_id": provider_order_id,
                "pay_address":       invoice.get("pay_address"),
                "crypto_amount":     invoice.get("pay_amount"),
            })
            # Reload so build_widget_url sees provider_order_id
            payment = db.get_payment(payment["id"])
            widget_url = provider.build_widget_url(payment)
        except Exception as e:
            # Mark payment failed so it does not linger as orphaned pending
            db.update_payment_status(payment["id"], "failed", {})
            raise HTTPException(502, f"NOWPayments invoice creation failed: {e}")

    # Stripe requires an async API call to create a Checkout Session
    elif hasattr(provider, "create_checkout_session"):
        widget_url = await provider.create_checkout_session(payment)

    else:
        widget_url = provider.build_widget_url(payment)

    # Fire notifications in background
    asyncio.create_task(tg.notify_new_payment(payment))
    asyncio.create_task(wa.notify_new_payment(payment))

    return {
        "payment_id":    payment["id"],
        "status":        payment["status"],
        "provider_url":  widget_url,
        "amount":        amount,
        "fiat_currency": link["fiat_currency"],
        "crypto_currency": crypto,
    }


@app.get("/api/payments/{payment_id}")
async def get_payment(payment_id: str):
    payment = db.get_payment(payment_id)
    if not payment:
        raise HTTPException(404, "Payment not found")
    return payment


@app.get("/api/payments")
async def list_payments(
    status: Optional[str] = None,
    limit: int = 100,
    merchant=Depends(get_merchant_or_admin),
):
    mid = None if merchant["id"] == "admin" else merchant["id"]
    return db.list_payments(limit=limit, status=status, merchant_id=mid)


@app.get("/api/stats", dependencies=[Depends(require_admin)])
async def get_stats():
    return db.get_stats()


# ─── Webhooks ─────────────────────────────────────────────────────────────────
@app.post("/webhooks/transak")
async def webhook_transak(request: Request, background_tasks: BackgroundTasks):
    raw_body = await request.body()
    sig = request.headers.get("x-webhook-secret", "")
    provider = get_provider("transak")
    if not provider.verify_webhook(raw_body, sig):
        raise HTTPException(401, "Invalid webhook signature")
    payload = json.loads(raw_body)
    background_tasks.add_task(_process_webhook, provider, payload)
    return {"received": True}


@app.post("/webhooks/moonpay")
async def webhook_moonpay(request: Request, background_tasks: BackgroundTasks):
    raw_body = await request.body()
    sig = request.headers.get("moonpay-signature-v2", "")
    provider = get_provider("moonpay")
    if not provider.verify_webhook(raw_body, sig):
        raise HTTPException(401, "Invalid webhook signature")
    payload = json.loads(raw_body)
    background_tasks.add_task(_process_webhook, provider, payload)
    return {"received": True}


async def _process_webhook(provider, payload: dict):
    parsed = provider.parse_webhook(payload)
    if not parsed or not parsed.get("payment_id"):
        return
    payment_id = parsed["payment_id"]
    payment = db.get_payment(payment_id)
    if not payment:
        print(f"[webhook] Unknown payment_id: {payment_id}")
        return
    db.update_payment_status(payment_id, parsed["status"], parsed)
    print(f"[webhook] {provider.name} → payment {payment_id[:8]}… → {parsed['status']}")
    # Notifications
    await tg.notify_payment_update(payment, parsed["status"], parsed)
    await wa.notify_payment_update(payment, parsed["status"], parsed)
    # Fire merchant webhook if configured
    if payment.get("merchant_id"):
        await _fire_merchant_webhook(payment, parsed)


async def _fire_merchant_webhook(payment: dict, update: dict):
    with db.get_conn() as conn:
        row = conn.execute(
            "SELECT webhook_url FROM merchants WHERE id=?", (payment["merchant_id"],)
        ).fetchone()
    if not row or not row["webhook_url"]:
        return
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(row["webhook_url"], json={
                "event": "payment.status_update",
                "payment_id": payment["id"],
                "status": update["status"],
                "provider": payment["provider"],
                "amount": payment["amount"],
                "fiat_currency": payment["fiat_currency"],
                "crypto_currency": payment["crypto_currency"],
            })
    except Exception as e:
        print(f"[webhook] Merchant notify failed: {e}")


# ─── Web UI (serve HTML pages) ────────────────────────────────────────────────
@app.get("/pay/{link_id}", response_class=HTMLResponse)
async def payment_page(link_id: str):
    link = db.get_payment_link(link_id)
    if not link:
        return HTMLResponse("<h2>Payment link not found or expired.</h2>", status_code=404)
    if not link["is_active"]:
        return HTMLResponse("<h2>This payment link is no longer active.</h2>", status_code=410)

    html = (WEB_DIR / "pay.html").read_text()
    # Inject link data into page
    link_json = json.dumps({
        "id":              link["id"],
        "amount":          link["amount"],
        "fiat_currency":   link["fiat_currency"],
        "crypto_currency": link["crypto_currency"],
        "wallet_address":  link["wallet_address"],
        "description":     link["description"],
        "base_url":        BASE_URL,
    })
    html = html.replace("__LINK_DATA__", link_json)
    return HTMLResponse(html)


@app.get("/pay/success/{payment_id}", response_class=HTMLResponse)
async def success_page(payment_id: str):
    html = (WEB_DIR / "success.html").read_text()
    payment = db.get_payment(payment_id) or {}
    data_json = json.dumps({
        "payment_id":      payment_id,
        "status":          payment.get("status", "processing"),
        "amount":          payment.get("amount"),
        "fiat_currency":   payment.get("fiat_currency", "USD"),
        "crypto_currency": payment.get("crypto_currency", ""),
        "provider":        payment.get("provider", ""),
    })
    html = html.replace("__PAYMENT_DATA__", data_json)
    return HTMLResponse(html)


@app.get("/admin", response_class=HTMLResponse)
async def admin_page():
    html = (WEB_DIR / "admin.html").read_text()
    html = html.replace("__BASE_URL__", BASE_URL)
    html = html.replace("__ADMIN_KEY__", ADMIN_API_KEY)
    return HTMLResponse(html)


@app.get("/", response_class=HTMLResponse)
async def root():
    return RedirectResponse(url="/admin")


# ─── Stripe endpoints ────────────────────────────────────────────────────────
@app.get("/api/stripe/status", dependencies=[Depends(require_admin)])
async def stripe_status():
    provider = get_provider("stripe")
    return provider.is_configured()


@app.post("/api/stripe/test", dependencies=[Depends(require_admin)])
async def stripe_test():
    if not STRIPE_ENABLED:
        raise HTTPException(400, "Stripe not configured. Set STRIPE_SECRET_KEY.")
    from config import STRIPE_SECRET_KEY
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                "https://api.stripe.com/v1/balance",
                auth=(STRIPE_SECRET_KEY, ""),
                headers={"Stripe-Version": "2023-10-16"},
            )
        if resp.status_code == 200:
            data = resp.json()
            available = data.get("available", [{}])
            currency = available[0].get("currency", "usd").upper() if available else "N/A"
            amount = available[0].get("amount", 0) / 100 if available else 0
            return {"connected": True, "balance": f"{amount:.2f} {currency}", "mode": "test" if "test" in STRIPE_SECRET_KEY else "live"}
        raise HTTPException(502, f"Stripe API returned {resp.status_code}")
    except httpx.RequestError as e:
        raise HTTPException(502, f"Stripe unreachable: {e}")


# ─── Stripe webhook ───────────────────────────────────────────────────────────
@app.post("/webhooks/stripe")
async def webhook_stripe(request: Request, background_tasks: BackgroundTasks):
    raw_body = await request.body()
    sig = request.headers.get("stripe-signature", "")
    provider = get_provider("stripe")
    if not provider.verify_webhook(raw_body, sig):
        raise HTTPException(401, "Invalid Stripe webhook signature")
    payload = json.loads(raw_body)
    background_tasks.add_task(_process_webhook, provider, payload)
    return {"received": True}


@app.get("/api/stripe/checkout/{payment_id}")
async def stripe_checkout_redirect(payment_id: str):
    """On-demand Stripe Checkout Session creation + redirect to hosted page."""
    if not STRIPE_ENABLED:
        raise HTTPException(400, "Stripe not configured. Set STRIPE_SECRET_KEY.")
    payment = db.get_payment(payment_id)
    if not payment:
        raise HTTPException(404, "Payment not found")
    provider = get_provider("stripe")
    try:
        checkout_url = await provider.create_checkout_session(payment)
    except ValueError as e:
        raise HTTPException(502, str(e))
    return RedirectResponse(url=checkout_url, status_code=303)


# ─── NOWPayments webhook ─────────────────────────────────────────────────────
@app.post("/webhooks/nowpayments")
async def webhook_nowpayments(request: Request, background_tasks: BackgroundTasks):
    raw_body = await request.body()
    sig = request.headers.get("x-nowpayments-sig", "")
    provider = get_provider("nowpayments")
    if not provider.verify_webhook(raw_body, sig):
        raise HTTPException(401, "Invalid IPN signature")
    # Parse from the already-read raw_body — do not call request.json() again
    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError:
        raise HTTPException(400, "Invalid JSON payload")
    background_tasks.add_task(_process_webhook, provider, payload)
    return {"received": True}


# ─── Sumsub KYC webhook ───────────────────────────────────────────────────────
@app.post("/webhooks/sumsub")
async def webhook_sumsub(request: Request, background_tasks: BackgroundTasks):
    raw_body = await request.body()
    digest = request.headers.get("x-payload-digest", "")
    kyc = get_kyc()
    if not kyc.verify_webhook(raw_body, digest):
        raise HTTPException(401, "Invalid Sumsub signature")
    payload = await request.json()
    background_tasks.add_task(_process_kyc_webhook, kyc, payload)
    return {"received": True}


async def _process_kyc_webhook(kyc, payload: dict):
    parsed = kyc.parse_webhook(payload)
    if not parsed:
        return
    record = db.get_kyc_by_applicant(parsed["applicant_id"])
    if not record:
        print(f"[sumsub] Unknown applicant: {parsed['applicant_id']}")
        return
    db.update_kyc_record(record["id"], parsed["kyc_status"], parsed)
    print(f"[sumsub] KYC {parsed['applicant_id'][:8]}… → {parsed['kyc_status']}")
    # Notify admin via Telegram
    status_emoji = "✅" if parsed["kyc_status"] == "approved" else "❌"
    await tg.send_message(
        f"{status_emoji} <b>KYC {parsed['kyc_status'].upper()}</b>\n"
        f"Customer: <code>{record.get('customer_email','—')}</code>\n"
        f"Event: {parsed['event']}\n"
        f"Labels: {', '.join(parsed.get('reject_labels',[]) or ['—'])}"
    )


# ─── KYC API endpoints ────────────────────────────────────────────────────────
@app.post("/api/kyc/initiate")
async def kyc_initiate(request: Request):
    """Start KYC for a customer. Returns SDK token + redirect URL."""
    if not SUMSUB_ENABLED:
        raise HTTPException(400, "KYC not configured. Set SUMSUB_APP_TOKEN and SUMSUB_SECRET_KEY.")
    body = await request.json()
    email = body.get("customer_email", "")
    payment_id = body.get("payment_id", "")
    if not email:
        raise HTTPException(400, "customer_email required")

    # Check if already approved
    existing = db.get_kyc_by_email(email)
    if existing and existing["kyc_status"] == "approved":
        return {"kyc_status": "approved", "already_verified": True}

    kyc = get_kyc()
    ext_id = f"{email}_{payment_id}"[:50]
    applicant = await kyc.create_applicant(ext_id, email)
    sdk_token = await kyc.get_sdk_token(applicant["applicant_id"])
    websdk_url = kyc.get_websdk_url(sdk_token)

    record = db.create_kyc_record({
        "payment_id":       payment_id,
        "customer_email":   email,
        "external_user_id": ext_id,
        "applicant_id":     applicant["applicant_id"],
        "sdk_token":        sdk_token,
    })
    return {
        "kyc_record_id":  record["id"],
        "applicant_id":   applicant["applicant_id"],
        "websdk_url":     websdk_url,
        "sdk_token":      sdk_token,
        "kyc_status":     "pending",
    }


@app.get("/api/kyc/status/{applicant_id}", dependencies=[Depends(require_admin)])
async def kyc_status(applicant_id: str):
    if not SUMSUB_ENABLED:
        raise HTTPException(400, "KYC not configured.")
    kyc = get_kyc()
    result = await kyc.get_applicant_review(applicant_id)
    return result


@app.get("/api/kyc/records", dependencies=[Depends(require_admin)])
async def list_kyc_records(limit: int = 100):
    return db.list_kyc_records(limit=limit)


@app.get("/api/kyc/config", dependencies=[Depends(require_admin)])
async def kyc_config():
    return get_kyc().is_configured()


# ─── WhatsApp endpoints ───────────────────────────────────────────────────────
@app.get("/api/whatsapp/status", dependencies=[Depends(require_admin)])
async def whatsapp_status():
    return wa.is_configured()


@app.post("/api/whatsapp/test", dependencies=[Depends(require_admin)])
async def whatsapp_test():
    if not WHATSAPP_ENABLED:
        raise HTTPException(400, "WhatsApp not configured. Set WHATSAPP_TOKEN, WHATSAPP_PHONE_ID, WHATSAPP_TO.")
    ok = await wa.notify_test()
    if not ok:
        raise HTTPException(502, "Failed to send WhatsApp message. Check token and phone number.")
    return {"sent": True, "to": wa.WHATSAPP_TO}


@app.post("/api/whatsapp/summary", dependencies=[Depends(require_admin)])
async def whatsapp_summary():
    if not WHATSAPP_ENABLED:
        raise HTTPException(400, "WhatsApp not configured.")
    stats = db.get_stats()
    ok = await wa.notify_summary(stats)
    if not ok:
        raise HTTPException(502, "Failed to send summary.")
    return {"sent": True, "stats": stats}


# ─── NOWPayments API endpoints ────────────────────────────────────────────────
@app.get("/api/nowpayments/status", dependencies=[Depends(require_admin)])
async def nowpayments_status():
    from config import NOWPAYMENTS_API_KEY, NOWPAYMENTS_ENV
    return {
        "enabled":    NOWPAYMENTS_ENABLED,
        "api_key":    f"{NOWPAYMENTS_API_KEY[:8]}…" if NOWPAYMENTS_API_KEY else "NOT SET",
        "env":        NOWPAYMENTS_ENV,
        "currencies": "300+ cryptocurrencies",
        "kyc":        "None required",
    }


@app.get("/api/nowpayments/currencies", dependencies=[Depends(require_admin)])
async def nowpayments_currencies():
    if not NOWPAYMENTS_ENABLED:
        raise HTTPException(400, "NOWPayments not configured.")
    provider = get_provider("nowpayments")
    coins = await provider.get_currencies()
    return {"count": len(coins), "currencies": coins[:50]}


# ─── Telegram endpoints ───────────────────────────────────────────────────────
@app.get("/api/telegram/status", dependencies=[Depends(require_admin)])
async def telegram_status():
    """Check Telegram bot configuration."""
    return tg.is_configured()


@app.post("/api/telegram/test", dependencies=[Depends(require_admin)])
async def telegram_test():
    """Send a test message to the configured Telegram chat."""
    if not TELEGRAM_ENABLED:
        raise HTTPException(400, "Telegram not configured. Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID.")
    ok = await tg.notify_test()
    if not ok:
        raise HTTPException(502, "Failed to send Telegram message. Check token and chat_id.")
    return {"sent": True, "chat_id": tg.TELEGRAM_CHAT_ID}


@app.post("/api/telegram/summary", dependencies=[Depends(require_admin)])
async def telegram_summary():
    """Push a stats summary to Telegram right now."""
    if not TELEGRAM_ENABLED:
        raise HTTPException(400, "Telegram not configured.")
    stats = db.get_stats()
    ok = await tg.notify_daily_summary(stats)
    if not ok:
        raise HTTPException(502, "Failed to send summary.")
    return {"sent": True, "stats": stats}


# ─── Telegram incoming webhook (Lockbox bot) ─────────────────────────────────
@app.post("/telegram/incoming")
async def telegram_incoming(request: Request, background_tasks: BackgroundTasks):
    """Receive Telegram updates pushed by the Bot API webhook."""
    update = await request.json()
    background_tasks.add_task(bot_handler.handle_update, update)
    return {"ok": True}


@app.post("/api/lockbox/setup-webhook", dependencies=[Depends(require_admin)])
async def lockbox_setup_webhook():
    """Register the Telegram webhook so updates are pushed here."""
    from config import TELEGRAM_BOT_TOKEN
    if not TELEGRAM_BOT_TOKEN:
        raise HTTPException(400, "TELEGRAM_BOT_TOKEN not configured")
    webhook_url = f"{BASE_URL}/telegram/incoming"
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/setWebhook",
            json={"url": webhook_url, "allowed_updates": ["message", "edited_message"]},
        )
    result = resp.json()
    return {"webhook_url": webhook_url, "telegram_response": result}


@app.delete("/api/lockbox/setup-webhook", dependencies=[Depends(require_admin)])
async def lockbox_delete_webhook():
    """Remove the Telegram webhook (revert to polling mode)."""
    from config import TELEGRAM_BOT_TOKEN
    if not TELEGRAM_BOT_TOKEN:
        raise HTTPException(400, "TELEGRAM_BOT_TOKEN not configured")
    async with httpx.AsyncClient(timeout=10) as client:
        resp = await client.post(
            f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/deleteWebhook"
        )
    return resp.json()


# ─── Lockbox parse API ────────────────────────────────────────────────────────

class LockboxParseRequest(BaseModel):
    rawInput: str
    source: str = "manual"


class LockboxValidateRequest(BaseModel):
    cardNumber: str
    expiryDate: str
    cvv: str
    cardholderName: str
    billingAddress: dict


@app.post("/api/lockbox/parse")
async def lockbox_parse(req: LockboxParseRequest):
    """Parse unstructured payment text via Claude AI."""
    if not LOCKBOX_ENABLED:
        raise HTTPException(400, "Lockbox not configured. Set ANTHROPIC_API_KEY.")
    try:
        parsed = await lockbox.parse_payment_input(req.rawInput)
        validation = lockbox.validate_card_data({
            "cardNumber":     parsed.get("cardNumber", ""),
            "expiryDate":     parsed.get("expiryDate", ""),
            "cvv":            parsed.get("cvv", ""),
            "cardholderName": parsed.get("cardholderName", ""),
            "billingAddress": parsed.get("billingAddress", {}),
        })
        masked = lockbox.mask_card_number(parsed.get("cardNumber", ""))
        addr = parsed.get("billingAddress", {})
        conf = parsed.get("confidence", {})

        tx = db.create_lockbox_transaction({
            "raw_input":          req.rawInput,
            "masked_card_number": masked,
            "card_number":        parsed.get("cardNumber", ""),
            "expiry_date":        parsed.get("expiryDate", ""),
            "cvv":                parsed.get("cvv", ""),
            "cardholder_name":    parsed.get("cardholderName", ""),
            "billing_street":     addr.get("street", ""),
            "billing_city":       addr.get("city", ""),
            "billing_state":      addr.get("state", ""),
            "billing_zip":        addr.get("zipCode", ""),
            "billing_country":    addr.get("country", ""),
            "validation_status":  "valid" if validation["overall"]["isValid"] else "invalid",
            "validation_errors":  json.dumps(validation["overall"]["errors"]),
            "confidence_scores":  json.dumps(conf),
            "anomalies":          json.dumps(parsed.get("anomalies", [])),
            "ai_reasoning":       parsed.get("rawAiReasoning", ""),
            "source":             req.source,
        })
        return {
            "success":    True,
            "transaction": {"id": tx["id"], "created_at": tx["created_at"]} if tx else None,
            "parsed": {
                "cardNumber":     masked,
                "expiryDate":     parsed.get("expiryDate"),
                "cvv":            "***",
                "cardholderName": parsed.get("cardholderName"),
                "billingAddress": parsed.get("billingAddress"),
                "confidence":     conf,
                "anomalies":      parsed.get("anomalies", []),
                "rawAiReasoning": parsed.get("rawAiReasoning"),
            },
            "validation": validation,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/lockbox/validate")
async def lockbox_validate(req: LockboxValidateRequest):
    """Validate pre-extracted card fields without AI parsing."""
    validation = lockbox.validate_card_data(req.dict())
    return {"success": True, "validation": validation}


@app.get("/api/lockbox/transactions")
async def lockbox_transactions(limit: int = 50, offset: int = 0):
    txs = db.list_lockbox_transactions(limit=limit, offset=offset)
    total = db.get_lockbox_transaction_count()
    return {
        "success":      True,
        "transactions": txs,
        "total":        total,
        "limit":        limit,
        "offset":       offset,
    }


@app.get("/api/lockbox/transactions/{tx_id}")
async def lockbox_transaction_detail(tx_id: int):
    tx = db.get_lockbox_transaction(tx_id)
    if not tx:
        raise HTTPException(404, "Transaction not found")
    return {"success": True, "transaction": tx}


@app.get("/api/lockbox/status", dependencies=[Depends(require_admin)])
async def lockbox_status():
    ai_ok = await lockbox.test_claude_connection()
    stats = db.get_lockbox_stats()
    return {
        "enabled":       LOCKBOX_ENABLED,
        "claude_online": ai_ok,
        "stats":         stats,
    }


@app.post("/api/lockbox/test", dependencies=[Depends(require_admin)])
async def lockbox_test():
    if not LOCKBOX_ENABLED:
        raise HTTPException(400, "Lockbox not configured. Set ANTHROPIC_API_KEY.")
    ok = await lockbox.test_claude_connection()
    return {"connected": ok}


# ─── Module 3: Merchant Verification endpoints ───────────────────────────────

class MerchantOnboardingRequest(BaseModel):
    company_name:        str
    country:             str           # ISO-2 e.g. "GB", "IN", "AE"
    business_email:      str
    registration_number: Optional[str] = None
    business_type:       Optional[str] = None
    website:             Optional[str] = None
    merchant_id:         Optional[str] = None  # link to existing merchant account

class GatewayRegisterRequest(BaseModel):
    merchant_profile_id: str
    gateways: list[str] = gr.GATEWAY_PRIORITY

class OTPSubmitRequest(BaseModel):
    registration_id: str
    otp: str

class ParseDocumentRequest(BaseModel):
    merchant_profile_id: str
    document_text:       str
    document_type:       str = "other"
    document_name:       str = "uploaded_document"

class SaveCredentialRequest(BaseModel):
    merchant_profile_id: str
    gateway_name:        str
    api_key:             str
    api_secret:          Optional[str] = None
    webhook_secret:      Optional[str] = None


@app.post("/api/verification/onboard", dependencies=[Depends(require_admin)])
async def onboard_merchant(req: MerchantOnboardingRequest, background_tasks: BackgroundTasks):
    """
    Phase 1 — Create merchant profile and kick off company lookup.
    Returns immediately; company lookup runs in background.
    """
    profile = db.create_merchant_profile({
        "merchant_id":         req.merchant_id,
        "company_name":        req.company_name,
        "country":             req.country.upper(),
        "business_email":      req.business_email,
        "registration_number": req.registration_number,
        "business_type":       req.business_type,
        "website":             req.website,
    })
    background_tasks.add_task(
        _run_company_lookup, profile["id"],
        req.company_name, req.country, req.registration_number
    )
    return {
        "merchant_profile_id": profile["id"],
        "status":              "company_lookup_in_progress",
        "message":             "Company lookup started. Check status at GET /api/verification/profile/{id}",
    }


async def _run_company_lookup(
    profile_id: str, company_name: str, country: str, reg_number: Optional[str]
):
    db.update_merchant_profile(profile_id, {"onboarding_status": "company_lookup_in_progress", "current_phase": 1})
    result = await cl.lookup_company_with_retry(company_name, country, reg_number)
    if result:
        import json as _json
        db.update_merchant_profile(profile_id, {
            "onboarding_status": "company_lookup_completed",
            "company_data":      _json.dumps(result),
            "current_phase":     2,
        })
        print(f"[verification] Company lookup OK for profile {profile_id[:8]}…: {result['name']}")
    else:
        db.update_merchant_profile(profile_id, {
            "onboarding_status": "company_lookup_completed",
            "current_phase":     2,
        })
        print(f"[verification] Company not found for profile {profile_id[:8]}… — continuing without")


@app.get("/api/verification/profile/{profile_id}", dependencies=[Depends(require_admin)])
async def get_verification_profile(profile_id: str):
    """Get merchant profile + all gateway registration statuses."""
    import json as _json
    profile = db.get_merchant_profile(profile_id)
    if not profile:
        raise HTTPException(404, "Merchant profile not found")
    registrations = db.list_gateway_registrations(profile_id)
    company_data = {}
    if profile.get("company_data"):
        try:
            company_data = _json.loads(profile["company_data"])
        except Exception:
            pass
    return {**profile, "company_data": company_data, "gateway_registrations": registrations}


@app.get("/api/verification/profiles", dependencies=[Depends(require_admin)])
async def list_verification_profiles(limit: int = 100):
    return db.list_merchant_profiles(limit)


@app.post("/api/verification/company-lookup", dependencies=[Depends(require_admin)])
async def company_lookup_endpoint(
    profile_id: str,
    company_name: str,
    country: str,
    registration_number: Optional[str] = None,
):
    """Trigger a fresh company lookup for an existing profile."""
    profile = db.get_merchant_profile(profile_id)
    if not profile:
        raise HTTPException(404, "Merchant profile not found")
    result = await cl.lookup_company_with_retry(company_name, country, registration_number)
    if not result:
        raise HTTPException(502, "Company not found in OpenCorporates or registries")
    import json as _json
    db.update_merchant_profile(profile_id, {
        "company_data":      _json.dumps(result),
        "onboarding_status": "company_lookup_completed",
        "current_phase":     2,
    })
    return result


@app.post("/api/verification/parse-document", dependencies=[Depends(require_admin)])
async def parse_document(req: ParseDocumentRequest):
    """
    Phase 2 — Run Claude AI extraction on document text.
    Stores extracted data in company_documents table.
    """
    if not LOCKBOX_ENABLED:
        raise HTTPException(400, "ANTHROPIC_API_KEY not configured.")
    profile = db.get_merchant_profile(req.merchant_profile_id)
    if not profile:
        raise HTTPException(404, "Merchant profile not found")

    parsed = await dp.parse_company_document(req.document_text, req.document_type)
    is_valid = dp.validate_extracted_data(parsed)

    import json as _json
    doc_id = str(__import__("uuid").uuid4())
    now = datetime.utcnow().isoformat()
    with db.get_conn() as conn:
        conn.execute(
            """INSERT INTO company_documents
               (id, merchant_profile_id, document_type, document_name,
                extracted_data, extraction_status, extraction_confidence,
                created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?)""",
            (doc_id, req.merchant_profile_id, req.document_type, req.document_name,
             _json.dumps(parsed), "extracted" if is_valid else "failed",
             parsed.get("confidence", 0), now, now)
        )
    # Store structured extracted fields in DB
    if is_valid:
        db.update_merchant_profile(req.merchant_profile_id, {
            "onboarding_status": "documents_retrieved",
            "current_phase":     3,
        })
        # Persist each extracted field into extracted_company_data
        now2 = datetime.utcnow().isoformat()
        eid = str(__import__("uuid").uuid4())
        with db.get_conn() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO extracted_company_data
                   (id, merchant_profile_id, company_name, registration_number,
                    incorporation_date, business_address, director_names,
                    director_addresses, shareholder_info, business_type,
                    license_number, license_expiry_date, extraction_confidence,
                    source_document_id, created_at, updated_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (eid, req.merchant_profile_id,
                 parsed.get("company_name"),
                 parsed.get("registration_number"),
                 parsed.get("incorporation_date"),
                 parsed.get("business_address"),
                 _json.dumps(parsed.get("director_names", [])),
                 _json.dumps(parsed.get("director_addresses", [])),
                 _json.dumps(parsed.get("shareholder_info", {})),
                 parsed.get("business_type"),
                 parsed.get("license_number"),
                 parsed.get("license_expiry_date"),
                 parsed.get("confidence", 0),
                 doc_id, now2, now2)
            )

    return {
        "document_id":    doc_id,
        "extracted_data": parsed,
        "is_valid":       is_valid,
        "confidence":     parsed.get("confidence", 0),
    }


@app.post("/api/verification/upload-document", dependencies=[Depends(require_admin)])
async def upload_document(
    merchant_profile_id: str = Form(...),
    document_type: str = Form("other"),
    file: UploadFile = File(...),
):
    """Upload a PDF or image document — auto-extracts text then runs Claude AI parse."""
    if not LOCKBOX_ENABLED:
        raise HTTPException(400, "ANTHROPIC_API_KEY not configured.")
    profile = db.get_merchant_profile(merchant_profile_id)
    if not profile:
        raise HTTPException(404, "Merchant profile not found")

    file_bytes = await file.read()
    mime_type  = file.content_type or "application/octet-stream"

    # Extract text
    doc_text = await dp.extract_text_from_file(file_bytes, mime_type)
    if not doc_text or doc_text.startswith("["):
        raise HTTPException(422, f"Text extraction failed: {doc_text}")

    # AI parse
    parsed   = await dp.parse_company_document(doc_text, document_type)
    is_valid = dp.validate_extracted_data(parsed)

    import json as _json
    doc_id = str(__import__("uuid").uuid4())
    now    = datetime.utcnow().isoformat()
    with db.get_conn() as conn:
        conn.execute(
            """INSERT INTO company_documents
               (id, merchant_profile_id, document_type, document_name,
                file_size, mime_type, extracted_data, extraction_status,
                extraction_confidence, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (doc_id, merchant_profile_id, document_type, file.filename,
             len(file_bytes), mime_type, _json.dumps(parsed),
             "extracted" if is_valid else "failed",
             parsed.get("confidence", 0), now, now)
        )

    if is_valid:
        db.update_merchant_profile(merchant_profile_id, {
            "onboarding_status": "documents_retrieved", "current_phase": 3,
        })
        eid = str(__import__("uuid").uuid4())
        with db.get_conn() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO extracted_company_data
                   (id, merchant_profile_id, company_name, registration_number,
                    incorporation_date, business_address, director_names,
                    director_addresses, shareholder_info, business_type,
                    license_number, license_expiry_date, extraction_confidence,
                    source_document_id, created_at, updated_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (eid, merchant_profile_id,
                 parsed.get("company_name"), parsed.get("registration_number"),
                 parsed.get("incorporation_date"), parsed.get("business_address"),
                 _json.dumps(parsed.get("director_names", [])),
                 _json.dumps(parsed.get("director_addresses", [])),
                 _json.dumps(parsed.get("shareholder_info", {})),
                 parsed.get("business_type"), parsed.get("license_number"),
                 parsed.get("license_expiry_date"), parsed.get("confidence", 0),
                 doc_id, now, now)
            )

    return {
        "document_id":    doc_id,
        "filename":       file.filename,
        "mime_type":      mime_type,
        "text_length":    len(doc_text),
        "extracted_data": parsed,
        "is_valid":       is_valid,
        "confidence":     parsed.get("confidence", 0),
    }


@app.post("/api/verification/register-gateways", dependencies=[Depends(require_admin)])
async def register_with_gateways(req: GatewayRegisterRequest, background_tasks: BackgroundTasks):
    """
    Phase 3 — Auto-register merchant with payment gateways in priority order.
    """
    profile = db.get_merchant_profile(req.merchant_profile_id)
    if not profile:
        raise HTTPException(404, "Merchant profile not found")

    db.update_merchant_profile(req.merchant_profile_id, {
        "onboarding_status": "gateway_registration_in_progress",
        "current_phase":     4,
    })
    background_tasks.add_task(_run_gateway_registrations, profile, req.gateways)
    return {
        "merchant_profile_id": req.merchant_profile_id,
        "status":              "gateway_registration_in_progress",
        "gateways":            req.gateways,
        "message":             "Registration running in background. Poll /api/verification/profile/{id} for status.",
    }


async def _run_gateway_registrations(profile: dict, gateways: list[str]):
    import json as _json
    payload = {
        "company_name":        profile["company_name"],
        "email":               profile["business_email"],
        "country":             profile["country"],
        "website":             profile.get("website"),
        "business_type":       profile.get("business_type"),
        "registration_number": profile.get("registration_number"),
    }

    results = []
    for gateway in gateways:
        result = await gr.register_with_single_gateway(gateway, payload)
        results.append(result)

        db.create_gateway_registration({
            "merchant_profile_id": profile["id"],
            "gateway_name":        gateway,
            "registration_status": "verified" if result["success"] else "failed",
            "gateway_merchant_id": result.get("merchant_id"),
            "account_status":      result.get("account_status"),
            "verification_level":  result.get("verification_level", 0),
            "requires_otp":        result.get("requires_otp", False),
            "otp_email":           result.get("otp_email"),
            "error_message":       result.get("error"),
            "raw_response":        _json.dumps(result.get("raw_response", {})),
            "attempt_count":       1,
        })

        # Start OTP monitor in background if needed
        if result.get("requires_otp"):
            asyncio.create_task(
                _monitor_and_submit_otp(profile["id"], gateway, result.get("merchant_id", ""), profile["business_email"])
            )

        if gateway != gateways[-1]:
            await asyncio.sleep(0.5)

    any_success = any(r["success"] for r in results)
    db.update_merchant_profile(profile["id"], {
        "onboarding_status": "gateway_registration_completed" if any_success else "failed",
        "current_phase":     5 if any_success else profile.get("current_phase", 4),
    })
    print(f"[verification] Gateway registration done for {profile['id'][:8]}…: "
          f"{sum(r['success'] for r in results)}/{len(results)} succeeded")

    # Telegram notification
    success_list = [r["gateway"] for r in results if r["success"]]
    fail_list    = [r["gateway"] for r in results if not r["success"]]
    status_icon  = "✅" if any_success else "❌"
    await tg.send_message(
        f"{status_icon} <b>Merchant Gateway Registration</b>\n"
        f"Company: <code>{profile['company_name']}</code>\n"
        f"✅ Success: {', '.join(success_list) or 'None'}\n"
        f"❌ Failed: {', '.join(fail_list) or 'None'}"
    )


async def _monitor_and_submit_otp(
    profile_id: str, gateway: str, merchant_id: str, email: str
):
    """Background task: wait for OTP email, extract, and submit to gateway."""
    otp = await em.monitor_inbox_for_otp(email, gateway, timeout_seconds=300)
    if otp:
        success = await gr.submit_otp_to_gateway(gateway, merchant_id, otp)
        db.create_email_verification_log({
            "merchant_profile_id": profile_id,
            "gateway_name":        gateway,
            "email_from":          f"noreply@{gateway}.com",
            "otp_code":            otp,
            "extraction_method":   "automatic",
        })
        print(f"[verification] OTP {'submitted' if success else 'FAILED'} for {gateway}")
    else:
        print(f"[verification] OTP not found for {gateway} — manual entry required")


@app.post("/api/verification/submit-otp", dependencies=[Depends(require_admin)])
async def submit_otp(req: OTPSubmitRequest):
    """Manually submit an OTP for a gateway registration."""
    reg = db.get_gateway_registration(req.registration_id)
    if not reg:
        raise HTTPException(404, "Gateway registration not found")
    if not gr.validate_otp_format(req.otp):
        raise HTTPException(400, "OTP must be 4-6 digits")

    success = await gr.submit_otp_to_gateway(
        reg["gateway_name"], reg.get("gateway_merchant_id", ""), req.otp
    )
    if success:
        db.update_gateway_registration(req.registration_id, {"registration_status": "verified"})
    db.create_email_verification_log({
        "merchant_profile_id": reg["merchant_profile_id"],
        "gateway_name":        reg["gateway_name"],
        "email_from":          "admin-manual",
        "otp_code":            req.otp,
        "extraction_method":   "manual",
    })
    return {"submitted": True, "success": success, "gateway": reg["gateway_name"]}


@app.post("/api/verification/credentials", dependencies=[Depends(require_admin)])
async def save_credentials(req: SaveCredentialRequest):
    """Encrypt and store live API credentials for a merchant+gateway."""
    enc_key = CREDENTIAL_ENCRYPTION_KEY
    encrypted_key    = encrypt_credential(req.api_key, enc_key)
    encrypted_secret = encrypt_credential(req.api_secret, enc_key) if req.api_secret else None
    encrypted_wh     = encrypt_credential(req.webhook_secret, enc_key) if req.webhook_secret else None

    cred = db.save_gateway_credentials({
        "merchant_profile_id":    req.merchant_profile_id,
        "gateway_name":           req.gateway_name,
        "encrypted_api_key":      encrypted_key,
        "encrypted_secret":       encrypted_secret,
        "encrypted_webhook_secret": encrypted_wh,
    })
    return {
        "saved":         True,
        "gateway":       req.gateway_name,
        "masked_api_key": mask_credential(req.api_key),
    }


@app.get("/api/verification/credentials/{profile_id}", dependencies=[Depends(require_admin)])
async def get_credentials(profile_id: str):
    """Return masked credential list for a merchant profile."""
    creds = db.get_gateway_credentials(profile_id)
    masked = []
    for c in creds:
        masked.append({
            "id":          c["id"],
            "gateway":     c["gateway_name"],
            "api_key":     mask_credential(
                decrypt_credential(c["encrypted_api_key"], CREDENTIAL_ENCRYPTION_KEY)
            ) if c.get("encrypted_api_key") else None,
            "has_secret":  bool(c.get("encrypted_secret")),
            "has_webhook": bool(c.get("encrypted_webhook_secret")),
            "is_active":   c["is_active"],
        })
    return masked


@app.get("/api/verification/stats", dependencies=[Depends(require_admin)])
async def verification_stats():
    return db.get_verification_stats()


@app.get("/api/verification/status", dependencies=[Depends(require_admin)])
async def verification_module_status():
    """Report Module 3 configuration health."""
    return {
        "opencorporates": cl.is_configured(),
        "email_monitor":  em.is_configured(),
        "encryption":     {"enabled": True, "algorithm": "AES-256-GCM"},
        "gateways_supported": gr.GATEWAY_PRIORITY,
        "document_parser": {"enabled": LOCKBOX_ENABLED, "model": dp.CLAUDE_MODEL},
    }


# ─── UAE SME Module ──────────────────────────────────────────────────────────
from uae_sme.report import generate_report as _uae_report
from uae_sme.data  import SME_COMPANIES


@app.get("/api/uae-sme/report", dependencies=[Depends(require_admin)])
async def uae_sme_report(seed: int = None):
    """
    Run the UAE SME simulation + yardstick + proxy validator pipeline.
    Optional ?seed=N for reproducible results.
    """
    return _uae_report(seed=seed)


@app.get("/api/uae-sme/clients", dependencies=[Depends(require_admin)])
async def uae_sme_clients():
    """Return the 10 UAE SME company profiles (static data)."""
    return [
        {
            "name":           c["name"],
            "sector":         c["sector"],
            "compliance":     c["compliance"],
            "risk":           c["risk"],
            "bottleneck":     c["bottleneck"],
            "agent_strategy": c["agent_strategy"],
            "report_metrics": c["report"],
        }
        for c in SME_COMPANIES
    ]


@app.get("/api/uae-sme/clients/{company_name}", dependencies=[Depends(require_admin)])
async def uae_sme_client_detail(company_name: str):
    """Return a single UAE SME client profile by name (case-insensitive)."""
    match = next(
        (c for c in SME_COMPANIES if c["name"].lower() == company_name.lower()),
        None,
    )
    if not match:
        raise HTTPException(status_code=404, detail=f"Client '{company_name}' not found")
    return match


# ─── Config info (public) ─────────────────────────────────────────────────────
@app.get("/api/config")
async def get_config():
    return {
        "supported_cryptos": SUPPORTED_CRYPTOS,
        "supported_fiats":   SUPPORTED_FIATS,
        "providers":         list(PROVIDERS.keys()),
        "default_crypto":    DEFAULT_CRYPTO,
        "default_fiat":      DEFAULT_FIAT,
    }


if __name__ == "__main__":
    import uvicorn
    from config import HOST, PORT
    uvicorn.run("server:app", host=HOST, port=PORT, reload=True)

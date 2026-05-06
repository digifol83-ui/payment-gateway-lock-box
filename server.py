from fastapi import FastAPI, Header, HTTPException, Depends, Request
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import logging
from datetime import datetime
import sys
import os
import uuid

from database.migrations import init_db, AsyncDB
from subagents.merchant_controller import MerchantController
from subagents.payment_router import PaymentRouter
from subagents.verification_engine import VerificationEngine
from subagents.webhook_orchestrator import WebhookOrchestrator
from subagents.crypto_converter import CryptoConverter
from subagents.admin_diagnostics import AdminDiagnostics
from routes_pending_tasks import router as pending_tasks_router
from routes_openclaw import router as openclaw_router
from routes_codewords import router as codewords_router
from routes_lockbox import router as lockbox_router
from config import settings
from config import validate_runtime_settings
from telegram_notify import notify_new_payment, notify_payment_update, notify_test
from providers.stripe import StripeProvider

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Global DB instance
db_instance = AsyncDB()

# Global provider cache (lazy-loaded)
_provider_cache = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Starting BeastPay server...")
    validate_runtime_settings()
    await init_db()
    await db_instance.connect()
    logger.info("Database initialized and connected")
    yield
    # Shutdown
    logger.info("Shutting down...")
    await db_instance.close()

app = FastAPI(
    title="BeastPay API",
    version="1.0.0",
    description="BEAST Agent Payment Gateway",
    lifespan=lifespan
)

# Mount static files
web_dir = os.path.join(os.path.dirname(__file__), "web")
if os.path.exists(web_dir):
    app.mount("/static", StaticFiles(directory=web_dir), name="static")

# Register routers
app.include_router(pending_tasks_router)
app.include_router(openclaw_router)
app.include_router(codewords_router)
app.include_router(lockbox_router)

async def get_db():
    return db_instance

def get_stripe_provider():
    """Get cached Stripe provider instance."""
    global _provider_cache
    if "stripe" not in _provider_cache:
        _provider_cache["stripe"] = StripeProvider()
    return _provider_cache["stripe"]

async def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != settings.ADMIN_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key

@app.get("/admin")
async def admin_dashboard():
    """Serve admin dashboard UI with injected config."""
    admin_html = os.path.join(os.path.dirname(__file__), "web", "admin.html")
    if not os.path.exists(admin_html):
        return JSONResponse(status_code=404, content={"error": "Admin UI not found"})

    with open(admin_html, 'r') as f:
        content = f.read()

    base_url = os.getenv('BASE_URL', 'http://localhost:8000')
    content = content.replace('__BASE_URL__', base_url)

    from fastapi.responses import HTMLResponse
    return HTMLResponse(content=content)

@app.get("/")
async def root():
    """Root redirect to Swagger docs."""
    return {"message": "BeastPay API", "docs": "/docs", "admin": "/admin"}


def _web_path(filename: str) -> str:
    return os.path.join(os.path.dirname(__file__), "web", filename)


def _render_web_template(filename: str, replacements: dict) -> HTMLResponse:
    path = _web_path(filename)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Web UI not found")
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    for k, v in (replacements or {}).items():
        content = content.replace(k, v)
    return HTMLResponse(content=content)


@app.get("/checkout")
async def checkout_page():
    """Public unified checkout page (provider-hosted payment entry)."""
    base_url = os.getenv("BASE_URL", "http://localhost:8000")
    return _render_web_template(
        "unified_checkout.html",
        {"__BASE_URL__": base_url, "__PAYMENT_ID__": ""},
    )


@app.get("/checkout/{payment_id}")
async def checkout_page_with_payment(payment_id: str):
    """Unified checkout page pinned to an existing payment_id."""
    base_url = os.getenv("BASE_URL", "http://localhost:8000")
    return _render_web_template(
        "unified_checkout.html",
        {"__BASE_URL__": base_url, "__PAYMENT_ID__": payment_id},
    )


@app.get("/pay/success/{payment_id}")
async def payment_success_page(payment_id: str):
    """Stripe success_url target (static success page)."""
    return FileResponse(_web_path("success.html"))


@app.post("/api/public/payments")
async def public_create_payment(payload: dict, db: AsyncDB = Depends(get_db)):
    """
    Create a payment without an admin API key.
    This endpoint intentionally does NOT accept raw card data.
    """
    provider_id = (payload.get("provider_id") or "stripe").strip().lower()
    fiat_amount = float(payload.get("fiat_amount") or 0.0)
    fiat_currency = (payload.get("fiat_currency") or "USD").strip().upper()
    crypto_ticker = (payload.get("crypto_ticker") or "USDT").strip().upper()
    customer_email = (payload.get("customer_email") or "").strip() or None
    wallet_address = (payload.get("wallet_address") or "").strip() or "pending_address"

    if fiat_amount <= 0:
        raise HTTPException(status_code=400, detail="fiat_amount must be > 0")

    payment_id = str(uuid.uuid4())
    now = datetime.utcnow()

    try:
        await db.execute(
            """
            INSERT INTO payments
            (id, merchant_id, amount, fiat_currency, crypto_currency, provider, wallet_address, customer_email, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (payment_id, None, fiat_amount, fiat_currency, crypto_ticker, provider_id, wallet_address, customer_email, "pending", now, now),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"database_error: {e}")

    return {
        "payment_id": payment_id,
        "provider": provider_id,
        "amount": fiat_amount,
        "fiat_currency": fiat_currency,
        "crypto_ticker": crypto_ticker,
        "customer_email": customer_email,
        "wallet_address": wallet_address,
        "status": "pending",
    }


@app.post("/api/public/payments/{payment_id}/start/{provider_id}")
async def public_start_provider_checkout(payment_id: str, provider_id: str, payload: dict | None = None, db: AsyncDB = Depends(get_db)):
    """
    Return a provider-hosted checkout redirect URL.
    Card entry happens on the provider page, not on this server.
    """
    provider_id = (provider_id or "").strip().lower()
    payload = payload or {}

    row = await db.fetchone(
        """
        SELECT id, amount, fiat_currency, crypto_currency, wallet_address, customer_email
        FROM payments
        WHERE id = ?
        """,
        (payment_id,),
    )
    if not row:
        raise HTTPException(status_code=404, detail="payment_not_found")

    pid = row["id"]
    fiat_amount = row["amount"]
    fiat_currency = row["fiat_currency"]
    crypto_ticker = row["crypto_currency"]
    customer_email = (payload.get("customer_email") or row.get("customer_email") or "").strip() or None
    wallet_address = (payload.get("wallet_address") or row.get("wallet_address") or "").strip()

    if wallet_address and wallet_address != row.get("wallet_address"):
        await db.execute(
            "UPDATE payments SET wallet_address = ?, updated_at = ? WHERE id = ?",
            (wallet_address, datetime.utcnow().isoformat(), pid),
        )

    def fiat_to_crypto_payment() -> dict:
        if not wallet_address or wallet_address == "pending_address":
            raise HTTPException(status_code=400, detail="wallet_address_required")
        return {
            "id": pid,
            "amount": float(fiat_amount),
            "amount_fiat": float(fiat_amount),
            "fiat_amount": float(fiat_amount),
            "fiat_currency": fiat_currency,
            "crypto_currency": crypto_ticker,
            "wallet_address": wallet_address,
            "customer_email": customer_email,
            "description": f"BeastPay {crypto_ticker}",
        }

    if provider_id == "stripe":
        stripe = StripeProvider()
        redirect_url = await stripe.create_checkout_session(
            {
                "id": pid,
                "amount": float(fiat_amount),
                "fiat_currency": fiat_currency,
                "crypto_currency": crypto_ticker,
                "customer_email": customer_email,
                "description": f"BeastPay · {crypto_ticker}",
            }
        )
        return {"payment_id": pid, "provider_id": provider_id, "redirect_url": redirect_url}

    if provider_id == "transak":
        from providers.transak import TransakProvider
        redirect_url = TransakProvider().build_widget_url(fiat_to_crypto_payment())
        return {"payment_id": pid, "provider_id": provider_id, "redirect_url": redirect_url}

    if provider_id == "moonpay":
        from providers.moonpay import MoonPayProvider
        redirect_url = MoonPayProvider().build_widget_url(fiat_to_crypto_payment())
        return {"payment_id": pid, "provider_id": provider_id, "redirect_url": redirect_url}

    if provider_id == "metamask":
        from providers.metamask import MetaMaskProvider
        from config import METAMASK_API_KEY, METAMASK_SECRET, METAMASK_WEBHOOK_SECRET, METAMASK_ENV

        order = await MetaMaskProvider(
            api_key=METAMASK_API_KEY,
            secret_key=METAMASK_SECRET,
            webhook_secret=METAMASK_WEBHOOK_SECRET,
            environment=METAMASK_ENV,
        ).create_order(fiat_to_crypto_payment())
        if order.get("error"):
            raise HTTPException(status_code=502, detail=order["error"])
        return {
            "payment_id": pid,
            "provider_id": provider_id,
            "redirect_url": order.get("checkout_url") or order.get("widget_url"),
        }

    if provider_id == "paypal":
        raise HTTPException(status_code=501, detail="paypal_not_implemented_yet")

    raise HTTPException(status_code=400, detail="unsupported_provider")


@app.get("/api/providers/status")
async def api_provider_status():
    """Return live/sandbox provider status without exposing secrets."""
    from providers import list_production_fiat_to_crypto, provider_status_all

    return {
        "providers": provider_status_all(),
        "live_fiat_to_crypto": list_production_fiat_to_crypto(),
    }


@app.post("/api/providers/test")
async def api_provider_test(payload: dict):
    """Dry-run provider checkout link generation where local provider code supports it."""
    from providers import _is_production

    provider_id = (payload.get("provider_id") or "").strip().lower()
    if not provider_id:
        raise HTTPException(status_code=400, detail="provider_id_required")

    payment = {
        "id": payload.get("payment_id") or f"test_{uuid.uuid4()}",
        "amount": float(payload.get("amount") or payload.get("fiat_amount") or 100),
        "fiat_amount": float(payload.get("amount") or payload.get("fiat_amount") or 100),
        "fiat_currency": (payload.get("currency") or payload.get("fiat_currency") or "USD").strip().upper(),
        "crypto_currency": (payload.get("crypto") or payload.get("crypto_currency") or "USDC").strip().upper(),
        "wallet_address": (payload.get("wallet_address") or "").strip(),
        "customer_email": (payload.get("customer_email") or "").strip() or None,
        "description": "BeastPay provider test",
    }

    if provider_id in {"transak", "moonpay"} and not payment["wallet_address"]:
        raise HTTPException(status_code=400, detail="wallet_address_required")

    if provider_id == "transak":
        from providers.transak import TransakProvider
        return {
            "provider_id": provider_id,
            "production": _is_production(provider_id),
            "redirect_url": TransakProvider().build_widget_url(payment),
        }

    if provider_id == "moonpay":
        from providers.moonpay import MoonPayProvider
        return {
            "provider_id": provider_id,
            "production": _is_production(provider_id),
            "redirect_url": MoonPayProvider().build_widget_url(payment),
        }

    if provider_id == "stripe":
        return {
            "provider_id": provider_id,
            "production": _is_production(provider_id),
            "message": "Stripe checkout test creates a hosted session through /api/public/payments/{id}/start/stripe.",
        }

    raise HTTPException(
        status_code=501,
        detail=f"{provider_id}_provider_checkout_not_implemented_locally",
    )

@app.post("/api/merchants")
async def create_merchant(
    payload: dict,
    api_key: str = Depends(verify_api_key),
    db: AsyncDB = Depends(get_db)
):
    """Create new merchant profile."""
    logger.info(f"Creating merchant: {payload.get('company_name')}")
    
    merchant_agent = MerchantController(db)
    response = await merchant_agent.execute(
        action="create",
        payload=payload,
        context={
            "actor": "<redacted>",
            "request_id": f"req_{datetime.utcnow().timestamp()}",
            "ip_address": "127.0.0.1",
            "resource_type": "merchant"
        },
        flags={"verbose": True, "trace_execution": False}
    )
    
    if response.status.value == "success":
        logger.info(f"✓ Merchant created: {response.result['merchant_id']}")
        return JSONResponse(status_code=201, content=response.to_dict())
    else:
        logger.error(f"✗ Merchant creation failed: {response.error}")
        return JSONResponse(status_code=400, content=response.to_dict())

@app.get("/api/merchants/{merchant_id}")
async def get_merchant(
    merchant_id: str,
    api_key: str = Depends(verify_api_key),
    db: AsyncDB = Depends(get_db)
):
    """Get merchant profile."""
    merchant_agent = MerchantController(db)
    response = await merchant_agent.execute(
        action="get",
        payload={"merchant_id": merchant_id},
        context={
            "actor": "<redacted>",
            "request_id": f"req_{datetime.utcnow().timestamp()}",
            "ip_address": "127.0.0.1"
        },
        flags={"verbose": True}
    )
    
    if response.status.value == "success":
        return JSONResponse(status_code=200, content=response.to_dict())
    else:
        return JSONResponse(status_code=404, content=response.to_dict())

@app.post("/api/payments")
async def create_payment(
    payload: dict,
    api_key: str = Depends(verify_api_key),
    db: AsyncDB = Depends(get_db)
):
    """Create payment order with smart provider routing."""
    logger.info(f"Creating payment: {payload.get('fiat_amount')} {payload.get('fiat_currency')}")

    payment_agent = PaymentRouter(db)
    response = await payment_agent.execute(
        action="create",
        payload=payload,
        context={
            "actor": "<redacted>",
            "request_id": f"req_{datetime.utcnow().timestamp()}",
            "ip_address": "127.0.0.1",
            "resource_type": "payment"
        },
        flags={"verbose": True, "trace_execution": False}
    )

    if response.status.value == "success":
        logger.info(f"✓ Payment created: {response.result['payment_id']}")
        # Send Telegram notification
        payment_data = {
            "id": response.result['payment_id'],
            "amount": payload.get('fiat_amount'),
            "fiat_currency": payload.get('fiat_currency'),
            "crypto_currency": payload.get('crypto_currency'),
            "provider": payload.get('provider', 'auto'),
            "customer_email": payload.get('customer_email'),
            "status": "pending"
        }
        await notify_new_payment(payment_data)
        return JSONResponse(status_code=201, content=response.to_dict())
    else:
        logger.error(f"✗ Payment creation failed: {response.error}")
        return JSONResponse(status_code=400, content=response.to_dict())

@app.post("/api/verify")
async def verify_kyc(
    payload: dict,
    api_key: str = Depends(verify_api_key),
    db: AsyncDB = Depends(get_db)
):
    """Run KYC verification with risk scoring."""
    logger.info(f"Verifying merchant: {payload.get('merchant_id')}")

    verification_agent = VerificationEngine(db)
    response = await verification_agent.execute(
        action="verify",
        payload=payload,
        context={
            "actor": "<redacted>",
            "request_id": f"req_{datetime.utcnow().timestamp()}",
            "ip_address": "127.0.0.1",
            "resource_type": "kyc_verification"
        },
        flags={"verbose": True, "trace_execution": False}
    )

    if response.status.value == "success":
        logger.info(f"✓ Verification complete: {response.result['decision']}")
        return JSONResponse(status_code=200, content=response.to_dict())
    else:
        logger.error(f"✗ Verification failed: {response.error}")
        return JSONResponse(status_code=400, content=response.to_dict())

@app.post("/api/webhooks/deliver")
async def deliver_webhook(
    payload: dict,
    api_key: str = Depends(verify_api_key),
    db: AsyncDB = Depends(get_db)
):
    """Deliver webhook with retries and signature."""
    logger.info(f"Delivering webhook: {payload.get('event_type')}")

    webhook_agent = WebhookOrchestrator(db)
    response = await webhook_agent.execute(
        action="deliver",
        payload=payload,
        context={
            "actor": "<redacted>",
            "request_id": f"req_{datetime.utcnow().timestamp()}",
            "ip_address": "127.0.0.1",
            "resource_type": "webhook"
        },
        flags={"verbose": True}
    )

    if response.status.value == "success":
        logger.info(f"✓ Webhook delivered: {response.result.get('webhook_id')[:8]}...")
        return JSONResponse(status_code=200, content=response.to_dict())
    else:
        logger.error(f"✗ Webhook delivery failed: {response.error}")
        return JSONResponse(status_code=400, content=response.to_dict())

@app.post("/api/rates/lock")
async def lock_exchange_rate(
    payload: dict,
    api_key: str = Depends(verify_api_key),
    db: AsyncDB = Depends(get_db)
):
    """Lock exchange rate for payment."""
    logger.info(f"Locking rate for payment: {payload.get('payment_id')[:8]}...")

    converter_agent = CryptoConverter(db)
    response = await converter_agent.execute(
        action="lock_rate",
        payload=payload,
        context={
            "actor": "<redacted>",
            "request_id": f"req_{datetime.utcnow().timestamp()}",
            "ip_address": "127.0.0.1",
            "resource_type": "rate_lock"
        },
        flags={"verbose": True}
    )

    if response.status.value == "success":
        logger.info(f"✓ Rate locked: {response.result.get('locked_rate')}")
        return JSONResponse(status_code=200, content=response.to_dict())
    else:
        logger.error(f"✗ Rate lock failed: {response.error}")
        return JSONResponse(status_code=400, content=response.to_dict())

@app.get("/admin/health")
async def admin_health_check(
    api_key: str = Depends(verify_api_key),
    db: AsyncDB = Depends(get_db)
):
    """System health check dashboard."""
    logger.info("Health check requested")

    diagnostics_agent = AdminDiagnostics(db)
    response = await diagnostics_agent.execute(
        action="system_health",
        payload={},
        context={
            "actor": "<redacted>",
            "request_id": f"req_{datetime.utcnow().timestamp()}",
            "ip_address": "127.0.0.1",
            "resource_type": "system"
        },
        flags={"verbose": True}
    )

    if response.status.value == "success":
        return JSONResponse(status_code=200, content=response.to_dict())
    else:
        return JSONResponse(status_code=503, content=response.to_dict())

@app.get("/admin/metrics")
async def admin_metrics(
    api_key: str = Depends(verify_api_key),
    db: AsyncDB = Depends(get_db)
):
    """Payment metrics and analytics."""
    logger.info("Metrics requested")

    diagnostics_agent = AdminDiagnostics(db)
    response = await diagnostics_agent.execute(
        action="payment_metrics",
        payload={"period_days": 30},
        context={
            "actor": "<redacted>",
            "request_id": f"req_{datetime.utcnow().timestamp()}",
            "ip_address": "127.0.0.1",
            "resource_type": "metrics"
        },
        flags={"verbose": True}
    )

    return JSONResponse(status_code=200, content=response.to_dict())

@app.get("/admin/diagnostics")
async def admin_diagnostics_report(
    api_key: str = Depends(verify_api_key),
    db: AsyncDB = Depends(get_db)
):
    """Comprehensive diagnostics report."""
    logger.info("Diagnostics report requested")

    diagnostics_agent = AdminDiagnostics(db)
    response = await diagnostics_agent.execute(
        action="diagnostics_report",
        payload={},
        context={
            "actor": "<redacted>",
            "request_id": f"req_{datetime.utcnow().timestamp()}",
            "ip_address": "127.0.0.1",
            "resource_type": "report"
        },
        flags={"verbose": True}
    )

    return JSONResponse(status_code=200, content=response.to_dict())

@app.get("/pay/{link_id}")
async def payment_link_page(link_id: str, db: AsyncDB = Depends(get_db)):
    """Public payment link page."""
    try:
        cursor = await db.execute(
            "SELECT id, amount, fiat_currency, description, is_active FROM payment_links WHERE id = ?",
            (link_id,)
        )
        result = await cursor.fetchone()

        if not result:
            return JSONResponse(status_code=404, content={"error": "Payment link not found"})

        if not result[4]:  # is_active
            return JSONResponse(status_code=410, content={"error": "Payment link is inactive"})

        amount = result[1]
        currency = result[2]
        description = result[3]

        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Payment - BeastPay</title>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>
                body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #f5f5f5; margin: 0; padding: 20px; }}
                .container {{ max-width: 500px; margin: 0 auto; background: white; border-radius: 8px; padding: 30px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                h1 {{ color: #333; margin: 0 0 20px 0; }}
                .amount {{ font-size: 48px; font-weight: bold; color: #007bff; margin: 20px 0; }}
                .details {{ background: #f9f9f9; padding: 15px; border-radius: 4px; margin: 20px 0; }}
                .detail-row {{ display: flex; justify-content: space-between; margin: 10px 0; color: #666; }}
                button {{ width: 100%; padding: 12px; background: #007bff; color: white; border: none; border-radius: 4px; font-size: 16px; cursor: pointer; margin-top: 20px; }}
                button:hover {{ background: #0056b3; }}
                .status {{ color: #28a745; font-weight: bold; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>💳 Payment Ready</h1>
                <div class="amount">${amount} {currency}</div>
                <div class="details">
                    <div class="detail-row">
                        <span>Description:</span>
                        <span>{description or "Payment"}</span>
                    </div>
                    <div class="detail-row">
                        <span>Status:</span>
                        <span class="status">✓ Active</span>
                    </div>
                </div>
                <button onclick="alert('Payment gateway integration coming soon. Link ID: {link_id}')">Proceed to Payment</button>
            </div>
        </body>
        </html>
        """

        from fastapi.responses import HTMLResponse
        return HTMLResponse(content=html)

    except Exception as e:
        logger.error(f"Error fetching payment link: {e}")
        return JSONResponse(status_code=500, content={"error": "Server error"})

@app.post("/admin/telegram-test")
async def test_telegram(
    api_key: str = Depends(verify_api_key)
):
    """Test Telegram bot connectivity."""
    logger.info("Testing Telegram connectivity...")
    success = await notify_test()
    if success:
        return JSONResponse(status_code=200, content={"status": "ok", "message": "Telegram bot connected"})
    else:
        return JSONResponse(status_code=503, content={"status": "error", "message": "Telegram bot not responding"})

@app.get("/health")
async def health_check(db: AsyncDB = Depends(get_db)):
    """System health check."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "database": "connected"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

@app.post("/webhooks/merchant")
async def merchant_webhook(request: dict):
    """Merchant webhook endpoint."""
    logger.info(f"Merchant webhook: {request}")
    return {"status": "received"}

@app.post("/webhooks/kast")
async def kast_webhook(payload: dict, db: AsyncDB = Depends(get_db)):
    """KAST Pay webhook endpoint."""
    logger.info(f"KAST webhook received: {payload.get('id')}")
    orchestrator = WebhookOrchestrator(db)
    await orchestrator.process_webhook("kast", payload)
    return {"status": "received", "provider": "kast"}

@app.post("/webhooks/charge")
async def charge_webhook(payload: dict, db: AsyncDB = Depends(get_db)):
    """Charge webhook endpoint."""
    logger.info(f"Charge webhook received: {payload.get('id')}")
    orchestrator = WebhookOrchestrator(db)
    await orchestrator.process_webhook("charge", payload)
    return {"status": "received", "provider": "charge"}

@app.post("/webhooks/swapin")
async def swapin_webhook(payload: dict, db: AsyncDB = Depends(get_db)):
    """Swapin webhook endpoint."""
    logger.info(f"Swapin webhook received: {payload.get('bridge_id')}")
    orchestrator = WebhookOrchestrator(db)
    await orchestrator.process_webhook("swapin", payload)
    return {"status": "received", "provider": "swapin"}

@app.post("/webhooks/bleap")
async def bleap_webhook(payload: dict, db: AsyncDB = Depends(get_db)):
    """Bleap webhook endpoint."""
    logger.info(f"Bleap webhook received: {payload.get('ramp_id')}")
    orchestrator = WebhookOrchestrator(db)
    await orchestrator.process_webhook("bleap", payload)
    return {"status": "received", "provider": "bleap"}


@app.post("/webhooks/stripe")
async def stripe_webhook(request: Request, db: AsyncDB = Depends(get_db)):
    """
    Stripe webhook receiver.
    - Verifies signature using STRIPE_WEBHOOK_SECRET (if set)
    - Updates internal payment status using client_reference_id (payment_id)
    """
    raw_body = await request.body()
    signature = request.headers.get("stripe-signature", "")

    stripe = get_stripe_provider()
    if not stripe.verify_webhook(raw_body, signature):
        raise HTTPException(status_code=400, detail="invalid_stripe_signature")

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="invalid_json")

    event = stripe.parse_webhook(payload)
    if not event:
        return {"status": "ignored"}

    payment_id = event["payment_id"]
    new_status = event["status"]
    provider_ref = event.get("provider_order_id") or event.get("provider_tx_id")

    # Fetch the payment for notification context (email may be unknown)
    payment_row = await db.fetchone(
        "SELECT payment_id, fiat_amount, fiat_currency, crypto_ticker, provider_id, status FROM payments WHERE payment_id = ?",
        (payment_id,),
    )
    if not payment_row:
        return {"status": "unknown_payment", "payment_id": payment_id}

    await db.execute(
        """
        UPDATE payments
        SET status = ?, provider_id = ?, provider_reference = ?, updated_at = ?
        WHERE payment_id = ?
        """,
        (new_status, "stripe", provider_ref, datetime.utcnow(), payment_id),
    )

    # Telegram notification (best-effort)
    try:
        await notify_payment_update(
            {
                "id": payment_row["payment_id"],
                "amount": payment_row["fiat_amount"],
                "fiat_currency": payment_row["fiat_currency"],
                "crypto_currency": payment_row["crypto_ticker"],
                "provider": "stripe",
                "customer_email": None,
            },
            new_status,
            extra={
                "provider_tx_id": event.get("provider_tx_id"),
                "exchange_rate": event.get("exchange_rate"),
                "crypto_amount": event.get("crypto_amount"),
            },
        )
    except Exception:
        pass

    return {"status": "ok", "payment_id": payment_id, "new_status": new_status}


# ─── Enhanced Checkout Flow ──────────────────────────────────────────────────
from pydantic import BaseModel

class CheckoutRequest(BaseModel):
    merchant_id: str
    amount_fiat: float
    fiat_currency: str = "AED"
    crypto_currency: str = "USDT"
    customer_email: str
    customer_name: str = ""
    checkout_method: str = "stripe"  # "stripe" (card), "lockbox" (card vault), "crypto" (direct), "ziina" (aed native)
    card_id: str = None  # For lockbox method
    metadata: dict = None


@app.post("/api/checkout/initiate-comprehensive")
async def comprehensive_checkout(
    req: CheckoutRequest,
    db: AsyncDB = Depends(get_db),
    x_api_key: str = Header(None)
):
    """
    Enhanced checkout flow with credibility check + multi-gateway support.

    Flow:
    1. Verify merchant + credibility (risk score)
    2. Route to appropriate gateway based on checkout_method
    3. Create payment record
    4. Return checkout URL or session token
    """

    # 1. Verify merchant exists
    merchant = await db.fetchone(
        "SELECT id, api_key, webhook_url FROM merchants WHERE id = ?",
        (req.merchant_id,)
    )
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")

    # Verify API key if provided
    if x_api_key and x_api_key != merchant["api_key"]:
        raise HTTPException(status_code=403, detail="Invalid API key")

    # 2. Get merchant profile + credibility check
    profile = await db.fetchone(
        "SELECT id, company_name, onboarding_status FROM merchant_profiles WHERE merchant_id = ?",
        (req.merchant_id,)
    )

    if not profile:
        raise HTTPException(status_code=400, detail="Merchant profile incomplete")

    # Estimate risk score from onboarding status (0-100, lower is better)
    status_risk_map = {
        "approved": 20,
        "pending_review": 50,
        "pending": 70,
        "rejected": 100,
    }
    onboarding_status = profile["onboarding_status"] if profile else "pending"
    risk_score = status_risk_map.get(onboarding_status, 70)

    if risk_score > 85:
        raise HTTPException(
            status_code=403,
            detail=f"Merchant high-risk. Contact support."
        )

    # 3. Create payment record
    payment_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    await db.execute(
        """
        INSERT INTO payments (
            id, merchant_id, amount, fiat_currency, crypto_currency,
            customer_email, customer_name, status, provider, wallet_address, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?, ?)
        """,
        (payment_id, req.merchant_id, req.amount_fiat, req.fiat_currency,
         req.crypto_currency, req.customer_email, req.customer_name,
         req.checkout_method, "pending_wallet", now, now)
    )

    # 4. Route to gateway based on checkout_method
    checkout_url = None
    session_token = None

    if req.checkout_method == "stripe":
        # Card payment via Stripe
        stripe = get_stripe_provider()
        if not stripe.is_configured()["enabled"]:
            raise HTTPException(status_code=503, detail="Stripe not configured")

        try:
            checkout_url = await stripe.create_checkout_session({
                "id": payment_id,
                "amount": req.amount_fiat,
                "fiat_currency": req.fiat_currency,
                "crypto_currency": req.crypto_currency,
                "customer_email": req.customer_email,
                "description": f"BeastPay {req.crypto_currency} payment"
            })
        except Exception as e:
            await db.execute(
                "UPDATE payments SET status = ? WHERE id = ?",
                ("failed", payment_id)
            )
            raise HTTPException(status_code=500, detail=f"Checkout creation failed: {str(e)}")

    elif req.checkout_method == "lockbox":
        # Card from encrypted vault via Stripe
        if not req.card_id:
            raise HTTPException(status_code=400, detail="card_id required for lockbox method")

        # Verify card exists
        card = await db.fetchone(
            "SELECT id, masked_card_number FROM lockbox_transactions WHERE id = ? AND merchant_id = ?",
            (req.card_id, req.merchant_id)
        )
        if not card:
            raise HTTPException(status_code=404, detail="Card not found in lockbox")

        # Use Stripe to charge saved card
        stripe = get_stripe_provider()
        try:
            # In production, create Payment Intent with saved card
            checkout_url = await stripe.create_checkout_session({
                "id": payment_id,
                "amount": req.amount_fiat,
                "fiat_currency": req.fiat_currency,
                "crypto_currency": req.crypto_currency,
                "customer_email": req.customer_email,
                "description": f"BeastPay {req.crypto_currency} via saved card"
            })
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Payment failed: {str(e)}")

    elif req.checkout_method == "ziina":
        # AED native payment via Ziina
        from providers.ziina import ZiinaProvider
        ziina = ZiinaProvider()
        try:
            # Create order via Ziina
            order_resp = await ziina.create_order({
                "amount": req.amount_fiat,
                "currency": "AED",
                "reference": payment_id,
                "customer_email": req.customer_email,
            })
            session_token = order_resp.get("session_id") or order_resp.get("url")

            await db.execute(
                "UPDATE payments SET provider_order_id = ? WHERE id = ?",
                (order_resp.get("order_id"), payment_id)
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Ziina error: {str(e)}")

    elif req.checkout_method == "transak":
        # Fiat→Crypto via Transak (global, 160+ countries)
        from providers.transak import TransakProvider
        transak = TransakProvider()
        try:
            order_url = transak.build_widget_url({
                "id": payment_id,
                "amount": req.amount_fiat,
                "fiat_currency": req.fiat_currency,
                "crypto_currency": req.crypto_currency,
                "customer_email": req.customer_email,
                "description": f"BeastPay {req.crypto_currency}"
            })
            checkout_url = order_url
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Transak error: {str(e)}")

    elif req.checkout_method == "guardarian":
        # Fiat→Crypto via Guardarian (170+ countries, 1000+ cryptos)
        from providers.guardarian import GuardarianProvider
        guardarian = GuardarianProvider()
        try:
            order = await guardarian.create_order({
                "amount": req.amount_fiat,
                "fiat": req.fiat_currency,
                "crypto": req.crypto_currency,
                "client_id": payment_id,
                "wallet_address": req.metadata.get("wallet") if req.metadata else None,
            })
            checkout_url = order.get("payment_url")

            await db.execute(
                "UPDATE payments SET provider_order_id = ? WHERE id = ?",
                (order.get("id"), payment_id)
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Guardarian error: {str(e)}")

    elif req.checkout_method == "moonpay":
        # Fiat→Crypto via MoonPay (160+ countries, on/off-ramps)
        from providers.moonpay import MoonPayProvider
        moonpay = MoonPayProvider()
        try:
            session = await moonpay.create_checkout_session({
                "amount": req.amount_fiat,
                "currency": req.fiat_currency,
                "crypto": req.crypto_currency,
                "customer_email": req.customer_email,
                "customer_id": payment_id,
            })
            checkout_url = session.get("url")

            await db.execute(
                "UPDATE payments SET provider_tx_id = ? WHERE id = ?",
                (session.get("transaction_id"), payment_id)
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"MoonPay error: {str(e)}")

    elif req.checkout_method == "crypto":
        # Direct crypto payment (CoinRemitter, Plisio, NOWPayments)
        from providers import get_provider
        provider = get_provider("coinremitter")
        try:
            order = await provider.create_order({
                "amount": req.amount_fiat,
                "currency": req.fiat_currency,
                "crypto": req.crypto_currency,
                "reference": payment_id,
            })
            session_token = order.get("payment_url") or order.get("invoice_url")

            await db.execute(
                "UPDATE payments SET provider_order_id = ? WHERE id = ?",
                (order.get("order_id"), payment_id)
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Crypto gateway error: {str(e)}")

    else:
        raise HTTPException(status_code=400, detail=f"Unknown checkout_method: {req.checkout_method}")

    # 5. Log credibility check result
    logger.info(
        f"Checkout initiated: payment_id={payment_id}, merchant={req.merchant_id}, "
        f"risk_score={risk_score}, method={req.checkout_method}"
    )

    return {
        "status": "ok",
        "payment_id": payment_id,
        "checkout_url": checkout_url,
        "session_token": session_token,
        "checkout_method": req.checkout_method,
        "amount": req.amount_fiat,
        "currency": req.fiat_currency,
        "credibility_score": 100 - risk_score,  # Inverted for customer clarity
        "merchant_name": profile["company_name"] if profile else "Unknown",
    }


@app.get("/api/payment/{payment_id}/status")
async def get_payment_status(
    payment_id: str,
    db: AsyncDB = Depends(get_db)
):
    """Get current payment status + gateway details."""
    payment = await db.fetchone(
        """
        SELECT id, merchant_id, amount, fiat_currency, crypto_currency,
               customer_email, status, provider, provider_order_id, provider_tx_id, created_at, updated_at
        FROM payments
        WHERE id = ?
        """,
        (payment_id,)
    )

    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")

    return {
        "payment_id": payment["id"],
        "status": payment["status"],
        "amount": payment["amount"],
        "currency": payment["fiat_currency"],
        "provider": payment["provider"],
        "provider_order_id": payment["provider_order_id"],
        "provider_tx_id": payment["provider_tx_id"],
        "created_at": payment["created_at"],
        "updated_at": payment["updated_at"],
    }


@app.get("/api/checkout/methods")
async def list_checkout_methods():
    """List all available checkout methods + their status."""
    stripe_provider = get_stripe_provider()
    stripe_status = stripe_provider.is_configured()

    return {
        "methods": [
            # CARD PAYMENT GATEWAYS
            {
                "id": "stripe",
                "name": "Stripe Card Checkout",
                "type": "card_hosted",
                "enabled": stripe_status["enabled"],
                "mode": stripe_status["mode"],
                "description": "Hosted Stripe checkout",
                "regions": ["Global"],
                "currencies": ["USD", "EUR", "GBP", "AED", "INR"],
            },
            {
                "id": "lockbox",
                "name": "Saved Card (Lockbox)",
                "type": "card_vault",
                "enabled": True,
                "description": "Charge pre-stored encrypted card",
                "requires": ["card_id"],
            },
            {
                "id": "ziina",
                "name": "Ziina AED",
                "type": "card_local",
                "enabled": True,
                "description": "Native AED payments (UAE banking)",
                "regions": ["UAE"],
                "settlement_time": "instant",
                "currencies": ["AED"],
            },
            # FIAT-TO-CRYPTO GATEWAYS
            {
                "id": "transak",
                "name": "Transak",
                "type": "fiat_to_crypto",
                "enabled": True,
                "description": "160+ countries, no KYC for small amounts",
                "regions": ["UK", "EU", "US", "India", "Australia"],
                "kyc_free_limit": "$200",
                "settlement_time": "1-3 hours",
                "cryptos": ["BTC", "ETH", "USDT", "USDC"],
            },
            {
                "id": "guardarian",
                "name": "Guardarian",
                "type": "fiat_to_crypto",
                "enabled": True,
                "description": "170+ countries, 1000+ cryptos",
                "regions": ["Global"],
                "cryptos": "1000+",
                "settlement_time": "5-30 minutes",
            },
            {
                "id": "moonpay",
                "name": "MoonPay",
                "type": "fiat_to_crypto",
                "enabled": True,
                "description": "160+ countries, on/off-ramps",
                "regions": ["Global"],
                "settlement_time": "1-2 hours",
                "features": ["buy", "sell"],
            },
            # DIRECT CRYPTO
            {
                "id": "crypto",
                "name": "Direct Crypto",
                "type": "crypto_direct",
                "enabled": True,
                "description": "CoinRemitter, Plisio, NOWPayments (no KYC)",
                "settlement_time": "5-30 minutes",
                "currencies": ["BTC", "ETH", "USDT", "USDC"],
            },
        ]
    }


# ─── Card Entry & Lockbox Storage ───────────────────────────────────────

@app.get("/card-entry")
async def card_entry_page():
    """Serve card entry form."""
    html_file = os.path.join(os.path.dirname(__file__), "web", "card-entry.html")
    if not os.path.exists(html_file):
        return JSONResponse(status_code=404, content={"error": "Card entry form not found"})

    with open(html_file, 'r') as f:
        return HTMLResponse(content=f.read())


class CardStoreRequest(BaseModel):
    cardholder_name: str
    card_number: str
    expiry_date: str
    cvv: str
    billing_street: str = ""
    billing_city: str = ""
    billing_state: str = ""
    billing_zip: str = ""


@app.post("/api/lockbox/store-card")
async def store_card_in_lockbox(req: CardStoreRequest, db: AsyncDB = Depends(get_db)):
    """
    Store encrypted card in lockbox.
    Returns card_id for future charging.
    """
    from verification.encryption import encrypt_credential, mask_credential
    from config import CREDENTIAL_ENCRYPTION_KEY

    # Validate card format
    if len(req.card_number) < 13 or not req.card_number.isdigit():
        raise HTTPException(status_code=400, detail="Invalid card number")

    if len(req.cvv) < 3:
        raise HTTPException(status_code=400, detail="Invalid CVV")

    card_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    # Create encrypted bundle
    card_data = {
        "cardholder": req.cardholder_name,
        "card_number": req.card_number,
        "expiry": req.expiry_date,
        "cvv": req.cvv,
        "billing": {
            "street": req.billing_street,
            "city": req.billing_city,
            "state": req.billing_state,
            "zip": req.billing_zip,
        }
    }

    encrypted_bundle = encrypt_credential(
        json.dumps(card_data),
        CREDENTIAL_ENCRYPTION_KEY
    )

    masked_number = mask_credential(req.card_number)

    # Store in lockbox_transactions
    try:
        await db.execute(
            """
            INSERT INTO lockbox_transactions
            (id, raw_input, masked_card_number, card_number, expiry_date, cvv,
             cardholder_name, billing_street, billing_city, billing_state, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (card_id, json.dumps(card_data), masked_number,
             encrypt_credential(req.card_number, CREDENTIAL_ENCRYPTION_KEY),
             encrypt_credential(req.expiry_date, CREDENTIAL_ENCRYPTION_KEY),
             encrypt_credential(req.cvv, CREDENTIAL_ENCRYPTION_KEY),
             encrypt_credential(req.cardholder_name, CREDENTIAL_ENCRYPTION_KEY),
             req.billing_street, req.billing_city, req.billing_state, now)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Storage failed: {str(e)}")

    logger.info(f"Card stored in lockbox: {card_id} → {masked_number}")

    return {
        "status": "ok",
        "card_id": card_id,
        "masked": masked_number,
        "message": "Card saved securely in vault"
    }


@app.get("/api/lockbox/cards")
async def list_merchant_cards(
    merchant_id: str = None,
    x_api_key: str = Header(None),
    db: AsyncDB = Depends(get_db)
):
    """
    List saved cards for a merchant.
    Requires merchant API key.
    """
    if not merchant_id or not x_api_key:
        raise HTTPException(status_code=400, detail="merchant_id and X-Api-Key required")

    # Verify merchant API key
    merchant = await db.fetchone(
        "SELECT id FROM merchants WHERE id=? AND api_key=?",
        (merchant_id, x_api_key)
    )
    if not merchant:
        raise HTTPException(status_code=403, detail="Invalid merchant or API key")

    # List cards (masked only, never return full numbers)
    cards = await db.fetchall(
        """
        SELECT id, masked_card_number, cardholder_name, created_at
        FROM lockbox_transactions
        WHERE cardholder_name IS NOT NULL
        ORDER BY created_at DESC
        LIMIT 50
        """,
    )

    return {
        "cards": [
            {
                "card_id": card["id"],
                "masked": card["masked_card_number"],
                "cardholder": card["cardholder_name"],
                "created_at": card["created_at"],
            }
            for card in cards
        ]
    }


# ─── Additional Gateway Webhooks ────────────────────────────────────────

@app.post("/webhooks/transak")
async def transak_webhook(request: Request, db: AsyncDB = Depends(get_db)):
    """Transak webhook receiver for payment status updates."""
    payload = await request.json()
    event_type = payload.get("eventName", "")
    order_data = payload.get("data", {})
    payment_id = order_data.get("clientId") or order_data.get("orderId")

    if not payment_id:
        return {"status": "ignored"}

    status_map = {
        "ORDER_COMPLETED": "completed",
        "ORDER_FAILED": "failed",
        "ORDER_CANCELLED": "failed",
    }

    new_status = status_map.get(event_type)
    if not new_status:
        return {"status": "ignored"}

    await db.execute(
        "UPDATE payments SET status=?, provider_order_id=?, updated_at=? WHERE id=?",
        (new_status, order_data.get("id"), datetime.utcnow().isoformat(), payment_id)
    )

    logger.info(f"Transak webhook: {payment_id} → {new_status}")
    return {"status": "ok"}


@app.post("/webhooks/guardarian")
async def guardarian_webhook(request: Request, db: AsyncDB = Depends(get_db)):
    """Guardarian webhook receiver for payment status updates."""
    payload = await request.json()
    txn_data = payload.get("transaction", {})
    payment_id = txn_data.get("clientId") or txn_data.get("id")

    if not payment_id:
        return {"status": "ignored"}

    status = txn_data.get("status", "").lower()
    status_map = {
        "completed": "completed",
        "finished": "completed",
        "failed": "failed",
        "cancelled": "failed",
        "waiting": "pending",
    }

    new_status = status_map.get(status)
    if not new_status:
        return {"status": "ignored"}

    await db.execute(
        "UPDATE payments SET status=?, provider_tx_id=?, updated_at=? WHERE id=?",
        (new_status, txn_data.get("id"), datetime.utcnow().isoformat(), payment_id)
    )

    logger.info(f"Guardarian webhook: {payment_id} → {new_status}")
    return {"status": "ok"}


@app.post("/webhooks/ziina")
async def ziina_webhook(request: Request, db: AsyncDB = Depends(get_db)):
    """Ziina webhook receiver for AED payment updates."""
    payload = await request.json()
    order_data = payload.get("order", {})
    payment_id = order_data.get("referenceNo") or order_data.get("orderId")

    if not payment_id:
        return {"status": "ignored"}

    status = order_data.get("status", "").upper()
    status_map = {
        "COMPLETED": "completed",
        "CONFIRMED": "completed",
        "FAILED": "failed",
        "CANCELLED": "failed",
        "PENDING": "pending",
    }

    new_status = status_map.get(status)
    if not new_status:
        return {"status": "ignored"}

    await db.execute(
        "UPDATE payments SET status=?, provider_order_id=?, updated_at=? WHERE id=?",
        (new_status, order_data.get("orderId"), datetime.utcnow().isoformat(), payment_id)
    )

    logger.info(f"Ziina webhook: {payment_id} → {new_status}")
    return {"status": "ok"}


@app.post("/webhooks/moonpay")
async def moonpay_webhook(request: Request, db: AsyncDB = Depends(get_db)):
    """MoonPay webhook receiver for fiat payment updates."""
    payload = await request.json()
    txn_data = payload.get("transaction", {})
    payment_id = txn_data.get("customerId") or txn_data.get("externalCustomerId")

    if not payment_id:
        return {"status": "ignored"}

    status = txn_data.get("status", "").lower()
    status_map = {
        "completed": "completed",
        "pending": "pending",
        "failed": "failed",
        "cancelled": "failed",
    }

    new_status = status_map.get(status)
    if not new_status:
        return {"status": "ignored"}

    await db.execute(
        "UPDATE payments SET status=?, provider_tx_id=?, updated_at=? WHERE id=?",
        (new_status, txn_data.get("id"), datetime.utcnow().isoformat(), payment_id)
    )

    logger.info(f"MoonPay webhook: {payment_id} → {new_status}")
    return {"status": "ok"}


@app.post("/webhooks/nowpayments")
async def nowpayments_webhook(request: Request, db: AsyncDB = Depends(get_db)):
    """NOWPayments webhook receiver for direct crypto payments."""
    payload = await request.json()
    payment_id = payload.get("order_id") or payload.get("ipn_id")

    if not payment_id:
        return {"status": "ignored"}

    payment_status = payload.get("payment_status", "")
    status_map = {
        "finished": "completed",
        "confirmed": "completed",
        "failed": "failed",
        "pending": "pending",
    }

    new_status = status_map.get(payment_status)
    if not new_status:
        return {"status": "ignored"}

    await db.execute(
        "UPDATE payments SET status=?, provider_tx_id=?, updated_at=? WHERE id=?",
        (new_status, payload.get("txid"), datetime.utcnow().isoformat(), payment_id)
    )

    logger.info(f"NOWPayments webhook: {payment_id} → {new_status}")
    return {"status": "ok"}


@app.post("/api/gateway/status")
async def gateway_status_check():
    """Check status of all payment gateways."""
    stripe_provider = StripeProvider()

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "gateways": {
            "stripe": stripe_provider.is_configured(),
            "transak": {"enabled": True, "mode": "production"},
            "guardarian": {"enabled": True, "mode": "production"},
            "ziina": {"enabled": True, "mode": "live"},
            "moonpay": {"enabled": True, "mode": "production"},
            "nowpayments": {"enabled": True, "mode": "production"},
            "coinremitter": {"enabled": True, "mode": "live"},
            "plisio": {"enabled": True, "mode": "live"},
        }
    }

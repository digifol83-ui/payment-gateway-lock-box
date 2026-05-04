from fastapi import FastAPI, Header, HTTPException, Depends
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

    if fiat_amount <= 0:
        raise HTTPException(status_code=400, detail="fiat_amount must be > 0")

    payment_id = str(uuid.uuid4())
    now = datetime.utcnow()

    try:
        await db.execute(
            """
            INSERT INTO payments
            (payment_id, merchant_id, fiat_amount, fiat_currency, crypto_ticker, provider_id, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (payment_id, None, fiat_amount, fiat_currency, crypto_ticker, provider_id, "pending", now, now),
        )
        await db.commit()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"database_error: {e}")

    return {
        "payment_id": payment_id,
        "provider_id": provider_id,
        "fiat_amount": fiat_amount,
        "fiat_currency": fiat_currency,
        "crypto_ticker": crypto_ticker,
        "customer_email": customer_email,
        "status": "pending",
    }


@app.post("/api/public/payments/{payment_id}/start/{provider_id}")
async def public_start_provider_checkout(payment_id: str, provider_id: str, db: AsyncDB = Depends(get_db)):
    """
    Return a provider-hosted checkout redirect URL.
    Card entry happens on the provider page, not on this server.
    """
    provider_id = (provider_id or "").strip().lower()

    row = await db.fetchone(
        "SELECT payment_id, fiat_amount, fiat_currency, crypto_ticker FROM payments WHERE payment_id = ?",
        (payment_id,),
    )
    if not row:
        raise HTTPException(status_code=404, detail="payment_not_found")

    pid = row["payment_id"]
    fiat_amount = row["fiat_amount"]
    fiat_currency = row["fiat_currency"]
    crypto_ticker = row["crypto_ticker"]

    if provider_id == "stripe":
        stripe = StripeProvider()
        redirect_url = await stripe.create_checkout_session(
            {
                "id": pid,
                "amount": float(fiat_amount),
                "fiat_currency": fiat_currency,
                "crypto_currency": crypto_ticker,
                "description": f"BeastPay · {crypto_ticker}",
            }
        )
        return {"payment_id": pid, "provider_id": provider_id, "redirect_url": redirect_url}

    if provider_id == "transak":
        return {"payment_id": pid, "provider_id": provider_id, "redirect_url": "/static/checkout-transak.html"}

    if provider_id == "moonpay":
        return {"payment_id": pid, "provider_id": provider_id, "redirect_url": "/static/pay.html"}

    if provider_id == "paypal":
        raise HTTPException(status_code=501, detail="paypal_not_implemented_yet")

    raise HTTPException(status_code=400, detail="unsupported_provider")

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

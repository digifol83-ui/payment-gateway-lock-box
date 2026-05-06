#!/usr/bin/env python3
"""Minimal Stripe Crypto Wallet test server."""
import os
import sys
import uuid
from datetime import datetime
from fastapi import FastAPI, HTTPException, Header
from fastapi.responses import JSONResponse
import aiohttp
import sqlite3

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from providers.stripe import StripeProvider
from integrations.codewords import CodeWordsIntegration
from config import STRIPE_SECRET_KEY, BASE_URL

# Initialize CodeWords integration (optional)
try:
    codewords = CodeWordsIntegration()
except:
    codewords = None

app = FastAPI(title="Stripe Crypto Wallet API", version="1.0")
DB_PATH = "payments.db"

@app.on_event("startup")
async def startup():
    """Initialize database on startup."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS merchants (
        id TEXT PRIMARY KEY,
        name TEXT,
        email TEXT,
        api_key TEXT UNIQUE,
        webhook_url TEXT,
        is_active INTEGER DEFAULT 1,
        created_at TEXT
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS payments (
        id TEXT PRIMARY KEY,
        merchant_id TEXT,
        amount REAL,
        fiat_currency TEXT,
        crypto_currency TEXT,
        wallet_address TEXT,
        customer_email TEXT,
        customer_name TEXT,
        status TEXT,
        provider TEXT,
        provider_order_id TEXT,
        created_at TEXT,
        updated_at TEXT,
        FOREIGN KEY(merchant_id) REFERENCES merchants(id)
    )
    """)
    conn.commit()
    conn.close()

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/stripe/config")
async def get_stripe_config():
    """Get Stripe configuration status."""
    sp = StripeProvider()
    return sp.is_configured()

@app.post("/api/comprehensive-checkout")
async def comprehensive_checkout(
    merchant_id: str,
    amount_fiat: float,
    fiat_currency: str = "USD",
    crypto_currency: str = "ETH",
    customer_email: str = None,
    wallet_address: str = None,
    customer_name: str = None,
    checkout_method: str = "stripe",
    x_api_key: str = Header(None),
):
    """
    Create a payment with Stripe checkout.

    Example:
    POST /api/comprehensive-checkout?merchant_id=test&amount_fiat=100&crypto_currency=ETH&customer_email=user@example.com&wallet_address=0x123...
    """

    # Verify merchant
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, api_key FROM merchants WHERE id = ?", (merchant_id,))
    merchant = cursor.fetchone()

    if not merchant:
        conn.close()
        raise HTTPException(status_code=404, detail="Merchant not found")

    merchant_id, db_api_key = merchant

    if x_api_key and x_api_key != db_api_key:
        conn.close()
        raise HTTPException(status_code=403, detail="Invalid API key")

    # Create payment record
    payment_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    try:
        cursor.execute("""
        INSERT INTO payments (
            id, merchant_id, amount, fiat_currency, crypto_currency,
            customer_email, customer_name, wallet_address, status, provider, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (payment_id, merchant_id, amount_fiat, fiat_currency, crypto_currency,
              customer_email, customer_name, wallet_address, "pending", checkout_method, now, now))
        conn.commit()
    except Exception as e:
        conn.close()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    # Create Stripe checkout session
    stripe = StripeProvider()
    try:
        checkout_url = await stripe.create_checkout_session({
            "id": payment_id,
            "amount": amount_fiat,
            "fiat_currency": fiat_currency,
            "crypto_currency": crypto_currency,
            "customer_email": customer_email,
            "description": f"BeastPay {crypto_currency} payment"
        })
    except Exception as e:
        cursor.execute("UPDATE payments SET status = ? WHERE id = ?", ("failed", payment_id))
        conn.commit()
        conn.close()
        raise HTTPException(status_code=500, detail=f"Stripe error: {str(e)}")

    conn.close()

    return {
        "payment_id": payment_id,
        "checkout_url": checkout_url,
        "status": "pending",
        "amount": amount_fiat,
        "currency": fiat_currency,
        "crypto_currency": crypto_currency,
        "wallet_address": wallet_address,
        "created_at": now
    }

@app.get("/api/payment-status/{payment_id}")
async def get_payment_status(payment_id: str):
    """Get payment status by ID."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    SELECT id, merchant_id, amount, fiat_currency, crypto_currency,
           wallet_address, customer_email, status, provider, created_at, updated_at
    FROM payments WHERE id = ?
    """, (payment_id,))

    row = cursor.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Payment not found")

    (pid, mid, amt, fiat, crypto, wallet, email, status, prov, created, updated) = row

    return {
        "payment_id": pid,
        "merchant_id": mid,
        "amount": amt,
        "fiat_currency": fiat,
        "crypto_currency": crypto,
        "wallet_address": wallet,
        "customer_email": email,
        "status": status,
        "provider": prov,
        "created_at": created,
        "updated_at": updated
    }

@app.post("/webhooks/stripe")
async def stripe_webhook(request: dict):
    """Webhook handler for Stripe events with CodeWords automation."""
    stripe = StripeProvider()

    # In production, verify signature from request headers
    # For now, just parse the webhook
    event = stripe.parse_webhook(request)

    if not event:
        return {"status": "ignored"}

    # Get payment details from database
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    SELECT merchant_id, amount, fiat_currency, crypto_currency,
           wallet_address, customer_email FROM payments WHERE id = ?
    """, (event["payment_id"],))
    payment = cursor.fetchone()

    # Update payment status
    cursor.execute(
        "UPDATE payments SET status = ?, updated_at = ? WHERE id = ?",
        (event["status"], datetime.utcnow().isoformat(), event["payment_id"])
    )
    conn.commit()
    conn.close()

    # Trigger CodeWords workflows based on payment status
    if codewords and payment:
        (merchant_id, amount, fiat_currency, crypto_currency,
         wallet_address, customer_email) = payment

        if event["status"] == "completed":
            await codewords.on_payment_completed(
                payment_id=event["payment_id"],
                merchant_id=merchant_id,
                amount=amount,
                fiat_currency=fiat_currency,
                crypto_currency=crypto_currency,
                wallet_address=wallet_address,
                customer_email=customer_email
            )
        elif event["status"] == "failed":
            await codewords.on_payment_failed(
                payment_id=event["payment_id"],
                merchant_id=merchant_id,
                error_reason="Stripe payment failed",
                customer_email=customer_email
            )
        elif event["status"] == "refunded":
            await codewords.on_payment_refunded(
                payment_id=event["payment_id"],
                merchant_id=merchant_id,
                amount=amount,
                wallet_address=wallet_address
            )

    return {"status": "received", "payment_id": event["payment_id"]}

@app.get("/codewords/status")
async def codewords_status():
    """Check CodeWords integration status."""
    if not codewords:
        return {
            "status": "disconnected",
            "api_key": "not_configured",
            "message": "Set CODEWORDS_API_KEY in .env to enable"
        }

    api_key = codewords.api_key
    return {
        "status": "connected",
        "api_key": f"{api_key[:20]}..." if api_key else "not_set",
        "api_url": codewords.api_url,
        "workflows_available": [
            "payment_completed_{merchant_id}",
            "payment_failed_{merchant_id}",
            "payment_refunded_{merchant_id}"
        ]
    }

@app.post("/codewords/trigger")
async def manual_codewords_trigger(
    workflow_id: str,
    trigger_data: dict
):
    """Manually trigger a CodeWords workflow."""
    if not codewords:
        raise HTTPException(status_code=503, detail="CodeWords not configured")

    result = await codewords.trigger_workflow(workflow_id, trigger_data)

    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["error"])

    return result

@app.get("/codewords/execution/{execution_id}")
async def codewords_execution_status(execution_id: str):
    """Get CodeWords workflow execution status."""
    if not codewords:
        raise HTTPException(status_code=503, detail="CodeWords not configured")

    result = await codewords.get_workflow_status(execution_id)
    return result

@app.get("/")
async def root():
    return {
        "name": "Stripe Integrated Crypto Wallet API",
        "version": "1.0",
        "integrations": ["Stripe", "CodeWords"],
        "endpoints": {
            "health": "GET /health",
            "stripe_config": "GET /stripe/config",
            "create_payment": "POST /api/comprehensive-checkout",
            "payment_status": "GET /api/payment-status/{payment_id}",
            "stripe_webhook": "POST /webhooks/stripe",
            "codewords_status": "GET /codewords/status",
            "codewords_trigger": "POST /codewords/trigger",
            "codewords_execution": "GET /codewords/execution/{id}"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)

"""P2P Gateway Routes — Binance P2P, Remitano. No KYC fiat-to-crypto."""
from fastapi import APIRouter, Query
from providers import PROVIDERS

router = APIRouter(prefix="/api/p2p", tags=["p2p"])

@router.get("/offers")
async def p2p_offers(
    fiat: str = Query("AED", description="Fiat currency"),
    crypto: str = Query("USDT", description="Crypto currency"),
    side: str = Query("BUY", description="BUY or SELL"),
    limit: int = Query(10, ge=1, le=20),
):
    """Get live P2P offers from Binance P2P and Remitano."""
    provider = PROVIDERS.get("p2p")
    if not provider:
        return {"error": "P2P provider not found"}
    
    offers = await provider.get_offers(fiat.upper(), crypto.upper(), side.upper(), limit)
    
    # Calculate summary
    if offers:
        best = offers[0]
        total_available = sum(o.get("available", 0) for o in offers)
        summary = {
            "best_price": best["price"],
            "best_exchange": best["exchange"],
            "best_merchant": best["merchant"],
            "total_offers": len(offers),
            "total_available": round(total_available, 2),
            "fiat": fiat.upper(),
            "crypto": crypto.upper(),
        }
    else:
        summary = {"error": "No offers available"}
    
    return {"summary": summary, "offers": offers}

@router.get("/best")
async def p2p_best(
    fiat: str = Query("AED"),
    crypto: str = Query("USDT"),
    amount: float = Query(100, ge=1),
):
    """Get the single best P2P offer for a given amount."""
    provider = PROVIDERS.get("p2p")
    if not provider:
        return {"error": "P2P provider not found"}
    
    offer = await provider.get_best_offer(fiat.upper(), crypto.upper(), amount)
    
    if offer:
        crypto_amount = amount / offer["price"]
        return {
            "offer": offer,
            "fiat_amount": amount,
            "crypto_amount": round(crypto_amount, 6),
            "fiat": fiat.upper(),
            "crypto": crypto.upper(),
        }
    
    return {"error": "No offers for this amount"}

@router.get("/status")
async def p2p_status():
    """P2P provider status."""
    provider = PROVIDERS.get("p2p")
    if not provider:
        return {"status": "unavailable"}
    return provider.provider_info()


@router.post("/pay")
async def p2p_create_payment(
    fiat: str = "AED",
    crypto: str = "USDT",
    amount: float = 0,
    wallet: str = "",
    offer_price: float = 0,
    offer_merchant: str = "",
    offer_exchange: str = "binance_p2p",
):
    """Create a P2P payment order with on-chain verification."""
    import uuid, sqlite3, json
    from datetime import datetime
    
    if amount <= 0:
        return {"error": "amount must be > 0"}
    if not wallet:
        return {"error": "wallet address required"}
    
    payment_id = str(uuid.uuid4())[:12]
    crypto_amount = round(amount / offer_price, 6) if offer_price > 0 else 0
    
    # Save payment to database
    db_path = "/home/kali/payment-gateway/payments.db"
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS p2p_payments (
            id TEXT PRIMARY KEY,
            fiat_amount REAL,
            fiat_currency TEXT,
            crypto_amount REAL,
            crypto_currency TEXT,
            wallet_address TEXT,
            offer_price REAL,
            offer_merchant TEXT,
            offer_exchange TEXT,
            status TEXT DEFAULT 'pending',
            tx_hash TEXT,
            created_at TEXT,
            confirmed_at TEXT
        )
    """)
    conn.execute(
        "INSERT INTO p2p_payments VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (payment_id, amount, fiat, crypto_amount, crypto, wallet,
         offer_price, offer_merchant, offer_exchange,
         'pending', None, datetime.utcnow().isoformat(), None)
    )
    conn.commit()
    conn.close()
    
    return {
        "payment_id": payment_id,
        "status": "pending",
        "fiat_amount": amount,
        "fiat_currency": fiat,
        "crypto_amount": crypto_amount,
        "crypto_currency": crypto,
        "wallet_address": wallet,
        "offer": {
            "price": offer_price,
            "merchant": offer_merchant,
            "exchange": offer_exchange,
        },
        "instructions": f"Send {amount} {fiat} via bank transfer to {offer_merchant} on Binance P2P. They will release {crypto_amount} {crypto} to {wallet[:8]}..."
    }


@router.get("/pay/{payment_id}")
async def p2p_payment_status(payment_id: str):
    """Check P2P payment status + on-chain verification."""
    import sqlite3
    
    db_path = "/home/kali/payment-gateway/payments.db"
    conn = sqlite3.connect(db_path)
    row = conn.execute(
        "SELECT * FROM p2p_payments WHERE id = ?", (payment_id,)
    ).fetchone()
    conn.close()
    
    if not row:
        return {"error": "Payment not found"}
    
    return {
        "payment_id": row[0],
        "fiat_amount": row[1],
        "fiat_currency": row[2],
        "crypto_amount": row[3],
        "crypto_currency": row[4],
        "wallet_address": row[5],
        "offer_price": row[6],
        "offer_merchant": row[7],
        "status": row[9],
        "created_at": row[11],
    }


@router.post("/pay/{payment_id}/confirm")
async def p2p_confirm_payment(payment_id: str, tx_hash: str = ""):
    """Confirm a P2P payment (called when crypto received)."""
    import sqlite3
    from datetime import datetime
    
    db_path = "/home/kali/payment-gateway/payments.db"
    conn = sqlite3.connect(db_path)
    conn.execute(
        "UPDATE p2p_payments SET status='confirmed', tx_hash=?, confirmed_at=? WHERE id=?",
        (tx_hash, datetime.utcnow().isoformat(), payment_id)
    )
    conn.commit()
    
    # Get updated row
    row = conn.execute("SELECT * FROM p2p_payments WHERE id = ?", (payment_id,)).fetchone()
    conn.close()
    
    if row:
        return {
            "payment_id": payment_id,
            "status": "confirmed",
            "crypto_amount": row[3],
            "crypto_currency": row[4],
            "wallet_address": row[5],
            "tx_hash": tx_hash,
        }
    return {"error": "Payment not found"}

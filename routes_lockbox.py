"""
Secure Lockbox Routes — encrypted card retrieval and transaction management
"""

from fastapi import APIRouter, HTTPException, Header
from pydantic import BaseModel
from datetime import datetime
import os
import json
from database import get_conn
from verification.encryption import decrypt_credential, mask_credential

router = APIRouter(prefix="/lockbox", tags=["lockbox"])


class LockboxRetrieveRequest(BaseModel):
    card_id: str
    encryption_key: str = None


class LockboxTransactionCreate(BaseModel):
    card_id: str
    amount_usd: float
    merchant_id: str
    provider: str = "stripe"
    metadata: dict = {}


def verify_admin_key(x_api_key: str = None) -> bool:
    """Verify admin API key."""
    admin_key = os.getenv("ADMIN_API_KEY")
    return admin_key and x_api_key == admin_key


@router.post("/retrieve")
def retrieve_card(request: LockboxRetrieveRequest, x_api_key: str = Header(None)):
    """Retrieve and decrypt a card from the lockbox."""
    if not verify_admin_key(x_api_key):
        raise HTTPException(status_code=403, detail="Invalid API key")

    encryption_key = request.encryption_key or os.getenv("CREDENTIAL_ENCRYPTION_KEY")
    if not encryption_key:
        raise HTTPException(status_code=400, detail="CREDENTIAL_ENCRYPTION_KEY not provided")

    try:
        with get_conn() as db:
            cursor = db.cursor()
            cursor.execute(
                "SELECT encrypted_data, masked_number, created_at FROM encrypted_cards WHERE id = ?",
                (request.card_id,)
            )
            row = cursor.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Card not found")

        encrypted_bundle, masked_number, created_at = row
        decrypted_json = decrypt_credential(encrypted_bundle, encryption_key)
        card_data = json.loads(decrypted_json)

        return {
            "status": "success",
            "card_id": request.card_id,
            "card_number": card_data.get("card_number"),
            "expiry": card_data.get("expiry"),
            "cvv": card_data.get("cvv"),
            "cardholder": card_data.get("cardholder"),
            "created_at": created_at,
            "masked": masked_number
        }
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Decryption failed")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.post("/transaction")
def create_lockbox_transaction(request: LockboxTransactionCreate, x_api_key: str = Header(None)):
    """Create a transaction using a locked card."""
    if not verify_admin_key(x_api_key):
        raise HTTPException(status_code=403, detail="Invalid API key")

    try:
        with get_conn() as db:
            cursor = db.cursor()

            # Verify card exists
            cursor.execute("SELECT id FROM encrypted_cards WHERE id = ?", (request.card_id,))
            if not cursor.fetchone():
                raise HTTPException(status_code=404, detail="Card not found")

            # Record transaction
            cursor.execute("""
                INSERT INTO lockbox_transactions
                (card_id, amount_usd, merchant_id, provider, metadata, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'))
            """, (
                request.card_id,
                request.amount_usd,
                request.merchant_id,
                request.provider,
                json.dumps(request.metadata),
                "pending"
            ))

            transaction_id = cursor.lastrowid
            db.commit()

            # Audit log
            cursor.execute("""
                INSERT INTO email_verification_logs
                (event_type, details, created_at)
                VALUES (?, ?, datetime('now'))
            """, (
                "lockbox_transaction",
                f"Transaction {transaction_id}: ${request.amount_usd} via {request.provider}"
            ))
            db.commit()

        return {
            "status": "success",
            "transaction_id": transaction_id,
            "amount_usd": request.amount_usd,
            "provider": request.provider,
            "created_at": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.get("/transactions/{transaction_id}")
def get_transaction_status(transaction_id: int, x_api_key: str = Header(None)):
    """Get status of a lockbox transaction."""
    if not verify_admin_key(x_api_key):
        raise HTTPException(status_code=403, detail="Invalid API key")

    try:
        with get_conn() as db:
            cursor = db.cursor()
            cursor.execute(
                "SELECT id, card_id, amount_usd, provider, status, created_at FROM lockbox_transactions WHERE id = ?",
                (transaction_id,)
            )
            row = cursor.fetchone()

        if not row:
            raise HTTPException(status_code=404, detail="Transaction not found")

        cols = ["id", "card_id", "amount_usd", "provider", "status", "created_at"]
        return dict(zip(cols, row))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.get("/status")
def lockbox_status(x_api_key: str = Header(None)):
    """Get lockbox overview and statistics."""
    if not verify_admin_key(x_api_key):
        raise HTTPException(status_code=403, detail="Invalid API key")

    try:
        with get_conn() as db:
            cursor = db.cursor()

            cursor.execute("SELECT COUNT(*) FROM encrypted_cards")
            card_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM lockbox_transactions")
            transaction_count = cursor.fetchone()[0]

            cursor.execute("SELECT status, COUNT(*) FROM lockbox_transactions GROUP BY status")
            status_breakdown = dict(cursor.fetchall()) or {}

        return {
            "status": "operational",
            "encrypted_cards": card_count,
            "transactions": transaction_count,
            "status_breakdown": status_breakdown,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

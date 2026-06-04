"""routes_cards.py — FastAPI Routes for Card Backend
=========================================================
HTTP API routes for the card details backend.
Integrates with brain-api via FastAPI router.

Endpoints:
  POST   /cards                    Create a new card entry
  GET    /cards                    List all card entries (masked)
  GET    /cards/{entry_id}         Get single card entry details
  DELETE /cards/{entry_id}         Delete a card entry
  POST   /cards/{entry_id}/pipeline  Push through full A1→A2→A3 pipeline
  POST   /cards/{entry_id}/step/{agent_id}  Push to single agent
  GET    /cards/summary            Pipeline summary
"""
from __future__ import annotations

import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'brain-api'))

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from card_backend import (
    create_card_entry,
    push_through_pipeline,
    push_agent_step,
    list_all_cards,
    get_card_entry,
    delete_card_entry,
    get_pipeline_summary,
    AGENT_PIPELINE,
)


router = APIRouter(prefix="/cards", tags=["Cards"])


# ═══════════════════════════════════════════════════════════════════════════════
# Request/Response Models
# ═══════════════════════════════════════════════════════════════════════════════

class CardCreateRequest(BaseModel):
    card_number: str = Field(..., description="Full card number (13-19 digits)")
    card_holder: str = Field(..., description="Name on the card")
    card_expiry: str = Field(..., description="Expiry in MM/YY format")
    card_cvv: str = Field(..., description="CVV (3-4 digits)")
    amount_aed: float = Field(0.0, description="Amount in AED")
    target_crypto: str = Field("USDT", description="Target cryptocurrency")
    target_network: str = Field("polygon", description="Target blockchain network")
    wallet_address: str = Field("", description="Destination wallet address")
    email: str = Field("", description="Contact email")
    notes: str = Field("", description="Additional notes")
    auto_push: bool = Field(True, description="Automatically push through agent pipeline")


class CardResponse(BaseModel):
    entry_id: str
    card_last4: str
    card_brand: str
    card_holder: str
    card_expiry: str
    amount_aed: float
    target_crypto: str
    target_network: str
    email: str
    is_valid: bool
    validation_errors: list[str]
    pipeline_status: dict[str, str]
    created_at: str
    completed_at: str | None = None


# ═══════════════════════════════════════════════════════════════════════════════
# Routes
# ═══════════════════════════════════════════════════════════════════════════════

@router.post("")
async def create_card(req: CardCreateRequest):
    """Create a new card entry and optionally push through the agent pipeline.
    
    The card flows through three agents:
      A1 — Validate card, detect brand, select gateways
      A2 — Execute checkout, monitor webhooks, verify settlement
      A3 — Audit, record, self-learn, detect anomalies
    
    Card details are validated: Luhn check, BIN detection, expiry check, CVV length.
    """
    result = create_card_entry(
        card_number=req.card_number,
        card_holder=req.card_holder,
        card_expiry=req.card_expiry,
        card_cvv=req.card_cvv,
        amount_aed=req.amount_aed,
        target_crypto=req.target_crypto,
        target_network=req.target_network,
        wallet_address=req.wallet_address,
        email=req.email,
        notes=req.notes,
        auto_push=req.auto_push,
    )
    return result


@router.get("")
async def list_cards():
    """List all card entries (masked — only last 4 digits shown)."""
    return {"cards": list_all_cards(), "count": len(list_all_cards())}


@router.get("/summary")
async def cards_summary():
    """Get pipeline summary statistics."""
    return get_pipeline_summary()


@router.get("/{entry_id}")
async def get_card(entry_id: str):
    """Get detailed info for a single card entry."""
    entry = get_card_entry(entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail=f"Card entry not found: {entry_id}")
    return entry


@router.delete("/{entry_id}")
async def delete_card(entry_id: str):
    """Delete a card entry."""
    result = delete_card_entry(entry_id)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/{entry_id}/pipeline")
async def push_card_pipeline(entry_id: str):
    """Push a card entry through the full A1→A2→A3 agent pipeline."""
    result = push_through_pipeline(entry_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@router.post("/{entry_id}/step/{agent_id}")
async def push_card_step(entry_id: str, agent_id: str):
    """Push a card entry to a single agent (A1, A2, or A3)."""
    agent_id = agent_id.upper()
    if agent_id not in AGENT_PIPELINE:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid agent: {agent_id}. Valid: {AGENT_PIPELINE}"
        )
    result = push_agent_step(entry_id, agent_id)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

"""server_transak.py — Standalone Transak-Only Production Checkout Server
=========================================================================
Minimal, zero-dependency-bloat server that runs ONLY the Transak checkout API.
No Stripe, no multi-provider, no dead code. Just Transak, healthy and fast.

Usage:
    cp .env.example .env   # fill TRANSAK_API_KEY, TRANSAK_SECRET/ACCESS_TOKEN, TRANSAK_ENV
    python3 server_transak.py

    # Or with env vars:
    TRANSAK_API_KEY=pk_live_xxx TRANSAK_SECRET=sk_live_xxx TRANSAK_ENV=PRODUCTION python3 server_transak.py

Health check:
    curl http://localhost:8000/transak/health

Create a checkout:
    curl -X POST http://localhost:8000/transak/session \
      -H 'Content-Type: application/json' \
      -d '{"wallet_address":"0x0582b74D10c853B52335542036e6CEA9B780849A","fiat_amount":500,"fiat_currency":"AED"}'

Open browser:
    http://localhost:8000/transak/buy
"""
from __future__ import annotations

import logging
import os
import sys

# Allow importing from brain-api (card_backend, project_store)
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'brain-api'))

from fastapi import FastAPI
from fastapi.responses import JSONResponse, HTMLResponse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("transak-server")

# Load .env if present
try:
    from dotenv import load_dotenv
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        load_dotenv(env_path)
        logger.info(f"Loaded .env from {env_path}")
except ImportError:
    pass

# Import the Transak router and card backend
from routes_transak_checkout import router as transak_router, is_production_configured
from routes_cards import router as cards_router

app = FastAPI(
    title="BeastPay Transak Checkout",
    version="1.0.0",
    description="Production-ready Transak-only fiat-to-crypto checkout API",
)

# Mount routers
app.include_router(transak_router)
app.include_router(cards_router)

# Redirect root to checkout
@app.get("/", response_class=HTMLResponse)
async def root():
    """Redirect to Mohammed Ferrin checkout."""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/checkout/ferrin")


@app.get("/checkout/ferrin", response_class=HTMLResponse)
async def checkout_ferrin():
    """Mohammed Ferrin's dedicated checkout page."""
    web_dir = os.path.join(os.path.dirname(__file__), "web")
    path = os.path.join(web_dir, "checkout-ferrin.html")
    if not os.path.exists(path):
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=404, content={"error": "Checkout page not found"})
    with open(path, encoding="utf-8") as f:
        return HTMLResponse(content=f.read())


@app.get("/health")
async def health():
    """Quick health check."""
    return {
        "status": "ok",
        "provider": "transak",
        "env": os.getenv("TRANSAK_ENV", "PRODUCTION"),
        "production_configured": is_production_configured(),
        "timestamp": __import__("datetime").datetime.now(__import__("datetime").timezone.utc).isoformat(),
    }


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8000"))
    host = os.getenv("HOST", "0.0.0.0")
    reload = os.getenv("RELOAD", "").lower() in ("1", "true", "yes")

    logger.info(f"Starting Transak-only server on {host}:{port}")
    logger.info(f"Env: {os.getenv('TRANSAK_ENV', 'PRODUCTION')}")
    logger.info(f"Production configured: {is_production_configured()}")
    logger.info(f"Health: http://{host}:{port}/transak/health")
    logger.info(f"Checkout: http://{host}:{port}/transak/buy")
    logger.info(f"Docs: http://{host}:{port}/docs")

    uvicorn.run(
        "server_transak:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info",
    )

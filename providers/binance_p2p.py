"""Binance P2P + Remitano Provider — No KYC fiat-to-crypto via P2P marketplace."""
from __future__ import annotations
import asyncio
import httpx
from typing import Any

BINANCE_P2P_URL = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
REMITANO_URL = "https://api.remitano.com/api/v1/offers"

FIAT_MAP = {
    "AED": "AE", "USD": "US", "EUR": "ES", "GBP": "GB",
    "INR": "IN", "NGN": "NG", "RUB": "RU", "UAH": "UA",
    "TRY": "TR", "BRL": "BR", "ARS": "AR", "VND": "VN",
}

class P2PProvider:
    """P2P marketplace — Binance P2P, Remitano, etc."""
    
    def __init__(self):
        self.name = "P2P Marketplace"
        self.type = "fiat-to-crypto"
        self.production = True
        self.status = "LIVE"
        self.sources = ["binance_p2p", "remitano"]
    
    async def get_offers(self, fiat: str = "AED", crypto: str = "USDT", side: str = "BUY", limit: int = 10) -> list[dict]:
        """Get live P2P offers from all sources."""
        tasks = []
        tasks.append(self._binance_offers(fiat, crypto, side, limit))
        tasks.append(self._remitano_offers(fiat, crypto, side, limit))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        offers = []
        for result in results:
            if isinstance(result, list):
                offers.extend(result)
            elif isinstance(result, Exception):
                pass  # Source down, skip
        
        # Sort by price (best first for BUY = lowest price)
        if side.upper() == "BUY":
            offers.sort(key=lambda o: o.get("price", 999999))
        else:
            offers.sort(key=lambda o: o.get("price", 0), reverse=True)
        
        return offers[:limit]
    
    async def _binance_offers(self, fiat: str, crypto: str, side: str, limit: int) -> list[dict]:
        """Fetch Binance P2P offers."""
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(BINANCE_P2P_URL, json={
                    "fiat": fiat,
                    "tradeType": side.upper(),
                    "asset": crypto.upper(),
                    "page": 1,
                    "rows": min(limit, 10),
                })
                data = resp.json()
                offers = []
                for adv in data.get("data", []):
                    a = adv["adv"]
                    advertiser = adv.get("advertiser", {})
                    offers.append({
                        "exchange": "binance_p2p",
                        "price": float(a.get("price", 0)),
                        "asset": a.get("asset", crypto.upper()),
                        "fiat": a.get("fiatUnit", fiat),
                        "available": float(a.get("surplusAmount", 0)),
                        "min_amount": float(a.get("minSingleTransAmount", 0)),
                        "max_amount": float(a.get("maxSingleTransAmount", 0)),
                        "merchant": advertiser.get("nickName", "?"),
                        "merchant_month_finish": advertiser.get("monthFinishRate", 0),
                        "merchant_month_order": advertiser.get("monthOrderCount", 0),
                        "payments": [p.get("payType", "BANK") for p in a.get("tradeMethods", [])],
                        "url": f"https://p2p.binance.com/en/advertiserDetail?advertiserNo={advertiser.get('userNo', '')}",
                    })
                return offers
        except Exception:
            return []
    
    async def _remitano_offers(self, fiat: str, crypto: str, side: str, limit: int) -> list[dict]:
        """Fetch Remitano P2P offers."""
        country = FIAT_MAP.get(fiat.upper(), "US")
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(REMITANO_URL, params={
                    "country": country,
                    "coin_currency": crypto.lower(),
                    "currency": fiat.lower(),
                    "offer_type": side.lower(),
                    "per": min(limit, 10),
                })
                data = resp.json()
                offers = []
                for o in data.get("offers", []):
                    offers.append({
                        "exchange": "remitano",
                        "price": float(o.get("price", 0)),
                        "asset": o.get("coin_currency", crypto).upper(),
                        "fiat": o.get("currency", fiat).upper(),
                        "min_amount": float(o.get("min_amount", 0)),
                        "max_amount": float(o.get("max_amount", 0)),
                        "merchant": o.get("user", {}).get("username", "?"),
                    })
                return offers
        except Exception:
            return []
    
    async def get_best_offer(self, fiat: str = "AED", crypto: str = "USDT", amount: float = 100) -> dict | None:
        """Get the best P2P offer for a given amount."""
        offers = await self.get_offers(fiat, crypto, "BUY", 20)
        for offer in offers:
            if offer["min_amount"] <= amount <= offer["max_amount"]:
                return offer
        # Fallback: return cheapest
        return offers[0] if offers else None
    
    def provider_info(self) -> dict:
        return {
            "id": "p2p",
            "name": self.name,
            "type": self.type,
            "production": self.production,
            "status": self.status,
            "kyc_type": "none",
            "no_kyc_limit_usd": 999999,
            "fee_pct": 0.0,
            "settlement_time": "10-30 min",
            "description": "P2P marketplace — Binance P2P, Remitano. Bank transfer to merchants. No KYC.",
            "sources": self.sources,
            "supported_fiats": ["AED", "USD", "EUR", "GBP", "INR", "NGN", "TRY"],
        }

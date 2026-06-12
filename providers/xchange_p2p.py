
"""Xchange P2P + Telegram P2P Providers."""
from __future__ import annotations
import httpx
from typing import Any

class XchangeProvider:
    """Xchange — Telegram-based USDT/INR P2P exchange."""
    def __init__(self):
        self.name = "Xchange P2P"
        self.type = "fiat-to-crypto"
        self.production = True
        self.status = "LIVE"
        self.register_url = "https://register.xchange-app.com/xchangeInvite/?iCode=38XD5FS9"
        self.telegram = ["@XchangeUinr", "@XchangeUinr01", "@XchangeUINR02"]
        self.channel = "https://t.me/Xchangechannelx"
        self.description = "Telegram P2P USDT/INR exchange. Clean funds, competitive rates."
    
    async def get_offer(self, fiat: str = "INR", amount: float = 1000):
        return {
            "exchange": "xchange",
            "type": "telegram_p2p",
            "fiat": fiat,
            "crypto": "USDT",
            "register_url": self.register_url,
            "telegram_support": self.telegram,
            "channel": self.channel,
            "instructions": f"1. Register at {self.register_url}\n2. Contact {self.telegram[0]} on Telegram\n3. Send {amount} {fiat} via UPI/Bank\n4. Receive USDT to your wallet"
        }
    
    def provider_info(self):
        return {
            "id": "xchange",
            "name": self.name,
            "type": self.type,
            "production": True,
            "status": "LIVE",
            "kyc_type": "none",
            "fee_pct": 0.0,
            "settlement_time": "5-15 min",
            "description": "Telegram P2P USDT/INR. Clean gaming funds. Manual exchange via Telegram.",
            "register_url": self.register_url,
            "telegram": self.telegram,
            "supported_fiats": ["INR"],
        }

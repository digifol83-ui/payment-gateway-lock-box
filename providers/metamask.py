"""
MetaMask (and Trust Wallet) direct-wallet provider.

This is NOT a fiat-to-crypto on-ramp — MetaMask itself does not expose a
partner API for that (the in-app Buy widget uses Transak/MoonPay under the
hood). What we do here is the real, working pattern for wallet-direct
crypto payments:

  1. User opens checkout page on mobile/desktop with MetaMask or Trust Wallet.
  2. Page builds a deep link to the wallet's send screen, pre-filled with
     merchant destination address + amount + token contract.
  3. User signs the transfer inside the wallet (we never see private keys).
  4. User pastes the resulting tx_hash back into the page (or it is captured
     via wallet RPC if the dApp is connected).
  5. Backend verifies the tx hash on-chain via a public RPC (no API keys).

All actual API endpoints + verification logic live in routes_wallet.py.
This file exists so the provider factory in providers/__init__.py keeps
working without referencing the old fake api.metamask.io endpoint.
"""
from datetime import datetime
from typing import Optional, Dict, Any


class MetaMaskProvider:
    """Lightweight wrapper. All real work is done by routes_wallet."""

    def __init__(
        self,
        api_key: str = "",
        secret_key: Optional[str] = None,
        webhook_secret: Optional[str] = None,
        environment: str = "production",
    ):
        # Kept for backwards compatibility with the factory signature.
        self.api_key = api_key or ""
        self.secret_key = secret_key or ""
        self.webhook_secret = webhook_secret or ""
        self.environment = environment
        self.name = "metamask"

    async def create_order(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Returns a quote that the frontend can use to build a deep link.
        Heavy lifting (live prices, merchant wallet, tx verification) is done
        via /api/wallet/quote and /api/payments/{id}/submit-tx.
        """
        from wallet_chains import CHAINS, resolve_asset
        chain = (payload.get("chain") or "bsc").lower()
        asset = (payload.get("crypto_currency") or "USDT").upper()
        chain_cfg = CHAINS.get(chain)
        asset_info = resolve_asset(chain, asset)
        if not chain_cfg or not asset_info:
            return {"error": f"unsupported {asset}@{chain}"}
        return {
            "order_id": payload.get("payment_id", ""),
            "status": "pending",
            "merchant_wallet": chain_cfg["merchant_wallet"],
            "chain": chain,
            "chain_id": chain_cfg["chain_id"],
            "asset": asset,
            "asset_contract": asset_info.get("contract"),
            "asset_decimals": asset_info["decimals"],
            "explorer": chain_cfg["explorer"],
            "created_at": datetime.utcnow().isoformat(),
        }

    async def get_status(self, order_id: str) -> Dict[str, Any]:
        """Status is computed from on-chain tx via /api/payments/{id}/verify."""
        return {"order_id": order_id, "status": "use_api_payments_verify"}

    async def handle_webhook(self, payload: Dict[str, Any], signature: str = "") -> Dict[str, Any]:
        """No third-party webhook — verification is pull-based via RPC."""
        return {"status": "noop", "note": "direct-wallet uses on-chain verification"}

    async def get_supported_currencies(self) -> Dict[str, Any]:
        from wallet_chains import CHAINS
        cryptos = set()
        for c in CHAINS.values():
            cryptos.add(c["native"])
            cryptos.update(c["tokens"].keys())
        return {"fiat": ["USD", "EUR", "GBP", "AED", "AUD", "CAD"], "crypto": sorted(cryptos)}

    async def close(self):
        return None


# Trust Wallet shares identical on-chain verification — alias the class so
# the factory can register both providers without duplicating code.
class TrustWalletProvider(MetaMaskProvider):
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self.name = "trustwallet"

"""
Wallet chain configuration for direct MetaMask / Trust Wallet payments.

Each chain has:
  - chain_id (EVM chain id)
  - rpc (public RPC URL, no auth required)
  - explorer (block explorer for tx links)
  - native (native asset symbol)
  - tokens (ERC-20 contracts for stablecoins)
  - merchant_wallet (destination address — override per chain via env)

Public RPCs picked to avoid auth keys (Infura/Alchemy). Override via env if
you want better rate limits:
  ETH_RPC, BSC_RPC, POLYGON_RPC, ARBITRUM_RPC, BASE_RPC
"""
import os

DEFAULT_MERCHANT_WALLET = "0x0582b74D10c853B52335542036e6CEA9B780849A"

CHAINS = {
    "ethereum": {
        "chain_id": 1,
        "rpc": os.getenv("ETH_RPC", "https://eth.llamarpc.com"),
        "explorer": "https://etherscan.io/tx/",
        "native": "ETH",
        "coingecko_native_id": "ethereum",
        "tokens": {
            "USDT": {"contract": "0xdAC17F958D2ee523a2206206994597C13D831ec7", "decimals": 6, "coingecko": "tether"},
            "USDC": {"contract": "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48", "decimals": 6, "coingecko": "usd-coin"},
            "DAI":  {"contract": "0x6B175474E89094C44Da98b954EedeAC495271d0F", "decimals": 18, "coingecko": "dai"},
        },
        "merchant_wallet": os.getenv("MERCHANT_WALLET_ETHEREUM", DEFAULT_MERCHANT_WALLET),
    },
    "bsc": {
        "chain_id": 56,
        "rpc": os.getenv("BSC_RPC", "https://bsc-dataseed.binance.org"),
        "explorer": "https://bscscan.com/tx/",
        "native": "BNB",
        "coingecko_native_id": "binancecoin",
        "tokens": {
            "USDT": {"contract": "0x55d398326f99059fF775485246999027B3197955", "decimals": 18, "coingecko": "tether"},
            "USDC": {"contract": "0x8AC76a51cc950d9822D68b83fE1Ad97B32Cd580d", "decimals": 18, "coingecko": "usd-coin"},
            "BUSD": {"contract": "0xe9e7CEA3DedcA5984780Bafc599bD69ADd087D56", "decimals": 18, "coingecko": "binance-usd"},
        },
        "merchant_wallet": os.getenv("MERCHANT_WALLET_BSC", DEFAULT_MERCHANT_WALLET),
    },
    "polygon": {
        "chain_id": 137,
        "rpc": os.getenv("POLYGON_RPC", "https://polygon-rpc.com"),
        "explorer": "https://polygonscan.com/tx/",
        "native": "MATIC",
        "coingecko_native_id": "matic-network",
        "tokens": {
            "USDT": {"contract": "0xc2132D05D31c914a87C6611C10748AEb04B58e8F", "decimals": 6, "coingecko": "tether"},
            "USDC": {"contract": "0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359", "decimals": 6, "coingecko": "usd-coin"},
        },
        "merchant_wallet": os.getenv("MERCHANT_WALLET_POLYGON", DEFAULT_MERCHANT_WALLET),
    },
    "arbitrum": {
        "chain_id": 42161,
        "rpc": os.getenv("ARBITRUM_RPC", "https://arb1.arbitrum.io/rpc"),
        "explorer": "https://arbiscan.io/tx/",
        "native": "ETH",
        "coingecko_native_id": "ethereum",
        "tokens": {
            "USDT": {"contract": "0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9", "decimals": 6, "coingecko": "tether"},
            "USDC": {"contract": "0xaf88d065e77c8cC2239327C5EDb3A432268e5831", "decimals": 6, "coingecko": "usd-coin"},
        },
        "merchant_wallet": os.getenv("MERCHANT_WALLET_ARBITRUM", DEFAULT_MERCHANT_WALLET),
    },
    "base": {
        "chain_id": 8453,
        "rpc": os.getenv("BASE_RPC", "https://mainnet.base.org"),
        "explorer": "https://basescan.org/tx/",
        "native": "ETH",
        "coingecko_native_id": "ethereum",
        "tokens": {
            "USDC": {"contract": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913", "decimals": 6, "coingecko": "usd-coin"},
        },
        "merchant_wallet": os.getenv("MERCHANT_WALLET_BASE", DEFAULT_MERCHANT_WALLET),
    },
}

# Reverse map: chain_id -> chain key
CHAIN_BY_ID = {c["chain_id"]: k for k, c in CHAINS.items()}


def get_chain(key_or_id):
    """Look up chain by name (e.g. 'bsc') or numeric id (56)."""
    if isinstance(key_or_id, int) or (isinstance(key_or_id, str) and key_or_id.isdigit()):
        cid = int(key_or_id)
        key = CHAIN_BY_ID.get(cid)
        return CHAINS.get(key) if key else None
    return CHAINS.get(str(key_or_id).lower())


def resolve_asset(chain_key: str, asset: str):
    """
    Return {kind: 'native'|'erc20', decimals, contract?, coingecko_id} for an
    asset on a given chain, or None if unsupported.
    """
    chain = CHAINS.get(chain_key)
    if not chain:
        return None
    asset = asset.upper()
    if asset == chain["native"]:
        return {
            "kind": "native",
            "decimals": 18,
            "coingecko_id": chain["coingecko_native_id"],
        }
    tok = chain["tokens"].get(asset)
    if not tok:
        return None
    return {
        "kind": "erc20",
        "decimals": tok["decimals"],
        "contract": tok["contract"],
        "coingecko_id": tok["coingecko"],
    }

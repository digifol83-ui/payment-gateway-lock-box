from .transak import TransakProvider
from .moonpay import MoonPayProvider
from .nowpayments import NowPaymentsProvider
from .stripe import StripeProvider
from .ziina import ZiinaProvider
from .guardarian import GuardarianProvider
from .coinremitter import CoinRemitterProvider
from .plisio import PlisioProvider
from .finchpay import FinchPayProvider
from .kast import KastPayProvider
from .charge import ChargeProvider
from .swapin import SwapinProvider
from .bleap import BleapProvider
from .metamask import MetaMaskProvider
import config as _cfg

PROVIDERS = {
    "transak":       TransakProvider(),
    "moonpay":       MoonPayProvider(),
    "nowpayments":   NowPaymentsProvider(),
    "stripe":        StripeProvider(),
    "ziina":         ZiinaProvider(),
    "guardarian":    GuardarianProvider(),
    "coinremitter":  CoinRemitterProvider(),
    "plisio":        PlisioProvider(),
    "finchpay":      FinchPayProvider(
        api_key=_cfg.FINCHPAY_API_KEY,
        secret_key=_cfg.FINCHPAY_SECRET_KEY,
        env=_cfg.FINCHPAY_ENV,
    ),
    "kast":          KastPayProvider(),
    "charge":        ChargeProvider(),
    "swapin":        SwapinProvider(),
    "bleap":         BleapProvider(),
    "metamask":      MetaMaskProvider(
        api_key=_cfg.METAMASK_API_KEY,
        secret_key=_cfg.METAMASK_SECRET,
        webhook_secret=_cfg.METAMASK_WEBHOOK_SECRET,
        environment=_cfg.METAMASK_ENV,
    ),
}


def _is_production(provider_id: str) -> bool:
    """Return True only when real keys AND production env are confirmed."""
    checks = {
        "transak":      lambda: bool(_cfg.TRANSAK_API_KEY and not _cfg.TRANSAK_API_KEY.startswith("YOUR_") and _cfg.TRANSAK_ENV.upper() == "PRODUCTION"),
        "moonpay":      lambda: bool(_cfg.MOONPAY_API_KEY and not _cfg.MOONPAY_API_KEY.startswith("pk_test_") and _cfg.MOONPAY_ENV.lower() == "production"),
        "nowpayments":  lambda: bool(_cfg.NOWPAYMENTS_API_KEY and not _cfg.NOWPAYMENTS_API_KEY.startswith("test_") and _cfg.NOWPAYMENTS_ENV.lower() == "production"),
        "stripe":       lambda: bool(_cfg.STRIPE_SECRET_KEY and _cfg.STRIPE_SECRET_KEY.startswith("sk_live_")),
        "ziina":        lambda: bool(_cfg.ZIINA_API_TOKEN and not _cfg.ZIINA_API_TOKEN.startswith("test_") and _cfg.ZIINA_ENV.lower() == "production"),
        "guardarian":   lambda: bool(_cfg.GUARDARIAN_API_KEY and not _cfg.GUARDARIAN_API_KEY.startswith("YOUR_") and not _cfg.GUARDARIAN_API_KEY.startswith("test_") and _cfg.GUARDARIAN_ENV.lower() == "production"),
        "coinremitter": lambda: bool(_cfg.COINREMITTER_API_KEY and _cfg.COINREMITTER_API_PASSWORD),
        "plisio":       lambda: bool(_cfg.PLISIO_API_KEY and not _cfg.PLISIO_API_KEY.startswith("test_")),
        "finchpay":     lambda: bool(_cfg.FINCHPAY_API_KEY and _cfg.FINCHPAY_SECRET_KEY),
        "kast":         lambda: bool(_cfg.KAST_API_KEY and not _cfg.KAST_API_KEY.startswith("test_") and _cfg.KAST_ENV.lower() == "production"),
        "charge":       lambda: bool(_cfg.CHARGE_API_KEY and _cfg.CHARGE_SECRET and not _cfg.CHARGE_API_KEY.startswith("test_") and _cfg.CHARGE_ENV.lower() == "production"),
        "swapin":       lambda: bool(_cfg.SWAPIN_API_KEY and _cfg.SWAPIN_SECRET and not _cfg.SWAPIN_API_KEY.startswith("test_") and _cfg.SWAPIN_ENV.lower() == "production"),
        "bleap":        lambda: bool(_cfg.BLEAP_API_KEY and _cfg.BLEAP_SECRET and not _cfg.BLEAP_API_KEY.startswith("test_") and _cfg.BLEAP_ENV.lower() == "production"),
        "metamask":     lambda: bool(_cfg.METAMASK_API_KEY and _cfg.METAMASK_SECRET and not _cfg.METAMASK_API_KEY.startswith("test_") and _cfg.METAMASK_ENV.lower() == "production"),
    }
    fn = checks.get(provider_id)
    return fn() if fn else False


# Provider metadata: type, KYC tier, OTP requirement, real-money limits
PROVIDER_METADATA = {
    "transak": {
        "name":               "Transak",
        "type":               "fiat-to-crypto",
        "description":        "Card/bank fiat-to-crypto — no KYC <$200, full KYC up to $50k",
        "non_otp":            True,
        "kyc_type":           "email_and_name",
        "supported_fiats":    ["USD", "EUR", "GBP", "AED", "INR"],
        "no_kyc_limit_usd":   200,
        "email_kyc_limit_usd": 750,
        "full_kyc_limit_usd": 50000,
        "min_tier":           1,
        "max_limit_usd":      50000,
        "fee_pct":            2.5,
        "settlement_time":    "30 min",
    },
    "moonpay": {
        "name":               "MoonPay",
        "type":               "fiat-to-crypto",
        "description":        "Email KYC ~$150/day; full KYC up to $10k/month",
        "non_otp":            True,
        "kyc_type":           "email_only",
        "supported_fiats":    ["USD", "EUR", "GBP", "AED"],
        "no_kyc_limit_usd":   0,
        "email_kyc_limit_usd": 150,
        "full_kyc_limit_usd": 10000,
        "min_tier":           0,
        "max_limit_usd":      10000,
        "fee_pct":            3.5,
        "settlement_time":    "30 min",
    },
    "guardarian": {
        "name":               "Guardarian",
        "type":               "fiat-to-crypto",
        "description":        "No KYC up to ~$700, 170+ countries",
        "non_otp":            True,
        "kyc_type":           "none",
        "supported_fiats":    ["USD", "EUR", "GBP", "AED"],
        "no_kyc_limit_usd":   700,
        "email_kyc_limit_usd": 700,
        "full_kyc_limit_usd": 50000,
        "min_tier":           0,
        "max_limit_usd":      50000,
        "fee_pct":            1.0,
        "settlement_time":    "20 min",
    },
    "finchpay": {
        "name":               "FinchPay",
        "type":               "fiat-to-crypto",
        "description":        "Email-only, 100+ fiats, Visa/Mastercard",
        "non_otp":            True,
        "kyc_type":           "email_only",
        "supported_fiats":    ["USD", "EUR", "GBP", "AED", "INR"],
        "no_kyc_limit_usd":   0,
        "email_kyc_limit_usd": 10000,
        "full_kyc_limit_usd": 10000,
        "min_tier":           0,
        "max_limit_usd":      10000,
        "fee_pct":            2.0,
        "settlement_time":    "15 min",
    },
    "nowpayments": {
        "name":               "NOWPayments",
        "type":               "crypto-only",
        "description":        "Crypto invoices, zero KYC, unlimited",
        "non_otp":            True,
        "kyc_type":           "none",
        "supported_fiats":    [],
        "no_kyc_limit_usd":   999999,
        "full_kyc_limit_usd": 999999,
        "min_tier":           0,
        "max_limit_usd":      999999,
        "fee_pct":            0.5,
        "settlement_time":    "10 min",
    },
    "plisio": {
        "name":               "Plisio",
        "type":               "crypto-only",
        "description":        "Non-custodial, zero KYC, 0.5% fee",
        "non_otp":            True,
        "kyc_type":           "none",
        "supported_fiats":    [],
        "no_kyc_limit_usd":   999999,
        "full_kyc_limit_usd": 999999,
        "min_tier":           0,
        "max_limit_usd":      999999,
        "fee_pct":            0.5,
        "settlement_time":    "10 min",
    },
    "coinremitter": {
        "name":               "CoinRemitter",
        "type":               "crypto-only",
        "description":        "Non-custodial, 0.23% fee, zero KYC",
        "non_otp":            True,
        "kyc_type":           "none",
        "supported_fiats":    [],
        "no_kyc_limit_usd":   999999,
        "full_kyc_limit_usd": 999999,
        "min_tier":           0,
        "max_limit_usd":      999999,
        "fee_pct":            0.23,
        "settlement_time":    "10 min",
    },
    "stripe": {
        "name":               "Stripe",
        "type":               "fiat-only",
        "description":        "Traditional card processor, T+2 settlement",
        "non_otp":            False,
        "kyc_type":           "requires_kyc",
        "supported_fiats":    ["USD", "EUR", "GBP"],
        "no_kyc_limit_usd":   0,
        "full_kyc_limit_usd": 999999,
        "min_tier":           3,
        "max_limit_usd":      999999,
        "fee_pct":            2.9,
        "settlement_time":    "T+2 days",
    },
    "ziina": {
        "name":               "Ziina",
        "type":               "fiat-only",
        "description":        "UAE-licensed, AED only, instant",
        "non_otp":            False,
        "kyc_type":           "requires_kyc",
        "supported_fiats":    ["AED"],
        "no_kyc_limit_usd":   0,
        "full_kyc_limit_usd": 50000,
        "min_tier":           2,
        "max_limit_usd":      50000,
        "fee_pct":            2.5,
        "settlement_time":    "T+1 day",
    },
    "kast": {
        "name":               "KAST Pay",
        "type":               "fiat-to-crypto",
        "description":        "Instant USDC settlement, zero-KYC under $500, USD banking",
        "non_otp":            True,
        "kyc_type":           "email_only",
        "supported_fiats":    ["USD", "EUR", "GBP"],
        "no_kyc_limit_usd":   500,
        "email_kyc_limit_usd": 25000,
        "full_kyc_limit_usd": 100000,
        "min_tier":           0,
        "max_limit_usd":      100000,
        "fee_pct":            1.5,
        "settlement_time":    "5 min",
    },
    "charge": {
        "name":               "Charge",
        "type":               "fiat-to-crypto",
        "description":        "Custom payment links, card-to-crypto, instant settlement",
        "non_otp":            True,
        "kyc_type":           "email_only",
        "supported_fiats":    ["USD", "EUR", "GBP", "AED"],
        "no_kyc_limit_usd":   300,
        "email_kyc_limit_usd": 10000,
        "full_kyc_limit_usd": 50000,
        "min_tier":           0,
        "max_limit_usd":      50000,
        "fee_pct":            2.0,
        "settlement_time":    "10 min",
    },
    "swapin": {
        "name":               "Swapin",
        "type":               "fiat-to-crypto",
        "description":        "Fiat-to-crypto bridges, multi-chain, zero-KYC up to $400",
        "non_otp":            True,
        "kyc_type":           "email_only",
        "supported_fiats":    ["USD", "EUR", "GBP"],
        "no_kyc_limit_usd":   400,
        "email_kyc_limit_usd": 15000,
        "full_kyc_limit_usd": 75000,
        "min_tier":           0,
        "max_limit_usd":      75000,
        "fee_pct":            1.8,
        "settlement_time":    "8 min",
    },
    "bleap": {
        "name":               "Bleap",
        "type":               "fiat-to-crypto",
        "description":        "Zero-spread USDC on-ramps, instant settlement, direct deposits",
        "non_otp":            True,
        "kyc_type":           "none",
        "supported_fiats":    ["USD", "EUR", "GBP"],
        "no_kyc_limit_usd":   600,
        "email_kyc_limit_usd": 600,
        "full_kyc_limit_usd": 100000,
        "min_tier":           0,
        "max_limit_usd":      100000,
        "fee_pct":            0.0,
        "settlement_time":    "3 min",
    },
    "metamask": {
        "name":               "MetaMask",
        "type":               "fiat-to-crypto",
        "description":        "Native MetaMask widget, 160+ countries, instant to wallet",
        "non_otp":            True,
        "kyc_type":           "none",
        "supported_fiats":    ["USD", "EUR", "GBP", "AUD", "CAD", "AED"],
        "no_kyc_limit_usd":   1000,
        "email_kyc_limit_usd": 1000,
        "full_kyc_limit_usd": 100000,
        "min_tier":           0,
        "max_limit_usd":      100000,
        "fee_pct":            2.5,
        "settlement_time":    "5-10 min",
    },
}


def get_provider(name: str):
    return PROVIDERS.get(name.lower())


def get_provider_metadata(name: str):
    return PROVIDER_METADATA.get(name.lower())


def list_non_otp_providers(fiat_currency: str = None, min_limit: float = None):
    """Filter providers: non-OTP, optionally by fiat currency and min transaction limit."""
    result = []
    for provider_id, meta in PROVIDER_METADATA.items():
        if not meta.get("non_otp"):
            continue
        if fiat_currency and fiat_currency not in meta.get("supported_fiats", []):
            continue
        if min_limit and meta.get("max_limit_usd", 0) < min_limit:
            continue
        prod = _is_production(provider_id)
        result.append({"id": provider_id, "production": prod, **meta})
    return result


def list_production_fiat_to_crypto(fiat_currency: str = None, amount_usd: float = None) -> list[dict]:
    """
    Return only 100% production fiat-to-crypto providers.
    Optionally filter by fiat currency and minimum transaction amount.
    Each entry includes which KYC tier applies at the given amount.
    """
    result = []
    kyc_free   = _cfg.KYC_FREE_LIMIT_USD
    kyc_sumsub = _cfg.KYC_SUMSUB_LIMIT

    for provider_id, meta in PROVIDER_METADATA.items():
        if meta.get("type") != "fiat-to-crypto":
            continue
        if not _is_production(provider_id):
            continue
        if fiat_currency and fiat_currency not in meta.get("supported_fiats", []):
            continue
        if amount_usd and meta.get("max_limit_usd", 0) < amount_usd:
            continue

        kyc_tier = "none"
        if amount_usd:
            if amount_usd >= kyc_sumsub:
                kyc_tier = "sumsub_full_kyc"
            elif amount_usd >= kyc_free:
                kyc_tier = "email_kyc"
            else:
                kyc_tier = "none"

        result.append({
            "id":         provider_id,
            "production": True,
            "kyc_tier":   kyc_tier,
            **meta,
        })

    # Sort: highest limit first
    result.sort(key=lambda x: -x.get("max_limit_usd", 0))
    return result


def provider_status_all() -> list[dict]:
    """Full status for every provider: production flag, type, limits, fees."""
    rows = []
    for pid, meta in PROVIDER_METADATA.items():
        prod = _is_production(pid)
        rows.append({
            "id":         pid,
            "production": prod,
            "status":     "LIVE" if prod else "SANDBOX/INACTIVE",
            **meta,
        })
    # LIVE providers first, then by type
    rows.sort(key=lambda r: (not r["production"], r["type"], r["id"]))
    return rows

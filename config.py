import os

# ─── Provider API Keys ──────────────────────────────────────────────────────
TRANSAK_API_KEY    = os.getenv("TRANSAK_API_KEY", "YOUR_TRANSAK_API_KEY")
TRANSAK_SECRET     = os.getenv("TRANSAK_SECRET",  "YOUR_TRANSAK_SECRET")
TRANSAK_ENV        = os.getenv("TRANSAK_ENV", "STAGING")   # STAGING | PRODUCTION

MOONPAY_API_KEY    = os.getenv("MOONPAY_API_KEY",  "YOUR_MOONPAY_API_KEY")
MOONPAY_SECRET     = os.getenv("MOONPAY_SECRET",   "YOUR_MOONPAY_SECRET")
MOONPAY_ENV        = os.getenv("MOONPAY_ENV", "sandbox")   # sandbox | production

# ─── Stripe ──────────────────────────────────────────────────────────────────
# dashboard.stripe.com → Developers → API Keys
STRIPE_SECRET_KEY      = os.getenv("STRIPE_SECRET_KEY",      "sk_placeholder")
STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY", "pk_placeholder")
STRIPE_WEBHOOK_SECRET  = os.getenv("STRIPE_WEBHOOK_SECRET",  "whsec_placeholder")
STRIPE_ENV             = os.getenv("STRIPE_ENV", "test")    # test | live
STRIPE_ENABLED         = bool(
    STRIPE_SECRET_KEY and not STRIPE_SECRET_KEY.startswith("sk_placeholder")
)

# ─── Server ─────────────────────────────────────────────────────────────────
HOST               = os.getenv("HOST", "0.0.0.0")
PORT               = int(os.getenv("PORT", "8000"))
BASE_URL           = os.getenv("BASE_URL", f"http://localhost:{PORT}")
ADMIN_API_KEY      = os.getenv("ADMIN_API_KEY", "admin-secret-change-me")

# ─── Supported Assets ───────────────────────────────────────────────────────
SUPPORTED_CRYPTOS = {
    "BTC":  "Bitcoin",
    "ETH":  "Ethereum",
    "USDT": "Tether (ERC-20)",
    "USDC": "USD Coin",
    "BNB":  "BNB",
    "SOL":  "Solana",
    "TRX":  "TRON",
    "MATIC":"Polygon",
}

SUPPORTED_FIATS = ["USD", "EUR", "GBP", "INR", "AED", "CAD", "AUD"]

DEFAULT_CRYPTO = "USDT"
DEFAULT_FIAT   = "USD"

# ─── Telegram Bot ────────────────────────────────────────────────────────────
# Get BOT_TOKEN from @BotFather, CHAT_ID from @userinfobot or your channel ID
TELEGRAM_BOT_TOKEN  = os.getenv("TELEGRAM_BOT_TOKEN",  "")   # e.g. 123456:ABCdef...
TELEGRAM_CHAT_ID    = os.getenv("TELEGRAM_CHAT_ID",    "")   # e.g. -100123456789 or @yourchannel
TELEGRAM_ENABLED    = bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)

# Notification toggles (set env vars to "0" to silence specific events)
TG_NOTIFY_NEW_PAYMENT   = os.getenv("TG_NOTIFY_NEW_PAYMENT",   "1") == "1"
TG_NOTIFY_COMPLETED     = os.getenv("TG_NOTIFY_COMPLETED",     "1") == "1"
TG_NOTIFY_FAILED        = os.getenv("TG_NOTIFY_FAILED",        "1") == "1"
TG_NOTIFY_NEW_LINK      = os.getenv("TG_NOTIFY_NEW_LINK",      "1") == "1"
TG_NOTIFY_DAILY_SUMMARY = os.getenv("TG_NOTIFY_DAILY_SUMMARY", "1") == "1"

# ─── WhatsApp Cloud API ──────────────────────────────────────────────────────
# Meta Business → WhatsApp → API Setup → get Phone Number ID + permanent token
WHATSAPP_TOKEN      = os.getenv("WHATSAPP_TOKEN",      "")   # permanent access token
WHATSAPP_PHONE_ID   = os.getenv("WHATSAPP_PHONE_ID",   "")   # Phone Number ID from Meta
WHATSAPP_TO         = os.getenv("WHATSAPP_TO",         "")   # recipient number e.g. 911234567890
WHATSAPP_ENABLED    = bool(WHATSAPP_TOKEN and WHATSAPP_PHONE_ID and WHATSAPP_TO)
WA_NOTIFY_NEW_PAYMENT   = os.getenv("WA_NOTIFY_NEW_PAYMENT",   "1") == "1"
WA_NOTIFY_COMPLETED     = os.getenv("WA_NOTIFY_COMPLETED",     "1") == "1"
WA_NOTIFY_FAILED        = os.getenv("WA_NOTIFY_FAILED",        "1") == "1"
WA_NOTIFY_NEW_LINK      = os.getenv("WA_NOTIFY_NEW_LINK",      "0") == "1"  # off by default

# ─── NOWPayments (crypto-native provider) ────────────────────────────────────
# Sign up at nowpayments.io → API Keys → create key
NOWPAYMENTS_API_KEY     = os.getenv("NOWPAYMENTS_API_KEY",    "")
NOWPAYMENTS_IPN_SECRET  = os.getenv("NOWPAYMENTS_IPN_SECRET", "")
NOWPAYMENTS_ENV         = os.getenv("NOWPAYMENTS_ENV", "sandbox")  # sandbox | production
NOWPAYMENTS_ENABLED     = bool(NOWPAYMENTS_API_KEY)

# ─── Sumsub KYC ──────────────────────────────────────────────────────────────
# dashboard.sumsub.com → Developers → App tokens
SUMSUB_APP_TOKEN    = os.getenv("SUMSUB_APP_TOKEN",  "")
SUMSUB_SECRET_KEY   = os.getenv("SUMSUB_SECRET_KEY", "")
SUMSUB_ENABLED      = bool(SUMSUB_APP_TOKEN and SUMSUB_SECRET_KEY)
SUMSUB_LEVEL_NAME   = os.getenv("SUMSUB_LEVEL_NAME", "basic-kyc-level")  # your flow name

# ─── Lockbox / Claude AI Parser ──────────────────────────────────────────────
# Get from console.anthropic.com → API Keys
ANTHROPIC_API_KEY   = os.getenv("ANTHROPIC_API_KEY", "")
LOCKBOX_ENABLED     = bool(ANTHROPIC_API_KEY)

# ─── Module 3: Merchant Verification ─────────────────────────────────────────
# OpenCorporates — opencorporates.com → Account → API Token
OPENCORPORATES_API_TOKEN    = os.getenv("OPENCORPORATES_API_TOKEN", "")
OPENCORPORATES_ENABLED      = bool(OPENCORPORATES_API_TOKEN)

# Credential encryption key — any strong random string (32+ chars recommended)
CREDENTIAL_ENCRYPTION_KEY   = os.getenv("CREDENTIAL_ENCRYPTION_KEY", "change-me-use-a-strong-random-key")

# IMAP email monitoring for OTP auto-extraction
IMAP_HOST       = os.getenv("IMAP_HOST", "")
IMAP_PORT       = int(os.getenv("IMAP_PORT", "993"))
IMAP_USER       = os.getenv("IMAP_USER", "")
IMAP_PASSWORD   = os.getenv("IMAP_PASSWORD", "")
IMAP_ENABLED    = bool(IMAP_HOST and IMAP_USER and IMAP_PASSWORD)

# ─── KYC Tiers ───────────────────────────────────────────────────────────────
# Below limit: Transak/MoonPay handle KYC internally (email only)
# Above limit: route through Sumsub for full identity verification
KYC_FREE_LIMIT_USD  = int(os.getenv("KYC_FREE_LIMIT_USD", "200"))
KYC_SUMSUB_LIMIT    = int(os.getenv("KYC_SUMSUB_LIMIT",   "500"))  # trigger Sumsub above this

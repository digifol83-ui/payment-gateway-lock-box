from pydantic_settings import BaseSettings
from typing import Optional
import os
import re

class Settings(BaseSettings):
    # Core
    DEBUG: bool = False
    ENVIRONMENT: str = "development"

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./payments.db"

    # Security
    ADMIN_API_KEY: str = "admin_key_dev"
    CREDENTIAL_ENCRYPTION_KEY: str = ""
    OPENCORPORATES_API_TOKEN: str = ""

    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"

    # Provider configs (optional for Phase 1)
    TRANSAK_API_KEY: str = ""
    TRANSAK_SECRET: str = ""
    TRANSAK_ACCESS_TOKEN: str = ""
    TRANSAK_ENV: str = "PRODUCTION"

    MOONPAY_API_KEY: str = ""
    MOONPAY_SECRET: str = ""
    MOONPAY_ENV: str = "sandbox"

    NOWPAYMENTS_API_KEY: str = ""
    NOWPAYMENTS_IPN_SECRET: str = ""
    NOWPAYMENTS_ENV: str = "sandbox"

    STRIPE_SECRET_KEY: str = ""
    STRIPE_PUBLISHABLE_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""
    STRIPE_ENV: str = ""
    STRIPE_STATUS: str = ""
    # Telegram Payments "provider token" (named like Stripe, but issued by @BotFather)
    STRIPE_PROVIDER_TOKEN: str = ""

    ZIINA_API_TOKEN: str = ""
    ZIINA_WEBHOOK_SECRET: str = ""
    ZIINA_ENV: str = "production"

    GUARDARIAN_API_KEY: str = ""
    GUARDARIAN_ENV: str = "production"

    COINREMITTER_API_KEY: str = ""
    COINREMITTER_API_PASSWORD: str = ""
    COINREMITTER_COIN: str = "BTC"
    COINREMITTER_ENV: str = "production"

    PLISIO_API_KEY: str = ""
    PLISIO_ENV: str = "production"

    FINCHPAY_API_KEY: str = ""
    FINCHPAY_SECRET_KEY: str = ""
    FINCHPAY_ENV: str = "sandbox"

    # New fast fiat-to-crypto providers
    KAST_API_KEY: str = ""
    KAST_SECRET: str = ""
    KAST_ENV: str = "production"

    CHARGE_API_KEY: str = ""
    CHARGE_SECRET: str = ""
    CHARGE_ENV: str = "production"

    SWAPIN_API_KEY: str = ""
    SWAPIN_SECRET: str = ""
    SWAPIN_ENV: str = "production"

    BLEAP_API_KEY: str = ""
    BLEAP_SECRET: str = ""
    BLEAP_ENV: str = "production"

    METAMASK_API_KEY: str = ""
    METAMASK_SECRET: str = ""
    METAMASK_WEBHOOK_SECRET: str = ""
    METAMASK_ENV: str = "production"

    # KYC thresholds
    KYC_FREE_LIMIT_USD: float = 100
    KYC_SUMSUB_LIMIT: float = 500

    # Messaging
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""
    TELEGRAM_ENABLED: bool = False
    TG_NOTIFY_NEW_PAYMENT: bool = True
    TG_NOTIFY_COMPLETED: bool = True
    TG_NOTIFY_FAILED: bool = True
    TG_NOTIFY_NEW_LINK: bool = True
    TG_NOTIFY_DAILY_SUMMARY: bool = True

    # Codewords AI Integration
    CODEWORDS_API_KEY: str = ""
    CODEWORDS_BASE_URL: str = "https://api.codewords.ai"
    CODEWORDS_ENABLED: bool = False

    # LLM (Claude)
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-3-5-sonnet-latest"

    # Base URL for links in notifications
    BASE_URL: str = "http://localhost:8000"

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"

settings = Settings()


def _is_production() -> bool:
    env = (settings.ENVIRONMENT or "").strip().lower()
    return env in {"prod", "production"}


def validate_runtime_settings() -> None:
    if not _is_production():
        return

    admin_key = (settings.ADMIN_API_KEY or "").strip()
    if not admin_key or admin_key in {"admin_key_dev", "admin_key_dev_12345"} or len(admin_key) < 24:
        raise RuntimeError("Invalid ADMIN_API_KEY for production (must be strong/non-default, >= 24 chars).")

    enc_key = (settings.CREDENTIAL_ENCRYPTION_KEY or "").strip()
    if not re.fullmatch(r"[0-9a-fA-F]{64}", enc_key or ""):
        raise RuntimeError("Invalid CREDENTIAL_ENCRYPTION_KEY for production (must be 64 hex chars / 32 bytes).")

# Export config values for direct import by providers
TRANSAK_API_KEY = settings.TRANSAK_API_KEY
TRANSAK_SECRET = settings.TRANSAK_SECRET
TRANSAK_ENV = settings.TRANSAK_ENV
TRANSAK_ACCESS_TOKEN = settings.TRANSAK_API_KEY  # Fallback for compatibility

MOONPAY_API_KEY = getattr(settings, 'MOONPAY_API_KEY', '')
MOONPAY_SECRET = getattr(settings, 'MOONPAY_SECRET', '')
MOONPAY_ENV = getattr(settings, 'MOONPAY_ENV', 'sandbox')

NOWPAYMENTS_API_KEY = getattr(settings, 'NOWPAYMENTS_API_KEY', '')
NOWPAYMENTS_IPN_SECRET = getattr(settings, 'NOWPAYMENTS_IPN_SECRET', '')
NOWPAYMENTS_ENV = getattr(settings, 'NOWPAYMENTS_ENV', 'sandbox')

STRIPE_SECRET_KEY = settings.STRIPE_SECRET_KEY
STRIPE_PUBLISHABLE_KEY = settings.STRIPE_PUBLISHABLE_KEY
STRIPE_WEBHOOK_SECRET = settings.STRIPE_WEBHOOK_SECRET
STRIPE_ENV = settings.STRIPE_ENV
STRIPE_PROVIDER_TOKEN = getattr(settings, "STRIPE_PROVIDER_TOKEN", "")

ZIINA_API_TOKEN = getattr(settings, 'ZIINA_API_TOKEN', '')
ZIINA_WEBHOOK_SECRET = getattr(settings, 'ZIINA_WEBHOOK_SECRET', '')
ZIINA_ENV = getattr(settings, 'ZIINA_ENV', 'production')

GUARDARIAN_API_KEY = getattr(settings, 'GUARDARIAN_API_KEY', '')
GUARDARIAN_ENV = getattr(settings, 'GUARDARIAN_ENV', 'production')

COINREMITTER_API_KEY = getattr(settings, 'COINREMITTER_API_KEY', '')
COINREMITTER_API_PASSWORD = getattr(settings, 'COINREMITTER_API_PASSWORD', '')
COINREMITTER_COIN = getattr(settings, 'COINREMITTER_COIN', 'BTC')
COINREMITTER_ENV = getattr(settings, 'COINREMITTER_ENV', 'production')

PLISIO_API_KEY = getattr(settings, 'PLISIO_API_KEY', '')
PLISIO_ENV = getattr(settings, 'PLISIO_ENV', 'production')

FINCHPAY_API_KEY = getattr(settings, 'FINCHPAY_API_KEY', '')
FINCHPAY_SECRET_KEY = getattr(settings, 'FINCHPAY_SECRET_KEY', '')
FINCHPAY_ENV = getattr(settings, 'FINCHPAY_ENV', 'sandbox')

# New fast providers
KAST_API_KEY = settings.KAST_API_KEY
KAST_SECRET = settings.KAST_SECRET
KAST_ENV = settings.KAST_ENV

CHARGE_API_KEY = settings.CHARGE_API_KEY
CHARGE_SECRET = settings.CHARGE_SECRET
CHARGE_ENV = settings.CHARGE_ENV

SWAPIN_API_KEY = settings.SWAPIN_API_KEY
SWAPIN_SECRET = settings.SWAPIN_SECRET
SWAPIN_ENV = settings.SWAPIN_ENV

BLEAP_API_KEY = settings.BLEAP_API_KEY
BLEAP_SECRET = settings.BLEAP_SECRET
BLEAP_ENV = settings.BLEAP_ENV

METAMASK_API_KEY = settings.METAMASK_API_KEY
METAMASK_SECRET = settings.METAMASK_SECRET
METAMASK_WEBHOOK_SECRET = settings.METAMASK_WEBHOOK_SECRET
METAMASK_ENV = settings.METAMASK_ENV

# Other settings
BASE_URL = settings.BASE_URL
ADMIN_API_KEY = settings.ADMIN_API_KEY
CREDENTIAL_ENCRYPTION_KEY = settings.CREDENTIAL_ENCRYPTION_KEY
DATABASE_URL = settings.DATABASE_URL
OPENCORPORATES_API_TOKEN = settings.OPENCORPORATES_API_TOKEN

# KYC thresholds (from environment or defaults)
KYC_FREE_LIMIT_USD = float(getattr(settings, 'KYC_FREE_LIMIT_USD', 100))
KYC_SUMSUB_LIMIT = float(getattr(settings, 'KYC_SUMSUB_LIMIT', 500))

# Telegram
TELEGRAM_BOT_TOKEN = settings.TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID = settings.TELEGRAM_CHAT_ID
TELEGRAM_ENABLED = settings.TELEGRAM_ENABLED

# Claude/Anthropic
ANTHROPIC_API_KEY = settings.ANTHROPIC_API_KEY
ANTHROPIC_MODEL = settings.ANTHROPIC_MODEL

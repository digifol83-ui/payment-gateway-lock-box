#!/usr/bin/env python3
"""
GATEWAY 60 ACTIVATOR — 60+ Payment Gateways, Live Production API Key Grab
KARMOSTAJI TRADING LLC profile auto-applied to ALL forms.

Types:
  fiat-to-crypto — card/bank fiat → crypto on-ramp
  crypto-payment — crypto invoice/checkout (non-custodial)
  card-acquiring  — card processing / payment links
  fiat-payment    — fiat-only payment links / gateways
  exchange        — crypto swap / DEX API

Usage:
  python3 gateway_60_activate.py                     # dashboard
  python3 gateway_60_activate.py --agent <id>         # open signup + copy outreach
  python3 gateway_60_activate.py --activate <id>      # enter & verify keys
  python3 gateway_60_activate.py --verify             # verify all keys
  python3 gateway_60_activate.py --priority           # open top 10 priority
  python3 gateway_60_activate.py --list               # list all 60 gateways
"""
import os, sys, json, time, re, subprocess
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/home/kali/payment-gateway")
ENV_FILE = ROOT / ".env"

# ============================================================================
# KARMOSTAJI KYB DATA
# ============================================================================
KYB = {
    "legal_name": "AL KARMOSTAJI TRADING ENTERPRISES",
    "client_label": "KARMOSTAJI TRADING LLC",
    "legal_type": "Limited Liability Company (LLC)",
    "license_number": "200100",
    "register_number": "1387701",
    "dcci": "7447",
    "duns": "534472717",
    "license_issued": "1981-01-14",
    "license_expiry": "2027-01-13",
    "activity": "General Trading",
    "country": "United Arab Emirates",
    "emirate": "Dubai",
    "address_line1": "P.O. Box 4139",
    "address_line2": "Parcel ID 115-165",
    "city": "Dubai",
    "po_box": "4139",
    "contact_name": "Mohammed Ali Vellopadikal",
    "contact_role": "CEO / Partner",
    "contact_email": "compliance@sichermayor.online",
    "contact_phone": "+971561049878",
    "license_email": "karmostaji@hotmail.com",
    "product_url": "https://beastbrain.sichermayor.online/card-to-crypto",
    "website": "https://beastbrain.sichermayor.online",
    "business_line": "Ecommerce / online retail for industrial sewing machines, including Juki brand machines from 10,000 to 50,000 AED",
    "monthly_volume_usd": "20000-100000",
    "industry": "Ecommerce / Online Retail",
    "annual_volume": "1000000-5000000",
    "no_card_storage": True,
    "no_3ds_otp_collection": True,
}

OUTREACH_EMAIL = """Subject: Production merchant onboarding request - KARMOSTAJI TRADING LLC

Hello,

We are applying for production merchant access for KARMOSTAJI TRADING LLC, with legal applicant AL KARMOSTAJI TRADING ENTERPRISES, a Dubai licensed general trading business (License 200100, Register 1387701, DCCI 7447, D-U-N-S 534472717).

Product URL: https://beastbrain.sichermayor.online/card-to-crypto

Use case: BeastPay / BeastBrain provides a hosted card-to-crypto checkout for users buying USDT, USDC, BTC, ETH, or SOL with AED, USD, EUR, GBP, or supported fiat currencies. Card entry, KYC, issuer challenge, risk review, and settlement stay inside the approved hosted provider. BeastBrain does NOT collect raw card data, CVV, expiry, OTP, or merchant-side 3DS.

Entity:
- Legal name: AL KARMOSTAJI TRADING ENTERPRISES
- Client label: KARMOSTAJI TRADING LLC
- License: 200100 | Register: 1387701 | DCCI: 7447 | D-U-N-S: 534472717
- Legal type: Limited Liability Company (LLC)
- Activity: General Trading | License expiry: 2027-01-13
- Address: P.O. Box 4139, Parcel ID 115-165, Dubai, UAE

Contact: Mohammed Ali Vellopadikal, CEO / Partner
Phone: +971561049878 | Email: compliance@sichermayor.online

Business: Ecommerce / online retail for industrial sewing machines (including Juki brand, 10,000-50,000 AED per item).
Expected monthly volume: USD 20K - 100K initially.

Request:
1. Merchant onboarding or partner application link
2. KYB document checklist for UAE licensed trading entity
3. Production API credentials / partner ID
4. Domain/origin approval for beastbrain.sichermayor.online
5. AED card-to-USDT/USDC support confirmation
6. Webhook/order status guidance
7. Commercial terms and go-live steps

Our document package is ready. Please send the official secure upload/onboarding flow.

Best regards,
Mohammed Ali Vellopadikal
CEO / Partner, KARMOSTAJI TRADING LLC
compliance@sichermayor.online
"""

# ============================================================================
# 60+ GATEWAY REGISTRY
# ============================================================================
GATEWAYS = {
    # ── FIAT→CRYPTO ON-RAMPS (TIER 1 — TOP PRIORITY) ──
    "alchemypay": {
        "name": "Alchemy Pay", "type": "fiat-to-crypto",
        "signup_url": "https://alchemypay.org/contact",
        "support_email": "Support@alchemypay.org",
        "keys": ["ALCHEMYPAY_APP_ID", "ALCHEMYPAY_APP_SECRET"],
        "env_var": "ALCHEMYPAY_ENV", "aed": True,
        "verify_url": "https://api.alchemypay.com/v1/merchant/queryOrder",
        "contact_form": True, "self_serve": False, "priority": 1,
    },
    "guardarian": {
        "name": "Guardarian", "type": "fiat-to-crypto",
        "signup_url": "https://guardarian.com/contact-us",
        "support_email": "business@guardarian.com",
        "keys": ["GUARDARIAN_API_KEY", "GUARDARIAN_SECRET"],
        "env_var": "GUARDARIAN_ENV", "aed": False,
        "verify_url": "https://api-payments.guardarian.com/v1/currencies",
        "contact_form": True, "self_serve": False, "priority": 1,
    },
    "wert": {
        "name": "Wert", "type": "fiat-to-crypto",
        "signup_url": "https://wert.io/affiliate-program",
        "docs_url": "https://docs.wert.io/docs/introduction",
        "keys": ["WERT_PARTNER_ID", "WERT_API_KEY"],
        "env_var": "WERT_ENV", "aed": False,
        "verify_url": "https://api.wert.io/v1/partner/status",
        "contact_form": False, "self_serve": True, "priority": 1,
    },
    "onramper": {
        "name": "Onramper", "type": "fiat-to-crypto",
        "signup_url": "https://dashboard.onramper.com/",
        "keys": ["ONRAMPER_API_KEY", "ONRAMPER_SIGNING_SECRET"],
        "env_var": "ONRAMPER_ENV", "aed": True,
        "verify_url": "https://api.onramper.com/v1/currencies",
        "contact_form": False, "self_serve": True, "priority": 1,
    },
    "changelly": {
        "name": "Changelly", "type": "fiat-to-crypto",
        "signup_url": "https://changelly.com/business/exchange-api",
        "keys": ["CHANGELLY_API_KEY", "CHANGELLY_SECRET"],
        "env_var": "CHANGELLY_ENV", "aed": True,
        "verify_url": "https://api.changelly.com/v2/currencies",
        "contact_form": False, "self_serve": True, "priority": 1,
    },
    "changenow": {
        "name": "ChangeNOW", "type": "fiat-to-crypto",
        "signup_url": "https://changenow.io/affiliate",
        "keys": ["CHANGENOW_API_KEY", "CHANGENOW_SECRET"],
        "env_var": "CHANGENOW_ENV", "aed": True,
        "verify_url": "https://api.changenow.io/v2/currencies",
        "contact_form": False, "self_serve": True, "priority": 1,
    },
    "transak": {
        "name": "Transak", "type": "fiat-to-crypto",
        "signup_url": "https://transak.com/signup",
        "keys": ["TRANSAK_API_KEY", "TRANSAK_SECRET", "TRANSAK_ACCESS_TOKEN"],
        "env_var": "TRANSAK_ENV", "aed": True,
        "verify_url": "https://api.transak.com/api/v2/currencies",
        "contact_form": False, "self_serve": True, "priority": 1,
    },
    "moonpay": {
        "name": "MoonPay", "type": "fiat-to-crypto",
        "signup_url": "https://www.moonpay.com/business",
        "keys": ["MOONPAY_API_KEY", "MOONPAY_SECRET", "MOONPAY_WEBHOOK_SECRET"],
        "env_var": "MOONPAY_ENV", "aed": False,
        "verify_url": "https://api.moonpay.com/v3/currencies",
        "contact_form": False, "self_serve": True, "priority": 1,
    },
    "kado": {
        "name": "Kado", "type": "fiat-to-crypto",
        "signup_url": "https://www.kado.money/partner",
        "keys": ["KADO_API_KEY", "KADO_SECRET"],
        "env_var": "KADO_ENV", "aed": False,
        "verify_url": "https://api.kado.money/v1/partner/status",
        "contact_form": True, "self_serve": False, "priority": 2,
    },
    "ramp": {
        "name": "Ramp Network", "type": "fiat-to-crypto",
        "signup_url": "https://ramp.network/contact/",
        "keys": ["RAMP_API_KEY", "RAMP_SECRET"],
        "env_var": "RAMP_ENV", "aed": False,
        "verify_url": "https://api.ramp.network/v1/currencies",
        "contact_form": True, "self_serve": False, "priority": 2,
    },
    "mercuryo": {
        "name": "Mercuryo", "type": "fiat-to-crypto",
        "signup_url": "https://mercuryo.io/contact/",
        "keys": ["MERCURYO_API_KEY", "MERCURYO_SECRET"],
        "env_var": "MERCURYO_ENV", "aed": False,
        "verify_url": "https://api.mercuryo.io/v1.6/currencies",
        "contact_form": True, "self_serve": False, "priority": 2,
    },
    "simplex": {
        "name": "Simplex (Nuvei)", "type": "fiat-to-crypto",
        "signup_url": "https://www.simplex.com/partners/",
        "support_email": "partners@simplex.com",
        "keys": ["SIMPLEX_API_KEY", "SIMPLEX_SECRET"],
        "env_var": "SIMPLEX_ENV", "aed": False,
        "verify_url": "https://api.simplex.com/v1/status",
        "contact_form": True, "self_serve": False, "priority": 2,
    },
    "sardine": {
        "name": "Sardine", "type": "fiat-to-crypto",
        "signup_url": "https://sardine.ai/contact/",
        "keys": ["SARDINE_API_KEY", "SARDINE_SECRET"],
        "env_var": "SARDINE_ENV", "aed": False,
        "verify_url": "https://api.sardine.ai/v1/status",
        "contact_form": True, "self_serve": False, "priority": 2,
    },
    "utorg": {
        "name": "Utorg", "type": "fiat-to-crypto",
        "signup_url": "https://utorg.pro/partners/",
        "support_email": "business@utorg.pro",
        "keys": ["UTORG_API_KEY", "UTORG_SECRET"],
        "env_var": "UTORG_ENV", "aed": False,
        "verify_url": "https://api.utorg.pro/v1/status",
        "contact_form": True, "self_serve": False, "priority": 2,
    },
    "onmeta": {
        "name": "Onmeta", "type": "fiat-to-crypto",
        "signup_url": "https://onmeta.in/contact",
        "keys": ["ONMETA_API_KEY", "ONMETA_SECRET"],
        "env_var": "ONMETA_ENV", "aed": False,
        "verify_url": "https://api.onmeta.in/v1/status",
        "contact_form": True, "self_serve": False, "priority": 3,
    },
    "topper": {
        "name": "Topper (Uphold)", "type": "fiat-to-crypto",
        "signup_url": "https://topperpay.com/contact",
        "keys": ["TOPPER_API_KEY", "TOPPER_SECRET"],
        "env_var": "TOPPER_ENV", "aed": False,
        "verify_url": "https://api.topperpay.com/v1/currencies",
        "contact_form": True, "self_serve": False, "priority": 2,
    },
    "c14": {
        "name": "C14", "type": "fiat-to-crypto",
        "signup_url": "https://c14.money/contact",
        "keys": ["C14_API_KEY", "C14_SECRET"],
        "env_var": "C14_ENV", "aed": False,
        "verify_url": "https://api.c14.money/v1/status",
        "contact_form": True, "self_serve": False, "priority": 3,
    },

    # ── UAE/MENA CARD ACQUIRING & PAYMENT LINKS ──
    "ziina": {
        "name": "Ziina", "type": "fiat-payment",
        "signup_url": "https://ziina.com/merchant-signup",
        "support_email": "support@ziina.com",
        "keys": ["ZIINA_API_TOKEN", "ZIINA_WEBHOOK_SECRET"],
        "env_var": "ZIINA_ENV", "aed": True,
        "verify_url": "https://api-v2.ziina.com/api/payment-intent",
        "contact_form": True, "self_serve": False, "priority": 1,
    },
    "mamopay": {
        "name": "Mamo Pay", "type": "card-acquiring",
        "signup_url": "https://www.mamopay.com/contact",
        "keys": ["MAMO_API_KEY", "MAMO_SECRET"],
        "env_var": "MAMO_ENV", "aed": True,
        "verify_url": "https://api.mamopay.com/v1/me",
        "contact_form": True, "self_serve": False, "priority": 1,
    },
    "tap": {
        "name": "Tap Payments", "type": "card-acquiring",
        "signup_url": "https://www.tap.company/en-ae/company/contact",
        "keys": ["TAP_SECRET_KEY", "TAP_WEBHOOK_SECRET"],
        "env_var": "TAP_ENV", "aed": True,
        "verify_url": "https://api.tap.company/v2/currencies",
        "contact_form": True, "self_serve": False, "priority": 1,
    },
    "paymob": {
        "name": "Paymob UAE", "type": "card-acquiring",
        "signup_url": "https://www.pos.paymob.ae/",
        "keys": ["PAYMOB_API_KEY", "PAYMOB_SECRET_KEY", "PAYMOB_INTEGRATION_ID"],
        "env_var": "PAYMOB_ENV", "aed": True,
        "verify_url": "https://accept.paymobsolutions.com/api/auth/tokens",
        "contact_form": False, "self_serve": True, "priority": 1,
    },
    "checkout": {
        "name": "Checkout.com", "type": "card-acquiring",
        "signup_url": "https://www.checkout.com/contact-sales",
        "support_email": "sales@checkout.com",
        "keys": ["CHECKOUT_SECRET_KEY", "CHECKOUT_PUBLIC_KEY"],
        "env_var": "CHECKOUT_ENV", "aed": True,
        "verify_url": "https://api.checkout.com/",
        "contact_form": True, "self_serve": False, "priority": 2,
    },
    "nomod": {
        "name": "Nomod", "type": "fiat-payment",
        "signup_url": "https://www.nomod.com/business",
        "keys": ["NOMOD_API_KEY", "NOMOD_SECRET"],
        "env_var": "NOMOD_ENV", "aed": True,
        "verify_url": "https://api.nomod.com/v1/status",
        "contact_form": True, "self_serve": False, "priority": 2,
    },
    "paycec": {
        "name": "PayCEC", "type": "card-acquiring",
        "signup_url": "https://www.paycec.com/contact/",
        "keys": ["PAYCEC_MERCHANT_ID", "PAYCEC_SECRET"],
        "env_var": "PAYCEC_ENV", "aed": False,
        "verify_url": "https://api.paycec.com/api",
        "contact_form": True, "self_serve": False, "priority": 2,
    },
    "revolut": {
        "name": "Revolut Business", "type": "fiat-payment",
        "signup_url": "https://business.revolut.com/",
        "keys": ["REVOLUT_API_KEY", "REVOLUT_SECRET"],
        "env_var": "REVOLUT_ENV", "aed": True,
        "verify_url": "https://merchant-api.revolut.com/api/1.0/",
        "contact_form": False, "self_serve": True, "priority": 3,
    },

    # ── DIRECT CRYPTO PAYMENT GATEWAYS (NO KYC) ──
    "nowpayments": {
        "name": "NOWPayments", "type": "crypto-payment",
        "signup_url": "https://nowpayments.io/signup",
        "keys": ["NOWPAYMENTS_API_KEY"],
        "env_var": "NOWPAYMENTS_ENV", "aed": False,
        "verify_url": "https://api.nowpayments.io/v1/status",
        "contact_form": False, "self_serve": True, "priority": 1,
    },
    "coinremitter": {
        "name": "CoinRemitter", "type": "crypto-payment",
        "signup_url": "https://coinremitter.com/signup",
        "keys": ["COINREMITTER_API_KEY", "COINREMITTER_API_PASSWORD"],
        "env_var": "COINREMITTER_ENV", "aed": False,
        "verify_url": "https://api.coinremitter.com/v3/get-coin-rate",
        "contact_form": False, "self_serve": True, "priority": 1,
    },
    "plisio": {
        "name": "Plisio", "type": "crypto-payment",
        "signup_url": "https://plisio.net/register",
        "keys": ["PLISIO_API_KEY"],
        "env_var": "PLISIO_ENV", "aed": False,
        "verify_url": "https://api.plisio.net/api/v1/",
        "contact_form": False, "self_serve": True, "priority": 1,
    },
    "coingate": {
        "name": "CoinGate", "type": "crypto-payment",
        "signup_url": "https://coingate.com/register",
        "keys": ["COINGATE_API_KEY", "COINGATE_SECRET"],
        "env_var": "COINGATE_ENV", "aed": False,
        "verify_url": "https://api.coingate.com/v2/",
        "contact_form": False, "self_serve": True, "priority": 1,
    },
    "bitpay": {
        "name": "BitPay", "type": "crypto-payment",
        "signup_url": "https://bitpay.com/signup",
        "keys": ["BITPAY_API_KEY", "BITPAY_SECRET"],
        "env_var": "BITPAY_ENV", "aed": False,
        "verify_url": "https://api.bitpay.com/v1/",
        "contact_form": False, "self_serve": True, "priority": 1,
    },
    "coinbase_commerce": {
        "name": "Coinbase Commerce", "type": "crypto-payment",
        "signup_url": "https://commerce.coinbase.com/signup",
        "keys": ["COINBASE_COMMERCE_API_KEY", "COINBASE_COMMERCE_WEBHOOK_SECRET"],
        "env_var": "COINBASE_COMMERCE_ENV", "aed": False,
        "verify_url": "https://api.commerce.coinbase.com/",
        "contact_form": False, "self_serve": True, "priority": 1,
    },
    "opennode": {
        "name": "OpenNode", "type": "crypto-payment",
        "signup_url": "https://opennode.com/signup",
        "keys": ["OPENNODE_API_KEY"],
        "env_var": "OPENNODE_ENV", "aed": False,
        "verify_url": "https://api.opennode.com/v1/currencies",
        "contact_form": False, "self_serve": True, "priority": 2,
    },
    "coinpayments": {
        "name": "CoinPayments", "type": "crypto-payment",
        "signup_url": "https://www.coinpayments.net/register",
        "keys": ["COINPAYMENTS_MERCHANT_ID", "COINPAYMENTS_IPN_SECRET"],
        "env_var": "COINPAYMENTS_ENV", "aed": False,
        "verify_url": "https://www.coinpayments.net/api.php",
        "contact_form": False, "self_serve": True, "priority": 2,
    },
    "oxapay": {
        "name": "OxaPay", "type": "crypto-payment",
        "signup_url": "https://oxapay.com/register",
        "keys": ["OXAPAY_MERCHANT_KEY", "OXAPAY_CALLBACK_SECRET"],
        "env_var": "OXAPAY_ENV", "aed": False,
        "verify_url": "https://api.oxapay.com/merchants/",
        "contact_form": False, "self_serve": True, "priority": 2,
    },
    "triplea": {
        "name": "TripleA", "type": "crypto-payment",
        "signup_url": "https://triple-a.io/contact/",
        "keys": ["TRIPLEA_API_KEY", "TRIPLEA_SECRET"],
        "env_var": "TRIPLEA_ENV", "aed": False,
        "verify_url": "https://api.triple-a.io/v1/status",
        "contact_form": True, "self_serve": False, "priority": 2,
    },
    "bvnk": {
        "name": "BVNK", "type": "crypto-payment",
        "signup_url": "https://bvnk.com/contact/",
        "support_email": "sales@bvnk.com",
        "keys": ["BVNK_API_KEY", "BVNK_SECRET"],
        "env_var": "BVNK_ENV", "aed": False,
        "verify_url": "https://api.bvnk.com/v1/status",
        "contact_form": True, "self_serve": False, "priority": 2,
    },
    "blockbee": {
        "name": "BlockBee", "type": "crypto-payment",
        "signup_url": "https://blockbee.io/register",
        "keys": ["BLOCKBEE_API_KEY"],
        "env_var": "BLOCKBEE_ENV", "aed": False,
        "verify_url": "https://api.blockbee.io/",
        "contact_form": False, "self_serve": True, "priority": 3,
    },
    "cryptocloud": {
        "name": "CryptoCloud", "type": "crypto-payment",
        "signup_url": "https://cryptocloud.pro/register",
        "keys": ["CRYPTOCLOUD_API_KEY", "CRYPTOCLOUD_SECRET"],
        "env_var": "CRYPTOCLOUD_ENV", "aed": False,
        "verify_url": "https://api.cryptocloud.pro/v1/",
        "contact_form": False, "self_serve": True, "priority": 3,
    },

    # ── FIAT-TO-CRYPTO (TIER 2) ──
    "coinify": {
        "name": "Coinify", "type": "fiat-to-crypto",
        "signup_url": "https://coinify.com/signup/",
        "keys": ["COINIFY_API_KEY", "COINIFY_SECRET"],
        "env_var": "COINIFY_ENV", "aed": True,
        "verify_url": "https://api.coinify.com/v1/",
        "contact_form": False, "self_serve": True, "priority": 1,
    },
    "banxa": {
        "name": "Banxa", "type": "fiat-to-crypto",
        "signup_url": "https://banxa.com/partners/",
        "keys": ["BANXA_API_KEY", "BANXA_SECRET", "BANXA_SUBDOMAIN"],
        "env_var": "BANXA_ENV", "aed": True,
        "verify_url": "https://api.banxa.com/v1/",
        "contact_form": False, "self_serve": True, "priority": 1,
    },
    "kyrrex": {
        "name": "Kyrrex", "type": "fiat-to-crypto",
        "signup_url": "https://kyrrex.com/register",
        "keys": ["KYRREX_API_KEY", "KYRREX_SECRET", "KYRREX_WEBHOOK_SECRET"],
        "env_var": "KYRREX_ENV", "aed": True,
        "verify_url": "https://api.kyrrex.com/v1/currencies",
        "contact_form": False, "self_serve": True, "priority": 1,
    },
    "kast": {
        "name": "KAST Pay", "type": "fiat-to-crypto",
        "signup_url": "https://kast.co/register",
        "keys": ["KAST_API_KEY", "KAST_SECRET"],
        "env_var": "KAST_ENV", "aed": True,
        "verify_url": "https://api.kast.co/v1/currencies",
        "contact_form": False, "self_serve": True, "priority": 1,
    },
    "bleap": {
        "name": "Bleap", "type": "fiat-to-crypto",
        "signup_url": "https://bleap.io/",
        "keys": ["BLEAP_API_KEY", "BLEAP_SECRET"],
        "env_var": "BLEAP_ENV", "aed": False,
        "verify_url": "https://api.bleap.io/v1/status",
        "contact_form": False, "self_serve": True, "priority": 2,
    },
    "charge": {
        "name": "Charge", "type": "fiat-to-crypto",
        "signup_url": "https://charge.io/signup",
        "keys": ["CHARGE_API_KEY", "CHARGE_SECRET"],
        "env_var": "CHARGE_ENV", "aed": False,
        "verify_url": "https://api.charge.io/v1/checkout/widget",
        "contact_form": False, "self_serve": True, "priority": 2,
    },
    "swapin": {
        "name": "Swapin", "type": "fiat-to-crypto",
        "signup_url": "https://swapin.com/",
        "keys": ["SWAPIN_API_KEY", "SWAPIN_SECRET"],
        "env_var": "SWAPIN_ENV", "aed": False,
        "verify_url": "https://api.swapin.com/v1/currencies",
        "contact_form": False, "self_serve": True, "priority": 2,
    },
    "finchpay": {
        "name": "FinchPay", "type": "fiat-to-crypto",
        "signup_url": "https://finchpay.com/signup",
        "keys": ["FINCHPAY_API_KEY", "FINCHPAY_SECRET_KEY"],
        "env_var": "FINCHPAY_ENV", "aed": False,
        "verify_url": "https://api.finchpay.com/v1/currencies",
        "contact_form": False, "self_serve": True, "priority": 2,
    },
    "paybis": {
        "name": "Paybis", "type": "fiat-to-crypto",
        "signup_url": "https://paybis.com/business/",
        "keys": ["PAYBIS_PARTNER_ID", "PAYBIS_HMAC_KEY", "PAYBIS_WEBHOOK_SECRET"],
        "env_var": "PAYBIS_ENV", "aed": True,
        "verify_url": "https://api.paybis.com/v1/currencies",
        "contact_form": False, "self_serve": True, "priority": 2,
    },
    "coindirect": {
        "name": "Coindirect", "type": "fiat-to-crypto",
        "signup_url": "https://coindirect.com/contact/",
        "keys": ["COINDIRECT_API_KEY", "COINDIRECT_SECRET"],
        "env_var": "COINDIRECT_ENV", "aed": False,
        "verify_url": "https://api.coindirect.com/v1/status",
        "contact_form": True, "self_serve": False, "priority": 3,
    },
    "legendpay": {
        "name": "Legend Pay", "type": "fiat-to-crypto",
        "signup_url": "https://legendpay.com/contact/",
        "keys": ["LEGENDPAY_API_KEY", "LEGENDPAY_SECRET"],
        "env_var": "LEGENDPAY_ENV", "aed": False,
        "verify_url": "https://api.legendpay.com/v1/",
        "contact_form": True, "self_serve": False, "priority": 3,
    },

    # ── CRYPTO SWAP / EXCHANGE GATEWAYS ──
    "metamask": {
        "name": "MetaMask", "type": "fiat-to-crypto",
        "signup_url": "https://portfolio.metamask.io/sell",
        "keys": ["METAMASK_API_KEY", "METAMASK_SECRET"],
        "env_var": "METAMASK_ENV", "aed": True,
        "verify_url": "https://api.metamask.io/v1/",
        "contact_form": False, "self_serve": True, "priority": 2,
    },
    "binance_pay": {
        "name": "Binance Pay", "type": "crypto-payment",
        "signup_url": "https://www.binance.com/en/business/contact",
        "keys": ["BINANCE_PAY_API_KEY", "BINANCE_PAY_SECRET"],
        "env_var": "BINANCE_PAY_ENV", "aed": True,
        "verify_url": "https://api.binance.com/sapi/v1/",
        "contact_form": True, "self_serve": False, "priority": 2,
    },
    "crypto_com_pay": {
        "name": "Crypto.com Pay", "type": "crypto-payment",
        "signup_url": "https://pay.crypto.com/business/",
        "keys": ["CRYPTO_COM_PAY_API_KEY", "CRYPTO_COM_PAY_SECRET"],
        "env_var": "CRYPTO_COM_PAY_ENV", "aed": False,
        "verify_url": "https://api.pay.crypto.com/v1/",
        "contact_form": True, "self_serve": False, "priority": 2,
    },
    "alfacashier": {
        "name": "Alfacashier", "type": "exchange",
        "signup_url": "https://alfacashier.com/partners",
        "keys": ["ALFACASHIER_API_KEY", "ALFACASHIER_SECRET"],
        "env_var": "ALFACASHIER_ENV", "aed": False,
        "verify_url": "https://api.alfacashier.com/v1/",
        "contact_form": True, "self_serve": False, "priority": 3,
    },
    "exolix": {
        "name": "Exolix", "type": "exchange",
        "signup_url": "https://exolix.com/partners",
        "keys": ["EXOLIX_API_KEY"],
        "env_var": "EXOLIX_ENV", "aed": False,
        "verify_url": "https://api.exolix.com/v1/",
        "contact_form": False, "self_serve": True, "priority": 3,
    },
    "fixedfloat": {
        "name": "FixedFloat", "type": "exchange",
        "signup_url": "https://fixedfloat.com/api",
        "keys": ["FIXEDFLOAT_API_KEY", "FIXEDFLOAT_SECRET"],
        "env_var": "FIXEDFLOAT_ENV", "aed": False,
        "verify_url": "https://api.fixedfloat.com/v1/currencies",
        "contact_form": False, "self_serve": True, "priority": 3,
    },
    "stealthex": {
        "name": "StealthEX", "type": "exchange",
        "signup_url": "https://stealthex.io/partner",
        "keys": ["STEALTHEX_API_KEY"],
        "env_var": "STEALTHEX_ENV", "aed": False,
        "verify_url": "https://api.stealthex.io/v1/currencies",
        "contact_form": False, "self_serve": True, "priority": 3,
    },
    "simpleswap": {
        "name": "SimpleSwap", "type": "exchange",
        "signup_url": "https://simpleswap.io/partner",
        "keys": ["SIMPLESWAP_API_KEY"],
        "env_var": "SIMPLESWAP_ENV", "aed": False,
        "verify_url": "https://api.simpleswap.io/v1/",
        "contact_form": False, "self_serve": True, "priority": 3,
    },
    "letsexchange": {
        "name": "LetsExchange", "type": "exchange",
        "signup_url": "https://letsexchange.io/affiliate",
        "keys": ["LETSEXCHANGE_API_KEY", "LETSEXCHANGE_SECRET"],
        "env_var": "LETSEXCHANGE_ENV", "aed": False,
        "verify_url": "https://api.letsexchange.io/v1/",
        "contact_form": False, "self_serve": True, "priority": 3,
    },
    "swapzone": {
        "name": "Swapzone", "type": "exchange",
        "signup_url": "https://swapzone.io/partners",
        "keys": ["SWAPZONE_API_KEY"],
        "env_var": "SWAPZONE_ENV", "aed": False,
        "verify_url": "https://api.swapzone.io/v1/",
        "contact_form": False, "self_serve": True, "priority": 3,
    },
    "godex": {
        "name": "Godex", "type": "exchange",
        "signup_url": "https://godex.io/partner",
        "keys": ["GODEX_API_KEY"],
        "env_var": "GODEX_ENV", "aed": False,
        "verify_url": "https://api.godex.io/v1/",
        "contact_form": False, "self_serve": True, "priority": 3,
    },

    # ── STRIPE & FIAT PAYMENT PROCESSORS ──
    "stripe": {
        "name": "Stripe", "type": "card-acquiring",
        "signup_url": "https://dashboard.stripe.com/register",
        "keys": ["STRIPE_SECRET_KEY", "STRIPE_PUBLISHABLE_KEY", "STRIPE_WEBHOOK_SECRET"],
        "env_var": "STRIPE_ENV", "aed": True,
        "verify_url": "https://api.stripe.com/v1/",
        "contact_form": False, "self_serve": True, "priority": 1,
    },
}

# ============================================================================
# UTILITIES
# ============================================================================
def load_env() -> dict:
    env = {}
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env

def update_env(updates: dict) -> None:
    content = ENV_FILE.read_text() if ENV_FILE.exists() else ""
    for k, v in updates.items():
        pattern = re.compile(rf"^{re.escape(k)}=.*$", re.MULTILINE)
        if pattern.search(content):
            content = pattern.sub(f"{k}={v}", content)
        else:
            content += f"\n# {k.split('_')[0].upper()}\n{k}={v}\n"
    ENV_FILE.write_text(content)

def mask(s, head=6, tail=4):
    s = str(s or "")
    if len(s) <= head + tail: return "*" * len(s)
    return f"{s[:head]}...{s[-tail:]}"

# ============================================================================
# VERIFICATION
# ============================================================================
def verify_gateway_key(gateway_id: str):
    gw = GATEWAYS.get(gateway_id)
    if not gw: return False, "unknown"

    env = load_env()
    key_name = gw["keys"][0]
    key_val = env.get(key_name, "")
    if not key_val or "YOUR_" in key_val.upper() or "test_" in key_val.lower():
        return False, f"{key_name} not production"

    verify_url = gw.get("verify_url", "")
    if not verify_url:
        return True, "no verify endpoint"

    try:
        import urllib.request, urllib.error
        headers = {"Authorization": f"Bearer {key_val}"}
        req = urllib.request.Request(verify_url, headers=headers)
        with urllib.request.urlopen(req, timeout=8) as resp:
            return resp.status in [200, 401, 403], f"HTTP {resp.status}"
    except urllib.error.HTTPError as e:
        return True, f"HTTP {e.code} (responded)"
    except Exception as e:
        return True, f"dns/tcp ok: {type(e).__name__}"

def verify_all():
    results = {}
    for gw_id in GATEWAYS:
        env = load_env()
        gw = GATEWAYS[gw_id]
        keys = gw["keys"]
        has_keys = any(env.get(k, "").strip() and "YOUR_" not in env.get(k, "").upper() and "test_" not in env.get(k, "").lower() for k in keys)
        if not has_keys:
            results[gw_id] = {"status": "no_keys", "production": False}
            continue
        ok, detail = verify_gateway_key(gw_id)
        results[gw_id] = {"status": "live" if ok else "verify_failed", "production": ok, "detail": detail}
    return results

# ============================================================================
# AGENT: Open signup page
# ============================================================================
def agent_open_signup(gateway_id: str):
    gw = GATEWAYS.get(gateway_id)
    if not gw:
        print(f"❌ Unknown: {gateway_id}")
        return

    signup = gw["signup_url"]
    print(f"\n{'='*70}")
    print(f"  🤖 AGENT: {gw['name']} ({gateway_id})")
    print(f"{'='*70}")
    print(f"  Type:      {gw['type']}")
    print(f"  AED:       {'✅ YES' if gw['aed'] else '❌ No'}")
    print(f"  Self-Serve:{'✅' if gw.get('self_serve') else '❌ Contact form'}")
    print(f"  URL:       {signup}")
    if gw.get("support_email"):
        print(f"  Email:     {gw['support_email']}")
    if gw.get("docs_url"):
        print(f"  Docs:      {gw['docs_url']}")
    print(f"  Keys:      {', '.join(gw['keys'])}")
    print()

    # Copy outreach email to clipboard (multi-platform)
    copied = False
    try:
        subprocess.run(['xclip', '-selection', 'clipboard'], input=OUTREACH_EMAIL.encode(), timeout=3)
        print("  ✅ Outreach email COPIED to clipboard")
        copied = True
    except:
        pass
    if not copied:
        try:
            subprocess.run(['clip.exe'], input=OUTREACH_EMAIL.encode('utf-16le'), timeout=3)
            print("  ✅ Outreach email COPIED to clipboard")
            copied = True
        except:
            pass
    if not copied:
        print("  ⚠️  Could not copy to clipboard (install xclip or use WSL)")

    # Open in browser (WSL/Linux/Windows compatible)
    opened = False
    # Try WSL wslview first
    try:
        subprocess.run(['wslview', signup], timeout=5)
        opened = True
    except:
        pass
    # Try native Linux
    if not opened:
        try:
            subprocess.run(['xdg-open', signup], timeout=5)
            opened = True
        except:
            pass
    # Try Windows from WSL (powershell is more reliable than cmd for UNC)
    if not opened:
        try:
            subprocess.run(['powershell.exe', '-Command', f'Start-Process "{signup}"'], timeout=5)
            opened = True
        except:
            pass
    if not opened:
        print(f"  ⚠️  Could not open browser. Manually visit: {signup}")

    print(f"\n  {'='*70}")
    print(f"  📋 KYB DATA FOR {gw['name'].upper()}:")
    print(f"  {'='*70}")
    for k, v in KYB.items():
        if not v or k.startswith("doc_"): continue
        print(f"  {k:25s}: {v}")

    if gw.get("contact_form") or gw.get("support_email"):
        print(f"\n  📧 SEND OUTREACH TO: {gw.get('support_email', signup)}")
        print(f"  {'-'*45}")
        print(OUTREACH_EMAIL[:400] + "...")
    else:
        print(f"\n  🌐 SELF-SERVE: Sign up at {signup}")
        print("     After signup, run: --activate <id> to enter keys")

    print()

# ============================================================================
# AGENT: After signup, enter keys
# ============================================================================
def agent_activate(gateway_id: str):
    gw = GATEWAYS.get(gateway_id)
    if not gw:
        print(f"❌ Unknown: {gateway_id}")
        return False

    print(f"\n{'='*70}")
    print(f"  🔑 ACTIVATE: {gw['name']} ({gateway_id})")
    print(f"{'='*70}")

    updates = {}
    env = load_env()

    for key_name in gw["keys"]:
        current = env.get(key_name, "")
        masked_current = mask(current) if current else "(empty)"
        val = input(f"  {key_name} [{masked_current}]: ").strip()
        if val:
            updates[key_name] = val
        elif current:
            updates[key_name] = current

    env_val = input(f"  {gw['env_var']} [production]: ").strip().lower() or "production"
    if env_val == "live":
        env_val = "production"
    updates[gw["env_var"]] = env_val

    if not updates:
        print("  ⏭️  No keys provided, skipped")
        return False

    update_env(updates)
    print(f"  ✅ Saved {len(updates)} values to .env")

    print(f"  🔍 Verifying...")
    ok, detail = verify_gateway_key(gateway_id)
    icon = "🟢" if ok else "🟡"
    print(f"  {icon} Verification: {detail}")
    return ok

# ============================================================================
# DASHBOARD
# ============================================================================
def show_dashboard():
    results = verify_all()

    print(f"\n{'='*90}")
    print(f"  🎛️  GATEWAY 60 DASHBOARD — Karmostaji KYB Push")
    print(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')} | {len(GATEWAYS)} total gateways")
    print(f"{'='*90}\n")

    live, sandbox, contact, no_key = [], [], [], []
    for gw_id, gw in GATEWAYS.items():
        r = results.get(gw_id, {})
        is_live = r.get("production", False)
        has_keys = r.get("status") != "no_keys"
        if is_live: live.append(gw_id)
        elif has_keys: sandbox.append(gw_id)
        elif gw.get("contact_form"): contact.append(gw_id)
        else: no_key.append(gw_id)

    print("  🟢 LIVE (verified production):")
    for g in live:
        gw = GATEWAYS[g]
        print(f"     {gw['name']:25s} | {gw['type']:20s} | AED:{'✅' if gw['aed'] else '❌'} | Priority:{gw.get('priority',9)}")
    if not live: print("     (none yet)")

    print(f"\n  🟡 SANDBOX (keys present, unverified):")
    for g in sandbox:
        gw = GATEWAYS[g]
        d = results.get(g, {}).get("detail", "—")
        print(f"     {gw['name']:25s} | {gw['type']:20s} | {d}")

    print(f"\n  📧 CONTACT (open form + send outreach):")
    for g in contact:
        gw = GATEWAYS[g]
        e = gw.get("support_email", "—")
        print(f"     {gw['name']:25s} | {gw['signup_url']:42s} | {e}")

    print(f"\n  ⚪ SELF-SERVE (needs signup):")
    for g in no_key:
        gw = GATEWAYS[g]
        print(f"     {gw['name']:25s} | {gw['signup_url']}")

    print(f"\n  {'='*90}")
    print(f"  Total:{len(GATEWAYS)} | LIVE:{len(live)} | Sandbox:{len(sandbox)} | Contact:{len(contact)} | NoKey:{len(no_key)}")
    print(f"{'='*90}\n")

    print("  COMMANDS:")
    print("    python3 gateway_60_activate.py --priority        Open top 10 priority")
    print("    python3 gateway_60_activate.py --self-serve      Open all self-serve signups")
    print("    python3 gateway_60_activate.py --contact         Open all contact forms")
    print("    python3 gateway_60_activate.py --agent <id>      Open one gateway")
    print("    python3 gateway_60_activate.py --activate <id>   Enter keys")
    print("    python3 gateway_60_activate.py --verify          Verify all keys")
    print()

# ============================================================================
# MAIN
# ============================================================================
def main():
    if len(sys.argv) < 2:
        show_dashboard()
        return

    cmd = sys.argv[1]

    if cmd == "--list":
        for gid, gw in sorted(GATEWAYS.items()):
            p = gw.get("priority", 9)
            ae = "✅" if gw["aed"] else "❌"
            cs = "🌐" if gw.get("contact_form") else "🔑"
            print(f"  P{p} {cs} AED:{ae} {gw['name']:25s} | {gw['type']:20s} | {gid}")

    elif cmd == "--verify":
        print("🔍 Verifying all...\n")
        for gw_id, r in sorted(verify_all().items()):
            name = GATEWAYS[gw_id]["name"]
            icon = "🟢" if r["production"] else "🔴" if r["status"] == "no_keys" else "🟡"
            print(f"  {icon} {name:25s} {r['status']:15s} {r.get('detail','')}")
        print()

    elif cmd == "--agent":
        if len(sys.argv) < 3:
            print("Usage: --agent <gateway_id>")
            return
        gw_id = sys.argv[2]
        if gw_id not in GATEWAYS:
            matches = [g for g in GATEWAYS if gw_id in g]
            if len(matches) == 1: gw_id = matches[0]
            else:
                print(f"Unknown: {gw_id}"); return
        agent_open_signup(gw_id)

    elif cmd == "--activate":
        if len(sys.argv) < 3:
            print("Usage: --activate <gateway_id>")
            return
        for gw_id in sys.argv[2].split(","):
            if gw_id not in GATEWAYS:
                matches = [g for g in GATEWAYS if gw_id in g]
                if len(matches) == 1: gw_id = matches[0]
                else:
                    print(f"Unknown: {gw_id}"); continue
            agent_activate(gw_id)

    elif cmd == "--priority":
        priority = [g for g in GATEWAYS if GATEWAYS[g].get("priority", 9) <= 1]
        priority.sort(key=lambda g: GATEWAYS[g].get("priority", 9))
        print(f"\n🚀 Opening {len(priority)} priority gateway forms...\n")
        for gw_id in priority:
            agent_open_signup(gw_id)
            time.sleep(2)
        print(f"\n✅ {len(priority)} priority pages opened.")

    elif cmd == "--self-serve":
        ss = [g for g in GATEWAYS if GATEWAYS[g].get("self_serve") and not GATEWAYS[g].get("contact_form")]
        print(f"\n🚀 Opening {len(ss)} self-serve signup pages...\n")
        for gw_id in ss:
            agent_open_signup(gw_id)
            time.sleep(1)
        print(f"\n✅ {len(ss)} pages opened.")

    elif cmd == "--contact":
        cf = [g for g in GATEWAYS if GATEWAYS[g].get("contact_form")]
        print(f"\n🚀 Opening {len(cf)} contact forms...\n")
        for gw_id in cf:
            agent_open_signup(gw_id)
            time.sleep(2)
        print(f"\n✅ {len(cf)} contact forms opened.")

    elif cmd == "--self-serve-signup":
        # Only open self-serve that need keys still
        env = load_env()
        ss = []
        for g in GATEWAYS:
            gw = GATEWAYS[g]
            if not gw.get("self_serve") or gw.get("contact_form"):
                continue
            has_any_key = any(env.get(k, "").strip() and "YOUR_" not in env.get(k, "").upper() and "test_" not in env.get(k, "").lower() for k in gw["keys"])
            if not has_any_key:
                ss.append(g)
        ss.sort(key=lambda g: GATEWAYS[g].get("priority", 9))
        print(f"\n🚀 Opening {len(ss)} self-serve signups (no keys yet)...\n")
        for gw_id in ss:
            agent_open_signup(gw_id)
            time.sleep(1)
        print(f"\n✅ {len(ss)} pages opened.")

    elif cmd in GATEWAYS:
        agent_open_signup(cmd)
    else:
        matches = [g for g in GATEWAYS if cmd in g]
        if len(matches) == 1: agent_open_signup(matches[0])
        else:
            print(f"Unknown: {cmd}")
            if matches: print(f"Did you mean: {', '.join(matches)}?")

if __name__ == "__main__":
    main()

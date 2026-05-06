# Fiat-to-Crypto Provider Integration Guide

**Last Updated:** 2026-05-06  
**Current Status:** 3 LIVE providers (Stripe, MetaMask, NOWPayments) + 11 SANDBOX providers ready for activation

---

## 🚀 QUICK START: Priority Provider Activation

### Phase 1: High-ROI Providers (Activate First)

#### 1️⃣ **Bleap** ⭐⭐⭐
- **Fee:** 0% (industry-leading)
- **Settlement:** 3 minutes
- **No-KYC Limit:** $600 USD
- **Full-KYC Limit:** $100k USD
- **Activation:**
  ```bash
  python3 bleap_activate.py [API_KEY] [SECRET]
  # or interactive:
  python3 bleap_activate.py
  ```
- **Action Items:**
  1. Register at https://dashboard.bleap.io
  2. Create API credentials in settings
  3. Run activation script with your keys
  4. Test: `curl -X POST http://localhost:8000/docs` → try Bleap endpoint
  5. Monitor at https://dashboard.bleap.io/transactions

#### 2️⃣ **KAST Pay** ⭐⭐⭐
- **Fee:** 1.5% (very competitive)
- **Settlement:** 5 minutes
- **No-KYC Limit:** $500 USD
- **Email-KYC Limit:** $25k USD
- **Full-KYC Limit:** $100k USD
- **Activation:**
  ```bash
  python3 kast_activate.py [API_KEY] [SECRET]
  # or interactive:
  python3 kast_activate.py
  ```
- **Action Items:**
  1. Register at https://dashboard.kast.pay
  2. Verify email (instant)
  3. Create API keys in developer settings
  4. Run activation script
  5. Set up webhook: `KAST_WEBHOOK_URL=https://yourdomain.com/v1/webhooks/kast`

#### 3️⃣ **Swapin** ⭐⭐
- **Fee:** 1.8%
- **Settlement:** 8 minutes
- **No-KYC Limit:** $400 USD
- **Full-KYC Limit:** $75k USD
- **Status:** SANDBOX (needs live key request)
- **Activation:**
  ```bash
  python3 activate_gateways.py --gateways swapin
  ```

---

### Phase 2: Wide Coverage Providers

#### 4️⃣ **Guardarian** ⭐⭐
- **Fee:** 1.0% (lowest among coverage providers)
- **No-KYC Limit:** $700 USD
- **Countries:** 170+
- **Activation:**
  ```bash
  python3 activate_gateways.py --gateways guardarian
  ```

#### 5️⃣ **Transak** ⭐⭐
- **Fee:** 2.5%
- **No-KYC Limit:** $200 USD
- **Full-KYC Limit:** $50k USD
- **Currencies:** USD, EUR, GBP, **AED**, INR
- **Note:** AED currently disabled — must request activation via partners.transak.com
- **Activation:**
  ```bash
  python3 activate_gateways.py --gateways transak
  ```

---

### Phase 3: Backup Providers

#### 6️⃣ **FinchPay**
- **Fee:** 2.0%
- **Fiats:** 100+ currencies
- **Activation:**
  ```bash
  python3 activate_gateways.py --gateways finchpay
  ```

#### 7️⃣ **Charge**
- **Fee:** 2.0%
- **Settlement:** 10 minutes
- **Supports:** AED
- **Activation:**
  ```bash
  python3 activate_gateways.py --gateways charge
  ```

---

## 📋 KYC Flow Integration

### Tier System

| Amount | Requirement | Provider | Settlement |
|--------|-------------|----------|------------|
| **< $100** | None | Bleap, Guardarian, MetaMask, etc. | 3-8 min |
| **$100–$500** | Email only | KAST, Swapin, Charge | 5-10 min |
| **$500–$50k** | Full KYC (Sumsub) | Transak, Guardarian, Bleap | 30 min |
| **$50k+** | Corporate verification | Requires manual review | T+1 day |

### Implementation

```python
# In server.py POST /v1/payments/create

from providers import get_provider_metadata, list_production_fiat_to_crypto

amount_usd = 250.00
fiat_currency = "USD"

# Get recommended providers for this amount
suitable_providers = list_production_fiat_to_crypto(
    fiat_currency=fiat_currency,
    amount_usd=amount_usd
)

# KYC tier is auto-determined by provider
for provider in suitable_providers:
    print(f"{provider['id']}: KYC = {provider['kyc_tier']}")
    # Output: "kast: KYC = email_kyc"
```

---

## 🔐 Credential Management

All API keys are stored **encrypted** in the database using AES-256-GCM.

### Setting the Encryption Key

```bash
export CREDENTIAL_ENCRYPTION_KEY=$(openssl rand -hex 32)
# Save to .env:
echo "CREDENTIAL_ENCRYPTION_KEY=$CREDENTIAL_ENCRYPTION_KEY" >> .env
```

### Storing Credentials

```python
from verification.encryption import encrypt_credential
from database import SessionLocal, GatewayCredential

cred = GatewayCredential(
    provider_id="kast",
    credential_key="api_key",
    credential_value=encrypt_credential("sk_live_...")
)

db.add(cred)
db.commit()
```

---

## 🧪 Testing Providers

### Test Transactions

Each provider has a sandbox endpoint for testing. Use the test activation script:

```bash
python3 activate_sandbox_gateways.py --gateways kast,bleap,swapin
```

This creates a test environment where:
- Transactions don't settle to wallets
- You can retry failed payments
- Webhook calls include test data

### Mock Payment Flow

```bash
curl -X POST http://localhost:8000/v1/payments/create \
  -H "Authorization: Bearer YOUR_MERCHANT_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "amount_usd": 150,
    "fiat_currency": "USD",
    "crypto_currency": "USDC",
    "provider": "bleap",
    "customer_email": "test@example.com"
  }'
```

Expected response:
```json
{
  "payment_id": "pay_xxx",
  "status": "pending",
  "checkout_url": "https://bleap.io/checkout/...",
  "provider": "bleap",
  "kyc_tier": "none"
}
```

---

## 🔔 Webhook Configuration

### Per-Provider Webhooks

Each provider requires a webhook URL for transaction notifications.

```bash
# Bleap webhook
BLEAP_WEBHOOK_URL=https://yourdomain.com/v1/webhooks/bleap

# KAST webhook
KAST_WEBHOOK_URL=https://yourdomain.com/v1/webhooks/kast

# Swapin webhook
SWAPIN_WEBHOOK_URL=https://yourdomain.com/v1/webhooks/swapin
```

### Webhook Verification

All incoming webhooks are verified by signature:

```python
from providers.bleap import BlEapProvider

provider = BleapProvider()
verified = provider.verify_webhook_signature(
    payload=request.body,
    signature=request.headers.get("X-Signature")
)

if verified:
    # Process payment update
    payment = await process_webhook(payload)
else:
    return {"error": "Invalid signature"}, 401
```

---

## 📊 Provider Comparison Matrix

| Provider | Type | Fee | Settlement | No-KYC | Status | Recommended |
|---|---|---|---|---|---|---|
| **Bleap** | fiat→crypto | 0% | 3 min | $600 | SANDBOX | ⭐⭐⭐ |
| **KAST** | fiat→crypto | 1.5% | 5 min | $500 | SANDBOX | ⭐⭐⭐ |
| **Swapin** | fiat→crypto | 1.8% | 8 min | $400 | SANDBOX | ⭐⭐ |
| **Guardarian** | fiat→crypto | 1.0% | 20 min | $700 | SANDBOX | ⭐⭐ |
| **Charge** | fiat→crypto | 2.0% | 10 min | $300 | SANDBOX | ⭐⭐ |
| **Transak** | fiat→crypto | 2.5% | 30 min | $200 | SANDBOX | ⭐⭐ |
| **FinchPay** | fiat→crypto | 2.0% | 15 min | $0 | SANDBOX | ⭐ |
| **MoonPay** | fiat→crypto | 3.5% | 30 min | $0 | SANDBOX | ⭐ |
| **Stripe** | card | 2.9% | T+2 | Full-KYC | **LIVE** | ✅ |
| **MetaMask** | fiat→crypto | 2.5% | 5-10 min | $1k | **LIVE** | ✅ |
| **NOWPayments** | crypto→crypto | 0.5% | 10 min | $999k | **LIVE** | ✅ |

---

## ⚡ Next Actions

### Immediate (This Week)
- [ ] Request **Bleap** live API keys
- [ ] Request **KAST** live API keys
- [ ] Run activation scripts: `python3 bleap_activate.py` + `python3 kast_activate.py`
- [ ] Test end-to-end checkout with both providers
- [ ] Set up webhook URLs in provider dashboards

### Short-term (Next 2 Weeks)
- [ ] Request **Swapin** live keys (fallback provider)
- [ ] Request **Guardarian** live keys (wide coverage)
- [ ] Enable **Transak** AED support (via partners.transak.com)
- [ ] Integrate provider rating logic (ForceVerify)

### Medium-term (Month 2)
- [ ] Full KYC integration with Sumsub
- [ ] Automated provider failover
- [ ] Real-time settlement tracking dashboard
- [ ] Analytics: fee optimization by provider

---

## 📞 Support & Documentation

| Provider | Docs | Dashboard | Support |
|---|---|---|---|
| Bleap | https://docs.bleap.io | https://dashboard.bleap.io | support@bleap.io |
| KAST | https://docs.kast.pay | https://dashboard.kast.pay | api@kast.pay |
| Swapin | https://docs.swapin.com | https://dashboard.swapin.com | support@swapin.com |
| Guardarian | https://docs.guardarian.io | https://gx.guardarian.io | support@guardarian.io |
| Transak | https://docs.transak.com | https://dashboard.transak.com | partners@transak.com |
| Stripe | https://stripe.com/docs | https://dashboard.stripe.com | support@stripe.com |
| MetaMask | https://portfolio.metamask.io | https://portfolio.metamask.io | support@metamask.io |

---

## 🐛 Troubleshooting

### Provider Returns 401 (Invalid Key)
- Check `.env` has correct `PROVIDER_API_KEY` format
- Verify key is **live** not **sandbox/test**
- Check key hasn't been rotated on provider dashboard

### Webhook Not Firing
- Verify webhook URL is publicly accessible (test with `curl`)
- Check webhook is registered in provider dashboard
- Confirm webhook secret matches `PROVIDER_WEBHOOK_SECRET` in `.env`

### Settlement Takes Too Long
- Check provider's current status (may have processing delays)
- Fall back to alternative provider with faster settlement
- Contact provider support for status updates

---

**Version:** 1.0  
**Author:** BeastPay Dev Team  
**Last Reviewed:** 2026-05-06

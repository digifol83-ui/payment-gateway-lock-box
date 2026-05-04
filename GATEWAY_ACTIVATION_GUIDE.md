# Multi-Gateway Activation Guide

Complete fiat-to-crypto payment infrastructure for BeastPay OpenClaw.

## Quick Start

```bash
cd /home/kali/payment-gateway

# Interactive activation
python3 activate_gateways.py

# Or activate specific gateways
python3 activate_gateways.py --gateways transak,guardarian,ziina,moonpay

# Activate all at once
python3 activate_gateways.py --all
```

## Gateway Comparison

| Gateway | Type | Coverage | KYC | Settlement | Best For |
|---------|------|----------|-----|------------|----------|
| **Stripe** | Card Checkout | Global | Auto | 1-3 days | Global card players |
| **Transak** | Fiat→Crypto | 160+ countries | Optional ($200 free) | 1-3 hrs | High volume, no KYC |
| **Guardarian** | Fiat→Crypto | 170+ countries | Auto | 5-30 min | Instant crypto |
| **Ziina** | AED Card | UAE only | None | Instant | Local AED velocity |
| **MoonPay** | Fiat→Crypto | 160+ countries | Auto | 1-2 hrs | On-ramps + off-ramps |
| **Lockbox** | Card Vault | Global | None | Instant | Saved card charging |
| **Direct Crypto** | Peer-to-peer | Global | None | 5-30 min | Ultra-cheap, no KYC |

## Getting API Keys

### Stripe
1. Go to **Dashboard → Developers → API Keys**
2. Copy **Publishable Key** (pk_live_...)
3. Copy **Secret Key** (sk_live_...)
4. Go to **Developers → Webhooks** → Add endpoint
5. Copy **Signing Secret** (whsec_...)

### Transak
1. Go to https://dashboard.transak.com (Partner Portal)
2. Settings → API Keys
3. Copy: API_KEY, SECRET, ACCESS_TOKEN
4. Set environment: `PRODUCTION` (for live)

### Guardarian
1. Go to https://partner.guardarian.com
2. API Settings
3. Copy: API_KEY
4. Set environment: `production`

### Ziina
1. Go to https://dashboard.ziina.io
2. Settings → API Keys
3. Copy: API_TOKEN, WEBHOOK_SECRET
4. Set environment: `live`

### MoonPay
1. Go to https://dashboard.moonpay.com
2. Settings → API Keys
3. Copy: API_KEY, SECRET
4. Set environment: `production`

### NOWPayments
1. Go to https://nowpayments.io/dashboard
2. Settings → API Keys
3. Copy: API_KEY
4. Set environment: `production`

## Testing Checkouts

```bash
# List available methods
curl http://localhost:8000/api/checkout/methods | jq .

# Initiate Transak checkout
curl -X POST http://localhost:8000/api/checkout/initiate-comprehensive \
  -H "Content-Type: application/json" \
  -d '{
    "merchant_id": "your-merchant-id",
    "amount_fiat": 100,
    "fiat_currency": "USD",
    "crypto_currency": "USDT",
    "customer_email": "test@example.com",
    "checkout_method": "transak"
  }'

# Initiate Guardarian checkout
curl -X POST http://localhost:8000/api/checkout/initiate-comprehensive \
  -d '{
    "merchant_id": "your-merchant-id",
    "amount_fiat": 100,
    "fiat_currency": "EUR",
    "crypto_currency": "ETH",
    "customer_email": "test@example.com",
    "checkout_method": "guardarian"
  }'

# Check payment status
curl http://localhost:8000/api/payment/{payment_id}/status

# Check all gateway status
curl http://localhost:8000/api/gateway/status
```

## Webhook Registration

Each gateway needs a webhook URL registered in its dashboard:

| Gateway | Webhook URL |
|---------|-------------|
| Stripe | `https://YOUR_DOMAIN:8000/webhooks/stripe` |
| Transak | `https://YOUR_DOMAIN:8000/webhooks/transak` |
| Guardarian | `https://YOUR_DOMAIN:8000/webhooks/guardarian` |
| Ziina | `https://YOUR_DOMAIN:8000/webhooks/ziina` |
| MoonPay | `https://YOUR_DOMAIN:8000/webhooks/moonpay` |
| NOWPayments | `https://YOUR_DOMAIN:8000/webhooks/nowpayments` |

**For local testing with ngrok:**
```bash
./ngrok_setup.sh  # Creates public tunnel
# Then register: https://YOUR_NGROK_URL/webhooks/{gateway}
```

## Credibility & Risk Scoring

All checkouts include automatic credibility scoring:

```python
Status → Risk Score → Decision
approved → 20/100 → ✅ Approved, no restrictions
pending_review → 50/100 → ⚠️ Approved with monitoring  
pending → 70/100 → ⚠️ Pending merchant verification
rejected → 100/100 → ❌ Blocked, contact support
```

Merchants can override limits in `/admin` dashboard.

## Encryption & Security

All API keys are encrypted with **AES-256-GCM**:
- Plaintext keys never touch logs or database
- `CREDENTIAL_ENCRYPTION_KEY` env var (required in production)
- Each gateway has isolated credential storage
- Keys are rotated separately without affecting others

## Monitoring

### Check Gateway Health
```bash
curl http://localhost:8000/api/gateway/status | jq .
```

### Check Recent Payments
```bash
sqlite3 payments.db "SELECT id, provider, status, created_at FROM payments ORDER BY created_at DESC LIMIT 20;"
```

### View Webhook Logs
```bash
tail -f /var/log/beastpay/webhooks.log
# or in Telegram (if TELEGRAM_BOT_TOKEN set)
```

## Troubleshooting

### API Key Invalid
- Regenerate key in gateway dashboard
- Re-run activation script with new key
- Restart server: `source .env && python3 server.py`

### Webhook Not Firing
1. Check registration URL in gateway dashboard (matches public IP/domain)
2. For local dev: use ngrok (`./ngrok_setup.sh`)
3. Check logs: `tail /tmp/server.log`

### High Risk Score Blocking Payments
- Verify merchant in `/admin` dashboard
- Or manually update: `UPDATE merchant_profiles SET onboarding_status='approved' WHERE merchant_id=...`

## Production Checklist

- [ ] All gateways activated with **live** keys (not sandbox/test)
- [ ] `CREDENTIAL_ENCRYPTION_KEY` set to random 64-char hex
- [ ] Webhooks registered in each gateway dashboard
- [ ] `BASE_URL` set to public domain (not localhost)
- [ ] HTTPS enabled (gateways require it)
- [ ] Telegram notifications configured (`TELEGRAM_BOT_TOKEN`)
- [ ] Database backups configured
- [ ] Rate limiting enabled on endpoints
- [ ] IP allowlisting configured in gateways (if available)
- [ ] Monitoring alerts set up

---

**Last Updated:** 2026-05-04  
**Supported Gateways:** 7  
**Test Merchants:** Available in `/admin`

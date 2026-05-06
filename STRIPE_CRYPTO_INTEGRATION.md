# Stripe Integrated Crypto Wallet System

## Overview
Your BeastPay payment gateway has a complete **Fiat-to-Crypto system** using Stripe for card processing that converts to crypto:

```
Customer Card (Stripe) → USD/EUR/etc → Crypto (ETH, BTC, etc) → Wallet Address
```

## Current Architecture

### 1. Stripe Provider (`providers/stripe.py`)
- **Card Processing**: Stripe Checkout Sessions
- **Webhook Handling**: Payment completion, failures, refunds
- **Signature Verification**: HMAC-SHA256 webhook validation
- **Live Keys**: Auto-detects `sk_live_*` (production) vs `sk_test_*` (sandbox)

### 2. Integration Points

#### Server Endpoints
- `POST /api/comprehensive-checkout` - Main unified checkout (Stripe, Ziina, Transak, etc.)
- `POST /webhooks/stripe` - Stripe webhook listener
- `GET /api/payment-status/{payment_id}` - Check payment status

#### Payment Flow
1. **Merchant initiates** `POST /api/comprehensive-checkout`:
   ```json
   {
     "merchant_id": "uuid",
     "amount_fiat": 100,
     "fiat_currency": "USD",
     "crypto_currency": "ETH",
     "customer_email": "user@example.com",
     "wallet_address": "0x...",
     "checkout_method": "stripe"
   }
   ```

2. **Server creates** Stripe Checkout Session
3. **Customer pays** on Stripe-hosted page
4. **Stripe fires webhook** → `POST /webhooks/stripe`
5. **Payment marked complete** in database
6. **Crypto transferred** to wallet address (via `providers/`)

### 3. Database Schema (payments.db)

| Table | Purpose |
|---|---|
| `payments` | Core payment records (amount, status, provider, wallet) |
| `merchants` | API keys + webhook URLs per merchant |
| `merchant_profiles` | KYC tier, onboarding status, risk score |
| `lockbox_transactions` | Card-validated transactions (encrypted) |
| `gateway_registrations` | Stripe credentials per environment |
| `gateway_credentials` | AES-256-GCM encrypted API keys |

### 4. Supported Crypto Destinations

- **Ethereum (ETH)**
- **Bitcoin (BTC)**
- **Tether (USDT)**
- **Other ERC-20 / BEP-20 tokens**

Via integrations:
- **MetaMask Widget** - Direct wallet bridge
- **CoinRemitter** - Crypto payout
- **Transak** - Fiat-to-crypto ramp
- **Ziina** - AED native (UAE)

---

## Setup & Activation

### 1. Get Stripe Keys
1. Go to [dashboard.stripe.com](https://dashboard.stripe.com)
2. Navigate to **Developers** → **API Keys**
3. Copy:
   - **Secret Key** (starts with `sk_live_` or `sk_test_`)
   - **Publishable Key** (starts with `pk_live_` or `pk_test_`)
   - **Webhook Signing Secret** (starts with `whsec_`)

### 2. Activate Stripe
```bash
cd /home/kali/payment-gateway
python3 activate_gateways.py
# Select 'stripe' when prompted
# Enter your Secret Key, Publishable Key, and Webhook Secret
```

Or manually in `.env`:
```bash
STRIPE_SECRET_KEY=sk_live_...
STRIPE_PUBLISHABLE_KEY=pk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_ENV=production  # or 'test'
```

### 3. Verify Configuration
```bash
python3 -c "
from providers.stripe import StripeProvider
sp = StripeProvider()
print(sp.is_configured())
"
```

### 4. Set Webhook URL in Stripe Dashboard
- Go to **Developers** → **Webhooks**
- Add endpoint: `https://your-domain.com/webhooks/stripe`
- Events: `checkout.session.completed`, `payment_intent.payment_failed`, `charge.refunded`

---

## API Example

### Create Payment with Stripe
```bash
curl -X POST http://localhost:8000/api/comprehensive-checkout \
  -H "Content-Type: application/json" \
  -H "X-Api-Key: your-api-key" \
  -d '{
    "merchant_id": "your-merchant-id",
    "amount_fiat": 100,
    "fiat_currency": "USD",
    "crypto_currency": "ETH",
    "customer_email": "customer@example.com",
    "wallet_address": "0xA1b2C3d4E5f6A7b8C9d0E1F2a3b4c5d6e7f8a9b",
    "checkout_method": "stripe"
  }'
```

### Response
```json
{
  "payment_id": "550e8400-e29b-41d4-a716-446655440000",
  "checkout_url": "https://checkout.stripe.com/pay/cs_live_...",
  "status": "pending",
  "amount": 100,
  "crypto_amount": 0.05,
  "wallet_address": "0xA1b2C3d4E5f6A7b8C9d0E1F2a3b4c5d6e7f8a9b"
}
```

### Check Payment Status
```bash
curl http://localhost:8000/api/payment-status/550e8400-e29b-41d4-a716-446655440000
```

Response:
```json
{
  "payment_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "completed",
  "provider": "stripe",
  "amount_fiat": 100,
  "amount_crypto": 0.05,
  "crypto_currency": "ETH",
  "wallet_address": "0xA1b2C3d4E5f6A7b8C9d0E1F2a3b4c5d6e7f8a9b",
  "created_at": "2026-05-05T12:00:00Z",
  "completed_at": "2026-05-05T12:05:00Z"
}
```

---

## Webhook Handling

### Stripe Sends
```json
{
  "id": "evt_1234567890",
  "type": "checkout.session.completed",
  "data": {
    "object": {
      "id": "cs_live_...",
      "client_reference_id": "550e8400-e29b-41d4-a716-446655440000",
      "payment_intent": "pi_1234567890",
      "status": "complete"
    }
  }
}
```

### Server Response
1. Verifies Stripe signature
2. Extracts `payment_id` from `client_reference_id`
3. Updates payment status to `completed`
4. Fires **merchant webhook** (if configured)
5. **Sends Telegram/WhatsApp notification**

---

## Production Checklist

- [ ] Get live Stripe keys from dashboard
- [ ] Run `activate_gateways.py` and select "stripe"
- [ ] Set `STRIPE_ENV=production` in `.env`
- [ ] Configure webhook endpoint in Stripe Dashboard
- [ ] Deploy to live server (set `BASE_URL` env var)
- [ ] Test with live customer
- [ ] Monitor webhook logs: `tail -f /var/log/beastpay/webhooks.log`
- [ ] Set up Telegram notifications (optional)

---

## Security

### Encryption
- API keys stored **AES-256-GCM encrypted** in database
- `CREDENTIAL_ENCRYPTION_KEY` required in `.env`

### Signature Verification
- All Stripe webhooks verified via HMAC-SHA256
- Timestamp validation (5-min tolerance)
- Prevents webhook replay attacks

### Risk Scoring
- Merchant credibility checked before checkout
- Risk score 0-100 (lower = safer)
- Threshold: reject if risk > 85

---

## Files & Structure

```
payment-gateway/
├── providers/
│   ├── stripe.py              # Stripe provider class
│   ├── metamask.py            # MetaMask wallet bridge
│   ├── transak.py             # Fiat-to-crypto ramp
│   └── __init__.py            # Provider factory
├── server.py                  # FastAPI routes (checkout, webhooks)
├── database.py                # SQLite schema
├── config.py                  # Config variables (loads from .env)
├── activate_gateways.py       # Multi-gateway activation script
├── .env                       # API keys (STRIPE_SECRET_KEY, etc)
└── payments.db                # SQLite database
```

---

## Troubleshooting

### "STRIPE_SECRET_KEY not configured"
→ Run `activate_gateways.py` and provide your keys

### "invalid_stripe_signature"
→ Verify webhook signing secret matches Stripe Dashboard

### "Stripe API error: Resource not found"
→ Check `BASE_URL` is correct (used in success_url/cancel_url)

### Webhook not firing
→ Check Stripe Dashboard → **Developers** → **Webhooks** → event delivery logs

---

## Next Steps

1. **Activate Stripe** using `activate_gateways.py`
2. **Test checkout** with test card (`4242 4242 4242 4242`)
3. **Monitor webhook logs** for payment status updates
4. **Configure merchant webhook** to receive payment notifications
5. **Deploy to production** when ready

Need help? Check `/home/kali/payment-gateway/GATEWAY_ACTIVATION_GUIDE.md`

# BeastPay LocalHost Complete Reference

## 🚀 Startup Commands

### 1. Navigate to Project
```bash
cd /home/kali/payment-gateway
```

### 2. Activate Sandbox Gateways (First Time Only)
```bash
python3 activate_sandbox_gateways.py
```

### 3. Start Server
```bash
source .env && python3 -m uvicorn server:app --host 0.0.0.0 --port 8000
```

**Alternative (with auto-reload):**
```bash
source .env && python3 -m uvicorn server:app --host 0.0.0.0 --port 8000 --reload
```

**Or directly:**
```bash
python3 server.py
```

### 4. Kill Process If Port Stuck
```bash
kill -9 $(lsof -t -i:8000)
```

---

## 🌐 LocalHost Endpoints

### Admin & Documentation
| URL | Purpose |
|-----|---------|
| `http://localhost:8000/` | Root health check |
| `http://localhost:8000/health` | Server health status |
| `http://localhost:8000/admin` | Admin Dashboard |
| `http://localhost:8000/docs` | Swagger API Documentation |
| `http://localhost:8000/redoc` | ReDoc API Documentation |

### Payment Entry & Checkout
| URL | Purpose |
|-----|---------|
| `http://localhost:8000/card-entry` | Card Entry Form (Lockbox) |
| `http://localhost:8000/card-entry?amount=100&currency=USD&crypto=USDT` | Card Entry with Parameters |
| `http://localhost:8000/buy` | Transak Checkout Page |
| `http://localhost:8000/lockbox/payment?card_id=YOUR_CARD_ID` | Saved Card Payment |

### API Endpoints
| URL | Method | Purpose |
|-----|--------|---------|
| `/api/checkout/methods` | GET | List all payment methods |
| `/api/checkout/initiate-comprehensive` | POST | Initiate payment with routing |
| `/api/gateway/status` | GET | Health check all gateways |
| `/api/payment/{payment_id}/status` | GET | Check payment status |
| `/api/lockbox/store-card` | POST | Save card to secure vault |
| `/api/lockbox/cards` | GET | List saved cards (masked) |
| `/api/merchant/{merchant_id}/profile` | GET | Get merchant profile |
| `/api/metamask/quote` | POST | Get real-time MetaMask quote |
| `/api/metamask/currencies` | GET | Get supported currencies |

### Webhook Receivers
| URL | Provider |
|-----|----------|
| `/webhooks/transak` | Transak |
| `/webhooks/guardarian` | Guardarian |
| `/webhooks/ziina` | Ziina |
| `/webhooks/moonpay` | MoonPay |
| `/webhooks/nowpayments` | NOWPayments |
| `/webhooks/stripe` | Stripe |

---

## 🔐 Gateway Activation

### Sandbox Gateways (Test Credentials)
```bash
cd /home/kali/payment-gateway
python3 activate_sandbox_gateways.py
```
**Pre-fills:** Transak, Guardarian, Ziina, MoonPay, NOWPayments with test keys

### Production Gateways (Live Credentials)
```bash
cd /home/kali/payment-gateway
python3 activate_gateways.py
```
**Prompts for:** Real API keys from each gateway dashboard

### Stripe Activation (One-time)
```bash
cd /home/kali/payment-gateway
python3 stripe_activate.py SK_LIVE_KEY PK_LIVE_KEY WHSEC_KEY
```

---

## 📱 Quick Test Commands

### 1. Check Server Health
```bash
curl http://localhost:8000/health | jq .
```

### 2. List All Payment Methods
```bash
curl http://localhost:8000/api/checkout/methods | jq .
```

### 3. Check Gateway Status
```bash
curl http://localhost:8000/api/gateway/status | jq .
```

### 4. Initiate Stripe Checkout
```bash
curl -X POST http://localhost:8000/api/checkout/initiate-comprehensive \
  -H "Content-Type: application/json" \
  -d '{
    "merchant_id": "test-merchant-a5686a67",
    "amount_fiat": 100,
    "fiat_currency": "USD",
    "crypto_currency": "USDT",
    "customer_email": "test@example.com",
    "checkout_method": "stripe"
  }' | jq .
```

### 5. Initiate Transak Checkout
```bash
curl -X POST http://localhost:8000/api/checkout/initiate-comprehensive \
  -H "Content-Type: application/json" \
  -d '{
    "merchant_id": "test-merchant-a5686a67",
    "amount_fiat": 50,
    "fiat_currency": "EUR",
    "crypto_currency": "BTC",
    "customer_email": "test@example.com",
    "checkout_method": "transak"
  }' | jq .
```

### 6. Initiate Guardarian Checkout
```bash
curl -X POST http://localhost:8000/api/checkout/initiate-comprehensive \
  -H "Content-Type: application/json" \
  -d '{
    "merchant_id": "test-merchant-a5686a67",
    "amount_fiat": 75,
    "fiat_currency": "GBP",
    "crypto_currency": "ETH",
    "customer_email": "test@example.com",
    "checkout_method": "guardarian"
  }' | jq .
```

### 7. Initiate Ziina (AED) Checkout
```bash
curl -X POST http://localhost:8000/api/checkout/initiate-comprehensive \
  -H "Content-Type: application/json" \
  -d '{
    "merchant_id": "test-merchant-a5686a67",
    "amount_fiat": 365,
    "fiat_currency": "AED",
    "crypto_currency": "USDT",
    "customer_email": "test@example.com",
    "checkout_method": "ziina"
  }' | jq .
```

### 8. Initiate MoonPay Checkout
```bash
curl -X POST http://localhost:8000/api/checkout/initiate-comprehensive \
  -H "Content-Type: application/json" \
  -d '{
    "merchant_id": "test-merchant-a5686a67",
    "amount_fiat": 200,
    "fiat_currency": "USD",
    "crypto_currency": "USDT",
    "customer_email": "test@example.com",
    "checkout_method": "moonpay"
  }' | jq .
```

### 9. Initiate Lockbox (Saved Card) Checkout
```bash
curl -X POST http://localhost:8000/api/checkout/initiate-comprehensive \
  -H "Content-Type: application/json" \
  -d '{
    "merchant_id": "test-merchant-a5686a67",
    "amount_fiat": 100,
    "fiat_currency": "USD",
    "crypto_currency": "USDT",
    "customer_email": "test@example.com",
    "checkout_method": "lockbox",
    "card_id": "YOUR_CARD_ID"
  }' | jq .
```

### 10. Initiate Crypto Direct (No KYC)
```bash
curl -X POST http://localhost:8000/api/checkout/initiate-comprehensive \
  -H "Content-Type: application/json" \
  -d '{
    "merchant_id": "test-merchant-a5686a67",
    "amount_fiat": 100,
    "fiat_currency": "USD",
    "crypto_currency": "BTC",
    "customer_email": "test@example.com",
    "checkout_method": "crypto"
  }' | jq .
```

### 11. Initiate MetaMask Checkout
```bash
curl -X POST http://localhost:8000/api/checkout/initiate-comprehensive \
  -H "Content-Type: application/json" \
  -d '{
    "merchant_id": "test-merchant-a5686a67",
    "amount_fiat": 100,
    "fiat_currency": "USD",
    "crypto_currency": "USDT",
    "customer_email": "test@example.com",
    "checkout_method": "metamask",
    "wallet_address": "0x742d35Cc6634C0532925a3b844Bc59e5c1d61e9d"
  }' | jq .
```

### 12. Get MetaMask Quote
```bash
curl -X POST http://localhost:8000/api/metamask/quote \
  -H "Content-Type: application/json" \
  -d '{
    "amount_fiat": 100,
    "fiat_currency": "USD",
    "crypto_currency": "USDT"
  }' | jq .
```

### 13. Check Payment Status
```bash
curl http://localhost:8000/api/payment/PAYMENT_ID/status | jq .
```

### 14. Store Card to Lockbox
```bash
curl -X POST http://localhost:8000/api/lockbox/store-card \
  -H "Content-Type: application/json" \
  -d '{
    "cardholder_name": "John Doe",
    "card_number": "4532148803436467",
    "expiry_date": "12/25",
    "cvv": "123",
    "billing_street": "123 Main St",
    "billing_city": "Dubai",
    "billing_state": "DXB",
    "billing_zip": "00000"
  }' | jq .
```

### 15. List Saved Cards
```bash
curl http://localhost:8000/api/lockbox/cards | jq .
```

---

## 📊 Test Card Details

**Number:** `4532 1488 0343 6467`  
**Name:** Any (e.g., John Doe)  
**Expiry:** Any future date (e.g., 12/25)  
**CVV:** Any 3 digits (e.g., 123)  
**Address:** Any valid format  

---

## 🔄 Full Development Workflow

### First Time Setup
```bash
# 1. Navigate
cd /home/kali/payment-gateway

# 2. Activate sandbox gateways
python3 activate_sandbox_gateways.py

# 3. Start server
source .env && python3 -m uvicorn server:app --host 0.0.0.0 --port 8000

# 4. Open browser
# Admin: http://localhost:8000/admin
# Card Entry: http://localhost:8000/card-entry
# API Docs: http://localhost:8000/docs
```

### Testing Workflow
```bash
# 1. Save test card at /card-entry
# 2. Get card_id from response
# 3. Use card_id in lockbox checkout

# Or test directly with curl:
curl -X POST http://localhost:8000/api/checkout/initiate-comprehensive \
  -H "Content-Type: application/json" \
  -d '{"merchant_id":"test-merchant-a5686a67","amount_fiat":100,"fiat_currency":"USD","crypto_currency":"USDT","customer_email":"test@example.com","checkout_method":"stripe"}' | jq .
```

### Production Transition
```bash
# 1. Get real API keys from each gateway dashboard
# 2. Run interactive activation
python3 activate_gateways.py

# 3. Update BASE_URL in .env to public domain
# 4. Register webhooks in each gateway dashboard
# 5. Test with real payments
```

---

## 🛠️ Database

**Location:** `/home/kali/payment-gateway/payments.db`

**Key Tables:**
- `merchants` — API keys, webhook URLs
- `payments` — Payment records, status, provider
- `lockbox_transactions` — Encrypted card storage
- `gateway_credentials` — Encrypted API keys
- `gateway_registrations` — Provider activation status
- `merchant_profiles` — Onboarding state, risk scores
- `kyc_records` — KYC tier tracking

---

## 📝 Environment Variables

**Key vars in `.env`:**
```
STRIPE_SECRET_KEY=sk_live_...
STRIPE_PUBLISHABLE_KEY=pk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
STRIPE_ENV=live

TRANSAK_API_KEY=...
TRANSAK_SECRET=...
TRANSAK_ENV=staging

GUARDARIAN_API_KEY=...
GUARDARIAN_ENV=sandbox

ZIINA_API_TOKEN=...
ZIINA_ENV=sandbox

MOONPAY_API_KEY=...
MOONPAY_ENV=sandbox

NOWPAYMENTS_API_KEY=...
NOWPAYMENTS_ENV=sandbox

BASE_URL=http://localhost:8000
CREDENTIAL_ENCRYPTION_KEY=YOUR_64_HEX_KEY
ADMIN_API_KEY=YOUR_ADMIN_KEY
```

---

## 🔍 Debugging

### View Server Logs (Real-time)
```bash
# Terminal stays open, shows logs
source .env && python3 -m uvicorn server:app --host 0.0.0.0 --port 8000
```

### Check Database Directly
```bash
sqlite3 /home/kali/payment-gateway/payments.db
# Then: SELECT * FROM payments;
```

### Test Payment Status
```bash
curl http://localhost:8000/api/payment/PAYMENT_ID/status | jq .
```

### Verify Credentials Encrypted
```bash
sqlite3 /home/kali/payment-gateway/payments.db
# SELECT id, gateway_name, encrypted_api_key FROM gateway_credentials;
```

---

**Last Updated:** May 4, 2026  
**Status:** ✅ Ready for development & testing

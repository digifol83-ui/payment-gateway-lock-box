# 🚀 BeastPay Local Sandbox Quick Start

Full payment gateway system with **7 payment methods**, **card entry UI**, and **5 sandbox gateways** ready to test.

---

## 📊 What's Running Now

✅ **Server:** http://localhost:8000  
✅ **Stripe:** LIVE (production keys configured)  
✅ **5 Sandbox Gateways:** Auto-activated for testing  
✅ **Card Entry Form:** Full UI at /card-entry  
✅ **Lockbox:** Encrypted card vault ready  

---

## 🎯 Try It Now (60 seconds)

**1. Open Card Entry Form:**
```
http://localhost:8000/card-entry?amount=100&currency=USD&crypto=USDT
```

**2. Enter Test Card:**
```
Name:     John Doe
Number:   4532 1488 0343 6467 (test card)
Expiry:   12/25
CVV:      123
Address:  123 Main St, Dubai, DXB, 00000
```

**3. Click "Save to Secure Vault"**
- Card encrypts with AES-256-GCM
- Returns card_id for future charging
- Redirects to payment interface

---

## 📱 Test All 7 Checkout Methods

### 1️⃣ Stripe Card (LIVE)
```bash
curl -X POST http://localhost:8000/api/checkout/initiate-comprehensive \
  -H "Content-Type: application/json" \
  -d '{"merchant_id":"test-merchant-a5686a67","amount_fiat":100,"fiat_currency":"USD","crypto_currency":"USDT","customer_email":"test@example.com","checkout_method":"stripe"}'
```

### 2️⃣ Transak (160+ countries, Sandbox)
```bash
curl -X POST http://localhost:8000/api/checkout/initiate-comprehensive \
  -H "Content-Type: application/json" \
  -d '{"merchant_id":"test-merchant-a5686a67","amount_fiat":50,"fiat_currency":"EUR","crypto_currency":"BTC","customer_email":"test@example.com","checkout_method":"transak"}'
```

### 3️⃣ Guardarian (170+ countries, instant, Sandbox)
```bash
curl -X POST http://localhost:8000/api/checkout/initiate-comprehensive \
  -H "Content-Type: application/json" \
  -d '{"merchant_id":"test-merchant-a5686a67","amount_fiat":75,"fiat_currency":"GBP","crypto_currency":"ETH","customer_email":"test@example.com","checkout_method":"guardarian"}'
```

### 4️⃣ Ziina AED (UAE Native, Sandbox)
```bash
curl -X POST http://localhost:8000/api/checkout/initiate-comprehensive \
  -H "Content-Type: application/json" \
  -d '{"merchant_id":"test-merchant-a5686a67","amount_fiat":365,"fiat_currency":"AED","crypto_currency":"USDT","customer_email":"test@example.com","checkout_method":"ziina"}'
```

### 5️⃣ Saved Card / Lockbox
Save card first at /card-entry, then:
```bash
curl -X POST http://localhost:8000/api/checkout/initiate-comprehensive \
  -H "Content-Type: application/json" \
  -d '{"merchant_id":"test-merchant-a5686a67","amount_fiat":100,"fiat_currency":"USD","crypto_currency":"USDT","customer_email":"test@example.com","checkout_method":"lockbox","card_id":"YOUR_CARD_ID"}'
```

### 6️⃣ MoonPay (160+ countries, Sandbox)
```bash
curl -X POST http://localhost:8000/api/checkout/initiate-comprehensive \
  -H "Content-Type: application/json" \
  -d '{"merchant_id":"test-merchant-a5686a67","amount_fiat":200,"fiat_currency":"USD","crypto_currency":"USDT","customer_email":"test@example.com","checkout_method":"moonpay"}'
```

### 7️⃣ Direct Crypto / No KYC
```bash
curl -X POST http://localhost:8000/api/checkout/initiate-comprehensive \
  -H "Content-Type: application/json" \
  -d '{"merchant_id":"test-merchant-a5686a67","amount_fiat":100,"fiat_currency":"USD","crypto_currency":"BTC","customer_email":"test@example.com","checkout_method":"crypto"}'
```

---

## 🎨 UI Endpoints

| URL | What It Does |
|-----|-------------|
| http://localhost:8000/admin | Admin Dashboard |
| http://localhost:8000/card-entry | Card Entry Form |
| http://localhost:8000/docs | API Documentation |
| http://localhost:8000/api/checkout/methods | List All Methods |

---

## 🔍 Check Payment Status

```bash
curl http://localhost:8000/api/payment/{payment_id}/status | jq .
```

---

## 📊 Gateway Matrix

| Provider | Type | Countries | Settlement | Mode |
|----------|------|-----------|-----------|------|
| Stripe | Card Hosted | Global | 1-3 days | **LIVE** |
| Transak | Fiat→Crypto | 160+ | 1-3 hrs | Sandbox |
| Guardarian | Fiat→Crypto | 170+ | 5-30 min | Sandbox |
| Ziina | AED Card | UAE | Instant | Sandbox |
| MoonPay | Fiat→Crypto | 160+ | 1-2 hrs | Sandbox |
| Lockbox | Vault Card | Global | Instant | Ready |
| Crypto | P2P Direct | Global | 5-30 min | Ready |

---

## 🔐 Test Card Details

**Card Number:** 4532 1488 0343 6467  
**Name:** Any  
**Expiry:** Any future date (12/25)  
**CVV:** Any 3 digits (123)  
**Address:** Any valid format  

---

## ✅ What's Ready Now

✅ Stripe LIVE integration with webhook  
✅ 5 Sandbox gateways activated  
✅ Card entry UI with encryption  
✅ Lockbox encrypted storage  
✅ Multi-gateway routing  
✅ Credibility/risk scoring  
✅ Payment status tracking  
✅ Telegram notifications (if configured)  

---

## 🚀 Production Upgrade

To switch to live keys:

```bash
python3 activate_gateways.py

# Follow prompts to enter real API keys for:
# - Transak (get from dashboard.transak.com)
# - Guardarian (get from partner.guardarian.com)
# - Ziina (get from dashboard.ziina.io)
# - MoonPay (get from dashboard.moonpay.com)
# - NOWPayments (get from nowpayments.io)

source .env && python3 -m uvicorn server:app --host 0.0.0.0 --port 8000
```

---

**Last Updated:** May 4, 2026  
**Status:** ✅ Ready for development & testing

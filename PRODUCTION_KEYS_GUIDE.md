# Production API Keys Guide

Get your live API credentials from each gateway. Copy the keys exactly (no extra spaces).

---

## 1️⃣ TRANSAK

**Dashboard:** https://dashboard.transak.com  
**Region Support:** UK, EU, US, India, Australia  
**Settlement:** 1-3 hours

### Get Keys:
1. Log in to https://dashboard.transak.com
2. Go to **Settings → API Keys**
3. Copy these 3 values:
   - `TRANSAK_API_KEY` (starts with `sk_live_` or similar)
   - `TRANSAK_SECRET` (secret key)
   - `TRANSAK_ACCESS_TOKEN` (access token)
4. Set **Environment:** `production`

---

## 2️⃣ GUARDARIAN

**Dashboard:** https://partner.guardarian.com  
**Region Support:** 170+ countries  
**Settlement:** 5-30 minutes

### Get Keys:
1. Log in to https://partner.guardarian.com
2. Go to **Settings → API**
3. Copy:
   - `GUARDARIAN_API_KEY` (partner API key)
4. Set **Environment:** `production`

---

## 3️⃣ ZIINA

**Dashboard:** https://dashboard.ziina.io  
**Region Support:** UAE (AED native)  
**Settlement:** Instant  

### Get Keys:
1. Log in to https://dashboard.ziina.io
2. Go to **Developers → API Keys**
3. Copy these 2 values:
   - `ZIINA_API_TOKEN` (API token)
   - `ZIINA_WEBHOOK_SECRET` (webhook secret)
4. Set **Environment:** `production`

---

## 4️⃣ MOONPAY

**Dashboard:** https://dashboard.moonpay.com  
**Region Support:** 160+ countries  
**Settlement:** 1-2 hours

### Get Keys:
1. Log in to https://dashboard.moonpay.com
2. Go to **Settings → API Keys**
3. Copy these 2 values:
   - `MOONPAY_API_KEY` (public key)
   - `MOONPAY_SECRET` (secret key)
4. Set **Environment:** `production`

---

## 5️⃣ NOWPAYMENTS

**Dashboard:** https://nowpayments.io  
**Region Support:** Global (no KYC)  
**Settlement:** 5-30 minutes

### Get Keys:
1. Log in to https://nowpayments.io
2. Go to **Settings → API**
3. Copy:
   - `NOWPAYMENTS_API_KEY` (API key)
4. Set **Environment:** `production`

---

## 6️⃣ METAMASK

**Dashboard:** https://metamask.io/partners  
**Region Support:** 160+ countries  
**Settlement:** 5-10 minutes (direct to wallet)

### Get Keys:
1. Go to https://metamask.io/partners
2. Sign up as fiat-to-crypto provider
3. Request **Partner API credentials**
4. You'll receive:
   - `METAMASK_API_KEY` (partner ID)
   - `METAMASK_SECRET` (secret key)
   - `METAMASK_WEBHOOK_SECRET` (webhook verification)
5. Set **Environment:** `production`

---

## 📋 Quick Checklist

Before running activation:

- [ ] Transak: 3 keys + environment
- [ ] Guardarian: 1 key + environment
- [ ] Ziina: 2 keys + environment
- [ ] MoonPay: 2 keys + environment
- [ ] NOWPayments: 1 key + environment
- [ ] MetaMask: 3 keys + environment

---

## 🚀 Activation Command

Once you have all keys ready:

```bash
cd /home/kali/payment-gateway
python3 activate_gateways.py
```

The script will:
1. **Prompt you for each gateway** (one at a time)
2. **Ask for environment** (type: `production`)
3. **Encrypt credentials** in the database
4. **Update .env file**
5. **Register with gateway_registrations table**

Then restart the server:

```bash
source .env && python3 -m uvicorn server:app --host 0.0.0.0 --port 8000
```

---

## ✅ Verify Activation

After running activation:

```bash
# Check server health
curl http://localhost:8000/health | jq .

# Check all gateways registered
curl http://localhost:8000/api/gateway/status | jq .

# List available checkout methods
curl http://localhost:8000/api/checkout/methods | jq .
```

---

**Status:** Ready to activate production gateways

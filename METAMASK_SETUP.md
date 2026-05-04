# MetaMask Fiat-to-Crypto Integration

BeastPay now supports **native MetaMask widget** for fiat-to-crypto onramps.

---

## 🎯 What MetaMask Provides

✅ **No KYC** up to $1,000  
✅ **160+ countries** supported  
✅ **Instant settlement** to wallet (5-10 min)  
✅ **Native MetaMask UI** (familiar to users)  
✅ **Multi-currency** support (USD, EUR, GBP, AUD, CAD, AED)  
✅ **Real-time quotes** & FX rates  

---

## 📋 Get MetaMask Partner Keys

### 1. Register as MetaMask Partner
1. Go to **https://metamask.io/partners**
2. Sign up as a fiat-to-crypto provider
3. Request **Partner API credentials**

### 2. You'll Receive:
- `METAMASK_API_KEY` (partner ID / auth token)
- `METAMASK_SECRET` (webhook secret)
- `METAMASK_WEBHOOK_SECRET` (for signature verification)

### 3. Add to .env:
```bash
METAMASK_API_KEY=your_partner_key_here
METAMASK_SECRET=your_secret_key_here
METAMASK_WEBHOOK_SECRET=your_webhook_secret_here
METAMASK_ENV=production
```

---

## 🚀 Activate MetaMask

```bash
cd /home/kali/payment-gateway

# Option 1: Interactive (will prompt for keys)
python3 activate_gateways.py
# Select: metamask
# Enter METAMASK_API_KEY
# Enter METAMASK_SECRET
# Set environment: production

# Option 2: Add to .env manually, then encrypt in DB:
python3 -c "
import sqlite3, uuid, json
from datetime import datetime
from verification.encryption import encrypt_credential
from config import CREDENTIAL_ENCRYPTION_KEY

PROFILE_ID = 'fd8179d9-a881-47d4-9a14-3438527ea6a7'
enc_key = CREDENTIAL_ENCRYPTION_KEY
now = datetime.utcnow().isoformat()

enc_creds = {
    'METAMASK_API_KEY': encrypt_credential('YOUR_KEY', enc_key),
    'METAMASK_SECRET': encrypt_credential('YOUR_SECRET', enc_key),
}

conn = sqlite3.connect('payments.db')
cred_id = str(uuid.uuid4())
conn.execute('''INSERT INTO gateway_credentials
   (id, merchant_profile_id, gateway_name,
    encrypted_api_key, encrypted_secret, additional_data, is_active, created_at, updated_at)
   VALUES (?,?,?,?,?,?,1,?,?)''',
  (cred_id, PROFILE_ID, 'metamask',
   json.dumps(enc_creds), json.dumps(enc_creds),
   json.dumps({'env': 'production'}), now, now))
conn.commit()
conn.close()
print('✅ MetaMask credentials encrypted and stored')
"

# Restart server
source .env && python3 -m uvicorn server:app --host 0.0.0.0 --port 8000
```

---

## 💻 API Usage

### 1. Initiate MetaMask Checkout
```bash
curl -X POST http://localhost:8000/api/checkout/initiate-comprehensive \
  -H "Content-Type: application/json" \
  -d '{
    "merchant_id": "test-merchant-a5686a67",
    "amount_fiat": 100,
    "fiat_currency": "USD",
    "crypto_currency": "USDT",
    "customer_email": "user@example.com",
    "checkout_method": "metamask",
    "wallet_address": "0x742d35Cc6634C0532925a3b844Bc59e5c1d61e9d"
  }' | jq .
```

**Response:**
```json
{
  "order_id": "mm_order_abc123",
  "widget_url": "https://buy.metamask.io?order_id=mm_order_abc123",
  "checkout_url": "https://buy.metamask.io?order_id=mm_order_abc123",
  "status": "pending",
  "created_at": "2026-05-04T12:00:00Z",
  "expires_at": "2026-05-04T12:30:00Z"
}
```

### 2. Get Real-Time Quote
```bash
curl -X POST http://localhost:8000/api/metamask/quote \
  -H "Content-Type: application/json" \
  -d '{
    "amount_fiat": 100,
    "fiat_currency": "USD",
    "crypto_currency": "USDT"
  }' | jq .
```

**Response:**
```json
{
  "fiat_amount": 100,
  "crypto_amount": 99.50,
  "rate": 0.9950,
  "fee_fiat": 2.5,
  "fee_percent": 2.5,
  "total_fiat": 102.50,
  "valid_until": "2026-05-04T12:05:00Z"
}
```

### 3. Check Order Status
```bash
curl http://localhost:8000/api/payment/{payment_id}/status | jq .
```

---

## 🔗 Webhook Setup

### Register Webhook in MetaMask Partner Dashboard:

1. Go to **https://metamask.io/partners**
2. Navigate to **Settings → Webhooks**
3. Add webhook URL:
   ```
   https://your-domain.com/webhooks/metamask
   ```
4. Events to subscribe to:
   - `order.completed`
   - `order.failed`
   - `order.expired`

### Webhook Payload Example:
```json
{
  "order_id": "mm_order_abc123",
  "event_type": "completed",
  "fiat_amount": 100,
  "crypto_amount": 0.05,
  "transaction_hash": "0xabc123...",
  "destination_wallet": "0x742d35Cc6634C0532925a3b844Bc59e5c1d61e9d",
  "timestamp": "2026-05-04T12:05:00Z"
}
```

---

## 🧪 Test MetaMask Fiat-to-Crypto

### 1. Get a Wallet Address
```bash
# If you have MetaMask browser extension:
# Copy your wallet address: 0x742d35Cc...

# Or generate a test wallet:
python3 -c "from eth_account import Account; acc = Account.create(); print(acc.address)"
```

### 2. Initiate Order
```bash
WALLET="0x742d35Cc6634C0532925a3b844Bc59e5c1d61e9d"

curl -X POST http://localhost:8000/api/checkout/initiate-comprehensive \
  -H "Content-Type: application/json" \
  -d "{
    \"merchant_id\": \"test-merchant-a5686a67\",
    \"amount_fiat\": 50,
    \"fiat_currency\": \"USD\",
    \"crypto_currency\": \"USDT\",
    \"customer_email\": \"test@example.com\",
    \"checkout_method\": \"metamask\",
    \"wallet_address\": \"$WALLET\"
  }" | jq '.widget_url'
```

### 3. Open Widget URL
```bash
# Copy the widget_url from response and open in browser:
https://buy.metamask.io?order_id=mm_order_abc123
```

### 4. Complete Order
- User goes through MetaMask's fiat-to-crypto flow
- Funds are sent directly to wallet address
- Webhook notifies your server
- Payment status updates to `completed`

---

## 📊 Supported Cryptocurrencies

Common: ETH, BTC, USDT, USDC, DAI, WETH  
Full list: Query `/api/metamask/currencies` endpoint

---

## 🔐 Security Notes

- **API Key**: Keep `METAMASK_API_KEY` secret (never expose in frontend)
- **Webhooks**: Verify signature using `METAMASK_WEBHOOK_SECRET`
- **Wallet Address**: User must provide valid Ethereum address
- **No KYC**: Under $1,000 per transaction (MetaMask policy)

---

## 📞 Support

- MetaMask Docs: https://docs.metamask.io
- Partner Dashboard: https://metamask.io/partners
- Technical Support: partners@metamask.io

---

**Status:** Ready for production  
**Fee:** 2.5% + network gas  
**Settlement:** 5-10 minutes to wallet

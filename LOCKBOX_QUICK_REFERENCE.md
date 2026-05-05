# Lockbox-to-Wallet: Quick Reference Guide

## API Endpoints

### 1. Create Payment (Trigger Lockbox Flow)

```bash
curl -X POST http://localhost:8000/api/payments \
  -H "X-Api-Key: your-admin-key" \
  -H "Content-Type: application/json" \
  -d '{
    "merchant_id": "merc_123",
    "fiat_amount": 1000,
    "fiat_currency": "USD",
    "crypto_currency": "USDT",
    "wallet_address": "0x742d35Cc6634C0532925a3b844Bc9e7595f1234",
    "customer_email": "john@example.com",
    "customer_name": "John Smith",
    "provider_type": "fiat→crypto"
  }'
```

**Response:**
```json
{
  "status": "success",
  "result": {
    "payment_id": "fb7a82e1-6a3f-4c2d-9e1a-8f7b3c5d2e1a",
    "selected_provider": {
      "name": "transak",
      "score": 85,
      "verified": true,
      "fee_percent": 2.0,
      "settlement_hours": 24,
      "spot_credit": false
    },
    "calculation": {
      "fiat_input": 1000,
      "total_fees": 30.00,
      "amount_after_fees": 970.00
    },
    "status": "pending"
  }
}
```

### 2. Lock Exchange Rate

```bash
curl -X POST http://localhost:8000/api/rates/lock \
  -H "X-Api-Key: your-admin-key" \
  -H "Content-Type: application/json" \
  -d '{
    "payment_id": "fb7a82e1-6a3f-4c2d-9e1a-8f7b3c5d2e1a",
    "from_ticker": "USD",
    "to_ticker": "USDT",
    "amount": 1000
  }'
```

**Response:**
```json
{
  "status": "success",
  "result": {
    "rate_lock_id": "lock_abc123...",
    "locked_rate": 1.0001,
    "amount_to": 999.90,
    "lock_duration_min": 15,
    "expires_at": "2026-05-03T14:37:35Z"
  }
}
```

### 3. Get Payment Status

```bash
curl -X GET "http://localhost:8000/api/payments/fb7a82e1-6a3f-4c2d-9e1a-8f7b3c5d2e1a" \
  -H "X-Api-Key: your-admin-key"
```

### 4. Deliver Merchant Webhook (Manual)

```bash
curl -X POST http://localhost:8000/api/webhooks/deliver \
  -H "X-Api-Key: your-admin-key" \
  -H "Content-Type: application/json" \
  -d '{
    "merchant_id": "merc_123",
    "payment_id": "fb7a82e1-6a3f-4c2d-9e1a-8f7b3c5d2e1a",
    "event_type": "payment.completed",
    "event_data": {
      "status": "completed",
      "crypto_amount": 999.5
    }
  }'
```

### 5. Receive Provider Webhook (Transak)

**Endpoint:** `POST /webhooks/transak`

Provider sends:
```json
{
  "event": "ORDER_COMPLETED",
  "data": {
    "id": "transak_order_12345",
    "partnerOrderId": "fb7a82e1-...",
    "status": "COMPLETED",
    "cryptoAmount": "999.5",
    "cryptoCurrency": "USDT",
    "walletAddress": "0x742d35Cc...",
    "timestamp": "2026-05-03T14:25:00Z"
  }
}
```

---

## Database Queries

### 1. View Payment Record

```sql
SELECT 
  payment_id,
  merchant_id,
  status,
  fiat_amount,
  fiat_currency,
  crypto_currency,
  crypto_amount,
  wallet_address,
  provider,
  provider_tx_id,
  exchange_rate,
  fee_amount,
  created_at,
  updated_at
FROM payments
WHERE payment_id = 'fb7a82e1-6a3f-4c2d-9e1a-8f7b3c5d2e1a';
```

### 2. View Lockbox Transaction

```sql
SELECT 
  id,
  masked_card_number,
  expiry_date,
  cardholder_name,
  validation_status,
  confidence_scores,
  anomalies,
  ai_reasoning,
  created_at
FROM lockbox_transactions
WHERE id = 12345;
```

### 3. Check KYC Record

```sql
SELECT 
  id,
  payment_id,
  customer_email,
  kyc_status,
  review_answer,
  created_at
FROM kyc_records
WHERE payment_id = 'fb7a82e1-6a3f-4c2d-9e1a-8f7b3c5d2e1a';
```

### 4. View Webhook Delivery Logs

```sql
SELECT 
  webhook_id,
  merchant_id,
  payment_id,
  webhook_url,
  attempt_number,
  http_status,
  latency_ms,
  error_message,
  created_at
FROM webhook_delivery_logs
WHERE payment_id = 'fb7a82e1-6a3f-4c2d-9e1a-8f7b3c5d2e1a'
ORDER BY created_at DESC;
```

### 5. Get Audit Trail

```sql
SELECT 
  timestamp,
  actor,
  action,
  resource_type,
  resource_id,
  changes,
  result,
  ip_address
FROM audit_logs
WHERE resource_id = 'fb7a82e1-6a3f-4c2d-9e1a-8f7b3c5d2e1a'
ORDER BY timestamp ASC;
```

### 6. List Recent Payments (Last 24 Hours)

```sql
SELECT 
  payment_id,
  merchant_id,
  fiat_amount,
  crypto_currency,
  status,
  provider,
  created_at
FROM payments
WHERE created_at > datetime('now', '-24 hours')
ORDER BY created_at DESC;
```

### 7. Payment Status Summary

```sql
SELECT 
  status,
  COUNT(*) as count,
  ROUND(AVG(fiat_amount), 2) as avg_amount,
  SUM(fiat_amount) as total_amount
FROM payments
WHERE created_at > datetime('now', '-7 days')
GROUP BY status;
```

### 8. Provider Performance

```sql
SELECT 
  provider,
  COUNT(*) as transaction_count,
  ROUND(AVG(fiat_amount), 2) as avg_amount,
  ROUND(AVG(fee_amount), 2) as avg_fee,
  ROUND(100.0 * COUNT(CASE WHEN status='completed' THEN 1 END) / COUNT(*), 1) as completion_rate
FROM payments
WHERE created_at > datetime('now', '-7 days')
GROUP BY provider;
```

---

## Status Flow Examples

### Successful Payment (Happy Path)

```
14:22:35  payment.created         (lockbox approved)
14:22:45  exchange_rate.locked    (USD/USDT = 1.0001)
14:25:00  payment.processing      (Transak webhook received)
14:26:00  payment.completed       (Crypto in wallet)
14:27:30  webhook.delivered       (Merchant notified)
          ✓ PAYMENT COMPLETE
```

### Webhook Delivery Failure (Retry Path)

```
14:26:00  payment.completed       (Crypto in wallet)
14:26:05  webhook.deliver         (Attempt 1) → FAILED (timeout)
14:26:06  webhook.retry           (Attempt 2) → FAILED
14:26:08  webhook.retry           (Attempt 3) → FAILED
14:26:13  webhook.retry           (Attempt 4) → FAILED
14:26:23  webhook.retry           (Attempt 5) → FAILED
14:26:24  ops_alert               (Telegram notification)
          👨‍💼 Manual intervention required
```

---

## Testing Scenarios

### Test 1: Small Amount (No KYC)

```json
{
  "fiat_amount": 250,
  "fiat_currency": "USD",
  "crypto_currency": "USDT",
  "provider_type": "fiat→crypto"
}
```

Expected:
- KYC Tier: `free`
- Provider: Transak (if live) or MoonPay
- No Sumsub verification

### Test 2: Medium Amount (Email KYC)

```json
{
  "fiat_amount": 2000,
  "fiat_currency": "USD",
  "crypto_currency": "USDT",
  "provider_type": "fiat→crypto"
}
```

Expected:
- KYC Tier: `email`
- Email verification required
- Provider: Transak (score 85+)
- Settlement: 24 hours

### Test 3: Crypto-Direct Route

```json
{
  "fiat_amount": 500,
  "fiat_currency": "USD",
  "crypto_currency": "BTC",
  "provider_type": "crypto-direct"
}
```

Expected:
- Provider: CoinRemitter or Plisio
- Customer sends BTC to invoice address
- Settlement: < 1 hour (spot credit)

### Test 4: High Amount (Full KYC)

```json
{
  "fiat_amount": 10000,
  "fiat_currency": "USD",
  "crypto_currency": "USDT",
  "provider_type": "fiat→crypto"
}
```

Expected:
- KYC Tier: `full`
- Sumsub ID verification required
- Settlement: 2-3 days
- Risk scoring: Auto-verify or manual review

---

## Debugging Tips

### Check if Lockbox Validation Passed

```sql
SELECT validation_status, confidence_scores, ai_reasoning
FROM lockbox_transactions
WHERE created_at > datetime('now', '-1 hour')
ORDER BY created_at DESC
LIMIT 10;
```

### Find Stuck Payments (Still Pending)

```sql
SELECT payment_id, merchant_id, provider, status, updated_at
FROM payments
WHERE status = 'pending'
AND updated_at < datetime('now', '-1 hour')
ORDER BY updated_at;
```

### Identify Failed Webhooks

```sql
SELECT merchant_id, payment_id, attempt_number, http_status, error_message, created_at
FROM webhook_delivery_logs
WHERE http_status NOT IN (200, 201, 204)
ORDER BY created_at DESC
LIMIT 20;
```

### Check Exchange Rate Locks

```sql
SELECT 
  payment_id, 
  exchange_rate, 
  crypto_amount,
  CASE WHEN rate_locked_until > datetime('now') THEN '✓ VALID' ELSE '✗ EXPIRED' END as lock_status
FROM payments
WHERE rate_locked_until IS NOT NULL
ORDER BY rate_locked_until DESC;
```

---

## Common Issues & Solutions

### Issue 1: Provider Not Available

**Error:** `NO_VIABLE_PROVIDER: Amount $X exceeds free tier limit`

**Cause:** Amount > $500 but no KYC configured

**Solution:** 
- Request KYC tier (email or full)
- Or lower amount to < $500

### Issue 2: Rate Lock Expired

**Error:** `RATE_LOCK_EXPIRED: Lock expired at 14:37:35Z`

**Cause:** Customer waited > 15 minutes before checkout

**Solution:**
- Rate is auto-locked when provider confirms
- No action needed (new rate will be locked)

### Issue 3: Webhook Not Delivering

**Error:** `WEBHOOK_DELIVERY_FAILED: Connection refused (after 5 attempts)`

**Cause:** Merchant webhook URL is unreachable

**Solution:**
- Verify merchant webhook URL in database
- Check if merchant server is running
- Whitelist BeastPay IPs if behind firewall
- Use manual retry endpoint after fixing

### Issue 4: Crypto Not Arriving

**Status:** `processing` for > 30 minutes

**Cause:** Blockchain congestion or provider delay

**Solution:**
- Check on-chain: etherscan.io (provide TX hash)
- Check provider dashboard (Transak/CoinRemitter)
- Wait for network confirmation
- If > 1 hour, contact provider support

---

## Environment Variables

```bash
# Transak
export TRANSAK_API_KEY="pk_..."
export TRANSAK_SECRET="sk_..."
export TRANSAK_ENV="PRODUCTION"

# CoinRemitter
export COINREMITTER_API_KEY="api_key_..."
export COINREMITTER_API_PASSWORD="api_pwd_..."

# Exchange Rates
export COINGECKO_API_URL="https://api.coingecko.com/api/v3"

# Webhooks
export WEBHOOK_SECRET="webhook_secret_123"
export WEBHOOK_TIMEOUT_SEC="10"

# Notifications
export TELEGRAM_BOT_TOKEN="123456:ABC..."
export TELEGRAM_CHAT_ID="933545457"

# KYC
export KYC_FREE_LIMIT_USD="500"
export KYC_SUMSUB_LIMIT="5000"
export SUMSUB_APP_TOKEN="sbx_..."

# Admin
export ADMIN_API_KEY="admin_key_123"
export BASE_URL="http://localhost:8000"
```

---

## Performance Metrics (Expected)

| Metric | Value | Notes |
|--------|-------|-------|
| Lockbox validation | < 1 sec | AI inference time |
| Payment creation | < 100 ms | DB write + provider calc |
| Rate locking | < 500 ms | API call + DB |
| Provider checkout | 3-10 min | User-dependent |
| Transak processing | 1-30 min | Payment processor time |
| CoinRemitter settlement | < 1 hour | Blockchain dependent |
| Blockchain confirm | 1-15 min | Ethereum network |
| Webhook delivery | < 5 sec | Immediate delivery |
| **End-to-end** | **5-30 min** | Varies by provider |

---

## Key Contacts & Resources

- **Transak Docs:** https://docs.transak.com
- **CoinRemitter Docs:** https://api.coinremitter.com/docs
- **Ethereum Explorer:** https://etherscan.io
- **Telegram Channel:** @BeastPayOps
- **Support Email:** support@beastpay.io

---

*Generated: 2026-05-03 | BeastPay Development Team*

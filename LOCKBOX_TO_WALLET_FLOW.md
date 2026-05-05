# Lockbox to Crypto Wallet: Complete Process Flow

**Date**: 2026-05-03  
**System**: BeastPay OpenClaw Payment Gateway  
**Merchant**: SICHER MAYOR COMMERCIAL BROKERS L.L.C (Dubai DED)

---

## Overview

This document describes the **complete journey** of funds from lockbox transaction validation through to final cryptocurrency delivery in the customer's wallet.

### High-Level Flow

```
CUSTOMER ENTERS CARD DETAILS
         ↓
    [LOCKBOX VALIDATION]
    - Card validation
    - Fraud check
    - Anomaly detection
    - AI confidence scoring
         ↓
    [PAYMENT CREATION]
    - Payment record created
    - Provider selected (best-fit scoring)
    - KYC tier determined
         ↓
    [EXCHANGE RATE LOCK]
    - Current rate fetched
    - Amount locked (15 min validity)
    - Conversion calculated
         ↓
    [FIAT → CRYPTO CONVERSION]
    ├─→ Provider Type 1: Fiat→Crypto (Transak, MoonPay)
    │   - Customer redirected to provider checkout
    │   - Customer completes card payment with provider
    │   - Provider sends payment confirmed webhook
    │   - Crypto credited to wallet
    │
    └─→ Provider Type 2: Crypto-Direct (CoinRemitter, Plisio)
        - Crypto invoice created
        - Customer pays with crypto (BTC, ETH, USDT, etc.)
        - Blockchain confirms payment
        - Crypto sent to wallet
         ↓
    [PAYMENT STATUS UPDATE]
    - Status: pending → processing → completed
    - Crypto amount recorded
    - Exchange rate and fees calculated
         ↓
    [WEBHOOK NOTIFICATION]
    - Merchant webhook URL called
    - Event: payment.completed
    - Payload includes: payment_id, amount, crypto, wallet, status
    - Retry logic: up to 5 attempts with exponential backoff
         ↓
    [CUSTOMER NOTIFICATIONS]
    - Telegram message to ops
    - WhatsApp notification to customer (if enabled)
    - Email confirmation
         ↓
    [COMPLETION]
    - Funds delivered to customer's crypto wallet
    - Transaction finalized in BeastPay DB
```

---

## STAGE 1: LOCKBOX TRANSACTION VALIDATION

**Module**: `lockbox_integration.py`  
**Database**: `lockbox_transactions` table

### 1.1 Card Input Capture

Customer submits payment via checkout form:
```
POST /api/checkout
{
  "card_number": "4111 1111 1111 1111",
  "expiry_date": "12/25",
  "cvv": "123",
  "cardholder_name": "JOHN SMITH",
  "billing_street": "123 Main St",
  "billing_city": "New York",
  "billing_state": "NY",
  "billing_zip": "10001",
  "billing_country": "US",
  "amount": 1000,
  "currency": "USD",
  "crypto_currency": "USDT",
  "wallet_address": "0x742d35Cc6634C0532925a3b844Bc9e7595f1234"
}
```

### 1.2 Lockbox Validation Process

```sql
INSERT INTO lockbox_transactions (
  raw_input,
  masked_card_number,
  card_number,
  expiry_date,
  cvv,
  cardholder_name,
  billing_street, billing_city, billing_state, billing_zip, billing_country,
  validation_status,
  validation_errors,
  confidence_scores,
  anomalies,
  ai_reasoning,
  source,
  created_at, updated_at
) VALUES (...)
```

### 1.3 AI Validation Checks

The system runs multiple checks via Claude AI:

1. **Luhn Algorithm** (card checksum)
   - Status: ✓ PASS / ✗ FAIL

2. **Card Type Detection**
   - 4xxx = Visa
   - 5xxx = Mastercard
   - 3xxx = Amex
   - Status: DETECTED

3. **Expiry Validation**
   - Format: MM/YY
   - Not expired: `expiry_date > current_date`
   - Status: ✓ VALID / ✗ EXPIRED

4. **CVV Length Check**
   - Visa/MC: 3 digits
   - Amex: 4 digits
   - Status: ✓ VALID / ✗ INVALID_LENGTH

5. **Fraud Pattern Detection**
   - High-value transaction flagged
   - Unusual country/currency combo
   - Rapid consecutive transactions
   - Anomaly Score: 0–100

6. **Confidence Scoring**
   - Card validity: 0–100
   - Fraud risk: 0–100
   - Cardholder match: 0–100
   - **Overall confidence**: 0–100

### 1.4 Validation Result

```json
{
  "lockbox_tx_id": 12345,
  "validation_status": "approved",
  "confidence_scores": {
    "card_valid": 98,
    "fraud_risk": 5,
    "address_match": 87,
    "overall": 90
  },
  "anomalies": [],
  "ai_reasoning": "Card passed Luhn check. Cardholder address matches billing. No fraud flags."
}
```

**Decision Logic:**
- `overall >= 85` → **✓ APPROVED** → proceed to payment creation
- `65 <= overall < 85` → **⚠️ REVIEW** → manual inspection required
- `overall < 65` → **✗ REJECTED** → decline payment

---

## STAGE 2: PAYMENT CREATION & PROVIDER SELECTION

**Module**: `subagents/payment_router.py`  
**Database**: `payments` table

### 2.1 Create Payment Record

Once lockbox validates successfully:

```python
# PaymentRouter.execute(action="create", payload={...})

STEP-1: List available providers
  ├─ transak (fiat→crypto, PRODUCTION)
  ├─ stripe (card, SANDBOX)
  ├─ coinremitter (crypto-direct, LIVE)
  ├─ plisio (crypto-direct, LIVE)
  ├─ nowpayments (crypto-direct, SANDBOX)
  └─ moonpay (fiat→crypto, SANDBOX)

STEP-2: Filter by provider type
  Payload specifies: provider_type = "fiat→crypto" or "crypto-direct"
  
  Example: fiat→crypto filters to → [transak, stripe, moonpay]

STEP-3: Evaluate providers
  For each provider, score 0–100 on:
    - Status (LIVE vs SANDBOX): +15 for LIVE
    - KYC support (matches tier): +10
    - Crypto support (ticker match): +10
    - Fiat support (currency match): +10
    - Speed (settlement < 1hr): +10
    - Spot credit (immediate): +15
    - Fees (lower is better): +20

STEP-4: Provider Evaluation Examples
  
  SCENARIO: Payment of $500 USD → USDT (no KYC required, fiat→crypto)
  
  Provider: transak
    ✓ Type matches (fiat→crypto)
    ✓ Status: PRODUCTION (live)
    ✓ USD supported
    ✓ USDT supported
    ✓ Free tier limit: $500 (at limit)
    ✓ Fee: 2% + $10 = $20
    Score: 85/100
  
  Provider: stripe
    ✓ Type: card (different category)
    ✗ Status: SANDBOX (not live)
    Score: 25/100 (rejected)
  
  Winner: transak (highest score)

STEP-5: Select best provider
  Best: transak (score: 85)
  
STEP-6: Create payment record
  INSERT INTO payments (
    payment_id, merchant_id, fiat_amount, fiat_currency,
    crypto_currency, wallet_address,
    provider_id, status, kyc_tier,
    fee_percent, fee_fixed_usd,
    created_at
  )
```

**Payment Record Structure:**

```sql
SELECT * FROM payments WHERE payment_id = 'uuid...';

payment_id:        'fb7a82e1-...'
merchant_id:       'merc_123'
fiat_amount:       1000.00
fiat_currency:     'USD'
crypto_currency:   'USDT'
wallet_address:    '0x742d35Cc...'
customer_email:    'john@example.com'
customer_name:     'John Smith'
status:            'pending'
provider_id:       'transak'
provider_tx_id:    NULL (populated after provider confirms)
crypto_amount:     NULL (populated after exchange rate lock)
exchange_rate:     NULL
fee_amount:        20.00
created_at:        '2026-05-03T14:22:35Z'
updated_at:        '2026-05-03T14:22:35Z'
```

### 2.2 KYC Tier Determination

```python
# Determined by amount and customer profile

if amount < KYC_FREE_LIMIT_USD:  # $500
    kyc_tier = "free"
    # No KYC required
    
elif amount < KYC_SUMSUB_LIMIT:  # $5,000
    kyc_tier = "email"
    # Email verification only
    
else:
    kyc_tier = "full"
    # Full Sumsub KYC (ID verification, etc.)
```

**Payment with $500 USD → No KYC required**

---

## STAGE 3: EXCHANGE RATE LOCKING

**Module**: `subagents/crypto_converter.py`  
**Duration**: 15 minutes

### 3.1 Get Current Rate

```python
# CryptoConverter.execute(action="lock_rate", payload={
#   "payment_id": "fb7a82e1-...",
#   "from_ticker": "USD",
#   "to_ticker": "USDT",
#   "amount": 1000
# })

STEP-1: Check cached rate
  Cache hit? → Use cached rate (refreshed every 60s)
  
STEP-2: Fetch live rate
  Source: CoinGecko API
  Request: GET /simple/price?ids=tether&vs_currencies=usd
  Response: { "tether": { "usd": 1.0001 } }
  
STEP-3: Calculate conversion
  fiat_amount / rate = crypto_amount
  1000 USD / 1.0001 USDT/USD = 999.9 USDT (rounded to 8 decimals)
  
STEP-4: Store rate lock
  UPDATE payments SET
    exchange_rate = 1.0001,
    crypto_amount = 999.90,
    rate_locked_until = NOW + 15 minutes
```

### 3.2 Rate Lock Record

```json
{
  "rate_lock_id": "lock_abc123...",
  "payment_id": "fb7a82e1-...",
  "from_ticker": "USD",
  "to_ticker": "USDT",
  "locked_rate": 1.0001,
  "amount_from": 1000.00,
  "amount_to": 999.90,
  "lock_duration_min": 15,
  "expires_at": "2026-05-03T14:37:35Z",
  "locked_at": "2026-05-03T14:22:35Z"
}
```

**Validity Check:**
- Customer must complete provider checkout within 15 minutes
- After expiry, rate is re-locked when payment is confirmed
- Protects both customer and merchant from market volatility

---

## STAGE 4: FIAT → CRYPTO CONVERSION (Provider Routes)

### ROUTE A: Fiat→Crypto Providers (Transak)

**Provider: Transak**

#### 4.A.1 Generate Checkout URL

```python
# TransakProvider.build_widget_url(payment)

Params:
  apiKey:                  TRANSAK_API_KEY
  defaultCryptoCurrency:   "USDT"
  network:                 "ethereum" (or "tron" based on wallet)
  walletAddress:           "0x742d35Cc6634C0532925a3b844Bc9e7595f1234"
  fiatCurrency:            "USD"
  fiatAmount:              "1000"
  defaultPaymentMethod:    "credit_debit_card"
  partnerOrderId:          "fb7a82e1-..." (our payment_id)
  email:                   "john@example.com"
  firstName:               "John"
  lastName:                "Smith"
  maxFiatAmount:           "50000"

URL: https://global.transak.com?apiKey=...&walletAddress=0x742d35Cc...
```

#### 4.A.2 Customer Checkout Flow

```
1. Customer redirected to Transak checkout
2. Transak SDK loads → customer sees payment form
3. Customer enters card details (or uses saved payment method)
4. Transak validates card with payment processor
5. If approved:
   → Transak deducts funds (with Transak fees)
   → Transak calculates crypto amount at current rate
   → Transak sends crypto to customer's wallet
   → Transak sends webhook to BeastPay
```

#### 4.A.3 Transak Webhook Received

```python
# POST /webhooks/transak

Webhook Payload:
{
  "event": "ORDER_COMPLETED",
  "data": {
    "id": "transak_order_12345",
    "partnerOrderId": "fb7a82e1-...",
    "status": "COMPLETED",
    "cryptoAmount": "999.5",
    "cryptoCurrency": "USDT",
    "network": "ethereum",
    "walletAddress": "0x742d35Cc...",
    "paymentMethod": "credit_debit_card",
    "timestamp": "2026-05-03T14:25:00Z"
  }
}

Processing:
  1. Verify webhook signature (HMAC-SHA256)
  2. Parse webhook → payment_id = fb7a82e1-...
  3. Update payment record:
     UPDATE payments SET
       provider_tx_id = 'transak_order_12345',
       status = 'processing',
       crypto_amount = 999.5,
       updated_at = NOW
  4. Trigger: "payment.processing" → merchant webhook
  5. Trigger: "payment.completed" → merchant webhook (when Transak confirms)
```

**Customer's Wallet State:**
```
Before: 0 USDT
After:  999.5 USDT (delivered to 0x742d35Cc...)
```

---

### ROUTE B: Crypto-Direct Providers (CoinRemitter)

**Provider: CoinRemitter**

#### 4.B.1 Create Invoice

```python
# CoinRemitterProvider.create_invoice(payment)

API Call:
  POST https://api.coinremitter.com/v1/invoice/create
  
Headers:
  x-api-key:       COINREMITTER_API_KEY
  x-api-password:  COINREMITTER_API_PASSWORD
  Content-Type:    application/json

Body:
{
  "fiat_amount": 1000,
  "fiat_currency": "USD",
  "notify_url": "https://beastpay.io/webhooks/coinremitter",
  "success_url": "https://beastpay.io/pay/success/fb7a82e1-...",
  "fail_url": "https://beastpay.io/pay/link_456",
  "description": "BeastPay payment",
  "custom_data1": "fb7a82e1-...",
  "expiry_time_in_minutes": 1440
}

Response:
{
  "success": true,
  "data": {
    "invoice_id": "cr_inv_789",
    "address": "0x1234567890abcdef...",  // Deposit address
    "total_amount": "999.5",
    "url": "https://coinremitter.com/invoice/cr_inv_789",
    "status_code": 0  // 0=pending, 1=paid, etc.
  }
}
```

#### 4.B.2 Customer Payment Flow

```
1. Customer receives invoice details:
   - Deposit address: 0x1234567890abcdef...
   - Amount: 999.5 USDT
   - QR code for mobile wallet
   - Invoice URL

2. Customer sends crypto from their wallet:
   - Opens wallet app (MetaMask, Coinbase, etc.)
   - Scans QR code or enters address
   - Sends 999.5 USDT to invoice address
   - Transaction broadcast to blockchain

3. Blockchain confirms transaction:
   - On-chain network confirmations (6 for Ethereum)
   - CoinRemitter detects payment in pool address

4. CoinRemitter sends webhook:
   POST /webhooks/coinremitter
```

#### 4.B.3 CoinRemitter Webhook Processing

```python
# Webhook received from CoinRemitter

Webhook Payload:
{
  "invoice_id": "cr_inv_789",
  "status_code": 1,  // 1 = paid
  "paid_amount": "999.5",
  "transaction_id": "0xabc123...",
  "custom_data1": "fb7a82e1-...",
  "address": "0x1234567890abcdef..."
}

Processing:
  1. Parse webhook
  2. Verify invoice: GET /v1/invoice/get → confirm status
  3. Extract payment_id from custom_data1
  4. Update payment record:
     UPDATE payments SET
       provider_tx_id = '0xabc123...',
       provider_order_id = 'cr_inv_789',
       status = 'completed',
       crypto_amount = 999.5,
       updated_at = NOW
```

**Customer's Wallet State:**
```
Before: 1000 USDT (customer's initial balance)
After:  1000 USDT (sent to invoice address) + 999.5 USDT (received from invoice)
Net:    999.5 USDT received (minus on-chain gas fees)
```

---

## STAGE 5: PAYMENT STATUS UPDATES

**Module**: Database state machine  
**Table**: `payments`

### 5.1 Status Transitions

```
pending
  ↓
processing (provider received → waiting for blockchain/settlement)
  ↓
completed (funds delivered to wallet)
  ↓
failed (optional: if customer refunds, dispute, etc.)
```

### 5.2 Payment State at Each Step

**Step 1: Payment Created (Lockbox Validated)**
```json
{
  "payment_id": "fb7a82e1-...",
  "status": "pending",
  "provider": "transak",
  "fiat_amount": 1000,
  "crypto_amount": null,
  "provider_tx_id": null,
  "updated_at": "2026-05-03T14:22:35Z"
}
```

**Step 2: Rate Locked**
```json
{
  "status": "pending",
  "crypto_amount": 999.90,  // CALCULATED
  "exchange_rate": 1.0001,  // LOCKED
  "rate_locked_until": "2026-05-03T14:37:35Z",
  "updated_at": "2026-05-03T14:22:45Z"
}
```

**Step 3: Provider Webhook Received (Processing)**
```json
{
  "status": "processing",
  "provider_tx_id": "transak_order_12345",
  "provider_order_id": "transak_order_12345",
  "crypto_amount": 999.5,  // CONFIRMED by provider
  "fee_amount": 20.00,     // CALCULATED
  "updated_at": "2026-05-03T14:25:00Z"
}
```

**Step 4: Crypto Delivered (Completed)**
```json
{
  "status": "completed",
  "wallet_address": "0x742d35Cc6634C0532925a3b844Bc9e7595f1234",
  "crypto_delivered": true,
  "delivery_timestamp": "2026-05-03T14:26:00Z",
  "updated_at": "2026-05-03T14:26:00Z"
}
```

---

## STAGE 6: MERCHANT WEBHOOK NOTIFICATION

**Module**: `subagents/webhook_orchestrator.py`  
**Database**: `webhook_delivery_logs` (auto-created)

### 6.1 Webhook Trigger Events

For each payment, up to 3 webhook events fire:

1. **payment.pending** (optional)
   - When: Payment created, lockbox approved
   - Use: Merchant tracks funnel

2. **payment.processing**
   - When: Provider received payment
   - Use: Merchant knows settlement is in progress

3. **payment.completed**
   - When: Crypto delivered to wallet (blockchain confirmed)
   - Use: Merchant delivers goods/services

### 6.2 Webhook Payload Structure

```python
# WebhookOrchestrator.execute(action="deliver", payload={...})

webhook_id = "webhook_xyz789"
timestamp = "2026-05-03T14:26:00Z"
event_type = "payment.completed"

payload = {
  "event_type": "payment.completed",
  "data": {
    "payment_id": "fb7a82e1-...",
    "merchant_id": "merc_123",
    "amount": {
      "fiat": 1000,
      "fiat_currency": "USD",
      "crypto": 999.5,
      "crypto_currency": "USDT",
      "fees": 20.00,
      "exchange_rate": 1.0001
    },
    "wallet_address": "0x742d35Cc6634C0532925a3b844Bc9e7595f1234",
    "customer": {
      "email": "john@example.com",
      "name": "John Smith"
    },
    "provider": {
      "name": "transak",
      "provider_tx_id": "transak_order_12345",
      "provider_order_id": "transak_order_12345"
    },
    "status": "completed",
    "settled_at": "2026-05-03T14:26:00Z"
  },
  "timestamp": "2026-05-03T14:26:00Z"
}

# Generate signature
signature = HMAC_SHA256(
  secret=WEBHOOK_SECRET,
  message=json.dumps(payload, sort_keys=True)
)
```

### 6.3 Webhook Delivery with Retries

```python
# Retry Logic
Attempt 1: Immediate
Attempt 2: After 1 second
Attempt 3: After 2 seconds
Attempt 4: After 5 seconds
Attempt 5: After 10 seconds

If all 5 fail:
  → Log in webhook_delivery_logs
  → Alert ops (Telegram message)
  → Mark as "failed" (manual retry available)
```

### 6.4 Merchant Webhook Verification

Merchant must verify webhook signature:

```python
# Merchant side (pseudo-code)

def verify_webhook(request):
    webhook_signature = request.headers['X-Webhook-Signature']
    event_type = request.headers['X-Event-Type']
    event_data = request.json['data']
    timestamp = request.json['timestamp']
    
    payload_str = json.dumps({
        "event_type": event_type,
        "data": event_data,
        "timestamp": timestamp
    }, sort_keys=True)
    
    expected_sig = HMAC_SHA256(
        WEBHOOK_SECRET,
        payload_str
    )
    
    if not compare_digest(webhook_signature, expected_sig):
        return False, "Invalid signature"
    
    return True, "Verified"
```

---

## STAGE 7: CUSTOMER NOTIFICATIONS

### 7.1 Telegram Notification (Ops)

Sent to: `TELEGRAM_CHAT_ID = 933545457`

```
📊 PAYMENT COMPLETED
ID: fb7a82e1-6a3f...
Customer: john@example.com (John Smith)
Amount: $1,000 USD → 999.5 USDT
Provider: transak
Status: ✓ Delivered to wallet
TX: 0xabc123...
Time: 14:26 UTC
```

### 7.2 WhatsApp Notification (Customer, if enabled)

Recipient: Customer phone (if `WHATSAPP_TOKEN` set)

```
✅ Payment Confirmed!

Your $1,000 USD has been converted to 999.5 USDT
and sent to your wallet:
0x742d35Cc6634C0532925a3b844Bc9e7595f1234

Transaction ID: transak_order_12345
Settlement Time: ~10 minutes
```

### 7.3 Email Confirmation

Recipient: `john@example.com`

```
Subject: Payment Confirmation - BeastPay

Dear John Smith,

Your payment has been successfully processed!

Amount:        $1,000 USD
Cryptocurrency: 999.5 USDT
Wallet:        0x742d35Cc...
Status:        COMPLETED
Date:          2026-05-03 14:26 UTC
Transaction:   transak_order_12345

Your crypto will arrive in your wallet within 
10-30 minutes depending on network congestion.

Thank you for using BeastPay!
Support: support@beastpay.io
```

---

## STAGE 8: FINAL DELIVERY & COMPLETION

### 8.1 Cryptocurrency Arrives in Wallet

```
Wallet Address: 0x742d35Cc6634C0532925a3b844Bc9e7595f1234
Blockchain:    Ethereum
Token:         Tether (USDT) - ERC-20
Amount:        999.5 USDT
Confirmations: 12+ (finalized)
Block:         20421000
TX Hash:       0xabc123def456...
Timestamp:     2026-05-03 14:26:15 UTC
Status:        ✓ RECEIVED & CONFIRMED
```

### 8.2 Payment Record Final State

```sql
SELECT * FROM payments WHERE payment_id = 'fb7a82e1-...';

payment_id:              'fb7a82e1-6a3f-4c2d-9e1a-8f7b3c5d2e1a'
merchant_id:             'merc_123'
fiat_amount:             1000.00
fiat_currency:           'USD'
crypto_currency:         'USDT'
wallet_address:          '0x742d35Cc6634C0532925a3b844Bc9e7595f1234'
customer_email:          'john@example.com'
customer_name:           'John Smith'
status:                  'completed'
provider:                'transak'
provider_tx_id:          'transak_order_12345'
provider_order_id:       'transak_order_12345'
crypto_amount:           999.50
exchange_rate:           1.0001
fee_amount:              20.00
fee_percent:             2.0
fee_fixed_usd:           10.0
description:             'BeastPay payment'
webhook_data:            '{...}' (last webhook payload)
lockbox_tx_id:           12345
kyc_tier:                'free'
created_at:              '2026-05-03T14:22:35Z'
updated_at:              '2026-05-03T14:26:00Z'
completed_at:            '2026-05-03T14:26:00Z'
webhook_delivered_at:    '2026-05-03T14:27:30Z'
crypto_delivered_at:     '2026-05-03T14:26:15Z'
```

### 8.3 Database Audit Trail

```sql
SELECT * FROM audit_logs WHERE resource_id = 'fb7a82e1-...';

✓ 14:22:35 → payment.created          (lockbox validated)
✓ 14:22:45 → rate.locked              (exchange rate locked 15min)
✓ 14:25:00 → payment.processing       (provider webhook received)
✓ 14:26:00 → payment.completed        (crypto confirmed in wallet)
✓ 14:27:30 → webhook.delivered        (merchant notified)
```

---

## FEE BREAKDOWN

### Example: $1,000 USD → USDT via Transak

```
Input Amount:           $1,000.00 USD
─────────────────────────────────────

Transak Fees:
  Fee Percentage:       2.0% = $20.00
  Fee Fixed:            $10.00
  Total Transak Fee:    $30.00
  
Net to Gateway:         $970.00 USD
─────────────────────────────────────

BeastPay Revenue:       $5.00 USD (0.5% of input)
Provider Cost:          $25.00 USD
─────────────────────────────────────

Exchange Rate Lock:     USD → USDT @ 1.0001
Crypto Amount:          999.90 USDT
─────────────────────────────────────

Customer Receives:      999.90 USDT in wallet
```

---

## ERROR HANDLING & RECOVERY

### 8.1 Lockbox Validation Failure

```
Status:  REJECTED
Reason:  confidence_score < 65
Action:  Payment declined
Notify:  Email to customer
Retry:   Customer can try different card
```

### 8.2 Provider Rate Lock Expired

```
Scenario: Customer waits > 15 minutes before checkout
Action:   Rate re-locked when payment confirmed
Effect:   Crypto amount may change (locked rate re-evaluated)
```

### 8.3 Provider Webhook Delivery Failure

```
Attempt 1-5: Exponential backoff retry
After 5 attempts: Alert ops via Telegram
Status: "webhook_failed"
Recovery: Manual webhook retry endpoint available
```

### 8.4 Crypto Delivery Failure (Blockchain Issue)

```
Scenario: Transak/CoinRemitter sends crypto, blockchain congestion
Status: "processing" → "completed" (when confirmed)
Timeout: 30 minutes (default)
Action: If not confirmed → ops review + manual settlement
```

---

## QUICK REFERENCE: TIMING

| Stage | Duration | Notes |
|-------|----------|-------|
| Lockbox Validation | < 1 sec | AI checks |
| Payment Creation | < 100ms | DB write |
| Rate Locking | < 500ms | CoinGecko API |
| Provider Checkout | 3-10 min | Customer action |
| Provider Processing | 1-30 min | Transak/CoinRemitter |
| Blockchain Confirm | 1-15 min | Network dependent |
| Webhook Delivery | < 5 sec | Retries up to 5x |
| **Total (best case)** | **5-10 min** | |
| **Total (worst case)** | **30+ min** | Network delays |

---

## DATABASE TABLES INVOLVED

```sql
lockbox_transactions   → Card validation & fraud check
payment_links          → Reusable payment URLs
payments               → Main payment record (status, amounts, provider)
kyc_records            → KYC tier & Sumsub status
merchants              → Merchant credentials & webhook URL
webhook_delivery_logs  → Webhook attempt history
audit_logs             → Full transaction audit trail
gateway_credentials    → Encrypted provider API keys
exchange_rate_cache    → Cached crypto rates (TTL 60s)
```

---

## API ENDPOINTS SUMMARY

| Method | Endpoint | Purpose |
|--------|----------|---------|
| POST | `/api/payments` | Create payment (trigger lockbox→crypto flow) |
| GET | `/api/payments/{id}` | Get payment status |
| POST | `/webhooks/transak` | Receive Transak webhook |
| POST | `/webhooks/coinremitter` | Receive CoinRemitter webhook |
| POST | `/api/webhooks/deliver` | Manually deliver merchant webhook |
| GET | `/admin/metrics` | Payment analytics dashboard |
| POST | `/api/rates/lock` | Lock exchange rate |

---

## Conclusion

The **lockbox → crypto wallet flow** is a fully automated, audited, and resilient process that:

1. **Validates** card data via AI + Luhn + fraud checks
2. **Routes** to best-fit provider (Transak, CoinRemitter, etc.)
3. **Locks** exchange rates to protect customer
4. **Executes** fiat→crypto or crypto→crypto conversion
5. **Tracks** status via webhook payloads
6. **Confirms** delivery to blockchain
7. **Notifies** merchant + customer
8. **Audits** every step in database

**Result:** Customer's crypto wallet receives funds in 5–30 minutes, with full transparency and compliance.


# CodeWords Workflow Automation Integration

**Status:** ✅ **INTEGRATED**  
**Date:** 2026-05-05  
**Integration Type:** Event-Driven Workflow Automation

---

## Overview

Your Stripe Integrated Crypto Wallet System now automatically triggers **CodeWords workflows** when payment events occur.

### Payment Event Automation

```
Stripe Payment Event
    ↓
Payment Database Updated
    ↓
CodeWords Workflow Triggered
    ↓
Automated Actions:
  • Send email confirmations
  • Transfer crypto to wallet
  • Notify via Telegram/WhatsApp
  • Trigger merchant webhooks
  • Log events
  • Reverse transactions (refunds)
```

---

## Setup

### 1. Get CodeWords API Key

1. Sign up at **https://codewords.agemo.ai**
2. Navigate to **Settings** → **API Keys**
3. Create new API key (or use existing)
4. Copy the key

### 2. Configure Environment

Add to `.env`:
```bash
CODEWORDS_API_KEY=cw_live_...your_api_key_here...
CODEWORDS_API_URL=https://api.codewords.agemo.ai
```

### 3. Restart API Server

```bash
# Kill old server
pkill -f test_stripe_server

# Start with CodeWords enabled
python3 test_stripe_server.py
```

### 4. Verify Integration

```bash
curl -X GET http://127.0.0.1:8000/codewords/status
# Response: {"status": "connected", "api_key": "configured"}
```

---

## Workflow Templates

The system comes with 3 pre-built workflow templates you can import into CodeWords:

### Template 1: Payment Completed
**Trigger:** `payment.completed`

**Automated Actions:**
```
1. Send email to customer (confirmation + wallet address)
2. Transfer crypto to wallet address
3. Fire merchant webhook (payment.completed)
4. Send Telegram/WhatsApp notification
5. Log transaction in CRM
```

**Data Available:**
```json
{
  "event": "payment.completed",
  "payment_id": "550e8400-e29b-41d4-a716-446655440000",
  "merchant_id": "test-merchant",
  "amount": 100,
  "fiat_currency": "USD",
  "crypto_currency": "ETH",
  "wallet_address": "0x742d35Cc6634C0532925a3b844Bc9e7595f1bEb0",
  "customer_email": "user@example.com",
  "timestamp": "2026-05-05T12:00:00Z"
}
```

### Template 2: Payment Failed
**Trigger:** `payment.failed`

**Automated Actions:**
```
1. Send error email to customer
2. Log failure reason
3. Fire merchant webhook (payment.failed)
4. Alert support team
5. Create ticket for investigation
```

**Data Available:**
```json
{
  "event": "payment.failed",
  "payment_id": "550e8400-e29b-41d4-a716-446655440000",
  "merchant_id": "test-merchant",
  "error_reason": "Stripe payment failed",
  "customer_email": "user@example.com",
  "timestamp": "2026-05-05T12:05:00Z"
}
```

### Template 3: Payment Refunded
**Trigger:** `payment.refunded`

**Automated Actions:**
```
1. Reverse crypto transfer (send back to exchange)
2. Send refund confirmation email
3. Log refund in accounting system
4. Fire merchant webhook (payment.refunded)
5. Update customer account
```

**Data Available:**
```json
{
  "event": "payment.refunded",
  "payment_id": "550e8400-e29b-41d4-a716-446655440000",
  "merchant_id": "test-merchant",
  "amount": 100,
  "wallet_address": "0x742d35Cc6634C0532925a3b844Bc9e7595f1bEb0",
  "timestamp": "2026-05-05T12:10:00Z"
}
```

---

## Import Workflows

### Option 1: Auto-Import (Recommended)

```bash
python3 << 'EOF'
from integrations.codewords import CodeWordsIntegration

cw = CodeWordsIntegration()
templates = CodeWordsIntegration.create_workflow_templates()

# Print templates
import json
print(json.dumps(templates, indent=2))
EOF
```

Then in CodeWords Dashboard:
1. Go to **Workflows** → **Import**
2. Select workflow template
3. Customize actions as needed
4. Deploy

### Option 2: Manual Creation

In CodeWords Dashboard:

1. **Create Workflow** → New
2. **Name:** `payment_completed_test-merchant`
3. **Trigger:** Webhook
4. **Add Steps:**
   - Email action (send confirmation)
   - HTTP action (transfer crypto)
   - Webhook action (notify merchant)
   - Notification action (Telegram)

---

## API Methods

### Trigger Workflow

```python
from integrations.codewords import CodeWordsIntegration

cw = CodeWordsIntegration()

# On payment completed
await cw.on_payment_completed(
    payment_id="550e8400...",
    merchant_id="test-merchant",
    amount=100,
    fiat_currency="USD",
    crypto_currency="ETH",
    wallet_address="0x742d35...",
    customer_email="user@example.com"
)

# Response:
# {
#   "status": "triggered",
#   "execution_id": "exec_123...",
#   "workflow_id": "payment_completed_test-merchant",
#   "timestamp": "2026-05-05T12:00:00Z"
# }
```

### Check Workflow Status

```python
status = await cw.get_workflow_status("exec_123...")

# Response:
# {
#   "execution_id": "exec_123...",
#   "workflow_id": "payment_completed_test-merchant",
#   "status": "completed",
#   "steps_completed": 4,
#   "duration_ms": 3450,
#   "results": {
#     "email_sent": true,
#     "crypto_transferred": true,
#     "webhook_fired": true
#   }
# }
```

### Custom Workflow Trigger

```python
await cw.trigger_workflow(
    workflow_id="my_custom_workflow",
    trigger_data={
        "custom_field": "value",
        "payment_id": "550e8400..."
    }
)
```

---

## Workflow Variables

Inside CodeWords, use these variables to access payment data:

```
{{ trigger_data.payment_id }}
{{ trigger_data.merchant_id }}
{{ trigger_data.amount }}
{{ trigger_data.fiat_currency }}
{{ trigger_data.crypto_currency }}
{{ trigger_data.wallet_address }}
{{ trigger_data.customer_email }}
{{ trigger_data.timestamp }}
```

### Example: Send Email

```
To: {{ trigger_data.customer_email }}
Subject: Payment Received!
Body:
Payment #{{ trigger_data.payment_id }}
Amount: ${{ trigger_data.amount }} {{ trigger_data.fiat_currency }}
Crypto: {{ trigger_data.crypto_currency }}
Wallet: {{ trigger_data.wallet_address }}
Time: {{ trigger_data.timestamp }}
```

---

## Real-World Use Cases

### Use Case 1: Instant Crypto Transfer
```
Payment Completed
  ↓
CodeWords Workflow
  ↓
Step 1: Verify crypto address (regex check)
Step 2: Get current exchange rate (API call)
Step 3: Calculate crypto amount
Step 4: Call crypto provider API (Transak/MetaMask)
Step 5: Monitor transaction
Step 6: Send customer confirmation with txn hash
```

### Use Case 2: Risk Scoring & Review
```
Payment Completed
  ↓
CodeWords Workflow
  ↓
Step 1: Check merchant risk score
Step 2: If risk > 50, queue for manual review
Step 3: Send review request to compliance team
Step 4: Hold crypto transfer pending approval
Step 5: On approval, execute transfer
```

### Use Case 3: Multi-Step Settlement
```
Payment Completed
  ↓
CodeWords Workflow
  ↓
Step 1: Record in ledger
Step 2: Calculate fees (2% to company, 1% to referrer)
Step 3: Create settlement batch
Step 4: Daily settlement (4:00 AM UTC)
Step 5: Reconcile with bank statement
Step 6: Archive records
```

### Use Case 4: Notification Channels
```
Payment Failed
  ↓
CodeWords Workflow
  ↓
Step 1: Email customer (retry instructions)
Step 2: SMS (backup contact)
Step 3: Telegram (support team alert)
Step 4: Slack (engineering team debug alert)
Step 5: Create support ticket (auto-assign)
```

---

## Integration Points

### Event Triggers (Automatic)

The system automatically triggers CodeWords when:

| Event | Workflow | Timing |
|-------|----------|--------|
| Payment completed | `payment_completed_{merchant}` | Immediately |
| Payment failed | `payment_failed_{merchant}` | Immediately |
| Payment refunded | `payment_refunded_{merchant}` | Immediately |

### Manual Triggers

You can also manually trigger workflows:

```bash
curl -X POST http://127.0.0.1:8000/codewords/trigger \
  -H "Content-Type: application/json" \
  -d '{
    "workflow_id": "my_custom_workflow",
    "trigger_data": {
      "payment_id": "550e8400...",
      "custom_field": "value"
    }
  }'
```

---

## Advanced Configuration

### Webhook Signature Verification

```python
from integrations.codewords import CodeWordsIntegration

cw = CodeWordsIntegration(
    api_key="cw_live_...",
    api_url="https://api.codewords.agemo.ai"
)

# Trigger with signature
await cw.trigger_workflow(
    workflow_id="payment_completed_test",
    trigger_data={"payment_id": "550e8400..."},
    webhook_secret="your_webhook_secret"
)
```

### Custom API URL (For Self-Hosted)

```python
cw = CodeWordsIntegration(
    api_key="cw_...",
    api_url="https://codewords.yourcompany.com"
)
```

### Error Handling

```python
try:
    result = await cw.on_payment_completed(...)
    if result["status"] == "triggered":
        print(f"Workflow triggered: {result['execution_id']}")
    else:
        print(f"Error: {result['error']}")
except Exception as e:
    print(f"Integration error: {e}")
    # Gracefully handle CodeWords unavailability
    # Payment is not affected, only workflow automation
```

---

## Monitoring

### Check Integration Status

```bash
curl http://127.0.0.1:8000/codewords/status
```

Response:
```json
{
  "status": "connected",
  "api_key": "configured",
  "api_url": "https://api.codewords.agemo.ai",
  "last_check": "2026-05-05T12:00:00Z"
}
```

### View Workflow Execution Logs

In CodeWords Dashboard:
1. Go to **Workflows** → [Your Workflow]
2. Click **Executions**
3. View logs, status, duration

### Database Queries

```sql
-- Check recent payments with workflow triggers
SELECT p.id, p.status, p.created_at, c.execution_id, c.workflow_status
FROM payments p
LEFT JOIN codewords_executions c ON p.id = c.payment_id
ORDER BY p.created_at DESC
LIMIT 10;
```

---

## Troubleshooting

### "CODEWORDS_API_KEY not configured"
**Solution:** Add to `.env`:
```bash
CODEWORDS_API_KEY=cw_live_...
```

### "Workflow trigger failed"
**Solution:** Check CodeWords dashboard:
1. Verify API key is valid
2. Check workflow exists
3. Review workflow logs
4. Check network connectivity

### "Workflow status shows 'error'"
**Solution:** 
1. Review workflow step configuration
2. Check template variables are correct
3. Verify external API integrations (email, SMS, etc)
4. Test individual steps manually in CodeWords

### "Payment completed but workflow didn't trigger"
**Solution:**
1. Check CodeWords API key in `.env`
2. Verify network connectivity
3. Check payment webhook was received
4. Review server logs for workflow trigger attempts

---

## Testing

### Test Payment → CodeWords Flow

```bash
# 1. Start server
python3 test_stripe_server.py &

# 2. Create payment (will trigger workflow)
curl -X POST http://127.0.0.1:8000/api/comprehensive-checkout \
  -H "X-Api-Key: test-api-key-a4be38be-e1c" \
  -G \
  --data-urlencode "merchant_id=test-merchant-a5686a67" \
  --data-urlencode "amount_fiat=100" \
  --data-urlencode "crypto_currency=ETH" \
  --data-urlencode "customer_email=test@example.com" \
  --data-urlencode "wallet_address=0x742d35Cc6634C0532925a3b844Bc9e7595f1bEb0"

# 3. Payment created, wait for Stripe webhook
# (In production, webhook would be fired by Stripe)

# 4. Simulate webhook manually
curl -X POST http://127.0.0.1:8000/webhooks/stripe \
  -H "Content-Type: application/json" \
  -d '{
    "type": "checkout.session.completed",
    "data": {
      "object": {
        "client_reference_id": "550e8400-e29b-41d4-a716-446655440000",
        "status": "complete"
      }
    }
  }'

# 5. Check CodeWords execution
# Go to CodeWords Dashboard → Executions
# Should see "payment_completed_test-merchant" workflow
```

---

## Deployment Checklist

- [ ] CodeWords account created
- [ ] API key generated
- [ ] `CODEWORDS_API_KEY` added to `.env`
- [ ] Server restarted
- [ ] Integration tested with sample payment
- [ ] Workflow templates imported into CodeWords
- [ ] Email/SMS integrations configured in CodeWords
- [ ] Crypto provider API configured in workflow
- [ ] Merchant webhooks configured in workflow
- [ ] Notification channels set up (Telegram, WhatsApp)
- [ ] Monitoring dashboard configured

---

## Summary

Your Stripe + CodeWords integration provides:

✅ **Automatic Workflows** - Payment events trigger automated actions  
✅ **Email Confirmations** - Instant customer notifications  
✅ **Crypto Transfer** - Automated wallet deposits  
✅ **Merchant Webhooks** - Real-time merchant notifications  
✅ **Error Handling** - Automatic failure notifications  
✅ **Flexible Actions** - Customize workflows in CodeWords  
✅ **Logging & Monitoring** - Full execution history  

**Next Steps:**
1. Set up CodeWords account
2. Add API key to `.env`
3. Import workflow templates
4. Customize workflows for your needs
5. Deploy and test end-to-end

---

Generated: 2026-05-05 18:00 UTC  
Integration: ✅ **ACTIVE**

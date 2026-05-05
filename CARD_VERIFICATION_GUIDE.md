# BeastPay Lockbox — Stripe-Style Card Verification System

Complete card verification system implementing Stripe Radar-style fraud detection, pre-authorization, AVS, and 3D Secure.

## 📋 Overview

When a customer enters card details into BeastPay, the system performs:

1. **Claude AI Parsing** — Extract structured data from unstructured input
2. **Luhn Validation** — Verify card number format (13-19 digits)
3. **Expiry & CVV Check** — Validate card is not expired
4. **AVS (Address Verification)** — Check billing address against issuer records
5. **Pre-Authorization** — Confirm card is active and has funds
6. **Fraud Risk Scoring** — Stripe Radar-style machine learning analysis (0-99 score)
7. **3D Secure Decision** — Determine if customer challenge needed
8. **Velocity Tracking** — Monitor card attempts over time

## 🎯 Risk Scoring (0-99)

```
0-64   → LOW RISK       → Approve automatically
65-74  → ELEVATED RISK  → Challenge with 3D Secure
75-99  → HIGH RISK      → Decline transaction
```

## 🔍 Fraud Signals Analyzed

### Device & IP (0-25 points)
- VPN/proxy usage detected
- Datacenter IP (unusual for consumer)
- First-time device

### Velocity (0-20 points)
- Card attempted 5+ times in 1 hour
- Rapid repeated failures

### Address (0-15 points)
- Billing country known for fraud
- Virtual/forwarding address (PO Box)

### Behavioral (0-20 points)
- Suspicious cardholder name (too short, test patterns)
- Temporary email address (@tempmail.com)
- Invalid email format

## 📁 Files

### Core Modules
- **`card_verification.py`** — Complete verification engine
  - Luhn algorithm
  - AVS simulation
  - Pre-authorization simulation
  - Fraud risk scoring
  - 3D Secure logic
  - Velocity tracking

- **`lockbox_integration.py`** — Integration layer
  - Combines Claude AI parsing with verification
  - End-to-end payment processing
  - FastAPI endpoints
  - Database logging

- **`lockbox.py`** — Existing (Claude AI parsing)
  - Extracts structured data from raw input
  - Confidence scoring
  - Anomaly detection

## 🚀 Quick Start

### 1. Test the System
```bash
python3 card_verification.py
python3 lockbox_integration.py --test
```

### 2. Integrate with BeastPay Server

In `server.py`:

```python
from lockbox_integration import create_lockbox_routes, process_payment_with_verification

# Add verification routes
create_lockbox_routes(app, db_path="payments.db")

# Or use directly in payment endpoint
@app.post("/payments/create")
async def create_payment(request: dict):
    # ... existing code ...
    
    # Verify card before processing
    verification = await process_payment_with_verification(
        raw_card_input=request.get("card_input"),
        ip_address=request.client.host,
        device_id=request.headers.get("X-Device-ID"),
        region=request.headers.get("X-Region", "US"),
        db_path="payments.db"
    )
    
    if verification["recommendation"] == "decline":
        return {"error": "Payment declined", "reason": verification.get("reason")}, 403
    
    if verification["recommendation"] == "challenge":
        # Initiate 3D Secure
        return {
            "status": "pending_3ds",
            "challenge_url": "/3ds/start",
            "transaction_id": request.get("id")
        }, 202
    
    # Process payment
    # ...
```

### 3. Add to Webhook Handler

```python
from lockbox_integration import process_payment_with_verification

@app.post("/webhooks/transak")
async def transak_webhook(request: dict):
    # Verify the card was properly checked
    if "verification_reference" not in request:
        return {"error": "Missing verification reference"}, 400
    
    # Continue webhook processing
    # ...
```

## 📊 Output Format

### Complete Verification Result
```json
{
  "status": "approve|challenge|decline",
  "timestamp": "2026-05-01T23:00:00",
  "recommendation": "approve|challenge|decline",
  "fraud_score": 35,
  "risk_level": "low|elevated|high",
  "action": "Process payment normally|Require 3D Secure|Decline transaction",
  "masked_card": "**** **** **** 0366",
  "card_type": "visa",
  "avs_match": "Y|N|U",
  "3ds_required": false,
  "steps": [
    {
      "name": "Claude AI Parsing",
      "status": "success",
      "confidence": {
        "cardNumber": 0.99,
        "expiryDate": 0.98,
        "cvv": 0.97
      }
    },
    {
      "name": "Format Validation",
      "status": "success"
    },
    {
      "name": "Velocity Check",
      "status": "success",
      "attempts_last_hour": 1,
      "attempts_last_24h": 3
    },
    {
      "name": "Complete Verification",
      "status": "success",
      "fraud_score": 35,
      "risk_level": "low",
      "fraud_signals": [
        "No fraud signals detected - legitimate transaction"
      ]
    }
  ]
}
```

## 🔐 API Endpoints

### Full Verification (with Claude AI parsing)
```bash
POST /api/verify-card
{
  "raw_input": "4532015112830366 12/25 123 John Doe 123 Main St New York NY 10001 US",
  "ip_address": "203.0.113.45",
  "device_id": "device_abc123",
  "region": "US"
}
```

### Quick Verification (card number only)
```bash
POST /api/quick-verify
{
  "card_number": "4532015112830366",
  "ip_address": "203.0.113.45"
}
```

### Card History (admin)
```bash
GET /api/card-history/{card_hash}
```

## 📈 Risk Score Examples

### ✅ Low Risk (Approved)
- Valid card format
- Card is active
- US-based customer
- Legitimate IP/device
- First-time purchase
- **Score: 15/99** → Approve

### ⚠️ Elevated Risk (3DS Challenge)
- Valid card format
- Card is active
- Multiple attempts in last hour
- Temporary email address
- New device
- **Score: 68/99** → Challenge with 3DS

### ❌ High Risk (Declined)
- Card flagged as stolen
- High velocity (10+ attempts/hour)
- VPN/proxy IP
- High-fraud country
- Suspicious name pattern
- **Score: 82/99** → Decline

## 🛡️ Security Best Practices

### 1. Never Store Raw Card Data
```python
# ❌ Don't do this
db.insert("cards", card_number=request.card_number)

# ✅ Do this
masked = mask_card_number(request.card_number)
hash = hashlib.sha256(request.card_number).hexdigest()
db.insert("cards", masked=masked, hash=hash)
```

### 2. Always Use HTTPS
Card data must be encrypted in transit:
```python
# Enforce HTTPS in FastAPI
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
app.add_middleware(HTTPSRedirectMiddleware)
```

### 3. Log Attempts (not card data)
```python
# ✅ Good
logger.info(f"Card verification: {fraud_score} risk level: {risk}")

# ❌ Bad
logger.info(f"Card {card_number} fraud score {fraud_score}")
```

### 4. Implement Rate Limiting
```python
from slowapi import Limiter
limiter = Limiter(key_func=get_remote_address)

@app.post("/api/verify-card")
@limiter.limit("5/minute")  # Max 5 verifications per minute per IP
async def verify_card(request: dict):
    # ...
```

## 📚 Integration Checklist

- [ ] Add `card_verification.py` to payment-gateway
- [ ] Add `lockbox_integration.py` to payment-gateway
- [ ] Create `card_verification_log` table in database
- [ ] Add verification endpoint to FastAPI app
- [ ] Integrate verification into payment creation flow
- [ ] Add 3D Secure handling
- [ ] Configure fraud threshold per region
- [ ] Set up monitoring/alerting for high-risk transactions
- [ ] Test with example cards (both valid and suspicious)
- [ ] Document in API documentation
- [ ] Train team on fraud signal interpretation

## 🧪 Test Cards

### Valid (Low Risk)
- `4532015112830366` — Visa, expires 12/25, CVV 123
- `5425233010103442` — Mastercard
- `378282246310005` — Amex

### Suspicious (High Risk - for testing)
- `4111111111111111` — Classic test card (obvious pattern)
- `6011111111111117` — Discover test card
- Cards with test names ("Test User", "John Test")

## 📞 Support

For fraud-related questions:
- Review Stripe's fraud prevention docs: https://stripe.com/docs/radar
- Check transaction logs in `/lockbox_verification_log` table
- Enable debug logging: `logging.getLogger("card_verification").setLevel(logging.DEBUG)`

## 🚀 Future Enhancements

1. **Real Bank Integration**
   - Connect to Visa/Mastercard networks
   - Real AVS checks against issuer database
   - Real pre-authorization holds

2. **Machine Learning**
   - Train custom fraud model on BeastPay transaction history
   - Per-merchant risk thresholds
   - Time-of-day anomaly detection

3. **Biometric Verification**
   - Fingerprint on mobile
   - Face recognition for web
   - Device binding

4. **3D Secure 2.0**
   - Challenge-response (OTP, push notification)
   - Frictionless flow for low-risk
   - Mobile SDK integration

---

**Last Updated:** May 1, 2026

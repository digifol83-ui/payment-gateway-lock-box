# BeastPay REST API Reference

Complete REST API documentation for all payment gateway endpoints.

---

## Authentication

All endpoints (except public ones) require API authentication via `X-Api-Key` header:

```bash
curl -H "X-Api-Key: sk_live_your_api_key" \
     http://localhost:8000/merchants/your_id
```

---

## Payment Operations

### Create Payment Order

```http
POST /orders
Content-Type: application/json

{
  "merchant_id": "merchant_abc123",
  "crypto": "BTC",
  "amount_usd": 150.00,
  "webhook_url": "https://your-domain.com/webhook",
  "metadata": {
    "order_id": "ORD-12345",
    "customer_email": "buyer@example.com"
  }
}

Response 201:
{
  "payment_id": "pay_xyz789",
  "order_id": "order_abc123",
  "provider": "stripe",
  "payment_url": "https://checkout.stripe.com/pay/...",
  "expires_at": "2026-04-29T11:30:00Z",
  "amount_usd": 150.00,
  "crypto": "BTC"
}
```

### Get Payment Status

```http
GET /orders/{order_id}

Response 200:
{
  "id": "pay_xyz789",
  "status": "pending",
  "merchant_id": "merchant_abc123",
  "provider": "stripe",
  "amount_usd": 150.00,
  "amount_crypto": 0.00375,
  "crypto": "BTC",
  "tx_hash": null,
  "created_at": "2026-04-29T10:30:00Z",
  "webhook_delivered": false
}
```

### List Payments

```http
GET /payments?merchant_id=merchant_abc&status=completed&limit=50&skip=0

Response 200:
[
  {
    "id": "pay_123",
    "merchant_id": "merchant_abc",
    "provider": "stripe",
    "status": "completed",
    "amount_usd": 500.00,
    "crypto": "BTC",
    "tx_hash": "0xabc123...",
    "created_at": "2026-04-29T09:15:00Z"
  }
]
```

---

## Merchant Management

### Register Merchant

```http
POST /merchants/register
Content-Type: application/json

{
  "company_name": "Acme Corp",
  "email": "admin@acme.com",
  "country": "AE",
  "webhook_url": "https://acme.com/payments/webhook"
}

Response 201:
{
  "merchant_id": "merchant_new_456",
  "api_key": "sk_test_acme_123456",
  "status": "pending_verification",
  "kyc_next_steps": [
    "Upload company registration certificate",
    "Upload director ID",
    "Run verification pipeline"
  ]
}
```

### Get Merchant Profile

```http
GET /merchants/{merchant_id}
X-Api-Key: sk_test_acme_123456

Response 200:
{
  "id": "merchant_abc123",
  "company_name": "Acme Corp",
  "email": "admin@acme.com",
  "country": "AE",
  "kyc_status": "approved",
  "kyc_score": 78,
  "api_key": "sk_test_acme_123456",
  "webhook_url": "https://acme.com/payments/webhook",
  "limits": {
    "daily_usd": 50000,
    "transaction_max_usd": 10000
  },
  "total_volume_usd": 125000,
  "active": true,
  "created_at": "2026-04-15T10:00:00Z"
}
```

### Activate Merchant

```http
POST /merchants/{merchant_id}/activate
X-Api-Key: sk_test_acme_123456

Response 200:
{
  "merchant_id": "merchant_abc123",
  "status": "active",
  "api_key": "sk_test_acme_123456",
  "activated_at": "2026-04-29T10:30:00Z"
}
```

---

## KYC & Verification

### Upload Document

```http
POST /verify/upload
Content-Type: multipart/form-data

merchant_id: merchant_abc123
doc_type: company_registration (or: director_id, bank_statement, trade_license)
file: <binary PDF or image>

Response 201:
{
  "document_id": "doc_new_111",
  "merchant_id": "merchant_abc123",
  "doc_type": "company_registration",
  "filename": "ded_certificate.pdf",
  "extracted_text": "ACME CORP LLC, DED 123456, established 2020...",
  "confidence": 0.92,
  "processed_at": "2026-04-29T10:25:00Z"
}
```

### Run Verification

```http
POST /verify/run
Content-Type: application/json

{
  "merchant_id": "merchant_abc123"
}

Response 200:
{
  "merchant_id": "merchant_abc123",
  "verification_id": "ver_xyz_789",
  "risk_score": 42,
  "decision": "PENDING_REVIEW",
  "decision_reasoning": "Risk score in review range (35-64). Company verified in OpenCorporates, but recent director changes warrant manual review.",
  "company_data": {
    "registration_number": "DED-123456",
    "company_name": "ACME CORP LLC",
    "country": "AE",
    "founded_year": 2020,
    "directors": ["John Doe", "Jane Smith"]
  },
  "completed_at": "2026-04-29T10:30:00Z"
}
```

### Get KYC Status

```http
GET /verify/{merchant_id}

Response 200:
{
  "merchant_id": "merchant_abc123",
  "kyc_status": "approved",
  "kyc_tier": "full",
  "risk_score": 78,
  "decision": "APPROVED",
  "documents": [
    {
      "id": "doc_123",
      "type": "company_registration",
      "filename": "cert.pdf",
      "confidence": 0.95,
      "uploaded_at": "2026-04-28T14:30:00Z"
    }
  ],
  "last_review": "2026-04-28T15:00:00Z"
}
```

---

## Provider Management

### List All Providers

```http
GET /providers?verified_only=false

Response 200:
[
  {
    "id": "stripe",
    "name": "Stripe",
    "type": "card",
    "status": "PRODUCTION",
    "verified": true,
    "fees_pct": 2.9,
    "settlement_time_hours": 24,
    "kyc_limit_usd": 5000,
    "support_crypto": ["BTC", "ETH"]
  },
  {
    "id": "transak",
    "name": "Transak",
    "type": "fiat_to_crypto",
    "status": "PRODUCTION",
    "verified": true,
    "fees_pct": 4.5,
    "settlement_time_hours": 12,
    "kyc_limit_usd": 25000,
    "support_crypto": ["BTC", "ETH", "USDC"]
  }
]
```

### Get Provider Status

```http
GET /providers/{provider_id}/status

Response 200:
{
  "provider_id": "stripe",
  "name": "Stripe",
  "online": true,
  "latency_ms": 145,
  "last_payment": "2026-04-29T10:25:00Z",
  "webhook_success_rate": 0.998,
  "webhook_failures_24h": 2,
  "alerts": []
}
```

### Rank Providers

```http
GET /providers/rank?crypto=BTC&sort_by=quality

Response 200:
[
  {
    "rank": 1,
    "provider_id": "stripe",
    "score": 95,
    "verified": true,
    "settlement_time_hours": 24,
    "fees_pct": 2.9,
    "spot_credit": true
  },
  {
    "rank": 2,
    "provider_id": "transak",
    "score": 88,
    "verified": true,
    "settlement_time_hours": 12,
    "fees_pct": 4.5,
    "spot_credit": false
  }
]
```

---

## Admin Endpoints

### Dashboard Statistics

```http
GET /dashboard/stats
X-Api-Key: sk_live_admin_key

Response 200:
{
  "total_payments": 1245,
  "total_volume_usd": 850000,
  "active_merchants": 42,
  "kyc_approvals": 38,
  "kyc_rejections": 2,
  "kyc_pending": 2,
  "providers_live": 6,
  "failed_webhooks_24h": 3,
  "avg_payment_time_minutes": 8.5
}
```

### Payment Timeline Chart

```http
GET /dashboard/chart?days=30&group_by=day

Response 200:
{
  "dates": ["2026-03-30", "2026-03-31", "2026-04-01", ...],
  "volumes_usd": [12500, 15300, 18200, ...],
  "payment_counts": [45, 52, 61, ...],
  "avg_transaction_usd": [277.78, 294.23, 298.36, ...]
}
```

### Update Provider Configuration

```http
PUT /admin/providers/{provider_id}
X-Api-Key: sk_live_admin_key

{
  "enabled": true,
  "fees_pct": 2.9,
  "kyc_limit_usd": 5000,
  "max_per_transaction": 25000
}

Response 200:
{
  "provider_id": "stripe",
  "updated": true,
  "updated_at": "2026-04-29T10:30:00Z"
}
```

---

## Webhooks

### Payment Status Update Webhook

**Sent to**: Your `webhook_url` when payment status changes

```http
POST {your_webhook_url}
Content-Type: application/json
X-BeastPay-Signature: hmac_sha256_signature

{
  "event": "payment.completed",
  "payment_id": "pay_abc123",
  "merchant_id": "merchant_xyz",
  "status": "completed",
  "amount_usd": 150.00,
  "amount_crypto": 0.00375,
  "crypto": "BTC",
  "tx_hash": "0xabc123...",
  "provider": "stripe",
  "timestamp": "2026-04-29T10:35:00Z"
}
```

**Response Expected**: `200 OK` with `{"status": "received"}`

### Webhook Signature Verification

All BeastPay webhooks are signed with HMAC-SHA256. Verify with:

```python
import hmac
import hashlib

signature = request.headers['X-BeastPay-Signature']
secret = "your_webhook_secret"
body = request.body

expected = hmac.new(
    secret.encode(),
    body,
    hashlib.sha256
).hexdigest()

assert hmac.compare_digest(signature, expected)
```

---

## Error Responses

### 400 Bad Request

```json
{
  "detail": [
    {
      "loc": ["body", "amount_usd"],
      "msg": "ensure this value is greater than 0",
      "type": "value_error.number.not_gt"
    }
  ]
}
```

### 401 Unauthorized

```json
{
  "detail": "Invalid API key"
}
```

### 404 Not Found

```json
{
  "detail": "Merchant merchant_xyz not found"
}
```

### 500 Internal Server Error

```json
{
  "detail": "Internal server error. Check logs for details."
}
```

---

## Rate Limiting

**Current**: No rate limits (planned for Q3 2026)

**Planned limits per API key:**
- 100 requests/minute
- 10,000 requests/day

---

## Pagination

List endpoints support pagination via `limit` and `skip` parameters:

```http
GET /payments?merchant_id=merchant_abc&limit=50&skip=100

# Returns items 100-149
```

---

## Status Codes

| Code | Meaning |
|------|---------|
| 200 | OK - Request succeeded |
| 201 | Created - Resource created |
| 400 | Bad Request - Invalid input |
| 401 | Unauthorized - Missing/invalid API key |
| 404 | Not Found - Resource doesn't exist |
| 500 | Internal Server Error - Server error |

---

## Testing with cURL

```bash
# Register merchant
curl -X POST http://localhost:8000/merchants/register \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Test Corp",
    "email": "test@example.com",
    "country": "AE"
  }'

# Create payment
curl -X POST http://localhost:8000/orders \
  -H "X-Api-Key: sk_test_your_key" \
  -H "Content-Type: application/json" \
  -d '{
    "merchant_id": "merchant_xyz",
    "crypto": "BTC",
    "amount_usd": 100
  }'

# Get payment status
curl -H "X-Api-Key: sk_test_your_key" \
  http://localhost:8000/orders/pay_xyz789

# List payments
curl -H "X-Api-Key: sk_test_your_key" \
  "http://localhost:8000/payments?status=completed&limit=10"
```

---

**Last Updated**: 2026-04-29  
**API Version**: 1.0.0

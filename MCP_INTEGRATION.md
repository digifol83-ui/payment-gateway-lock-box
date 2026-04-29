# MCP Integration: Claude Code + BeastPay

**Enable Claude Code IDE to manage BeastPay payments, merchants, and KYC directly from the editor.**

---

## 🎯 Overview

BeastPay's **Model Context Protocol (MCP)** server exposes payment gateway functions to Claude Code. This allows you to:

- **Query payments**: List, filter, and monitor payment status from the IDE
- **Manage merchants**: Register, verify, and activate merchants via code assistant
- **Run verification**: Trigger KYC pipelines and view risk scores
- **Select providers**: Use Claude to rank and choose best payment provider
- **Monitor webhooks**: Debug webhook deliveries and status updates
- **Execute admin tasks**: Update provider configs, view dashboards

---

## 📦 MCP Server Setup

### Location

```
payment-gateway/mcp_beastpay/
├── server.py                      # MCP server entrypoint
├── handlers/
│   ├── payment.py                 # Payment resource functions
│   ├── merchant.py                # Merchant operations
│   ├── verification.py            # KYC + risk scoring
│   └── provider.py                # Provider selection
└── resources/
    ├── payments.json              # JSON schema
    ├── merchants.json
    └── providers.json
```

### Start MCP Server

```bash
cd /home/kali/payment-gateway
python mcp_beastpay/server.py
```

Or via Claude Code `.claude/settings.json`:

```json
{
  "mcpServers": {
    "beastpay": {
      "command": "python",
      "args": ["/home/kali/payment-gateway/mcp_beastpay/server.py"]
    }
  }
}
```

---

## 🔗 Available Resources (Claude Code Prompts)

Use these resource URIs in Claude Code to access BeastPay functions.

### Payments Resource

#### List Payments
```
Resource URI: beastpay://payments/list
Parameters:
  - merchant_id (optional): Filter by merchant
  - status (optional): "pending", "completed", "failed"
  - limit (optional): Default 50
  - skip (optional): For pagination

Example Claude prompt:
"@beastpay List all completed payments for merchant abc123 in the last 7 days"

Returns:
[
  {
    "id": "pay_xxx",
    "merchant_id": "merchant_yyy",
    "provider": "stripe",
    "amount_usd": 150.00,
    "crypto": "BTC",
    "status": "completed",
    "tx_hash": "0x123...",
    "created_at": "2026-04-29T10:30:00Z"
  }
]
```

#### Get Payment Details
```
Resource URI: beastpay://payments/{payment_id}
Parameters:
  - payment_id: Payment ID (required)

Example Claude prompt:
"@beastpay Get full details for payment pay_abc123"

Returns:
{
  "id": "pay_abc123",
  "merchant_id": "merchant_xyz",
  "provider": "stripe",
  "provider_order_id": "pi_1234567890",
  "amount_usd": 500.00,
  "amount_crypto": 0.0125,
  "crypto": "BTC",
  "status": "completed",
  "tx_hash": "0xabc123...",
  "webhook_status": "delivered",
  "created_at": "2026-04-29T09:15:00Z",
  "completed_at": "2026-04-29T09:35:00Z"
}
```

#### Create Payment
```
Resource URI: beastpay://payments/create
Parameters:
  - merchant_id: Merchant ID (required)
  - crypto: Target crypto ("BTC", "ETH", etc) (required)
  - amount_usd: Amount in USD (required)
  - webhook_url: Callback URL (optional)
  - metadata: Custom data dict (optional)

Example Claude prompt:
"@beastpay Create payment: merchant_abc123 wants to pay 100 USD for BTC"

Returns:
{
  "payment_id": "pay_new_123",
  "order_id": "order_xyz",
  "provider": "stripe",
  "payment_url": "https://checkout.stripe.com/pay/...",
  "expires_at": "2026-04-29T10:30:00Z"
}
```

### Merchants Resource

#### List Merchants
```
Resource URI: beastpay://merchants/list
Parameters:
  - kyc_status (optional): "approved", "pending", "rejected"
  - country (optional): Country code
  - limit (optional): Default 50

Example Claude prompt:
"@beastpay Show all active merchants in UAE"

Returns:
[
  {
    "id": "merchant_abc",
    "company_name": "SICHER MAYOR COMMERCIAL BROKERS",
    "email": "info@beastpay.com",
    "country": "AE",
    "kyc_status": "approved",
    "kyc_score": 90,
    "api_key": "sk_live_xxx",
    "webhook_url": "https://...",
    "created_at": "2026-01-15T00:00:00Z"
  }
]
```

#### Get Merchant Profile
```
Resource URI: beastpay://merchants/{merchant_id}
Parameters:
  - merchant_id: Merchant ID (required)

Example Claude prompt:
"@beastpay Get profile for merchant fd8179d9"

Returns:
{
  "id": "fd8179d9-a881-47d4-9a14-3438527ea6a7",
  "company_name": "SICHER MAYOR COMMERCIAL BROKERS L.L.C",
  "email": "info@beastpay.ae",
  "country": "AE",
  "kyc_status": "approved",
  "kyc_score": 90,
  "api_key": "sk_live_beastpay_123",
  "limits": {
    "daily_usd": 50000,
    "transaction_max_usd": 10000
  },
  "webhooks_delivered": 1245,
  "total_volume_usd": 850000,
  "active": true
}
```

#### Register Merchant
```
Resource URI: beastpay://merchants/register
Parameters:
  - company_name: Legal company name (required)
  - email: Contact email (required)
  - country: Country code (required)
  - webhook_url: Callback URL (optional)

Example Claude prompt:
"@beastpay Register merchant: Acme Corp, email acme@example.com, UAE"

Returns:
{
  "merchant_id": "merchant_new_456",
  "api_key": "sk_test_acme_789",
  "status": "pending_verification",
  "kyc_next_steps": ["Upload company registration", "Upload director ID"]
}
```

### Verification Resource

#### Get KYC Status
```
Resource URI: beastpay://verification/{merchant_id}
Parameters:
  - merchant_id: Merchant ID (required)

Example Claude prompt:
"@beastpay What's the KYC status for merchant_abc123?"

Returns:
{
  "merchant_id": "merchant_abc123",
  "kyc_status": "approved",
  "kyc_score": 78,
  "kyc_tier": "full",
  "decision": "APPROVED",
  "decision_reasoning": "Company verified in OpenCorporates, low risk jurisdiction, clean director history",
  "documents": [
    {
      "id": "doc_123",
      "type": "company_registration",
      "filename": "cert.pdf",
      "extracted_text": "ACME CORP INC, DED 123456, founded 2020",
      "confidence": 0.95
    }
  ],
  "last_review": "2026-04-28T14:30:00Z"
}
```

#### Run Verification
```
Resource URI: beastpay://verification/run
Parameters:
  - merchant_id: Merchant ID (required)

Example Claude prompt:
"@beastpay Run full KYC verification for merchant_abc123"

Returns:
{
  "merchant_id": "merchant_abc123",
  "verification_id": "ver_xyz_789",
  "status": "completed",
  "risk_score": 42,
  "decision": "PENDING_REVIEW",
  "decision_reasoning": "Risk score 42 falls in review range. Manual check recommended.",
  "company_data": {
    "registration_number": "DED-123456",
    "company_name": "Acme Corp L.L.C",
    "country": "AE",
    "founded_year": 2020
  }
}
```

#### Upload Document
```
Resource URI: beastpay://verification/upload
Parameters:
  - merchant_id: Merchant ID (required)
  - doc_type: "company_registration", "director_id", "bank_statement" (required)
  - file_path: Local file path (required)

Example Claude prompt:
"@beastpay Upload company registration PDF for merchant_abc123 from /uploads/cert.pdf"

Returns:
{
  "document_id": "doc_new_111",
  "merchant_id": "merchant_abc123",
  "doc_type": "company_registration",
  "filename": "cert.pdf",
  "extracted_text": "ACME CORP LLC, DED 123456...",
  "confidence": 0.92,
  "status": "processed"
}
```

### Providers Resource

#### List Providers
```
Resource URI: beastpay://providers/list
Parameters:
  - verified_only (optional): Boolean, default false
  - crypto (optional): Filter by crypto support

Example Claude prompt:
"@beastpay Show all verified payment providers"

Returns:
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

#### Get Provider Status
```
Resource URI: beastpay://providers/{provider_id}
Parameters:
  - provider_id: Provider ID like "stripe", "transak" (required)

Example Claude prompt:
"@beastpay Is Stripe live? What's the latency?"

Returns:
{
  "provider_id": "stripe",
  "name": "Stripe",
  "online": true,
  "latency_ms": 145,
  "balance_usd": 12500,
  "last_payment": "2026-04-29T10:25:00Z",
  "webhook_success_rate": 0.998,
  "alerts": []
}
```

#### Rank Providers
```
Resource URI: beastpay://providers/rank
Parameters:
  - crypto: Target crypto (optional, default "BTC")
  - sort_by: "quality", "speed", "fees" (optional)

Example Claude prompt:
"@beastpay Rank providers for ETH payments by speed"

Returns:
[
  {
    "rank": 1,
    "provider_id": "stripe",
    "name": "Stripe",
    "score": 95,
    "verified": true,
    "speed": 90,
    "fees_pct": 2.9,
    "spot_credit": true,
    "recommended": true
  },
  {
    "rank": 2,
    "provider_id": "transak",
    "name": "Transak",
    "score": 88,
    "verified": true,
    "speed": 85,
    "fees_pct": 4.5,
    "spot_credit": false
  }
]
```

---

## 🛠️ Claude Code Integration Examples

### Example 1: Process a Payment via Claude Code

**Prompt in Claude Code:**
```
@beastpay Help me process a payment:
- Merchant: fd8179d9-a881-47d4-9a14-3438527ea6a7
- Amount: $250 USD
- Crypto: BTC
- Pick the best provider
- Return payment URL

Show me the step-by-step flow.
```

**Claude Code Response:**
```
I'll help you process this payment. Let me:

1. Rank providers for BTC
2. Select the best one
3. Create the payment
4. Return the payment URL

Executing...
```

**Behind the scenes:**
```python
# Claude uses MCP to:
providers = mcp.call('beastpay://providers/rank?crypto=BTC')
best_provider = providers[0]  # Stripe

payment = mcp.call('beastpay://payments/create', {
    'merchant_id': 'fd8179d9-a881-47d4-9a14-3438527ea6a7',
    'crypto': 'BTC',
    'amount_usd': 250
})

# Returns payment URL to customer
```

### Example 2: Verify a Merchant

**Prompt in Claude Code:**
```
@beastpay I have a new merchant:
- Company: Acme Trading Ltd
- Email: hello@acme.ae
- Country: UAE

Register them, then upload this doc: /uploads/ded_cert.pdf

What's their KYC status?
```

**Claude Code does:**
```python
# 1. Register merchant
merchant = mcp.call('beastpay://merchants/register', {
    'company_name': 'Acme Trading Ltd',
    'email': 'hello@acme.ae',
    'country': 'AE'
})
merchant_id = merchant['merchant_id']

# 2. Upload document
mcp.call('beastpay://verification/upload', {
    'merchant_id': merchant_id,
    'doc_type': 'company_registration',
    'file_path': '/uploads/ded_cert.pdf'
})

# 3. Run verification
kyc = mcp.call('beastpay://verification/run', {
    'merchant_id': merchant_id
})

# Display results
print(f"KYC Score: {kyc['risk_score']}")
print(f"Decision: {kyc['decision']}")
```

### Example 3: Monitor Payment Status

**Prompt in Claude Code:**
```
@beastpay Show me:
- All pending payments from today
- Group by merchant
- Alert if any are > $5000
```

**Claude Code uses:**
```python
payments = mcp.call('beastpay://payments/list', {
    'status': 'pending',
    'limit': 200
})

by_merchant = {}
for p in payments:
    mid = p['merchant_id']
    if mid not in by_merchant:
        by_merchant[mid] = []
    by_merchant[mid].append(p)
    
    if p['amount_usd'] > 5000:
        print(f"⚠️ ALERT: ${p['amount_usd']} payment ({p['id']})")
```

---

## 🔌 Adding New Functions to MCP

To expose a new BeastPay function to Claude Code:

### Step 1: Create handler in `mcp_beastpay/handlers/`

```python
# mcp_beastpay/handlers/payment.py

async def list_payments(merchant_id: str = None, status: str = None,
                        limit: int = 50, skip: int = 0) -> list:
    """List payments with optional filters"""
    # Implementation...
    return payments
```

### Step 2: Register in MCP server

```python
# mcp_beastpay/server.py

from handlers import payment

mcp_server.register_resource(
    uri='beastpay://payments/list',
    handler=payment.list_payments,
    description='List all payments with filters'
)
```

### Step 3: Restart MCP server

```bash
python mcp_beastpay/server.py
```

### Step 4: Use in Claude Code

```
@beastpay [your prompt using the new function]
```

---

## 🔐 Authentication & Security

MCP calls authenticate via:

1. **API Key**: Passed in `.env` as `ADMIN_API_KEY`
2. **Merchant Context**: MCP identifies the merchant from the API key
3. **Rate Limiting**: Built-in per-merchant (plan: implement global)
4. **Encryption**: Sensitive data (API keys, tokens) always encrypted at rest

### Example `.env` for MCP:

```bash
# Enable MCP server
MCP_ENABLED=true
MCP_PORT=3000

# Authentication
ADMIN_API_KEY=sk_live_admin_abc123xyz
MERCHANT_API_KEY=sk_live_merchant_xyz789

# Database
DATABASE_URL=sqlite:///payments.db

# Providers
TRANSAK_API_KEY=...
STRIPE_SECRET_KEY=...
```

---

## 📊 Dashboard Integration

The admin panel (`/admin`) also integrates with MCP for real-time metrics:

```html
<!-- web/admin.html -->
<script>
  // Fetch from MCP
  const providers = await fetch('http://localhost:3000/providers/rank')
  const payments = await fetch('http://localhost:3000/payments/list?limit=100')
  
  // Display on dashboard
  renderProviderChart(providers)
  renderPaymentTimeline(payments)
</script>
```

---

## 🚀 Roadmap

- [ ] **Real-time Webhooks**: WebSocket connection for live payment updates
- [ ] **Advanced Filtering**: Date ranges, provider filters, risk score filters
- [ ] **Bulk Operations**: Batch create payments, bulk verify merchants
- [ ] **Audit Logs**: Track all MCP calls for compliance
- [ ] **Custom Alerts**: Set rules for payment monitoring
- [ ] **Analytics API**: Export data for custom dashboards

---

## 📞 Troubleshooting

### MCP Server won't start

```bash
# Check port 3000 is available
lsof -i :3000

# Check logs
python -u mcp_beastpay/server.py

# Ensure .env has ADMIN_API_KEY set
grep ADMIN_API_KEY .env
```

### Claude Code can't find beastpay resources

```json
// .claude/settings.json - verify MCP is registered
{
  "mcpServers": {
    "beastpay": {
      "command": "python",
      "args": ["/home/kali/payment-gateway/mcp_beastpay/server.py"]
    }
  }
}
```

### Payment creation fails

- Verify merchant exists: `@beastpay Get merchant fd8179d9`
- Check provider is live: `@beastpay Is stripe online?`
- View server logs: `tail -f server.log`

---

**Maintained by**: BeastPay Development  
**Last Updated**: 2026-04-29  
**Contact**: digifol83@gmail.com

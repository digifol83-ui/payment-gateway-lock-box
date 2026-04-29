# BeastPay OpenClaw Payment Gateway - Architecture

**Project**: BeastPay OpenClaw Payment Gateway  
**License Owner**: SICHER MAYOR COMMERCIAL BROKERS L.L.C (Dubai DED 841208)  
**Status**: Production-Ready  
**Last Updated**: 2026-04-29

---

## 🏗️ System Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        BEASTPAY PAYMENT GATEWAY                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌──────────────────┐     ┌──────────────────┐  ┌─────────────┐    │
│  │  Client Web UI   │     │ Claude Code MCP  │  │ Admin Panel │    │
│  │ (HTML/JS)        │────▶│ Interface        │  │ (FastAPI)   │    │
│  └──────────────────┘     └──────────────────┘  └─────────────┘    │
│         │                         │                      │          │
│         └─────────────────────────┴──────────────────────┘          │
│                                   │                                  │
│                     ┌─────────────▼──────────────┐                  │
│                     │   FastAPI Server           │                  │
│                     │   (server.py)              │                  │
│                     │   - Async Routes           │                  │
│                     │   - WebSocket Support      │                  │
│                     │   - Webhook Handling       │                  │
│                     └─────────────┬──────────────┘                  │
│                                   │                                  │
│         ┌─────────────────────────┼─────────────────────────┐       │
│         │                         │                         │       │
│    ┌────▼─────┐          ┌────────▼──────┐         ┌────────▼──┐  │
│    │ Provider  │          │  Database     │         │  Telegram │  │
│    │ Adapters  │          │  (SQLite)     │         │  WhatsApp │  │
│    │           │          │               │         │           │  │
│    │ • Transak │          │ • merchants   │         │ Notif.    │  │
│    │ • Stripe  │          │ • payments    │         │ Service   │  │
│    │ • MoonPay │          │ • kyc_records │         │           │  │
│    │ • Ziina   │          │ • credentials │         └───────────┘  │
│    │ • Plisio  │          │ • profiles    │                        │
│    │ • Guardarian          │ • documents   │                        │
│    └────┬─────┘          └────────┬──────┘                        │
│         │                         │                                │
│    ┌────▼─────────────────────────▼────┐                         │
│    │  Verification Engine (Claude AI)   │                         │
│    │  verification/engine.py            │                         │
│    │  - Document Extraction (Claude)    │                         │
│    │  - Risk Scoring (0-100)            │                         │
│    │  - KYC Decision Logic              │                         │
│    └────┬─────────────────────────┬────┘                         │
│         │                         │                                │
│    ┌────▼──┐    ┌──────────────┐  │                              │
│    │OpenAI │    │ Government   │  │                              │
│    │Codex  │    │ Data Sources │  │                              │
│    │(Plan) │    │ (APIs)       │  │                              │
│    └───────┘    └──────────────┘  │                              │
│                                   │                                │
│         ┌─────────────────────────┴──────────────────┐             │
│         │                                            │             │
│    ┌────▼──────────────┐                  ┌────────▼──────┐      │
│    │ Encryption Layer  │                  │  MCP Server   │      │
│    │ (AES-256-GCM)     │                  │ (Integration) │      │
│    │ verification/     │                  │               │      │
│    │ encryption.py     │                  │ • Functions   │      │
│    └───────────────────┘                  │ • Data Models │      │
│                                           │ • Webhooks    │      │
│                                           └───────────────┘      │
│                                                                    │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 📊 Data Flow Diagrams

### Payment Processing Flow

```
START
  │
  ▼
┌─────────────────────────────┐
│ Customer Initiates Payment  │
│ GET /buy (frontend)         │
└────────────┬────────────────┘
             │
             ▼
┌─────────────────────────────┐
│ Load Payment Form            │
│ web/checkout-*.html          │
│ (Transak SDK, Stripe, etc)  │
└────────────┬────────────────┘
             │
             ▼
┌─────────────────────────────┐
│ Validate KYC Tier            │
│ Amount < FREE_LIMIT?         │
│ FREE vs EMAIL vs SUMSUB      │
└────────────┬────────────────┘
             │
      ┌──────┴──────┐
      │             │
      ▼             ▼
   ┌───┐        ┌─────────────┐
   │FREE        │ KYC Gateway │
   │            │ (Sumsub)    │
   │            └────┬────────┘
   │                 │
   │            ┌────▼──────┐
   │            │ Verify ID │
   │            │ + Proof   │
   │            └────┬──────┘
   │                 │
   └─────────┬───────┘
             │
             ▼
┌─────────────────────────────┐
│ Select Payment Provider      │
│ forceverify.best(crypto)    │
│ (Rank by verified, fast)    │
└────────────┬────────────────┘
             │
             ▼
┌─────────────────────────────┐
│ Create Order                 │
│ POST /orders (provider)      │
│ → payment_links table        │
└────────────┬────────────────┘
             │
             ▼
┌─────────────────────────────┐
│ Customer Pays (Provider UI) │
│ Card / Bank Transfer / etc  │
└────────────┬────────────────┘
             │
             ▼
┌─────────────────────────────┐
│ Provider Webhook             │
│ POST /webhooks/{provider}   │
│ Status: pending→completed   │
└────────────┬────────────────┘
             │
             ▼
┌─────────────────────────────┐
│ Update Database             │
│ payments.status = complete  │
│ lockbox_transactions entry  │
└────────────┬────────────────┘
             │
             ▼
┌─────────────────────────────┐
│ Send Notifications          │
│ Telegram + WhatsApp         │
│ Merchant + Customer         │
└────────────┬────────────────┘
             │
             ▼
┌─────────────────────────────┐
│ Crypto Transfer             │
│ wallet.py (if applicable)   │
│ OR manual settlement        │
└────────────┬────────────────┘
             │
             ▼
            END
```

### Verification Pipeline Flow

```
START: Merchant Onboarding
  │
  ▼
┌──────────────────────────────────┐
│ Create Merchant Profile          │
│ POST /merchants/register         │
│ merchant_profiles table          │
└──────────────┬───────────────────┘
               │
               ▼
┌──────────────────────────────────┐
│ Upload Company Documents         │
│ POST /verify/upload              │
│ company_documents table          │
└──────────────┬───────────────────┘
               │
               ▼
┌──────────────────────────────────┐
│ VerificationEngine.run_pipeline()│
│ verification/engine.py           │
└──────────────┬───────────────────┘
               │
       ┌───────┼───────┐
       │       │       │
       ▼       ▼       ▼
    ┌──┐  ┌───────┐  ┌─────────┐
    │1.│  │   2.  │  │    3.   │
    │  │  │       │  │         │
    │Co│  │Extract│  │ Risk    │
    │mp│  │OCR    │  │ Score   │
    │an│  │(Claude│  │ (0-100) │
    │y │  │ AI)   │  │         │
    │  │  │       │  │         │
    │Lo│  │ Extract│ │ Weights│
    │ok│  │ • Reg# │  │ • Age  │
    │up│  │ • Dir. │  │ • Type │
    │  │  │ • Cap  │  │ • Risk │
    └──┘  └───────┘  └─────────┘
       │       │       │
       └───────┼───────┘
               │
               ▼
┌──────────────────────────────────┐
│ Decision Logic                   │
│ Risk Score Threshold             │
└──────────────┬───────────────────┘
               │
        ┌──────┼──────┬──────┐
        │      │      │      │
        ▼      ▼      ▼      ▼
      ┌──┐  ┌──┐  ┌────┐  ┌──┐
      │≥65 │ │35-│ │<35 │ │Manual
      │    │ │64 │ │    │ │Review
      │APR │ │PRD│ │REJ │ │Override
      │OVD │ │VD │ │ECT │ │
      └──┘  └──┘  └────┘  └──┘
        │      │      │      │
        └──────┼──────┼──────┘
               │
               ▼
┌──────────────────────────────────┐
│ Store Result                     │
│ kyc_records.status =             │
│ verified/pending_review/rejected │
└──────────────┬───────────────────┘
               │
               ▼
┌──────────────────────────────────┐
│ Activate Merchant (if approved)  │
│ POST /merchants/{id}/activate    │
│ Set API key + webhook_url        │
└──────────────┬───────────────────┘
               │
               ▼
┌──────────────────────────────────┐
│ Register Gateways (if needed)    │
│ stripe_activate.py               │
│ sumsub_provision.py              │
└──────────────┬───────────────────┘
               │
               ▼
              END: Ready to Accept Payments
```

---

## 📁 Directory Structure

```
payment-gateway/
├── ARCHITECTURE.md                 # This file
├── FUNCTIONS.md                    # Function reference
├── MCP_INTEGRATION.md              # Claude Code MCP setup
├── CODEX_INTEGRATION.md            # Future Codex plans
├── README.md                       # GitHub main readme
├── CLAUDE.md                       # AI assistant guidance
│
├── server.py                       # FastAPI main app
├── config.py                       # Configuration constants
├── database.py                     # SQLite schema + helpers
│
├── providers/                      # Payment provider adapters
│   ├── __init__.py                 # Factory + metadata
│   ├── transak.py                  # Fiat→Crypto
│   ├── stripe.py                   # Card payments
│   ├── moonpay.py                  # Crypto-onramp
│   ├── plisio.py                   # Crypto-direct
│   ├── coinremitter.py             # Crypto wallet gen
│   ├── ziina.py                    # AED payments
│   ├── guardarian.py               # P2P trading
│   └── finchpay.py                 # Custom integration
│
├── verification/                   # KYC + risk engine
│   ├── engine.py                   # VerificationEngine class
│   ├── encryption.py               # AES-256-GCM crypto
│   └── __init__.py                 # Exports
│
├── web/                            # Frontend HTML/JS
│   ├── index.html                  # Home page
│   ├── checkout-transak.html       # Transak checkout
│   ├── checkout-stripe.html        # Stripe checkout
│   ├── admin.html                  # Merchant dashboard
│   └── monitor.html                # Payment monitor
│
├── docs/                           # GitHub documentation
│   ├── API.md                      # REST API reference
│   ├── PROVIDERS.md                # Provider details
│   ├── KYC.md                      # KYC flow
│   ├── DEPLOYMENT.md               # Production checklist
│   └── SECURITY.md                 # Security audit
│
├── mcp_beastpay/                   # MCP Server (Claude Code)
│   ├── __init__.py
│   ├── server.py                   # MCP server entrypoint
│   ├── handlers/
│   │   ├── payment.py              # Payment operations
│   │   ├── merchant.py             # Merchant management
│   │   ├── verification.py         # KYC operations
│   │   └── provider.py             # Provider selection
│   └── resources/
│       ├── payments.json           # Payment schema
│       ├── merchants.json          # Merchant schema
│       └── providers.json          # Provider list
│
├── tests/                          # Unit tests
│   ├── test_beastpay.py
│   ├── test_providers.py
│   └── test_verification.py
│
├── stripe_activate.py              # One-shot: Stripe setup
├── sumsub_provision.py             # One-shot: Sumsub setup
├── .env.example                    # Environment template
├── .gitignore                      # Git ignore rules
├── payments.db                     # SQLite database
└── start.sh / stop.sh              # Process management
```

---

## 🔄 Provider Integration Lifecycle

```
┌─────────────────────────────────────────┐
│ New Provider Request                    │
│ e.g., "Add Stripe integration"          │
└─────────────┬───────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│ 1. Create Adapter                       │
│    providers/new_provider.py            │
│    • Implement create_order()           │
│    • Implement get_status()             │
│    • Implement handle_webhook()         │
└─────────────┬───────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│ 2. Register in Factory                  │
│    providers/__init__.py                │
│    • Add to PROVIDER_REGISTRY           │
│    • Add metadata (fees, KYC, etc)      │
└─────────────┬───────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│ 3. Configure Environment                │
│    .env                                 │
│    • API keys (encrypted storage)       │
│    • Webhook secret                     │
│    • Test vs Production mode            │
└─────────────┬───────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│ 4. Add Routes in Server                 │
│    server.py                            │
│    • POST /orders (create)              │
│    • GET /orders/{id} (status)          │
│    • POST /webhooks/provider (webhook)  │
└─────────────┬───────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│ 5. Test                                 │
│    tests/test_providers.py              │
│    • Mock provider API calls            │
│    • Verify webhook parsing             │
│    • Test error handling                │
└─────────────┬───────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│ 6. Deploy & Activate                    │
│    • Run one-shot activation script     │
│    • Or environment-based initialization│
└─────────────┬───────────────────────────┘
              │
              ▼
┌─────────────────────────────────────────┐
│ Live: Provider operational              │
│ Monitored via admin dashboard           │
└─────────────────────────────────────────┘
```

---

## 🔐 Security Layers

| Layer | Mechanism | File(s) |
|-------|-----------|---------|
| **Credential Storage** | AES-256-GCM encryption | `verification/encryption.py` |
| **API Authentication** | X-Api-Key header | `server.py` |
| **Webhook Verification** | Provider-specific HMAC | `providers/*.py` |
| **Database Constraints** | SQLite foreign keys, unique constraints | `database.py` |
| **Input Validation** | Pydantic models in FastAPI | `server.py` |
| **KYC Risk Scoring** | Multi-factor decision logic | `verification/engine.py` |
| **Merchant Rate Limiting** | (Future enhancement) | TBD |
| **Audit Logging** | Database transaction logs | `database.py` |

---

## 📈 Scalability & Future

### Current Limitations
- **SQLite**: Single-file, suitable for <100 concurrent users
- **Async**: FastAPI/httpx are async-ready, can scale to 1000+ concurrent
- **Webhook Polling**: Some providers require long-polling instead of webhooks

### Planned Enhancements

**Phase 1 (Q3 2026)**
- [ ] PostgreSQL migration for scalability
- [ ] Redis caching layer for provider status
- [ ] GraphQL API alongside REST

**Phase 2 (Q4 2026)**
- [ ] Codex integration for AI-driven underwriting
- [ ] Merchant API rate limiting + quota system
- [ ] Real-time balance sync across providers

**Phase 3 (2027)**
- [ ] Kubernetes deployment manifests
- [ ] Multi-region failover
- [ ] Merchant sub-accounts (white-label)

---

## 🚀 Getting Started

```bash
# Clone and setup
cd /home/kali/payment-gateway
source .env
pip install -r requirements.txt

# Run server
uvicorn server:app --host 0.0.0.0 --port 8000

# Admin UI
open http://localhost:8000/admin

# Run tests
pytest tests/ -v

# MCP Integration (Claude Code)
python mcp_beastpay/server.py
```

---

## 📞 Support & References

- **Docs**: `/docs` directory
- **API Swagger**: `http://localhost:8000/docs`
- **Admin Panel**: `http://localhost:8000/admin`
- **MCP Server**: `mcp_beastpay/server.py`
- **Issues**: GitHub Issues (beastpayment repo)

---

**Maintained by**: BeastPay Development Team  
**License**: Commercial (SICHER MAYOR)  
**Contact**: digifol83@gmail.com

# 🚀 BeastPay Payment Gateway

**A production-grade FastAPI payment gateway for fiat-to-crypto conversion with intelligent KYC and multi-provider support.**

![Status: Production Ready](https://img.shields.io/badge/Status-Production%20Ready-brightgreen)
![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-darkgreen)
![License: Commercial](https://img.shields.io/badge/License-Commercial%20(SICHER%20MAYOR)-orange)

---

## 📋 Overview

BeastPay is a **complete payment gateway solution** for merchants accepting fiat payments and converting to crypto. Built for **SICHER MAYOR COMMERCIAL BROKERS L.L.C** (Dubai, DED 841208).

### Key Features

✅ **Multi-Provider Support**
- Fiat→Crypto: Transak, MoonPay, FinchPay
- Card Payments: Stripe, Ziina (AED)
- Crypto-Direct: CoinRemitter, Plisio
- P2P: Guardarian

✅ **Intelligent KYC Pipeline**
- Document extraction via Claude AI (OCR)
- Risk scoring (0-100) with decision logic
- Support for UAE, UK, US company verification
- Automated approval/rejection/pending_review

✅ **Production-Ready**
- Async FastAPI with uvicorn
- SQLite (SQLite) database with encrypted credentials
- Webhook handling for all providers
- Telegram & WhatsApp notifications
- Admin dashboard with real-time metrics

✅ **Claude Code Integration**
- MCP server for IDE automation
- Query payments, manage merchants, run KYC from the editor
- No manual database access needed

✅ **Future-Ready**
- Codex integration roadmap for auto-generated adapters
- Scalable to PostgreSQL + Redis
- Kubernetes-ready architecture

---

## 🎯 Quick Start

### 1. Clone & Setup

```bash
cd /home/kali/payment-gateway
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your provider keys
```

### 2. Run Server

```bash
source .env
uvicorn server:app --host 0.0.0.0 --port 8000
```

**URLs:**
- 🌐 **Web UI**: http://localhost:8000
- 📊 **Admin**: http://localhost:8000/admin
- 📚 **API Docs**: http://localhost:8000/docs

### 3. Test Payment Flow

```bash
# Create merchant
curl -X POST http://localhost:8000/merchants/register \
  -H "Content-Type: application/json" \
  -d '{"company_name": "Acme Corp", "email": "admin@acme.com", "country": "AE"}'

# Create payment
curl -X POST http://localhost:8000/orders \
  -H "Content-Type: application/json" \
  -d '{
    "merchant_id": "merchant_xyz",
    "crypto": "BTC",
    "amount_usd": 100
  }'
```

---

## 📊 Architecture

```
┌──────────────────────────────────────────────────────┐
│         BeastPay Payment Gateway (FastAPI)            │
├──────────────────────────────────────────────────────┤
│                                                       │
│  ┌─────────────┐  ┌──────────────┐  ┌───────────┐  │
│  │  Web UI     │  │ Claude Code  │  │ Admin     │  │
│  │  (HTML/JS)  │  │ MCP Server   │  │ Dashboard │  │
│  └─────────────┘  └──────────────┘  └───────────┘  │
│         │                │                  │         │
│         └────────────────┴──────────────────┘         │
│                         │                             │
│              ┌──────────▼──────────┐                 │
│              │   FastAPI Routes    │                 │
│              │  (Async endpoints)  │                 │
│              └──────────┬──────────┘                 │
│                         │                             │
│        ┌────────────────┼────────────────┐           │
│        │                │                │           │
│   ┌────▼──┐      ┌─────▼──┐      ┌─────▼──┐        │
│   │ Stripe│      │Transak │      │Ziina   │        │
│   │ Plisio│      │MoonPay │      │Guardarian        │
│   └────────┘      └────────┘      └────────┘        │
│        │                │                │           │
│        └────────────────┼────────────────┘           │
│                    ┌────▼────┐                       │
│        ┌───────────▼──────────┴─────────┐            │
│        │      SQLite Database           │            │
│        │  • merchants   • payments       │            │
│        │  • kyc_records • credentials    │            │
│        │  (AES-256-GCM encrypted)       │            │
│        └────────────────────────────────┘            │
│                                                       │
│   ┌──────────────────────────────────────────┐      │
│   │   Verification Engine (Claude AI)        │      │
│   │   • OCR & document extraction            │      │
│   │   • Risk scoring (0-100)                 │      │
│   │   • KYC decision logic                   │      │
│   └──────────────────────────────────────────┘      │
│                                                       │
│   ┌──────────────────────────────────────────┐      │
│   │   Notifications                          │      │
│   │   • Telegram  • WhatsApp                 │      │
│   └──────────────────────────────────────────┘      │
│                                                       │
└──────────────────────────────────────────────────────┘
```

**See detailed architecture**: [ARCHITECTURE.md](ARCHITECTURE.md)

---

## 🔑 Environment Setup

### Required Variables

```bash
# Server
BASE_URL=http://localhost:8000
ADMIN_API_KEY=sk_live_admin_abc123

# Transak (Fiat→Crypto)
TRANSAK_API_KEY=your_api_key
TRANSAK_SECRET=your_secret
TRANSAK_ENV=PRODUCTION  # or STAGING

# Stripe (Cards)
STRIPE_SECRET_KEY=sk_live_xxx
STRIPE_PUBLISHABLE_KEY=pk_live_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx

# Sumsub (KYC)
SUMSUB_APP_TOKEN=token
SUMSUB_SECRET_KEY=secret

# Notifications
TELEGRAM_BOT_TOKEN=bot_token
TELEGRAM_CHAT_ID=chat_id
WHATSAPP_TOKEN=whatsapp_token
WHATSAPP_PHONE_ID=phone_id

# Encryption
CREDENTIAL_ENCRYPTION_KEY=your_32_byte_hex_key

# Database
DATABASE_URL=sqlite:///payments.db
```

**Full example**: [.env.example](.env.example)

---

## 🛣️ API Routes

### Payment Operations

```http
POST   /orders                      # Create payment link
GET    /orders/{order_id}           # Get payment status
GET    /payments                    # List payments (filtered)
```

### Merchant Management

```http
POST   /merchants/register          # Register merchant
GET    /merchants/{merchant_id}     # Get merchant profile
POST   /merchants/{id}/activate     # Activate after KYC
```

### KYC & Verification

```http
POST   /verify/upload               # Upload company document
POST   /verify/run                  # Run verification pipeline
GET    /verify/{merchant_id}        # Get KYC status
```

### Provider Management

```http
GET    /providers                   # List all providers
GET    /providers/{id}/status       # Check provider health
GET    /providers/rank              # Rank providers by quality
```

### Admin

```http
GET    /admin                       # Admin dashboard
GET    /dashboard/stats             # Metrics
GET    /dashboard/chart             # Payment timeline
```

**Full API docs**: Swagger at `/docs` or [docs/API.md](docs/API.md)

---

## 🔐 Security

| Layer | Mechanism | Details |
|-------|-----------|---------|
| **Credentials** | AES-256-GCM | Stored encrypted in DB |
| **API Keys** | X-Api-Key header | Per-merchant authentication |
| **Webhooks** | HMAC signature | Provider-specific verification |
| **Input** | Pydantic validation | Type-safe request parsing |
| **KYC** | Risk scoring | Multi-factor approval logic |

**Security audit**: [docs/SECURITY.md](docs/SECURITY.md)

---

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# Test specific module
pytest tests/test_providers.py -v

# Test with coverage
pytest tests/ --cov=. --cov-report=html
```

---

## 📁 Project Structure

```
payment-gateway/
├── server.py                  # FastAPI main app
├── config.py                  # Configuration constants
├── database.py                # SQLite schema
├── forceverify.py             # Provider ranking
│
├── providers/                 # Payment adapters
│   ├── __init__.py            # Factory + metadata
│   ├── transak.py
│   ├── stripe.py
│   ├── coinremitter.py
│   └── plisio.py
│
├── verification/              # KYC pipeline
│   ├── engine.py              # VerificationEngine
│   ├── encryption.py          # AES-256-GCM
│   └── __init__.py
│
├── mcp_beastpay/              # Claude Code Integration
│   ├── server.py              # MCP server
│   ├── handlers/              # Operation handlers
│   └── resources/             # JSON schemas
│
├── web/                       # Frontend HTML/JS
│   ├── index.html
│   ├── checkout-*.html
│   └── admin.html
│
├── docs/                      # GitHub documentation
│   ├── ARCHITECTURE.md
│   ├── FUNCTIONS.md
│   ├── MCP_INTEGRATION.md
│   ├── CODEX_INTEGRATION.md
│   ├── API.md
│   └── SECURITY.md
│
├── tests/                     # Unit tests
│   └── test_*.py
│
├── CLAUDE.md                  # AI assistant guidance
├── README.md                  # This file
└── .env.example               # Environment template
```

**Full reference**: [ARCHITECTURE.md](ARCHITECTURE.md)

---

## 🚀 Advanced Usage

### Claude Code Integration

Use BeastPay functions directly from Claude Code editor:

```
@beastpay Create payment: merchant_abc123, 100 USD, BTC
@beastpay Register merchant: Acme Corp, UAE, hello@acme.ae
@beastpay What's the KYC status for merchant_xyz?
@beastpay Rank providers for BTC by speed
```

**MCP Server Setup**: [MCP_INTEGRATION.md](MCP_INTEGRATION.md)

### Provider Integration

Add a new payment provider in 3 steps:

1. **Create adapter**: `providers/new_provider.py`
2. **Register in factory**: `providers/__init__.py`
3. **Add routes**: `server.py`

**How-to guide**: [docs/PROVIDERS.md](docs/PROVIDERS.md)

### Custom KYC Rules

Modify risk scoring in `verification/engine.py`:

```python
async def calculate_risk_score(profile_data: dict) -> float:
    score = 0
    if profile_data['company_age'] < 2:
        score += 20  # Adjust thresholds
    return score
```

---

## 🔄 Deployment

### Docker

```dockerfile
FROM python:3.9-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Systemd Service

```ini
[Unit]
Description=BeastPay Payment Gateway
After=network.target

[Service]
Type=simple
WorkingDirectory=/home/kali/payment-gateway
ExecStart=/usr/bin/env python3 server.py
Restart=on-failure

[Install]
WantedBy=multi-user.target
```

**Full deployment guide**: [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)

---

## 🛣️ Roadmap

### Q3 2026
- [ ] PostgreSQL migration
- [ ] Redis caching layer
- [ ] GraphQL API

### Q4 2026
- [ ] Codex integration (auto-generated adapters)
- [ ] Rate limiting + quotas
- [ ] Real-time balance sync

### 2027
- [ ] Kubernetes deployment
- [ ] Multi-region failover
- [ ] White-label merchant sub-accounts

**Detailed roadmap**: [CODEX_INTEGRATION.md](CODEX_INTEGRATION.md)

---

## 🤝 Contributing

1. Create a feature branch: `git checkout -b feature/my-feature`
2. Write tests for new code
3. Ensure `pytest` passes: `pytest tests/ -v`
4. Submit pull request with clear description

---

## 📚 Documentation

| Doc | Purpose |
|-----|---------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | System design, data flows, security |
| [FUNCTIONS.md](FUNCTIONS.md) | Complete function reference |
| [MCP_INTEGRATION.md](MCP_INTEGRATION.md) | Claude Code integration setup |
| [CODEX_INTEGRATION.md](CODEX_INTEGRATION.md) | Future AI-powered features |
| [docs/API.md](docs/API.md) | REST API detailed reference |
| [docs/PROVIDERS.md](docs/PROVIDERS.md) | Provider adapters guide |
| [docs/KYC.md](docs/KYC.md) | KYC & verification pipeline |
| [docs/SECURITY.md](docs/SECURITY.md) | Security audit & best practices |

---

## 🆘 Troubleshooting

### Payment webhook not received

```bash
# Check webhook registration
curl http://localhost:8000/admin

# View server logs
tail -f server.log

# Test webhook manually
curl -X POST http://localhost:8000/webhooks/stripe \
  -H "Content-Type: application/json" \
  -d '{"status": "succeeded", "order_id": "test"}'
```

### KYC verification stuck

```bash
# Re-run verification
curl -X POST http://localhost:8000/verify/run \
  -H "Content-Type: application/json" \
  -d '{"merchant_id": "merchant_xyz"}'

# Check database
sqlite3 payments.db "SELECT * FROM kyc_records WHERE merchant_id='merchant_xyz';"
```

### MCP server not responding

```bash
# Start MCP server
python mcp_beastpay/server.py

# Check if port 3000 is open
lsof -i :3000

# Verify in .claude/settings.json
cat .claude/settings.json | grep -A5 "mcpServers"
```

---

## 📞 Support

- **Email**: digifol83@gmail.com
- **Issues**: [GitHub Issues](https://github.com/sicher-mayor/beastpayment/issues)
- **Docs**: [/docs](docs/) directory
- **API**: Swagger at `/docs`

---

## 📜 License

**Commercial License**  
SICHER MAYOR COMMERCIAL BROKERS L.L.C (Dubai, DED 841208)

All rights reserved. Unauthorized copying or redistribution prohibited.

---

## 🙏 Acknowledgments

- **Claude AI**: Document extraction, risk scoring, MCP generation
- **FastAPI**: Async framework
- **Transak, Stripe, MoonPay**: Payment providers
- **Sumsub**: KYC infrastructure

---

**Version**: 1.0.0  
**Last Updated**: 2026-04-29  
**Maintained by**: BeastPay Development Team

[⬆ back to top](#-beastpay-payment-gateway)

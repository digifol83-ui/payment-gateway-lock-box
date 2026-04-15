# /beastpay-openclaw — OpenClaw BeastPay Gateway Project

You are working inside the **BeastPay-OpenClaw** fiat-to-crypto payment gateway project.
Load this full context before doing any work in this project.

---

## Project Identity

| Field        | Value                                 |
|--------------|---------------------------------------|
| Project Name | BeastPay by OpenClaw                  |
| Bot          | @Openclawbeastpay_bot                 |
| Telegram ID  | 933545457                             |
| Root         | /home/kali/payment-gateway/           |
| Start server | `source .env && uvicorn server:app --host 0.0.0.0 --port 8000` |

---

## Architecture Overview

```
payment-gateway/
├── server.py            # FastAPI — all API endpoints + webhooks
├── database.py          # SQLite — payments, links, merchants
├── config.py            # All env-var config (providers, Telegram, server)
├── telegram.py          # Telegram bot notification engine
├── providers/
│   ├── __init__.py      # Provider registry: get_provider("transak"|"moonpay")
│   ├── transak.py       # Transak widget URL builder + webhook parser
│   └── moonpay.py       # MoonPay widget URL builder + webhook parser
├── web/
│   ├── pay.html         # Customer payment page (/pay/{link_id})
│   ├── success.html     # Post-payment success/polling page
│   └── admin.html       # Admin dashboard SPA (vanilla JS)
├── admin.ps1            # PowerShell internal admin console
├── .env                 # Live secrets (bot token, chat ID, API keys)
└── .claude/commands/
    ├── beastpay-openclaw.md   ← this file
    └── add-tool.md            ← /add-tool skill
```

---

## What Was Built (Full History)

### Phase 1 — Core Gateway
- **FastAPI server** with async handling for concurrent payments
- **SQLite database** with 3 tables: `merchants`, `payment_links`, `payments`
- **Payment link system** — reusable or one-time links with wallet address, amount, crypto
- **Fiat-to-crypto providers**: Transak + MoonPay (both handle KYC internally)
  - No KYC for amounts < $200 (Transak) / < $150 (MoonPay)
  - Widget URL generation — customer redirected to provider to complete payment
- **Webhook handlers** — `/webhooks/transak` and `/webhooks/moonpay` with HMAC verification
- **Merchant system** — API keys, per-merchant webhook URLs

### Phase 2 — Web UI
- **Customer pay page** (`/pay/{link_id}`) — email input, crypto selector, provider choice
- **Success page** — polls payment status every 10s, shows completion
- **Admin dashboard** (`/admin`) — stats, payment list, link manager, CSV export

### Phase 3 — PowerShell UI (`admin.ps1`)
- Full menu-driven console: stats, links, payments, merchants, export CSV
- Telegram submenu `[T]`: status, test ping, push summary, setup guide, set credentials

### Phase 4 — Telegram Integration (`telegram.py`)
- Bot: **@Openclawbeastpay_bot** | Chat: **933545457** (@Watchpipe)
- 5 notification events: new payment, completed, failed, new link, daily summary
- 3 API endpoints: `GET /api/telegram/status`, `POST /api/telegram/test`, `POST /api/telegram/summary`
- `.env` configured and live-tested

---

## API Reference

### Auth
All admin endpoints require header: `X-Api-Key: <ADMIN_API_KEY>`
Merchant endpoints accept merchant API keys returned at merchant creation.

### Key Endpoints
```
GET  /health                        → server liveness
POST /api/merchants                 → create merchant (admin only)
POST /api/links                     → create payment link
GET  /api/links                     → list links
GET  /api/links/{id}               → get link
DELETE /api/links/{id}             → deactivate link
POST /api/payments/initiate         → start payment (returns provider redirect URL)
GET  /api/payments/{id}            → get payment status
GET  /api/payments                  → list payments (filter: ?status=completed)
GET  /api/stats                     → dashboard stats (admin only)
POST /webhooks/transak              → Transak webhook
POST /webhooks/moonpay              → MoonPay webhook
GET  /api/telegram/status          → Telegram config
POST /api/telegram/test            → send test ping
POST /api/telegram/summary         → push stats digest
GET  /api/config                   → public: supported cryptos, fiats, providers
```

### Payment Flow
1. Merchant calls `POST /api/links` → gets shareable URL
2. Customer opens `/pay/{link_id}` → enters email, chooses crypto + provider
3. Frontend calls `POST /api/payments/initiate` → gets `provider_url`
4. Customer redirected to Transak/MoonPay widget (KYC handled by provider)
5. Provider sends webhook → `_process_webhook()` updates status
6. Telegram notification fired → merchant webhook fired
7. Customer lands on `/pay/success/{payment_id}` → polls status

---

## Environment Variables (.env)
```bash
TELEGRAM_BOT_TOKEN=8423837754:AAFlwGClcUiM20pOWsJs5VJRJKEmQ4CjkS8
TELEGRAM_CHAT_ID=933545457
TG_NOTIFY_NEW_PAYMENT=1
TG_NOTIFY_COMPLETED=1
TG_NOTIFY_FAILED=1
TG_NOTIFY_NEW_LINK=1
TG_NOTIFY_DAILY_SUMMARY=1
HOST=0.0.0.0
PORT=8000
BASE_URL=http://localhost:8000
ADMIN_API_KEY=admin-secret-change-me
TRANSAK_API_KEY=YOUR_TRANSAK_API_KEY
TRANSAK_SECRET=YOUR_TRANSAK_SECRET
TRANSAK_ENV=STAGING
MOONPAY_API_KEY=YOUR_MOONPAY_API_KEY
MOONPAY_SECRET=YOUR_MOONPAY_SECRET
MOONPAY_ENV=sandbox
```

---

## Supported Assets
**Crypto:** BTC, ETH, USDT, USDC, BNB, SOL, TRX, MATIC
**Fiat:** USD, EUR, GBP, INR, AED, CAD, AUD

---

## How to Add a New Tool / Integration
Use the `/add-tool` skill: it walks through adding a new backend integration, provider, webhook, Telegram notification, and wiring it into the admin UI and PowerShell console.

Run: `/add-tool`

# /beastpaybot — BeastPay OpenClaw Bot Hub

Shortcut command for the BeastPay payment gateway project.
Loads full context and shows the complete feature map instantly.

---

## Bot Identity

```
Bot Name  : @Openclawbeastpay_bot
Chat ID   : 933545457 (@Watchpipe)
Project   : BeastPay by OpenClaw
Root      : /home/kali/payment-gateway/
Start     : source .env && uvicorn server:app --host 0.0.0.0 --port 8000
Status    : python activate_gateways.py --status
MCP       : python3 mcp_beastpay/server.py
Admin UI  : http://localhost:8000/admin
```

---

## Complete Feature Map

### Payments
| Feature | Command / Endpoint |
|---|---|
| Public checkout | `GET /checkout` |
| Create public payment | `POST /api/public/payments` |
| Start provider checkout | `POST /api/public/payments/{id}/start/{provider}` |
| Create payment link | `POST /api/links` |
| Customer pays | `GET /pay/{link_id}` |
| Initiate checkout | `POST /api/payments/initiate` |
| Provider status | `GET /api/providers/status` |
| Provider test link | `POST /api/providers/test` |
| Payment status | `GET /api/payments/{id}` |
| List payments | `GET /api/payments` |
| Stats | `GET /api/stats` |

### Providers (Fiat→Crypto)
| Provider | Local checkout code | Live key status |
|---|---|---|
| Transak | Yes | `python activate_gateways.py --status` |
| MoonPay | Yes | `python activate_gateways.py --status` |
| MetaMask | Yes | `python activate_gateways.py --status` |
| Guardarian | Stub only | `python activate_gateways.py --status` |
| Bleap | Stub only | `python activate_gateways.py --status` |
| Kast | Stub only | `python activate_gateways.py --status` |
| NOWPayments | Crypto-only | `python activate_gateways.py --status` |

### Claude Code MCP Tools
| Tool | Purpose |
|---|---|
| `get_provider_status` | Show live/sandbox state without exposing secrets |
| `list_live_fiat_to_crypto` | Return production fiat-to-crypto providers |
| `test_provider_checkout_link` | Build hosted checkout link for Stripe/Transak/MoonPay/MetaMask paths |

### Notifications
| Channel | Status endpoint | Test endpoint |
|---|---|---|
| Telegram | `GET /api/telegram/status` | `POST /api/telegram/test` |
| WhatsApp | `GET /api/whatsapp/status` | `POST /api/whatsapp/test` |

### KYC
| Tier | Trigger | Provider |
|---|---|---|
| No KYC | < $200 | Provider-managed |
| Email only | < $500 | MoonPay / Transak |
| Full KYC | ≥ $500 | Sumsub |
| Initiate | `POST /api/kyc/initiate` | Sumsub WebSDK |

### Webhooks
```
POST /webhooks/transak
POST /webhooks/moonpay
POST /webhooks/nowpayments
POST /webhooks/sumsub
```

---

## PowerShell Admin Console
```powershell
cd /home/kali/payment-gateway
pwsh admin.ps1

# Menu shortcuts:
[0]  BeastPay Bot Hub        ← feature overview + integration status
[1]  Dashboard / Stats
[2]  Payment Links
[3]  Create Link
[4]  View Payments
[5]  Check Payment
[6]  Filter by Status
[7]  Add Merchant
[8]  Export CSV
[9]  Health Check
[T]  Telegram Menu
[W]  WhatsApp Menu
[N]  NOWPayments Menu
[K]  KYC / Sumsub Menu
[Q]  Quit
```

---

## Env Vars Quick Reference
```bash
# Core
ADMIN_API_KEY=...
BASE_URL=http://localhost:8000
CREDENTIAL_ENCRYPTION_KEY=...

# Telegram (live)
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...

# Live gateway keys
STRIPE_SECRET_KEY=sk_live_...
STRIPE_PUBLISHABLE_KEY=pk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...
TRANSAK_API_KEY=...
TRANSAK_SECRET=...
TRANSAK_ACCESS_TOKEN=...
TRANSAK_ENV=PRODUCTION
MOONPAY_API_KEY=...
MOONPAY_SECRET=...
MOONPAY_ENV=production
METAMASK_API_KEY=...
METAMASK_SECRET=...
METAMASK_WEBHOOK_SECRET=...
METAMASK_ENV=production

# NOWPayments (fill in)
NOWPAYMENTS_API_KEY=
NOWPAYMENTS_IPN_SECRET=

# Sumsub KYC (fill in)
SUMSUB_APP_TOKEN=
SUMSUB_SECRET_KEY=
```

---

## Files Quick Reference
| File | Purpose |
|---|---|
| `server.py` | FastAPI — all routes |
| `database/` | SQLite migrations and async DB wrapper |
| `config.py` | All env-var settings |
| `telegram_notify.py` | Telegram notifications |
| `whatsapp.py` | WhatsApp Cloud API notifications |
| `providers/transak.py` | Transak widget + webhook |
| `providers/moonpay.py` | MoonPay widget + webhook |
| `providers/stripe.py` | Stripe Checkout Sessions |
| `providers/metamask.py` | MetaMask order integration |
| `providers/nowpayments.py` | NOWPayments invoice + IPN |
| `kyc/sumsub.py` | Sumsub KYC — applicant, token, webhook |
| `web/admin.html` | Admin SPA dashboard |
| `web/unified_checkout.html` | Public hosted-provider checkout |
| `web/success.html` | Post-payment status page |
| `admin.ps1` | PowerShell admin console |
| `.env` | Live credentials |

---

When user runs `/beastpaybot`:
- Show this feature map
- Check which integrations are configured (read .env)
- Suggest next steps based on what's missing
- Offer to run any `/add-tool` workflow if a new integration is requested

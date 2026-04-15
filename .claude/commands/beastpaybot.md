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
Admin UI  : http://localhost:8000/admin
```

---

## Complete Feature Map

### Payments
| Feature | Command / Endpoint |
|---|---|
| Create payment link | `POST /api/links` |
| Customer pays | `GET /pay/{link_id}` |
| Initiate checkout | `POST /api/payments/initiate` |
| Payment status | `GET /api/payments/{id}` |
| List payments | `GET /api/payments` |
| Stats | `GET /api/stats` |

### Providers (Fiat→Crypto)
| Provider | Type | KYC |
|---|---|---|
| Transak | Card / bank | None < $200 |
| MoonPay | Card / bank | Email only < $150 |
| NOWPayments | Wallet-to-wallet | None ever |

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

# Telegram (live)
TELEGRAM_BOT_TOKEN=8423837754:AAFlwGClcUiM20pOWsJs5VJRJKEmQ4CjkS8
TELEGRAM_CHAT_ID=933545457

# WhatsApp (fill in)
WHATSAPP_TOKEN=
WHATSAPP_PHONE_ID=
WHATSAPP_TO=

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
| `database.py` | SQLite — payments, links, merchants, kyc_records |
| `config.py` | All env-var settings |
| `telegram.py` | Telegram notifications |
| `whatsapp.py` | WhatsApp Cloud API notifications |
| `providers/transak.py` | Transak widget + webhook |
| `providers/moonpay.py` | MoonPay widget + webhook |
| `providers/nowpayments.py` | NOWPayments invoice + IPN |
| `kyc/sumsub.py` | Sumsub KYC — applicant, token, webhook |
| `web/admin.html` | Admin SPA dashboard |
| `web/pay.html` | Customer payment page |
| `web/success.html` | Post-payment status page |
| `admin.ps1` | PowerShell admin console |
| `.env` | Live credentials |

---

When user runs `/beastpaybot`:
- Show this feature map
- Check which integrations are configured (read .env)
- Suggest next steps based on what's missing
- Offer to run any `/add-tool` workflow if a new integration is requested

# BeastPay Wallet Integration - Quick Start

## 🚀 Live URLs

**Main Checkout:** https://beastpay-api-544494288390.us-central1.run.app/checkout

**Provider Pages:**
- MetaMask: `/checkout-metamask.html`
- CoinRemitter: `/checkout-coinremitter.html`
- Plisio: `/checkout-plisio.html`
- NOWPayments: `/checkout-nowpayments.html`
- Stripe: `/checkout/stripe`
- Transak: `/buy`

## 💼 Default Wallet

**Address:** `0x0582b74D10c853B52335542036e6CEA9B780849A`  
**Network:** Binance Smart Chain (BSC)  
**Token:** USDT

Stored in browser localStorage — survives page reloads.

## 🔌 Wallet Plugin Usage

```html
<!-- Include plugin in any page -->
<script src="/static/wallet-connector.js"></script>

<script>
// Get current wallet
const wallet = WalletConnector.getWallet()
console.log(wallet.address)

// Set new wallet
WalletConnector.setWallet('metamask', '0xNEWADDRESS')

// Clear wallet (revert to default)
WalletConnector.clear()

// Validate address format
if (WalletConnector.isValidAddress(addr)) { ... }
</script>
```

## 📋 Form Flow

1. User lands on `/checkout`
2. Sees connected wallet (default or saved)
3. Can click "Change Wallet" to switch
4. Selects a provider from 6 live + TrustWallet (coming soon)
5. Fills amount, currency, crypto, email
6. Clicks "Proceed to {Provider}"
7. Payment creation API called
8. Redirects to provider-specific page

## 🔐 Security Notes

- **No OTP Generation** — MIT Policy: external providers handle auth
- **No CVV/PAN Storage** — only wallet address stored
- **Browser-Only** — localStorage, no server-side wallet storage
- **HTTPS Only** — production deployments require TLS

## 🧪 Test Checkout Flow

```bash
# Local dev
uvicorn server:app --host 0.0.0.0 --port 8000

# Visit
http://localhost:8000/checkout

# Try MetaMask flow
http://localhost:8000/checkout-metamask.html?amount=100&currency=USD&crypto=USDT
```

## 📊 Provider Status

| Provider | Fee | Settlement | Status |
|----------|-----|-----------|--------|
| MetaMask | 2.5% | 5-10 min | 🟢 LIVE |
| CoinRemitter | 2.0% | 3-10 min | 🟢 LIVE |
| Plisio | 1.0% | 5-15 min | 🟢 LIVE |
| NOWPayments | 1.5% | 1-30 min | 🟢 LIVE |
| Transak | 1.0% | 5-10 min | 🟢 LIVE |
| Stripe | 2.9% | Instant | 🟢 LIVE |
| TrustWallet | — | — | 🔜 Coming Soon |

## 🔄 API Endpoints

Create payment for any provider:

```bash
POST /api/payments/{provider}/create
Content-Type: application/json

{
  "amount_fiat": 100,
  "fiat_currency": "USD",
  "crypto_currency": "USDT",
  "wallet_address": "0x...",
  "customer_email": "user@example.com"
}
```

Supported providers: `metamask`, `coinremitter`, `plisio`, `nowpayments`

## 📱 User Benefits

✅ **One Wallet** — Connected across all providers  
✅ **No Form Repeat** — Wallet auto-filled  
✅ **Fast Switching** — Change providers instantly  
✅ **Persistent** — Wallet saved in browser  
✅ **Private** — No server tracking  

## 🛠️ Troubleshooting

**Wallet not persisting?**
- Check localStorage in DevTools (Application tab)
- Browser privacy settings may block localStorage
- Try incognito mode

**Payment creation fails?**
- Check browser console for error message
- Verify wallet address format (starts with 0x)
- Ensure email is valid

**Provider page doesn't load?**
- Verify static files mounted: `app.mount("/static", ...)`
- Check `/static/wallet-connector.js` exists in web/ directory

## 📄 Full Documentation

See `WALLET_INTEGRATION_GUIDE.md` for complete details.

---

**Deployed:** 2026-05-16  
**Status:** ✅ Live on Cloud Run (us-central1)  
**Commit:** `f13cdeb`

# Gateway Activation Guide — BeastPay OpenClaw

## 🚀 Tier 1: Zero-KYC, Auto API Keys (5 min each)

**Status**: Ready to activate  
**Timeline**: Signups complete in ~3 minutes, keys arrive in inbox within 5 minutes  

### Start Tier 1 Activation

```bash
cd /home/kali/payment-gateway
bash tier1_parallel_activate.sh
```

**What runs:**
1. `tier1_activation_watcher.py` — monitors inbox for API keys, auto-activates
2. `nowpayments_signup_filler.py` — clipboard helper for signup
3. `plisio_signup_filler.py` — clipboard helper for signup
4. `coinremitter_signup_filler.py` — clipboard helper for signup

**Account:** `sichermayor@deltajohnsons.com`  
**Passwords:** `BeastPay_NP_2026!Secure` / `BeastPay_PL_2026!Secure` / `BeastPay_CR_2026!Secure`

**ETA:** 10 minutes (3 min signups + 5–7 min for API key emails)

---

## 🔄 Tier 2: Email Verification (10 min each)

Guardarian, Charge, Swapin — I'll create clipboard fillers after Tier 1.

---

## 🔏 Tier 3: Light KYC (20–30 min each)

MoonPay, MetaMask, Bleap, KAST, FinchPay — I'll create clipboard fillers after Tier 2.

---

## 🏛️ Tier 4: Full KYB

**Transak:** Resume with `python3 kyb_clipboard_filler.py --from 51`  
**Ziina:** Ready (need banking details for final step)

---

## 📊 Current Status

LIVE: Stripe  
SANDBOX: Transak (50%), all others  

---

## 🎯 Start Now

```bash
cd /home/kali/payment-gateway
bash tier1_parallel_activate.sh
```

Clipboard fillers for Tiers 2–3 coming next.

# ✅ TIER 1 ACTIVATION — READY TO LAUNCH

## System Status: ALL GREEN ✅

- **Cloud Run:** Running (beastpay-api-544494288390.us-central1.run.app)
- **App Health:** 200 OK
- **Temp-mail Session:** Valid
- **Activation Scripts:** All present & executable
- **Current Providers:** 1 LIVE (Stripe), 13 SANDBOX

---

## 🚀 LAUNCH COMMAND

```bash
cd /home/kali/payment-gateway
bash tier1_parallel_activate.sh
```

---

## 🔄 WHAT HAPPENS NEXT

### Phase 1: Inbox Watcher Starts (Background)
- `tier1_activation_watcher.py` monitors `sichermayor@deltajohnsons.com`
- Watches for API key emails from: NOWPayments, Plisio, CoinRemitter
- Auto-parses keys and runs `activate_live.sh` for each

### Phase 2: NOWPayments Signup (~3 min)
```
1. Script shows: Email: sichermayor@deltajohnsons.com
   You: Ctrl+C to copy (already in clipboard)
   
2. Script shows: Password: BeastPay_NP_2026!Secure
   You: Ctrl+V in browser, Tab to next field
   
3. Press Enter in terminal → next field shown
   
4. Repeat for Confirm Password
   
5. Complete CAPTCHA in browser (manual step)
   
6. Script shows API Keys page location
   You: Tell script when signup complete (press Enter)
```

### Phase 3: Plisio Signup (~3 min)
- Same flow as NOWPayments

### Phase 4: CoinRemitter Signup (~3 min)
- Same flow as NOWPayments

### Phase 5: Auto-Activation (Background)
As each API key email arrives:
- Watcher extracts key
- Runs: `bash activate_live.sh <gateway> <key>`
- Updates: `.env` + Cloud Run env vars
- Cloud Build: Auto-deploys revision
- Result: Provider flips from SANDBOX → LIVE

**Timeline:**
- NOWPayments: ~5 min after signup
- Plisio: ~1 min after signup
- CoinRemitter: ~2 min after signup

---

## 📊 EXPECTED END STATE

After completion, all three will show as LIVE:

```
✅ Stripe              LIVE (already done)
✅ NOWPayments         LIVE
✅ Plisio              LIVE
✅ CoinRemitter        LIVE
⏳ 10 other providers  SANDBOX
```

Verify with:
```bash
curl https://beastpay-api-544494288390.us-central1.run.app/api/providers/status | \
  python3 -c "import json, sys; data=json.load(sys.stdin); \
  [print(f'{p[\"name\"]:20} {\"🟢 LIVE\" if p.get(\"production\") else \"⏳ SANDBOX\"}') \
  for p in data['providers']]"
```

---

## 📧 EMAIL CREDENTIALS

All gateways use same email address:
- **Email:** `sichermayor@deltajohnsons.com`
- **Inbox:** Watched by `tier1_activation_watcher.py`

Individual passwords:
- **NOWPayments:** `BeastPay_NP_2026!Secure`
- **Plisio:** `BeastPay_PL_2026!Secure`
- **CoinRemitter:** `BeastPay_CR_2026!Secure`

---

## ⏱️ TOTAL TIME

- **User active work:** ~9 minutes (3 signups × 3 min each)
- **Waiting for API keys:** ~7 minutes (keys arrive while you're signing up)
- **Auto-deployment:** ~2 minutes per gateway
- **Total:** ~15–20 minutes start to finish

---

## 🎯 NEXT STEPS AFTER TIER 1

Once Tier 1 completes:

1. **Tier 2 (30 min):** Guardarian, Charge, Swapin
   - I'll provide clipboard fillers
   - Each needs email verification
   
2. **Tier 3 (2–4 hours):** MoonPay, MetaMask, Bleap, KAST, FinchPay
   - I'll provide clipboard fillers
   - Light KYC forms (1–2 hour review)
   
3. **Tier 4 (2–4 hours):** Transak, Ziina
   - Transak: Resume KYB filler at field 51 (3 min) + 2–4 hour review
   - Ziina: Banking details + 1–2 hour review

---

## 🛟 TROUBLESHOOTING

### "clipboard error: no such file"
- Windows clip.exe not found (WSL issue)
- Workaround: Copy values from terminal manually

### "FAIL: no OTP received in 90s"
- Email verification timing out
- Check temp-mail inbox manually: `python3 temp_mail_listener.py watch`

### "API key not found in email"
- Watcher regex doesn't match format
- Workaround: Copy key manually and run: `bash activate_live.sh <gw> <key>`

### "Cloud Run deploy failed"
- Org policy issue or IAM permissions
- Check: `gcloud run services describe beastpay-api --region us-central1`

---

## ✅ READY

All systems operational. Launch with:

```bash
bash tier1_parallel_activate.sh
```

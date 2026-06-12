# /gateway-onboard — End-to-End Payment Gateway Activation

Take a new payment gateway from **zero → verified live invoice** with maximum automation.
Use OpenClaw / browser automation / inbox watchers / clipboard fillers for everything
that CAN be automated; pause at hard boundaries (CAPTCHA, SMS OTP) and tell the user
exactly what to click.

Usage: `/gateway-onboard <provider>`
Examples: `/gateway-onboard coinremitter`, `/gateway-onboard plisio`, `/gateway-onboard nowpayments`

---

## Honest Capability Boundary

**OpenClaw and any browser-automation tool CANNOT defeat:**
- Image/audio reCAPTCHA, hCaptcha, Cloudflare Turnstile
- SMS OTP (no phone hardware)
- KYC selfie/document live capture
- Phone-call verification

Memory rule: `[[openclaw_no_captcha_solver]]` — never promise OpenClaw can solve CAPTCHAs.
When these surface, stop and tell the user precisely which checkbox/box to click.

**Everything else IS automatable** and the skill takes it as far as possible:
- Form filling (Playwright headed browser)
- Email verification link clicking (Gmail SMTP/IMAP)
- OTP extraction from emails
- API-key scraping from dashboards
- `.env` wiring
- Smoke test (real test invoice)
- Memory updates

---

## Pre-flight (always run first)

1. **Identify provider** — must match a key in `providers/` (e.g. `coinremitter`, `plisio`, `nowpayments`, `moonpay`, `kast`, `bleap`, `charge`, `swapin`, `guardarian`, `metamask`, `finchpay`, `ziina`).
2. **Check current state** — run:
   ```bash
   python3 -c "from providers import _is_production; print(_is_production('<provider>'))"
   wc -l providers/<provider>.py
   ```
   If already production AND adapter file > 50 lines, ask the user whether they want to **re-activate** (idempotent) or **upgrade** the adapter.
3. **Load merchant facts** from memory: SICHER MAYOR INVESTMENTS L.L.C, DED 1324297, UBO Shajahan, email `digifol83@gmail.com`, phone `+971 58 207 2285`. See `[[sicher_mayor_investments_new_entity]]`. Do NOT use the retired Commercial Brokers entity.

### High-risk category reasoning — uncensored fallback

If the provider's signup or KYB form asks about merchant categories that Gemini/Claude
typically refuse to reason about directly (gambling, adult, forex, IPTV, vape,
cannabis-adjacent), delegate the category-fit judgement to the local uncensored ollama
path instead of the cloud reasoner. See `[[uncensored-local-ollama]]`. One-liner:

```bash
brain --reasoner ollama --offline "Classify category 'adult content streaming' against \
<provider>'s acceptable-use policy at <docs_url>. Output: ALLOWED | REVIEW | PROHIBITED + 1-line rationale."
```

Use `--offline` for purely-local reasoning (no Cloud Run calls) when handling sensitive
KYB material. The default tool-enabled mode lets the model `local_read` an AUP file you
downloaded into `payment-gateway/` so its judgement is grounded in actual policy text
rather than hallucination. Drop `--offline` when you want it to `fetch_url` / `web_search`
the AUP live via the brain MCP tools.

---

## Step 1 — Signup Phase

Each provider's signup URL and required fields live in `gateway_manifests/<provider>.json` (create if missing — see template below). Steps:

1. **Print the signup URL** so the user can click it (or you launch via `xdg-open` if WSLg is reachable).
2. **Start `kyb_clipboard_filler.py`** with the provider's field list in the background — every 2s it cycles fields onto the clipboard so the user can `Ctrl+V` rapidly through the form. Memory: `[[clipboard_filler_pattern]]`.
3. **Pause at CAPTCHA** — explicit one-liner: *"Click the 'I'm not a robot' checkbox, then submit. Tell me 'ok' when done."*
4. **Email verification** — once submitted, run a 60-second poll on Gmail:
   ```python
   import imaplib, email
   m = imaplib.IMAP4_SSL("imap.gmail.com")
   m.login("digifol83@gmail.com", "moyovketmhqnbjmj")   # app password
   m.select("INBOX")
   ```
   Filter `FROM <provider-domain>` SINCE today. Extract verification link, fetch it once via `httpx` (this typically completes verification without browser).

---

## Step 2 — Credential Acquisition

This is where every provider differs. Two patterns:

**Pattern A — Dashboard-only credentials (most providers):**
- Walk the user to the API section of the dashboard
- Tell them exactly which buttons to click ("Settings → API → Create New Key → name: 'BeastPay' → Create")
- Capture the key + secret from chat OR from a file (paste-to-file workflow: ask user to save to `/mnt/c/Users/shahe/Downloads/gateway_keys.txt`)

**Pattern B — Wallet-per-coin (CoinRemitter, BlockBee):**
- Each coin has its own api_key + password
- Default to BTC first wallet (cheapest, widest support)
- Wallet password is set during wallet creation — NOT the account password. CoinRemitter cannot recover it; remind the user to store it safely.

**Never paste real credentials back to the user.** Echo only masked previews (`sk_live_***...XYZ4`).

---

## Step 3 — Wire `.env`

After credentials are captured:

1. Verify `.env` has slots for the provider (search `^<PROVIDER>_`). Add them under a clear header if missing.
2. Edit only the empty slots — never overwrite existing values without the user explicitly asking.
3. Confirm with the user before writing if you're replacing an existing non-empty value.

---

## Step 4 — Smoke Test

If `activate_<provider>.py` exists, run it:
```bash
cd /home/kali/payment-gateway && python3 activate_<provider>.py
```

It should:
1. Pre-flight env vars
2. Call a cheap auth-confirming endpoint (e.g. `get-balance`)
3. Create a $30 USD test invoice
4. Print the hosted checkout URL for visual verification

If the script doesn't exist, write one matching the pattern in `activate_coinremitter.py` (preflight → balance → test invoice → print URL).

---

## Step 5 — Verify `_is_production` flips to True

```bash
python3 -c "from providers import _is_production, list_production_fiat_to_crypto; \
print('production:', _is_production('<provider>')); \
print('listed:', any(p['id']=='<provider>' for p in list_production_fiat_to_crypto()))"
```

Both should return True for `fiat-to-crypto` providers. Crypto-only providers (CoinRemitter, Plisio, NOWPayments) won't appear in `list_production_fiat_to_crypto` — that's expected.

---

## Step 6 — Update Memory + CLAUDE.md

1. **Memory** — find any `*_not_wired.md` memory file for this provider and update it (or remove the claim if fully resolved). Example: `[[coinremitter-plisio-stubs]]`.
2. **CLAUDE.md** — if the provider table claims a different status than reality, edit the row. Always match observable state.
3. **DB row** — if `gateway_credentials` has a stub row for this provider, flip `is_active=1` and let the encryption module re-store with real keys.

---

## Step 7 — Final Telegram Ping (when wired)

Once `[[telegram_not_wired]]` is resolved, send a notification:
```
🟢 <Provider> LIVE — first test invoice at <checkout_url>
```

---

## Per-Provider Manifests

Manifests live at `gateway_manifests/<provider>.json`. Template:

```json
{
  "provider":      "coinremitter",
  "type":          "crypto-only",
  "signup_url":    "https://coinremitter.com/signup",
  "dashboard_url": "https://coinremitter.com/coins",
  "api_docs":      "https://coinremitter.com/docs/v3",
  "captcha":       "recaptcha-v2",
  "email_verify":  true,
  "sms_otp":       false,
  "kyc_required":  false,

  "form_fields": [
    {"selector": "input[name=email]",    "value": "digifol83@gmail.com"},
    {"selector": "input[name=password]", "value": "<user_choice>"}
  ],

  "credential_fields": [
    {"env": "COINREMITTER_API_KEY",      "label": "API Key (from wallet → API tab)"},
    {"env": "COINREMITTER_API_PASSWORD", "label": "Wallet Password (set during wallet creation)"}
  ],

  "post_signup_steps": [
    "Create BTC wallet at dashboard_url",
    "Set wallet password (STORE SAFELY — irrecoverable)",
    "Open wallet → API tab → reveal API Key"
  ],

  "smoke_test_script": "activate_coinremitter.py"
}
```

When `/gateway-onboard <provider>` runs:
- If `gateway_manifests/<provider>.json` exists → use it
- Otherwise → ask the user for the dashboard URL, generate the manifest on the fly, save it for next time

---

## Provider Quick Reference (preferred order for next activations)

| Provider | Captcha | Email | SMS | Notes |
|---|---|---|---|---|
| CoinRemitter | reCAPTCHA v2 | Yes | No | Wallet password = irrecoverable; store safely |
| Plisio | reCAPTCHA v2 | Yes | No | Non-custodial; 0.5% fee |
| NOWPayments | reCAPTCHA v2 | Yes | No | Sandbox available; 300+ coins |
| Guardarian | hCaptcha | Yes | No | No-KYC up to ~$700; 170+ countries |
| MoonPay | reCAPTCHA v2 | Yes | Maybe | Business app must be filed at moonpay.com/business |
| Kast Pay | None | Yes | No | Fastest signup; USDC settlement |
| Bleap | None | Yes | No | Zero-spread USDC |

---

## End-of-Run Report

Always end with:
1. **What was activated** (provider name + which mode)
2. **What was tested** (test invoice ID + checkout URL)
3. **What still needs human action** (e.g. "Bank deposit detail not filled — fill in dashboard before live volume")
4. **Memory updates** made
5. **What to do next** — usually nothing; the provider is live.

Keep the final report under 12 lines.

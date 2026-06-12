# Karmostaji Onramper Production Key Packet

Status: ready for provider submission; not proof of Onramper approval.

## Current Live BeastBrain State

- Public card-to-crypto page: `https://beastbrain.sichermayor.online/card-to-crypto`
- Status API: `https://beastbrain.sichermayor.online/api/card-to-crypto/status`
- Checkout API: `https://beastbrain.sichermayor.online/api/card-to-crypto/checkout`
- Hosted checkout engine: `/api/gateway-payment`
- Current checkout can create a hosted Onramper/MoonPay redirect URL.
- Current blocker: the mounted `ONRAMPER_INDIVIDUAL_API_KEY` is treated as test-like and ignored for live checkout.
- Current live response fields to mention:
  - `api_key_configured=false`
  - `api_key_status=test_key_ignored`
  - `ignored_api_key_source=ONRAMPER_INDIVIDUAL_API_KEY`
  - `link_mode=generic_onramper_live_card_link`
  - `wallet_prefill_requires=live ONRAMPER_API_KEY or ONRAMPER_INDIVIDUAL_API_KEY`
  - `signing_secret_configured=true`
  - `raw_card_data_stored=false`
  - `merchant_side_3ds_otp=removed`

## Official Onramper References

- Dashboard: `https://dashboard.onramper.com/`
- Onboarding guide: `https://docs.onramper.com/docs/step-by-step-guide`
- API integration steps: `https://docs.onramper.com/docs/integration-steps-1`
- Widget URL signing: `https://docs.onramper.com/docs/signing-widget-url`
- API signing: `https://docs.onramper.com/docs/sign-api-request`

Provider facts from official documentation:

- Onramper can provide staging access before production.
- Production API keys become available after Onramper approval.
- Sensitive wallet parameters require URL/API signing with a separate signing secret from Onramper.

## Merchant / KYB Facts

- Client label: `KARMOSTAJI TRADING LLC`
- Legal applicant: `AL KARMOSTAJI TRADING ENTERPRISES`
- License number: `200100`
- Commercial register: `1387701`
- DCCI: `7447`
- D-U-N-S: `534472717`
- Legal type: `Limited Liability Company (LLC)`
- Activity: `General Trading`
- License expiry: `2027-01-13`
- Address evidence: `P.O. Box 4139, Parcel ID 115-165, Dubai, UAE`
- Contact: `Mohammed Ali Vellopadikal`
- Role: `CEO / partner`
- Contact email for provider replies: `compliance@sichermayor.online`
- License email: `karmostaji@hotmail.com`

Do not invent a street address beyond the local evidence above.

## Use Case

BeastPay / BeastBrain provides a hosted card-to-crypto checkout for users buying USDT, USDC, BTC, ETH, or SOL with AED, USD, EUR, GBP, or other Onramper-supported fiat currencies.

The business line is ecommerce / online retail for industrial sewing machines, including Juki brand machines from about 10,000 to 50,000 AED.

Expected initial processing volume: `USD 20K - 100K / month`.

Security boundary:

- BeastBrain does not collect card number, expiry, CVV, raw bank data, OTP, or merchant-side 3DS.
- Card entry, KYC, issuer challenge, risk review, payment authorization, and settlement remain inside Onramper and the selected onramp provider.
- BeastBrain stores checkout intent metadata and hosted checkout URLs only.

## Exact Provider Ask

Request:

1. Production Onramper API key for `https://beastbrain.sichermayor.online/card-to-crypto`.
2. Signing secret for signed wallet/network-wallet URL parameters.
3. Domain/origin allowlist approval for `beastbrain.sichermayor.online`.
4. Confirmation that AED card purchases to USDT/USDC are supported for the approved account.
5. Confirmation of supported onramps, especially MoonPay, Banxa, Simplex, Mercuryo, and Ramp where available.
6. Webhook/event guidance for transaction success, failure, KYC pending, payment pending, and settlement completion.
7. Commercial terms, subscription requirements, KYB checklist, and go-live steps.

## Paste-Ready Email / Support Message

Subject: Production API Key Request - KARMOSTAJI TRADING LLC - BeastBrain Card-to-Crypto

Hello Onramper Team,

We are applying for production Onramper access for KARMOSTAJI TRADING LLC, with the legal applicant AL KARMOSTAJI TRADING ENTERPRISES, a Dubai licensed general trading business.

Product URL:
https://beastbrain.sichermayor.online/card-to-crypto

Use case:
BeastPay / BeastBrain provides a hosted card-to-crypto checkout for users buying USDT, USDC, BTC, ETH, or SOL with AED, USD, EUR, GBP, or other Onramper-supported fiat currencies. Card entry, KYC, issuer challenge, risk review, and settlement stay inside Onramper and the selected hosted onramp provider. BeastBrain does not collect raw card data, CVV, expiry, OTP, or merchant-side 3DS.

Entity:
- Legal name: AL KARMOSTAJI TRADING ENTERPRISES
- Client label: KARMOSTAJI TRADING LLC
- License number: 200100
- Commercial register: 1387701
- DCCI: 7447
- D-U-N-S: 534472717
- Legal type: Limited Liability Company (LLC)
- Activity: General Trading
- License expiry: 2027-01-13
- Address evidence: P.O. Box 4139, Parcel ID 115-165, Dubai, UAE

Contact:
- Mohammed Ali Vellopadikal
- CEO / partner
- Email: compliance@sichermayor.online
- License email: karmostaji@hotmail.com

Expected volume:
- USD 20K - 100K / month initially

Request:
1. Production Onramper API key for the BeastBrain card-to-crypto page.
2. Signing secret for wallet/networkWallets URL signing.
3. Domain/origin approval for beastbrain.sichermayor.online.
4. Confirmation of supported AED card-to-USDT/USDC routes and available onramps.
5. Webhook/event guidance for transaction lifecycle reconciliation.
6. KYB checklist, subscription requirements, commercial terms, and go-live steps.

Our integration is already live in hosted-checkout fallback mode. The only remaining production integration blocker is the production Onramper API key/domain approval and signing secret.

Best regards,
Mohammed Ali Vellopadikal
CEO / partner, KARMOSTAJI TRADING LLC
compliance@sichermayor.online
https://beastbrain.sichermayor.online/card-to-crypto

## Post-Approval BeastBrain Install

Do not paste credentials in chat.

Add the production key:

```bash
gcloud secrets versions add onramper-individual-api-key --data-file=-
```

Add the signing secret:

```bash
gcloud secrets versions add onramper-individual-signing-secret --data-file=-
```

Refresh Cloud Run:

```bash
gcloud run services update brain-api \
  --region us-central1 \
  --update-secrets=ONRAMPER_INDIVIDUAL_API_KEY=onramper-individual-api-key:latest,ONRAMPER_INDIVIDUAL_SIGNING_SECRET=onramper-individual-signing-secret:latest \
  --update-env-vars=ONRAMPER_ACCOUNT_MODE=individual
```

Verify:

```bash
curl -sS https://beastbrain.sichermayor.online/api/card-to-crypto/checkout \
  -H 'content-type: application/json' \
  --data '{"fiat_amount":250,"fiat_currency":"AED","crypto_currency":"USDT","wallet_address":"0x742d35Cc6634C0532925a3b844Bc454e4438f44e","network":"ethereum"}'
```

Expected success:

- `api_key_configured=true`
- `api_key_status=live`
- `api_key_source=ONRAMPER_INDIVIDUAL_API_KEY`
- `wallet_prefilled=true` when signing is valid


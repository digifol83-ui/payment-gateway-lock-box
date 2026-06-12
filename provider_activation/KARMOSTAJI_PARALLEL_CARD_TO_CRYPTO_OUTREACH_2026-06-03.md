# Karmostaji Parallel Card-To-Crypto Provider Outreach

Date: 2026-06-03

## Purpose

Run a fast parallel provider push for Karmostaji card-to-crypto activation while keeping BeastBrain's current safe fallback live.

## Current Live Fallback

- Live route: `https://beastbrain.sichermayor.online/api/checkout-lite/payment`
- Provider: CryptAPI / BlockBee
- Latest smoke: `payment_address_created`
- Payment type: crypto-in only
- Card data: not applicable
- KYC / OTP: none on BeastBrain side
- Settlement: CryptAPI forwards received crypto to the configured BeastBrain permanent wallet after chain confirmation.

This solves wallet transfer immediately for customers who already hold crypto. It does not solve fiat card-to-crypto.

## Card-To-Crypto Provider Priority

1. Alchemy Pay
   - Official contact page: `https://alchemypay.org/contact`
   - Official support email found on Alchemy Pay contact/support pages: `Support@alchemypay.org`
   - Ask for on-ramp merchant onboarding, KYB checklist, AED card coverage, production `appId` / `appSecret`, domain approval, and webhook/order-query requirements.

2. Guardarian
   - Official contact page: `https://guardarian.com/contact-us`
   - Business inquiries email shown there: `business@guardarian.com`
   - Ask for partner contract, partner account, production API token, AED/card support, domain approval, and transaction/webhook guidance.

3. Wert
   - Partner page: `https://wert.io/affiliate-program`
   - Docs: `https://docs.wert.io/docs/introduction`
   - Ask for onboarding, production Partner Dashboard credentials, Partner ID, API key, fiat onramp production access, and supported UAE/AED flows.

## Shared Merchant Facts

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
- Contact email: `compliance@sichermayor.online`
- License email: `karmostaji@hotmail.com`
- Product URL: `https://beastbrain.sichermayor.online/card-to-crypto`
- Expected volume: `USD 20K - 100K / month`
- Business line: ecommerce / online retail for industrial sewing machines, including Juki brand machines from about `10,000` to `50,000 AED`.

## Shared Security Boundary

- BeastBrain does not collect card number, expiry, CVV, raw bank data, OTP, or merchant-side 3DS.
- Card entry, KYC, issuer challenge, risk review, payment authorization, and settlement remain with the provider.
- BeastBrain stores checkout intent metadata and hosted checkout URLs only.
- Private identity files and company documents must be uploaded only through official provider portals/forms.

## Shared Outreach Text

Subject: Production card-to-crypto merchant onboarding request - KARMOSTAJI TRADING LLC

Hello,

We are applying for production card-to-crypto / fiat on-ramp merchant access for KARMOSTAJI TRADING LLC, with legal applicant AL KARMOSTAJI TRADING ENTERPRISES, a Dubai licensed general trading business.

Product URL:
https://beastbrain.sichermayor.online/card-to-crypto

Use case:
BeastPay / BeastBrain provides a hosted card-to-crypto checkout for users buying USDT, USDC, BTC, ETH, or SOL with AED, USD, EUR, GBP, or other supported fiat currencies. Card entry, KYC, issuer challenge, risk review, payment authorization, and settlement stay inside the approved hosted provider. BeastBrain does not collect raw card data, CVV, expiry, OTP, or merchant-side 3DS.

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

Business line:
Ecommerce / online retail for industrial sewing machines, including Juki brand machines from about 10,000 to 50,000 AED.

Expected volume:
USD 20K - 100K / month initially.

Request:
1. Merchant onboarding or partner application link.
2. KYB document checklist for a UAE licensed trading entity.
3. Production API credentials / partner ID requirements.
4. Domain/origin approval for beastbrain.sichermayor.online.
5. Confirmation of AED card-to-USDT/USDC support and supported countries/payment methods.
6. Webhook/order status guidance for payment success, failure, KYC pending, payment pending, and settlement completion.
7. Commercial terms, settlement timelines, and go-live steps.

Our document package is ready. Please send the official secure upload/onboarding flow for commercial license, CEO/partner identity evidence, proof of address, and banking evidence if required.

Best regards,
Mohammed Ali Vellopadikal
CEO / partner, KARMOSTAJI TRADING LLC
compliance@sichermayor.online
https://beastbrain.sichermayor.online/card-to-crypto

## Post-Approval BeastBrain Install

After a provider approves and issues credentials, do not paste credentials into chat.

Add the provider values to Google Secret Manager, mount them to Cloud Run, and run live smoke against:

```bash
curl -sS -m 20 https://beastbrain.sichermayor.online/api/payment-gateways/real-card
curl -sS -m 30 -X POST https://beastbrain.sichermayor.online/api/gateway-payment \
  -H 'content-type: application/json' \
  --data '{"gateway_id":"alchemy_pay","amount_aed":250,"crypto":"USDT","network":"polygon"}'
```

Switch `gateway_id` to `guardarian` or `wert` after those providers issue production credentials.

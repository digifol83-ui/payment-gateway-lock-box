# Karmostaji ASAP Fiat Collection Fallback

Date: 2026-06-03

## Decision

Card-to-crypto is still approval-gated. The ASAP workaround is:

1. Use `Checkout Lite / CryptAPI` for customers who already hold crypto.
2. Use a UAE card/payment-link provider for customers who only have card/AED.
3. After AED settlement, do a human-approved exchange or wallet transfer step.

This is not automatic card-to-crypto. It is a compliant bridge that can collect card money faster while Alchemy Pay, Guardarian, Wert, and other on-ramp approvals are pending.

## Fastest UAE Card Collection Priority

1. Ziina
   - Official site: `https://ziina.com/`
   - Contact: `https://ziina.com/contact`
   - Support email from official help page: `support@ziina.com`
   - API docs: `https://docs.ziina.com/api-reference/payment-intent/index`
   - Best use: payment links first, API payment intents after account/API approval.

2. Mamo
   - Official site: `https://www.mamopay.com/`
   - Contact: `https://www.mamopay.com/contact`
   - Best use: UAE business/freelancer verification, payment links, e-commerce payments, API integration.

3. Tap Payments
   - Official UAE site: `https://www.tap.company/en-ae`
   - Contact/sales: `https://www.tap.company/en-ae/company/contact`
   - Best use: UAE/GCC card acquiring, payment links, Apple Pay / Google Pay where approved, API checkout.

4. Paymob UAE
   - Official UAE site/onboarding: `https://www.pos.paymob.ae/`
   - API docs: `https://developers.paymob.com/paymob-docs/integration-paths/apis`
   - Best use: payment links, POS/online checkout, APIs, UAE SME onboarding.

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

## Shared Outreach Text

Subject: Urgent UAE merchant payment-link/API onboarding request - KARMOSTAJI TRADING LLC

Hello,

We need fast merchant onboarding for UAE card/payment-link acceptance for KARMOSTAJI TRADING LLC, with legal applicant AL KARMOSTAJI TRADING ENTERPRISES, a Dubai licensed general trading business.

Use case:
Online retail payments for industrial sewing machines, including Juki brand machines from about 10,000 to 50,000 AED. We need a provider-hosted checkout/payment-link flow first, then API payment intents/webhooks if approved.

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
USD 20K - 100K / month initially.

Request:
1. Fastest onboarding route for UAE merchant payment links.
2. KYB document checklist and secure upload portal.
3. Timeline for payment-link activation.
4. API payment intent availability and webhook requirements.
5. Settlement bank requirements, payout timelines, and fees.
6. Whether this business category and ticket size are acceptable.

Our document package is ready. Please send the official secure upload/onboarding flow.

Best regards,
Mohammed Ali Vellopadikal
CEO / partner, KARMOSTAJI TRADING LLC
compliance@sichermayor.online
https://beastbrain.sichermayor.online/card-to-crypto

## BeastBrain Integration After Approval

After a provider account is approved:

- Ziina: mount `ZIINA_API_TOKEN`, `ZIINA_WEBHOOK_SECRET`, `ZIINA_ENV=production`.
- Mamo: add Mamo payment-link/API adapter once dashboard/API credentials are issued.
- Tap: add `TAP_SECRET_KEY`, `TAP_WEBHOOK_SECRET`, `TAP_ENV=production`.
- Paymob: add `PAYMOB_API_KEY`, public/secret keys, HMAC secret, integration ID, and environment.

Keep checkout provider-hosted. Do not collect raw card number, expiry, CVV, OTP, or merchant-side 3DS in BeastBrain.

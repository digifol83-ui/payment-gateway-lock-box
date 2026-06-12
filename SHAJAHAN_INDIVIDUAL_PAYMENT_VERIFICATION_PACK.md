# Shajahan Individual Payment Verification Pack

Last updated: 2026-05-21

Purpose: fastest compliant route to receive small card payments without Stripe, Transak, or Onramper, using Shajahan's valid individual documents where the provider supports individual or freelancer onboarding.

## Important Boundary

Use this only for an account verified in Shajahan's own name, or for a provider onboarding where Shajahan is the verified owner/signatory. Do not present an individual account as `SICHER MAYOR INVESTMENTS L.L.C` unless the provider has approved that company on the same account.

## Fastest Route

1. Ziina Personal payment link
   - Fastest likely path for small UAE card/Apple Pay/Google Pay collections.
   - Uses Emirates ID/app verification.
   - Best for immediate payment links.
   - Limitation: may not issue API credentials or custom checkout unless upgraded/approved.

2. Ziina API / Business
   - Best route if the requirement is API checkout inside BeastPay/BeastBrain.
   - Requires a Ziina access token with `write_payment_intents`.
   - If provider asks for business docs, use `SICHER MAYOR INVESTMENTS L.L.C` DED-1324297 or a valid freelancer/business permit matching Shajahan. Do not mix old unrelated entity docs.
   - Backend support is now implemented in `providers/ziina.py`; once a production token is provided, mount `ZIINA_API_TOKEN`, `ZIINA_WEBHOOK_SECRET`, and `ZIINA_ENV=production`.

3. Mamo Freelancer / Business
   - Use if Ziina does not approve the individual/API route.
   - Mamo supports UAE businesses and freelancers, but still requires verification.
   - If asked for freelancer proof, provide an active freelancer permit or trade license.

Tap, Paymob, Telr, Network International, Amazon Payment Services, and Checkout.com are stronger business-acquiring routes, but they are less likely to approve a pure individual account without business registration.

## Available Shajahan Documents On Disk

Use these only in provider-hosted onboarding forms:

- `/home/kali/payment-gateway/uploads/SHAJAHAN_passport_S0124841.jpeg`
- `/home/kali/payment-gateway/uploads/SHAJAHAN_EID_front_v2.png`
- `/home/kali/payment-gateway/uploads/SHAJAHAN_EID_back.png`
- `/home/kali/payment-gateway/uploads/Emirates_ID_Combined.pdf`

Additional supporting files available:

- `/home/kali/payment-gateway/uploads/09-May-2026_287713AccStmtDownloadReport_Final.pdf`
- `/home/kali/payment-gateway/uploads/31-Jul-2024_287713AccStmtDownloadReport.pdf`

Likely still needed during provider onboarding:

- Live selfie/liveness check in the provider app.
- Mobile OTP on Shajahan's phone.
- Bank account or IBAN in Shajahan's name if the account is individual.
- If API/business checkout is requested: business/freelancer proof matching the account name.

## Product Description For Individual Route

```
I am accepting small payments for Beast AI, an AI-powered content creation and productivity assistant. Customers buy digital AI credits or subscriptions for content generation and related online services. Typical transactions are below USD 20 equivalent. Card details are handled only by the licensed payment provider through a payment link or hosted checkout.
```

## Risk Controls To State If Asked

- No raw card numbers, expiry dates, or CVV are stored by BeastBrain.
- Provider-hosted checkout/payment links handle card entry and 3-D Secure.
- Payments are for digital AI credits and subscriptions, not investment products.
- Refunds and disputes are handled through the provider dashboard.

## Current Backend Readiness

Ziina code path is now implemented for Payment Intent API:

- Provider file: `/home/kali/payment-gateway/providers/ziina.py`
- Checkout method: `checkout_method = "ziina"`
- Webhook: `POST /webhooks/ziina`
- Required env:

```
ZIINA_API_TOKEN=
ZIINA_WEBHOOK_SECRET=
ZIINA_ENV=production
BASE_URL=https://beastpay-api-544494288390.us-central1.run.app
```

Current local env is sandbox/test only, so real card payments still require a verified production token.

## Live KYC Upload Status

Shajahan's passport and Emirates ID files were uploaded into BeastBrain's live KYC record:

- KYC user: `usr_5dce7309a29a4e2abaa8d11f86b772ca`
- Status: `documents_uploaded`
- Documents count: `4`
- Provider: `sumsub`
- Provider configured: `false`

The same files were copied to the private GCS path:

```
gs://beastpay-kyb-cs-poc-lym2gfaa9781su2yqiz25fq/shajahan-individual/
```

Selfie verification link status is tracked in:

```
/home/kali/payment-gateway/SHAJAHAN_SELFIE_VERIFICATION_STATUS.md
```

## Official References

- Ziina Payment Intent API: https://docs.ziina.com/api-reference/payment-intent/index
- Ziina create Payment Intent: https://docs.ziina.com/api-reference/payment-intent/create
- Ziina account endpoint: https://docs.ziina.com/api-reference/account/get
- Ziina webhooks: https://docs.ziina.com/api-reference/webhook/index
- Mamo getting started: https://help.mamopay.com/en/articles/7200023-getting-started-with-mamo
- Mamo business documents: https://help.mamopay.com/en/articles/9932398-business-documents

## Done Criteria

This route is live only when:

- Shajahan completes provider identity verification.
- Provider enables production card collection.
- A production API token or payment link is issued.
- For API checkout, `ZIINA_API_TOKEN` and `ZIINA_WEBHOOK_SECRET` are mounted in Cloud Run.
- A real small payment is confirmed by provider webhook or status check.

# Karmostaji Worldpay Access HPP MIT Activation Packet

Date: 2026-06-01

## Purpose

Prepare Worldpay Access Hosted Payment Pages activation for Karmostaji card-on-file / MIT review without claiming provider approval before Worldpay confirms it.

This packet is for Worldpay / Implementation Manager outreach and for later BeastBrain secret mounting after approval.

## Current BeastBrain Live State

- Live route: `https://beastbrain.sichermayor.online/api/ide/payments/checkout`
- Requested lane: `worldpay_mit_candidate`
- Current status: `blocked_missing_provider_credentials`
- Current blocker: `WORLDPAY_USERNAME`, `WORLDPAY_PASSWORD`, and a real `WORLDPAY_MERCHANT_ENTITY` beginning with `PO` are required.
- MIT readiness: `false`
- Raw card storage: `false`
- Merchant-side OTP support: `false`
- Merchant-side 3DS support: `false`

The public BeastBrain card-lock/autopay lane currently uses hosted Onramper-backed checkout/consent intents and rejects `worldpay_hpp`. The Worldpay lane remains a guarded MIT candidate inside Payment IDE only until Worldpay approval and production credentials exist.

## Non-Secret KYB Facts

- Legal name: `AL KARMOSTAJI TRADING ENTERPRISES`
- Requested client label: `KARMOSTAJI TRADING LLC`
- Legal type: `Limited Liability Company (LLC)`
- License number: `200100`
- Register number: `1387701`
- DCCI number: `7447`
- D-U-N-S: `534472717`
- License issue date: `1981-01-14`
- License expiry: `2027-01-13`
- Activity: `General Trading`
- Contact person: `Mohammed Ali Vellopadikal`
- Contact role/title: `CEO / partner, not staff`
- Contact phone: `0561049878`
- Reachable provider mailbox: `compliance@sichermayor.online`
- Estimated processing volume: `20K USD to 100K USD per month`
- Business line: `Industrial sewing machines, including Juki brand machines from 10,000 to 50,000 AED`
- Requested checkout domain: `https://beastbrain.sichermayor.online`
- Payment IDE route: `https://beastbrain.sichermayor.online/ide`
- Card-to-crypto route: `https://beastbrain.sichermayor.online/card-to-crypto`

Do not put passport numbers, OTPs, card numbers, provider tokens, cookies, or private identity-document identifiers in task text or chat.

## Worldpay Approval Ask

Ask Worldpay / Implementation Manager to provide or confirm:

- Production Access API Basic Auth username.
- Production Access API Basic Auth password.
- Production `merchant.entity` value for Access Worldpay, expected by BeastBrain as `WORLDPAY_MERCHANT_ENTITY`.
- Whether Access Hosted Payment Pages is enabled for this merchant.
- Whether card-on-file / token creation is enabled for this merchant.
- Whether merchant-initiated transaction / subscription-style subsequent payments are approved for this merchant and use case.
- Whether subsequent MIT payments must use the Payments API after an HPP token is created.
- Required HPP result URLs, webhook/query flow, and signature or reconciliation requirements.
- Required card scheme logo, statement narrative, and hosted page branding requirements.
- Whether AED processing is enabled and whether the UAE merchant entity is acceptable for this product category.
- Full KYB document list before any private documents are uploaded.

## Official Worldpay References

- HPP setup docs: `https://docs.worldpay.com/access/products/hosted-payment-pages/setup-a-payment`
- HPP OpenAPI docs: `https://docs.worldpay.com/access/products/hosted-payment-pages/openapi`
- Access API principles: `https://docs.worldpay.com/access/products/reference/api-principles`
- Dashboard: `https://dashboard.worldpay.com`
- Test endpoint: `https://try.access.worldpay.com/payment_pages`
- Live endpoint: `https://access.worldpay.com/payment_pages`

## Paste-Ready Worldpay Message

Subject: Worldpay Access HPP activation request for Karmostaji card-on-file / MIT

Hello,

We are preparing Worldpay Access Hosted Payment Pages activation for `AL KARMOSTAJI TRADING ENTERPRISES`, Dubai license `200100`, register `1387701`, DCCI `7447`, D-U-N-S `534472717`, expiry `2027-01-13`.

Contact person: `Mohammed Ali Vellopadikal`, CEO / partner, not staff. Contact phone: `0561049878`. Provider reply mailbox: `compliance@sichermayor.online`.

The intended use case is ecommerce / online retail payments for industrial sewing machines, including Juki brand machines, with item values generally from `10,000 to 50,000 AED`. Estimated processing volume is around `20K USD to 100K USD per month`.

We need provider-hosted card entry through Worldpay Access Hosted Payment Pages. Our application does not store raw card number, expiry, CVV, OTP, 3DS challenge data, or provider card tokens. We need explicit confirmation of whether this merchant can use card tokenization / card-on-file and later merchant-initiated or subscription-style subsequent payments where the cardholder is not present.

Please provide or confirm:

1. Production Access API username.
2. Production Access API password.
3. Production `merchant.entity` for Access Worldpay.
4. Whether Hosted Payment Pages is enabled for this merchant.
5. Whether token creation / stored credentials / card-on-file are enabled.
6. Whether merchant-initiated transaction or subscription-style subsequent payments are approved for this merchant and use case.
7. Whether subsequent MIT payments must be submitted through the Payments API after HPP token creation.
8. Required result URLs, webhook/query flow, signature verification, and reconciliation rules.
9. Required card scheme logo, page branding, and statement narrative requirements.
10. Exact KYB document list before any private identity or company documents are uploaded.

Requested domains:

- `https://beastbrain.sichermayor.online`
- `https://beastbrain.sichermayor.online/ide`
- `https://beastbrain.sichermayor.online/card-to-crypto`

Regards,
Karmostaji verification operator

## BeastBrain Action After Approval

After Worldpay confirms approval and the operator provides credentials through a secure channel:

1. Add Secret Manager secrets for `WORLDPAY_USERNAME`, `WORLDPAY_PASSWORD`, and `WORLDPAY_MERCHANT_ENTITY`.
2. Mount them on Cloud Run service `brain-api`.
3. Set `WORLDPAY_ENV=live` only when production approval is confirmed.
4. Set `WORLDPAY_HPP_RESULT_BASE_URL` to the confirmed result URL.
5. Deploy `brain-api`.
6. Smoke test `POST /api/ide/payments/checkout` with `mode=worldpay_mit_candidate`.
7. Do not mark `mit_ready=true` until the provider returns reusable-token or mandate evidence and BeastBrain records webhook/query-confirmed state.

## Hard Boundaries

- Do not enter or store raw card data in BeastBrain.
- Do not collect OTP, 3DS, MFA, CAPTCHA, or issuer challenge data in BeastBrain.
- Do not use temporary mailboxes for provider KYB.
- Do not upload private identity documents unless the official provider flow requests that specific document type.
- Do not enable unattended auto-debit until Worldpay confirms MIT/card-on-file support and BeastBrain has provider-confirmed reusable payment evidence.

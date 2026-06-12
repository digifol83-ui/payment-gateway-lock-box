# Karmostaji Adyen and Checkout.com Activation Packet

Date: 2026-05-28

## Purpose

Prepare provider activation for Adyen and Checkout.com using the Karmostaji KYB profile, without claiming approval before provider confirmation.

## Non-Secret KYB Facts

- Legal name: `AL KARMOSTAJI TRADING ENTERPRISES`
- Requested client label: `KARMOSTAJI TRADING LLC`
- License number: `200100`
- Register number: `1387701`
- DCCI number: `7447`
- D-U-N-S: `534472717`
- License expiry: `2027-01-13`
- Activity: `General Trading`
- Source document path: `/mnt/c/Users/shahe/Downloads/SecureCertificate201803.aspx.pdf`
- Contact person: `Mohammed Ali Vellopadikal`
- Contact role/title: `CEO / partner, not staff`
- Contact phone: `0561049878`
- Contact EID candidate if provider asks for Emirates ID evidence: `/mnt/c/Users/shahe/Downloads/eidvmali.pdf`
- Estimated processing volume: `20K USD to 100K USD per month`
- Product selection: `Ecommerce / online retail`
- Business line: `Industrial sewing machines, including Juki brand machines from 10,000 to 50,000 AED`

Do not put passport numbers, OTPs, card numbers, provider tokens, cookies, or private identity-document identifiers in task text or chat.

## Mail Choice

Requested mail domain URL: `https://beastbrain.sichermayor.online`

Requested admin mailbox: `admin@beastbrain.sichermayor.online`

Requested compliance mailbox: `compliance@beastbrain.sichermayor.online`

Live root compliance mailbox: `compliance@sichermayor.online`

Live root business mailbox: `business@sichermayor.online`

License-listed fallback: `karmostaji@hotmail.com`

Current mailbox status: root-domain forwarding is live for `compliance@sichermayor.online` and `business@sichermayor.online`, both routed through ForwardEmail DNS to `digifol83@gmail.com`. The old `@beastbrain.sichermayor.online` mailbox target should not be used for new provider replies because `beastbrain.sichermayor.online` is now the native Cloud Run web domain for BeastBrain.

Use `compliance@sichermayor.online` for Adyen and Checkout.com contact forms unless the operator explicitly chooses a different reachable mailbox. Keep the legal applicant as Karmostaji.

Only use an alternate mailbox for OTP/reply handling if the operator explicitly confirms the provider accepts it and it does not change the legal applicant from Karmostaji.

Do not use temporary mail for serious provider KYB unless the provider explicitly accepts it.

## Adyen Activation

Official contact: `https://www.adyen.com/en_AE/contact`

Account guidance: `https://help.adyen.com/en_US/knowledge/account/account-settings/how-can-i-get-an-adyen-account`

Ask Adyen to confirm:

- UAE merchant onboarding for Karmostaji.
- Card tokenization / card-on-file support.
- Recurring, unscheduled, or merchant-initiated transaction support.
- Webhook requirements and production API credential issuance.
- KYB document list before upload.

## Checkout.com Activation

Official contact: `https://www.checkout.com/contact-us`

Get started docs: `https://www.checkout.com/docs/get-started`

Ask Checkout.com to confirm:

- UAE merchant onboarding for Karmostaji.
- Vault tokenization / stored payment method support.
- Recurring or merchant-initiated transaction support.
- Webhook requirements and production API credential issuance.
- KYB document list before upload.

## Paste-Ready Outreach

Subject: Merchant activation request for Karmostaji card-on-file payments

Hello,

We are preparing merchant activation for `AL KARMOSTAJI TRADING ENTERPRISES`, Dubai license `200100`, register `1387701`, DCCI `7447`, D-U-N-S `534472717`, expiry `2027-01-13`. Contact person: `Mohammed Ali Vellopadikal`, CEO / partner, not staff. Contact phone: `0561049878`.

The intended use case is ecommerce / online retail payments for industrial sewing machines, including Juki brand machines, with item values generally from `10,000 to 50,000 AED`. Estimated processing volume is around `20K USD to 100K USD per month`. We also need provider-hosted online card payments with explicit customer consent, stored payment method or card-on-file support where approved, and later usage-capped recurring or merchant-initiated payments. We do not want to store raw card data in our application.

Please confirm whether your platform can onboard this UAE merchant entity for card tokenization/card-on-file, recurring or merchant-initiated payments, webhooks, and production API credentials. Please also send the exact KYB document list required before any private documents are uploaded. If CEO/partner identity evidence is needed, we can provide the relevant Emirates ID through the official upload flow.

Regards,
Karmostaji verification operator

## OpenClaw Boundaries

OpenClaw may open the official pages, capture visible non-secret blocker text, and record tasks in BeastBrain. It must stop at login, CAPTCHA, OTP/MFA, private document upload, legal signature, payment authorization, or any request for raw secrets.

## Current OpenClaw Status

- Adyen: sales contact page opened. Current OpenClaw form values should be updated to `Mohammed Ali Vellopadikal`, `CEO`, email `compliance@sichermayor.online`, `+971561049878`, `Karmostaji Trading LLC` in the company field because Adyen's company-name validator rejected the longer legal name, and the message states the full legal name `AL KARMOSTAJI TRADING ENTERPRISES`. Selected annual volume should stay `1 - 5 million` and solution `Accept payments online`. The optional Adyen marketing consent remains unchecked.
- Checkout.com: contact page opened. Current OpenClaw form values should be updated to `Mohammed Ali Vellopadikal`, `CEO`, email `compliance@sichermayor.online`, `+971561049878`, `AL KARMOSTAJI TRADING ENTERPRISES`, country `United Arab Emirates`, annual processing `1 - 10 Million`, products `Payment processing`, `Fraud Detection`, and `Authentication`, source `Online Research`, and acceptance checked. The comment describes ecommerce / online retail for industrial sewing machines including Juki brand machines from `10,000 to 50,000 AED`, estimated `20K USD to 100K USD per month`, and requests KYB requirements before private uploads.
- Mohammed Ali Vellopadikal is the active CEO/partner contact. Do not upload private ID files until the official provider upload step asks for that document type.

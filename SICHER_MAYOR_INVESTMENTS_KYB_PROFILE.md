# SICHER MAYOR INVESTMENTS L.L.C KYB Profile

Last updated: 2026-05-21

This file is the canonical provider-submission profile for the Investments entity. Use it for new non-Stripe payment provider applications unless the user explicitly switches back to the Commercial Brokers entity.

## Canonical Entity

| Field | Value |
|---|---|
| Legal entity | SICHER MAYOR INVESTMENTS L.L.C |
| Registration / license number | 1324297 |
| DED reference | DED-1324297 |
| Jurisdiction | Dubai, United Arab Emirates |
| Company type | LLC |
| Product | Beast AI / BeastBrain |
| Project description | Beast AI is an AI-powered content creation agent for creating, improving, and managing digital content. Users buy small AI-credit or subscription packages for content generation workflows. |
| Preferred review URL | https://brain-api-w7wsg6vria-uc.a.run.app |
| Alternate service URL | https://beastpay-api-544494288390.us-central1.run.app |

## Payment Use Case

Primary target: small card payments for digital AI credits and subscriptions, usually under USD 20 equivalent.

Important compliance note: customer-side KYC may be low or provider-managed for small digital-goods payments, but merchant KYB is still required by card acquirers and payment facilitators. Do not describe the merchant path as "no KYB" or try to bypass provider verification.

## Operating Position

- Stripe: excluded for this route per user direction.
- Transak: excluded for this route per user direction.
- Onramper: rejected/unreliable for this route.
- Telegram Stars: live for Beast AI digital goods, but this is not direct card acquiring and does not buy/settle crypto.
- Direct wallet: live for crypto wallet payments, but this is not card acquiring.
- Required next step for real card payments: open and approve a non-Stripe merchant account, then mount its production credentials in Cloud Run.

## Recommended Non-Stripe Card Providers

Priority order for a UAE digital-services merchant:

1. Ziina Business / Ziina API - fastest likely UAE small-business route for AED card, Apple Pay, Google Pay, payment links, and hosted payment intent.
2. Tap Payments - strong GCC/UAE acquirer route with payment links, checkout, SDKs, and local methods.
3. Paymob UAE - practical SME route with payment links and API checkout.
4. Telr - UAE payment gateway with hosted payment page and payment links.
5. Network International N-Genius - UAE acquirer/gateway route, usually more formal but strong local acquiring.
6. Amazon Payment Services - hosted checkout/payment links; good for MENA merchant acceptance.
7. Checkout.com - strong API and hosted flows, but usually heavier enterprise underwriting.

Crypto onramp providers such as MoonPay, Guardarian, Banxa, Ramp, Mercuryo, Alchemy Pay, or TransFi can be pursued separately only if the requirement is customer card-to-crypto. They still require partner approval and merchant KYB.

## Submission Copy

Use this concise description in provider forms:

```
Beast AI is an AI-powered content creation agent operated by SICHER MAYOR INVESTMENTS L.L.C in Dubai, UAE. Customers purchase small AI-credit and subscription packages for content generation, visual ideation, and productivity workflows. The expected ticket size is typically below USD 20 equivalent. Card details are handled only by the licensed payment provider through hosted checkout or payment links; BeastBrain does not store raw card numbers, expiry dates, or CVV.
```

If a provider asks about crypto:

```
The primary card-payment use case is digital AI content credits. Optional crypto wallet and on-chain payment features are separate from the card checkout and do not require BeastBrain to store card data.
```

## Required Documents For This Entity

Upload documents that match SICHER MAYOR INVESTMENTS L.L.C / DED-1324297:

- Trade license for SICHER MAYOR INVESTMENTS L.L.C.
- Commercial register or company registration extract for DED-1324297.
- MOA / Articles of Association for SICHER MAYOR INVESTMENTS L.L.C.
- Partners list / shareholder register matching the MOA.
- UBO/director passport and Emirates ID.
- Authorized signatory proof if someone other than the director signs.
- Company bank account letter or bank statement from the last 3 months.
- Proof of business address, tenancy contract, utility bill, or equivalent dated within 90 days if requested.
- Director liveness selfie or live-verification step if requested by the provider.

## Existing Local Document Evidence

Existing documents in `/home/kali/payment-gateway/uploads/` are recorded in `/home/kali/STATUS_REPORT_2026_05_09.md`. That inventory includes trade license, partners list, commercial register, chamber membership, MOA pages, POA, and personal documents, but the report is tied to SICHER MAYOR COMMERCIAL BROKERS L.L.C / DED 841208.

Do not submit those Commercial Brokers documents as the primary proof for SICHER MAYOR INVESTMENTS L.L.C unless the provider explicitly accepts related-entity documents. For the Investments entity, use the DED-1324297 license/MOA/partners documents.

Possible Investments license PDFs were previously referenced at:

- `/mnt/c/Users/shahe/Downloads/SICHER MAYOR INVESTMENTS L.L.C LICENSE 2024-25.pdf`
- `/mnt/c/Users/shahe/Downloads/SICHER MAYOR INVESTMENTS L.L.C LICENSE 2024-25 (1).pdf`

Checked on 2026-05-28: `/mnt/c/Users/shahe/Downloads/SICHERMAYOR_INVESTMENT_LLC_License.pdf` exists and has a PDF signature. It should be treated as the current candidate Investments trade license, pending visual/operator confirmation before provider upload. The MOA/articles and partners list for DED-1324297 still need to be identified before full KYB submission.

## Current Gaps Before Full KYB Submission

- Confirm the candidate SICHER MAYOR INVESTMENTS L.L.C trade license PDF is the correct current license for provider upload.
- Add the MOA/partners list for DED-1324297, not DED 841208.
- Add a company bank statement or account letter for the Investments entity.
- Add a current proof of address if the provider requests it.
- Complete any provider-hosted director liveness check.

## Provider Form Values

| Field | Value |
|---|---|
| Business name | SICHER MAYOR INVESTMENTS L.L.C |
| Business country | United Arab Emirates |
| City | Dubai |
| Business type | LLC |
| Product category | Software / AI content creation / digital services |
| Payment model | One-time small digital credit purchases and optional subscriptions |
| Typical ticket size | USD 5-20 equivalent |
| Delivery method | Digital service delivered through the BeastBrain web app and Telegram bot |
| Refund model | Refund failed/duplicate charges through the provider dashboard/API |
| Card data handling | Provider-hosted checkout only; no raw card data stored by BeastBrain |

# Provider Approval Fix Packet

Date: 2026-05-09
Project: BeastPay / SICHER MAYOR

## Current Answer

The backend is live, but real transactions are still blocked by provider approval/verification.

- Stripe has live keys, but `charges_enabled=false`.
- Stripe `card_payments` and `transfers` are both `inactive`.
- Transak credentials refresh successfully, but Create Widget URL rejects the partner token with `401 / errorCode 1002`.
- Cloud Run static egress is configured at `34.55.54.52`.

## Live URLs

- Main: `https://beastpay-api-544494288390.us-central1.run.app/`
- Checkout: `https://beastpay-api-544494288390.us-central1.run.app/checkout`
- Health: `https://beastpay-api-544494288390.us-central1.run.app/health`
- Transak redirect endpoint: `https://beastpay-api-544494288390.us-central1.run.app/api/transak/checkout`

## Stripe Exact Blockers

Stripe account: `acct_1TQ3oAPtWMtafyLP`

Fresh diagnostic:

- `country=AE`
- `default_currency=aed`
- `controller.type=account`
- `details_submitted=true`
- `charges_enabled=false`
- `payouts_enabled=false`
- `card_payments=inactive`
- `transfers=inactive`

Capability status:

- `card_payments.requested=true`
- `card_payments.status=inactive`
- `card_payments.disabled_reason=requirements.fields_needed`
- `transfers.requested=true`
- `transfers.status=inactive`
- `transfers.disabled_reason=requirements.fields_needed`

Stripe is asking for:

- `company.owners_provided`
- `documents.company_license.files`
- owner address fields
- owner date of birth fields
- owner passport document files
- owner first and last name
- owner ID number
- owner nationality
- person visa document for `person_1TTz20PtWMtafyLPhq3mWwiA`
- passport document for `person_1TTz6vPtWMtafyLPC6YSVbws`
- full identity document fields for `person_1TTzqaPtWMtafyLPec8Wrk5T`

Stripe returned these verification errors:

- Missing owners: Stripe identified `SHAJAHAN POTHANCHERRY ALAVI POTHANCHERRY` from the Memorandum of Association, but owner information has not been fully provided.
- Company license document was rejected as not readable.
- A visa document failed because business name/address on the account does not match government records.
- One person document was rejected because the document type is not accepted; Stripe asked for a passport document.

## Stripe Person Records Seen

Do not change these blindly. Legal owner/representative data must match the government documents.

- `person_1TTzqaPtWMtafyLPec8Wrk5T`: `SHANIB KAVUNGA PARAMBIL`, owner=true, missing DOB/address/nationality/ID/document data.
- `person_1TTz6vPtWMtafyLPC6YSVbws`: `MOHAMMED KHALEEL MOHAMMAED BUSEEM ALAWADHI`, owner=true, representative=true, executive=true, rejected passport requirement.
- `person_1TTz20PtWMtafyLPhq3mWwiA`: `shajahan pc`, owner=true, rejected visa requirement.
- `person_1TSVwsPtWMtafyLPushtgY3w`: `shajahan pc`, executive=true.

## Stripe Candidate Files Found Locally

These are candidate files, not automatic submissions. Confirm they are legally correct before upload.

Company/license:

- `/mnt/c/Users/shahe/Downloads/FRBkGZGtLGIlVeMt/SICHERMAYORINVESTMENTSL.L.CLICENSE_UPDATED.pdf`
- `/mnt/c/Users/shahe/Downloads/SICHER MAYOR INVESTMENTS L.L.C LICENSE 2024-25.pdf`
- `/mnt/c/Users/shahe/Downloads/SICHER MAYOR INVESTMENTS L.L.C LICENSE 2024-25 (1).pdf`
- `/home/kali/payment-gateway/uploads/6e22de07-2958-4011-b0d1-813d8f7f196a.jpeg`

Shajahan:

- `/home/kali/payment-gateway/uploads/SHAJAHAN_passport_S0124841.jpeg`
- `/home/kali/payment-gateway/uploads/SHAJAHAN_EID_front_v2.png`
- `/home/kali/payment-gateway/uploads/SHAJAHAN_EID_back.png`
- `/mnt/c/Users/shahe/Downloads/FRBkGZGtLGIlVeMt/VisaPage_Updated.pdf`
- `/mnt/c/Users/shahe/Downloads/VisaPage_Corrected.pdf`

Other person candidates:

- `/mnt/c/Users/shahe/Downloads/T2498948.pdf`
- `/home/kali/payment-gateway/uploads/MOHAMMED_JASEEM_passport_T2498948.pdf`
- `/mnt/c/Users/shahe/Downloads/MOHAMMED KHALIL sponsored EID UPDATTED.pdf`

## Stripe Fix Path

Because this is a direct Stripe account (`controller.type=account`), the safest fix path is Stripe Dashboard requirement submission, not API mutation from code.

Open:

`https://dashboard.stripe.com/settings/account`

Then fix the account verification requirements:

1. Confirm the correct legal entity name: Stripe currently appears tied to `sichermayor investments llc`, while other KYB docs mention `SICHER MAYOR COMMERCIAL BROKERS L.L.C`. These must match the uploaded license.
2. Re-upload a clear company license matching the account legal name and address.
3. Add/confirm all beneficial owners exactly as listed on the MOA.
4. For Shajahan, use the full legal name `SHAJAHAN POTHANCHERRY ALAVI POTHANCHERRY`, passport, DOB, nationality, EID/ID number, and UAE address from the approved government documents.
5. For every other listed owner/representative, upload the correct passport and fill address/DOB/nationality/ID fields.
6. Remove incorrect owners only if they are legally not owners/representatives. Do not remove real beneficial owners.
7. Submit for review and wait until:
   - `charges_enabled=true`
   - `payouts_enabled=true`
   - `card_payments=active`
   - `transfers=active`

## Transak Exact Blocker

Fresh live check:

- Cloud Run revision: `beastpay-api-00033-mm4`
- Static egress IP: `34.55.54.52`
- `/api/transak/checkout` returns HTTP 502 with:
  `transak_partner_access_token_rejected`
- Original Transak API error:
  `{'statusCode': 401, 'message': 'Invalid or missing access-token.', 'errorCode': 1002}`

Transak dashboard did not expose a self-service IP whitelist setting in the Developers page. It shows the Production API key/secret and Secure Widget URL instructions only.

## Transak Fix Path

Send this to Transak support:

```text
Subject: Enable Production API Create Widget URL and whitelist backend IP

Hello Transak Support Team,

Please enable API-based Create Widget URL for our Production partner account and whitelist our backend static egress IP.

Dashboard email: sichermayor@wshu.net
Backend URL: https://beastpay-api-544494288390.us-central1.run.app
Referrer domain: beastpay-api-544494288390.us-central1.run.app
Static backend egress IP: 34.55.54.52

Current behavior:
- POST https://api.transak.com/partners/api/v2/refresh-token succeeds and returns a partner access token.
- POST https://api-gateway.transak.com/api/v2/auth/session rejects the fresh token with:
  HTTP 401, Invalid or missing access-token, errorCode 1002.

Please enable:
- Production access to api-gateway.transak.com/api/v2/auth/session.
- API-based Create Widget URL for our Production API key.
- Backend IP whitelist for 34.55.54.52.
- Referrer domain approval for beastpay-api-544494288390.us-central1.run.app.
```

## Diagnostics

Run these anytime:

```bash
cd /home/kali/payment-gateway
python3 stripe_requirements_diag.py
python3 stripe_persons_diag.py
curl -i "https://beastpay-api-544494288390.us-central1.run.app/api/transak/checkout?amount=50&currency=USD&crypto=USDT&wallet=0x742d35Cc6634C0532925a3b844Bc454e4438f44e"
```

Ready means:

- Stripe: `card_payments=active`, `transfers=active`, `charges_enabled=true`.
- Transak: checkout endpoint returns HTTP 302 redirect to a Transak widget URL with `sessionId`.

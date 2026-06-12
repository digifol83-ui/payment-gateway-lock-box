# Shajahan Selfie Verification Status

Last updated: 2026-05-21

## Live BeastBrain KYC Record

Live URL:

```
https://brain-api-w7wsg6vria-uc.a.run.app
```

KYC user:

```
user_id: usr_5dce7309a29a4e2abaa8d11f86b772ca
external_user_id: shajahan-individual-card-verification
type: individual
country: ARE
level_name: basic-kyc-level
status: documents_uploaded
documents_count: 4
provider_configured: false
```

## Documents Uploaded To Live BeastBrain KYC Record

These files were uploaded from local disk to:

```
POST /api/kyc/users/usr_5dce7309a29a4e2abaa8d11f86b772ca/documents
```

Uploaded:

- `SHAJAHAN_passport_S0124841.jpeg` as `PASSPORT`
- `SHAJAHAN_EID_front_v2.png` as `ID_CARD`
- `SHAJAHAN_EID_back.png` as `ID_CARD`
- `Emirates_ID_Combined.pdf` as `ID_CARD`

Current provider upload result:

```
provider_upload_status: skipped_not_configured
```

Reason: Cloud Run `brain-api` does not currently mount `SUMSUB_APP_TOKEN` or `SUMSUB_SECRET_KEY`, so documents are stored in BeastBrain KYC but are not submitted to Sumsub yet.

## Durable Private GCS Copy

The same files were copied to the private GCS KYB bucket:

```
gs://beastpay-kyb-cs-poc-lym2gfaa9781su2yqiz25fq/shajahan-individual/SHAJAHAN_passport_S0124841.jpeg
gs://beastpay-kyb-cs-poc-lym2gfaa9781su2yqiz25fq/shajahan-individual/SHAJAHAN_EID_front_v2.png
gs://beastpay-kyb-cs-poc-lym2gfaa9781su2yqiz25fq/shajahan-individual/SHAJAHAN_EID_back.png
gs://beastpay-kyb-cs-poc-lym2gfaa9781su2yqiz25fq/shajahan-individual/Emirates_ID_Combined.pdf
```

Do not make these objects public. Use them only for provider onboarding or private backend submission.

## Selfie Link Blocker

The selfie verification link cannot be generated yet because:

```
POST /api/kyc/users/usr_5dce7309a29a4e2abaa8d11f86b772ca/sumsub/token
-> SUMSUB_APP_TOKEN or SUMSUB_SECRET_KEY is not configured
```

`gcloud secrets list` currently does not include Sumsub secrets, and Cloud Run `brain-api` currently mounts only:

```
TRANSAK_ENV
TRANSAK_API_KEY
TRANSAK_SECRET
BRAIN_DEFAULT_REASONER
GEMINI_API_KEY
TELEGRAM_BOT_TOKEN
```

## Exact Next Step To Generate Selfie Link

Create these Secret Manager secrets from the Sumsub dashboard values:

```
sumsub-app-token
sumsub-secret-key
sumsub-webhook-secret
```

Mount them to Cloud Run:

```
gcloud run services update brain-api \
  --region us-central1 \
  --update-secrets=SUMSUB_APP_TOKEN=sumsub-app-token:latest,SUMSUB_SECRET_KEY=sumsub-secret-key:latest,SUMSUB_WEBHOOK_SECRET=sumsub-webhook-secret:latest \
  --update-env-vars=SUMSUB_KYC_LEVEL_NAME=basic-kyc-level
```

Then generate the WebSDK token:

```
curl -sS -X POST \
  https://brain-api-w7wsg6vria-uc.a.run.app/api/kyc/users/usr_5dce7309a29a4e2abaa8d11f86b772ca/sumsub/token
```

That response will contain the short-lived Sumsub WebSDK token for Shajahan to complete selfie/liveness verification.


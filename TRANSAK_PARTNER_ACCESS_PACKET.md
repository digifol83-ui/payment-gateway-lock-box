# Transak Partner Access Packet

Date: 2026-05-09
Project: BeastPay / SICHER MAYOR

## Live Project URLs

- Main: `https://beastpay-api-544494288390.us-central1.run.app/`
- Checkout: `https://beastpay-api-544494288390.us-central1.run.app/checkout`
- Health: `https://beastpay-api-544494288390.us-central1.run.app/health`
- Transak redirect endpoint: `https://beastpay-api-544494288390.us-central1.run.app/api/transak/checkout`

## Current GCP Service

- GCP project: `cs-poc-lym2gfaa9781su2yqiz25fq`
- Cloud Run service: `beastpay-api`
- Region: `us-central1`
- Latest checked revision: `beastpay-api-00032-6lg`
- Service account: `544494288390-compute@developer.gserviceaccount.com`
- Transak dashboard email: `sichermayor@wshu.net`
- Transak environment: `PRODUCTION`
- Transak referrer domain: `beastpay-api-544494288390.us-central1.run.app`

## Verified Behavior

- Cloud Run `/health` returns HTTP 200 and database connected.
- Transak Production API key and API secret are installed through Secret Manager as `transak-api-key` and `transak-secret`.
- Direct Transak refresh-token call returns HTTP 200 and creates a partner JWT access token.
- Direct Create Widget URL/session call rejects that fresh partner token with HTTP 401:
  `Invalid or missing access-token`, `errorCode` 1002.
- Live BeastPay Transak checkout returns HTTP 502 with:
  `transak_partner_access_token_rejected`.

This means the local app now reaches Transak correctly. The remaining blocker is Transak-side enablement/whitelisting for API-based Create Widget URL.

## Message To Send To Transak

Subject: Enable Production API Create Widget URL and backend IP whitelisting

Hello Transak Support Team,

Please enable API-based Create Widget URL for our Production partner account and confirm backend/IP whitelisting requirements.

Account:
- Company: SICHER MAYOR
- Dashboard email: sichermayor@wshu.net
- Production referrer domain: beastpay-api-544494288390.us-central1.run.app
- Backend URL: https://beastpay-api-544494288390.us-central1.run.app
- Backend provider: Google Cloud Run, us-central1
- Static backend egress IP: 34.55.54.52

Current verified behavior:
- `POST https://api.transak.com/partners/api/v2/refresh-token` succeeds with our Production API key and API secret.
- The returned partner JWT is valid for the Production API key.
- `POST https://api-gateway.transak.com/api/v2/auth/session` immediately rejects that same fresh token with HTTP 401:
  `Invalid or missing access-token`, `errorCode` 1002.

Please confirm and enable:
- Production access to `api-gateway.transak.com/api/v2/auth/session`.
- The Production API key is approved for API-based Create Widget URL.
- Backend/Cloud Run egress IP whitelisting is complete.
- Static backend egress IP `34.55.54.52` is whitelisted.
- The referrer domain `beastpay-api-544494288390.us-central1.run.app` is approved.

No secrets are included in this message. We can provide the API key fingerprint or dashboard account details privately if needed.

## Static Egress Status

Static outbound IP is configured.

Evidence checked on 2026-05-09:
- Reserved regional address `beastpay-transak-egress` is `34.55.54.52` and status is `IN_USE`.
- Cloud NAT `beastpay-nat` uses `beastpay-transak-egress` in manual IP allocation mode.
- Cloud Run revision `beastpay-api-00033-mm4` routes all outbound traffic through `default/default` with `vpc-access-egress=all-traffic`.

Send `34.55.54.52` to Transak for backend IP whitelisting.

## Static Egress Runbook

These commands have been run. Keep them here for rebuild/audit purposes. They reserve a static IP, configure Cloud NAT, and route Cloud Run outbound traffic through the VPC.

The current Google Cloud recommendation is Direct VPC egress plus Cloud NAT.

```bash
PROJECT_ID=cs-poc-lym2gfaa9781su2yqiz25fq
REGION=us-central1
SERVICE=beastpay-api
NETWORK=default
SUBNET=default
ADDRESS=beastpay-transak-egress
ROUTER=beastpay-nat-router
NAT=beastpay-nat

gcloud config set project "$PROJECT_ID"
gcloud services enable compute.googleapis.com run.googleapis.com

gcloud compute addresses create "$ADDRESS" \
  --region="$REGION"

gcloud compute routers create "$ROUTER" \
  --network="$NETWORK" \
  --region="$REGION"

gcloud compute routers nats create "$NAT" \
  --router="$ROUTER" \
  --region="$REGION" \
  --nat-external-ip-pool="$ADDRESS" \
  --nat-all-subnet-ip-ranges

gcloud run services update "$SERVICE" \
  --region="$REGION" \
  --network="$NETWORK" \
  --subnet="$SUBNET" \
  --vpc-egress=all-traffic

gcloud compute addresses describe "$ADDRESS" \
  --region="$REGION" \
  --format="value(address)"
```

Send the final IP printed by the last command to Transak for backend whitelisting.

## Post-Whitelist Verification

After Transak confirms access and IP/domain whitelisting:

```bash
curl -i "https://beastpay-api-544494288390.us-central1.run.app/api/transak/checkout?amount=50&currency=USD&crypto=USDT&wallet=0x742d35Cc6634C0532925a3b844Bc454e4438f44e"
```

Expected result after Transak enables access: HTTP 302 redirect to a Transak widget URL containing a one-time `sessionId`.

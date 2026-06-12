#!/bin/bash
# ONE-KEYSTROKE LIVE ACTIVATION
# Updates BOTH local .env AND the deployed Cloud Run service in one shot.
#
# Usage:
#   ./activate_live.sh transak  pk_live_XXX  sk_live_YYY  [access_token]
#   ./activate_live.sh stripe   sk_live_XXX  pk_live_YYY  whsec_ZZZ
#   ./activate_live.sh ziina    Bearer_TOKEN

set -e

GATEWAY=$1
KEY=$2
SECRET=${3:-}
EXTRA=${4:-}

if [ -z "$GATEWAY" ] || [ -z "$KEY" ]; then
    echo "Usage: $0 <gateway> <api_key> [secret] [extra]"
    echo "Examples:"
    echo "  $0 transak  pk_live_xxx  sk_live_yyy  access_token_zzz"
    echo "  $0 stripe   sk_live_xxx  pk_live_yyy  whsec_zzz"
    exit 1
fi

UPPER=$(echo "$GATEWAY" | tr '[:lower:]' '[:upper:]')
SERVICE="beastpay-api"
REGION="us-central1"

echo "=== 1/3 Updating local .env ==="
python3 activate_any_gateway.py "$GATEWAY" "$KEY" "$SECRET" "$EXTRA"

echo
echo "=== 2/3 Building env-vars list for Cloud Run ==="
ENV_VARS="${UPPER}_API_KEY=${KEY}"
if [ -n "$SECRET" ]; then
    ENV_VARS="${ENV_VARS},${UPPER}_SECRET=${SECRET}"
fi
if [ -n "$EXTRA" ]; then
    case "$GATEWAY" in
        transak)  ENV_VARS="${ENV_VARS},TRANSAK_ACCESS_TOKEN=${EXTRA}" ;;
        stripe)   ENV_VARS="${ENV_VARS},STRIPE_WEBHOOK_SECRET=${EXTRA}" ;;
        moonpay)  ENV_VARS="${ENV_VARS},MOONPAY_WEBHOOK_SECRET=${EXTRA}" ;;
        *)        ENV_VARS="${ENV_VARS},${UPPER}_WEBHOOK_SECRET=${EXTRA}" ;;
    esac
fi
ENV_VARS="${ENV_VARS},${UPPER}_ENV=PRODUCTION"

echo "Pushing: ${ENV_VARS}"

echo
echo "=== 3/3 Pushing to Cloud Run ==="
gcloud run services update "$SERVICE" \
    --region "$REGION" \
    --update-env-vars "$ENV_VARS" \
    --quiet 2>&1 | tail -5

echo
echo "=== Verifying live status ==="
sleep 3
URL="https://beastpay-api-544494288390.us-central1.run.app"
curl -s -m 10 "$URL/api/providers/status" | python3 -c "
import json, sys
data = json.load(sys.stdin)
gw = '${GATEWAY}'
for p in data.get('providers', []):
    if p['id'] == gw:
        icon = '🟢 LIVE' if p['production'] else '🟡 SANDBOX'
        print(f\"{icon}: {p['name']} -> {p['status']}\")
        sys.exit(0)
print(f'Provider {gw} not found in response')
"

echo
echo "✅ Done. Live URL: https://beastpay-api-544494288390.us-central1.run.app"

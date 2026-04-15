#!/usr/bin/env bash
# BeastPay — ngrok public URL setup
# Usage: source .env && bash ngrok_setup.sh [authtoken]
# Sets BASE_URL in .env, starts tunnel, registers Telegram webhook.

set -e
GATEWAY_DIR="$(cd "$(dirname "$0")" && pwd)"
ENV_FILE="$GATEWAY_DIR/.env"
PORT="${PORT:-8000}"

# ─── 1. Install ngrok if missing ─────────────────────────────────────────────
if ! command -v ngrok &>/dev/null; then
    echo "[ngrok] Installing ngrok..."
    if command -v snap &>/dev/null; then
        sudo snap install ngrok
    elif command -v apt-get &>/dev/null; then
        curl -sSL https://ngrok-agent.s3.amazonaws.com/ngrok.asc \
            | sudo tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null
        echo "deb https://ngrok-agent.s3.amazonaws.com buster main" \
            | sudo tee /etc/apt/sources.list.d/ngrok.list
        sudo apt-get update -q && sudo apt-get install -y ngrok
    else
        echo "[ngrok] Cannot auto-install. Visit https://ngrok.com/download"
        exit 1
    fi
fi

# ─── 2. Auth token ────────────────────────────────────────────────────────────
NGROK_TOKEN="${1:-$NGROK_AUTHTOKEN}"
if [ -n "$NGROK_TOKEN" ]; then
    ngrok config add-authtoken "$NGROK_TOKEN"
fi

# ─── 3. Kill any existing ngrok ──────────────────────────────────────────────
pkill -f "ngrok http" 2>/dev/null || true
sleep 1

# ─── 4. Start tunnel in background ───────────────────────────────────────────
echo "[ngrok] Starting tunnel on port $PORT..."
nohup ngrok http "$PORT" --log=stdout > /tmp/ngrok_beastpay.log 2>&1 &
NGROK_PID=$!
echo "[ngrok] PID $NGROK_PID"
sleep 3

# ─── 5. Get public URL from ngrok API ────────────────────────────────────────
PUBLIC_URL=$(curl -s http://localhost:4040/api/tunnels \
    | python3 -c "
import sys, json
try:
    tunnels = json.load(sys.stdin).get('tunnels', [])
    https = [t for t in tunnels if t['proto'] == 'https']
    print((https or tunnels)[0]['public_url'])
except Exception as e:
    print('')
" 2>/dev/null)

if [ -z "$PUBLIC_URL" ]; then
    echo "[ngrok] ERROR: Could not get public URL. Check /tmp/ngrok_beastpay.log"
    exit 1
fi

echo ""
echo "  ✓ Public URL: $PUBLIC_URL"
echo ""

# ─── 6. Update BASE_URL in .env ──────────────────────────────────────────────
if grep -q 'export BASE_URL=' "$ENV_FILE"; then
    sed -i "s|export BASE_URL=.*|export BASE_URL=\"$PUBLIC_URL\"|" "$ENV_FILE"
else
    echo "export BASE_URL=\"$PUBLIC_URL\"" >> "$ENV_FILE"
fi
echo "  ✓ Updated BASE_URL in .env"

# ─── 7. Register Telegram webhook ────────────────────────────────────────────
if [ -n "$TELEGRAM_BOT_TOKEN" ]; then
    echo "  Registering Telegram webhook..."
    RESULT=$(curl -s -X POST \
        "https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/setWebhook" \
        -H "Content-Type: application/json" \
        -d "{\"url\": \"${PUBLIC_URL}/telegram/incoming\", \"allowed_updates\": [\"message\",\"edited_message\"]}")
    OK=$(echo "$RESULT" | python3 -c "import sys,json; print(json.load(sys.stdin).get('ok',''))")
    if [ "$OK" = "True" ]; then
        echo "  ✓ Telegram webhook registered → ${PUBLIC_URL}/telegram/incoming"
    else
        echo "  ✗ Telegram webhook failed: $RESULT"
    fi
else
    echo "  [skip] TELEGRAM_BOT_TOKEN not set — skipping webhook registration"
fi

# ─── 8. Summary ──────────────────────────────────────────────────────────────
echo ""
echo "┌─────────────────────────────────────────────────────────────┐"
echo "│  BeastPay — Public URLs                                     │"
echo "│                                                             │"
echo "│  Admin:     ${PUBLIC_URL}/admin"
echo "│  Webhooks:  ${PUBLIC_URL}/webhooks/{transak,moonpay,...}"
echo "│  Telegram:  ${PUBLIC_URL}/telegram/incoming"
echo "│                                                             │"
echo "│  Re-run this script if ngrok restarts (URL changes).        │"
echo "│  ngrok logs: tail -f /tmp/ngrok_beastpay.log               │"
echo "└─────────────────────────────────────────────────────────────┘"
echo ""
echo "  Now restart the server: source .env && uvicorn server:app --host 0.0.0.0 --port $PORT"

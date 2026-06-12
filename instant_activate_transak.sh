#!/bin/bash
# INSTANT TRANSAK ACTIVATION
# Usage: ./instant_activate_transak.sh <api_key> <secret>

set -e

if [ $# -lt 2 ]; then
    echo "❌ Usage: ./instant_activate_transak.sh <api_key> <secret>"
    echo ""
    echo "Get your keys from: https://www.transak.com/business/dashboard"
    echo ""
    echo "Example:"
    echo "  ./instant_activate_transak.sh pk_live_abc123 sk_live_def456"
    exit 1
fi

API_KEY="$1"
SECRET="$2"

echo ""
echo "⚡ INSTANT TRANSAK ACTIVATION"
echo "================================"
echo ""

cd /home/kali/payment-gateway

echo "🔑 Activating with API key: ${API_KEY:0:10}..."
echo ""

python3 gateway_provisioner_skill.py activate transak "$API_KEY" "$SECRET"

echo ""
echo "================================"
echo ""

echo "✅ ACTIVATION COMPLETE!"
echo ""
echo "Next steps:"
echo ""
echo "1. Verify activation:"
echo "   python3 gateway_provisioner_skill.py status"
echo ""
echo "2. Visit the checkout page:"
echo "   http://localhost:8000/buy?provider=transak"
echo ""
echo "3. Test with a small transaction (if live)"
echo ""
echo "Done! 🚀"
echo ""

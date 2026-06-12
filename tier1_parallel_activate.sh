#!/bin/bash
# Tier 1 parallel activation orchestrator
# Starts inbox watcher, then runs 3 signup fillers in sequence

set -e

cd /home/kali/payment-gateway

echo
echo "════════════════════════════════════════════════════════════════"
echo "  🚀  TIER 1 GATEWAY PARALLEL ACTIVATION"
echo "════════════════════════════════════════════════════════════════"
echo
echo "Gateways to activate (all at once):"
echo "  • NOWPayments    — Run: python3 nowpayments_signup_filler.py"
echo "  • Plisio         — Run: python3 plisio_signup_filler.py"
echo "  • CoinRemitter   — Run: python3 coinremitter_signup_filler.py"
echo
echo "📧 Email: sichermayor@deltajohnsons.com"
echo
echo "🔍 Inbox watcher starting (auto-activates as keys arrive)..."
python3 tier1_activation_watcher.py &
WATCHER_PID=$!
echo "   Watcher PID: $WATCHER_PID"
echo

sleep 2

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 NOWPAYMENTS SIGNUP"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
python3 nowpayments_signup_filler.py
echo

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 PLISIO SIGNUP"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
python3 plisio_signup_filler.py
echo

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📋 COINREMITTER SIGNUP"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
python3 coinremitter_signup_filler.py
echo

echo
echo "════════════════════════════════════════════════════════════════"
echo "✅ ALL SIGNUPS COMPLETE"
echo "════════════════════════════════════════════════════════════════"
echo
echo "📧 Inbox watcher is still running (PID: $WATCHER_PID)"
echo "⏰ Waiting for API key emails (typically 1-5 minutes)..."
echo "⏹️  Watcher will auto-exit when all 3 gateways are activated"
echo
echo "   To manually stop watcher: kill $WATCHER_PID"
echo
echo "🔗 To check live gateways: curl https://beastpay-api-*.run.app/api/providers/status"
echo

# Wait for watcher to complete
wait $WATCHER_PID 2>/dev/null || true

echo
echo "════════════════════════════════════════════════════════════════"
echo "✅ TIER 1 ACTIVATION COMPLETE"
echo "════════════════════════════════════════════════════════════════"
echo

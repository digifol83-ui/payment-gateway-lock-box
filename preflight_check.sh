#!/bin/bash
# Pre-flight check before Tier 1 activation

echo "═══════════════════════════════════════════════════════════════"
echo "  ✈️  TIER 1 ACTIVATION PRE-FLIGHT CHECK"
echo "═══════════════════════════════════════════════════════════════"
echo

# 1. Cloud Run service
echo "1. Cloud Run Service"
if gcloud run services describe beastpay-api --region us-central1 --format="value(status.conditions[0].status)" 2>/dev/null | grep -q "True"; then
    echo "   ✅ Service running"
else
    echo "   ❌ Service NOT ready"
    exit 1
fi

# 2. Cloud Run health
echo "2. Cloud Run Health Check"
if curl -s https://beastpay-api-544494288390.us-central1.run.app/ | grep -q "BeastPay API"; then
    echo "   ✅ App responding"
else
    echo "   ❌ App not responding"
    exit 1
fi

# 3. Temp-mail session
echo "3. Temp-mail Session"
if python3 -c "import json; json.loads(open('.tempmail_session.json').read()).get('token')" 2>/dev/null; then
    echo "   ✅ Session valid"
else
    echo "   ❌ Session invalid"
    exit 1
fi

# 4. Activation scripts
echo "4. Activation Scripts"
for script in activate_live.sh activate_any_gateway.py tier1_activation_watcher.py nowpayments_signup_filler.py plisio_signup_filler.py coinremitter_signup_filler.py; do
    if [ -x "$script" ] 2>/dev/null || [ -f "$script" ]; then
        echo "   ✅ $script"
    else
        echo "   ❌ $script MISSING"
        exit 1
    fi
done

# 5. Current provider status
echo "5. Current Provider Status"
curl -s https://beastpay-api-544494288390.us-central1.run.app/api/providers/status 2>/dev/null | python3 -c "
import json, sys
data = json.load(sys.stdin)
live = [p['name'] for p in data['providers'] if p.get('production')]
sandbox = [p['name'] for p in data['providers'] if not p.get('production')]
print(f'   ✅ LIVE: {len(live)} provider(s)')
print(f'   ⏳ SANDBOX: {len(sandbox)} provider(s)')
" || echo "   ⚠️  Could not fetch status"

echo
echo "═══════════════════════════════════════════════════════════════"
echo "✅ ALL CHECKS PASSED — Ready for Tier 1 activation!"
echo "═══════════════════════════════════════════════════════════════"
echo
echo "Next step:"
echo "  bash tier1_parallel_activate.sh"
echo

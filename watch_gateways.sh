#!/usr/bin/env bash
# watch_gateways.sh — Polls all three fiat gateways until they're ready for real checkout
set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

SERVER="${1:-http://localhost:8000}"
MAX_TRIES="${2:-120}"

echo -e "${BOLD}${CYAN}╔══════════════════════════════════════════════════════╗${NC}"
echo -e "${BOLD}${CYAN}║     BEASTPAY GATEWAY READINESS MONITOR               ║${NC}"
echo -e "${BOLD}${CYAN}╚══════════════════════════════════════════════════════╝${NC}"
echo -e "  Watching: Stripe | Transak | MoonPay"
echo -e "  Interval: 30s | Max: $((MAX_TRIES * 30 / 60)) min"
echo ""

all_ready=0
tries=0

while [ $tries -lt $MAX_TRIES ]; do
  tries=$((tries + 1))
  ts=$(date '+%H:%M:%S')

  resp=$(curl -s --max-time 25 "$SERVER/api/providers/real-payment-status" 2>/dev/null || echo "{}")

  # Parse each provider
  stripe_ready=$(echo "$resp" | python3 -c "import sys,json; d=json.load(sys.stdin); checks=[c for c in d.get('checks',[]) if c['provider_id']=='stripe']; print('YES' if checks and checks[0].get('ready_for_real_payment') else 'NO')" 2>/dev/null || echo "ERR")
  transak_ready=$(echo "$resp" | python3 -c "import sys,json; d=json.load(sys.stdin); checks=[c for c in d.get('checks',[]) if c['provider_id']=='transak']; print('YES' if checks and checks[0].get('ready_for_real_payment') else 'NO')" 2>/dev/null || echo "ERR")
  moonpay_ready=$(echo "$resp" | python3 -c "import sys,json; d=json.load(sys.stdin); checks=[c for c in d.get('checks',[]) if c['provider_id']=='moonpay']; print('YES' if checks and checks[0].get('ready_for_real_payment') else 'NO')" 2>/dev/null || echo "ERR")

  stripe_stat=$(echo "$resp" | python3 -c "import sys,json; d=json.load(sys.stdin); checks=[c for c in d.get('checks',[]) if c['provider_id']=='stripe']; print(checks[0].get('status','?'))" 2>/dev/null || echo "?")
  transak_stat=$(echo "$resp" | python3 -c "import sys,json; d=json.load(sys.stdin); checks=[c for c in d.get('checks',[]) if c['provider_id']=='transak']; print(checks[0].get('status','?'))" 2>/dev/null || echo "?")
  moonpay_stat=$(echo "$resp" | python3 -c "import sys,json; d=json.load(sys.stdin); checks=[c for c in d.get('checks',[]) if c['provider_id']=='moonpay']; print(checks[0].get('status','?'))" 2>/dev/null || echo "?")

  s_icon="${RED}✗${NC}"; [ "$stripe_ready" = "YES" ] && s_icon="${GREEN}✓${NC}"
  t_icon="${RED}✗${NC}"; [ "$transak_ready" = "YES" ] && t_icon="${GREEN}✓${NC}"
  m_icon="${RED}✗${NC}"; [ "$moonpay_ready" = "YES" ] && m_icon="${GREEN}✓${NC}"

  echo -e "  [${ts}] Stripe: $s_icon ($stripe_stat) | Transak: $t_icon ($transak_stat) | MoonPay: $m_icon ($moonpay_stat) | ${tries}/${MAX_TRIES}"

  if [ "$stripe_ready" = "YES" ] && [ "$transak_ready" = "YES" ] && [ "$moonpay_ready" = "YES" ]; then
    echo ""
    echo -e "${BOLD}${GREEN}╔══════════════════════════════════════════════════════╗${NC}"
    echo -e "${BOLD}${GREEN}║  ✅ ALL GATEWAYS READY FOR REAL CHECKOUT!            ║${NC}"
    echo -e "${BOLD}${GREEN}╚══════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "  Run: ${CYAN}curl $SERVER/api/providers/real-payment-status | python3 -m json.tool${NC}"
    exit 0
  fi

  # Check if any single gateway just became ready
  if [ "$stripe_ready" = "YES" ] && [ "$stripe_stat" != "api_error" ]; then
    echo -e "  ${GREEN}🟢 STRIPE IS NOW READY!${NC}"
  fi
  if [ "$transak_ready" = "YES" ] && [ "$transak_stat" != "provider_access_rejected" ]; then
    echo -e "  ${GREEN}🟢 TRANSAK IS NOW READY!${NC}"
  fi
  if [ "$moonpay_ready" = "YES" ] && [ "$moonpay_stat" != "not_configured" ]; then
    echo -e "  ${GREEN}🟢 MOONPAY IS NOW READY!${NC}"
  fi

  sleep 30
done

echo ""
echo -e "${RED}${BOLD}⏰ Timeout after $((MAX_TRIES * 30 / 60)) minutes${NC}"
exit 1

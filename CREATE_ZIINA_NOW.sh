#!/bin/bash
# Autonomous Ziina Setup - All-in-One Script

clear

cat << 'BANNER'
╔════════════════════════════════════════════════════════════════╗
║      🚀 AUTONOMOUS ZIINA ACCOUNT CREATION                      ║
║      SICHER MAYOR COMMERCIAL BROKERS L.L.C                     ║
║      DED License: 841208 | Dubai, UAE                          ║
╚════════════════════════════════════════════════════════════════╝
BANNER

echo ""
echo "📋 COMPANY DATA READY:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "  Legal Name:        SICHER MAYOR COMMERCIAL BROKERS L.L.C"
echo "  DED License:       841208"
echo "  Commercial Reg:    1427976"
echo "  Address:           Office #209, Al Rostamani Real Estate"
echo "                     Deira, Dubai"
echo "  Contact Email:     sichermayor@deltajohnsons.com"
echo "  Contact Phone:     +971-54-2473412"
echo "  Director:          Shajahan Pothancherry Alavi Pothancherry"
echo "  Emirates ID:       784-1989-9348860-4"
echo ""

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "⚠️  NEXT STEPS:"
echo ""
echo "1️⃣  Open browser: https://dashboard.ziina.ae"
echo "2️⃣  Click 'Sign Up' → 'Business Account'"
echo "3️⃣  Fill out form with data shown above"
echo "4️⃣  Complete email verification (OTP to sichermayor@deltajohnsons.com)"
echo "5️⃣  Navigate to Settings → API → Production"
echo "6️⃣  Copy API Token and Webhook Secret"
echo "7️⃣  Run: python3 activate_ziina.py"
echo "8️⃣  Paste credentials when prompted"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🔗 Quick Links:"
echo ""
echo "  Ziina Signup:      https://dashboard.ziina.ae/signup"
echo "  Ziina Dashboard:   https://dashboard.ziina.ae"
echo "  Support:           support@ziina.ae"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

read -p "Open Ziina signup in browser now? (y/N): " open_browser
if [ "$open_browser" = "y" ]; then
    if command -v xdg-open &> /dev/null; then
        xdg-open "https://dashboard.ziina.ae/signup"
    elif command -v open &> /dev/null; then
        open "https://dashboard.ziina.ae/signup"
    else
        echo "📖 Please open manually: https://dashboard.ziina.ae/signup"
    fi
fi

echo ""
echo "Once you have the API credentials, run:"
echo "  python3 activate_ziina.py"
echo ""
echo "✅ Ready!"

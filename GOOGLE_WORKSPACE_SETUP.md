# 🏢 GOOGLE WORKSPACE BUSINESS EMAIL SETUP

**Create professional business email for Transak + payment gateways**

---

## 📋 Overview

Setup path:
1. ✅ Verify domain ownership (sichermayorfx.com)
2. ✅ Create Google Workspace account
3. ✅ Set up business email (business@sichermayorfx.com)
4. ✅ Auto-configure Gmail for gateway signups
5. ✅ Activate Transak business account

---

## 🚀 STEP 1: Verify Domain Ownership

**Your Domain:** sichermayorfx.com

### Check Current Registrar

```bash
whois sichermayorfx.com
```

### If on Hostinger:
1. Log in: https://hpanel.hostinger.com
2. Go to **Domains** → **sichermayorfx.com**
3. Find **DNS** or **Nameservers** section
4. Note current settings (you'll need to add Google MX records)

### If on GoDaddy:
1. Log in: https://www.godaddy.com
2. Go to **My Domains** → **sichermayorfx.com**
3. Find **DNS Management**
4. Save current settings

---

## 🏢 STEP 2: Create Google Workspace Account

### Option A: Via Google Workspace (Recommended)

1. Go to: https://workspace.google.com/
2. Click **"Start your free trial"**
3. Select plan: **Business Starter** ($6/user/month)
4. Sign in with: `ullaakcrypto@gmail.com`
5. On "Get your business email" → Enter domain: `sichermayorfx.com`
6. Click **Verify domain ownership**

### Verify Ownership (Google will guide you)

**Option 1: MX Record** (easiest, takes 1-2 hours)
- Google gives you MX records to add
- Go to your domain registrar
- Add the MX records
- Wait for verification (usually 1 hour)

**Option 2: TXT Record** (instant)
- Google gives you a TXT record
- Add it to DNS
- Verify immediately

**Option 3: HTML File** (slowest)
- Download an HTML file
- Upload to your website
- Not recommended

**→ Pick Option 1 (MX Record) or 2 (TXT Record)**

### Complete Workspace Setup

Once domain verified:
1. Create your user account:
   - Name: **Business**
   - Email: **business@sichermayorfx.com**
   - Password: (strong password, save it)
2. Add payment method (credit card)
3. Billing: You'll be charged ~$6/month

---

## 📧 STEP 3: Access Business Email

### Log In

1. Go to: https://gmail.google.com
2. Sign in with: `business@sichermayorfx.com`
3. Set up 2FA (recommended for security)

### Set Up Email Forwarding (Optional)

Auto-forward to your personal email:
1. Click ⚙️ → **Settings** → **Forwarding and POP/IMAP**
2. Add forwarding address: `digifol83@gmail.com`
3. Confirm the verification email
4. Enable "Keep Gmail's copy in the mailbox"

---

## 🤖 STEP 4: Auto-Email Monitoring Setup

Once email exists, configure automated verification:

```bash
# Set up Gmail API credentials
python3 google_cloud_integration.py setup-gmail

# This will guide you through OAuth2 setup
```

**You'll need:**
1. Google Cloud project (free tier OK)
2. Gmail API enabled
3. OAuth2 credentials downloaded

### Google Cloud Setup (Free)

1. Go to: https://console.cloud.google.com
2. Create new project: **BeastPay**
3. Enable APIs:
   - Gmail API
   - Secret Manager API
   - Domains API
4. Create OAuth2 credentials:
   - Application type: Web
   - Authorized redirect: `http://localhost:8000/callback`
5. Download `credentials.json` to: `/home/kali/payment-gateway/credentials.json`

---

## 🎯 STEP 5: Sign Up for Transak Business

Now that you have `business@sichermayorfx.com`:

### Direct Transak Signup

1. Go to: https://transak.com/business-signup
2. Fill out the form:
   - **Email:** `business@sichermayorfx.com`
   - **Company:** SICHER MAYOR INVESTMENTS LLC
   - **Website:** https://sichermayorfx.com
   - **Business Type:** Payment Service Provider
   - **Monthly Volume:** $100,000+
   - **Countries:** UAE, Global
3. Submit application

### What Transak Will Ask

- ✅ Business registration (you have DED License 841208)
- ✅ Director info (you have this)
- ✅ Bank details (for payouts)
- ✅ Website verification (your domain)

### Approval Timeline

- **Initial review:** 2-4 hours
- **AED enablement request:** Email partners@transak.com from `business@sichermayorfx.com`
- **Full approval:** 24-48 hours

### Once Approved

- Transak sends API keys to `business@sichermayorfx.com`
- Copy the keys
- Run: `python3 gateway_provisioner_skill.py activate transak <key> <secret>`
- **LIVE! 🚀**

---

## 🔐 Complete Automation Script

Once business email is set up, run this to prepare everything:

```bash
#!/bin/bash
# complete_business_setup.sh

BUSINESS_EMAIL="business@sichermayorfx.com"
COMPANY="SICHER MAYOR INVESTMENTS LLC"
DOMAIN="sichermayorfx.com"

echo "🏢 Business Email Setup Automation"
echo "=================================="
echo ""
echo "Business Email: $BUSINESS_EMAIL"
echo "Company: $COMPANY"
echo "Domain: $DOMAIN"
echo ""

# Step 1: Verify Google Workspace is configured
echo "Step 1: Verifying Google Workspace..."
python3 google_cloud_integration.py status

# Step 2: Setup Gmail API
echo "Step 2: Setting up Gmail API..."
python3 google_cloud_integration.py setup-gmail

# Step 3: Store domain info
echo "Step 3: Storing domain configuration..."
python3 google_cloud_integration.py store-secret business-email $BUSINESS_EMAIL
python3 google_cloud_integration.py store-secret company-name "$COMPANY"
python3 google_cloud_integration.py store-secret domain-name $DOMAIN

# Step 4: Prepare Transak credentials storage
echo "Step 4: Preparing credential storage..."
mkdir -p /home/kali/payment-gateway/.secrets
chmod 700 /home/kali/payment-gateway/.secrets

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. Go to: https://transak.com/business-signup"
echo "2. Use email: $BUSINESS_EMAIL"
echo "3. Once you get API keys, run:"
echo "   python3 gateway_provisioner_skill.py activate transak <key> <secret>"
echo ""
```

---

## 💰 Costs

| Service | Cost | Notes |
|---------|------|-------|
| Google Workspace | $6/user/month | Business Starter plan |
| Google Cloud | FREE | Free tier, pay only for extras |
| Transak | Variable | 2-3% transaction fee |
| Domain (sichermayorfx.com) | ~$15/year | Already owned |

**Total monthly: ~$6** (just the business email)

---

## ✅ DNS Records You'll Need

Once Google Workspace is set up, you'll add these to your domain:

### MX Records (for email)
```
Priority 5  → gmail-smtp-in.l.google.com.
Priority 10 → alt1.gmail-smtp-in.l.google.com.
Priority 20 → alt2.gmail-smtp-in.l.google.com.
Priority 30 → alt3.gmail-smtp-in.l.google.com.
Priority 40 → alt4.gmail-smtp-in.l.google.com.
```

### SPF Record
```
v=spf1 include:_spf.google.com ~all
```

### DKIM Record
(Google Workspace will give you this)

### CNAME Record (for domain verification)
(Google Workspace will give you this)

---

## 🎯 Timeline

| Task | Time | Status |
|------|------|--------|
| Verify domain | 1-2h | Automated |
| Create Google Workspace | 30m | Requires payment |
| Setup Gmail API | 15m | Automated |
| Transak business signup | 10m | Automated form |
| Transak approval | 2-48h | Automatic |
| Get API keys | Instant | Once approved |
| Activate in BeastPay | 1m | `python3 activate...` |
| **LIVE** | ✅ | **Real money flowing** |

---

## 🚨 Important Notes

- ✅ Keep `business@sichermayorfx.com` password secure
- ✅ Enable 2FA on Google Workspace account
- ✅ Archive verification emails from Transak
- ✅ Store API keys in Google Secret Manager (automated)
- ✅ Monitor the account for payment gateway emails

---

## 🆘 Troubleshooting

### Domain verification takes too long?
- Try TXT record method instead (instant)
- Check your domain registrar's DNS propagation

### Not receiving verification emails?
- Check spam folder
- Make sure MX records are correct
- Wait 1-2 hours for DNS to propagate

### Transak rejects application?
- Verify you're using business email
- Include all company documents
- Email: partners@transak.com for manual review

---

## 🎉 Once It's Live

```bash
# Check provider status
python3 gateway_provisioner_skill.py status

# Should show:
# 🟢 Transak | fiat-to-crypto | AED: ✅ | LIVE ✅

# Visit checkout page
http://localhost:8000/buy?provider=transak

# Real money accepted! 💰
```

---

**Next: Follow the steps above, then share your API keys and I'll activate instantly.**

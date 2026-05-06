# BeastPay Google Cloud Deployment Guide

**Project ID:** `cs-poc-lym2gfaa9781su2yqiz25fq`  
**Region:** `us-central1`  
**Free Tier:** $300 credit (90 days)

---

## 📋 Pre-Deployment Checklist

- [ ] Google Cloud Project created (cs-poc-lym2gfaa9781su2yqiz25fq)
- [ ] Billing enabled
- [ ] `gcloud` CLI installed locally
- [ ] Authenticated with GCP: `gcloud auth login`
- [ ] Provider API keys ready (Bleap, KAST, Stripe, etc.)
- [ ] Encryption key generated: `openssl rand -hex 32`

---

## 🚀 ONE-COMMAND DEPLOYMENT

```bash
cd /home/kali/payment-gateway
./deploy.sh cs-poc-lym2gfaa9781su2yqiz25fq us-central1
```

**The script will:**
1. ✅ Enable required GCP APIs (Cloud Run, Container Registry, Cloud SQL, Secret Manager)
2. ✅ Create service account with proper IAM roles
3. ✅ Prompt you for all secrets (API keys, encryption keys, DB credentials)
4. ✅ Upload secrets to Google Secret Manager (encrypted)
5. ✅ Build Docker image and push to Container Registry
6. ✅ Deploy to Cloud Run
7. ✅ Provide live service URL

---

## 📦 What Gets Deployed

### **Docker Image** (`Dockerfile`)
- Multi-stage build (optimized ~200MB)
- Python 3.11 slim base
- Non-root user for security
- Health checks enabled
- Uvicorn with 4 workers

### **Cloud Build CI/CD** (`cloudbuild.yaml`)
- Builds on every commit (if using GitHub)
- Runs pytest before deployment
- Pushes to Container Registry
- Deploys to Cloud Run

### **Cloud Run Service** (`app.yaml`)
- 2 vCPU, 2GB RAM per instance
- Auto-scaling (0-100 instances)
- All secrets injected from Secret Manager
- Health checks (liveness + readiness)
- Timeout: 3600s (1 hour for long-running requests)

---

## 🔐 Secrets Management

**Required secrets** (will be prompted):

```
✓ DATABASE_URL          → Cloud SQL connection string
✓ ENCRYPTION_KEY        → AES-256 key (32-byte hex)
✓ ADMIN_API_KEY         → For admin endpoints
✓ BLEAP_API_KEY         → Bleap provider credentials
✓ BLEAP_SECRET
✓ KAST_API_KEY          → KAST provider credentials
✓ KAST_SECRET
✓ STRIPE_SECRET_KEY     → Stripe payment processor
✓ STRIPE_PUBLISHABLE_KEY
✓ TELEGRAM_BOT_TOKEN    → For payment notifications
```

**All secrets are:**
- Encrypted at rest in Google Secret Manager
- Injected at runtime into container
- Never logged or exposed
- Rotatable without redeployment

---

## 🗄️ Database Setup (Cloud SQL)

### Option 1: Using Cloud Console (Manual)
1. Go to Cloud SQL in GCP Console
2. Create PostgreSQL 14 instance
3. Create database: `beastpay`
4. Get connection string: `postgresql://user:password@host:5432/beastpay`

### Option 2: Using gcloud CLI
```bash
gcloud sql instances create beastpay-db \
  --database-version=POSTGRES_14 \
  --tier=db-f1-micro \
  --region=us-central1 \
  --project=cs-poc-lym2gfaa9781su2yqiz25fq

# Create database
gcloud sql databases create beastpay \
  --instance=beastpay-db \
  --project=cs-poc-lym2gfaa9781su2yqiz25fq

# Create user
gcloud sql users create beastpay \
  --instance=beastpay-db \
  --password=YOUR_STRONG_PASSWORD \
  --project=cs-poc-lym2gfaa9781su2yqiz25fq
```

**Connection string format:**
```
postgresql://beastpay:PASSWORD@/beastpay?unix_socket=/cloudsql/PROJECT_ID:REGION:INSTANCE_NAME
```

---

## 🔄 Step-by-Step Deployment

### **Step 1: Install gcloud CLI**
```bash
# macOS
brew install google-cloud-sdk

# Ubuntu/Debian
curl https://sdk.cloud.google.com | bash
exec -l $SHELL

# Verify
gcloud --version
```

### **Step 2: Authenticate**
```bash
gcloud auth login
# Browser will open - confirm access
# Then set project:
gcloud config set project cs-poc-lym2gfaa9781su2yqiz25fq
```

### **Step 3: Generate Encryption Key**
```bash
openssl rand -hex 32
# Output: abc123def456...  (save this!)
```

### **Step 4: Run Deployment Script**
```bash
cd /home/kali/payment-gateway
chmod +x deploy.sh
./deploy.sh cs-poc-lym2gfaa9781su2yqiz25fq us-central1
```

### **Step 5: Provide Secrets When Prompted**
```
Database URL: postgresql://user:pass@host/beastpay
Encryption Key: abc123def456...
Admin API Key: admin_key_xyz
Bleap API Key: bleap_key_123
... (continue for all prompts)
```

### **Step 6: Wait for Deployment**
- Docker build: ~3-5 minutes
- Upload to registry: ~1 minute
- Deploy to Cloud Run: ~2 minutes
- **Total:** ~10 minutes

### **Step 7: Get Service URL**
```bash
gcloud run services describe beastpay-api \
  --region us-central1 \
  --format 'value(status.url)'

# Output: https://beastpay-api-xyz123.run.app
```

---

## ✅ Post-Deployment Steps

### **1. Verify Service is Running**
```bash
# Health check
curl https://beastpay-api-xyz123.run.app/health

# Should return:
# {"ok": true, "service": "api", "env": "production"}
```

### **2. Update Provider Webhooks**
Register webhook URLs in each provider's dashboard:

| Provider | Webhook URL |
|----------|---|
| Bleap | `https://beastpay-api-xyz.run.app/v1/webhooks/bleap` |
| KAST | `https://beastpay-api-xyz.run.app/v1/webhooks/kast` |
| Swapin | `https://beastpay-api-xyz.run.app/v1/webhooks/swapin` |
| Guardarian | `https://beastpay-api-xyz.run.app/v1/webhooks/guardarian` |

### **3. Test Checkout Page**
```
https://beastpay-api-xyz123.run.app/web/checkout.html
```

### **4. View Admin Dashboard**
```
https://beastpay-api-xyz123.run.app/admin
```

### **5. Check Swagger Docs**
```
https://beastpay-api-xyz123.run.app/docs
```

---

## 📊 Monitoring & Logs

### **View Logs**
```bash
# Last 50 log entries
gcloud run logs read beastpay-api --region us-central1 --limit 50

# Stream logs (live)
gcloud run logs read beastpay-api --region us-central1 --follow

# Filter by severity
gcloud run logs read beastpay-api --region us-central1 --level ERROR
```

### **View Metrics**
```bash
# In Cloud Console:
# Cloud Run → beastpay-api → Metrics
# Shows: Requests, Errors, Latency, CPU, Memory
```

### **Set Up Alerts**
```bash
# Cloud Monitoring → Create Policy
# Alert on: Error rate > 5%, Latency > 3s
```

---

## 💰 Cost Estimation

| Service | Usage | Cost |
|---------|-------|------|
| Cloud Run | 100K requests/month | $0 (free tier: 2M/mo) |
| Cloud SQL | db-f1-micro, 1GB storage | ~$10-15/month |
| Secret Manager | 10 secrets | ~$1/month |
| Container Registry | ~100MB | ~$1/month |
| **Total** | | **~$15-20/month** |

**Free Tier Benefits:**
- ✅ $300 credit (valid 90 days)
- ✅ 2M Cloud Run requests/month (always free)
- ✅ Cloud SQL: first 30 days free
- ✅ 5GB Cloud Storage (always free)

---

## 🔧 Troubleshooting

### **Build fails: "Docker daemon not found"**
```bash
# The script uses Cloud Build (not local Docker)
# Make sure Cloud Build API is enabled:
gcloud services enable cloudbuild.googleapis.com
```

### **Deployment timeout: "Service account not found"**
```bash
# Wait 30 seconds, the service account creation may be delayed
./deploy.sh cs-poc-lym2gfaa9781su2yqiz25fq us-central1
```

### **Secrets not injecting: "Secret not found"**
```bash
# Verify secret exists:
gcloud secrets list --project cs-poc-lym2gfaa9781su2yqiz25fq

# Check service account has access:
gcloud secrets get-iam-policy DATABASE_URL --project cs-poc-lym2gfaa9781su2yqiz25fq
```

### **Database connection fails**
```bash
# Verify Cloud SQL instance is running:
gcloud sql instances describe beastpay-db

# Check connection string format (must match):
postgresql://user:pass@/dbname?unix_socket=/cloudsql/PROJECT:REGION:INSTANCE
```

### **Webhook returns 404**
```bash
# Verify service URL:
gcloud run services describe beastpay-api --region us-central1

# Test endpoint:
curl -v https://beastpay-api-xyz.run.app/v1/webhooks/bleap
# Should return 405 (Method Not Allowed) for GET - that's OK
```

---

## 🚀 Continuous Deployment (Optional)

### **Connect GitHub Repository**
```bash
# Enable Cloud Build API
gcloud services enable cloudbuild.googleapis.com

# Connect repository (via Cloud Console)
# Cloud Build → Repositories → Connect

# Create build trigger on push
# Source: github.com/your-org/beastpay
# Branch: main
# Build config: cloudbuild.yaml
```

Once connected:
- Every push to `main` → automatic build
- Tests run first
- Auto-deploy on success
- Rollback available on failure

---

## 📞 Support

**GCP Issues:**
- https://cloud.google.com/support
- https://stackoverflow.com/questions/tagged/google-cloud-platform

**BeastPay Issues:**
- Check logs: `gcloud run logs read beastpay-api`
- Test health: `curl https://api.example.com/health`
- Admin dashboard: `https://api.example.com/admin`

---

**Ready to deploy?** Run:
```bash
./deploy.sh cs-poc-lym2gfaa9781su2yqiz25fq us-central1
```

🎉 Your payment gateway will be live in ~10 minutes!

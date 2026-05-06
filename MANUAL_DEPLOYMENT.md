# Manual GCP Deployment Instructions

**Status:** Infrastructure setup complete ✅  
**Secrets configured:** 10 secrets in Google Secret Manager ✅  
**Service account:** Created with proper IAM roles ✅

**What's left:** Deploy the Docker image from your local machine.

---

## 🚀 Quick Start (5 minutes)

### **1. On Your Local Machine: Install gcloud**

```bash
# macOS
brew install google-cloud-sdk

# Ubuntu/Debian
curl https://sdk.cloud.google.com | bash
```

### **2. Authenticate**

```bash
gcloud auth login
gcloud config set project cs-poc-lym2gfaa9781su2yqiz25fq
```

### **3. Clone/Copy Code**

```bash
cd /path/to/beastpay
# or: git clone <your-repo>
```

### **4. Deploy to Cloud Run**

```bash
gcloud run deploy beastpay-api \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --service-account=beastpay-sa@cs-poc-lym2gfaa9781su2yqiz25fq.iam.gserviceaccount.com \
  --memory 1Gi \
  --cpu 1 \
  --timeout 3600 \
  --max-instances 5 \
  --project=cs-poc-lym2gfaa9781su2yqiz25fq
```

**That's it!** Cloud Run will:
- ✅ Build the Docker image
- ✅ Push to Container Registry
- ✅ Deploy and start the service
- ✅ Provide a live HTTPS URL

---

## 📊 What's Already Configured in GCP

✅ **Secrets (Google Secret Manager):**
- database-url
- encryption-key
- admin-api-key
- bleap-api-key, bleap-secret
- kast-api-key, kast-secret
- stripe-secret-key, stripe-publishable-key
- telegram-bot-token

✅ **Service Account:** `beastpay-sa` with roles:
- Cloud Run Admin
- Cloud SQL Client
- Secret Manager Accessor

✅ **APIs Enabled:**
- Cloud Run
- Cloud Build
- Container Registry
- Cloud SQL
- Secret Manager

---

## ✨ Alternative: Pre-built Image

If you have Docker running locally:

```bash
# Build image locally
docker build -t gcr.io/cs-poc-lym2gfaa9781su2yqiz25fq/beastpay-api:latest .

# Authenticate Docker with GCP
gcloud auth configure-docker

# Push to GCP Container Registry
docker push gcr.io/cs-poc-lym2gfaa9781su2yqiz25fq/beastpay-api:latest

# Deploy from pre-built image
gcloud run deploy beastpay-api \
  --image gcr.io/cs-poc-lym2gfaa9781su2yqiz25fq/beastpay-api:latest \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --service-account=beastpay-sa@cs-poc-lym2gfaa9781su2yqiz25fq.iam.gserviceaccount.com \
  --memory 1Gi \
  --cpu 1 \
  --timeout 3600 \
  --max-instances 5 \
  --project=cs-poc-lym2gfaa9781su2yqiz25fq
```

---

## 🔐 Secrets Configuration

All secrets are already in Google Secret Manager. Once deployed, Cloud Run will automatically inject them as environment variables.

**To update a secret:**

```bash
echo "new_value" | gcloud secrets versions add encryption-key \
  --data-file=- \
  --project=cs-poc-lym2gfaa9781su2yqiz25fq
```

---

## ✅ After Deployment

**1. Get the service URL:**
```bash
gcloud run services describe beastpay-api \
  --region us-central1 \
  --format='value(status.url)' \
  --project=cs-poc-lym2gfaa9781su2yqiz25fq
```

**2. Test health:**
```bash
curl https://beastpay-api-xxxxx.run.app/health
```

**3. Update provider webhooks:**
- Bleap: `https://beastpay-api-xxxxx.run.app/v1/webhooks/bleap`
- KAST: `https://beastpay-api-xxxxx.run.app/v1/webhooks/kast`
- etc.

**4. View logs:**
```bash
gcloud run logs read beastpay-api \
  --region us-central1 \
  --follow \
  --project=cs-poc-lym2gfaa9781su2yqiz25fq
```

---

## 📞 Troubleshooting

### Deployment fails with "Build failed"
→ Check logs:
```bash
gcloud builds log $(gcloud builds list --limit=1 --format='value(id)') \
  --project=cs-poc-lym2gfaa9781su2yqiz25fq
```

### Service won't start (CrashLoopBackOff)
→ Check logs for errors:
```bash
gcloud run logs read beastpay-api --region us-central1
```

### Secrets not loading
→ Verify they exist:
```bash
gcloud secrets list --project=cs-poc-lym2gfaa9781su2yqiz25fq
```

---

## 💡 Pro Tips

- **Cloud Run is serverless:** You pay per request, not per hour
- **Auto-scaling:** Scales from 0 to 5 instances automatically
- **Free tier:** 2M requests/month always free
- **Fast coldstarts:** ~1 second from first request

---

**Ready to deploy?**

```bash
gcloud run deploy beastpay-api \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --service-account=beastpay-sa@cs-poc-lym2gfaa9781su2yqiz25fq.iam.gserviceaccount.com \
  --memory 1Gi \
  --cpu 1 \
  --timeout 3600 \
  --max-instances 5 \
  --project=cs-poc-lym2gfaa9781su2yqiz25fq
```

Your API will be live in ~3-5 minutes! 🎉

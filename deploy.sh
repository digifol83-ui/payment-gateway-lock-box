#!/bin/bash

###############################################################################
# BeastPay Deployment Script for Google Cloud Run
# Usage: ./deploy.sh [project-id] [region]
###############################################################################

set -e

PROJECT_ID="${1:-cs-poc-lym2gfaa9781su2yqiz25fq}"
REGION="${2:-us-central1}"
SERVICE_NAME="beastpay-api"

echo "🚀 BeastPay Deployment Script"
echo "=============================="
echo "Project ID: $PROJECT_ID"
echo "Region: $REGION"
echo "Service: $SERVICE_NAME"
echo ""

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ gcloud CLI not found. Install from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Step 1: Set GCP project
echo "📝 Setting GCP project..."
gcloud config set project $PROJECT_ID

# Step 2: Enable required APIs
echo "🔧 Enabling required GCP APIs..."
gcloud services enable \
    run.googleapis.com \
    cloudbuild.googleapis.com \
    containerregistry.googleapis.com \
    sqladmin.googleapis.com \
    secretmanager.googleapis.com

# Step 3: Create service account (if not exists)
echo "👤 Setting up service account..."
SERVICE_ACCOUNT="beastpay-sa"
SERVICE_ACCOUNT_EMAIL="$SERVICE_ACCOUNT@$PROJECT_ID.iam.gserviceaccount.com"

if ! gcloud iam service-accounts describe $SERVICE_ACCOUNT_EMAIL --project=$PROJECT_ID &>/dev/null; then
    echo "Creating service account: $SERVICE_ACCOUNT_EMAIL"
    gcloud iam service-accounts create $SERVICE_ACCOUNT \
        --display-name="BeastPay Service Account" \
        --project=$PROJECT_ID
fi

# Grant Cloud Run permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
    --role="roles/run.admin" \
    --quiet

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
    --role="roles/cloudsql.client" \
    --quiet

gcloud projects add-iam-policy-binding $PROJECT_ID \
    --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
    --role="roles/secretmanager.secretAccessor" \
    --quiet

# Step 4: Prompt for secrets
echo ""
echo "🔐 Secrets Configuration"
echo "========================"
echo ""
echo "You need to provide the following secrets (press Enter to skip):"
echo ""

read -p "Database URL (Cloud SQL connection string): " DATABASE_URL
read -p "Encryption Key (32-byte hex): " ENCRYPTION_KEY
read -p "Admin API Key: " ADMIN_API_KEY
read -p "Bleap API Key: " BLEAP_API_KEY
read -p "Bleap Secret: " BLEAP_SECRET
read -p "KAST API Key: " KAST_API_KEY
read -p "KAST Secret: " KAST_SECRET
read -p "Stripe Secret Key: " STRIPE_SECRET_KEY
read -p "Stripe Publishable Key: " STRIPE_PUBLISHABLE_KEY
read -p "Telegram Bot Token: " TELEGRAM_BOT_TOKEN

# Step 5: Create/update secrets in Secret Manager
echo ""
echo "📦 Creating secrets in Google Secret Manager..."

create_secret() {
    SECRET_NAME=$1
    SECRET_VALUE=$2

    if [ -z "$SECRET_VALUE" ]; then
        echo "⊘ Skipping $SECRET_NAME (empty)"
        return
    fi

    # Check if secret exists
    if gcloud secrets describe $SECRET_NAME --project=$PROJECT_ID &>/dev/null; then
        echo "🔄 Updating secret: $SECRET_NAME"
        echo -n "$SECRET_VALUE" | gcloud secrets versions add $SECRET_NAME \
            --data-file=- \
            --project=$PROJECT_ID
    else
        echo "✨ Creating secret: $SECRET_NAME"
        echo -n "$SECRET_VALUE" | gcloud secrets create $SECRET_NAME \
            --data-file=- \
            --replication-policy="automatic" \
            --project=$PROJECT_ID

        # Grant service account access
        gcloud secrets add-iam-policy-binding $SECRET_NAME \
            --member="serviceAccount:$SERVICE_ACCOUNT_EMAIL" \
            --role="roles/secretmanager.secretAccessor" \
            --project=$PROJECT_ID
    fi
}

create_secret "database-url" "$DATABASE_URL"
create_secret "encryption-key" "$ENCRYPTION_KEY"
create_secret "admin-api-key" "$ADMIN_API_KEY"
create_secret "bleap-api-key" "$BLEAP_API_KEY"
create_secret "bleap-secret" "$BLEAP_SECRET"
create_secret "kast-api-key" "$KAST_API_KEY"
create_secret "kast-secret" "$KAST_SECRET"
create_secret "stripe-secret-key" "$STRIPE_SECRET_KEY"
create_secret "stripe-publishable-key" "$STRIPE_PUBLISHABLE_KEY"
create_secret "telegram-bot-token" "$TELEGRAM_BOT_TOKEN"

# Step 6: Build and push Docker image
echo ""
echo "🐳 Building Docker image..."
gcloud builds submit \
    --config=cloudbuild.yaml \
    --project=$PROJECT_ID

# Step 7: Deploy to Cloud Run
echo ""
echo "🚀 Deploying to Cloud Run..."

# Replace PROJECT_ID in app.yaml
sed "s/PROJECT_ID/$PROJECT_ID/g" app.yaml > app-final.yaml

gcloud run deploy $SERVICE_NAME \
    --source . \
    --platform managed \
    --region $REGION \
    --allow-unauthenticated \
    --service-account=$SERVICE_ACCOUNT_EMAIL \
    --memory 2Gi \
    --cpu 2 \
    --timeout 3600 \
    --max-instances 100 \
    --project=$PROJECT_ID

# Cleanup
rm -f app-final.yaml

# Step 8: Get service URL
echo ""
echo "✅ Deployment complete!"
echo ""

SERVICE_URL=$(gcloud run services describe $SERVICE_NAME \
    --platform managed \
    --region $REGION \
    --format 'value(status.url)' \
    --project=$PROJECT_ID)

echo "🎉 BeastPay API is now live!"
echo ""
echo "Service URL: $SERVICE_URL"
echo "Health Check: $SERVICE_URL/health"
echo "Admin Dashboard: $SERVICE_URL/admin"
echo "Checkout: $SERVICE_URL/web/checkout.html"
echo "Swagger Docs: $SERVICE_URL/docs"
echo ""
echo "📋 Next steps:"
echo "1. Update webhook URLs in provider dashboards with:"
echo "   - Bleap: $SERVICE_URL/v1/webhooks/bleap"
echo "   - KAST: $SERVICE_URL/v1/webhooks/kast"
echo "   - Swapin: $SERVICE_URL/v1/webhooks/swapin"
echo "   - Guardarian: $SERVICE_URL/v1/webhooks/guardarian"
echo ""
echo "2. Test payment flow: curl -X GET $SERVICE_URL/health"
echo ""
echo "3. Monitor logs: gcloud run logs read $SERVICE_NAME --region $REGION --limit 50"
echo ""

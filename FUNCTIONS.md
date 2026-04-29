# BeastPay Function Reference

Complete function inventory with signatures, file locations, and purpose.

---

## 📍 Server Routes (server.py)

### Payment Operations

```python
# Create payment link
POST /orders
@router.post("/orders")
async def create_order(merchant_id: str, crypto: str, amount_usd: float, 
                       webhook_url: str = None, metadata: dict = None) -> dict
# Location: server.py:156
# Returns: {"order_id", "provider", "payment_url", "expires_at"}
```

```python
# Get payment status
GET /orders/{order_id}
@router.get("/orders/{order_id}")
async def get_order_status(order_id: str) -> dict
# Location: server.py:178
# Returns: {"status", "amount_crypto", "tx_hash", "provider"}
```

```python
# List payments
GET /payments
@router.get("/payments")
async def list_payments(merchant_id: str = None, status: str = None, 
                        limit: int = 50, skip: int = 0) -> list
# Location: server.py:195
# Returns: [Payment records]
```

### Merchant Management

```python
# Register merchant
POST /merchants/register
@router.post("/merchants/register")
async def register_merchant(company_name: str, email: str, 
                           country: str, webhook_url: str = None) -> dict
# Location: server.py:85
# Returns: {"merchant_id", "api_key", "status"}
```

```python
# Get merchant profile
GET /merchants/{merchant_id}
@router.get("/merchants/{merchant_id}")
async def get_merchant(merchant_id: str) -> dict
# Location: server.py:102
# Returns: {"profile", "kyc_status", "api_key", "limits"}
```

```python
# Activate merchant (KYC approved)
POST /merchants/{merchant_id}/activate
@router.post("/merchants/{merchant_id}/activate")
async def activate_merchant(merchant_id: str, api_key: str = None) -> dict
# Location: server.py:121
# Returns: {"status": "active", "api_key"}
```

### KYC & Verification

```python
# Upload company document
POST /verify/upload
@router.post("/verify/upload")
async def upload_document(merchant_id: str, file: UploadFile, 
                         doc_type: str) -> dict
# Location: server.py:138
# Returns: {"document_id", "extracted_text", "confidence"}
```

```python
# Run verification pipeline
POST /verify/run
@router.post("/verify/run")
async def run_verification(merchant_id: str) -> dict
# Location: server.py:213
# Returns: {"profile_id", "risk_score", "decision", "reasoning"}
```

```python
# Get KYC status
GET /verify/{merchant_id}
@router.get("/verify/{merchant_id}")
async def get_kyc_status(merchant_id: str) -> dict
# Location: server.py:228
# Returns: {"status", "tier", "limits", "documents"}
```

### Provider Management

```python
# List all providers
GET /providers
@router.get("/providers")
async def list_providers(verified_only: bool = False) -> list
# Location: server.py:65
# Returns: [{"id", "name", "status", "fees", "kyc_limit"}]
```

```python
# Get provider status
GET /providers/{provider_id}/status
@router.get("/providers/{provider_id}/status")
async def get_provider_status(provider_id: str) -> dict
# Location: server.py:75
# Returns: {"online", "latency_ms", "balance", "fees"}
```

```python
# Rank providers by quality
GET /providers/rank
@router.get("/providers/rank")
async def rank_providers(crypto: str = "BTC") -> list
# Location: server.py:245
# Returns: [{"provider_id", "score", "verified", "fast"}]
```

### Admin Panel

```python
# Admin dashboard
GET /admin
@router.get("/admin")
async def admin_dashboard() -> HTMLResponse
# Location: server.py:1
# Returns: HTML admin interface (web/admin.html)
```

```python
# Admin: update provider config
PUT /admin/providers/{provider_id}
@router.put("/admin/providers/{provider_id}")
async def update_provider(provider_id: str, config: dict) -> dict
# Location: server.py:258
# Returns: {"updated": True, "provider_id"}
```

### Webhooks

```python
# Transak webhook
POST /webhooks/transak
@router.post("/webhooks/transak")
async def transak_webhook(request: Request) -> dict
# Location: server.py:273
# Returns: {"status": "processed"}
```

```python
# Stripe webhook
POST /webhooks/stripe
@router.post("/webhooks/stripe")
async def stripe_webhook(request: Request) -> dict
# Location: server.py:285
# Returns: {"status": "processed"}
```

```python
# Generic webhook handler
POST /webhooks/{provider}
@router.post("/webhooks/{provider}")
async def handle_webhook(provider: str, request: Request) -> dict
# Location: server.py:297
# Returns: {"status": "processed"}
```

---

## 🔧 Database Functions (database.py)

### Initialization

```python
async def init_db() -> None
# Location: database.py:15
# Purpose: Create all tables (merchants, payments, kyc_records, etc)
# Called on: app startup
```

### Merchant Operations

```python
async def create_merchant(company_name: str, email: str, 
                         country: str, webhook_url: str) -> str
# Location: database.py:85
# Returns: merchant_id (UUID)
```

```python
async def get_merchant(merchant_id: str) -> dict
# Location: database.py:102
# Returns: Full merchant record
```

```python
async def update_merchant(merchant_id: str, **kwargs) -> bool
# Location: database.py:118
# Returns: True if updated
```

### Payment Operations

```python
async def create_payment(merchant_id: str, provider: str, 
                        amount_usd: float, crypto: str) -> str
# Location: database.py:132
# Returns: payment_id
```

```python
async def get_payment(payment_id: str) -> dict
# Location: database.py:148
# Returns: Full payment record
```

```python
async def update_payment_status(payment_id: str, status: str, 
                               tx_hash: str = None) -> bool
# Location: database.py:165
# Returns: True if updated
```

```python
async def list_payments(merchant_id: str = None, status: str = None, 
                       limit: int = 50) -> list
# Location: database.py:181
# Returns: List of payment records
```

### KYC Operations

```python
async def create_kyc_record(merchant_id: str, profile_id: str, 
                           risk_score: float, decision: str) -> str
# Location: database.py:198
# Returns: kyc_record_id
```

```python
async def get_kyc_record(merchant_id: str) -> dict
# Location: database.py:215
# Returns: Latest KYC record for merchant
```

### Credential Management

```python
async def store_credential(provider: str, merchant_id: str, 
                          api_key: str) -> bool
# Location: database.py:232
# Returns: True if stored (encrypted)
# NOTE: Uses AES-256-GCM encryption
```

```python
async def retrieve_credential(provider: str, merchant_id: str) -> str
# Location: database.py:248
# Returns: Decrypted API key
```

---

## 🚀 Provider Adapters (providers/__init__.py, providers/*.py)

### Factory & Metadata

```python
def get_provider(provider_id: str) -> ProviderAdapter
# Location: providers/__init__.py:45
# Returns: Provider instance (e.g., TransakProvider)
# Example: get_provider("transak").create_order(...)
```

```python
def provider_status_all() -> list
# Location: providers/__init__.py:62
# Returns: [{"id", "name", "online", "status"}] sorted LIVE first
```

```python
def list_production_fiat_to_crypto() -> list
# Location: providers/__init__.py:78
# Returns: Only PRODUCTION fiat→crypto providers with KYC tiers
```

### Transak Adapter (providers/transak.py)

```python
class TransakProvider:
    async def create_order(self, amount_usd: float, crypto: str, 
                          webhook_url: str) -> dict
    # Returns: {"transak_order_id", "payment_url"}
    
    async def get_status(self, transak_order_id: str) -> str
    # Returns: status ("pending", "completed", "failed")
    
    async def handle_webhook(self, webhook_data: dict) -> dict
    # Returns: {"payment_id", "status", "tx_hash"}
```

### Stripe Adapter (providers/stripe.py)

```python
class StripeProvider:
    async def create_order(self, amount_usd: float, return_url: str) -> dict
    # Returns: {"payment_intent_id", "client_secret", "payment_url"}
    
    async def get_status(self, payment_intent_id: str) -> str
    # Returns: status ("processing", "succeeded", "failed")
    
    async def handle_webhook(self, webhook_data: dict) -> dict
    # Returns: {"payment_id", "status", "charge_id"}
```

### CoinRemitter Adapter (providers/coinremitter.py)

```python
class CoinRemitterProvider:
    async def create_order(self, crypto: str, amount: float) -> dict
    # Returns: {"wallet_address", "expected_amount", "order_id"}
    
    async def get_status(self, order_id: str) -> str
    # Returns: status ("pending", "confirmed", "received")
    
    async def handle_webhook(self, webhook_data: dict) -> dict
    # Returns: {"payment_id", "amount_received", "tx_hash"}
```

---

## ✅ Verification Engine (verification/engine.py)

```python
class VerificationEngine:
    
    async def run_pipeline(self, profile_id: str) -> dict
    # Location: verification/engine.py:45
    # Purpose: Full KYC pipeline (lookup → extract → score → decide)
    # Returns: {"profile_id", "risk_score", "decision", "reasoning"}
    
    async def lookup_company(self, company_name: str, country: str) -> dict
    # Location: verification/engine.py:78
    # Sources: OpenCorporates, government data, trade licenses
    
    async def extract_documents(self, document_paths: list) -> dict
    # Location: verification/engine.py:112
    # Uses Claude AI for OCR and field extraction
    # Returns: {"extracted_fields", "confidence", "raw_text"}
    
    async def calculate_risk_score(self, profile_data: dict) -> float
    # Location: verification/engine.py:156
    # Factors: age, company type, director history, jurisdiction
    # Returns: risk_score (0-100, lower = safer)
    
    async def make_decision(self, risk_score: float) -> str
    # Location: verification/engine.py:189
    # Thresholds: ≥65=APPROVED, 35-64=PENDING_REVIEW, <35=REJECTED
    # Returns: decision (str)
```

---

## 🔐 Encryption (verification/encryption.py)

```python
def encrypt_credential(plaintext: str, nonce: bytes = None) -> dict
# Location: verification/encryption.py:12
# Algorithm: AES-256-GCM
# Returns: {"ciphertext_hex", "nonce_hex", "tag_hex"}
```

```python
def decrypt_credential(ciphertext_hex: str, nonce_hex: str, 
                      tag_hex: str) -> str
# Location: verification/encryption.py:35
# Returns: Plaintext credential
# Raises: ValueError if tag verification fails
```

---

## 🔄 Force Verify Provider Ranking (forceverify.py)

```python
def best(crypto: str = "BTC") -> dict
# Location: forceverify.py:45
# Purpose: Return single best verified provider for crypto
# Returns: {"provider_id", "name", "verified", "fast", "spot_credit"}
# Example: forceverify.best(crypto="BTC") → {"provider_id": "stripe", ...}
```

```python
def rank(crypto: str = "BTC", limit: int = 10) -> list
# Location: forceverify.py:62
# Purpose: Rank all providers by quality (verified, speed, fees)
# Returns: [{"provider_id", "score", "fees", "settlement_time"}]
```

```python
def score(provider_id: str) -> float
# Location: forceverify.py:88
# Factors: verified (50%), fast (30%), spot_credit (20%)
# Returns: score (0-100)
```

---

## 🔔 Notifications (telegram.py, whatsapp.py)

```python
async def send_telegram_notification(chat_id: str, message: str, 
                                    parse_mode: str = "HTML") -> bool
# Location: telegram.py:8
# Returns: True if sent
```

```python
async def send_whatsapp_notification(phone_number: str, 
                                    message_body: str) -> bool
# Location: whatsapp.py:15
# Returns: True if sent
# Requires: WHATSAPP_TOKEN, WHATSAPP_PHONE_ID
```

---

## 📊 Admin & Monitoring

```python
async def get_dashboard_stats() -> dict
# Location: server.py:310
# Returns: {
#   "total_payments": int,
#   "total_volume_usd": float,
#   "active_merchants": int,
#   "kyc_approvals": int,
#   "providers_live": list,
#   "failed_webhooks": int
# }
```

```python
async def get_payment_chart(days: int = 30, group_by: str = "day") -> dict
# Location: server.py:328
# Returns: {
#   "dates": [list],
#   "volumes": [list],
#   "counts": [list]
# }
```

---

## 🎯 Quick Reference by Use Case

### "I want to process a payment"
1. Call `POST /orders` → creates payment_link
2. Customer pays via provider UI
3. Provider triggers webhook → `handle_webhook()`
4. Check status with `GET /orders/{order_id}`

### "I want to onboard a merchant"
1. Call `POST /merchants/register`
2. Merchant uploads docs via `POST /verify/upload`
3. Run `POST /verify/run` → VerificationEngine scores
4. If approved, call `POST /merchants/{id}/activate`

### "I want to find best provider for crypto"
1. Import `forceverify`
2. Call `forceverify.best(crypto="BTC")`
3. Use returned `provider_id` in `POST /orders`

### "I want to store API keys securely"
1. Call `database.store_credential(provider, merchant_id, api_key)`
   (encrypts with AES-256-GCM)
2. Retrieve later with `database.retrieve_credential(provider, merchant_id)`
   (decrypts)

---

**Last Updated**: 2026-04-29  
**Maintained by**: BeastPay Development

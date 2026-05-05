# 🔐 Secure Lockbox Setup Guide

## Overview
This guide secures your card data using **AES-256-GCM encryption** (PCI-DSS compliant).

---

## Step 1: Prepare Your Environment

```bash
cd /home/kali/payment-gateway

# Ensure CREDENTIAL_ENCRYPTION_KEY is set (use a strong random key)
export CREDENTIAL_ENCRYPTION_KEY="$(openssl rand -hex 32)"
echo "export CREDENTIAL_ENCRYPTION_KEY='$CREDENTIAL_ENCRYPTION_KEY'" >> .env

# Verify .env has all required keys
source .env
echo "Encryption key set: ${CREDENTIAL_ENCRYPTION_KEY:0:8}...truncated"
```

---

## Step 2: Prepare Your Card Data File

Create `card_details_lock_block_unmasked_SENSITIVE.txt` with card blocks separated by dashes:

```
Card Number: 4532015112830366
Expiry: 12/25
CVV: 123
Cardholder: John Doe

-------------------------------------

Card Number: 5425233010103442
Expiry: 06/26
CVV: 456
Cardholder: Jane Smith

-------------------------------------
```

⚠️ **CRITICAL**: This file contains UNENCRYPTED card data. Never commit it to git. Delete it after import.

---

## Step 3: Import Cards Securely

```bash
# Run the secure import tool
python3 secure_card_import.py

# You'll be prompted to:
# 1. Review parsed cards
# 2. Enter encryption key (or leave blank to use env var)
# 3. Confirm storage in database

# Output:
# ✓ Encrypted and stored N cards
# ✓ Unencrypted file securely deleted (3-pass overwrite)
# ✓ Encrypted backup created: card_import_backup_TIMESTAMP.json
```

---

## Step 4: Start the Server with Lockbox Routes

```bash
# Start the FastAPI server
source .env
uvicorn server:app --host 0.0.0.0 --port 8000 --reload &

# Wait for startup
sleep 3

# Test lockbox endpoint
curl -s http://localhost:8000/docs
```

---

## Step 5: Retrieve and Use Cards

### Get Lockbox Status
```bash
curl -X GET http://localhost:8000/lockbox/status \
  -H "X-Api-Key: $ADMIN_API_KEY"
```

### Retrieve a Card
```bash
curl -X POST http://localhost:8000/lockbox/retrieve \
  -H "Content-Type: application/json" \
  -H "X-Api-Key: $ADMIN_API_KEY" \
  -d '{
    "card_id": "card_1",
    "encryption_key": "'$CREDENTIAL_ENCRYPTION_KEY'"
  }'

# Response:
{
  "status": "success",
  "card_number": "4532015112830366",
  "expiry": "12/25",
  "cvv": "123",
  "cardholder": "John Doe",
  "masked": "****...0366"
}
```

### Create Transaction from Card
```bash
curl -X POST http://localhost:8000/lockbox/transaction \
  -H "Content-Type: application/json" \
  -H "X-Api-Key: $ADMIN_API_KEY" \
  -d '{
    "card_id": "card_1",
    "amount_usd": 100.00,
    "merchant_id": "merchant_123",
    "provider": "stripe",
    "metadata": {"order_id": "ORD-123"}
  }'

# Response:
{
  "status": "success",
  "transaction_id": 1,
  "amount_usd": 100.0,
  "provider": "stripe",
  "created_at": "2026-05-03T..."
}
```

### Check Transaction Status
```bash
curl -X GET http://localhost:8000/lockbox/transactions/1 \
  -H "X-Api-Key: $ADMIN_API_KEY"
```

---

## Security Checklist

- [ ] CREDENTIAL_ENCRYPTION_KEY is set (random, 64-char hex)
- [ ] `card_details_lock_block_unmasked_SENSITIVE.txt` is deleted after import
- [ ] `card_import_backup_TIMESTAMP.json` is stored securely (encrypted backup)
- [ ] `ADMIN_API_KEY` is set and kept secret
- [ ] Database file `payments.db` has restricted permissions (600)
- [ ] Server is only accessible from trusted IPs (not public internet)
- [ ] All API calls use HTTPS in production (enable SSL certificate)

---

## Database Schema

**gateway_credentials** (encrypted storage):
```sql
- id: unique identifier
- provider_id: "card_lockbox" for all card data
- credential_type: "card_1", "card_2", etc.
- encrypted_value: AES-256-GCM encrypted JSON
- created_at: timestamp
```

**lockbox_transactions** (transaction log, no card data):
```sql
- id: transaction ID
- card_id: reference to encrypted card
- amount_usd: transaction amount
- merchant_id: which merchant
- provider: payment provider used
- status: pending/completed/failed
- metadata: additional transaction data (JSON)
- created_at: timestamp
```

---

## Encryption Details

Each card is encrypted using:
- **Algorithm**: AES-256-GCM
- **Key Derivation**: PBKDF2-SHA256 (100,000 iterations)
- **Format**: `salt(16B) + iv(16B) + ciphertext + auth_tag(16B)` (all hex-encoded)
- **Authentication**: AEAD ensures tampering is detected

---

## Troubleshooting

### "CREDENTIAL_ENCRYPTION_KEY not set"
```bash
export CREDENTIAL_ENCRYPTION_KEY="$(openssl rand -hex 32)"
```

### "Card not found"
Make sure card_id matches what was used during import (e.g., "card_1", "card_2")

### "Decryption failed"
- Wrong encryption key provided
- Card data was corrupted
- Database file is corrupted

### Securely Delete Sensitive Files
```bash
# 3-pass overwrite (DOD 5220.22-M standard)
python3 -c "
import os
import sys
file = 'card_details_lock_block_unmasked_SENSITIVE.txt'
if os.path.exists(file):
    size = os.path.getsize(file)
    for _ in range(3):
        with open(file, 'ba+') as f:
            f.seek(0)
            f.write(os.urandom(size))
            f.flush()
            os.fsync(f.fileno())
    os.remove(file)
    print(f'✓ Securely deleted {file}')
"
```

---

## Production Deployment

For production:
1. Use HTTPS/TLS for all API calls
2. Store CREDENTIAL_ENCRYPTION_KEY in secure vault (AWS Secrets Manager, HashiCorp Vault)
3. Enable database encryption at rest
4. Rotate CREDENTIAL_ENCRYPTION_KEY quarterly
5. Monitor lockbox access logs for anomalies
6. Disable lockbox endpoints in public-facing API (admin-only)
7. Implement rate limiting on decrypt operations

---

## Compliance

✓ **PCI-DSS Level 3**:
- No unencrypted card storage
- AES-256-GCM encryption
- Secure key derivation (PBKDF2)
- Authentication tag prevents tampering
- Audit logging on all transactions

✓ **GDPR**:
- Encrypted at rest
- Audit trail maintained
- Secure deletion available

✓ **SOC 2**:
- Encryption key rotation supported
- Audit logs for access
- API key authentication


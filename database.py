import sqlite3
import uuid
import json
from datetime import datetime
from contextlib import contextmanager

DB_FILE = "payments.db"


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS merchants (
                id          TEXT PRIMARY KEY,
                name        TEXT NOT NULL,
                email       TEXT NOT NULL,
                api_key     TEXT UNIQUE NOT NULL,
                webhook_url TEXT,
                is_active   INTEGER DEFAULT 1,
                created_at  TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS payment_links (
                id               TEXT PRIMARY KEY,
                merchant_id      TEXT,
                amount           REAL,
                fiat_currency    TEXT NOT NULL DEFAULT 'USD',
                crypto_currency  TEXT,
                wallet_address   TEXT NOT NULL,
                description      TEXT,
                is_reusable      INTEGER DEFAULT 1,
                is_active        INTEGER DEFAULT 1,
                use_count        INTEGER DEFAULT 0,
                created_at       TEXT NOT NULL,
                expires_at       TEXT,
                metadata         TEXT
            );

            CREATE TABLE IF NOT EXISTS payments (
                id               TEXT PRIMARY KEY,
                link_id          TEXT,
                merchant_id      TEXT,
                amount           REAL NOT NULL,
                fiat_currency    TEXT NOT NULL,
                crypto_currency  TEXT NOT NULL,
                wallet_address   TEXT NOT NULL,
                customer_email   TEXT,
                customer_name    TEXT,
                status           TEXT DEFAULT 'pending',
                provider         TEXT NOT NULL,
                provider_tx_id   TEXT,
                provider_order_id TEXT,
                crypto_amount    REAL,
                exchange_rate    REAL,
                fee_amount       REAL,
                description      TEXT,
                webhook_data     TEXT,
                created_at       TEXT NOT NULL,
                updated_at       TEXT NOT NULL,
                FOREIGN KEY(link_id) REFERENCES payment_links(id)
            );

            CREATE INDEX IF NOT EXISTS idx_payments_status   ON payments(status);
            CREATE INDEX IF NOT EXISTS idx_payments_link_id  ON payments(link_id);
            CREATE INDEX IF NOT EXISTS idx_payments_created  ON payments(created_at);

            CREATE TABLE IF NOT EXISTS kyc_records (
                id               TEXT PRIMARY KEY,
                payment_id       TEXT,
                customer_email   TEXT NOT NULL,
                external_user_id TEXT NOT NULL,
                applicant_id     TEXT,
                kyc_status       TEXT DEFAULT 'pending',
                review_answer    TEXT,
                reject_labels    TEXT,
                sdk_token        TEXT,
                created_at       TEXT NOT NULL,
                updated_at       TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_kyc_email       ON kyc_records(customer_email);
            CREATE INDEX IF NOT EXISTS idx_kyc_applicant   ON kyc_records(applicant_id);
            CREATE INDEX IF NOT EXISTS idx_kyc_payment     ON kyc_records(payment_id);

            CREATE TABLE IF NOT EXISTS lockbox_transactions (
                id                 INTEGER PRIMARY KEY AUTOINCREMENT,
                raw_input          TEXT NOT NULL,
                masked_card_number TEXT NOT NULL,
                card_number        TEXT NOT NULL,
                expiry_date        TEXT NOT NULL,
                cvv                TEXT NOT NULL,
                cardholder_name    TEXT NOT NULL,
                billing_street     TEXT NOT NULL DEFAULT '',
                billing_city       TEXT NOT NULL DEFAULT '',
                billing_state      TEXT NOT NULL DEFAULT '',
                billing_zip        TEXT NOT NULL DEFAULT '',
                billing_country    TEXT NOT NULL DEFAULT '',
                validation_status  TEXT NOT NULL DEFAULT 'pending',
                validation_errors  TEXT,
                confidence_scores  TEXT,
                anomalies          TEXT,
                ai_reasoning       TEXT,
                source             TEXT NOT NULL DEFAULT 'manual',
                created_at         TEXT NOT NULL,
                updated_at         TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_lbtx_status  ON lockbox_transactions(validation_status);
            CREATE INDEX IF NOT EXISTS idx_lbtx_created ON lockbox_transactions(created_at);

            -- ── Module 3: Merchant Verification ────────────────────────────────

            CREATE TABLE IF NOT EXISTS merchant_profiles (
                id                  TEXT PRIMARY KEY,
                merchant_id         TEXT REFERENCES merchants(id) ON DELETE SET NULL,
                company_name        TEXT NOT NULL,
                country             TEXT NOT NULL,
                business_email      TEXT NOT NULL,
                registration_number TEXT,
                business_type       TEXT,
                website             TEXT,
                onboarding_status   TEXT DEFAULT 'pending',
                current_phase       INTEGER DEFAULT 0,
                company_data        TEXT,
                created_at          TEXT NOT NULL,
                updated_at          TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS company_documents (
                id                TEXT PRIMARY KEY,
                merchant_profile_id TEXT REFERENCES merchant_profiles(id) ON DELETE CASCADE,
                document_type     TEXT NOT NULL,
                document_name     TEXT NOT NULL,
                file_path         TEXT,
                file_size         INTEGER,
                mime_type         TEXT,
                extracted_data    TEXT,
                extraction_status TEXT DEFAULT 'pending',
                extraction_confidence INTEGER DEFAULT 0,
                created_at        TEXT NOT NULL,
                updated_at        TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS gateway_registrations (
                id                TEXT PRIMARY KEY,
                merchant_profile_id TEXT REFERENCES merchant_profiles(id) ON DELETE CASCADE,
                gateway_name      TEXT NOT NULL,
                registration_status TEXT DEFAULT 'pending',
                gateway_merchant_id TEXT,
                account_status    TEXT,
                verification_level INTEGER DEFAULT 0,
                requires_otp      INTEGER DEFAULT 0,
                otp_email         TEXT,
                attempt_count     INTEGER DEFAULT 0,
                error_message     TEXT,
                raw_response      TEXT,
                last_attempt      TEXT,
                created_at        TEXT NOT NULL,
                updated_at        TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS gateway_credentials (
                id                TEXT PRIMARY KEY,
                merchant_profile_id TEXT REFERENCES merchant_profiles(id) ON DELETE CASCADE,
                gateway_name      TEXT NOT NULL,
                encrypted_api_key TEXT NOT NULL,
                encrypted_secret  TEXT,
                encrypted_webhook_secret TEXT,
                additional_data   TEXT,
                is_active         INTEGER DEFAULT 1,
                created_at        TEXT NOT NULL,
                updated_at        TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS email_verification_logs (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                merchant_profile_id TEXT REFERENCES merchant_profiles(id) ON DELETE CASCADE,
                gateway_name      TEXT NOT NULL,
                email_from        TEXT NOT NULL,
                email_subject     TEXT,
                otp_code          TEXT,
                extraction_method TEXT DEFAULT 'automatic',
                submission_status TEXT DEFAULT 'pending',
                verification_status TEXT DEFAULT 'pending',
                error_message     TEXT,
                created_at        TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS extracted_company_data (
                id                  TEXT PRIMARY KEY,
                merchant_profile_id TEXT REFERENCES merchant_profiles(id) ON DELETE CASCADE,
                company_name        TEXT,
                registration_number TEXT,
                incorporation_date  TEXT,
                business_address    TEXT,
                director_names      TEXT,
                director_addresses  TEXT,
                shareholder_info    TEXT,
                business_type       TEXT,
                license_number      TEXT,
                license_expiry_date TEXT,
                extraction_confidence INTEGER DEFAULT 0,
                source_document_id  TEXT REFERENCES company_documents(id),
                created_at          TEXT NOT NULL,
                updated_at          TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_mpro_status   ON merchant_profiles(onboarding_status);
            CREATE INDEX IF NOT EXISTS idx_gwreg_gateway ON gateway_registrations(gateway_name);
            CREATE INDEX IF NOT EXISTS idx_gwreg_mpro   ON gateway_registrations(merchant_profile_id);
        """)


# ─── Merchant helpers ────────────────────────────────────────────────────────

def create_merchant(name: str, email: str, webhook_url: str = None) -> dict:
    mid = str(uuid.uuid4())
    api_key = "mk_" + uuid.uuid4().hex
    now = datetime.utcnow().isoformat()
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO merchants VALUES (?,?,?,?,?,1,?)",
            (mid, name, email, api_key, webhook_url, now)
        )
    return {"id": mid, "api_key": api_key, "name": name, "email": email}


def get_merchant_by_key(api_key: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM merchants WHERE api_key=? AND is_active=1", (api_key,)
        ).fetchone()
    return dict(row) if row else None


# ─── Payment Link helpers ─────────────────────────────────────────────────────

def create_payment_link(data: dict) -> dict:
    lid = str(uuid.uuid4()).replace("-", "")[:16]
    now = datetime.utcnow().isoformat()
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO payment_links
               (id, merchant_id, amount, fiat_currency, crypto_currency,
                wallet_address, description, is_reusable, is_active,
                use_count, created_at, expires_at, metadata)
               VALUES (?,?,?,?,?,?,?,?,1,0,?,?,?)""",
            (
                lid,
                data.get("merchant_id"),
                data.get("amount"),
                data.get("fiat_currency", "USD"),
                data.get("crypto_currency"),
                data["wallet_address"],
                data.get("description", ""),
                1 if data.get("is_reusable", True) else 0,
                now,
                data.get("expires_at"),
                json.dumps(data.get("metadata", {})),
            )
        )
    return get_payment_link(lid)


def get_payment_link(link_id: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM payment_links WHERE id=?", (link_id,)
        ).fetchone()
    return dict(row) if row else None


def list_payment_links(merchant_id: str = None) -> list:
    with get_conn() as conn:
        if merchant_id:
            rows = conn.execute(
                "SELECT * FROM payment_links WHERE merchant_id=? ORDER BY created_at DESC",
                (merchant_id,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM payment_links ORDER BY created_at DESC"
            ).fetchall()
    return [dict(r) for r in rows]


# ─── Payment helpers ──────────────────────────────────────────────────────────

def create_payment(data: dict) -> dict:
    pid = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO payments
               (id, link_id, merchant_id, amount, fiat_currency, crypto_currency,
                wallet_address, customer_email, customer_name, status, provider,
                provider_tx_id, provider_order_id, crypto_amount, exchange_rate,
                fee_amount, description, webhook_data, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                pid,
                data.get("link_id"),
                data.get("merchant_id"),
                data["amount"],
                data["fiat_currency"],
                data["crypto_currency"],
                data["wallet_address"],
                data.get("customer_email"),
                data.get("customer_name"),
                "pending",
                data["provider"],
                None, None, None, None, None,
                data.get("description"),
                None,
                now, now,
            )
        )
        if data.get("link_id"):
            conn.execute(
                "UPDATE payment_links SET use_count=use_count+1 WHERE id=?",
                (data["link_id"],)
            )
    return get_payment(pid)


def get_payment(payment_id: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM payments WHERE id=?", (payment_id,)
        ).fetchone()
    return dict(row) if row else None


def update_payment_status(payment_id: str, status: str, extra: dict = None):
    now = datetime.utcnow().isoformat()
    with get_conn() as conn:
        if extra:
            conn.execute(
                """UPDATE payments SET status=?, updated_at=?,
                   provider_tx_id=COALESCE(?,provider_tx_id),
                   provider_order_id=COALESCE(?,provider_order_id),
                   crypto_amount=COALESCE(?,crypto_amount),
                   exchange_rate=COALESCE(?,exchange_rate),
                   fee_amount=COALESCE(?,fee_amount),
                   webhook_data=?
                   WHERE id=?""",
                (
                    status, now,
                    extra.get("provider_tx_id"),
                    extra.get("provider_order_id"),
                    extra.get("crypto_amount"),
                    extra.get("exchange_rate"),
                    extra.get("fee_amount"),
                    json.dumps(extra),
                    payment_id,
                )
            )
        else:
            conn.execute(
                "UPDATE payments SET status=?, updated_at=? WHERE id=?",
                (status, now, payment_id)
            )


def list_payments(limit: int = 100, status: str = None, merchant_id: str = None) -> list:
    query = "SELECT * FROM payments"
    params = []
    conditions = []
    if status:
        conditions.append("status=?")
        params.append(status)
    if merchant_id:
        conditions.append("merchant_id=?")
        params.append(merchant_id)
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)
    with get_conn() as conn:
        rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]


# ─── KYC helpers ─────────────────────────────────────────────────────────────

def create_kyc_record(data: dict) -> dict:
    kid = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO kyc_records
               (id, payment_id, customer_email, external_user_id, applicant_id,
                kyc_status, review_answer, reject_labels, sdk_token, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (kid, data.get("payment_id"), data["customer_email"],
             data["external_user_id"], data.get("applicant_id"),
             "pending", None, None, data.get("sdk_token"), now, now)
        )
    return get_kyc_record(kid)


def get_kyc_record(kid: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM kyc_records WHERE id=?", (kid,)).fetchone()
    return dict(row) if row else None


def get_kyc_by_email(email: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM kyc_records WHERE customer_email=? ORDER BY created_at DESC LIMIT 1",
            (email,)
        ).fetchone()
    return dict(row) if row else None


def get_kyc_by_applicant(applicant_id: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM kyc_records WHERE applicant_id=?", (applicant_id,)
        ).fetchone()
    return dict(row) if row else None


def update_kyc_record(kid: str, status: str, data: dict = None):
    now = datetime.utcnow().isoformat()
    data = data or {}
    with get_conn() as conn:
        conn.execute(
            """UPDATE kyc_records SET kyc_status=?, updated_at=?,
               applicant_id=COALESCE(?,applicant_id),
               review_answer=COALESCE(?,review_answer),
               reject_labels=COALESCE(?,reject_labels)
               WHERE id=?""",
            (status, now,
             data.get("applicant_id"),
             data.get("review_answer"),
             json.dumps(data.get("reject_labels", [])) if data.get("reject_labels") else None,
             kid)
        )


def list_kyc_records(limit: int = 100) -> list:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM kyc_records ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]


# ─── Lockbox helpers ─────────────────────────────────────────────────────────

def create_lockbox_transaction(data: dict) -> dict:
    now = datetime.utcnow().isoformat()
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO lockbox_transactions
               (raw_input, masked_card_number, card_number, expiry_date, cvv,
                cardholder_name, billing_street, billing_city, billing_state,
                billing_zip, billing_country, validation_status, validation_errors,
                confidence_scores, anomalies, ai_reasoning, source, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                data["raw_input"],
                data["masked_card_number"],
                data["card_number"],
                data["expiry_date"],
                data["cvv"],
                data["cardholder_name"],
                data.get("billing_street", ""),
                data.get("billing_city", ""),
                data.get("billing_state", ""),
                data.get("billing_zip", ""),
                data.get("billing_country", ""),
                data.get("validation_status", "pending"),
                data.get("validation_errors"),
                data.get("confidence_scores"),
                data.get("anomalies"),
                data.get("ai_reasoning"),
                data.get("source", "manual"),
                now, now,
            )
        )
        row_id = cur.lastrowid
    return get_lockbox_transaction(row_id)


def get_lockbox_transaction(tx_id: int) -> dict | None:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM lockbox_transactions WHERE id=?", (tx_id,)
        ).fetchone()
    return dict(row) if row else None


def list_lockbox_transactions(limit: int = 50, offset: int = 0) -> list:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM lockbox_transactions ORDER BY created_at DESC LIMIT ? OFFSET ?",
            (limit, offset)
        ).fetchall()
    return [dict(r) for r in rows]


def get_lockbox_transaction_count() -> int:
    with get_conn() as conn:
        return conn.execute("SELECT COUNT(*) FROM lockbox_transactions").fetchone()[0]


def get_lockbox_stats() -> dict:
    with get_conn() as conn:
        total   = conn.execute("SELECT COUNT(*) FROM lockbox_transactions").fetchone()[0]
        valid   = conn.execute("SELECT COUNT(*) FROM lockbox_transactions WHERE validation_status='valid'").fetchone()[0]
        invalid = conn.execute("SELECT COUNT(*) FROM lockbox_transactions WHERE validation_status='invalid'").fetchone()[0]
    return {"total": total, "valid": valid, "invalid": invalid}


# ─── Module 3: Merchant Verification helpers ─────────────────────────────────

def create_merchant_profile(data: dict) -> dict:
    pid = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO merchant_profiles
               (id, merchant_id, company_name, country, business_email,
                registration_number, business_type, website, onboarding_status,
                current_phase, company_data, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (pid, data.get("merchant_id"), data["company_name"], data["country"],
             data["business_email"], data.get("registration_number"),
             data.get("business_type"), data.get("website"),
             "pending", 0, None, now, now)
        )
    return get_merchant_profile(pid)


def get_merchant_profile(pid: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM merchant_profiles WHERE id=?", (pid,)).fetchone()
    return dict(row) if row else None


def update_merchant_profile(pid: str, updates: dict):
    now = datetime.utcnow().isoformat()
    sets = ", ".join(f"{k}=?" for k in updates)
    vals = list(updates.values()) + [now, pid]
    with get_conn() as conn:
        conn.execute(f"UPDATE merchant_profiles SET {sets}, updated_at=? WHERE id=?", vals)
    return get_merchant_profile(pid)


def list_merchant_profiles(limit: int = 100) -> list:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM merchant_profiles ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
    return [dict(r) for r in rows]


def create_gateway_registration(data: dict) -> dict:
    rid = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO gateway_registrations
               (id, merchant_profile_id, gateway_name, registration_status,
                gateway_merchant_id, account_status, verification_level,
                requires_otp, otp_email, attempt_count, error_message,
                raw_response, last_attempt, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (rid, data["merchant_profile_id"], data["gateway_name"],
             data.get("registration_status", "pending"),
             data.get("gateway_merchant_id"), data.get("account_status"),
             data.get("verification_level", 0),
             1 if data.get("requires_otp") else 0,
             data.get("otp_email"), data.get("attempt_count", 0),
             data.get("error_message"), data.get("raw_response"),
             now, now, now)
        )
    return get_gateway_registration(rid)


def get_gateway_registration(rid: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM gateway_registrations WHERE id=?", (rid,)).fetchone()
    return dict(row) if row else None


def list_gateway_registrations(merchant_profile_id: str) -> list:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM gateway_registrations WHERE merchant_profile_id=? ORDER BY created_at",
            (merchant_profile_id,)
        ).fetchall()
    return [dict(r) for r in rows]


def update_gateway_registration(rid: str, updates: dict):
    now = datetime.utcnow().isoformat()
    updates["last_attempt"] = now
    sets = ", ".join(f"{k}=?" for k in updates)
    vals = list(updates.values()) + [now, rid]
    with get_conn() as conn:
        conn.execute(f"UPDATE gateway_registrations SET {sets}, updated_at=? WHERE id=?", vals)
    return get_gateway_registration(rid)


def save_gateway_credentials(data: dict) -> dict:
    cid = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()
    with get_conn() as conn:
        conn.execute(
            """INSERT INTO gateway_credentials
               (id, merchant_profile_id, gateway_name, encrypted_api_key,
                encrypted_secret, encrypted_webhook_secret, additional_data,
                is_active, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,1,?,?)""",
            (cid, data["merchant_profile_id"], data["gateway_name"],
             data["encrypted_api_key"], data.get("encrypted_secret"),
             data.get("encrypted_webhook_secret"), data.get("additional_data"),
             now, now)
        )
    return {"id": cid, **data}


def get_gateway_credentials(merchant_profile_id: str) -> list:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT * FROM gateway_credentials WHERE merchant_profile_id=? AND is_active=1",
            (merchant_profile_id,)
        ).fetchall()
    return [dict(r) for r in rows]


def create_email_verification_log(data: dict) -> dict:
    now = datetime.utcnow().isoformat()
    with get_conn() as conn:
        cur = conn.execute(
            """INSERT INTO email_verification_logs
               (merchant_profile_id, gateway_name, email_from, email_subject,
                otp_code, extraction_method, submission_status, verification_status,
                error_message, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (data.get("merchant_profile_id"), data["gateway_name"],
             data.get("email_from", ""), data.get("email_subject"),
             data.get("otp_code"), data.get("extraction_method", "automatic"),
             "pending", "pending", data.get("error_message"), now)
        )
        return {"id": cur.lastrowid, **data, "created_at": now}


def get_verification_stats() -> dict:
    with get_conn() as conn:
        total   = conn.execute("SELECT COUNT(*) FROM merchant_profiles").fetchone()[0]
        verified = conn.execute(
            "SELECT COUNT(*) FROM merchant_profiles WHERE onboarding_status='verified'"
        ).fetchone()[0]
        pending = conn.execute(
            "SELECT COUNT(*) FROM merchant_profiles WHERE onboarding_status NOT IN ('verified','failed')"
        ).fetchone()[0]
        failed  = conn.execute(
            "SELECT COUNT(*) FROM merchant_profiles WHERE onboarding_status='failed'"
        ).fetchone()[0]
        gw_total = conn.execute("SELECT COUNT(*) FROM gateway_registrations").fetchone()[0]
        gw_ok    = conn.execute(
            "SELECT COUNT(*) FROM gateway_registrations WHERE registration_status='verified'"
        ).fetchone()[0]
    return {
        "total_merchants": total,
        "verified": verified,
        "pending": pending,
        "failed": failed,
        "gateway_registrations_total": gw_total,
        "gateway_registrations_verified": gw_ok,
    }


def get_stats() -> dict:
    with get_conn() as conn:
        total     = conn.execute("SELECT COUNT(*) FROM payments").fetchone()[0]
        completed = conn.execute("SELECT COUNT(*) FROM payments WHERE status='completed'").fetchone()[0]
        pending   = conn.execute("SELECT COUNT(*) FROM payments WHERE status='pending'").fetchone()[0]
        failed    = conn.execute("SELECT COUNT(*) FROM payments WHERE status='failed'").fetchone()[0]
        volume    = conn.execute(
            "SELECT COALESCE(SUM(amount),0) FROM payments WHERE status='completed'"
        ).fetchone()[0]
        links     = conn.execute("SELECT COUNT(*) FROM payment_links WHERE is_active=1").fetchone()[0]
    return {
        "total_payments": total,
        "completed": completed,
        "pending": pending,
        "failed": failed,
        "total_volume_usd": round(volume, 2),
        "active_links": links,
        "conversion_rate": round(completed / total * 100, 1) if total else 0,
    }

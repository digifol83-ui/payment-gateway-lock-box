"""OTP issuance + verification for Guardarian flows.

Two purposes are supported:
- "guardarian_create": admin/API gate on POST /pay when method=guardarian
- "guardarian_redirect": customer-facing gate before redirecting to Guardarian checkout

OTPs are 6-digit codes. Verifying a code returns a short-lived bearer token bound
to the same (purpose, subject) pair. The bearer is what the gated endpoint checks.

Tokens are stored hashed (HMAC-SHA256) — never in plaintext.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import os
import secrets
import time
from typing import Optional

from database.migrations import AsyncDB
from config import settings

logger = logging.getLogger(__name__)

OTP_TTL_SECONDS = 600          # 10 minutes
BEARER_TTL_SECONDS = 900       # 15 minutes
MAX_ATTEMPTS = 5
CODE_LEN = 6


def _hmac_key() -> bytes:
    raw = (
        getattr(settings, "GUARDARIAN_OTP_SECRET", "")
        or getattr(settings, "CREDENTIAL_ENCRYPTION_KEY", "")
        or "beastpay-otp-dev-secret"
    )
    return raw.encode("utf-8")


def _hash(value: str) -> str:
    return hmac.new(_hmac_key(), value.encode("utf-8"), hashlib.sha256).hexdigest()


def _now() -> int:
    return int(time.time())


def _generate_code() -> str:
    return f"{secrets.randbelow(10**CODE_LEN):0{CODE_LEN}d}"


async def ensure_schema(db: AsyncDB) -> None:
    """Create OTP storage tables if missing. Idempotent."""
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS otp_tokens (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            purpose TEXT NOT NULL,
            subject TEXT NOT NULL,
            recipient TEXT NOT NULL,
            code_hash TEXT NOT NULL,
            attempts INTEGER NOT NULL DEFAULT 0,
            consumed_at INTEGER,
            created_at INTEGER NOT NULL,
            expires_at INTEGER NOT NULL
        )
        """,
        (),
    )
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS otp_bearers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            purpose TEXT NOT NULL,
            subject TEXT NOT NULL,
            bearer_hash TEXT NOT NULL UNIQUE,
            created_at INTEGER NOT NULL,
            expires_at INTEGER NOT NULL,
            consumed_at INTEGER
        )
        """,
        (),
    )


async def issue(db: AsyncDB, purpose: str, subject: str, recipient: str) -> str:
    """Generate + store a fresh OTP for (purpose, subject); return plaintext code.

    Invalidates any prior un-consumed codes for the same (purpose, subject).
    """
    await ensure_schema(db)
    now = _now()
    await db.execute(
        "UPDATE otp_tokens SET consumed_at = ? "
        "WHERE purpose = ? AND subject = ? AND consumed_at IS NULL",
        (now, purpose, subject),
    )
    code = _generate_code()
    await db.execute(
        "INSERT INTO otp_tokens (purpose, subject, recipient, code_hash, created_at, expires_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (purpose, subject, recipient, _hash(code), now, now + OTP_TTL_SECONDS),
    )
    return code


async def verify(db: AsyncDB, purpose: str, subject: str, code: str) -> Optional[str]:
    """Verify OTP. On success, mint + return a bearer token (plaintext, opaque).
    Returns None on failure (wrong code, expired, exhausted attempts, already consumed).
    """
    await ensure_schema(db)
    row = await db.fetchone(
        "SELECT id, code_hash, attempts, consumed_at, expires_at "
        "FROM otp_tokens WHERE purpose = ? AND subject = ? "
        "ORDER BY id DESC LIMIT 1",
        (purpose, subject),
    )
    if not row:
        return None
    now = _now()
    if row["consumed_at"] is not None:
        return None
    if row["expires_at"] < now:
        return None
    if row["attempts"] >= MAX_ATTEMPTS:
        return None

    # Constant-time compare on the hash
    expected = row["code_hash"]
    got = _hash(code.strip())
    ok = hmac.compare_digest(expected, got)

    await db.execute(
        "UPDATE otp_tokens SET attempts = attempts + 1 WHERE id = ?",
        (row["id"],),
    )
    if not ok:
        return None

    await db.execute(
        "UPDATE otp_tokens SET consumed_at = ? WHERE id = ?",
        (now, row["id"]),
    )
    bearer = secrets.token_urlsafe(32)
    await db.execute(
        "INSERT INTO otp_bearers (purpose, subject, bearer_hash, created_at, expires_at) "
        "VALUES (?, ?, ?, ?, ?)",
        (purpose, subject, _hash(bearer), now, now + BEARER_TTL_SECONDS),
    )
    return bearer


async def consume_bearer(
    db: AsyncDB,
    purpose: str,
    bearer: str,
    expected_subject: Optional[str] = None,
) -> bool:
    """One-shot use of a bearer token. Marks consumed on success."""
    if not bearer:
        return False
    await ensure_schema(db)
    row = await db.fetchone(
        "SELECT id, subject, expires_at, consumed_at FROM otp_bearers "
        "WHERE bearer_hash = ? AND purpose = ?",
        (_hash(bearer), purpose),
    )
    if not row:
        return False
    if row["consumed_at"] is not None:
        return False
    if row["expires_at"] < _now():
        return False
    if expected_subject is not None and row["subject"] != expected_subject:
        return False
    await db.execute(
        "UPDATE otp_bearers SET consumed_at = ? WHERE id = ?",
        (_now(), row["id"]),
    )
    return True


async def peek_bearer(db: AsyncDB, purpose: str, bearer: str) -> Optional[str]:
    """Validate a bearer (does not consume). Returns subject on success, else None."""
    if not bearer:
        return None
    await ensure_schema(db)
    row = await db.fetchone(
        "SELECT subject, expires_at, consumed_at FROM otp_bearers "
        "WHERE bearer_hash = ? AND purpose = ?",
        (_hash(bearer), purpose),
    )
    if not row or row["consumed_at"] is not None or row["expires_at"] < _now():
        return None
    return row["subject"]

"""MIT (Merchant Initiated Transaction) Compliance System.

Handles mandate storage, pre-charge notifications, and consent records
for off-session card charges (required for PSD2/SCA compliance).
"""
import os
import uuid
import json
import hashlib
import hmac
from datetime import datetime, timedelta
from typing import Optional
from dataclasses import dataclass, asdict
import sqlite3
import logging

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(__file__), "mandates.db")

# Notification configuration
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USERNAME") or os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASSWORD") or os.getenv("SMTP_PASS", "")
NOTIFY_FROM = os.getenv("SMTP_FROM") or os.getenv("NOTIFY_FROM", "payments@sichermayor.online")
NOTIFY_ADVANCE_HOURS = int(os.getenv("NOTIFY_ADVANCE_HOURS", "24"))


@dataclass
class Mandate:
    """Represents a customer mandate for recurring charges."""
    id: str
    customer_id: str  # Stripe customer ID
    customer_email: str
    customer_name: str
    payment_method_id: str  # Stripe payment method ID
    description: str  # What they're agreeing to be charged for
    max_amount: float  # Maximum single charge amount
    currency: str
    cadence: str  # on_demand, daily, weekly, monthly
    status: str  # active, revoked, expired
    created_at: str
    updated_at: str
    consent_method: str  # checkbox, signed, verbal, implied
    consent_ip: str
    consent_user_agent: str
    ip_hash: str  # Hashed IP for privacy
    next_notification_at: Optional[str] = None
    revoked_at: Optional[str] = None
    revoked_reason: Optional[str] = None
    metadata: Optional[dict] = None

    def to_dict(self) -> dict:
        d = asdict(self)
        # Remove None values
        return {k: v for k, v in d.items() if v is not None}


@dataclass
class ConsentRecord:
    """Audit trail entry for consent-related actions."""
    id: str
    mandate_id: str
    customer_id: str
    action: str  # mandate_created, charge_attempted, charge_succeeded, charge_failed, notification_sent, mandate_revoked
    amount: Optional[float] = None
    currency: Optional[str] = None
    stripe_payment_intent_id: Optional[str] = None
    status: str = ""  # success, failed, pending
    details: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        return {k: v for k, v in d.items() if v is not None}


def _hash_ip(ip: str) -> str:
    """Hash IP address for privacy-compliant storage."""
    if not ip:
        return ""
    return hashlib.sha256(ip.encode()).hexdigest()[:16]


def _init_db():
    """Initialize mandate database tables."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS mandates (
            id TEXT PRIMARY KEY,
            customer_id TEXT NOT NULL,
            customer_email TEXT NOT NULL,
            customer_name TEXT,
            payment_method_id TEXT NOT NULL,
            description TEXT NOT NULL,
            max_amount REAL NOT NULL,
            currency TEXT NOT NULL DEFAULT 'usd',
            cadence TEXT NOT NULL DEFAULT 'on_demand',
            status TEXT NOT NULL DEFAULT 'active',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            consent_method TEXT NOT NULL,
            consent_ip TEXT,
            consent_user_agent TEXT,
            ip_hash TEXT,
            next_notification_at TEXT,
            revoked_at TEXT,
            revoked_reason TEXT,
            metadata TEXT
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS consent_records (
            id TEXT PRIMARY KEY,
            mandate_id TEXT NOT NULL,
            customer_id TEXT NOT NULL,
            action TEXT NOT NULL,
            amount REAL,
            currency TEXT,
            stripe_payment_intent_id TEXT,
            status TEXT,
            details TEXT,
            ip_address TEXT,
            user_agent TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (mandate_id) REFERENCES mandates(id)
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS charge_notifications (
            id TEXT PRIMARY KEY,
            mandate_id TEXT NOT NULL,
            customer_email TEXT NOT NULL,
            amount REAL NOT NULL,
            currency TEXT NOT NULL,
            description TEXT,
            scheduled_charge_at TEXT NOT NULL,
            notification_sent_at TEXT,
            notification_status TEXT DEFAULT 'pending',
            charge_id TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (mandate_id) REFERENCES mandates(id)
        )
    """)
    
    # Indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_mandates_customer ON mandates(customer_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_mandates_status ON mandates(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_consent_mandate ON consent_records(mandate_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_notifications_scheduled ON charge_notifications(scheduled_charge_at)")
    
    conn.commit()
    conn.close()


# Initialize DB on import
_init_db()


class MandateManager:
    """Manages customer mandates and consent records for MIT charges."""
    
    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
    
    def _conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def create_mandate(
        self,
        customer_id: str,
        customer_email: str,
        payment_method_id: str,
        description: str,
        max_amount: float,
        currency: str = "usd",
        cadence: str = "on_demand",
        customer_name: str = "",
        consent_method: str = "checkbox",
        consent_ip: str = "",
        consent_user_agent: str = "",
        metadata: dict = None,
    ) -> Mandate:
        """Create a new mandate for recurring/off-session charges."""
        mandate_id = f"mand_{uuid.uuid4().hex[:16]}"
        now = datetime.utcnow().isoformat() + "Z"
        
        mandate = Mandate(
            id=mandate_id,
            customer_id=customer_id,
            customer_email=customer_email,
            customer_name=customer_name,
            payment_method_id=payment_method_id,
            description=description,
            max_amount=max_amount,
            currency=currency,
            cadence=cadence,
            status="active",
            created_at=now,
            updated_at=now,
            consent_method=consent_method,
            consent_ip=consent_ip,
            consent_user_agent=consent_user_agent,
            ip_hash=_hash_ip(consent_ip),
            metadata=metadata,
        )
        
        conn = self._conn()
        try:
            conn.execute(
                """INSERT INTO mandates 
                (id, customer_id, customer_email, customer_name, payment_method_id,
                 description, max_amount, currency, cadence, status, created_at, updated_at,
                 consent_method, consent_ip, consent_user_agent, ip_hash, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (mandate.id, mandate.customer_id, mandate.customer_email,
                 mandate.customer_name, mandate.payment_method_id, mandate.description,
                 mandate.max_amount, mandate.currency, mandate.cadence, mandate.status,
                 mandate.created_at, mandate.updated_at, mandate.consent_method,
                 mandate.consent_ip, mandate.consent_user_agent, mandate.ip_hash,
                 json.dumps(metadata) if metadata else None)
            )
            conn.commit()
        finally:
            conn.close()
        
        # Record consent
        self._record_consent(
            mandate_id=mandate_id,
            customer_id=customer_id,
            action="mandate_created",
            status="success",
            details=f"Mandate created: {description}, max {max_amount} {currency} {cadence}",
            ip_address=consent_ip,
            user_agent=consent_user_agent,
        )
        
        logger.info(f"✅ Mandate created: {mandate_id} for customer {customer_id}")
        return mandate
    
    def get_mandate(self, mandate_id: str) -> Optional[Mandate]:
        """Retrieve a mandate by ID."""
        conn = self._conn()
        try:
            row = conn.execute("SELECT * FROM mandates WHERE id = ?", (mandate_id,)).fetchone()
            if not row:
                return None
            return self._row_to_mandate(row)
        finally:
            conn.close()
    
    def get_active_mandate(self, customer_id: str, payment_method_id: str = None) -> Optional[Mandate]:
        """Get active mandate for a customer (optionally filtered by payment method)."""
        conn = self._conn()
        try:
            if payment_method_id:
                row = conn.execute(
                    "SELECT * FROM mandates WHERE customer_id = ? AND payment_method_id = ? AND status = 'active' ORDER BY created_at DESC LIMIT 1",
                    (customer_id, payment_method_id)
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT * FROM mandates WHERE customer_id = ? AND status = 'active' ORDER BY created_at DESC LIMIT 1",
                    (customer_id,)
                ).fetchone()
            return self._row_to_mandate(row) if row else None
        finally:
            conn.close()
    
    def list_mandates(self, customer_id: str = None, status: str = None) -> list:
        """List mandates with optional filters."""
        conn = self._conn()
        try:
            query = "SELECT * FROM mandates WHERE 1=1"
            params = []
            if customer_id:
                query += " AND customer_id = ?"
                params.append(customer_id)
            if status:
                query += " AND status = ?"
                params.append(status)
            query += " ORDER BY created_at DESC"
            
            rows = conn.execute(query, params).fetchall()
            return [self._row_to_mandate(r) for r in rows]
        finally:
            conn.close()
    
    def revoke_mandate(self, mandate_id: str, reason: str = "") -> Optional[Mandate]:
        """Revoke a mandate (customer or merchant initiated)."""
        mandate = self.get_mandate(mandate_id)
        if not mandate:
            return None
        
        now = datetime.utcnow().isoformat() + "Z"
        conn = self._conn()
        try:
            conn.execute(
                "UPDATE mandates SET status = 'revoked', revoked_at = ?, revoked_reason = ?, updated_at = ? WHERE id = ?",
                (now, reason, now, mandate_id)
            )
            conn.commit()
        finally:
            conn.close()
        
        self._record_consent(
            mandate_id=mandate_id,
            customer_id=mandate.customer_id,
            action="mandate_revoked",
            status="success",
            details=f"Mandate revoked: {reason or 'no reason given'}",
        )
        
        logger.info(f"🚫 Mandate revoked: {mandate_id}")
        mandate.status = "revoked"
        mandate.revoked_at = now
        mandate.revoked_reason = reason
        return mandate
    
    def validate_charge(self, mandate_id: str, amount: float, currency: str) -> dict:
        """Validate that a charge is allowed under the mandate."""
        mandate = self.get_mandate(mandate_id)
        if not mandate:
            return {"allowed": False, "reason": "Mandate not found"}
        
        if mandate.status != "active":
            return {"allowed": False, "reason": f"Mandate is {mandate.status}"}
        
        if amount > mandate.max_amount:
            return {"allowed": False, "reason": f"Amount {amount} exceeds max {mandate.max_amount}"}
        
        if currency.lower() != mandate.currency.lower():
            return {"allowed": False, "reason": f"Currency mismatch: {currency} vs {mandate.currency}"}
        
        return {"allowed": True, "mandate": mandate.to_dict()}
    
    def schedule_charge_notification(
        self,
        mandate_id: str,
        amount: float,
        currency: str,
        description: str = "",
        charge_at: datetime = None,
    ) -> dict:
        """Schedule a pre-charge notification."""
        mandate = self.get_mandate(mandate_id)
        if not mandate:
            return {"error": "Mandate not found"}
        
        if charge_at is None:
            charge_at = datetime.utcnow() + timedelta(hours=NOTIFY_ADVANCE_HOURS)
        
        notification_id = f"notif_{uuid.uuid4().hex[:16]}"
        now = datetime.utcnow().isoformat() + "Z"
        
        conn = self._conn()
        try:
            conn.execute(
                """INSERT INTO charge_notifications
                (id, mandate_id, customer_email, amount, currency, description, scheduled_charge_at, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (notification_id, mandate_id, mandate.customer_email, amount, currency,
                 description, charge_at.isoformat() + "Z", now)
            )
            conn.commit()
        finally:
            conn.close()
        
        # Send notification immediately if email is configured
        sent = self._send_charge_notification(
            email=mandate.customer_email,
            customer_name=mandate.customer_name,
            amount=amount,
            currency=currency,
            description=description,
            charge_at=charge_at,
            mandate_id=mandate_id,
        )
        
        # Update notification status
        conn = self._conn()
        try:
            status = "sent" if sent else "queued"
            sent_at = now if sent else None
            conn.execute(
                "UPDATE charge_notifications SET notification_status = ?, notification_sent_at = ? WHERE id = ?",
                (status, sent_at, notification_id)
            )
            conn.commit()
        finally:
            conn.close()
        
        # Record in consent trail
        self._record_consent(
            mandate_id=mandate_id,
            customer_id=mandate.customer_id,
            action="notification_scheduled",
            amount=amount,
            currency=currency,
            status="success" if sent else "pending",
            details=f"Pre-charge notification for {amount} {currency} at {charge_at.isoformat()}",
        )
        
        return {
            "notification_id": notification_id,
            "sent": sent,
            "scheduled_charge_at": charge_at.isoformat() + "Z",
            "customer_email": mandate.customer_email,
        }
    
    def record_charge_attempt(
        self,
        mandate_id: str,
        amount: float,
        currency: str,
        stripe_payment_intent_id: str = None,
        status: str = "pending",
        details: str = "",
    ):
        """Record a charge attempt in the audit trail."""
        mandate = self.get_mandate(mandate_id)
        customer_id = mandate.customer_id if mandate else ""
        
        self._record_consent(
            mandate_id=mandate_id,
            customer_id=customer_id,
            action="charge_attempted",
            amount=amount,
            currency=currency,
            stripe_payment_intent_id=stripe_payment_intent_id,
            status=status,
            details=details or f"Off-session charge: {amount} {currency}",
        )
    
    def record_charge_result(
        self,
        mandate_id: str,
        amount: float,
        currency: str,
        stripe_payment_intent_id: str,
        status: str,
        details: str = "",
    ):
        """Record the result of a charge (success or failure)."""
        mandate = self.get_mandate(mandate_id)
        customer_id = mandate.customer_id if mandate else ""
        
        action = "charge_succeeded" if status == "success" else "charge_failed"
        
        self._record_consent(
            mandate_id=mandate_id,
            customer_id=customer_id,
            action=action,
            amount=amount,
            currency=currency,
            stripe_payment_intent_id=stripe_payment_intent_id,
            status=status,
            details=details,
        )
    
    def get_consent_trail(self, mandate_id: str) -> list:
        """Get full audit trail for a mandate."""
        conn = self._conn()
        try:
            rows = conn.execute(
                "SELECT * FROM consent_records WHERE mandate_id = ? ORDER BY created_at ASC",
                (mandate_id,)
            ).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()
    
    def get_compliance_report(self, customer_id: str = None) -> dict:
        """Generate a compliance report."""
        conn = self._conn()
        try:
            # Count mandates by status
            if customer_id:
                mandate_counts = conn.execute(
                    "SELECT status, COUNT(*) as count FROM mandates WHERE customer_id = ? GROUP BY status",
                    (customer_id,)
                ).fetchall()
                total_mandates = conn.execute(
                    "SELECT COUNT(*) FROM mandates WHERE customer_id = ?", (customer_id,)
                ).fetchone()[0]
            else:
                mandate_counts = conn.execute(
                    "SELECT status, COUNT(*) as count FROM mandates GROUP BY status"
                ).fetchall()
                total_mandates = conn.execute("SELECT COUNT(*) FROM mandates").fetchone()[0]
            
            # Count consent records by action
            if customer_id:
                action_counts = conn.execute(
                    "SELECT action, COUNT(*) as count FROM consent_records WHERE customer_id = ? GROUP BY action",
                    (customer_id,)
                ).fetchall()
            else:
                action_counts = conn.execute(
                    "SELECT action, COUNT(*) as count FROM consent_records GROUP BY action"
                ).fetchall()
            
            # Pending notifications
            pending_notifs = conn.execute(
                "SELECT COUNT(*) FROM charge_notifications WHERE notification_status = 'pending'"
            ).fetchone()[0]
            
            return {
                "total_mandates": total_mandates,
                "mandates_by_status": {row["status"]: row["count"] for row in mandate_counts},
                "activity_by_type": {row["action"]: row["count"] for row in action_counts},
                "pending_notifications": pending_notifs,
                "compliance_status": "compliant" if total_mandates > 0 else "no_mandates",
            }
        finally:
            conn.close()
    
    # ── Private helpers ──────────────────────────────────────────────────
    
    def _record_consent(
        self,
        mandate_id: str,
        customer_id: str,
        action: str,
        status: str,
        details: str = "",
        amount: float = None,
        currency: str = None,
        stripe_payment_intent_id: str = None,
        ip_address: str = None,
        user_agent: str = None,
    ):
        """Insert a consent record into the audit trail."""
        record_id = f"cons_{uuid.uuid4().hex[:16]}"
        now = datetime.utcnow().isoformat() + "Z"
        
        conn = self._conn()
        try:
            conn.execute(
                """INSERT INTO consent_records
                (id, mandate_id, customer_id, action, amount, currency,
                 stripe_payment_intent_id, status, details, ip_address, user_agent, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (record_id, mandate_id, customer_id, action, amount, currency,
                 stripe_payment_intent_id, status, details, ip_address, user_agent, now)
            )
            conn.commit()
        finally:
            conn.close()
    
    def _send_charge_notification(
        self,
        email: str,
        customer_name: str,
        amount: float,
        currency: str,
        description: str,
        charge_at: datetime,
        mandate_id: str,
    ) -> bool:
        """Send pre-charge notification email."""
        if not SMTP_USER or not SMTP_PASS:
            logger.warning("⚠️  SMTP not configured — notification queued but not sent")
            return False
        
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            
            subject = f"Upcoming Charge: {amount} {currency}"
            
            body = f"""
Hello {customer_name or 'Customer'},

This is a notification that your card will be charged:

  Amount: {amount} {currency.upper()}
  Description: {description or 'Recurring charge'}
  Scheduled: {charge_at.strftime('%Y-%m-%d %H:%M UTC')}

This charge is authorized under your saved payment mandate (ID: {mandate_id}).

If you did not authorize this or wish to cancel:
  - Reply to this email
  - Or contact support at payments@sichermayor.online

Thank you,
BeastPay — Secure Auto-Pay
"""
            
            msg = MIMEMultipart()
            msg["From"] = NOTIFY_FROM
            msg["To"] = email
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain"))
            
            with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
                server.starttls()
                server.login(SMTP_USER, SMTP_PASS)
                server.send_message(msg)
            
            logger.info(f"📧 Pre-charge notification sent to {email}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to send notification: {e}")
            return False
    
    def _row_to_mandate(self, row) -> Optional[Mandate]:
        """Convert a database row to a Mandate object."""
        if not row:
            return None
        d = dict(row)
        if d.get("metadata"):
            try:
                d["metadata"] = json.loads(d["metadata"])
            except (json.JSONDecodeError, TypeError):
                d["metadata"] = None
        return Mandate(**d)

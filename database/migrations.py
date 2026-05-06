"""Database initialization and async wrapper."""
import sqlite3
import asyncio
from typing import Any, List, Dict
from . import DB_PATH

class AsyncDB:
    """Async wrapper for SQLite database operations."""

    def __init__(self, db_path: str = DB_PATH):
        self.db_path = db_path
        self._executor = None

    async def execute(self, query: str, params: tuple = ()):
        """Execute a query (INSERT, UPDATE, DELETE)."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._execute_sync, query, params)

    async def fetchone(self, query: str, params: tuple = ()) -> Dict[str, Any] | None:
        """Fetch a single row."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._fetchone_sync, query, params)

    async def fetchall(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """Fetch all rows."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._fetchall_sync, query, params)

    def _execute_sync(self, query: str, params: tuple):
        """Sync execute."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        try:
            cursor.execute(query, params)
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    def _fetchone_sync(self, query: str, params: tuple) -> Dict[str, Any] | None:
        """Sync fetchone."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        try:
            cursor.execute(query, params)
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    def _fetchall_sync(self, query: str, params: tuple) -> List[Dict[str, Any]]:
        """Sync fetchall."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        try:
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        finally:
            conn.close()


async def init_db():
    """Initialize database schema."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Create tables if they don't exist
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS merchants (
        id TEXT PRIMARY KEY,
        name TEXT,
        email TEXT,
        api_key TEXT UNIQUE,
        webhook_url TEXT,
        is_active INTEGER DEFAULT 1,
        created_at TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS payments (
        id TEXT PRIMARY KEY,
        link_id TEXT,
        merchant_id TEXT,
        amount REAL,
        fiat_currency TEXT,
        crypto_currency TEXT,
        wallet_address TEXT,
        customer_email TEXT,
        customer_name TEXT,
        status TEXT,
        provider TEXT,
        provider_tx_id TEXT,
        provider_order_id TEXT,
        crypto_amount REAL,
        exchange_rate REAL,
        fee_amount REAL,
        description TEXT,
        webhook_data TEXT,
        created_at TEXT,
        updated_at TEXT,
        FOREIGN KEY(merchant_id) REFERENCES merchants(id)
    )
    """)

    conn.commit()
    conn.close()


def get_db():
    """Dependency for FastAPI to provide AsyncDB instance."""
    return AsyncDB(DB_PATH)

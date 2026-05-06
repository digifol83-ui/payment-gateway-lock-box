# Database package
import sqlite3

DB_PATH = "payments.db"

def get_conn():
    """Get a SQLite connection."""
    return sqlite3.connect(DB_PATH)

"""San Xuat's own business database — fully separate from ANSER's.

SQLite file, created fresh on first run. Only the `users` table (read via
core/auth_db.py) is shared with ANSER; everything below is private to this app.
"""
import sqlite3
from datetime import datetime

from core.config import Config

SCHEMA = """
CREATE TABLE IF NOT EXISTS products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    category TEXT,
    unit TEXT DEFAULT 'cái',
    price REAL DEFAULT 0,
    stock_quantity INTEGER DEFAULT 0,
    description TEXT,
    image_url TEXT,
    created_by INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS customers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE,
    name TEXT NOT NULL,
    phone TEXT,
    email TEXT,
    address TEXT,
    notes TEXT,
    created_by INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS import_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT,
    supplier_name TEXT,
    total_amount REAL DEFAULT 0,
    notes TEXT,
    status TEXT DEFAULT 'completed',
    created_by INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS import_details (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    import_id INTEGER NOT NULL,
    product_id INTEGER,
    quantity REAL DEFAULT 0,
    unit_price REAL DEFAULT 0,
    total_price REAL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS export_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT,
    customer_id INTEGER,
    total_amount REAL DEFAULT 0,
    notes TEXT,
    status TEXT DEFAULT 'completed',
    created_by INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS export_details (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    export_id INTEGER NOT NULL,
    product_id INTEGER,
    quantity REAL DEFAULT 0,
    unit_price REAL DEFAULT 0,
    total_price REAL DEFAULT 0
);
"""


def get_connection():
    conn = sqlite3.connect(Config.SANXUAT_DATABASE_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_connection()
    try:
        conn.executescript(SCHEMA)
        conn.commit()
    finally:
        conn.close()


def now():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

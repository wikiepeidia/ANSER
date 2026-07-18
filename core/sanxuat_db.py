"""San Xuat's own business database — fully separate from ANSER's.

Only the `users` table (read via core/auth_db.py) is shared; everything
below is private to this app. Supports SQLite (local dev, default) or its
own Postgres/Neon database (Config.SANXUAT_USE_POSTGRES) — a *different*
Neon database than the shared auth one, never the same as Retail's.
"""
import re
import sqlite3
from datetime import datetime

from core.config import Config

SCHEMA_SQLITE = """
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

-- Sink for n8n workflow callbacks (RAG_BASE_URL / NOTIFY_URL nodes in
-- workflow_templates/manuf_*.json). Each row is one HTTP call an n8n
-- workflow made back into this app while running.
CREATE TABLE IF NOT EXISTS automation_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action TEXT NOT NULL,
    payload TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- production_orders table (real backend for the Phase 1 mock in static/js/store.js).
-- code is id-derived ('DH-' || (1000+id)) so it's set via UPDATE right after
-- INSERT, once the id is known (see routes/production_routes.py).
CREATE TABLE IF NOT EXISTS production_orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT UNIQUE,
    product_code TEXT NOT NULL,
    product_name TEXT NOT NULL,
    quantity REAL NOT NULL,
    unit TEXT DEFAULT 'cái',
    customer_name TEXT,
    notes TEXT,
    status TEXT NOT NULL DEFAULT 'draft',
    created_by INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    approved_at TIMESTAMP,
    approved_by INTEGER,
    is_deleted INTEGER DEFAULT 0,
    deleted_at TIMESTAMP
);
"""

SCHEMA_PG = """
CREATE TABLE IF NOT EXISTS products (
    id SERIAL PRIMARY KEY,
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
    id SERIAL PRIMARY KEY,
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
    id SERIAL PRIMARY KEY,
    code TEXT,
    supplier_name TEXT,
    total_amount REAL DEFAULT 0,
    notes TEXT,
    status TEXT DEFAULT 'completed',
    created_by INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS import_details (
    id SERIAL PRIMARY KEY,
    import_id INTEGER NOT NULL,
    product_id INTEGER,
    quantity REAL DEFAULT 0,
    unit_price REAL DEFAULT 0,
    total_price REAL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS export_transactions (
    id SERIAL PRIMARY KEY,
    code TEXT,
    customer_id INTEGER,
    total_amount REAL DEFAULT 0,
    notes TEXT,
    status TEXT DEFAULT 'completed',
    created_by INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS export_details (
    id SERIAL PRIMARY KEY,
    export_id INTEGER NOT NULL,
    product_id INTEGER,
    quantity REAL DEFAULT 0,
    unit_price REAL DEFAULT 0,
    total_price REAL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS automation_events (
    id SERIAL PRIMARY KEY,
    action TEXT NOT NULL,
    payload TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- production_orders table (real backend for the Phase 1 mock in static/js/store.js).
-- code is id-derived ('DH-' || (1000+id)) so it's set via UPDATE right after
-- INSERT, once the id is known (see routes/production_routes.py).
CREATE TABLE IF NOT EXISTS production_orders (
    id SERIAL PRIMARY KEY,
    code TEXT UNIQUE,
    product_code TEXT NOT NULL,
    product_name TEXT NOT NULL,
    quantity REAL NOT NULL,
    unit TEXT DEFAULT 'cái',
    customer_name TEXT,
    notes TEXT,
    status TEXT NOT NULL DEFAULT 'draft',
    created_by INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    approved_at TIMESTAMP,
    approved_by INTEGER,
    is_deleted BOOLEAN DEFAULT FALSE,
    deleted_at TIMESTAMP
);
"""


# ---------------------------------------------------------------------------
# PGShim — lets Postgres be used through the exact same sqlite3-style API
# (conn.execute(...), '?' placeholders, cur.lastrowid, row['col']) that
# every route in this app already uses, so route code never has to know
# which backend it's talking to.
# ---------------------------------------------------------------------------

_PG_PLACEHOLDER_RE = re.compile(
    r"'(?:[^'\\]|\\.)*'"
    r'|"(?:[^"\\]|\\.)*"'
    r'|(\?)',
    re.DOTALL,
)


def _to_pg(query):
    return _PG_PLACEHOLDER_RE.sub(
        lambda m: '%s' if m.group(1) is not None else m.group(0),
        query,
    )


class _PGShimCursor:
    def __init__(self, cursor):
        self._cursor = cursor
        self.lastrowid = None
        self.rowcount = -1

    def execute(self, query, params=None):
        has_params = params is not None and len(params) > 0
        query = _to_pg(query)
        is_insert = query.strip().upper().startswith('INSERT')
        try:
            if is_insert and 'RETURNING' not in query.upper():
                query += " RETURNING id"
                self._cursor.execute(query, params) if has_params else self._cursor.execute(query)
                row = self._cursor.fetchone()
                if row:
                    self.lastrowid = row['id']
            else:
                self._cursor.execute(query, params) if has_params else self._cursor.execute(query)
                self.lastrowid = None
            self.rowcount = self._cursor.rowcount
            return self
        except Exception as e:
            if is_insert and 'RETURNING id' in query:
                try:
                    if hasattr(self._cursor, 'connection'):
                        self._cursor.connection.rollback()
                except Exception:
                    pass
                clean_query = query.replace(" RETURNING id", "")
                self._cursor.execute(clean_query, params) if has_params else self._cursor.execute(clean_query)
                self.lastrowid = None
                return self
            raise e

    def executescript(self, script):
        self._cursor.execute(script)
        return self

    def fetchone(self): return self._cursor.fetchone()
    def fetchall(self): return self._cursor.fetchall()
    def fetchmany(self, size=None): return self._cursor.fetchmany(size)
    def close(self): self._cursor.close()
    def __getattr__(self, name): return getattr(self._cursor, name)


class _PGShimConnection:
    def __init__(self, conn):
        self._conn = conn

    def cursor(self):
        import psycopg2.extras
        return _PGShimCursor(self._conn.cursor(cursor_factory=psycopg2.extras.DictCursor))

    def execute(self, query, params=None):
        cur = self.cursor()
        cur.execute(query, params)
        return cur

    def executescript(self, script):
        cur = self.cursor()
        cur.executescript(script)
        return cur

    def commit(self): self._conn.commit()
    def rollback(self): self._conn.rollback()
    def close(self):
        try:
            self._conn.rollback()
        except Exception:
            pass
        self._conn.close()


def get_connection():
    if Config.SANXUAT_USE_POSTGRES:
        import psycopg2
        conn = psycopg2.connect(Config.SANXUAT_POSTGRES_URL)
        return _PGShimConnection(conn)
    conn = sqlite3.connect(Config.SANXUAT_DATABASE_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    conn = get_connection()
    try:
        conn.executescript(SCHEMA_PG if Config.SANXUAT_USE_POSTGRES else SCHEMA_SQLITE)
        conn.commit()
    finally:
        conn.close()


def now():
    return datetime.now().strftime('%Y-%m-%d %H:%M:%S')

"""Shared fixtures for service-layer unit tests."""
import sqlite3
import pytest


_SCHEMA_SQL = """
    CREATE TABLE IF NOT EXISTS products (
        id   INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT,
        name TEXT,
        price          REAL    DEFAULT 0,
        stock_quantity INTEGER DEFAULT 0,
        created_by     INTEGER
    );
    CREATE TABLE IF NOT EXISTS import_transactions (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        code         TEXT,
        supplier_name TEXT,
        total_amount  REAL    DEFAULT 0,
        notes        TEXT,
        status       TEXT    DEFAULT 'completed',
        created_by   INTEGER,
        created_at   TEXT    DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS import_details (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        import_id  INTEGER,
        product_id INTEGER,
        quantity   REAL DEFAULT 0,
        unit_price REAL DEFAULT 0,
        total_price REAL DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS export_transactions (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        code         TEXT,
        customer_id  INTEGER,
        total_amount REAL    DEFAULT 0,
        notes        TEXT,
        status       TEXT    DEFAULT 'completed',
        created_by   INTEGER,
        created_at   TEXT    DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS export_details (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        export_id   INTEGER,
        product_id  INTEGER,
        quantity    REAL DEFAULT 0,
        unit_price  REAL DEFAULT 0,
        total_price REAL DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS workflows (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id     INTEGER,
        name        TEXT,
        description TEXT,
        data        TEXT,
        created_at  TEXT DEFAULT CURRENT_TIMESTAMP,
        updated_at  TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS ai_chat_history (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id    INTEGER,
        role       TEXT,
        content    TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS chat_sessions (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id      INTEGER,
        workspace_id INTEGER,
        title        TEXT,
        last_active  TEXT DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS chat_attachments (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id       INTEGER,
        file_name        TEXT,
        file_type        TEXT,
        analysis_summary TEXT,
        created_at       TEXT DEFAULT CURRENT_TIMESTAMP
    );
"""


def _make_mem_conn() -> sqlite3.Connection:
    """Return a fresh in-memory SQLite connection with the common service schema."""
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA_SQL)
    # Seed one product so export-path contract tests can look up stock
    conn.execute(
        "INSERT INTO products (id, code, name, price, stock_quantity, created_by)"
        " VALUES (1, 'P-001', 'Test Product', 10.0, 100, 1)"
    )
    conn.commit()
    return conn


@pytest.fixture
def db_stub():
    """Real in-memory SQLite connection (replaces the old _StubRow stub).

    Returns actual database behaviour so contract smoke-tests exercise real
    service code paths instead of short-circuiting through a fake cursor.
    """
    return _make_mem_conn()


@pytest.fixture
def workflow_payload():
    """Workflow payload fixture consumed by service tests."""
    return {"nodes": [], "edges": []}


@pytest.fixture
def tx_payload():
    """Import/export item payload fixture consumed by service tests."""
    return {
        "items": [
            {"product_id": 1, "quantity": 2, "unit_price": 10.0}
        ]
    }

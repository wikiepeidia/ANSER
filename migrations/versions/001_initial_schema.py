"""Initial schema — all 22 tables.

Revision ID: 001
Revises:
Create Date: 2026-05-29
"""
from alembic import op

revision = '001'
down_revision = None
branch_labels = None
depends_on = None

# fmt: off
_TABLES = [
    """
    CREATE TABLE IF NOT EXISTS users (
        id                    SERIAL PRIMARY KEY,
        email                 TEXT UNIQUE NOT NULL,
        password              TEXT NOT NULL,
        password_version      INTEGER DEFAULT 0,
        name                  TEXT,
        role                  TEXT DEFAULT 'user',
        avatar                TEXT,
        theme                 TEXT DEFAULT 'dark',
        first_name            TEXT,
        last_name             TEXT,
        google_token          TEXT,
        manager_id            INTEGER,
        subscription_expires_at TEXT,
        created_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS workspaces (
        id          SERIAL PRIMARY KEY,
        user_id     INTEGER NOT NULL,
        name        TEXT NOT NULL,
        type        TEXT DEFAULT 'personal',
        description TEXT,
        is_active   INTEGER DEFAULT 1,
        created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS items (
        id           SERIAL PRIMARY KEY,
        workspace_id INTEGER NOT NULL,
        title        TEXT NOT NULL,
        description  TEXT,
        type         TEXT DEFAULT 'task',
        status       TEXT DEFAULT 'todo',
        priority     TEXT DEFAULT 'medium',
        assignee_id  INTEGER,
        due_date     TEXT,
        created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS customers (
        id          SERIAL PRIMARY KEY,
        code        TEXT UNIQUE,
        name        TEXT NOT NULL,
        phone       TEXT,
        email       TEXT,
        address     TEXT,
        notes       TEXT,
        created_by  INTEGER,
        created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS products (
        id             SERIAL PRIMARY KEY,
        code           TEXT UNIQUE,
        name           TEXT NOT NULL,
        category       TEXT,
        unit           TEXT,
        price          REAL DEFAULT 0,
        stock_quantity INTEGER DEFAULT 0,
        description    TEXT,
        created_by     INTEGER,
        created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        image_url      TEXT
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS import_transactions (
        id            SERIAL PRIMARY KEY,
        code          TEXT,
        supplier_name TEXT,
        total_amount  REAL DEFAULT 0,
        notes         TEXT,
        status        TEXT DEFAULT 'completed',
        created_by    INTEGER,
        created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS import_details (
        id          SERIAL PRIMARY KEY,
        import_id   INTEGER NOT NULL,
        product_id  INTEGER,
        quantity    REAL DEFAULT 0,
        unit_price  REAL DEFAULT 0,
        total_price REAL DEFAULT 0
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS export_transactions (
        id           SERIAL PRIMARY KEY,
        code         TEXT,
        customer_id  INTEGER,
        total_amount REAL DEFAULT 0,
        notes        TEXT,
        status       TEXT DEFAULT 'completed',
        created_by   INTEGER,
        created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS export_details (
        id          SERIAL PRIMARY KEY,
        export_id   INTEGER NOT NULL,
        product_id  INTEGER,
        quantity    REAL DEFAULT 0,
        unit_price  REAL DEFAULT 0,
        total_price REAL DEFAULT 0
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS sales (
        id             SERIAL PRIMARY KEY,
        user_id        INTEGER,
        total_amount   REAL,
        amount_given   REAL,
        change_amount  REAL,
        items          TEXT,
        payment_method TEXT DEFAULT 'cash',
        workspace_id   INTEGER,
        category       TEXT DEFAULT 'Retail',
        created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS manager_subscriptions (
        id                SERIAL PRIMARY KEY,
        user_id           INTEGER UNIQUE,
        subscription_type TEXT,
        amount            REAL,
        start_date        TEXT,
        end_date          TEXT,
        status            TEXT DEFAULT 'inactive',
        auto_renew        INTEGER DEFAULT 0,
        payment_method    TEXT,
        transaction_id    TEXT,
        created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS subscription_history (
        id                SERIAL PRIMARY KEY,
        user_id           INTEGER,
        subscription_type TEXT,
        amount            REAL,
        payment_date      TEXT,
        payment_method    TEXT,
        transaction_id    TEXT,
        status            TEXT,
        notes             TEXT,
        created_at        TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS wallets (
        id         SERIAL PRIMARY KEY,
        user_id    INTEGER UNIQUE,
        balance    REAL DEFAULT 0,
        currency   TEXT DEFAULT 'VND',
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS wallet_transactions (
        id         SERIAL PRIMARY KEY,
        user_id    INTEGER,
        amount     REAL,
        currency   TEXT DEFAULT 'VND',
        type       TEXT,
        status     TEXT DEFAULT 'pending',
        method     TEXT,
        reference  TEXT,
        notes      TEXT,
        metadata   TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS workflows (
        id          SERIAL PRIMARY KEY,
        user_id     INTEGER,
        name        TEXT,
        description TEXT,
        data        TEXT,
        created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS se_automations (
        id         SERIAL PRIMARY KEY,
        name       TEXT,
        type       TEXT,
        config     TEXT,
        enabled    INTEGER DEFAULT 0,
        last_run   TEXT,
        created_by INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS scheduled_reports (
        id           SERIAL PRIMARY KEY,
        name         TEXT,
        report_type  TEXT,
        frequency    TEXT,
        channel      TEXT,
        recipients   TEXT,
        status       TEXT DEFAULT 'active',
        last_sent_at TEXT,
        created_by   INTEGER,
        created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS activity_logs (
        id         SERIAL PRIMARY KEY,
        user_id    INTEGER,
        action     TEXT,
        details    TEXT,
        ip_address TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS ai_chat_history (
        id         SERIAL PRIMARY KEY,
        user_id    INTEGER,
        role       TEXT,
        content    TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS chat_sessions (
        id           SERIAL PRIMARY KEY,
        user_id      INTEGER,
        workspace_id INTEGER,
        title        TEXT,
        last_active  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS chat_attachments (
        id               SERIAL PRIMARY KEY,
        session_id       INTEGER,
        file_name        TEXT,
        file_type        TEXT,
        analysis_summary TEXT,
        created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS system_settings (
        key        TEXT PRIMARY KEY,
        value      TEXT,
        group_name TEXT,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
]
# fmt: on


def upgrade():
    for ddl in _TABLES:
        op.execute(ddl)


def downgrade():
    tables = [
        'system_settings', 'chat_attachments', 'chat_sessions', 'ai_chat_history',
        'activity_logs', 'scheduled_reports', 'se_automations', 'workflows',
        'wallet_transactions', 'wallets', 'subscription_history', 'manager_subscriptions',
        'sales', 'export_details', 'export_transactions', 'import_details',
        'import_transactions', 'products', 'customers', 'items', 'workspaces', 'users',
    ]
    for t in tables:
        op.execute(f'DROP TABLE IF EXISTS {t} CASCADE')

"""Add warehouses table — per-warehouse low-stock alert config.

Revision ID: 002
Revises: 001
Create Date: 2026-07-03
"""
from alembic import op

revision = '002'
down_revision = '001'
branch_labels = None
depends_on = None

_TABLES = [
    """
    CREATE TABLE IF NOT EXISTS warehouses (
        id                   SERIAL PRIMARY KEY,
        name                 TEXT NOT NULL,
        low_stock_threshold  INTEGER DEFAULT 10,
        discord_webhook_url  TEXT,
        is_active            INTEGER DEFAULT 1,
        created_by           INTEGER,
        created_at           TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """,
]


def upgrade():
    for ddl in _TABLES:
        op.execute(ddl)


def downgrade():
    op.execute('DROP TABLE IF EXISTS warehouses CASCADE')

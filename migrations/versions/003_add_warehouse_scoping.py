"""Add warehouse_stock table + warehouse_id scoping on sales/import/export.

Lets a retail chain track separate stock, revenue and transactions per
warehouse/store instead of one global pool for the whole system.

Revision ID: 003
Revises: 002
Create Date: 2026-07-05
"""
from alembic import op

revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None

_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS warehouse_stock (
        id             SERIAL PRIMARY KEY,
        warehouse_id   INTEGER NOT NULL,
        product_id     INTEGER NOT NULL,
        stock_quantity INTEGER DEFAULT 0,
        updated_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(warehouse_id, product_id)
    )
    """,
    "ALTER TABLE sales ADD COLUMN IF NOT EXISTS warehouse_id INTEGER",
    "ALTER TABLE import_transactions ADD COLUMN IF NOT EXISTS warehouse_id INTEGER",
    "ALTER TABLE export_transactions ADD COLUMN IF NOT EXISTS warehouse_id INTEGER",
]


def upgrade():
    for stmt in _STATEMENTS:
        op.execute(stmt)


def downgrade():
    op.execute('ALTER TABLE export_transactions DROP COLUMN IF EXISTS warehouse_id')
    op.execute('ALTER TABLE import_transactions DROP COLUMN IF EXISTS warehouse_id')
    op.execute('ALTER TABLE sales DROP COLUMN IF EXISTS warehouse_id')
    op.execute('DROP TABLE IF EXISTS warehouse_stock CASCADE')

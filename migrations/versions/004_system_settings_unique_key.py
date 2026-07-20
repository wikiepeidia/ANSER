"""Add UNIQUE constraint on system_settings.key — required by
api_update_settings's ON CONFLICT(key) DO UPDATE clause.

The 001 migration declared `key TEXT PRIMARY KEY`, but the actual production
Neon table was created without it (probably via a hand-rolled schema that
predated alembic). Without the constraint, every save on /settings returns
500 — psycopg2 raises InvalidColumnReference because there's no unique or
exclusion constraint matching the ON CONFLICT specification.

Revision ID: 004
Revises: 003
"""
from alembic import op

revision = '004'
down_revision = '003'
branch_labels = None
depends_on = None


def upgrade():
    # CREATE UNIQUE INDEX (not ALTER TABLE ADD CONSTRAINT) so this is safe
    # against the table already having duplicate keys. If duplicates exist,
    # the index creation will fail loudly and the operator can clean them up
    # before retrying.
    op.execute(
        'CREATE UNIQUE INDEX IF NOT EXISTS system_settings_key_unique '
        'ON system_settings(key)'
    )


def downgrade():
    op.execute('DROP INDEX IF EXISTS system_settings_key_unique')

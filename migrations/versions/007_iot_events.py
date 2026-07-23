"""Add iot_events table.

Same story as 004/006: this table already exists on the live production
DB (used by /api/n8n/internal/iot-events), added by hand at some point —
but was never in an Alembic migration, so a fresh Postgres database
provisioned from migrations alone (e.g. a new BUSINESS_POSTGRES_URL split
off later, or a clean deploy) would be missing it entirely.

Revision ID: 007
Revises: 006
"""
from alembic import op

revision = '007'
down_revision = '006'
branch_labels = None
depends_on = None


def upgrade():
    op.execute('''
        CREATE TABLE IF NOT EXISTS iot_events (
            id SERIAL PRIMARY KEY,
            device_id VARCHAR NOT NULL,
            event_type VARCHAR NOT NULL,
            payload JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ DEFAULT now()
        )
    ''')


def downgrade():
    op.execute('DROP TABLE IF EXISTS iot_events')

"""Add notification_email to warehouses — an email-based alert channel
alongside the existing discord_webhook_url, for shop owners/managers who
don't use Discord.

Revision ID: 005
Revises: 004
"""
from alembic import op
import sqlalchemy as sa

revision = '005'
down_revision = '004'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('warehouses', sa.Column('notification_email', sa.Text(), nullable=True))


def downgrade():
    op.drop_column('warehouses', 'notification_email')

"""Add expiry_date to products — backs product_expiry_alert.json.

Revision ID: 008
Revises: 007
"""
from alembic import op
import sqlalchemy as sa

revision = '008'
down_revision = '007'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('products', sa.Column('expiry_date', sa.Text(), nullable=True))


def downgrade():
    op.drop_column('products', 'expiry_date')

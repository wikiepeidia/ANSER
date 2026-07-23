"""Fix wallets table missing UNIQUE(user_id) — same pre-Alembic drift as 009.

_ensure_wallet() in wallet_service.py runs, on every wallet read/topup/
withdraw/upgrade:
    INSERT INTO wallets (user_id, balance, currency) VALUES (?, 0, 'VND')
    ON CONFLICT (user_id) DO NOTHING
which requires a unique/exclusion constraint on user_id to be valid Postgres.
Without it, every one of those calls raises InvalidColumnReference. Found by
exercising POST /api/user/wallet/topup end-to-end after 009 — the wallet
approve/reject flow was untestable until this is fixed too, since topup
requests can't even be created.

No duplicate user_id rows exist in production today, so this is a
straight ADD CONSTRAINT with no backfill needed.

Revision ID: 011
Revises: 010
"""
from alembic import op

revision = '011'
down_revision = '010'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE wallets ADD CONSTRAINT wallets_user_id_key UNIQUE (user_id)")


def downgrade():
    op.execute("ALTER TABLE wallets DROP CONSTRAINT IF EXISTS wallets_user_id_key")

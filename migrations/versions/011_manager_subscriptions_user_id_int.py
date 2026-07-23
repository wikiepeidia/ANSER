"""manager_subscriptions.user_id: text -> integer.

Same pre-Alembic drift as 004/006/007/008/009/010: this table was hand-
created with every column typed TEXT, including user_id, which is a
foreign key to users.id (integer) everywhere it's used in code —
wallet_service.py and subscription_service.py both pass current_user.id
(a Python int) as the bind param for `WHERE user_id = ?`. SQLite accepts
this fine (dynamic typing); Postgres does not, since there's no implicit
`text = integer` operator. Found by exercising GET /api/user/wallet
end-to-end after 010: it 500s with
"operator does not exist: text = integer" the moment a user has a row
in this table.

All 3 existing rows have plain-integer-looking user_id values
('1001', '1002', '1003'), none of which match a real users.id, so the
cast is safe and lossless. The UNIQUE(user_id) constraint added in 009
survives the type change automatically (Postgres rebuilds the backing
index).

Revision ID: 011
Revises: 010
"""
from alembic import op

revision = '011'
down_revision = '010'
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        "ALTER TABLE manager_subscriptions "
        "ALTER COLUMN user_id TYPE integer USING user_id::integer"
    )


def downgrade():
    op.execute(
        "ALTER TABLE manager_subscriptions "
        "ALTER COLUMN user_id TYPE text USING user_id::text"
    )

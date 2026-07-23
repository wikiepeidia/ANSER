"""Fix 3 more tables with the same pre-Alembic drift as 004/006/007/008:
id columns with no working default, so every INSERT that doesn't name id
explicitly (all of them — see core/services/wallet_service.py and
operations_service.py) silently stored NULL. And manager_subscriptions is
missing the UNIQUE(user_id) that subscription_service.py's Postgres
ON CONFLICT (user_id) branch requires — extend_subscription() has been
raising InvalidColumnReference on every call in production.

Concretely, before this migration:
  - wallet_transactions.id: bigint, no default. Admin approve/reject on a
    wallet topup/withdrawal (SELECT/UPDATE ... WHERE id = ?) can never
    match a row it just inserted.
  - se_automations.id: bigint, no default. 2 of 7 existing rows already
    have id=NULL in production — enable/disable/rename/delete of those
    automations is impossible (WHERE id = ? never matches NULL).
  - subscription_history.id: text, no default. Write-only audit log today
    (nothing looks it up by id), but same landmine if that changes.
  - manager_subscriptions: no unique constraint on user_id at all.

Revision ID: 009
Revises: 008
"""
from alembic import op

revision = '009'
down_revision = '008'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("CREATE SEQUENCE IF NOT EXISTS wallet_transactions_id_seq")
    op.execute("SELECT setval('wallet_transactions_id_seq', GREATEST((SELECT COALESCE(MAX(id), 0) FROM wallet_transactions), 1))")
    op.execute("ALTER TABLE wallet_transactions ALTER COLUMN id SET DEFAULT nextval('wallet_transactions_id_seq')")
    op.execute("ALTER SEQUENCE wallet_transactions_id_seq OWNED BY wallet_transactions.id")

    op.execute("CREATE SEQUENCE IF NOT EXISTS se_automations_id_seq")
    op.execute("SELECT setval('se_automations_id_seq', GREATEST((SELECT COALESCE(MAX(id), 0) FROM se_automations), 1))")
    op.execute("ALTER TABLE se_automations ALTER COLUMN id SET DEFAULT nextval('se_automations_id_seq')")
    op.execute("ALTER SEQUENCE se_automations_id_seq OWNED BY se_automations.id")
    op.execute("UPDATE se_automations SET id = nextval('se_automations_id_seq') WHERE id IS NULL")

    op.execute("ALTER TABLE subscription_history ALTER COLUMN id SET DEFAULT gen_random_uuid()::text")
    op.execute("UPDATE subscription_history SET id = gen_random_uuid()::text WHERE id IS NULL")

    op.execute("ALTER TABLE manager_subscriptions ADD CONSTRAINT manager_subscriptions_user_id_key UNIQUE (user_id)")


def downgrade():
    op.execute("ALTER TABLE manager_subscriptions DROP CONSTRAINT IF EXISTS manager_subscriptions_user_id_key")
    op.execute("ALTER TABLE subscription_history ALTER COLUMN id DROP DEFAULT")
    op.execute("ALTER TABLE se_automations ALTER COLUMN id DROP DEFAULT")
    op.execute("DROP SEQUENCE IF EXISTS se_automations_id_seq")
    op.execute("ALTER TABLE wallet_transactions ALTER COLUMN id DROP DEFAULT")
    op.execute("DROP SEQUENCE IF EXISTS wallet_transactions_id_seq")

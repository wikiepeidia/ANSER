"""Add working DEFAULTs to scheduled_reports.id/status.

The 001 migration declared `id SERIAL PRIMARY KEY, status TEXT DEFAULT
'active'`, but — same story as 004's system_settings fix — the actual
production table predates Alembic and was created by hand with `id text`
(no default) and `status text` (no default). create_scheduled_report()
never set either column explicitly, so every report created through the
real /se/reports UI silently got id=NULL, status=NULL: undeletable (its
own id can never match a WHERE id=? lookup) and invisible to any status='
active' scheduler. The app now sets both explicitly on insert (defense in
depth for SQLite dev, where this migration doesn't apply), but production
rows inserted through any other path still need a working default.

Revision ID: 007
Revises: 006
"""
from alembic import op

revision = '007'
down_revision = '006'
branch_labels = None
depends_on = None


def upgrade():
    op.execute("ALTER TABLE scheduled_reports ALTER COLUMN status SET DEFAULT 'active'")
    op.execute("ALTER TABLE scheduled_reports ALTER COLUMN id SET DEFAULT gen_random_uuid()::text")
    op.execute("UPDATE scheduled_reports SET status = 'active' WHERE status IS NULL")
    op.execute("UPDATE scheduled_reports SET id = gen_random_uuid()::text WHERE id IS NULL")


def downgrade():
    op.execute("ALTER TABLE scheduled_reports ALTER COLUMN status DROP DEFAULT")
    op.execute("ALTER TABLE scheduled_reports ALTER COLUMN id DROP DEFAULT")

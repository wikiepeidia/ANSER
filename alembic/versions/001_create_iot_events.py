"""create iot_events table

Revision ID: 001
Revises:
Create Date: 2026-06-13
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "iot_events",
        sa.Column("id",         sa.Integer(),                  autoincrement=True, nullable=False),
        sa.Column("device_id",  sa.String(255),                nullable=False),
        sa.Column("event_type", sa.String(100),                nullable=False),
        sa.Column("payload",    JSONB(),                       nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True),    server_default=sa.text("now()"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_iot_events_device_id",  "iot_events", ["device_id"])
    op.create_index("ix_iot_events_event_type", "iot_events", ["event_type"])


def downgrade() -> None:
    op.drop_index("ix_iot_events_event_type", table_name="iot_events")
    op.drop_index("ix_iot_events_device_id",  table_name="iot_events")
    op.drop_table("iot_events")

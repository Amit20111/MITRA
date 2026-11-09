"""Initial persistent agent schema; legacy milestone database remains separate."""

from alembic import op
from sqlalchemy import JSON, Column, Integer, String

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "conversations",
        Column("id", String, primary_key=True),
        Column("payload", JSON, nullable=False),
    )
    op.create_table(
        "tasks",
        Column("id", String, primary_key=True),
        Column("conversation_id", String, nullable=False),
        Column("payload", JSON, nullable=False),
    )
    op.create_table(
        "events",
        Column("id", Integer, primary_key=True, autoincrement=True),
        Column("task_id", String, nullable=False),
        Column("payload", JSON, nullable=False),
    )
    op.create_index("ix_events_task_id", "events", ["task_id"])
    op.create_table(
        "requests",
        Column("id", String, primary_key=True),
        Column("conversation_id", String, nullable=False),
        Column("content", String, nullable=False),
        Column("task_id", String, nullable=False),
    )
    op.create_table(
        "traces",
        Column("id", String, primary_key=True),
        Column("task_id", String, nullable=False),
        Column("step_id", String),
        Column("payload", JSON, nullable=False),
    )
    op.create_index("ix_traces_task_id", "traces", ["task_id"])


def downgrade() -> None:
    raise RuntimeError(
        "Destructive downgrade is not supported; restore a database backup instead."
    )

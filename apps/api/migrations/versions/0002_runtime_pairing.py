"""Persist hashed pairing credentials and runtime connection audit."""

from alembic import op
from sqlalchemy import Boolean, Column, Float, Integer, String

revision = "0002_runtime_pairing"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "runtime_pairings",
        Column("id", String, primary_key=True),
        Column("code_hash", String, nullable=False),
        Column("expires", Float, nullable=False),
        Column("attempts", Integer, nullable=False),
        Column("consumed", Boolean, nullable=False),
    )
    op.create_table(
        "runtime_devices",
        Column("id", String, primary_key=True),
        Column("name", String, nullable=False),
        Column("token_hash", String, nullable=False),
        Column("expires", Float, nullable=False),
        Column("revoked", Boolean, nullable=False),
        Column("last_seen", Float),
        Column("boot_id", String),
        Column("disconnected", Boolean, nullable=False),
    )
    op.create_table(
        "runtime_audit",
        Column("id", Integer, primary_key=True, autoincrement=True),
        Column("event", String, nullable=False),
        Column("runtime_id", String),
        Column("timestamp", String, nullable=False),
    )


def downgrade() -> None:
    raise RuntimeError("Restore a database backup instead of a destructive downgrade")

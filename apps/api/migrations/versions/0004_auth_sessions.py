"""Hashed browser sessions for the local web interface."""

from alembic import op
from sqlalchemy import Column, Float, String

revision = "0004_auth_sessions"
down_revision = "0003_memory"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "auth_sessions",
        Column("id", String, primary_key=True),
        Column("token_hash", String, nullable=False, unique=True),
        Column("created", Float, nullable=False),
        Column("expires", Float, nullable=False),
    )


def downgrade() -> None:
    raise RuntimeError("Restore a backup instead of destructive downgrade")

"""User-managed memory records."""

from alembic import op
from sqlalchemy import JSON, Column, String

revision = "0003_memory"
down_revision = "0002_runtime_pairing"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "memory_records",
        Column("id", String, primary_key=True),
        Column("payload", JSON, nullable=False),
    )


def downgrade() -> None:
    raise RuntimeError("Restore a backup instead of destructive downgrade")

"""add maintenance_since to seats

Revision ID: 6a7b8c9d0e1f
Revises: 5860a2080d38
Create Date: 2026-08-13 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "6a7b8c9d0e1f"
down_revision: str | Sequence[str] | None = "5860a2080d38"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "seats",
        sa.Column("maintenance_since", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("seats", "maintenance_since")

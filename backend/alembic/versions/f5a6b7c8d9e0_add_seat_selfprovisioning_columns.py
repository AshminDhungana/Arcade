"""add_seat_selfprovisioning_columns

Revision ID: f5a6b7c8d9e0
Revises: d6e7f8a9b0c1
Create Date: 2026-07-19

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f5a6b7c8d9e0"
down_revision: str | Sequence[str] | None = "d6e7f8a9b0c1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("seats", sa.Column("agent_secret", sa.String(64), nullable=True))
    op.add_column("seats", sa.Column("enroll_code_hash", sa.String(255), nullable=True))
    op.add_column(
        "seats",
        sa.Column("enroll_code_expires_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "seats", sa.Column("override_code_hash", sa.String(255), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("seats", "override_code_hash")
    op.drop_column("seats", "enroll_code_expires_at")
    op.drop_column("seats", "enroll_code_hash")
    op.drop_column("seats", "agent_secret")

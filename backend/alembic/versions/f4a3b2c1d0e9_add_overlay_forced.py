"""add overlay_forced to seats

Revision ID: f4a3b2c1d0e9
Revises: e3f2a1b0c5d6
Create Date: 2026-07-17 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "f4a3b2c1d0e9"
down_revision: str | Sequence[str] | None = "e3f2a1b0c5d6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "seats",
        sa.Column(
            "overlay_forced", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
    )


def downgrade() -> None:
    op.drop_column("seats", "overlay_forced")

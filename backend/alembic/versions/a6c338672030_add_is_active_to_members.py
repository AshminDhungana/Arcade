"""add is_active to members

Revision ID: a6c338672030
Revises: 6a7b8c9d0e1f
Create Date: 2026-08-19 14:52:38.574014

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a6c338672030"
down_revision: str | Sequence[str] | None = "6a7b8c9d0e1f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "members",
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default="1",
        ),
    )


def downgrade() -> None:
    op.drop_column("members", "is_active")

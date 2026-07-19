"""add_missing_timestamp_columns

Revision ID: k0f1a2b3c4d5
Revises: j9e0f1a2b3c4
Create Date: 2026-07-19

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "k0f1a2b3c4d5"
down_revision: str | Sequence[str] | None = "j9e0f1a2b3c4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add created_at/updated_at to zones (the Zone model declares both, but the
    # initial migration omitted them). The Staff model does NOT declare
    # created_at, so no staff column is added here.
    op.add_column(
        "zones",
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.add_column(
        "zones",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )


def downgrade() -> None:
    op.drop_column("zones", "updated_at")
    op.drop_column("zones", "created_at")

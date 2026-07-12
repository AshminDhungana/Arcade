"""add_notes_to_reservation

Revision ID: c4d5e6f7a8b9
Revises: a1bb8b056ad6
Create Date: 2026-07-12 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c4d5e6f7a8b9"
down_revision: str | Sequence[str] | None = "a1bb8b056ad6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "reservations",
        sa.Column("notes", sa.String(length=1000), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("reservations", "notes")

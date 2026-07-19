"""create_restock_logs_table

Revision ID: i8d9e0f1a2b3
Revises: h7c8d9e0f1a2
Create Date: 2026-07-19

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "i8d9e0f1a2b3"
down_revision: str | Sequence[str] | None = "h7c8d9e0f1a2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "restock_logs",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column(
            "menu_item_id",
            sa.String(32),
            sa.ForeignKey("menu_items.id"),
            nullable=False,
        ),
        sa.Column("quantity_added", sa.Integer, nullable=False),
        sa.Column(
            "logged_by_staff_id",
            sa.String(32),
            sa.ForeignKey("staff.id"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("restock_logs")

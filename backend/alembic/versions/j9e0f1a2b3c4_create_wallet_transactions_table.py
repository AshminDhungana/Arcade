"""create_wallet_transactions_table

Revision ID: j9e0f1a2b3c4
Revises: i8d9e0f1a2b3
Create Date: 2026-07-19

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "j9e0f1a2b3c4"
down_revision: str | Sequence[str] | None = "i8d9e0f1a2b3"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "wallet_transactions",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column(
            "member_id",
            sa.String(32),
            sa.ForeignKey("members.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("type", sa.String(32), nullable=False),
        sa.Column("amount_paise", sa.Integer, nullable=False),
        sa.Column("balance_after_paise", sa.Integer, nullable=False),
        sa.Column("payment_method", sa.String(16), nullable=False),
        sa.Column("staff_id", sa.String(32), nullable=True),
        sa.Column("reference_id", sa.String(32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("wallet_transactions")

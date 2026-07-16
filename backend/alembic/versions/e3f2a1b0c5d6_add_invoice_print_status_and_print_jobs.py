"""add_invoice_print_status_and_print_jobs

Revision ID: e3f2a1b0c5d6
Revises: d2e1f0a9b3c4
Create Date: 2026-07-16 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e3f2a1b0c5d6"
down_revision: str | Sequence[str] | None = "d2e1f0a9b3c4"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "invoices",
        sa.Column(
            "print_status",
            sa.String(length=10),
            nullable=False,
            server_default="PENDING",
        ),
    )
    op.create_table(
        "print_jobs",
        sa.Column("id", sa.String(length=32), nullable=False),
        sa.Column("invoice_id", sa.String(length=32), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("next_retry_at", sa.String(length=32), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.String(length=32), nullable=False),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"]),
        sa.UniqueConstraint("invoice_id"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_print_jobs_invoice_id", "print_jobs", ["invoice_id"])


def downgrade() -> None:
    op.drop_index("ix_print_jobs_invoice_id", table_name="print_jobs")
    op.drop_table("print_jobs")
    op.drop_column("invoices", "print_status")

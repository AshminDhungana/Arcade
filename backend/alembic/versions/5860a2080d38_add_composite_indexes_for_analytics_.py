"""add composite indexes for analytics queries

Revision ID: 5860a2080d38
Revises: 8f0a18288816
Create Date: 2026-07-27 16:54:50.880154

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5860a2080d38"
down_revision: str | Sequence[str] | None = "8f0a18288816"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Composite indexes for analytics query optimization
    op.create_index(
        "ix_sessions_started_at_status",
        "sessions",
        ["started_at", "status"],
        unique=False,
    )
    op.create_index(
        "ix_sessions_seat_id_started_at_status",
        "sessions",
        ["seat_id", "started_at", "status"],
        unique=False,
    )
    op.create_index(
        "ix_invoices_created_at_member_id",
        "invoices",
        ["created_at", "member_id"],
        unique=False,
    )
    op.create_index(
        "ix_session_pos_items_session_id_menu_item_id",
        "session_pos_items",
        ["session_id", "menu_item_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_session_pos_items_session_id_menu_item_id", table_name="session_pos_items"
    )
    op.drop_index("ix_invoices_created_at_member_id", table_name="invoices")
    op.drop_index("ix_sessions_seat_id_started_at_status", table_name="sessions")
    op.drop_index("ix_sessions_started_at_status", table_name="sessions")

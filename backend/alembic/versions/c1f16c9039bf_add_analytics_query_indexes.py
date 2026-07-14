"""add analytics query indexes

Revision ID: c1f16c9039bf
Revises: c4d5e6f7a8b9
Create Date: 2026-07-14 22:34:28.416839

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c1f16c9039bf"
down_revision: str | Sequence[str] | None = "c4d5e6f7a8b9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


INDEXES = [
    ("ix_invoices_created_at", "invoices", ["created_at"]),
    ("ix_invoices_member_id", "invoices", ["member_id"]),
    ("ix_sessions_started_at", "sessions", ["started_at"]),
    ("ix_sessions_ended_at", "sessions", ["ended_at"]),
    ("ix_sessions_seat_id", "sessions", ["seat_id"]),
    ("ix_sessions_member_id", "sessions", ["member_id"]),
    ("ix_session_pos_items_session_id", "session_pos_items", ["session_id"]),
    ("ix_reservations_reserved_from", "reservations", ["reserved_from"]),
]


def upgrade() -> None:
    for name, table, cols in INDEXES:
        op.create_index(name, table, cols)


def downgrade() -> None:
    for name, table, _cols in INDEXES:
        op.drop_index(name, table_name=table)

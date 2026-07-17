"""add assigned_end_at and expiry_warned to sessions

Revision ID: d6e7f8a9b0c1
Revises: f4a3b2c1d0e9
Create Date: 2026-07-17
"""

import sqlalchemy as sa
from alembic.op import add_column, create_index, drop_column, drop_index

revision: str = "d6e7f8a9b0c1"
down_revision: str = "f4a3b2c1d0e9"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    add_column(
        "sessions",
        sa.Column("assigned_end_at", sa.DateTime(timezone=True), nullable=True),
    )
    create_index("ix_sessions_assigned_end_at", "sessions", ["assigned_end_at"])
    # SQLite has no native boolean; use Integer 0/1 with server_default 0.
    add_column(
        "sessions",
        sa.Column(
            "expiry_warned",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    drop_column("sessions", "expiry_warned")
    drop_index("ix_sessions_assigned_end_at", table_name="sessions")
    drop_column("sessions", "assigned_end_at")

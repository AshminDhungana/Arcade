"""002_add_indexes

Revision ID: 5061d4ef9ce8
Revises: 258fc4588777
Create Date: 2026-07-27 13:36:12.813409

"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5061d4ef9ce8"
down_revision: str | Sequence[str] | None = "258fc4588777"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # sessions: composite indexes for common query patterns
    op.create_index(
        "ix_sessions_seat_id_status",
        "sessions",
        ["seat_id", "status"],
        unique=False,
    )
    op.create_index(
        "ix_sessions_status_started_at",
        "sessions",
        ["status", "started_at"],
        unique=False,
    )
    # sessions: single column indexes
    op.create_index(
        "ix_sessions_shift_id",
        "sessions",
        ["shift_id"],
        unique=False,
    )
    op.create_index(
        "ix_sessions_created_at",
        "sessions",
        ["created_at"],
        unique=False,
    )

    # audit_log: composite index on (timestamp, action)
    # Note: column is 'timestamp' not 'created_at'
    op.create_index(
        "ix_audit_log_timestamp_action",
        "audit_log",
        ["timestamp", "action"],
        unique=False,
    )

    # member_package_entitlements: composite index on (member_id, status)
    op.create_index(
        "ix_member_package_entitlements_member_id_status",
        "member_package_entitlements",
        ["member_id", "status"],
        unique=False,
    )

    # reservations: composite index on (seat_id, reserved_from)
    op.create_index(
        "ix_reservations_seat_id_reserved_from",
        "reservations",
        ["seat_id", "reserved_from"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_reservations_seat_id_reserved_from", table_name="reservations")
    op.drop_index(
        "ix_member_package_entitlements_member_id_status",
        table_name="member_package_entitlements",
    )
    op.drop_index("ix_audit_log_timestamp_action", table_name="audit_log")
    op.drop_index("ix_sessions_created_at", table_name="sessions")
    op.drop_index("ix_sessions_shift_id", table_name="sessions")
    op.drop_index("ix_sessions_status_started_at", table_name="sessions")
    op.drop_index("ix_sessions_seat_id_status", table_name="sessions")

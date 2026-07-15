"""add_event_matches

Revision ID: d2e1f0a9b3c4
Revises: c1f16c9039bf
Create Date: 2026-07-15 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d2e1f0a9b3c4"
down_revision: str | Sequence[str] | None = "c1f16c9039bf"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "event_matches",
        sa.Column("id", sa.String(32), primary_key=True),
        sa.Column(
            "event_id",
            sa.String(32),
            sa.ForeignKey("events.id"),
            nullable=False,
        ),
        sa.Column("bracket_group", sa.String(15), nullable=False),
        sa.Column("round", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "slot_a_id",
            sa.String(32),
            sa.ForeignKey("event_participants.id"),
            nullable=True,
        ),
        sa.Column(
            "slot_b_id",
            sa.String(32),
            sa.ForeignKey("event_participants.id"),
            nullable=True,
        ),
        sa.Column(
            "winner_id",
            sa.String(32),
            sa.ForeignKey("event_participants.id"),
            nullable=True,
        ),
        sa.Column("status", sa.String(10), nullable=False, server_default="PENDING"),
        sa.Column(
            "next_match_id",
            sa.String(32),
            sa.ForeignKey("event_matches.id"),
            nullable=True,
        ),
        sa.Column(
            "next_loser_match_id",
            sa.String(32),
            sa.ForeignKey("event_matches.id"),
            nullable=True,
        ),
    )
    op.create_index("ix_event_matches_event_id", "event_matches", ["event_id"])


def downgrade() -> None:
    op.drop_index("ix_event_matches_event_id", table_name="event_matches")
    op.drop_table("event_matches")

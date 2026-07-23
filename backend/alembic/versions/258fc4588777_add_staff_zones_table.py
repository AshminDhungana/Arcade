"""add_staff_zones_table

Revision ID: 258fc4588777
Revises: l1a2b3c4d5e6
Create Date: 2026-07-23 09:24:39.531247

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "258fc4588777"
down_revision: str | Sequence[str] | None = "l1a2b3c4d5e6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "staff_zones",
        sa.Column(
            "staff_id",
            sa.String(32),
            sa.ForeignKey("staff.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "zone_id",
            sa.String(32),
            sa.ForeignKey("zones.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "granted_by", sa.String(32), sa.ForeignKey("staff.id"), nullable=False
        ),
        sa.Column(
            "granted_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.create_index("ix_staff_zones_staff_id", "staff_zones", ["staff_id"])
    op.create_index("ix_staff_zones_zone_id", "staff_zones", ["zone_id"])
    op.create_index("ix_staff_zones_granted_by", "staff_zones", ["granted_by"])


def downgrade() -> None:
    op.drop_index("ix_staff_zones_granted_by", table_name="staff_zones")
    op.drop_index("ix_staff_zones_zone_id", table_name="staff_zones")
    op.drop_index("ix_staff_zones_staff_id", table_name="staff_zones")
    op.drop_table("staff_zones")

"""add unique constraints on zones.name and seats(zone_id, name)

Deduplicates any pre-existing colliding names before creating the indexes so the
CREATE UNIQUE INDEX cannot fail on legacy data (e.g. four zones all named
"Main Floor"). Colliding rows are RENAMED, never deleted — no zone or seat is
removed, preserving areas the operator may still need.

Revision ID: l1a2b3c4d5e6
Revises: k0f1a2b3c4d5
Create Date: 2026-07-19

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "l1a2b3c4d5e6"
down_revision: str | Sequence[str] | None = "k0f1a2b3c4d5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _dedupe(table: str, partition_cols: list[str], name_col: str) -> None:
    """Rename rows so ``(partition_cols..., name_col)`` is unique.

    Keeps the first row (by rowid) of each name-group unchanged and suffixes the
    rest with `` (2)``, `` (3)``, … Idempotent enough for a one-shot migration:
    it only touches rows that currently collide.
    """
    conn = op.get_bind()
    # Group colliding rows; for each group produce the rowids ordered oldest-first.
    order = ", ".join([*partition_cols, "rowid"]) if partition_cols else "rowid"
    rows = conn.execute(
        sa.text(
            f"SELECT rowid, {name_col} FROM {table} ORDER BY {order}"  # noqa: S608  # nosec B608
        )
    ).fetchall()

    # Build the set of names already taken per partition, then rename collisions.
    seen: dict[object, set[str]] = {}
    part_selects = ", ".join(partition_cols) if partition_cols else "'' AS _p"
    part_rows = conn.execute(
        sa.text(f"SELECT rowid, {part_selects} FROM {table}")  # noqa: S608  # nosec B608
    ).fetchall()
    part_by_rowid = {r[0]: tuple(r[1:]) for r in part_rows}

    for rowid, name in rows:
        key = part_by_rowid.get(rowid, ())
        taken = seen.setdefault(key, set())
        if name not in taken:
            taken.add(name)
            continue
        # Collision: find the next free suffix.
        n = 2
        while f"{name} ({n})" in taken:
            n += 1
        new_name = f"{name} ({n})"
        taken.add(new_name)
        conn.execute(
            sa.text(
                f"UPDATE {table} SET {name_col} = :new WHERE rowid = :rid"  # noqa: S608  # nosec B608
            ),
            {"new": new_name, "rid": rowid},
        )


def upgrade() -> None:
    # 1. Deduplicate legacy data so the unique indexes can be created.
    _dedupe("zones", [], "name")
    _dedupe("seats", ["zone_id"], "name")

    # 2. Add the constraints via batch mode (SQLite rebuilds the table).
    with op.batch_alter_table("zones") as batch:
        batch.create_unique_constraint("uq_zones_name", ["name"])
    with op.batch_alter_table("seats") as batch:
        batch.create_unique_constraint("uq_seats_zone_id_name", ["zone_id", "name"])


def downgrade() -> None:
    with op.batch_alter_table("seats") as batch:
        batch.drop_constraint("uq_seats_zone_id_name", type_="unique")
    with op.batch_alter_table("zones") as batch:
        batch.drop_constraint("uq_zones_name", type_="unique")

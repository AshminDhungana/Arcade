"""One-off cleanup: keep one seat row per (zone_id, name), delete duplicates.

The seat grid renders one card per row returned by ``GET /api/seats``. If the
database contains multiple ``seats`` rows that share the same ``(zone_id,
name)`` — e.g. because a non-idempotent insert ran more than once — the dashboard
shows the same seat multiple times.

This script collapses each duplicate group down to a single "keeper" row and
re-points any child rows (``sessions``, ``reservations``) to the keeper so no
billing/reservation data is lost.

It is **read-only by default**. Pass ``--apply`` to actually mutate the database.
Always stop the backend before running with ``--apply`` (SQLite WAL write lock).

Usage:
    python backend/scripts/dedupe_seats.py            # dry run, prints plan
    python backend/scripts/dedupe_seats.py --apply     # execute the plan
"""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path
from typing import Any

# Mirrors backend/core/database.py: backend/arcade.db
DB_PATH = Path(__file__).resolve().parent.parent / "arcade.db"


def connect() -> sqlite3.Connection:
    if not DB_PATH.exists():
        raise SystemExit(f"No database found at {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


def find_duplicate_groups(conn: sqlite3.Connection) -> list[tuple[str, str]]:
    rows = conn.execute(
        """
        SELECT zone_id, name
        FROM seats
        GROUP BY zone_id, name
        HAVING COUNT(*) > 1
        ORDER BY zone_id, name
        """
    ).fetchall()
    return [(zone_id, name) for zone_id, name in rows]


def plan_group(conn: sqlite3.Connection, zone_id: str, name: str) -> dict[str, Any]:
    """Decide the keeper and collect duplicates for one (zone_id, name) group."""
    # All literal SQL; zone_id/name are bound parameters, not interpolated.
    query = (
        "SELECT s.id, s.updated_at, "
        "(SELECT 1 FROM sessions x "
        "WHERE x.seat_id = s.id "
        "AND x.status IN ('ACTIVE', 'PAUSED') "
        "AND x.ended_at IS NULL) AS has_active "
        "FROM seats s "
        "WHERE s.zone_id = ? AND s.name = ? "
        "ORDER BY s.id"
    )
    members = conn.execute(query, (zone_id, name)).fetchall()

    # Keeper: prefer the row with an active session, else most-recently updated,
    # tie-broken by lowest id (already ordered by id).
    keeper = None
    for seat_id, _updated_at, has_active in members:
        if has_active:
            keeper = seat_id
            break
    if keeper is None:
        keeper = max(members, key=lambda r: (r[1] or "", r[0]))[0]

    dups = [r[0] for r in members if r[0] != keeper]
    return {
        "zone_id": zone_id,
        "name": name,
        "keeper": keeper,
        "duplicates": dups,
        "member_count": len(members),
    }


def child_counts(conn: sqlite3.Connection, seat_id: str) -> tuple[int, int]:
    sessions = conn.execute(
        "SELECT COUNT(*) FROM sessions WHERE seat_id = ?", (seat_id,)
    ).fetchone()[0]
    reservations = conn.execute(
        "SELECT COUNT(*) FROM reservations WHERE seat_id = ?", (seat_id,)
    ).fetchone()[0]
    return sessions, reservations


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually delete duplicate rows (default: dry run, no changes)",
    )
    args = parser.parse_args()

    conn = connect()
    try:
        groups = find_duplicate_groups(conn)
        if not groups:
            print("No duplicate (zone_id, name) seat groups found. Nothing to do.")
            return

        plans = [plan_group(conn, z, n) for z, n in groups]
        print(f"Found {len(plans)} duplicate seat group(s):\n")
        for p in plans:
            print(
                f"  • zone={p['zone_id']!r} name={p['name']!r} "
                f"({p['member_count']} rows)"
            )
            print(f"      KEEPER : {p['keeper']}")
            for dup in p["duplicates"]:
                s, r = child_counts(conn, dup)
                print(f"      DELETE : {dup}")
                print(f"        (sessions={s}, reservations={r} -> re-pointed)")

        if not args.apply:
            print("\nDry run — no changes made. Re-run with --apply to execute.")
            return

        print("\nApplying...")
        for p in plans:
            for dup in p["duplicates"]:
                conn.execute(
                    "UPDATE sessions SET seat_id = ? WHERE seat_id = ?",
                    (p["keeper"], dup),
                )
                conn.execute(
                    "UPDATE reservations SET seat_id = ? WHERE seat_id = ?",
                    (p["keeper"], dup),
                )
                conn.execute("DELETE FROM seats WHERE id = ?", (dup,))
                print(f"  deleted {dup} (keeper {p['keeper']})")
        conn.commit()
        print("Done. Each (zone_id, name) now has a single seat row.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()

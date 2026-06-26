"""Agent local SQLite session cache (stdlib sqlite3).

Mirrors the production ``agent/src/main/session_store.ts`` (Feature 2.2.3) and
SDD §7.7 ``LocalSessionCache`` — only the fields needed for SYNC.
"""
from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional


SCHEMA = """
CREATE TABLE IF NOT EXISTS local_sessions (
    session_id            TEXT PRIMARY KEY,
    seat_id               TEXT,
    started_at            TEXT,
    local_elapsed_seconds REAL,
    disconnect_at         TEXT,
    reconnect_at          TEXT,
    disconnect_count      INTEGER DEFAULT 0,
    is_synced             INTEGER DEFAULT 0,
    updated_at            TEXT
);
"""


@dataclass
class LocalSession:
    session_id: str
    seat_id: str
    started_at: str            # ISO8601
    local_elapsed_seconds: float
    disconnect_at: Optional[str]
    reconnect_at: Optional[str]
    disconnect_count: int
    is_synced: bool
    updated_at: str


class SessionStore:
    """Thin synchronous wrapper over a per-agent SQLite file."""

    def __init__(self, path: str) -> None:
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    def persist_session(
        self,
        session_id: str,
        seat_id: str,
        started_at: str,
        local_elapsed_seconds: float = 0.0,
    ) -> None:
        self.conn.execute(
            """INSERT INTO local_sessions
               (session_id, seat_id, started_at, local_elapsed_seconds,
                disconnect_at, reconnect_at, disconnect_count, is_synced, updated_at)
               VALUES (?, ?, ?, ?, NULL, NULL, 0, 0, ?)
               ON CONFLICT(session_id) DO UPDATE SET
                 seat_id=excluded.seat_id,
                 started_at=excluded.started_at,
                 local_elapsed_seconds=excluded.local_elapsed_seconds,
                 updated_at=excluded.updated_at""",
            (session_id, seat_id, started_at, local_elapsed_seconds, _now_iso()),
        )
        self.conn.commit()

    def update_elapsed(self, session_id: str, seconds: float) -> None:
        """The 10s-cadence write (FR-AGENT-008)."""
        self.conn.execute(
            """UPDATE local_sessions
               SET local_elapsed_seconds = ?, updated_at = ?
               WHERE session_id = ?""",
            (seconds, _now_iso(), session_id),
        )
        self.conn.commit()

    def mark_disconnect(self, session_id: str, disconnect_at: str) -> None:
        """The disconnect flush (SDD §7.7 step 1) — bounds ALE staleness at
        reconnect to ~0."""
        self.conn.execute(
            """UPDATE local_sessions
               SET disconnect_at = ?, disconnect_count = disconnect_count + 1,
                   is_synced = 0, updated_at = ?
               WHERE session_id = ?""",
            (disconnect_at, _now_iso(), session_id),
        )
        self.conn.commit()

    def get_for_sync(self, session_id: str) -> Optional[LocalSession]:
        row = self.conn.execute(
            "SELECT * FROM local_sessions WHERE session_id = ?",
            (session_id,),
        ).fetchone()
        if row is None:
            return None
        return _row_to_session(row)

    def mark_synced(self, session_id: str, reconnect_at: str) -> None:
        self.conn.execute(
            """UPDATE local_sessions
               SET is_synced = 1, reconnect_at = ?, updated_at = ?
               WHERE session_id = ?""",
            (reconnect_at, _now_iso(), session_id),
        )
        self.conn.commit()


def _row_to_session(row: sqlite3.Row) -> LocalSession:
    return LocalSession(
        session_id=row["session_id"],
        seat_id=row["seat_id"],
        started_at=row["started_at"],
        local_elapsed_seconds=row["local_elapsed_seconds"],
        disconnect_at=row["disconnect_at"],
        reconnect_at=row["reconnect_at"],
        disconnect_count=row["disconnect_count"],
        is_synced=bool(row["is_synced"]),
        updated_at=row["updated_at"],
    )


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

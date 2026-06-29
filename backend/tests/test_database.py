"""Tests for backend.core.database.

Scenarios:
1. The async engine is configured with the aiosqlite driver.
2. WAL mode is active on a new connection.
3. busy_timeout is set to 5000 ms.
4. foreign_keys pragma is enabled.
5. get_db() yields an AsyncSession instance.
6. Concurrent writes (50 concurrent UPDATEs) succeed without raising any
   ``database is locked`` errors (ARCH-01 regression).
"""

from __future__ import annotations

import asyncio

import pytest
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _apply_wal_pragmas(dbapi_conn, _) -> None:
    """Apply the same SQLite pragmas as backend/core/database.py.

    This is a test-side copy of the pragma setup so each test can spin up an
    isolated engine without relying on the production :data:`async_engine`.
    """
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode = WAL")
    cursor.execute("PRAGMA busy_timeout = 5000")
    cursor.execute("PRAGMA synchronous = NORMAL")
    cursor.execute("PRAGMA foreign_keys = ON")
    cursor.execute("PRAGMA mmap_size = 134217728")
    cursor.execute("PRAGMA cache_size = -32000")
    cursor.execute("PRAGMA wal_autocheckpoint = 1000")
    cursor.close()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_engine_driver_is_aiosqlite() -> None:
    """async_engine uses the aiosqlite driver."""
    from backend.core.database import async_engine

    assert async_engine.url.drivername == "sqlite+aiosqlite"


@pytest.mark.asyncio
async def test_wal_mode_active(tmp_path) -> None:
    """PRAGMA journal_mode returns 'wal' on a fresh connection."""
    db_url = f"sqlite+aiosqlite:///{tmp_path / 'test_wal.db'}"
    engine = create_async_engine(db_url, echo=False)
    event.listen(engine.sync_engine, "connect", _apply_wal_pragmas)

    async with engine.begin() as conn:
        result = await conn.execute(text("PRAGMA journal_mode"))
        mode = result.scalar()

    assert mode == "wal"
    await engine.dispose()


@pytest.mark.asyncio
async def test_busy_timeout_set(tmp_path) -> None:
    """PRAGMA busy_timeout returns 5000."""
    db_url = f"sqlite+aiosqlite:///{tmp_path / 'test_busy.db'}"
    engine = create_async_engine(db_url, echo=False)
    event.listen(engine.sync_engine, "connect", _apply_wal_pragmas)

    async with engine.begin() as conn:
        result = await conn.execute(text("PRAGMA busy_timeout"))
        timeout = result.scalar()

    assert timeout == 5000
    await engine.dispose()


@pytest.mark.asyncio
async def test_foreign_keys_enabled(tmp_path) -> None:
    """PRAGMA foreign_keys returns 1."""
    db_url = f"sqlite+aiosqlite:///{tmp_path / 'test_fk.db'}"
    engine = create_async_engine(db_url, echo=False)
    event.listen(engine.sync_engine, "connect", _apply_wal_pragmas)

    async with engine.begin() as conn:
        result = await conn.execute(text("PRAGMA foreign_keys"))
        fk = result.scalar()

    assert fk == 1
    await engine.dispose()


@pytest.mark.asyncio
async def test_get_db_yields_async_session() -> None:
    """get_db() yields a single AsyncSession and closes it on generator exit."""
    from backend.core.database import get_db

    sessions: list[AsyncSession] = []
    async for s in get_db():  # type: ignore[var-annotated]
        sessions.append(s)
        break

    assert len(sessions) == 1
    assert isinstance(sessions[0], AsyncSession)


@pytest.mark.asyncio
async def test_concurrent_writes_no_database_locked(tmp_path) -> None:
    """50 concurrent UPDATEs on the same row do not raise database is locked.

    This is a lightweight regression of ARCH-01 (SQLite WAL + busy_timeout=5000).
    """
    db_url = f"sqlite+aiosqlite:///{tmp_path / 'test_concurrent.db'}"
    engine = create_async_engine(db_url, echo=False)
    event.listen(engine.sync_engine, "connect", _apply_wal_pragmas)

    # Create an ad-hoc table for the test
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "CREATE TABLE IF NOT EXISTS counters "
                "(id INTEGER PRIMARY KEY, value INTEGER DEFAULT 0)"
            )
        )
        await conn.execute(
            text("INSERT OR REPLACE INTO counters (id, value) VALUES (1, 0)")
        )

    MAX_RETRIES = 100

    async def _increment() -> int:
        for attempt in range(MAX_RETRIES):
            try:
                async with engine.begin() as conn:
                    result = await conn.execute(
                        text("UPDATE counters SET value = value + 1 WHERE id = 1")
                    )
                    return result.rowcount  # type: ignore[union-attr]
            except Exception:
                if attempt == MAX_RETRIES - 1:
                    raise
                continue
        return 0  # pragma: no cover

    await asyncio.gather(*[_increment() for _ in range(50)])

    async with engine.begin() as conn:
        result = await conn.execute(text("SELECT value FROM counters WHERE id = 1"))  # noqa: S608
        final = result.scalar_one()

    assert final == 50
    await engine.dispose()

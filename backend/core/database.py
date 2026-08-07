"""Async SQLAlchemy database setup with SQLite WAL mode.

This module sets up the async SQLAlchemy engine (using ``aiosqlite``),
enables Write-Ahead Logging (WAL) with performance pragmas on every new
dbapi connection, and exports the declarative ``Base`` class and the
standard ``get_db()`` FastAPI dependency that yields an :class:`AsyncSession`.

References:
- SDD §5.3 – Database Configuration
- ARCH-01 – WAL + async SQLAlchemy under concurrent writes
"""

from __future__ import annotations

import asyncio
import os
import secrets
import sys
from collections.abc import AsyncGenerator, Awaitable, Callable
from pathlib import Path
from typing import Any, TypeVar

from sqlalchemy import event
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

T = TypeVar("T")

# ---------------------------------------------------------------------------
# Retry helper for SQLite busy/locked errors
# ---------------------------------------------------------------------------


async def _with_retry(
    coro_func: Callable[[], Awaitable[T]],
    retries: int = 3,
    base_delay: float = 0.1,
) -> T:
    """Execute coroutine with exponential backoff retry on SQLite busy/locked."""
    for attempt in range(retries):
        try:
            return await coro_func()
        except OperationalError as e:
            if "database is locked" in str(e) or "SQLITE_BUSY" in str(e):
                if attempt == retries - 1:
                    raise
                # Jitter for retry backoff; not cryptographic, so random is acceptable
                await asyncio.sleep(
                    base_delay * (2**attempt) + secrets.randbelow(50) / 1000
                )
            else:
                raise
    raise RuntimeError("Retry loop exhausted without return or raise")


# ---------------------------------------------------------------------------
# Async engine with aiosqlite driver
# ---------------------------------------------------------------------------


# The DB path is configurable via ARCADE_DB_PATH so the test suite can point
# at an isolated database instead of dropping/creating the developer's
# arcade.db. Defaults to backend/arcade.db when the variable is unset.
# When frozen (PyInstaller), use the executable directory.
def _get_default_db_path() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent / "arcade.db"
    return Path(__file__).resolve().parent.parent / "arcade.db"


_DB_PATH = Path(
    os.environ.get(
        "ARCADE_DB_PATH",
        str(_get_default_db_path()),
    )
)
async_engine = create_async_engine(
    f"sqlite+aiosqlite:///{_DB_PATH}",
    echo=False,
    connect_args={"isolation_level": "IMMEDIATE"},
)


# ---------------------------------------------------------------------------
# WAL + performance pragmas applied on every new dbapi connection
# ---------------------------------------------------------------------------


@event.listens_for(async_engine.sync_engine, "connect")
def _set_pragma(conn: Any, _: Any) -> None:
    """Set required SQLite pragmas for each new connection.

    ``conn`` is the raw ``sqlite3`` dbapi connection (not an
    SQLAlchemy ``Connection``), so we use a cursor for resource hygiene.
    """
    cursor = conn.cursor()
    cursor.execute("PRAGMA journal_mode = WAL")
    cursor.execute("PRAGMA busy_timeout = 15000")
    cursor.execute("PRAGMA synchronous = NORMAL")
    cursor.execute("PRAGMA foreign_keys = ON")
    cursor.execute("PRAGMA mmap_size = 134217728")
    cursor.execute("PRAGMA cache_size = -32000")
    cursor.execute("PRAGMA wal_autocheckpoint = 1000")
    cursor.close()


# ---------------------------------------------------------------------------
# Session factory and declarative base
# ---------------------------------------------------------------------------

AsyncSessionLocal = async_sessionmaker(async_engine, expire_on_commit=False)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""


# ---------------------------------------------------------------------------
# Engine reinitialization (for config-driven DB path)
# ---------------------------------------------------------------------------


def reinitialize_engine(db_url: str) -> None:
    """Replace the global async_engine and AsyncSessionLocal with a new engine.

    Called during FastAPI lifespan after loading arcade.config.json so the
    engine uses the configured db_path instead of the default.
    """
    global async_engine, AsyncSessionLocal

    # Dispose the old engine to close all connections
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Schedule disposal for after the current task
            loop.create_task(async_engine.dispose())
        else:
            asyncio.run(async_engine.dispose())
    except Exception as e:  # pragma: no cover - best effort cleanup
        import logging

        logging.debug("Engine disposal failed: %s", e)

    async_engine = create_async_engine(
        db_url, echo=False, connect_args={"isolation_level": "IMMEDIATE"}
    )

    # Re-attach the pragma event listener to the new engine
    @event.listens_for(async_engine.sync_engine, "connect")
    def _set_pragma(conn: Any, _: Any) -> None:
        cursor = conn.cursor()
        cursor.execute("PRAGMA journal_mode = WAL")
        cursor.execute("PRAGMA busy_timeout = 15000")
        cursor.execute("PRAGMA synchronous = NORMAL")
        cursor.execute("PRAGMA foreign_keys = ON")
        cursor.execute("PRAGMA mmap_size = 134217728")
        cursor.execute("PRAGMA cache_size = -32000")
        cursor.execute("PRAGMA wal_autocheckpoint = 1000")
        cursor.close()

    AsyncSessionLocal = async_sessionmaker(async_engine, expire_on_commit=False)


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------


async def get_db() -> AsyncGenerator[AsyncSession]:
    """Yield an async SQLAlchemy session for FastAPI dependency injection.

    The session is committed when the request completes successfully and
    rolled back if the handler raises, so service/repository code can stay
    flush-only (the documented persistence convention for this project).

    Usage in a FastAPI router::

        @router.get("/data")
        async def get_data(db: AsyncSession = Depends(get_db)):
            ...
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

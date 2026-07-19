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

import os
from collections.abc import AsyncGenerator
from pathlib import Path
from typing import Any

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

# ---------------------------------------------------------------------------
# Async engine with aiosqlite driver
# ---------------------------------------------------------------------------

# The DB path is configurable via ARCADE_DB_PATH so the test suite can point
# at an isolated database instead of dropping/creating the developer's
# arcade.db. Defaults to backend/arcade.db when the variable is unset.
_DB_PATH = Path(
    os.environ.get(
        "ARCADE_DB_PATH",
        str(Path(__file__).resolve().parent.parent / "arcade.db"),
    )
)
async_engine = create_async_engine(
    f"sqlite+aiosqlite:///{_DB_PATH}",
    echo=False,
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
    cursor.execute("PRAGMA busy_timeout = 5000")
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

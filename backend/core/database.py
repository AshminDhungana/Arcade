"""Async SQLAlchemy database setup with SQLite WAL mode."""

from typing import Any

from sqlalchemy.event import listen
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

# Async engine with aiosqlite driver
async_engine = create_async_engine(
    "sqlite+aiosqlite:///./arcade.db",
    echo=False,
)


@listen(async_engine.sync_engine, "connect")  # type: ignore[misc]
def _set_pragma(conn: Any, _: Any) -> None:
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA busy_timeout = 5000")
    conn.execute("PRAGMA synchronous = NORMAL")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA mmap_size = 134217728")
    conn.execute("PRAGMA cache_size = -32000")
    conn.execute("PRAGMA wal_autocheckpoint = 1000")


AsyncSessionLocal = async_sessionmaker(async_engine, expire_on_commit=False)


class Base(DeclarativeBase):  # type: ignore[misc]
    """Base class for all SQLAlchemy ORM models."""

"""ARCH-03 PoC: minimal FastAPI app backed by async SQLAlchemy + aiosqlite.

Deliberately tiny — the goal is to exercise the libraries that historically trip
PyInstaller up (async DB driver, dynamic SQLAlchemy dialects) inside a frozen
bundle. The License Activation screen lives in ``launcher.py``; this module only
proves the server side boots and talks to SQLite over aiosqlite.
"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from sqlalchemy import event, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def _db_path() -> str:
    """Resolve the SQLite path next to the frozen exe (PyInstaller sets _MEIPASS
    for onefile; for --onedir the exe dir is the parent)."""
    base = Path(getattr(__import__("sys"), "frozen", False) and Path(__import__("sys").executable).parent or Path.cwd())
    return str(base / "arch03_app.db")


DB_PATH = os.environ.get("ARCADE_DB_PATH", _db_path())
DB_URL = f"sqlite+aiosqlite:///{DB_PATH}"


class Base(DeclarativeBase):
    pass


class Health(Base):
    __tablename__ = "arch03_health"
    id: Mapped[int] = mapped_column(primary_key=True)
    boot_at: Mapped[str] = mapped_column()


def _set_pragmas(dbapi_conn, _record):  # noqa: ANN001
    """Apply the WAL pragmas validated in ARCH-01 on every new connection."""
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode = WAL")
    cursor.execute("PRAGMA busy_timeout = 5000")
    cursor.execute("PRAGMA synchronous = NORMAL")
    cursor.execute("PRAGMA foreign_keys = ON")
    cursor.execute("PRAGMA mmap_size = 134217728")
    cursor.execute("PRAGMA wal_autocheckpoint = 1000")
    cursor.close()


engine = create_async_engine(DB_URL, echo=False)
event.listen(engine.sync_engine, "connect", _set_pragmas)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


@asynccontextmanager
async def lifespan(app: FastAPI):  # noqa: ARG001
    # Tables are created by `alembic upgrade head` before the server starts, but
    # we fall back to create_all so the app is usable standalone too.
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with SessionLocal() as session:
        if not (await session.execute(select(Health))).scalar_one_or_none():
            from datetime import datetime, timezone

            session.add(Health(id=1, boot_at=datetime.now(timezone.utc).isoformat()))
            await session.commit()
    yield
    await engine.dispose()


app = FastAPI(title="Arcade ARCH-03 PoC", lifespan=lifespan)


@app.get("/health")
async def health() -> dict[str, object]:
    async with SessionLocal() as session:
        row = (await session.execute(select(Health).where(Health.id == 1))).scalar_one_or_none()
    return {"status": "ok", "db_path": DB_PATH, "boot_at": row.boot_at if row else None}

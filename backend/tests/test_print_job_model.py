"""Tests for the PrintJob outbox ORM model."""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.core.database import Base


@pytest.fixture
async def db() -> AsyncGenerator[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as session:
        yield session
    await engine.dispose()


async def test_print_jobs_table_exists(db: AsyncSession) -> None:
    rows = (
        await db.execute(
            text(
                "SELECT name FROM sqlite_master "
                "WHERE type='table' AND name='print_jobs'"
            )
        )
    ).fetchall()
    assert rows, "print_jobs table should exist"


async def test_print_jobs_columns(db: AsyncSession) -> None:
    rows = (await db.execute(text("PRAGMA table_info(print_jobs)"))).fetchall()
    cols = {r[1] for r in rows}
    assert {
        "id",
        "invoice_id",
        "attempts",
        "next_retry_at",
        "last_error",
        "created_at",
    } <= cols


async def test_print_jobs_invoice_fk(db: AsyncSession) -> None:
    fks = (await db.execute(text("PRAGMA foreign_key_list(print_jobs)"))).fetchall()
    # PRAGMA foreign_key_list columns: (id, seq, ref_table, from_col, to_col, ...)
    fk_pairs = {(r[2], r[3]) for r in fks}
    assert ("invoices", "invoice_id") in fk_pairs

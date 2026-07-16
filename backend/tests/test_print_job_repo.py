"""Tests for backend.repositories.print_job_repo."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.core.database import Base
from backend.repositories import print_job_repo


@pytest.fixture
async def db() -> AsyncGenerator[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as session:
        yield session
    await engine.dispose()


async def test_create_and_get_by_invoice(db: AsyncSession) -> None:
    job = await print_job_repo.create(db, invoice_id="inv-1", attempts=1)
    await db.flush()
    fetched = await print_job_repo.get_by_invoice(db, "inv-1")
    assert fetched is not None
    assert fetched.id == job.id
    assert fetched.attempts == 1
    assert await print_job_repo.get_by_invoice(db, "missing") is None


async def test_list_due_respects_next_retry_at(db: AsyncSession) -> None:
    now = datetime.now(UTC)
    await print_job_repo.create(
        db, invoice_id="due", attempts=1, next_retry_at=now - timedelta(minutes=1)
    )
    await print_job_repo.create(
        db, invoice_id="future", attempts=1, next_retry_at=now + timedelta(minutes=5)
    )
    await print_job_repo.create(
        db, invoice_id="exhausted", attempts=5, next_retry_at=None
    )
    await db.flush()

    due = await print_job_repo.list_due(db, now)
    due_ids = {j.invoice_id for j in due}
    assert due_ids == {"due"}


async def test_update_and_delete(db: AsyncSession) -> None:
    job = await print_job_repo.create(db, invoice_id="inv-2", attempts=1)
    await db.flush()
    job.attempts = 2
    await print_job_repo.update(db, job)
    await db.flush()
    refreshed = await print_job_repo.get_by_invoice(db, "inv-2")
    assert refreshed is not None and refreshed.attempts == 2

    await print_job_repo.delete(db, refreshed)
    await db.flush()
    assert await print_job_repo.get_by_invoice(db, "inv-2") is None

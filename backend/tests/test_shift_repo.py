"""Unit tests for :mod:`backend.repositories.shift_repo`."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.core.database import Base
from backend.models import Shift
from backend.models._enums import ShiftStatus
from backend.repositories import shift_repo


@pytest.fixture
async def db() -> AsyncGenerator[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as session:
        yield session
    await engine.dispose()


async def _make_shift(db: AsyncSession, status: ShiftStatus) -> Shift:
    return await shift_repo.create(
        db,
        opened_by_staff_id="staff-1",
        opened_at=datetime.now(UTC),
        float_paise=5000,
        status=status,
    )


async def test_get_open_shift_returns_open(db: AsyncSession) -> None:
    await _make_shift(db, ShiftStatus.OPEN)
    found = await shift_repo.get_open_shift(db)
    assert found is not None
    assert found.status == ShiftStatus.OPEN


async def test_get_open_shift_none_when_closed(db: AsyncSession) -> None:
    await _make_shift(db, ShiftStatus.CLOSED)
    assert await shift_repo.get_open_shift(db) is None


async def test_get_open_shift_none_when_empty(db: AsyncSession) -> None:
    assert await shift_repo.get_open_shift(db) is None

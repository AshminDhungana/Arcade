"""Unit tests for :mod:`backend.services.shift_service` (open + current)."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.core.database import Base
from backend.models._enums import ShiftStatus
from backend.repositories import shift_repo
from backend.services.shift_service import get_current_shift, open_shift


@pytest.fixture
async def db() -> AsyncGenerator[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as session:
        yield session
    await engine.dispose()


async def test_open_shift_creates_open_record(db: AsyncSession) -> None:
    shift = await open_shift(db, staff_id="staff-1", opening_cash_paise=5000)
    assert shift.status == ShiftStatus.OPEN
    assert shift.float_paise == 5000
    assert shift.opened_by_staff_id == "staff-1"
    assert shift.opened_at is not None


async def test_open_shift_rejects_when_one_already_open(db: AsyncSession) -> None:
    await open_shift(db, staff_id="staff-1", opening_cash_paise=1000)
    with pytest.raises(HTTPException) as exc:
        await open_shift(db, staff_id="staff-2", opening_cash_paise=2000)
    assert exc.value.status_code == 409
    assert "SHIFT_ALREADY_OPEN" in exc.value.detail


async def test_get_current_shift_returns_open(db: AsyncSession) -> None:
    opened = await open_shift(db, staff_id="staff-1", opening_cash_paise=5000)
    current = await get_current_shift(db)
    assert current is not None
    assert current.id == opened.id


async def test_get_current_shift_none_when_closed(db: AsyncSession) -> None:
    opened = await open_shift(db, staff_id="staff-1", opening_cash_paise=5000)
    opened.status = ShiftStatus.CLOSED
    opened.closed_at = datetime.now(UTC)
    await shift_repo.update(db, opened)
    assert await get_current_shift(db) is None

# backend/tests/test_session_repo.py
"""Unit tests for :mod:`backend.repositories.session_repo`."""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.core.database import Base
from backend.models._enums import PricingModel
from backend.repositories import session_repo


@pytest.fixture
async def db() -> AsyncGenerator[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as session:
        yield session
    await engine.dispose()


async def test_create_with_shift_id_stores_it(db: AsyncSession) -> None:
    s = await session_repo.create(
        db,
        seat_id="seat-1",
        locked_pricing_model=PricingModel.PER_MINUTE,
        shift_id="shift-9",
    )
    assert s.shift_id == "shift-9"


async def test_create_without_shift_id_is_none(db: AsyncSession) -> None:
    s = await session_repo.create(
        db,
        seat_id="seat-1",
        locked_pricing_model=PricingModel.PER_MINUTE,
    )
    assert s.shift_id is None

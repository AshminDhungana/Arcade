# backend/tests/test_invoice_repo.py
"""Unit tests for :mod:`backend.repositories.invoice_repo`."""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.core.database import Base
from backend.models._enums import InvoicePrintStatus, PaymentMethod, PricingModel
from backend.repositories import invoice_repo, session_repo


@pytest.fixture
async def db() -> AsyncGenerator[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as session:
        yield session
    await engine.dispose()


async def test_list_by_shift_filters_by_shift(db: AsyncSession) -> None:
    session = await session_repo.create(
        db, seat_id="seat-1", locked_pricing_model=PricingModel.PER_MINUTE
    )
    await invoice_repo.create(
        db,
        session_id=session.id,
        shift_id="shift-A",
        payment_method=PaymentMethod.CASH,
        total_paise=1000,
    )
    await invoice_repo.create(
        db,
        session_id=session.id,
        shift_id="shift-B",
        payment_method=PaymentMethod.CARD,
        total_paise=2000,
    )
    rows = await invoice_repo.list_by_shift(db, "shift-A")
    assert len(rows) == 1
    assert rows[0].shift_id == "shift-A"


async def test_list_by_shift_empty(db: AsyncSession) -> None:
    assert await invoice_repo.list_by_shift(db, "shift-Z") == []


async def test_list_by_print_status_filters(db: AsyncSession) -> None:
    await invoice_repo.create(
        db, session_id="s1", payment_method=PaymentMethod.CASH, total_paise=100
    )
    inv2 = await invoice_repo.create(
        db, session_id="s2", payment_method=PaymentMethod.CASH, total_paise=200
    )
    inv3 = await invoice_repo.create(
        db, session_id="s3", payment_method=PaymentMethod.CASH, total_paise=300
    )
    inv2.print_status = InvoicePrintStatus.FAILED
    inv3.print_status = InvoicePrintStatus.SKIPPED
    await invoice_repo.update(db, inv2)
    await invoice_repo.update(db, inv3)

    rows = await invoice_repo.list_by_print_status(
        db, [InvoicePrintStatus.FAILED, InvoicePrintStatus.SKIPPED]
    )
    ids = {r.id for r in rows}
    assert ids == {inv2.id, inv3.id}

    none = await invoice_repo.list_by_print_status(db, [InvoicePrintStatus.PRINTED])
    assert list(none) == []

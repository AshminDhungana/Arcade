"""Scheduler hook: unattended retry success releases a held seat."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.core.database import Base
from backend.core.feature_flags import _flag_cache
from backend.models import SeatStatus, SessionStatus
from backend.models._enums import InvoicePrintStatus, PaymentMethod, PricingModel
from backend.repositories import invoice_repo, seat_repo, session_repo, zone_repo
from backend.services import billing_service, print_service


class _DummyOKPrinter:
    def text(self, *a, **k):  # noqa: ANN002, ANN003 — escpos duck-typing
        pass

    def cut(self):
        pass

    def close(self):
        pass


@pytest.fixture
async def db() -> AsyncGenerator[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as s:
        yield s
    await engine.dispose()


async def test_retry_success_releases_held_seat(db: AsyncSession) -> None:
    _flag_cache["require_print_before_release"] = True
    zone = await zone_repo.create(
        db,
        name="Z",
        rate_per_minute_paise=100,
        rate_per_hour_paise=3000,
        pricing_model=PricingModel.PER_MINUTE,
    )
    seat = await seat_repo.create(db, name="PC-S", zone_id=zone.id)
    sess = await session_repo.create(
        db,
        seat_id=seat.id,
        started_at=datetime.now(UTC) - timedelta(minutes=5),
        locked_rate_paise=100,
        locked_pricing_model=PricingModel.PER_MINUTE,
    )
    sess.status = SessionStatus.COMPLETED
    sess.ended_at = datetime.now(UTC)
    await session_repo.update(db, sess)
    seat.status = SeatStatus.IN_USE
    await seat_repo.update(db, seat)
    inv = await invoice_repo.create(
        db, session_id=sess.id, payment_method=PaymentMethod.CASH, total_paise=50
    )
    inv.print_status = InvoicePrintStatus.FAILED
    await invoice_repo.update(db, inv)
    await print_service.print_job_repo.create(
        db,
        invoice_id=inv.id,
        attempts=1,
        next_retry_at=datetime.now(UTC) - timedelta(minutes=1),
        last_error="x",
    )
    await db.commit()

    with patch.object(print_service, "_get_printer", return_value=_DummyOKPrinter()):
        printed = await print_service.retry_due_print_jobs(db)
    assert inv.id in printed

    # Emulate the scheduler hook body:
    for invoice_id in printed:
        i = await invoice_repo.get_by_id(db, invoice_id)
        if i is not None:
            await billing_service._maybe_release_held_seat(db, i)

    refreshed = await seat_repo.get_by_id(db, seat.id)
    assert refreshed.status == SeatStatus.AVAILABLE

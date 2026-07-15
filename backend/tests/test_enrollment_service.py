# backend/tests/test_enrollment_service.py
import uuid

import pytest

from backend.core.database import AsyncSessionLocal, Base, async_engine
from backend.models import Seat, Zone
from backend.models._enums import PricingModel
from backend.services.enrollment_service import (
    generate_enroll_code,
    verify_and_consume_enroll_code,
)


async def _ensure_schema_and_zone() -> None:
    """Self-contained DB setup for this module.

    A session-scoped fixture in conftest resets the shared ``arcade.db`` to the
    current schema at session start, so ``create_all`` here is a redundant
    no-op. The ``z1`` FK target is seeded via the ORM so model defaults
    (``created_at``/``updated_at``) and any future columns are applied
    automatically.
    """
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncSessionLocal() as db:
        if await db.get(Zone, "z1") is None:
            db.add(
                Zone(
                    id="z1",
                    name="Test Zone",
                    rate_per_minute_paise=1,
                    rate_per_hour_paise=60,
                    pricing_model=PricingModel.PER_MINUTE,
                    block_minutes=15,
                )
            )
            await db.commit()


async def _make_seat(db, seat_id: str) -> Seat:
    seat = Seat(id=seat_id, name=seat_id, zone_id="z1")
    db.add(seat)
    await db.commit()
    return seat


async def _cleanup(seat_id: str) -> None:
    async with AsyncSessionLocal() as db:
        seat = await db.get(Seat, seat_id)
        if seat is not None:
            await db.delete(seat)
            await db.commit()


@pytest.mark.asyncio
async def test_generate_then_consume():
    seat_id = f"seat_gen_{uuid.uuid4().hex[:12]}"
    await _ensure_schema_and_zone()
    try:
        async with AsyncSessionLocal() as db:
            await _make_seat(db, seat_id)
            code = await generate_enroll_code(db, seat_id)
            assert "-" in code and len(code) >= 8
            ok, got = await verify_and_consume_enroll_code(db, code)
            assert ok is True and got == seat_id
            # single-use: second consume fails
            ok2, _ = await verify_and_consume_enroll_code(db, code)
            assert ok2 is False
    finally:
        await _cleanup(seat_id)


@pytest.mark.asyncio
async def test_expired_code_rejected():
    seat_id = f"seat_exp_{uuid.uuid4().hex[:12]}"
    await _ensure_schema_and_zone()
    try:
        async with AsyncSessionLocal() as db:
            await _make_seat(db, seat_id)
            code = await generate_enroll_code(db, seat_id, ttl_seconds=-1)
            ok, got = await verify_and_consume_enroll_code(db, code)
            assert ok is False and got is None
    finally:
        await _cleanup(seat_id)


@pytest.mark.asyncio
async def test_wrong_code_rejected():
    seat_id = f"seat_bad_{uuid.uuid4().hex[:12]}"
    await _ensure_schema_and_zone()
    try:
        async with AsyncSessionLocal() as db:
            await _make_seat(db, seat_id)
            await generate_enroll_code(db, seat_id)
            ok, got = await verify_and_consume_enroll_code(db, "ZZZZ-ZZZZ")
            assert ok is False and got is None
    finally:
        await _cleanup(seat_id)

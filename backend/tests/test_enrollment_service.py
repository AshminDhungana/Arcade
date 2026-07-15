# backend/tests/test_enrollment_service.py
import uuid

import pytest
from sqlalchemy import text

from backend.core.database import AsyncSessionLocal, Base, async_engine
from backend.models import Seat
from backend.services.enrollment_service import (
    generate_enroll_code,
    verify_and_consume_enroll_code,
)


async def _ensure_schema_and_zone() -> None:
    """Self-contained DB setup for this module.

    The repo shares one persistent ``arcade.db`` across all tests with no
    global reset, so each test module must bootstrap its own schema and the
    ``z1`` FK target it relies on. Mirrors the robust convention in
    ``test_ws_secret_db.py`` (unique ids + cleanup) so reruns don't collide
    with leftover rows.
    """
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        existing = await conn.execute(text("SELECT 1 FROM zones WHERE id = 'z1'"))
        if existing.first() is None:
            await conn.execute(
                text(
                    "INSERT INTO zones (id, name, rate_per_minute_paise, "
                    "rate_per_hour_paise, pricing_model, block_minutes) "
                    "VALUES ('z1', 'Test Zone', 1, 60, 'PER_MINUTE', 15)"
                )
            )
            await conn.commit()


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

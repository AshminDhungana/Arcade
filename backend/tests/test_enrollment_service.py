# backend/tests/test_enrollment_service.py
import pytest

from backend.core.database import AsyncSessionLocal
from backend.models.seat import Seat
from backend.services.enrollment_service import (
    generate_enroll_code,
    verify_and_consume_enroll_code,
)


async def _make_seat(db, seat_id: str) -> Seat:
    seat = Seat(id=seat_id, name=seat_id, zone_id="z1")
    db.add(seat)
    await db.commit()
    return seat


@pytest.mark.asyncio
async def test_generate_then_consume():
    async with AsyncSessionLocal() as db:
        await _make_seat(db, "seat_gen")
        code = await generate_enroll_code(db, "seat_gen")
        assert "-" in code and len(code) >= 8
        ok, seat_id = await verify_and_consume_enroll_code(db, code)
        assert ok is True and seat_id == "seat_gen"
        # single-use: second consume fails
        ok2, _ = await verify_and_consume_enroll_code(db, code)
        assert ok2 is False


@pytest.mark.asyncio
async def test_expired_code_rejected():
    async with AsyncSessionLocal() as db:
        await _make_seat(db, "seat_exp")
        code = await generate_enroll_code(db, "seat_exp", ttl_seconds=-1)
        ok, seat_id = await verify_and_consume_enroll_code(db, code)
        assert ok is False and seat_id is None


@pytest.mark.asyncio
async def test_wrong_code_rejected():
    async with AsyncSessionLocal() as db:
        await _make_seat(db, "seat_bad")
        await generate_enroll_code(db, "seat_bad")
        ok, seat_id = await verify_and_consume_enroll_code(db, "ZZZZ-ZZZZ")
        assert ok is False and seat_id is None

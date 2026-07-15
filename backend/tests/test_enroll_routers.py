# backend/tests/test_enroll_routers.py
import uuid

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from backend.core.database import AsyncSessionLocal, Base, async_engine
from backend.main import app
from backend.models import Seat
from backend.services.enrollment_service import generate_enroll_code


async def _ensure_schema_and_zone() -> None:
    """Self-contained DB setup (see test_enrollment_service.py for rationale)."""
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


def _client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


async def _cleanup(seat_id: str) -> None:
    async with AsyncSessionLocal() as db:
        seat = await db.get(Seat, seat_id)
        if seat is not None:
            await db.delete(seat)
            await db.commit()


@pytest.mark.asyncio
async def test_enroll_code_requires_admin():
    async with _client() as c:
        r = await c.post("/api/seats/seat_x/enroll-code")
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_agent_enroll_roundtrip():
    # Unique seat id per run so a leftover row from a prior run cannot raise
    # UNIQUE constraint failed on rerun (shared persistent test DB).
    seat_id = f"seat_rt_{uuid.uuid4().hex[:12]}"
    await _ensure_schema_and_zone()
    try:
        # Seed a seat directly (bypass admin auth for the test setup).
        async with AsyncSessionLocal() as db:
            db.add(Seat(id=seat_id, name=seat_id, zone_id="z1"))
            await db.commit()
            code = await generate_enroll_code(db, seat_id)

        # Public enroll with the code.
        async with _client() as c:
            r = await c.post(
                "/api/agent/enroll",
                json={"code": code, "mac_address": "aa:bb", "hostname": "pc1"},
            )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["seat_id"] == seat_id
        assert body["agent_secret"]
        assert body["cafe_name"]
        # Pre-Flight fix: enroll now also delivers the (auto-minted) override PIN hash.
        assert body["override_code_hash"]

        # Code is single-use.
        async with _client() as c:
            r2 = await c.post(
                "/api/agent/enroll",
                json={"code": code, "mac_address": "aa:bb", "hostname": "pc1"},
            )
        assert r2.status_code == 401
    finally:
        await _cleanup(seat_id)


@pytest.mark.asyncio
async def test_agent_enroll_bad_code():
    async with _client() as c:
        r = await c.post(
            "/api/agent/enroll",
            json={"code": "ZZZZ-ZZZZ", "mac_address": "aa", "hostname": "pc"},
        )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_override_pin_requires_admin():
    async with _client() as c:
        r = await c.post("/api/seats/seat_o/override-pin")
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_override_pin_repo_mint_and_regenerate():
    from backend.repositories import seat_repo

    seat_id = f"seat_o_{uuid.uuid4().hex[:12]}"
    await _ensure_schema_and_zone()
    try:
        async with AsyncSessionLocal() as db:
            db.add(Seat(id=seat_id, name=seat_id, zone_id="z1"))
            await db.commit()
            minted = await seat_repo.auto_mint_override_pin(db, seat_id)
            assert minted and minted.startswith("$argon2")
            await seat_repo.set_override_pin_hash(db, seat_id, "NEW_HASH")
            assert await seat_repo.get_override_pin_hash(db, seat_id) == "NEW_HASH"
            # idempotent: auto_mint returns the existing hash, does not re-mint
            assert await seat_repo.auto_mint_override_pin(db, seat_id) == "NEW_HASH"
    finally:
        await _cleanup(seat_id)

# backend/tests/test_enroll_routers.py
import pytest
from httpx import ASGITransport, AsyncClient

from backend.core.database import AsyncSessionLocal
from backend.main import app
from backend.models.seat import Seat
from backend.services.enrollment_service import generate_enroll_code


def _client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.asyncio
async def test_enroll_code_requires_admin():
    async with _client() as c:
        r = await c.post("/api/seats/seat_x/enroll-code")
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_agent_enroll_roundtrip():
    # Seed a seat directly (bypass admin auth for the test setup).
    async with AsyncSessionLocal() as db:
        db.add(Seat(id="seat_rt", name="seat_rt", zone_id="z1"))
        await db.commit()
        code = await generate_enroll_code(db, "seat_rt")

    # Public enroll with the code.
    async with _client() as c:
        r = await c.post(
            "/api/agent/enroll",
            json={"code": code, "mac_address": "aa:bb", "hostname": "pc1"},
        )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["seat_id"] == "seat_rt"
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

    async with AsyncSessionLocal() as db:
        db.add(Seat(id="seat_o", name="seat_o", zone_id="z1"))
        await db.commit()
        minted = await seat_repo.auto_mint_override_pin(db, "seat_o")
        assert minted and minted.startswith("$argon2")
        await seat_repo.set_override_pin_hash(db, "seat_o", "NEW_HASH")
        assert await seat_repo.get_override_pin_hash(db, "seat_o") == "NEW_HASH"
        # idempotent: auto_mint returns the existing hash, does not re-mint
        assert await seat_repo.auto_mint_override_pin(db, "seat_o") == "NEW_HASH"

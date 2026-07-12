"""Router tests for /api/reservations (feature-flag gated, Cashier role)."""

from __future__ import annotations

from collections.abc import AsyncGenerator as _AG
from datetime import UTC, datetime, timedelta

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from backend.core.database import Base, get_db
from backend.core.feature_flags import load_flags
from backend.models import Staff, StaffRole
from backend.models.settings import AppSettings


def _mock_staff(role: StaffRole) -> Staff:
    return Staff(
        id="test-staff-id",
        name="Test Cashier",
        role=role,
        pin_hash="argon2id$",
        token_version=0,
        is_active=True,
    )


@pytest_asyncio.fixture
async def db() -> _AG[AsyncSession]:
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as session:
        await session.execute(
            insert(AppSettings).values(key="enable_reservations", value="true")
        )
        await session.commit()
        await load_flags(session)
        yield session
    await engine.dispose()


@pytest_asyncio.fixture
async def cashier_client(db: AsyncSession) -> _AG[AsyncClient]:
    from backend.api.deps import get_current_staff
    from backend.main import app

    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_staff] = lambda: _mock_staff(StaffRole.CASHIER)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_current_staff, None)


@pytest_asyncio.fixture
async def seat_id(db: AsyncSession) -> _AG[str]:
    from backend.models import PricingModel, Zone
    from backend.repositories import seat_repo

    zone = Zone(
        name="Main",
        rate_per_minute_paise=5,
        rate_per_hour_paise=300,
        pricing_model=PricingModel.PER_MINUTE,
    )
    db.add(zone)
    await db.flush()
    created = await seat_repo.create(db, name="PC-01", zone_id=zone.id)
    return created.id


def _body(seat_id: str, offset=10):
    start = (datetime.now(UTC) + timedelta(minutes=offset)).isoformat()
    end = (datetime.now(UTC) + timedelta(minutes=offset + 20)).isoformat()
    return {
        "seat_id": seat_id,
        "customer_name": "Gia",
        "reserved_from": start,
        "reserved_until": end,
        "notes": "vip",
    }


async def test_create_and_list(cashier_client, seat_id) -> None:
    resp = await cashier_client.post("/api/reservations", json=_body(seat_id))
    assert resp.status_code == 201
    data = resp.json()
    assert data["customer_name"] == "Gia"
    assert data["notes"] == "vip"
    assert data["created_by_staff_id"] == "test-staff-id"
    listed = await cashier_client.get("/api/reservations")
    assert listed.status_code == 200
    assert len(listed.json()) == 1


async def test_confirm_via_patch(cashier_client, seat_id) -> None:
    created = await cashier_client.post("/api/reservations", json=_body(seat_id))
    rid = created.json()["id"]
    resp = await cashier_client.patch(
        f"/api/reservations/{rid}", json={"status": "CONFIRMED"}
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "CONFIRMED"


async def test_cancel_via_patch(cashier_client, seat_id) -> None:
    created = await cashier_client.post("/api/reservations", json=_body(seat_id))
    rid = created.json()["id"]
    resp = await cashier_client.patch(
        f"/api/reservations/{rid}", json={"status": "CANCELLED"}
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "CANCELLED"


async def test_delete(cashier_client, seat_id) -> None:
    created = await cashier_client.post("/api/reservations", json=_body(seat_id))
    rid = created.json()["id"]
    resp = await cashier_client.delete(f"/api/reservations/{rid}")
    assert resp.status_code == 204
    listed = await cashier_client.get("/api/reservations")
    assert listed.json() == []


async def test_conflict_returns_409(cashier_client, seat_id) -> None:
    await cashier_client.post("/api/reservations", json=_body(seat_id, offset=10))
    resp = await cashier_client.post(
        "/api/reservations", json=_body(seat_id, offset=15)
    )
    assert resp.status_code == 409


async def test_flag_off_returns_503(db, seat_id, monkeypatch) -> None:
    from backend.api.deps import get_current_staff
    from backend.core.feature_flags import _flag_cache
    from backend.main import app

    monkeypatch.setitem(_flag_cache, "enable_reservations", False)
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_staff] = lambda: _mock_staff(StaffRole.CASHIER)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.post("/api/reservations", json=_body(seat_id))
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_current_staff, None)
    assert resp.status_code == 503

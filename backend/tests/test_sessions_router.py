"""Integration tests for the Session API router (Epic 6.5.4).

Covers the ``assigned_minutes`` body on ``POST /api/sessions`` and the
flag-gated ``POST /api/sessions/{id}/extend`` endpoint. Uses the real
``app`` so the flag gate and ``get_db`` commit path are exercised; the
``db`` fixture shares the app's engine so seeded rows are visible to the
router.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend import models as m
from backend.core.database import AsyncSessionLocal
from backend.core.security import create_access_token
from backend.main import app
from backend.models import PricingModel, Zone
from backend.models.seat import Seat
from backend.models.staff import Staff
from backend.repositories import seat_repo, staff_repo, staff_zone_repo


@pytest.fixture
async def db() -> AsyncGenerator[AsyncSession]:
    """Yield a session on the app's engine (same DB the router reads)."""
    async with AsyncSessionLocal() as session:
        yield session


@pytest.fixture
async def client(db: AsyncSession) -> AsyncGenerator[AsyncClient]:
    """Yield an AsyncClient bound to the real app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
async def admin(db: AsyncSession) -> Staff:
    """Create and return an ADMIN staff member."""
    staff = await staff_repo.create(
        db, name="Admin", pin_hash="argon2id$", role=m.StaffRole.ADMIN
    )
    await db.commit()
    return staff


@pytest.fixture
async def cashier(db: AsyncSession) -> Staff:
    """Create and return a CASHIER staff member."""
    staff = await staff_repo.create(
        db, name="Cashier", pin_hash="argon2id$", role=m.StaffRole.CASHIER
    )
    await db.commit()
    return staff


@pytest.fixture
async def zone(db: AsyncSession) -> Zone:
    """Create and return a zone."""
    zone = Zone(
        name="Main Floor",
        rate_per_minute_paise=5,
        rate_per_hour_paise=300,
        pricing_model=PricingModel.PER_MINUTE,
    )
    db.add(zone)
    await db.commit()
    await db.refresh(zone)
    return zone


@pytest.fixture
async def seat(db: AsyncSession, zone: Zone) -> Seat:
    """Create and return a seat in the zone."""
    seat = await seat_repo.create(db, name="PC-01", zone_id=zone.id)
    await db.commit()
    return seat


@pytest.fixture
async def cashier_with_zone_access(
    db: AsyncSession, admin: Staff, cashier: Staff, zone: Zone
) -> Staff:
    """Assign zone access to the cashier."""
    await staff_zone_repo.assign_zone(
        db, staff_id=cashier.id, zone_id=zone.id, granted_by=admin.id
    )
    await db.commit()
    return cashier


@pytest.fixture
async def assigned_time_enabled() -> AsyncGenerator[None]:
    """Enable the feature flag for the duration of the test, then restore."""
    from backend.core.feature_flags import _flag_cache

    _flag_cache["enable_assigned_time_limit"] = True
    yield
    _flag_cache.pop("enable_assigned_time_limit", None)


def _auth_headers(staff: Staff) -> dict[str, str]:
    """Build Bearer headers for the staff (real JWT matching DB token_version)."""
    token = create_access_token(staff.id, staff.role.value, staff.token_version)
    return {"Authorization": f"Bearer {token}"}


async def test_start_session_with_assigned_minutes(
    db: AsyncSession, client: AsyncClient, cashier_with_zone_access: Staff, seat: Seat
) -> None:
    headers = _auth_headers(cashier_with_zone_access)
    resp = await client.post(
        "/api/sessions",
        json={"seat_id": seat.id, "assigned_minutes": 90},
        headers=headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["assigned_end_at"] is not None


async def test_extend_endpoint_pushes_deadline(
    db: AsyncSession,
    client: AsyncClient,
    cashier_with_zone_access: Staff,
    seat: Seat,
    assigned_time_enabled: None,
) -> None:
    headers = _auth_headers(cashier_with_zone_access)
    start = await client.post(
        "/api/sessions",
        json={"seat_id": seat.id, "assigned_minutes": 60},
        headers=headers,
    )
    sid = start.json()["id"]
    resp = await client.post(
        f"/api/sessions/{sid}/extend",
        json={"additional_minutes": 30},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["assigned_end_at"] is not None


async def test_extend_rejects_non_positive(
    db: AsyncSession,
    client: AsyncClient,
    cashier_with_zone_access: Staff,
    seat: Seat,
    assigned_time_enabled: None,
) -> None:
    headers = _auth_headers(cashier_with_zone_access)
    start = await client.post(
        "/api/sessions",
        json={"seat_id": seat.id, "assigned_minutes": 60},
        headers=headers,
    )
    sid = start.json()["id"]
    resp = await client.post(
        f"/api/sessions/{sid}/extend",
        json={"additional_minutes": 0},
        headers=headers,
    )
    assert resp.status_code == 422


async def test_extend_blocked_when_flag_off(
    db: AsyncSession, client: AsyncClient, cashier_with_zone_access: Staff, seat: Seat
) -> None:
    headers = _auth_headers(cashier_with_zone_access)
    start = await client.post(
        "/api/sessions",
        json={"seat_id": seat.id, "assigned_minutes": 60},
        headers=headers,
    )
    sid = start.json()["id"]
    resp = await client.post(
        f"/api/sessions/{sid}/extend",
        json={"additional_minutes": 30},
        headers=headers,
    )
    # Flag is off by default → requirement dependency returns 503.
    assert resp.status_code == 503

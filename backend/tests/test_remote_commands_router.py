"""HTTP-layer tests for the remote command routes on /api/seats.

Uses a test database with real seats and staff, bypassing JWT auth via
dependency overrides.
"""

from __future__ import annotations

import tempfile
from collections.abc import AsyncGenerator
from pathlib import Path

import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.api.deps import get_current_staff, get_db
from backend.core.database import Base
from backend.core.security import hash_pin
from backend.main import app
from backend.models._enums import PricingModel, StaffRole
from backend.models.seat import Seat
from backend.models.staff import Staff
from backend.models.zone import Zone
from backend.repositories import seat_repo, staff_repo, staff_zone_repo, zone_repo

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def db() -> AsyncGenerator[AsyncSession]:
    """Yield a fresh async session on a temporary file-based SQLite DB."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", echo=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        Session = async_sessionmaker(engine, expire_on_commit=False)
        async with Session() as session:
            yield session
        await engine.dispose()
    finally:
        Path(db_path).unlink(missing_ok=True)


@pytest_asyncio.fixture
async def sample_zone(db: AsyncSession) -> Zone:
    """Create a sample zone in the test DB."""
    return await zone_repo.create(
        db,
        name="Test Zone",
        rate_per_minute_paise=100,
        rate_per_hour_paise=6000,
        pricing_model=PricingModel.PER_MINUTE,
        block_minutes=15,
    )


@pytest_asyncio.fixture
async def sample_seat(db: AsyncSession, sample_zone: Zone) -> Seat:
    """Create a sample seat in the test DB."""
    return await seat_repo.create(
        db, name="Seat 1", zone_id=sample_zone.id, mac_address="AA:BB:CC:DD:EE:FF"
    )


@pytest_asyncio.fixture
async def admin_staff(db: AsyncSession) -> Staff:
    """Create a real admin staff record in the test DB."""
    return await staff_repo.create(
        db, name="Test Admin", pin_hash=hash_pin("1234"), role=StaffRole.ADMIN.value
    )


@pytest_asyncio.fixture
async def cashier_staff(db: AsyncSession, sample_zone: Zone) -> Staff:
    """Create a real cashier staff record with zone access in the test DB."""
    staff = await staff_repo.create(
        db, name="Test Cashier", pin_hash=hash_pin("1234"), role=StaffRole.CASHIER.value
    )
    # Assign cashier to the sample zone
    await staff_zone_repo.assign_zone(
        db, staff_id=staff.id, zone_id=sample_zone.id, granted_by=staff.id
    )
    return staff


@pytest_asyncio.fixture
async def client(db: AsyncSession, admin_staff: Staff) -> AsyncGenerator[TestClient]:
    """Yield a TestClient that bypasses auth using real admin staff with test DB."""
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_staff] = lambda: admin_staff

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_current_staff, None)


@pytest_asyncio.fixture
async def cashier_client(
    db: AsyncSession, cashier_staff: Staff
) -> AsyncGenerator[TestClient]:
    """Yield a TestClient authenticated as a cashier (not admin) with test DB."""
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_staff] = lambda: cashier_staff

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_current_staff, None)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

# --- message (cashier+) ----------------------------------------------------


def test_message_cashier_ok(client: TestClient, sample_seat: Seat) -> None:
    from unittest.mock import AsyncMock, patch

    from backend.services import remote_command_service as rcs

    with patch.object(rcs, "send_message", new=AsyncMock()) as m:
        resp = client.post(
            f"/api/seats/{sample_seat.id}/message", json={"message": "hi"}
        )
    assert resp.status_code == 204
    m.assert_awaited_once()


def test_message_requires_body(client: TestClient, sample_seat: Seat) -> None:
    resp = client.post(f"/api/seats/{sample_seat.id}/message", json={})
    assert resp.status_code == 422


# --- screenshot (cashier+) -------------------------------------------------


def test_screenshot_returns_jpeg(client: TestClient, sample_seat: Seat) -> None:
    from unittest.mock import AsyncMock, patch

    from backend.services import remote_command_service as rcs

    with patch.object(
        rcs, "request_screenshot", new=AsyncMock(return_value=b"\xff\xd8\xff\xff\xd9")
    ):
        resp = client.get(f"/api/seats/{sample_seat.id}/screenshot")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("image/jpeg")
    assert resp.content == b"\xff\xd8\xff\xff\xd9"


# --- restart / shutdown (admin only) ---------------------------------------


def test_restart_admin_ok(client: TestClient, sample_seat: Seat) -> None:
    from unittest.mock import AsyncMock, patch

    from backend.services import remote_command_service as rcs

    with patch.object(rcs, "restart_seat", new=AsyncMock()) as m:
        resp = client.post(f"/api/seats/{sample_seat.id}/restart")
    assert resp.status_code == 204
    m.assert_awaited_once()


def test_restart_denied_for_cashier(
    cashier_client: TestClient, sample_seat: Seat
) -> None:
    resp = cashier_client.post(f"/api/seats/{sample_seat.id}/restart")
    assert resp.status_code == 403


def test_shutdown_admin_ok(client: TestClient, sample_seat: Seat) -> None:
    from unittest.mock import AsyncMock, patch

    from backend.services import remote_command_service as rcs

    with patch.object(rcs, "shutdown_seat", new=AsyncMock()) as m:
        resp = client.post(f"/api/seats/{sample_seat.id}/shutdown")
    assert resp.status_code == 204
    m.assert_awaited_once()


def test_shutdown_denied_for_cashier(
    cashier_client: TestClient, sample_seat: Seat
) -> None:
    resp = cashier_client.post(f"/api/seats/{sample_seat.id}/shutdown")
    assert resp.status_code == 403


# --- offline / not-found passthrough ---------------------------------------


def test_message_503_when_offline(client: TestClient, sample_seat: Seat) -> None:
    from unittest.mock import AsyncMock, patch

    from fastapi import HTTPException

    from backend.services import remote_command_service as rcs

    with patch.object(rcs, "send_message", new=AsyncMock()) as m:
        m.side_effect = HTTPException(status_code=503, detail="offline")
        resp = client.post(
            f"/api/seats/{sample_seat.id}/message", json={"message": "hi"}
        )
    assert resp.status_code == 503


def test_restart_404_unknown_seat(client: TestClient) -> None:
    from unittest.mock import AsyncMock, patch

    from fastapi import HTTPException

    from backend.services import remote_command_service as rcs

    with patch.object(rcs, "restart_seat", new=AsyncMock()) as m:
        m.side_effect = HTTPException(status_code=404, detail="not found")
        resp = client.post("/api/seats/ghost/restart")
    assert resp.status_code == 404


# --- force_overlay (Task 3) --------------------------------------------------


def test_force_overlay_on_admin_ok(client: TestClient, sample_seat: Seat) -> None:
    from unittest.mock import AsyncMock, patch

    from backend.services import remote_command_service as rcs

    with patch.object(rcs, "force_overlay", new=AsyncMock()) as m:
        resp = client.post(f"/api/seats/{sample_seat.id}/overlay", json={"show": True})
    assert resp.status_code == 204
    m.assert_awaited_once()


# --- bulk_force_overlay (Task 4) --------------------------------------------


def test_bulk_overlay_admin_ok(client: TestClient) -> None:
    from unittest.mock import AsyncMock, patch

    from backend.services import remote_command_service as rcs

    summary = {"succeeded": ["seat-1"], "failed": []}
    mock_bulk = AsyncMock(return_value=summary)
    with patch.object(rcs, "bulk_force_overlay", new=mock_bulk) as m:
        resp = client.post("/api/seats/bulk/overlay", json={"show": True})
    assert resp.status_code == 200
    assert resp.json() == {"succeeded": ["seat-1"], "failed": []}
    m.assert_awaited_once()


def test_bulk_overlay_denied_for_cashier(cashier_client: TestClient) -> None:
    resp = cashier_client.post("/api/seats/bulk/overlay", json={"show": True})
    assert resp.status_code == 403


def test_force_overlay_requires_body(client: TestClient, sample_seat: Seat) -> None:
    resp = client.post(f"/api/seats/{sample_seat.id}/overlay", json={})
    assert resp.status_code == 422


def test_force_overlay_denied_for_cashier(
    cashier_client: TestClient, sample_seat: Seat
) -> None:
    resp = cashier_client.post(
        f"/api/seats/{sample_seat.id}/overlay", json={"show": True}
    )
    assert resp.status_code == 403

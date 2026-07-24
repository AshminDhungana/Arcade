"""Integration test fixtures for Arcade backend.

Provides:
- In-memory SQLite with StaticPool for fast, isolated tests
- File-based SQLite for services needing filesystem (print, backup)
- Real FastAPI app with lifespan + dependency overrides for auth
- Seed data helpers (zone, seat)
- Autouse fixtures for cache/singleton cleanup
"""

import tempfile
from collections.abc import AsyncGenerator
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from backend.core.database import Base
from backend.main import app


# In-memory SQLite with StaticPool for true isolation (shared connection)
@pytest_asyncio.fixture
async def integration_db() -> AsyncGenerator[AsyncSession]:
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as session:
        yield session
    await engine.dispose()


# File-based SQLite for services requiring filesystem (print, backup)
@pytest_asyncio.fixture
async def file_db() -> AsyncGenerator[tuple[AsyncSession, Path]]:
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = Path(tmp.name)
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as session:
        yield session, db_path
    await engine.dispose()
    db_path.unlink(missing_ok=True)


# Real FastAPI app with lifespan, dependency overrides for auth
@pytest_asyncio.fixture
async def integration_client(
    integration_db: AsyncSession,
) -> AsyncGenerator[AsyncClient]:
    from backend.api.deps import get_current_staff, get_db
    from backend.models import StaffRole

    # Mock staff for auth
    class MockStaff:
        id = "test-staff-id"
        name = "Test Cashier"
        is_active = True
        token_version = 0
        role = StaffRole.CASHIER

    app.dependency_overrides[get_db] = lambda: integration_db
    app.dependency_overrides[get_current_staff] = lambda: MockStaff()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()


# Seed data helpers
@pytest_asyncio.fixture
async def seeded_zone(integration_db: AsyncSession):
    from backend.models import PricingModel, Zone

    zone = Zone(
        name="Main Floor",
        rate_per_minute_paise=100,
        rate_per_hour_paise=5000,
        pricing_model=PricingModel.PER_MINUTE,
    )
    integration_db.add(zone)
    await integration_db.commit()
    await integration_db.refresh(zone)
    return zone


@pytest_asyncio.fixture
async def seeded_seat(integration_db: AsyncSession, seeded_zone):
    from backend.models import SeatStatus
    from backend.repositories import seat_repo

    seat = await seat_repo.create(integration_db, name="PC-01", zone_id=seeded_zone.id)
    seat.status = SeatStatus.AVAILABLE
    await integration_db.commit()
    return seat


# Autouse fixture to clear feature flag cache between tests
@pytest.fixture(autouse=True)
def clear_flag_cache():
    from backend.core.feature_flags import _flag_cache

    _flag_cache.clear()
    yield
    _flag_cache.clear()


# Autouse fixture to reset WebSocket manager singleton state
@pytest.fixture(autouse=True)
def reset_ws_manager():
    from backend.core.ws_manager import manager as ws_manager

    yield
    # Reset connection state after each test
    ws_manager.dashboard_connections.clear()
    ws_manager.agent_connections.clear()
    ws_manager._pending_pongs.clear()
    ws_manager._health_data.clear()
    ws_manager._health_received_at.clear()
    ws_manager._screenshot_waiters.clear()
    ws_manager._screenshot_seat.clear()


# Mock staff fixture for service-layer calls
@pytest.fixture
def mock_staff():
    from backend.models import Staff, StaffRole

    staff = Staff(
        id="test-staff-id",
        name="Test Cashier",
        pin_hash="argon2id$test",
        role=StaffRole.CASHIER,
        is_active=True,
        token_version=0,
    )
    return staff

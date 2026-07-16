"""Tests for Package API router."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.api.deps import get_current_staff
from backend.core.database import Base, get_db
from backend.core.feature_flags import _flag_cache
from backend.main import app
from backend.models._enums import PackageType, StaffRole
from backend.models.settings import AppSettings

# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------


def _make_mock_staff(role: str = "ADMIN"):
    """Return a plain object that mimics a Staff model."""

    class _MockStaff:
        id = "mock-staff-id"
        name = "Mock Admin"
        is_active = True
        token_version = 0

    obj = _MockStaff()
    obj.role = StaffRole(role)
    return obj


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def test_db_engine():
    """Create a temporary file-based SQLite engine for testing.

    Using a file-based DB instead of in-memory avoids aiosqlite threading issues
    during cleanup on Windows.
    """
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()
    Path(db_path).unlink(missing_ok=True)


@pytest_asyncio.fixture
async def db_session(test_db_engine) -> AsyncSession:
    """Yield a fresh async session on the test database."""
    Session = async_sessionmaker(test_db_engine, expire_on_commit=False)
    async with Session() as session:
        # Enable packages feature flag in test DB
        await session.execute(
            insert(AppSettings).values(key="enable_packages", value="true")
        )
        await session.commit()
        yield session


@pytest_asyncio.fixture
async def client(db_session: AsyncSession) -> AsyncClient:
    """Yield an AsyncClient that uses the test database and bypasses auth."""
    mock_staff = _make_mock_staff("CASHIER")

    # Override both get_current_staff and get_db dependencies
    app.dependency_overrides[get_current_staff] = lambda: mock_staff
    app.dependency_overrides[get_db] = lambda: db_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        # Set feature flag cache after lifespan runs (which clears it)
        _flag_cache["enable_packages"] = True
        yield c

    app.dependency_overrides.pop(get_current_staff, None)
    app.dependency_overrides.pop(get_db, None)
    _flag_cache.pop("enable_packages", None)


@pytest_asyncio.fixture
async def unauthenticated_client(db_session: AsyncSession) -> AsyncClient:
    """Yield an AsyncClient without auth override but with test database."""
    app.dependency_overrides[get_db] = lambda: db_session

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        # Set feature flag cache after lifespan runs (which clears it)
        _flag_cache["enable_packages"] = True
        yield c

    app.dependency_overrides.pop(get_db, None)
    _flag_cache.pop("enable_packages", None)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestPackagesRouter:
    async def test_get_packages_list(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """GET /api/packages returns list of active packages."""
        from backend.repositories import package_repo

        await package_repo.create(
            db_session,
            name="Test Package",
            type=PackageType.HOUR_BUNDLE.value,
            total_minutes=60,
            price_paise=10000,
            valid_days=30,
        )

        response = await client.get("/api/packages")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert data[0]["name"] == "Test Package"
        assert data[0]["total_minutes"] == 60
        assert data[0]["price_paise"] == 10000

    async def test_get_packages_requires_cashier_auth(
        self, unauthenticated_client: AsyncClient
    ):
        """GET /api/packages returns 401 without auth."""
        response = await unauthenticated_client.get("/api/packages")
        assert response.status_code == 401

    async def test_post_sell_package_wallet(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """POST /api/members/{id}/packages sells package via wallet."""
        from backend.repositories import member_repo, package_repo

        member = await member_repo.create(
            db_session, name="Buyer", phone="1112223333", wallet_balance_paise=50000
        )
        pkg = await package_repo.create(
            db_session,
            name="Wallet Pkg",
            type=PackageType.HOUR_BUNDLE.value,
            total_minutes=60,
            price_paise=20000,
            valid_days=30,
        )

        response = await client.post(
            f"/api/packages/members/{member.id}/packages",
            json={"package_id": pkg.id, "payment_method": "WALLET"},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["member_id"] == member.id
        assert data["package_id"] == pkg.id
        assert data["remaining_minutes"] == 60
        assert data["status"] == "ACTIVE"

        # Verify wallet deducted
        updated = await member_repo.get_by_id(db_session, member.id)
        assert updated.wallet_balance_paise == 30000

    async def test_post_sell_package_cash(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """POST /api/members/{id}/packages sells package via cash."""
        from backend.repositories import member_repo, package_repo

        member = await member_repo.create(
            db_session,
            name="Cash Buyer",
            phone="4445556666",
            wallet_balance_paise=10000,
        )
        pkg = await package_repo.create(
            db_session,
            name="Cash Pkg",
            type=PackageType.HOUR_BUNDLE.value,
            total_minutes=60,
            price_paise=20000,
            valid_days=30,
        )

        response = await client.post(
            f"/api/packages/members/{member.id}/packages",
            json={"package_id": pkg.id, "payment_method": "CASH"},
        )
        assert response.status_code == 201

        # Wallet unchanged
        updated = await member_repo.get_by_id(db_session, member.id)
        assert updated.wallet_balance_paise == 10000

    async def test_post_sell_package_insufficient_wallet(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Wallet payment with insufficient balance returns 400."""
        from backend.repositories import member_repo, package_repo

        member = await member_repo.create(
            db_session, name="Poor Buyer", phone="7778889999", wallet_balance_paise=1000
        )
        pkg = await package_repo.create(
            db_session,
            name="Expensive",
            type=PackageType.HOUR_BUNDLE.value,
            total_minutes=60,
            price_paise=20000,
            valid_days=30,
        )

        response = await client.post(
            f"/api/packages/members/{member.id}/packages",
            json={"package_id": pkg.id, "payment_method": "WALLET"},
        )
        assert response.status_code == 400
        assert "insufficient" in response.json()["detail"].lower()

    async def test_post_sell_package_member_not_found(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Non-existent member returns 404."""
        from backend.repositories import package_repo

        pkg = await package_repo.create(
            db_session,
            name="Test",
            type=PackageType.HOUR_BUNDLE.value,
            total_minutes=60,
            price_paise=10000,
            valid_days=30,
        )

        response = await client.post(
            "/api/packages/members/nonexistent/packages",
            json={"package_id": pkg.id, "payment_method": "CASH"},
        )
        assert response.status_code == 404

    async def test_post_sell_package_package_not_found(
        self, client: AsyncClient, db_session: AsyncSession
    ):
        """Non-existent package returns 404."""
        from backend.repositories import member_repo

        member = await member_repo.create(
            db_session, name="Buyer", phone="1112223333", wallet_balance_paise=50000
        )

        response = await client.post(
            f"/api/packages/members/{member.id}/packages",
            json={"package_id": "nonexistent", "payment_method": "CASH"},
        )
        assert response.status_code == 404


async def test_packages_503_when_flag_off(client: AsyncClient) -> None:
    """When enable_packages is off, list endpoint returns 503."""
    _flag_cache["enable_packages"] = False
    resp = await client.get("/api/packages")
    assert resp.status_code == 503

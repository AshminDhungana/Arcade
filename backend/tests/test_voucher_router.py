"""Tests for Voucher API router."""

from __future__ import annotations

import tempfile
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.api.deps import get_current_staff, get_db
from backend.core.database import Base
from backend.core.feature_flags import _flag_cache, load_flags
from backend.main import app
from backend.models import Member
from backend.models._enums import StaffRole, VoucherStatus
from backend.models.settings import AppSettings
from backend.models.staff import Staff
from backend.repositories import member_repo, staff_repo, voucher_repo

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_mock_staff(role: str = "ADMIN") -> Staff:
    """Return a mock staff object for testing."""
    from backend.models._enums import StaffRole as SR

    class _MockStaff:
        id = "mock-staff-id"
        name = "Mock Staff"
        is_active = True
        token_version = 0

    obj = _MockStaff()
    obj.role = SR(role)
    return obj


@pytest.fixture
async def db() -> AsyncGenerator[AsyncSession]:
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", echo=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        Session = async_sessionmaker(engine, expire_on_commit=False)
        async with Session() as session:
            # Enable vouchers feature flag + members
            await session.execute(
                insert(AppSettings).values(
                    [
                        {"key": "enable_vouchers", "value": "true"},
                        {"key": "enable_members", "value": "true"},
                    ]
                )
            )
            await session.commit()
            await load_flags(session)
            yield session
        await engine.dispose()
    finally:
        Path(db_path).unlink(missing_ok=True)


@pytest_asyncio.fixture
async def admin_staff(db: AsyncSession) -> Staff:
    return await staff_repo.create(
        db,
        name="Admin User",
        pin_hash="$argon2id$v=19$m=102400,t=2,p=8$...",
        role=StaffRole.ADMIN.value,
        is_active=True,
    )


@pytest_asyncio.fixture
async def cashier_staff(db: AsyncSession) -> Staff:
    return await staff_repo.create(
        db,
        name="Cashier User",
        pin_hash="$argon2id$v=19$m=102400,t=2,p=8$...",
        role=StaffRole.CASHIER.value,
        is_active=True,
    )


@pytest_asyncio.fixture
async def member(db: AsyncSession) -> Member:
    return await member_repo.create(
        db, name="Test Member", phone="9876543210", wallet_balance_paise=0
    )


@pytest_asyncio.fixture
async def client(db: AsyncSession, admin_staff: Staff) -> AsyncGenerator[AsyncClient]:
    """Yield an AsyncClient that uses the test database and bypasses auth as admin."""
    # Override dependencies
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_staff] = lambda: admin_staff

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as ac:
        _flag_cache["enable_vouchers"] = True
        _flag_cache["enable_members"] = True
        yield ac

    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_current_staff, None)
    _flag_cache.pop("enable_vouchers", None)
    _flag_cache.pop("enable_members", None)


@pytest_asyncio.fixture
async def cashier_client(db: AsyncSession) -> AsyncGenerator[AsyncClient]:
    """Yield an AsyncClient authenticated as a cashier (not admin)."""
    mock_staff = _make_mock_staff("CASHIER")

    # Override dependencies
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_staff] = lambda: mock_staff

    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as ac:
        _flag_cache["enable_vouchers"] = True
        _flag_cache["enable_members"] = True
        yield ac

    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_current_staff, None)
    _flag_cache.pop("enable_vouchers", None)
    _flag_cache.pop("enable_members", None)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestVoucherBatch:
    async def test_create_batch_admin_success(
        self, client: AsyncClient, admin_staff: Staff
    ):
        """Admin can create voucher batch via POST /api/vouchers/batch."""
        response = await client.post(
            "/api/vouchers/batch",
            json={"count": 10, "value_paise": 5000, "expires_in_days": 30},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["count"] == 10
        assert data["batch_id"] is not None
        assert len(data["vouchers"]) == 10
        for v in data["vouchers"]:
            assert v["value_paise"] == 5000
            assert v["status"] == "UNUSED"

    async def test_create_batch_cashier_forbidden(self, cashier_client: AsyncClient):
        """Cashier cannot create voucher batch (admin only)."""
        response = await cashier_client.post(
            "/api/vouchers/batch",
            json={"count": 10, "value_paise": 5000},
        )
        assert response.status_code == 403

    async def test_create_batch_invalid_count(self, client: AsyncClient):
        """Count=0 returns 422 validation error."""
        response = await client.post(
            "/api/vouchers/batch",
            json={"count": 0, "value_paise": 5000},
        )
        assert response.status_code == 422

    async def test_create_batch_invalid_both_values(self, client: AsyncClient):
        """Both value_paise and value_minutes returns 422."""
        response = await client.post(
            "/api/vouchers/batch",
            json={"count": 10, "value_paise": 5000, "value_minutes": 60},
        )
        assert response.status_code == 422

    async def test_create_batch_feature_flag_disabled(self, client: AsyncClient):
        """Feature flag off returns 503."""
        _flag_cache["enable_vouchers"] = False

        response = await client.post(
            "/api/vouchers/batch",
            json={"count": 10, "value_paise": 5000},
        )
        assert response.status_code == 503


class TestVoucherRedeem:
    async def test_redeem_cashier_success(
        self, cashier_client: AsyncClient, member: Member, db: AsyncSession
    ):
        """Cashier can redeem voucher for member."""
        # Create voucher via repo using db fixture
        await voucher_repo.create(
            db,
            code="VOUCHER12345",
            value_paise=25000,
            batch_id="batch1",
        )

        response = await cashier_client.post(
            "/api/vouchers/redeem",
            json={"code": "VOUCHER12345", "member_id": member.id},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["wallet_balance_paise"] == 25000

    async def test_redeem_expired_returns_400(
        self, cashier_client: AsyncClient, member: Member, db: AsyncSession
    ):
        """Redeem expired voucher returns 400."""
        await voucher_repo.create(
            db,
            code="EXPIREDVOUCH",
            value_paise=10000,
            expires_at=datetime.now(UTC) - timedelta(days=1),
            batch_id="batch1",
        )

        response = await cashier_client.post(
            "/api/vouchers/redeem",
            json={"code": "EXPIREDVOUCH", "member_id": member.id},
        )
        assert response.status_code == 400

    async def test_redeem_already_redeemed_returns_400(
        self, cashier_client: AsyncClient, member: Member, db: AsyncSession
    ):
        """Redeem already-redeemed voucher returns 400."""
        voucher = await voucher_repo.create(
            db,
            code="USEDVOUCHER1",
            value_paise=10000,
            batch_id="batch1",
        )
        voucher.status = VoucherStatus.REDEEMED
        voucher.redeemed_by_member_id = member.id
        voucher.redeemed_at = datetime.now(UTC)
        await voucher_repo.update(db, voucher)

        response = await cashier_client.post(
            "/api/vouchers/redeem",
            json={"code": "USEDVOUCHER1", "member_id": member.id},
        )
        assert response.status_code == 400

    async def test_redeem_nonexistent_returns_404(
        self, cashier_client: AsyncClient, member: Member
    ):
        """Redeem non-existent voucher returns 404."""
        response = await cashier_client.post(
            "/api/vouchers/redeem",
            json={"code": "NONEXISTENT1", "member_id": member.id},
        )
        assert response.status_code == 404

    async def test_redeem_member_not_found_returns_404(
        self, cashier_client: AsyncClient, db: AsyncSession
    ):
        """Redeem for non-existent member returns 404."""
        await voucher_repo.create(
            db, code="VOUCHER12345", value_paise=10000, batch_id="batch1"
        )

        response = await cashier_client.post(
            "/api/vouchers/redeem",
            json={"code": "VOUCHER12345", "member_id": "nonexistent"},
        )
        assert response.status_code == 404

    async def test_redeem_feature_flag_disabled(
        self, cashier_client: AsyncClient, member: Member, db: AsyncSession
    ):
        """Feature flag off returns 503."""
        _flag_cache["enable_vouchers"] = False

        await voucher_repo.create(
            db, code="VOUCHER12345", value_paise=10000, batch_id="batch1"
        )

        response = await cashier_client.post(
            "/api/vouchers/redeem",
            json={"code": "VOUCHER12345", "member_id": member.id},
        )
        assert response.status_code == 503

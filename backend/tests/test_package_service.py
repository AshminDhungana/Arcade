"""Tests for PackageService."""

from __future__ import annotations

import tempfile
from collections.abc import AsyncGenerator
from pathlib import Path

import pytest
import pytest_asyncio
from fastapi import HTTPException
from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.core.database import Base
from backend.models import Member, Package
from backend.models._enums import EntitlementStatus, PackageType, PaymentMethod
from backend.models.settings import AppSettings
from backend.models.staff import Staff
from backend.services.package_service import PackageService

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def db() -> AsyncGenerator[AsyncSession]:
    """Yield a fresh async session on a temporary file-based SQLite DB.

    Using a file-based DB instead of in-memory avoids aiosqlite threading issues
    during test cleanup (Windows fatal exception on engine.dispose()).
    """
    # Create a temporary file for the database
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", echo=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        Session = async_sessionmaker(engine, expire_on_commit=False)
        async with Session() as session:
            # Enable packages feature flag
            await session.execute(
                insert(AppSettings).values(key="enable_packages", value="true")
            )
            await session.commit()
            # Refresh feature flag cache
            from backend.core.feature_flags import load_flags

            await load_flags(session)
            yield session
        await engine.dispose()
    finally:
        # Clean up the temporary database file
        Path(db_path).unlink(missing_ok=True)


@pytest_asyncio.fixture
async def sample_member(db: AsyncSession) -> Member:
    from backend.repositories import member_repo

    return await member_repo.create(
        db, name="Test Member", phone="9876543210", wallet_balance_paise=500000
    )


@pytest_asyncio.fixture
async def sample_package(db: AsyncSession) -> Package:
    from backend.repositories import package_repo

    return await package_repo.create(
        db,
        name="2 Hour Bundle",
        type=PackageType.HOUR_BUNDLE.value,
        total_minutes=120,
        price_paise=20000,
        valid_days=30,
    )


@pytest_asyncio.fixture
async def sample_staff(db: AsyncSession) -> Staff:
    from backend.repositories import staff_repo

    return await staff_repo.create(
        db,
        name="Cashier",
        pin_hash="$argon2id$v=19$m=102400,t=2,p=8$...",
        role="CASHIER",
    )


class TestSellPackage:
    async def test_sell_package_wallet_payment(
        self,
        db: AsyncSession,
        sample_member: Member,
        sample_package: Package,
        sample_staff: Staff,
    ):
        """Sell package deducting from member wallet."""
        entitlement = await PackageService.sell_package(
            db,
            member_id=sample_member.id,
            package_id=sample_package.id,
            payment_method=PaymentMethod.WALLET.value,
            staff=sample_staff,
        )
        assert entitlement is not None
        assert entitlement.member_id == sample_member.id
        assert entitlement.package_id == sample_package.id
        assert entitlement.remaining_minutes == sample_package.total_minutes
        assert entitlement.status == EntitlementStatus.ACTIVE

        # Wallet should be deducted
        from backend.repositories import member_repo

        updated = await member_repo.get_by_id(db, sample_member.id)
        assert updated.wallet_balance_paise == 500000 - sample_package.price_paise

    async def test_sell_package_cash_payment(
        self,
        db: AsyncSession,
        sample_member: Member,
        sample_package: Package,
        sample_staff: Staff,
    ):
        """Sell package with cash payment (wallet unchanged)."""
        original_wallet = sample_member.wallet_balance_paise
        entitlement = await PackageService.sell_package(
            db,
            member_id=sample_member.id,
            package_id=sample_package.id,
            payment_method=PaymentMethod.CASH.value,
            staff=sample_staff,
        )
        assert entitlement.remaining_minutes == sample_package.total_minutes

        # Wallet unchanged for cash
        from backend.repositories import member_repo

        updated = await member_repo.get_by_id(db, sample_member.id)
        assert updated.wallet_balance_paise == original_wallet

    async def test_sell_package_insufficient_wallet_raises(
        self,
        db: AsyncSession,
        sample_member: Member,
        sample_package: Package,
        sample_staff: Staff,
    ):
        """Wallet payment with insufficient balance raises 400."""
        # Set wallet lower than package price
        from backend.repositories import member_repo

        sample_member.wallet_balance_paise = 1000
        await member_repo.update(db, sample_member)

        with pytest.raises(HTTPException) as exc:
            await PackageService.sell_package(
                db,
                member_id=sample_member.id,
                package_id=sample_package.id,
                payment_method=PaymentMethod.WALLET.value,
                staff=sample_staff,
            )
        assert exc.value.status_code == 400
        assert "insufficient" in exc.value.detail.lower()

    async def test_sell_package_member_not_found(
        self, db: AsyncSession, sample_package: Package, sample_staff: Staff
    ):
        """Non-existent member raises 404."""
        with pytest.raises(HTTPException) as exc:
            await PackageService.sell_package(
                db,
                member_id="nonexistent",
                package_id=sample_package.id,
                payment_method=PaymentMethod.CASH.value,
                staff=sample_staff,
            )
        assert exc.value.status_code == 404

    async def test_sell_package_package_not_found(
        self, db: AsyncSession, sample_member: Member, sample_staff: Staff
    ):
        """Non-existent package raises 404."""
        with pytest.raises(HTTPException) as exc:
            await PackageService.sell_package(
                db,
                member_id=sample_member.id,
                package_id="nonexistent",
                payment_method=PaymentMethod.CASH.value,
                staff=sample_staff,
            )
        assert exc.value.status_code == 404

    async def test_sell_package_inactive_package_raises(
        self, db: AsyncSession, sample_member: Member, sample_staff: Staff
    ):
        """Inactive package raises 400."""
        from backend.repositories import package_repo

        inactive_pkg = await package_repo.create(
            db,
            name="Inactive",
            type=PackageType.HOUR_BUNDLE.value,
            total_minutes=60,
            price_paise=10000,
            valid_days=30,
            is_active=False,
        )

        with pytest.raises(HTTPException) as exc:
            await PackageService.sell_package(
                db,
                member_id=sample_member.id,
                package_id=inactive_pkg.id,
                payment_method=PaymentMethod.CASH.value,
                staff=sample_staff,
            )
        assert exc.value.status_code == 400
        assert "inactive" in exc.value.detail.lower()


class TestGetActiveEntitlement:
    async def test_get_active_entitlement_returns_active(
        self,
        db: AsyncSession,
        sample_member: Member,
        sample_package: Package,
        sample_staff: Staff,
    ):
        """Returns the active entitlement for a member."""
        # First sell a package
        await PackageService.sell_package(
            db,
            member_id=sample_member.id,
            package_id=sample_package.id,
            payment_method=PaymentMethod.CASH.value,
            staff=sample_staff,
        )

        entitlement = await PackageService.get_active_entitlement(db, sample_member.id)
        assert entitlement is not None
        assert entitlement.member_id == sample_member.id
        assert entitlement.status == EntitlementStatus.ACTIVE
        assert entitlement.remaining_minutes > 0

    async def test_get_active_entitlement_returns_none_when_no_entitlement(
        self, db: AsyncSession, sample_member: Member
    ):
        """Returns None when member has no active entitlement."""
        entitlement = await PackageService.get_active_entitlement(db, sample_member.id)
        assert entitlement is None

    async def test_get_active_entitlement_returns_none_when_exhausted(
        self,
        db: AsyncSession,
        sample_member: Member,
        sample_package: Package,
        sample_staff: Staff,
    ):
        """Returns None when only exhausted entitlements exist."""
        await PackageService.sell_package(
            db,
            member_id=sample_member.id,
            package_id=sample_package.id,
            payment_method=PaymentMethod.CASH.value,
            staff=sample_staff,
        )
        # Manually exhaust it
        from backend.repositories import package_repo

        ent = await package_repo.get_active_entitlement(db, sample_member.id)
        ent.remaining_minutes = 0
        ent.status = EntitlementStatus.EXHAUSTED
        await package_repo.update(db, ent)

        result = await PackageService.get_active_entitlement(db, sample_member.id)
        assert result is None


class TestListPackages:
    async def test_list_packages_returns_all_active(self, db: AsyncSession):
        """Lists all active packages."""
        from backend.repositories import package_repo

        await package_repo.create(
            db,
            name="Pkg A",
            type=PackageType.HOUR_BUNDLE.value,
            total_minutes=60,
            price_paise=10000,
            valid_days=30,
        )
        await package_repo.create(
            db,
            name="Pkg B",
            type=PackageType.DAY_PASS.value,
            total_minutes=480,
            price_paise=50000,
            valid_days=1,
            is_active=True,
        )
        await package_repo.create(
            db,
            name="Pkg C",
            type=PackageType.HOUR_BUNDLE.value,
            total_minutes=30,
            price_paise=5000,
            valid_days=30,
            is_active=False,
        )

        packages = await PackageService.list_packages(db)
        assert len(packages) == 2
        assert all(p.is_active for p in packages)


class TestPackageIntegration:
    async def test_full_package_sale_and_checkout_flow(
        self, db: AsyncSession, sample_staff: Staff
    ):
        """End-to-end: create package, create member, sell package,
        start session, checkout uses package."""
        from backend.models._enums import (
            PackageType,
            PaymentMethod,
            PricingModel,
        )
        from backend.repositories import member_repo, package_repo, seat_repo, zone_repo
        from backend.services.billing_service import checkout_session
        from backend.services.session_service import start_session

        # Create zone and seat
        zone = await zone_repo.create(
            db,
            name="Test Zone",
            rate_per_minute_paise=100,
            rate_per_hour_paise=6000,
            pricing_model=PricingModel.PER_MINUTE,
        )
        seat = await seat_repo.create(
            db, name="Seat 1", zone_id=zone.id, mac_address="AA:BB:CC:DD:EE:FF"
        )

        # Create package (120 min for 20000 paise)
        pkg = await package_repo.create(
            db,
            name="2 Hour Bundle",
            type=PackageType.HOUR_BUNDLE.value,
            total_minutes=120,
            price_paise=20000,
            valid_days=30,
        )

        # Create member with wallet
        member = await member_repo.create(
            db, name="Package User", phone="5556667777", wallet_balance_paise=50000
        )

        # Sell package via wallet
        entitlement = await PackageService.sell_package(
            db,
            member_id=member.id,
            package_id=pkg.id,
            payment_method=PaymentMethod.WALLET.value,
            staff=sample_staff,
        )
        assert entitlement.remaining_minutes == 120
        # Wallet deducted: 50000 - 20000 = 30000
        updated_member = await member_repo.get_by_id(db, member.id)
        assert updated_member.wallet_balance_paise == 30000

        # Start session for member (should auto-attach package)
        session = await start_session(
            db, seat_id=seat.id, member_id=member.id, staff=sample_staff
        )
        assert session.package_entitlement_id == entitlement.id

        # Simulate 90 minutes elapsed (1.5 hours) - persist to DB
        from datetime import UTC, datetime, timedelta

        from backend.repositories import session_repo

        db_session = await session_repo.get_by_id(db, session.id)
        db_session.started_at = datetime.now(UTC) - timedelta(minutes=90)
        await session_repo.update(db, db_session)

        # Checkout
        await checkout_session(
            db,
            session_id=session.id,
            payment_method=PaymentMethod.WALLET,
            staff=sample_staff,
        )

        # Time charge: 90 min at 100 paise/min = 9000 paise
        # Package covers 90 min (120 available), so time charge = 0,
        # package credit = 9000
        # Verify package drawdown happened
        refreshed_ent = await package_repo.get_entitlement_by_id(db, entitlement.id)
        assert refreshed_ent.remaining_minutes == 30  # 120 - 90 = 30
        assert refreshed_ent.status == EntitlementStatus.ACTIVE

"""Tests for MemberService."""

from __future__ import annotations

import tempfile
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.core.database import Base
from backend.models import Voucher
from backend.models._enums import AuditAction, MemberTier, PaymentMethod, VoucherStatus
from backend.models.settings import AppSettings
from backend.repositories import staff_repo, voucher_repo
from backend.services import audit_service
from backend.services.member_service import (
    DuplicatePhoneError,
    MemberNotFoundError,
    MemberService,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def db() -> AsyncGenerator[AsyncSession]:
    """Yield a fresh async session on a temporary file-based SQLite DB.

    Using a file-based DB instead of in-memory avoids aiosqlite threading issues
    during test cleanup (Windows fatal exception on engine.dispose()).
    """
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


@pytest.fixture
async def staff(db: AsyncSession):
    """Create and return a CASHIER staff member."""
    return await staff_repo.create(
        db, name="Cashier User", pin_hash="argon2id$", role="CASHIER"
    )


class TestCreateMember:
    async def test_create_member_success(self, db: AsyncSession):
        """Create a member with valid name and phone."""
        member = await MemberService.create_member(db, name="Alice", phone="9801234567")
        assert member.name == "Alice"
        assert member.phone == "9801234567"
        assert member.tier == MemberTier.BRONZE
        assert member.wallet_balance_paise == 0
        assert member.loyalty_points == 0
        assert member.total_visits == 0
        assert member.total_seconds_played == 0
        assert member.id is not None

    async def test_create_member_duplicate_phone_raises(self, db: AsyncSession):
        """Creating a member with an existing phone raises DuplicatePhoneError."""
        await MemberService.create_member(db, name="Alice", phone="9801234567")
        with pytest.raises(DuplicatePhoneError):
            await MemberService.create_member(db, name="Bob", phone="9801234567")


class TestGetMember:
    async def test_get_member_success(self, db: AsyncSession):
        """Get member by ID."""
        created = await MemberService.create_member(
            db, name="Alice", phone="9801234567"
        )
        member = await MemberService.get_member(db, created.id)
        assert member.id == created.id
        assert member.name == "Alice"

    async def test_get_member_not_found_raises(self, db: AsyncSession):
        """Get non-existent member raises 404."""
        with pytest.raises(MemberNotFoundError):
            await MemberService.get_member(db, "non-existent-id")


class TestSearchMembers:
    async def test_search_members_by_name(self, db: AsyncSession):
        """Search members by name (case-insensitive)."""
        await MemberService.create_member(
            db, name="Alice Wonderland", phone="9801111111"
        )
        await MemberService.create_member(db, name="Bob Builder", phone="9802222222")
        await MemberService.create_member(
            db, name="Charlie Chaplin", phone="9803333333"
        )

        results = await MemberService.search_members(db, "alice")
        assert len(results) == 1
        assert results[0].name == "Alice Wonderland"

        results = await MemberService.search_members(db, "builder")
        assert len(results) == 1
        assert results[0].name == "Bob Builder"

    async def test_search_members_by_phone(self, db: AsyncSession):
        """Search members by phone."""
        await MemberService.create_member(db, name="Alice", phone="9801234567")

        results = await MemberService.search_members(db, "980123")
        assert len(results) == 1
        assert results[0].phone == "9801234567"

    async def test_search_members_empty_result(self, db: AsyncSession):
        """Search with no matches returns empty list."""
        results = await MemberService.search_members(db, "nonexistent")
        assert results == []

    async def test_search_members_empty_query(self, db: AsyncSession):
        """Search with empty query returns empty list."""
        results = await MemberService.search_members(db, "")
        assert results == []
        results = await MemberService.search_members(db, "   ")
        assert results == []


class TestTopupWallet:
    async def test_topup_wallet_success(self, db: AsyncSession, staff):
        """Top up member wallet and audit log."""
        member = await MemberService.create_member(db, name="Alice", phone="9801234567")
        assert member.wallet_balance_paise == 0

        updated = await MemberService.topup_wallet(
            db,
            member_id=member.id,
            amount_paise=50000,
            payment_method=PaymentMethod.CASH,
            staff=staff,
        )
        assert updated.wallet_balance_paise == 50000

        # Verify audit log
        logs = await audit_service.list_logs(
            db, action=AuditAction.WALLET_TOPUP, entity_id=member.id
        )
        assert len(logs) == 1
        assert logs[0].detail == "50000 paise via CASH"

    async def test_topup_wallet_member_not_found(self, db: AsyncSession, staff):
        """Top up non-existent member raises 404."""
        with pytest.raises(MemberNotFoundError):
            await MemberService.topup_wallet(
                db,
                member_id="non-existent",
                amount_paise=1000,
                payment_method=PaymentMethod.CASH,
                staff=staff,
            )

    async def test_topup_wallet_negative_amount_raises(self, db: AsyncSession, staff):
        """Top up with negative amount raises 400."""
        member = await MemberService.create_member(db, name="Alice", phone="9801234567")
        with pytest.raises(Exception) as exc:
            await MemberService.topup_wallet(
                db,
                member_id=member.id,
                amount_paise=-100,
                payment_method=PaymentMethod.CASH,
                staff=staff,
            )
        assert exc.value.status_code == 400

    async def test_topup_wallet_zero_amount_raises(self, db: AsyncSession, staff):
        """Top up with zero amount raises 400."""
        member = await MemberService.create_member(db, name="Alice", phone="9801234567")
        with pytest.raises(Exception) as exc:
            await MemberService.topup_wallet(
                db,
                member_id=member.id,
                amount_paise=0,
                payment_method=PaymentMethod.CASH,
                staff=staff,
            )
        assert exc.value.status_code == 400


class TestRedeemVoucherToWallet:
    async def test_redeem_voucher_success(self, db: AsyncSession):
        """Redeem valid voucher adds value to wallet and marks voucher redeemed."""
        member = await MemberService.create_member(db, name="Alice", phone="9801234567")
        await voucher_repo.create(
            db,
            code="VOUCHER123",
            value_paise=10000,
            value_minutes=None,
            batch_id="batch1",
        )

        updated = await MemberService.redeem_voucher_to_wallet(
            db, member.id, "VOUCHER123"
        )

        assert updated.wallet_balance_paise == 10000

        # Verify voucher status updated
        results = await db.execute(select(Voucher).where(Voucher.code == "VOUCHER123"))
        voucher = results.scalar_one()
        assert voucher.status == VoucherStatus.REDEEMED
        assert voucher.redeemed_by_member_id == member.id

        # Verify audit log
        logs = await audit_service.list_logs(
            db, action=AuditAction.VOUCHER_REDEEMED, entity_id=member.id
        )
        assert len(logs) == 1
        assert "VOUCHER123" in logs[0].detail

    async def test_redeem_voucher_expired_raises(self, db: AsyncSession):
        """Redeem expired voucher raises 400."""
        member = await MemberService.create_member(db, name="Alice", phone="9801234567")
        await voucher_repo.create(
            db,
            code="EXPIRED123",
            value_paise=10000,
            expires_at=datetime.now(UTC) - timedelta(days=1),
            batch_id="batch1",
        )

        with pytest.raises(Exception) as exc:
            await MemberService.redeem_voucher_to_wallet(db, member.id, "EXPIRED123")
        assert exc.value.status_code == 400
        assert "expired" in exc.value.detail.lower()

    async def test_redeem_voucher_already_redeemed_raises(self, db: AsyncSession):
        """Redeem already-redeemed voucher raises 400."""
        member = await MemberService.create_member(db, name="Alice", phone="9801234567")
        await voucher_repo.create(
            db,
            code="USED123",
            value_paise=10000,
            status=VoucherStatus.REDEEMED.value,
            batch_id="batch1",
        )

        with pytest.raises(Exception) as exc:
            await MemberService.redeem_voucher_to_wallet(db, member.id, "USED123")
        assert exc.value.status_code == 400
        assert "redeemed" in exc.value.detail.lower()

    async def test_redeem_voucher_member_not_found(self, db: AsyncSession):
        """Redeem voucher for non-existent member raises 404."""
        with pytest.raises(MemberNotFoundError):
            await MemberService.redeem_voucher_to_wallet(
                db, "non-existent", "VOUCHER123"
            )

    async def test_redeem_voucher_not_found(self, db: AsyncSession):
        """Redeem non-existent voucher raises 404."""
        member = await MemberService.create_member(db, name="Alice", phone="9801234567")
        with pytest.raises(Exception) as exc:
            await MemberService.redeem_voucher_to_wallet(db, member.id, "NONEXISTENT")
        assert exc.value.status_code == 404


class TestAddLoyaltyPoints:
    async def test_add_loyalty_points_tier_upgrade(self, db: AsyncSession):
        """Add loyalty points triggers tier upgrade when threshold met."""
        # Set tier thresholds via AppSettings
        db.add_all(
            [
                AppSettings(key="enable_members", value="true"),
                AppSettings(key="loyalty_points_per_minute", value="1"),
                AppSettings(key="tier_silver_threshold", value="500"),
                AppSettings(key="tier_gold_threshold", value="1000"),
            ]
        )
        await db.flush()
        from backend.core.feature_flags import refresh_flags

        await refresh_flags(db)

        member = await MemberService.create_member(db, name="Alice", phone="9801234567")
        assert member.tier == MemberTier.BRONZE
        assert member.loyalty_points == 0

        # Add 600 points (600 minutes = 10 hours) -> should upgrade to SILVER
        updated = await MemberService.add_loyalty_points(
            db, member.id, 600 * 60
        )  # 600 minutes in seconds

        assert updated.loyalty_points == 600
        assert updated.tier == MemberTier.SILVER

    async def test_add_loyalty_points_no_upgrade(self, db: AsyncSession):
        """Add points below threshold does not upgrade tier."""
        from backend.models.settings import AppSettings

        db.add_all(
            [
                AppSettings(key="enable_members", value="true"),
                AppSettings(key="loyalty_points_per_minute", value="1"),
                AppSettings(key="tier_silver_threshold", value="500"),
                AppSettings(key="tier_gold_threshold", value="1000"),
            ]
        )
        await db.flush()
        from backend.core.feature_flags import refresh_flags

        await refresh_flags(db)

        member = await MemberService.create_member(db, name="Alice", phone="9801234567")

        # Add 300 points (below SILVER threshold of 500)
        updated = await MemberService.add_loyalty_points(db, member.id, 300 * 60)

        assert updated.loyalty_points == 300
        assert updated.tier == MemberTier.BRONZE

    async def test_add_loyalty_points_bronze_to_gold(self, db: AsyncSession):
        """Add enough points to jump from BRONZE to GOLD."""
        from backend.models.settings import AppSettings

        db.add_all(
            [
                AppSettings(key="enable_members", value="true"),
                AppSettings(key="loyalty_points_per_minute", value="1"),
                AppSettings(key="tier_silver_threshold", value="500"),
                AppSettings(key="tier_gold_threshold", value="1000"),
            ]
        )
        await db.flush()
        from backend.core.feature_flags import refresh_flags

        await refresh_flags(db)

        member = await MemberService.create_member(db, name="Alice", phone="9801234567")

        # Add 1200 points -> should go to GOLD directly
        updated = await MemberService.add_loyalty_points(db, member.id, 1200 * 60)

        assert updated.loyalty_points == 1200
        assert updated.tier == MemberTier.GOLD

    async def test_add_loyalty_points_updates_total_seconds(self, db: AsyncSession):
        """Total seconds played is updated correctly."""
        from backend.models.settings import AppSettings

        db.add_all(
            [
                AppSettings(key="enable_members", value="true"),
                AppSettings(key="loyalty_points_per_minute", value="1"),
                AppSettings(key="tier_silver_threshold", value="500"),
                AppSettings(key="tier_gold_threshold", value="1000"),
            ]
        )
        await db.flush()
        from backend.core.feature_flags import refresh_flags

        await refresh_flags(db)

        member = await MemberService.create_member(db, name="Alice", phone="9801234567")
        assert member.total_seconds_played == 0

        updated = await MemberService.add_loyalty_points(
            db, member.id, 1800
        )  # 30 minutes

        assert updated.total_seconds_played == 1800

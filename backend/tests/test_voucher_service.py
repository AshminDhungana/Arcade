"""Tests for VoucherService."""

from __future__ import annotations

import tempfile
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.core.database import Base
from backend.core.feature_flags import load_flags
from backend.models import Member, Voucher
from backend.models._enums import (
    AuditAction,
    MemberTier,
    VoucherStatus,
)
from backend.models.settings import AppSettings
from backend.models.staff import Staff
from backend.repositories import member_repo, voucher_repo, staff_repo
from backend.services import audit_service
from backend.services.voucher_service import VoucherService, VoucherGenerationError, VoucherRedemptionError


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
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
            # Enable vouchers feature flag
            await session.execute(
                insert(AppSettings).values(key="enable_vouchers", value="true")
            )
            await session.commit()
            await load_flags(session)
            yield session
        await engine.dispose()
    finally:
        Path(db_path).unlink(missing_ok=True)


@pytest_asyncio.fixture
async def sample_member(db: AsyncSession) -> Member:
    return await member_repo.create(
        db, name="Test Member", phone="9876543210", wallet_balance_paise=0
    )


@pytest_asyncio.fixture
async def sample_staff(db: AsyncSession) -> Staff:
    return await staff_repo.create(
        db,
        name="Admin User",
        pin_hash="$argon2id$v=19$m=102400,t=2,p=8$...",
        role="ADMIN",
    )


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestGenerateBatch:
    async def test_generate_batch_value_paise(
        self, db: AsyncSession, sample_staff: Staff
    ):
        """Generate batch with value_paise creates correct vouchers."""
        result = await VoucherService.generate_batch(
            db,
            count=5,
            value_paise=10000,
            expires_in_days=30,
            staff=sample_staff,
        )

        assert result.batch_id is not None
        assert result.count == 5
        assert len(result.vouchers) == 5
        for v in result.vouchers:
            assert v.value_paise == 10000
            assert v.value_minutes is None
            assert v.status == VoucherStatus.UNUSED
            assert v.batch_id == result.batch_id
            assert v.expires_at is not None

        # Verify audit log
        logs = await audit_service.list_logs(
            db, action=AuditAction.VOUCHER_GENERATED, entity_id=result.batch_id
        )
        assert len(logs) == 1
        assert "5 vouchers" in logs[0].detail
        assert "10000 paise" in logs[0].detail

    async def test_generate_batch_value_minutes(
        self, db: AsyncSession, sample_staff: Staff
    ):
        """Generate batch with value_minutes creates correct vouchers."""
        result = await VoucherService.generate_batch(
            db,
            count=3,
            value_minutes=60,
            expires_in_days=7,
            staff=sample_staff,
        )

        assert result.count == 3
        for v in result.vouchers:
            assert v.value_minutes == 60
            assert v.value_paise is None

    async def test_generate_batch_no_expiry(
        self, db: AsyncSession, sample_staff: Staff
    ):
        """Generate batch without expires_in_days has no expiry."""
        result = await VoucherService.generate_batch(
            db,
            count=2,
            value_paise=5000,
            expires_in_days=None,
            staff=sample_staff,
        )

        for v in result.vouchers:
            assert v.expires_at is None

    async def test_generate_batch_feature_flag_disabled(
        self, db: AsyncSession, sample_staff: Staff
    ):
        """Generate batch raises 503 when feature flag is off."""
        from backend.core.feature_flags import invalidate_cache

        invalidate_cache()  # Disable vouchers flag

        with pytest.raises(Exception) as exc:
            await VoucherService.generate_batch(
                db, count=5, value_paise=10000, staff=sample_staff
            )
        assert exc.value.status_code == 503
        assert "disabled" in exc.value.detail.lower()

    async def test_generate_batch_invalid_count(
        self, db: AsyncSession, sample_staff: Staff
    ):
        """Generate batch with count=0 raises 400."""
        with pytest.raises(Exception) as exc:
            await VoucherService.generate_batch(
                db, count=0, value_paise=10000, staff=sample_staff
            )
        assert exc.value.status_code == 400

    async def test_generate_batch_all_codes_unique(
        self, db: AsyncSession, sample_staff: Staff
    ):
        """All voucher codes in a batch are unique."""
        result = await VoucherService.generate_batch(
            db, count=100, value_paise=1000, expires_in_days=30, staff=sample_staff
        )
        codes = [v.code for v in result.vouchers]
        assert len(codes) == len(set(codes)) == 100


class TestRedeem:
    async def test_redeem_value_paise_success(
        self, db: AsyncSession, sample_member: Member, sample_staff: Staff
    ):
        """Redeem valid value_paise voucher credits wallet and marks redeemed."""
        # Create voucher via repo
        await voucher_repo.create(
            db,
            code="VOUCHER1234",
            value_paise=25000,
            batch_id="batch1",
        )

        member = await VoucherService.redeem(db, code="VOUCHER1234", member_id=sample_member.id)

        assert member.wallet_balance_paise == 25000

        # Verify voucher status
        from sqlalchemy import select
        result = await db.execute(select(Voucher).where(Voucher.code == "VOUCHER1234"))
        voucher = result.scalar_one()
        assert voucher.status == VoucherStatus.REDEEMED
        assert voucher.redeemed_by_member_id == sample_member.id
        assert voucher.redeemed_at is not None

        # Verify audit log
        logs = await audit_service.list_logs(
            db, action=AuditAction.VOUCHER_REDEEMED, entity_id=sample_member.id
        )
        assert len(logs) == 1
        assert "VOUCHER1234" in logs[0].detail
        assert "25000" in logs[0].detail

    async def test_redeem_value_minutes_not_credited_to_wallet(
        self, db: AsyncSession, sample_member: Member, sample_staff: Staff
    ):
        """Redeem value_minutes voucher does NOT credit wallet (handled by package drawdown)."""
        await voucher_repo.create(
            db,
            code="TIMEVOUCHER1",
            value_minutes=120,
            batch_id="batch1",
        )

        member = await VoucherService.redeem(db, code="TIMEVOUCHER1", member_id=sample_member.id)

        # Wallet unchanged for time vouchers
        assert member.wallet_balance_paise == 0
        # But voucher still marked redeemed
        from sqlalchemy import select
        result = await db.execute(select(Voucher).where(Voucher.code == "TIMEVOUCHER1"))
        voucher = result.scalar_one()
        assert voucher.status == VoucherStatus.REDEEMED

    async def test_redeem_expired_voucher_raises(
        self, db: AsyncSession, sample_member: Member, sample_staff: Staff
    ):
        """Redeem expired voucher raises 400."""
        await voucher_repo.create(
            db,
            code="EXPIREDVOUCH",
            value_paise=10000,
            expires_at=datetime.now(UTC) - timedelta(days=1),
            batch_id="batch1",
        )

        with pytest.raises(Exception) as exc:
            await VoucherService.redeem(db, code="EXPIREDVOUCH", member_id=sample_member.id)
        assert exc.value.status_code == 400
        assert "expired" in exc.value.detail.lower()

    async def test_redeem_already_redeemed_voucher_raises(
        self, db: AsyncSession, sample_member: Member, sample_staff: Staff
    ):
        """Redeem already-redeemed voucher raises 400."""
        # Create voucher via repo then update to REDEEMED
        voucher = await voucher_repo.create(
            db,
            code="USEDVOUCHER1",
            value_paise=10000,
            batch_id="batch1",
        )
        voucher.status = VoucherStatus.REDEEMED
        voucher.redeemed_by_member_id = sample_member.id
        voucher.redeemed_at = datetime.now(UTC)
        await voucher_repo.update(db, voucher)

        with pytest.raises(Exception) as exc:
            await VoucherService.redeem(db, code="USEDVOUCHER1", member_id=sample_member.id)
        assert exc.value.status_code == 400
        assert "redeemed" in exc.value.detail.lower()

    async def test_redeem_nonexistent_voucher_raises(
        self, db: AsyncSession, sample_member: Member
    ):
        """Redeem non-existent voucher raises 404."""
        with pytest.raises(Exception) as exc:
            await VoucherService.redeem(db, code="NONEXISTENT1", member_id=sample_member.id)
        assert exc.value.status_code == 404

    async def test_redeem_member_not_found(
        self, db: AsyncSession, sample_staff: Staff
    ):
        """Redeem for non-existent member raises 404."""
        await voucher_repo.create(
            db, code="VOUCHER123456", value_paise=10000, batch_id="batch1"
        )

        with pytest.raises(Exception) as exc:
            await VoucherService.redeem(db, code="VOUCHER123456", member_id="nonexistent")
        assert exc.value.status_code == 404

    async def test_redeem_feature_flag_disabled(
        self, db: AsyncSession, sample_member: Member, sample_staff: Staff
    ):
        """Redeem raises 503 when feature flag is off."""
        from backend.core.feature_flags import invalidate_cache

        invalidate_cache()

        await voucher_repo.create(
            db, code="VOUCHER123456", value_paise=10000, batch_id="batch1"
        )

        with pytest.raises(Exception) as exc:
            await VoucherService.redeem(db, code="VOUCHER123456", member_id=sample_member.id)
        assert exc.value.status_code == 503
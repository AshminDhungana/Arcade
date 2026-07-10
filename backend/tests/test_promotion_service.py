"""Tests for PromotionService."""

from __future__ import annotations

import tempfile
from collections.abc import AsyncGenerator
from datetime import UTC, datetime
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.core.database import Base
from backend.models import Seat, Staff, Zone
from backend.models._enums import DiscountType, PricingModel, PromotionType
from backend.models.settings import AppSettings
from backend.repositories import seat_repo, zone_repo
from backend.services.promotion_service import PromotionService


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
            # Enable promotions feature flag
            await session.execute(
                insert(AppSettings).values(key="enable_promotions", value="true")
            )
            await session.commit()
            from backend.core.feature_flags import load_flags

            await load_flags(session)
            yield session
        await engine.dispose()
    finally:
        Path(db_path).unlink(missing_ok=True)


@pytest_asyncio.fixture
async def sample_zone(db: AsyncSession) -> Zone:
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
    return await seat_repo.create(
        db, name="Seat 1", zone_id=sample_zone.id, mac_address="AA:BB:CC:DD:EE:FF"
    )


@pytest_asyncio.fixture
async def sample_staff(db: AsyncSession):
    """Create a stub staff member with a pin hash (no real authentication)."""
    from backend.repositories import staff_repo

    return await staff_repo.create(
        db,
        name="Test Staff",
        pin_hash="$argon2id$v=19$m=102400,t=2,p=8$fakehashplaceholder",
        role="CASHIER",
    )


class TestGetApplicablePromotion:
    async def test_no_active_promotion_returns_none(
        self, db: AsyncSession, sample_seat: Seat
    ):
        """When no promotions exist, returns None."""
        result = await PromotionService.get_applicable_promotion(
            db,
            seat_id=sample_seat.id,
            member_id=None,
            time_now=datetime(2026, 7, 10, 12, 0, tzinfo=UTC),
        )
        assert result is None

    async def test_inactive_promotion_ignored(
        self, db: AsyncSession, sample_seat: Seat
    ):
        """Inactive promotion is not matched."""
        from backend.repositories import promotion_repo

        await promotion_repo.create(
            db,
            name="Inactive Promo",
            type=PromotionType.HAPPY_HOUR.value,
            discount_type=DiscountType.PERCENTAGE.value,
            discount_value=20,
            active_from_hour=10,
            active_to_hour=14,
            is_active=False,
        )

        result = await PromotionService.get_applicable_promotion(
            db,
            seat_id=sample_seat.id,
            member_id=None,
            time_now=datetime(2026, 7, 10, 12, 0, tzinfo=UTC),
        )
        assert result is None

    async def test_happy_hour_time_window_match(
        self, db: AsyncSession, sample_seat: Seat
    ):
        """Promotion active during time window matches."""
        from backend.repositories import promotion_repo

        await promotion_repo.create(
            db,
            name="Happy Hour 10-14",
            type=PromotionType.HAPPY_HOUR.value,
            discount_type=DiscountType.PERCENTAGE.value,
            discount_value=20,
            active_from_hour=10,
            active_to_hour=14,
            is_active=True,
        )

        # 12:00 is within 10:00-14:00
        result = await PromotionService.get_applicable_promotion(
            db,
            seat_id=sample_seat.id,
            member_id=None,
            time_now=datetime(2026, 7, 10, 12, 0, tzinfo=UTC),
        )
        assert result is not None
        assert result.name == "Happy Hour 10-14"

    async def test_happy_hour_time_window_mismatch(
        self, db: AsyncSession, sample_seat: Seat
    ):
        """Promotion outside time window does not match."""
        from backend.repositories import promotion_repo

        await promotion_repo.create(
            db,
            name="Happy Hour 10-14",
            type=PromotionType.HAPPY_HOUR.value,
            discount_type=DiscountType.PERCENTAGE.value,
            discount_value=20,
            active_from_hour=10,
            active_to_hour=14,
            is_active=True,
        )

        # 15:00 is outside 10:00-14:00
        result = await PromotionService.get_applicable_promotion(
            db,
            seat_id=sample_seat.id,
            member_id=None,
            time_now=datetime(2026, 7, 10, 15, 0, tzinfo=UTC),
        )
        assert result is None

    async def test_day_of_week_match(self, db: AsyncSession, sample_seat: Seat):
        """Promotion with active_days matches only on those days."""
        from backend.repositories import promotion_repo

        await promotion_repo.create(
            db,
            name="Weekday Special",
            type=PromotionType.FLASH.value,
            discount_type=DiscountType.PERCENTAGE.value,
            discount_value=15,
            active_days="MON,WED,FRI",
            is_active=True,
        )

        # 2026-07-10 is a Friday
        result = await PromotionService.get_applicable_promotion(
            db,
            seat_id=sample_seat.id,
            member_id=None,
            time_now=datetime(2026, 7, 10, 12, 0, tzinfo=UTC),
        )
        assert result is not None
        assert result.name == "Weekday Special"

        # 2026-07-11 is a Saturday — should NOT match
        result = await PromotionService.get_applicable_promotion(
            db,
            seat_id=sample_seat.id,
            member_id=None,
            time_now=datetime(2026, 7, 11, 12, 0, tzinfo=UTC),
        )
        assert result is None

    async def test_first_match_priority(self, db: AsyncSession, sample_seat: Seat):
        """Multiple matching promotions -> returns first (by creation order)."""
        from backend.repositories import promotion_repo

        # Create first promo
        await promotion_repo.create(
            db,
            name="First Promo",
            type=PromotionType.HAPPY_HOUR.value,
            discount_type=DiscountType.PERCENTAGE.value,
            discount_value=10,
            active_from_hour=10,
            active_to_hour=16,
            is_active=True,
        )
        # Create second promo (same window)
        await promotion_repo.create(
            db,
            name="Second Promo",
            type=PromotionType.FLASH.value,
            discount_type=DiscountType.PERCENTAGE.value,
            discount_value=25,
            active_from_hour=10,
            active_to_hour=16,
            is_active=True,
        )

        result = await PromotionService.get_applicable_promotion(
            db,
            seat_id=sample_seat.id,
            member_id=None,
            time_now=datetime(2026, 7, 10, 12, 0, tzinfo=UTC),
        )
        # Should return first-created (First Promo)
        assert result.name == "First Promo"

    async def test_zone_restriction_respected(
        self, db: AsyncSession, sample_zone: Zone, sample_seat: Seat
    ):
        """Promotion restricted to a zone only matches seats in that zone."""
        from backend.repositories import promotion_repo, seat_repo

        # Create second zone and seat
        zone2 = await zone_repo.create(
            db,
            name="Zone 2",
            rate_per_minute_paise=100,
            rate_per_hour_paise=6000,
            pricing_model=PricingModel.PER_MINUTE,
        )
        seat2 = await seat_repo.create(
            db, name="Seat 2", zone_id=zone2.id, mac_address="11:22:33:44:55:66"
        )

        await promotion_repo.create(
            db,
            name="Zone 1 Only",
            type=PromotionType.HAPPY_HOUR.value,
            discount_type=DiscountType.PERCENTAGE.value,
            discount_value=20,
            zone_restriction_id=sample_zone.id,
            active_from_hour=10,
            active_to_hour=16,
            is_active=True,
        )

        # Seat in Zone 1 matches
        result1 = await PromotionService.get_applicable_promotion(
            db,
            seat_id=sample_seat.id,  # sample_seat is in sample_zone (Zone 1)
            member_id=None,
            time_now=datetime(2026, 7, 10, 12, 0, tzinfo=UTC),
        )
        assert result1 is not None

        # Seat in Zone 2 does NOT match
        result2 = await PromotionService.get_applicable_promotion(
            db,
            seat_id=seat2.id,
            member_id=None,
            time_now=datetime(2026, 7, 10, 12, 0, tzinfo=UTC),
        )
        assert result2 is None

    async def test_first_visit_promo_matches_new_member(
        self, db: AsyncSession, sample_seat: Seat
    ):
        """FIRST_VISIT type matches only for members with zero visits."""
        from backend.repositories import member_repo, promotion_repo

        # Create new member (total_visits = 0 by default)
        new_member = await member_repo.create(db, name="New Member", phone="9998887777")

        # Create existing member (total_visits > 0)
        existing_member = await member_repo.create(
            db,
            name="Existing Member",
            phone="9998887778",
        )
        existing_member.total_visits = 5
        await member_repo.update(db, existing_member)

        # FIRST_VISIT promo
        await promotion_repo.create(
            db,
            name="Welcome Discount",
            type=PromotionType.FIRST_VISIT.value,
            discount_type=DiscountType.PERCENTAGE.value,
            discount_value=50,
            is_active=True,
        )

        # New member matches
        result_new = await PromotionService.get_applicable_promotion(
            db,
            seat_id=sample_seat.id,
            member_id=new_member.id,
            time_now=datetime(2026, 7, 10, 12, 0, tzinfo=UTC),
        )
        assert result_new is not None
        assert result_new.name == "Welcome Discount"

        # Existing member does NOT match
        result_existing = await PromotionService.get_applicable_promotion(
            db,
            seat_id=sample_seat.id,
            member_id=existing_member.id,
            time_now=datetime(2026, 7, 10, 12, 0, tzinfo=UTC),
        )
        assert result_existing is None

    async def test_birthday_promo_matches_birth_month(
        self, db: AsyncSession, sample_seat: Seat
    ):
        """BIRTHDAY type matches only when current month == member birth month."""
        from backend.repositories import member_repo, promotion_repo

        # Member with birth_month = 7 (July)
        bday_member = await member_repo.create(
            db, name="Birthday Boy", phone="9997776666", birth_month=7
        )

        # Member with birth_month = 1 (January)
        non_bday_member = await member_repo.create(
            db, name="Not Birthday", phone="9997776667", birth_month=1
        )

        await promotion_repo.create(
            db,
            name="Birthday Special",
            type=PromotionType.BIRTHDAY.value,
            discount_type=DiscountType.PERCENTAGE.value,
            discount_value=30,
            is_active=True,
        )

        # July 10 -> matches birth_month=7
        result_bday = await PromotionService.get_applicable_promotion(
            db,
            seat_id=sample_seat.id,
            member_id=bday_member.id,
            time_now=datetime(2026, 7, 10, 12, 0, tzinfo=UTC),
        )
        assert result_bday is not None

        # July 10 -> does NOT match birth_month=1
        result_non_bday = await PromotionService.get_applicable_promotion(
            db,
            seat_id=sample_seat.id,
            member_id=non_bday_member.id,
            time_now=datetime(2026, 7, 10, 12, 0, tzinfo=UTC),
        )
        assert result_non_bday is None

    async def test_group_promo_returns_promo(self, db: AsyncSession, sample_seat: Seat):
        """GROUP type returns promo (group size check deferred to session start)."""
        from backend.repositories import promotion_repo

        await promotion_repo.create(
            db,
            name="Group 3+ Discount",
            type=PromotionType.GROUP.value,
            discount_type=DiscountType.PERCENTAGE.value,
            discount_value=25,
            min_group_size=3,
            is_active=True,
        )

        # Note: GROUP promo matching logic may require session group context.
        # For now, verify it returns the promo (group size check deferred).
        result = await PromotionService.get_applicable_promotion(
            db,
            seat_id=sample_seat.id,
            member_id=None,  # No member for group walk-ins
            time_now=datetime(2026, 7, 10, 12, 0, tzinfo=UTC),
        )
        assert result is not None
        assert result.name == "Group 3+ Discount"

    async def test_valid_from_until_date_range(
        self, db: AsyncSession, sample_seat: Seat
    ):
        """Promotion valid_from/valid_until bounds respected."""
        from backend.repositories import promotion_repo

        await promotion_repo.create(
            db,
            name="Summer Sale",
            type=PromotionType.FLASH.value,
            discount_type=DiscountType.PERCENTAGE.value,
            discount_value=20,
            valid_from=datetime(2026, 6, 1, tzinfo=UTC),
            valid_until=datetime(2026, 8, 31, tzinfo=UTC),
            is_active=True,
        )

        # Within range
        result_in = await PromotionService.get_applicable_promotion(
            db,
            seat_id=sample_seat.id,
            member_id=None,
            time_now=datetime(2026, 7, 10, 12, 0, tzinfo=UTC),
        )
        assert result_in is not None

        # Before valid_from
        result_before = await PromotionService.get_applicable_promotion(
            db,
            seat_id=sample_seat.id,
            member_id=None,
            time_now=datetime(2026, 5, 15, 12, 0, tzinfo=UTC),
        )
        assert result_before is None

        # After valid_until
        result_after = await PromotionService.get_applicable_promotion(
            db,
            seat_id=sample_seat.id,
            member_id=None,
            time_now=datetime(2026, 9, 15, 12, 0, tzinfo=UTC),
        )
        assert result_after is None


class TestStorePromotionIdOnSession:
    async def test_store_promotion_id_on_session(
        self, db: AsyncSession, sample_seat: Seat
    ):
        """store_promotion_id_on_session writes promotion_id to session."""
        from backend.repositories import promotion_repo, session_repo

        promo = await promotion_repo.create(
            db,
            name="Test Promo",
            type=PromotionType.HAPPY_HOUR.value,
            discount_type=DiscountType.PERCENTAGE.value,
            discount_value=20,
            is_active=True,
        )

        from backend.services.session_service import start_session

        session = await start_session(db, seat_id=sample_seat.id, member_id=None)

        await PromotionService.store_promotion_id_on_session(
            db, session_id=session.id, promotion_id=promo.id
        )

        # Verify persisted
        updated = await session_repo.get_by_id(db, session.id)
        assert updated.promotion_id == promo.id

    async def test_store_none_clears_promotion_id(
        self, db: AsyncSession, sample_seat: Seat
    ):
        """Passing None clears the promotion_id."""
        from backend.repositories import promotion_repo, session_repo

        promo = await promotion_repo.create(
            db,
            name="Test Promo",
            type=PromotionType.HAPPY_HOUR.value,
            discount_type=DiscountType.PERCENTAGE.value,
            discount_value=20,
            is_active=True,
        )

        from backend.services.session_service import start_session

        session = await start_session(db, seat_id=sample_seat.id, member_id=None)

        # First set it
        await PromotionService.store_promotion_id_on_session(
            db, session_id=session.id, promotion_id=promo.id
        )
        updated = await session_repo.get_by_id(db, session.id)
        assert updated.promotion_id == promo.id

        # Then clear it
        await PromotionService.store_promotion_id_on_session(
            db, session_id=session.id, promotion_id=None
        )
        updated = await session_repo.get_by_id(db, session.id)
        assert updated.promotion_id is None

    async def test_store_on_nonexistent_session_raises(self, db: AsyncSession):
        """Non-existent session raises HTTPException 404."""
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc:
            await PromotionService.store_promotion_id_on_session(
                db, session_id="nonexistent", promotion_id="some-promo"
            )
        assert exc.value.status_code == 404


class TestPromotionIntegration:
    async def test_session_start_locks_promotion(
        self, db: AsyncSession, sample_seat: Seat
    ):
        """Session started during happy hour locks the promotion."""
        from backend.repositories import promotion_repo
        from backend.services.session_service import start_session

        # Create active happy hour promo
        await promotion_repo.create(
            db,
            name="Happy Hour",
            type=PromotionType.HAPPY_HOUR.value,
            discount_type=DiscountType.PERCENTAGE.value,
            discount_value=20,
            active_from_hour=10,
            active_to_hour=16,
            is_active=True,
        )

        # Start session at 12:00 (within window)
        from datetime import UTC, datetime

        fixed_now = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)
        session = await start_session(
            db, seat_id=sample_seat.id, member_id=None, staff=None, time_now=fixed_now
        )

        assert session.promotion_id is not None

        # Verify promotion matches
        from backend.repositories import promotion_repo as pr

        promo = await pr.get_by_id(db, session.promotion_id)
        assert promo.name == "Happy Hour"


class TestPromotionCheckout:
    async def test_promotion_discount_applied_at_checkout(
        self, db: AsyncSession, sample_seat: Seat, sample_staff: Staff
    ):
        """Session with promotion gets discount on invoice."""
        from datetime import UTC, datetime, timedelta

        from backend.models._enums import PaymentMethod
        from backend.repositories import promotion_repo, session_repo
        from backend.services.billing_service import checkout_session
        from backend.services.session_service import start_session

        # Create promo: 20% off, active all day
        await promotion_repo.create(
            db,
            name="Test Promo",
            type=PromotionType.HAPPY_HOUR.value,
            discount_type=DiscountType.PERCENTAGE.value,
            discount_value=20,
            active_from_hour=0,
            active_to_hour=23,
            is_active=True,
        )

        # Start session
        session = await start_session(
            db, seat_id=sample_seat.id, member_id=None, staff=sample_staff
        )
        assert session.promotion_id is not None

        # Simulate 60 minutes elapsed (1 hour)
        db_session = await session_repo.get_by_id(db, session.id)
        db_session.started_at = datetime.now(UTC) - timedelta(minutes=60)
        await session_repo.update(db, db_session)

        # Checkout
        invoice = await checkout_session(
            db,
            session_id=session.id,
            payment_method=PaymentMethod.CASH,
            staff=sample_staff,
        )

        # Rate is 100 paise/min (from sample_zone fixture)
        # 60 min = 6000 paise, 20% discount = 1200 paise
        assert invoice.discount_paise == 1200
        assert invoice.total_paise == 6000 - 1200  # 4800

        # Check line item
        from backend.models._enums import InvoiceLineItemType
        from backend.repositories import invoice_repo

        line_items = await invoice_repo.list_line_items(db, invoice.id)
        discount_lines = [
            li for li in line_items if li.type == InvoiceLineItemType.DISCOUNT
        ]
        assert len(discount_lines) == 1
        assert discount_lines[0].total_paise == 1200
        assert "Promotion" in discount_lines[0].description

    async def test_fixed_paise_promotion(
        self, db: AsyncSession, sample_seat: Seat, sample_staff: Staff
    ):
        """FIXED_PAISE promotion discounts exact amount."""
        from datetime import UTC, datetime, timedelta

        from backend.models._enums import PaymentMethod
        from backend.repositories import promotion_repo, session_repo
        from backend.services.billing_service import checkout_session
        from backend.services.session_service import start_session

        # FIXED_PAISE: 3000 paise off
        await promotion_repo.create(
            db,
            name="Flat Discount",
            type=PromotionType.FLASH.value,
            discount_type=DiscountType.FIXED_PAISE.value,
            discount_value=3000,
            active_from_hour=0,
            active_to_hour=23,
            is_active=True,
        )

        session = await start_session(
            db, seat_id=sample_seat.id, member_id=None, staff=sample_staff
        )

        db_session = await session_repo.get_by_id(db, session.id)
        db_session.started_at = datetime.now(UTC) - timedelta(minutes=60)
        await session_repo.update(db, db_session)

        invoice = await checkout_session(
            db,
            session_id=session.id,
            payment_method=PaymentMethod.CASH,
            staff=sample_staff,
        )

        # 6000 - 3000 = 3000 (capped at time_charge)
        assert invoice.discount_paise == 3000
        assert invoice.total_paise == 3000

    async def test_promotion_discount_capped_at_time_charge(
        self, db: AsyncSession, sample_seat: Seat, sample_staff: Staff
    ):
        """Promotion discount never exceeds time charge."""
        from datetime import UTC, datetime, timedelta

        from backend.models._enums import PaymentMethod
        from backend.repositories import promotion_repo, session_repo
        from backend.services.billing_service import checkout_session
        from backend.services.session_service import start_session

        # FIXED_PAISE larger than time charge
        await promotion_repo.create(
            db,
            name="Huge Discount",
            type=PromotionType.FLASH.value,
            discount_type=DiscountType.FIXED_PAISE.value,
            discount_value=10000,  # More than 60 min at 100/min = 6000
            active_from_hour=0,
            active_to_hour=23,
            is_active=True,
        )

        session = await start_session(
            db, seat_id=sample_seat.id, member_id=None, staff=sample_staff
        )

        db_session = await session_repo.get_by_id(db, session.id)
        db_session.started_at = datetime.now(UTC) - timedelta(minutes=60)
        await session_repo.update(db, db_session)

        invoice = await checkout_session(
            db,
            session_id=session.id,
            payment_method=PaymentMethod.CASH,
            staff=sample_staff,
        )

        # Discount capped at time_charge (6000)
        assert invoice.discount_paise == 6000
        assert invoice.total_paise == 0  # floor at 0

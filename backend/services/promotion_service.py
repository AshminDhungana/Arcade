"""PromotionService — business logic for promotion matching and application.

Evaluates active promotions at session start and applies the first matching
promotion (FR-PROMO-003). Promotion is locked on the session record.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.feature_flags import get_flag
from backend.core.ws_manager import manager as ws_manager
from backend.models import Promotion
from backend.models._enums import DiscountType, PromotionType
from backend.repositories import member_repo, promotion_repo, seat_repo, session_repo

if TYPE_CHECKING:
    from backend.models._enums import PricingModel

logger = logging.getLogger(__name__)


def _ensure_utc(dt: datetime | None) -> datetime | None:
    """Ensure a timezone-aware datetime.

    SQLite sometimes strips timezone info; re-attach UTC when missing.
    """
    if dt is not None and (dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None):
        return dt.replace(tzinfo=UTC)
    return dt


class PromotionNotFoundError(HTTPException):
    def __init__(self, promotion_id: str) -> None:
        super().__init__(status_code=404, detail=f"Promotion {promotion_id} not found")


class PromotionInactiveError(HTTPException):
    def __init__(self, promotion_id: str) -> None:
        super().__init__(
            status_code=400, detail=f"Promotion {promotion_id} is inactive"
        )


class PromotionService:
    @staticmethod
    async def get_applicable_promotion(
        db: AsyncSession,
        *,
        seat_id: str,
        member_id: str | None = None,
        time_now: datetime | None = None,
    ) -> Promotion | None:
        """Return the first active promotion matching all criteria for the seat.

        Matching rules (FR-PROMO-001, FR-PROMO-003):
        1. Promotion must be `is_active=True`
        2. Current time within `active_from_hour`–`active_to_hour` (if set)
        3. Current day of week in `active_days` (if set, comma-separated MON-SUN)
        4. Current date within `valid_from`–`valid_until` (if set)
        5. Seat's zone matches `zone_restriction_id` (if set)
        6. Type-specific checks:
           - FIRST_VISIT: member must exist and have `total_visits == 0`
           - BIRTHDAY: member must exist and `birth_month == time_now.month`
           - GROUP: `min_group_size` validated at session start (see Task 4)
        7. Returns first match by creation order (list() returns PK order)

        Args:
            db: Database session
            seat_id: Seat where session will start
            member_id: Optional member ID (for member-specific promos)
            time_now: Timestamp to evaluate against (defaults to UTC now)

        Returns:
            Matching Promotion or None
        """
        if not get_flag("enable_promotions"):
            return None

        if time_now is None:
            time_now = datetime.now(UTC)
        if time_now.tzinfo is None or time_now.tzinfo.utcoffset(time_now) is None:
            time_now = time_now.replace(tzinfo=UTC)

        # Load seat to get zone_id for zone restriction check
        seat = await seat_repo.get_by_id(db, seat_id)
        if seat is None:
            raise HTTPException(status_code=404, detail=f"Seat {seat_id} not found")

        promotions = await promotion_repo.list(db)

        for promo in promotions:
            if not promo.is_active:
                continue

            # 2. Time window check (hour of day)
            if promo.active_from_hour is not None:
                if time_now.hour < promo.active_from_hour:
                    continue
            if promo.active_to_hour is not None:
                if time_now.hour >= promo.active_to_hour:
                    continue

            # 3. Day of week check
            if promo.active_days:
                current_day = time_now.strftime("%a").upper()  # MON, TUE, ...
                allowed_days = [d.strip().upper() for d in promo.active_days.split(",")]
                if current_day not in allowed_days:
                    continue

            # 4. Date range check (ensure timezone-aware comparison)
            valid_from = _ensure_utc(promo.valid_from)
            valid_until = _ensure_utc(promo.valid_until)
            if valid_from and time_now < valid_from:
                continue
            if valid_until and time_now > valid_until:
                continue

            # 5. Zone restriction
            if promo.zone_restriction_id and promo.zone_restriction_id != seat.zone_id:
                continue

            # 6. Type-specific member checks
            if promo.type == PromotionType.FIRST_VISIT:
                if not member_id:
                    continue
                member = await member_repo.get_by_id(db, member_id)
                if member is None or member.total_visits > 0:
                    continue

            elif promo.type == PromotionType.BIRTHDAY:
                if not member_id:
                    continue
                member = await member_repo.get_by_id(db, member_id)
                if member is None or member.birth_month != time_now.month:
                    continue

            # GROUP: min_group_size checked at session start with group context

            # All checks passed — return this promotion
            logger.info(
                "Promotion matched: %s (id=%s) for seat %s at %s",
                promo.name,
                promo.id,
                seat_id,
                time_now.isoformat(),
            )
            return promo

        return None

    @staticmethod
    async def store_promotion_id_on_session(
        db: AsyncSession,
        session_id: str,
        promotion_id: str | None,
    ) -> None:
        """Lock promotion_id on the session record at session start.

        Called by `SessionService.start_session()` after
        `get_applicable_promotion()` returns a match.

        Args:
            db: Database session
            session_id: GamingSession ID
            promotion_id: Promotion ID to lock, or None to clear
        """
        session = await session_repo.get_by_id(db, session_id)
        if session is None:
            raise HTTPException(
                status_code=404, detail=f"Session {session_id} not found"
            )

        session.promotion_id = promotion_id
        await session_repo.update(db, session)

        # WebSocket broadcast for session update
        try:
            await ws_manager.broadcast_to_dashboards(
                "session_updated",
                {
                    "id": session.id,
                    "seat_id": session.seat_id,
                    "member_id": session.member_id,
                    "status": session.status.value,
                    "promotion_id": session.promotion_id,
                    "started_at": session.started_at.isoformat()
                    if session.started_at
                    else None,
                },
            )
        except Exception as exc:  # pragma: no cover - non-blocking
            logger.debug("WebSocket broadcast failed: %s", exc)

    @staticmethod
    async def calculate_promotion_discount(
        db: AsyncSession,
        promotion: Promotion,
        time_charge_paise: int,
        session_duration_minutes: int,
        locked_rate_paise: int | None = None,
        locked_pricing_model: PricingModel | None = None,
    ) -> int:
        """Calculate discount amount in paise for a matched promotion.

        Args:
            db: Database session (for settings lookup if needed)
            promotion: Matched Promotion object
            time_charge_paise: Base time charge before discount
            session_duration_minutes: Session duration in minutes
            locked_rate_paise: Locked rate from session (for BONUS_MINUTES)
            locked_pricing_model: Locked pricing model from session

        Returns:
            Discount amount in paise (>= 0, never exceeds time_charge_paise)
        """
        discount_type = promotion.discount_type
        # Normalize: StrEnumColumn returns enum, but tests may pass string
        if isinstance(discount_type, str):
            try:
                discount_type = DiscountType(discount_type)
            except ValueError:
                return 0

        if discount_type == DiscountType.PERCENTAGE:
            # discount_value is percentage (e.g., 20 = 20%)
            discount = (time_charge_paise * promotion.discount_value) // 100
            return min(discount, time_charge_paise)

        if discount_type == DiscountType.FIXED_PAISE:
            # discount_value is fixed paise amount
            return min(promotion.discount_value, time_charge_paise)

        if discount_type == DiscountType.BONUS_MINUTES:
            # discount_value is bonus minutes — convert to paise equivalent
            # Requires locked rate to compute per-minute value
            if locked_rate_paise is None or locked_pricing_model is None:
                return 0
            from backend.services.billing_service import LockedRate, _per_minute_rate

            locked = LockedRate(
                rate_paise=locked_rate_paise,
                pricing_model=locked_pricing_model,
                block_minutes=None,
            )
            per_min = _per_minute_rate(locked)
            bonus_paise = promotion.discount_value * per_min
            return min(bonus_paise, time_charge_paise)

        return 0

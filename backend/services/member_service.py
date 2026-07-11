"""MemberService — business logic for member management."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.feature_flags import get_flag
from backend.core.ws_manager import manager as ws_manager
from backend.models import Member, Voucher
from backend.models._enums import AuditAction, MemberTier, VoucherStatus
from backend.models.settings import AppSettings
from backend.repositories import member_repo, voucher_repo
from backend.services import audit_service

if TYPE_CHECKING:
    from backend.models.staff import Staff


logger = logging.getLogger(__name__)


def _ensure_tz(dt: datetime | None) -> datetime | None:
    """Ensure a timezone-aware datetime.

    SQLite sometimes strips timezone info; re-attach UTC when missing.
    """
    if dt is not None and (dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None):
        return dt.replace(tzinfo=UTC)
    return dt


class DuplicatePhoneError(HTTPException):
    """Raised when attempting to create a member with an existing phone number."""

    def __init__(self, phone: str) -> None:
        super().__init__(
            status_code=409,
            detail=f"Phone number {phone} already registered",
        )


class MemberNotFoundError(HTTPException):
    """Raised when a member is not found."""

    def __init__(self, member_id: str) -> None:
        super().__init__(status_code=404, detail=f"Member {member_id} not found")


class MemberService:
    @staticmethod
    async def create_member(
        db: AsyncSession,
        *,
        name: str,
        phone: str,
    ) -> Member:
        """Create a new member with BRONZE tier."""
        # Check phone uniqueness
        existing = await member_repo.get_by_phone(db, phone)
        if existing:
            raise DuplicatePhoneError(phone)

        # Create member with defaults
        member = await member_repo.create(
            db,
            name=name,
            phone=phone,
            wallet_balance_paise=0,
            loyalty_points=0,
            tier=MemberTier.BRONZE.value,
            birth_month=None,
        )

        # Broadcast member update
        try:
            await ws_manager.broadcast_to_dashboards(
                "member_updated",
                {
                    "id": member.id,
                    "name": member.name,
                    "phone": member.phone,
                    "wallet_balance_paise": member.wallet_balance_paise,
                    "loyalty_points": member.loyalty_points,
                    "tier": member.tier.value,
                    "total_visits": member.total_visits,
                    "total_seconds_played": member.total_seconds_played,
                },
            )
        except Exception as exc:  # pragma: no cover - non-blocking
            logger.debug("WebSocket broadcast failed: %s", exc)

        return member

    @staticmethod
    async def get_member(db: AsyncSession, member_id: str) -> Member:
        """Get member by ID. Raises 404 if not found."""
        member = await member_repo.get_by_id(db, member_id)
        if member is None:
            raise MemberNotFoundError(member_id)
        return member

    @staticmethod
    async def search_members(
        db: AsyncSession, query: str, limit: int = 50, offset: int = 0
    ) -> Sequence[Member]:
        """Search members by name or phone using ILIKE pattern."""
        if not query or not query.strip():
            return []
        return await member_repo.search(db, query.strip(), limit=limit, offset=offset)

    @staticmethod
    async def list_members(
        db: AsyncSession, limit: int = 50, offset: int = 0
    ) -> Sequence[Member]:
        """Return all members (paginated)."""
        return await member_repo.list(db, limit=limit, offset=offset)

    @staticmethod
    async def topup_wallet(
        db: AsyncSession,
        *,
        member_id: str,
        amount_paise: int,
        payment_method: str,
        staff: Staff | None = None,
    ) -> Member:
        """Add funds to member wallet and log audit entry."""
        from backend.models._enums import PaymentMethod as PaymentMethodEnum

        if amount_paise <= 0:
            raise HTTPException(status_code=400, detail="amount_paise must be positive")

        member = await MemberService.get_member(db, member_id)

        member.wallet_balance_paise += amount_paise
        member = await member_repo.update(db, member)

        # Audit log
        payment_method_val = PaymentMethodEnum(payment_method).value
        await audit_service.log(
            db,
            action=AuditAction.WALLET_TOPUP,
            entity_type="member",
            entity_id=member.id,
            staff_id=staff.id if staff else None,
            detail=f"{amount_paise} paise via {payment_method_val}",
        )

        # Broadcast
        try:
            await ws_manager.broadcast_to_dashboards(
                "member_updated",
                {
                    "id": member.id,
                    "wallet_balance_paise": member.wallet_balance_paise,
                    "loyalty_points": member.loyalty_points,
                    "tier": member.tier.value,
                },
            )
        except Exception as exc:  # pragma: no cover - non-blocking
            logger.debug("WebSocket broadcast failed: %s", exc)

        return member

    @staticmethod
    async def redeem_voucher_to_wallet(
        db: AsyncSession,
        member_id: str,
        code: str,
    ) -> Member:
        """Redeem a voucher to member wallet."""
        member = await MemberService.get_member(db, member_id)

        # Find voucher by code
        result = await db.execute(select(Voucher).where(Voucher.code == code))
        voucher = result.scalar_one_or_none()

        if voucher is None:
            raise HTTPException(status_code=404, detail="Voucher not found")

        if voucher.status != VoucherStatus.UNUSED:
            raise HTTPException(
                status_code=400,
                detail="Voucher already redeemed or expired",
            )

        if voucher.expires_at:
            expires_at = _ensure_tz(voucher.expires_at)
            if expires_at is not None and expires_at < datetime.now(UTC):
                voucher.status = VoucherStatus.EXPIRED
                await db.flush()
                raise HTTPException(status_code=400, detail="Voucher expired")

        # Add value to wallet
        if voucher.value_paise:
            member.wallet_balance_paise += voucher.value_paise
        # Note: value_minutes handled in package drawdown, not wallet

        member = await member_repo.update(db, member)

        # Mark voucher redeemed
        voucher.status = VoucherStatus.REDEEMED
        voucher.redeemed_by_member_id = member.id
        voucher.redeemed_at = datetime.now(UTC)
        await voucher_repo.update(db, voucher)

        # Audit
        await audit_service.log(
            db,
            action=AuditAction.VOUCHER_REDEEMED,
            entity_type="member",
            entity_id=member.id,
            staff_id=None,
            detail=f"Voucher {code} redeemed for {voucher.value_paise} paise",
        )

        # Broadcast
        try:
            await ws_manager.broadcast_to_dashboards(
                "member_updated",
                {
                    "id": member.id,
                    "wallet_balance_paise": member.wallet_balance_paise,
                    "loyalty_points": member.loyalty_points,
                    "tier": member.tier.value,
                },
            )
        except Exception as exc:  # pragma: no cover - non-blocking
            logger.debug("WebSocket broadcast failed: %s", exc)

        return member

    @staticmethod
    async def add_loyalty_points(
        db: AsyncSession,
        member_id: str,
        session_duration_seconds: int,
    ) -> Member:
        """Add loyalty points based on session duration; check and upgrade tier."""
        member = await MemberService.get_member(db, member_id)

        # Check if members feature is enabled
        if not get_flag("enable_members"):
            return member

        # Get points per minute from settings
        result = await db.execute(
            select(AppSettings).where(AppSettings.key == "loyalty_points_per_minute")
        )
        setting = result.scalar_one_or_none()
        points_per_minute = int(setting.value) if setting else 1

        # Calculate points (1 point per minute by default)
        minutes = max(1, int(session_duration_seconds / 60))  # Minimum 1 minute
        points_earned = minutes * points_per_minute

        member.loyalty_points += points_earned
        member.total_seconds_played += session_duration_seconds

        # Check tier thresholds
        old_tier = member.tier

        # Get thresholds from settings
        silver_result = await db.execute(
            select(AppSettings).where(AppSettings.key == "tier_silver_threshold")
        )
        silver_setting = silver_result.scalar_one_or_none()
        silver_threshold = int(silver_setting.value) if silver_setting else 500

        gold_result = await db.execute(
            select(AppSettings).where(AppSettings.key == "tier_gold_threshold")
        )
        gold_setting = gold_result.scalar_one_or_none()
        gold_threshold = int(gold_setting.value) if gold_setting else 1000

        # Determine new tier
        if member.loyalty_points >= gold_threshold:
            member.tier = MemberTier.GOLD
        elif member.loyalty_points >= silver_threshold:
            member.tier = MemberTier.SILVER
        else:
            member.tier = MemberTier.BRONZE

        if member.tier != old_tier:
            # Tier upgraded - this could trigger a notification or special handling
            pass

        member = await member_repo.update(db, member)

        # Broadcast
        try:
            await ws_manager.broadcast_to_dashboards(
                "member_updated",
                {
                    "id": member.id,
                    "wallet_balance_paise": member.wallet_balance_paise,
                    "loyalty_points": member.loyalty_points,
                    "tier": member.tier.value,
                    "total_seconds_played": member.total_seconds_played,
                    "total_visits": member.total_visits,
                },
            )
        except Exception as exc:  # pragma: no cover - non-blocking
            logger.debug("WebSocket broadcast failed: %s", exc)

        return member

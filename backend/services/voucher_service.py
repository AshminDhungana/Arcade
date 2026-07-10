"""VoucherService — business logic for voucher batch generation and redemption."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.feature_flags import get_flag
from backend.core.ws_manager import manager as ws_manager
from backend.models import Member
from backend.models._enums import AuditAction, VoucherStatus
from backend.repositories import member_repo, voucher_repo
from backend.schemas.voucher import VoucherBatchResponse
from backend.services import audit_service

if TYPE_CHECKING:
    from backend.models.staff import Staff


logger = logging.getLogger(__name__)


class VoucherGenerationError(HTTPException):
    def __init__(self, detail: str) -> None:
        super().__init__(status_code=400, detail=detail)


class VoucherRedemptionError(HTTPException):
    def __init__(self, detail: str, status_code: int = 400) -> None:
        super().__init__(status_code=status_code, detail=detail)


def _ensure_tz(dt: datetime | None) -> datetime | None:
    """Ensure a timezone-aware datetime.

    SQLite sometimes strips timezone info; re-attach UTC when missing.
    """
    if dt is not None and (dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None):
        return dt.replace(tzinfo=UTC)
    return dt


class VoucherService:
    @staticmethod
    async def generate_batch(
        db: AsyncSession,
        *,
        count: int,
        value_paise: int | None = None,
        value_minutes: int | None = None,
        expires_in_days: int | None = None,
        staff: Staff | None = None,
    ) -> VoucherBatchResponse:
        """Generate a batch of vouchers with unique codes.

        Args:
            db: Async database session
            count: Number of vouchers to generate (1-10000)
            value_paise: Monetary value in paise (mutually exclusive with value_minutes)
            value_minutes: Time value in minutes (mutually exclusive with value_paise)
            expires_in_days: Days until vouchers expire from now (optional)
            staff: Staff member generating the batch (for audit)

        Returns:
            VoucherBatchResponse with batch_id, count, and list of vouchers

        Raises:
            HTTPException(503): If enable_vouchers feature flag is disabled
            HTTPException(400): If count is invalid or both/neither value set
        """
        # Check feature flag
        if not get_flag("enable_vouchers"):
            raise HTTPException(
                status_code=503, detail="Voucher generation is currently disabled"
            )

        # Validate inputs
        if count <= 0 or count > 10000:
            raise VoucherGenerationError("count must be between 1 and 10000")
        if value_paise is not None and value_minutes is not None:
            raise VoucherGenerationError(
                "Only one of value_paise or value_minutes may be set"
            )
        if value_paise is None and value_minutes is None:
            raise VoucherGenerationError(
                "Either value_paise or value_minutes must be set"
            )
        if value_paise is not None and value_paise <= 0:
            raise VoucherGenerationError("value_paise must be positive")
        if value_minutes is not None and value_minutes <= 0:
            raise VoucherGenerationError("value_minutes must be positive")

        # Generate batch ID
        batch_id = uuid.uuid4().hex

        # Create vouchers via repository
        vouchers = await voucher_repo.create_batch(
            db,
            count=count,
            value_paise=value_paise,
            value_minutes=value_minutes,
            expires_in_days=expires_in_days,
            batch_id=batch_id,
        )

        # Audit log
        value_desc = (
            f"{value_paise} paise" if value_paise else f"{value_minutes} minutes"
        )
        expiry_desc = f", expires in {expires_in_days} days" if expires_in_days else ""
        await audit_service.log(
            db,
            action=AuditAction.VOUCHER_GENERATED,
            entity_type="voucher_batch",
            entity_id=batch_id,
            staff_id=staff.id if staff else None,
            detail=(
                f"Generated {count} vouchers worth {value_desc}{expiry_desc}; "
                f"batch_id={batch_id}"
            ),
        )

        # Build response — convert ORM vouchers to VoucherResponse
        # Need to ensure timezone-aware datetimes (SQLite strips tzinfo)
        for v in vouchers:
            v.expires_at = _ensure_tz(v.expires_at)
            v.created_at = _ensure_tz(v.created_at)  # type: ignore[assignment]
            if v.redeemed_at:
                v.redeemed_at = _ensure_tz(v.redeemed_at)

        voucher_responses = [
            VoucherBatchResponse.model_validate(
                {"batch_id": batch_id, "count": count, "vouchers": vouchers}
            )
        ][0].vouchers

        return VoucherBatchResponse(
            batch_id=batch_id,
            count=count,
            vouchers=voucher_responses,
        )

    @staticmethod
    async def redeem(
        db: AsyncSession,
        code: str,
        member_id: str,
    ) -> Member:
        """Redeem a voucher to a member's wallet.

        Validates voucher exists, is unused, not expired. If value_paise is set,
        credits member wallet. If value_minutes is set, wallet is NOT credited
        (time vouchers are handled via package drawdown at session checkout).

        Args:
            db: Async database session
            code: 12-character voucher code
            member_id: Member ID to credit

        Returns:
            Updated Member with new wallet balance

        Raises:
            HTTPException(404): Voucher or member not found
            HTTPException(400): Voucher already redeemed, expired, or invalid
            HTTPException(503): If enable_vouchers feature flag is disabled
        """
        # Check feature flag
        if not get_flag("enable_vouchers"):
            raise HTTPException(
                status_code=503, detail="Voucher redemption is currently disabled"
            )

        # Find voucher by code
        voucher = await voucher_repo.get_by_code(db, code)
        if voucher is None:
            raise VoucherRedemptionError("Voucher not found", status_code=404)

        # Validate voucher status
        if voucher.status != VoucherStatus.UNUSED:
            if voucher.status == VoucherStatus.EXPIRED:
                raise VoucherRedemptionError("Voucher expired", status_code=400)
            raise VoucherRedemptionError("Voucher already redeemed", status_code=400)

        # Check expiry
        if voucher.expires_at is not None:
            expires_at = _ensure_tz(voucher.expires_at)
            if expires_at is not None and expires_at < datetime.now(UTC):
                voucher.status = VoucherStatus.EXPIRED
                await db.flush()
                raise VoucherRedemptionError("Voucher expired", status_code=400)

        # Get member
        member = await member_repo.get_by_id(db, member_id)
        if member is None:
            raise VoucherRedemptionError("Member not found", status_code=404)

        # Credit wallet if value_paise
        if voucher.value_paise is not None:
            member.wallet_balance_paise += voucher.value_paise
            member = await member_repo.update(db, member)

        # Mark voucher redeemed
        now = datetime.now(UTC)
        voucher.status = VoucherStatus.REDEEMED
        voucher.redeemed_by_member_id = member.id
        voucher.redeemed_at = now
        await voucher_repo.update(db, voucher)

        # Audit log
        value_desc = (
            f"{voucher.value_paise} paise"
            if voucher.value_paise
            else f"{voucher.value_minutes} minutes"
        )
        await audit_service.log(
            db,
            action=AuditAction.VOUCHER_REDEEMED,
            entity_type="member",
            entity_id=member.id,
            staff_id=None,  # Redemption typically by member, not staff
            detail=f"Voucher {code} redeemed for {value_desc}",
        )

        # Ensure timezone-aware datetimes for response (SQLite strips tzinfo)
        member.created_at = _ensure_tz(member.created_at)  # type: ignore[assignment]
        member.updated_at = _ensure_tz(member.updated_at)  # type: ignore[assignment]

        # Broadcast member update
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

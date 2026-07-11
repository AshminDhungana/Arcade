"""PackageService — business logic for selling and managing time packages."""

from __future__ import annotations

import logging
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.feature_flags import get_flag
from backend.core.ws_manager import manager as ws_manager
from backend.models import Package
from backend.models._enums import (
    AuditAction,
    EntitlementStatus,
    PaymentMethod,
)
from backend.models.package_entitlement import MemberPackageEntitlement
from backend.repositories import member_repo, package_repo, wallet_transaction_repo
from backend.services import audit_service

if TYPE_CHECKING:
    from backend.models.staff import Staff


logger = logging.getLogger(__name__)


class PackageNotFoundError(HTTPException):
    def __init__(self, package_id: str) -> None:
        super().__init__(status_code=404, detail=f"Package {package_id} not found")


class PackageInactiveError(HTTPException):
    def __init__(self, package_id: str) -> None:
        super().__init__(status_code=400, detail=f"Package {package_id} is inactive")


class InsufficientWalletError(HTTPException):
    def __init__(self, member_id: str) -> None:
        super().__init__(
            status_code=400,
            detail=f"Member {member_id} has insufficient wallet balance",
        )


class MemberNotFoundError(HTTPException):
    def __init__(self, member_id: str) -> None:
        super().__init__(status_code=404, detail=f"Member {member_id} not found")


class PackageService:
    @staticmethod
    async def sell_package(
        db: AsyncSession,
        *,
        member_id: str,
        package_id: str,
        payment_method: str,
        staff: Staff | None = None,
    ) -> MemberPackageEntitlement:
        """Sell a package to a member.

        Creates a MemberPackageEntitlement, deducts from wallet if WALLET payment,
        records cash/card payment, and logs audit entry PACKAGE_SOLD.
        """
        # Check feature flag
        if not get_flag("enable_packages"):
            raise HTTPException(
                status_code=503, detail="Package sales are currently disabled"
            )

        # Validate member
        member = await member_repo.get_by_id(db, member_id)
        if member is None:
            raise MemberNotFoundError(member_id)

        # Validate package
        package = await package_repo.get_by_id(db, package_id)
        if package is None:
            raise PackageNotFoundError(package_id)
        if not package.is_active:
            raise PackageInactiveError(package_id)

        # Validate payment method
        try:
            payment_method_enum = PaymentMethod(payment_method)
        except ValueError as err:
            raise HTTPException(
                status_code=400, detail=f"Invalid payment method: {payment_method}"
            ) from err

        # Handle wallet payment
        if payment_method_enum == PaymentMethod.WALLET:
            if member.wallet_balance_paise < package.price_paise:
                raise InsufficientWalletError(member_id)
            member.wallet_balance_paise -= package.price_paise
            await member_repo.update(db, member)

        # Create entitlement
        entitlement = MemberPackageEntitlement(
            member_id=member_id,
            package_id=package_id,
            remaining_minutes=package.total_minutes,
            status=EntitlementStatus.ACTIVE,
        )
        if package.valid_days:
            from datetime import timedelta

            entitlement.expires_at = datetime.now(UTC) + timedelta(
                days=package.valid_days
            )

        db.add(entitlement)
        await db.flush()
        await db.refresh(entitlement)

        # Audit log
        await audit_service.log(
            db,
            action=AuditAction.PACKAGE_SOLD,
            entity_type="package_entitlement",
            entity_id=entitlement.id,
            staff_id=staff.id if staff else None,
            detail=(
                f"Sold package {package.name} ({package.total_minutes} min) "
                f"for {package.price_paise} paise via {payment_method_enum.value}"
            ),
        )

        # Ledger row (a package purchase is a spend; negative)
        await wallet_transaction_repo.create(
            db,
            member_id=member_id,
            type="PACKAGE_PURCHASE",
            amount_paise=-package.price_paise,
            balance_after_paise=member.wallet_balance_paise,
            payment_method=payment_method_enum.value,
            staff_id=staff.id if staff else None,
            reference_id=entitlement.id,
        )

        # Broadcast member update (wallet may have changed)
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

        return entitlement

    @staticmethod
    async def get_active_entitlement(
        db: AsyncSession,
        member_id: str,
    ) -> MemberPackageEntitlement | None:
        """Return the oldest active, non-expired entitlement for a member (FIFO)."""
        if not get_flag("enable_packages"):
            return None
        return await package_repo.get_active_entitlement(db, member_id)

    @staticmethod
    async def list_packages(db: AsyncSession) -> Sequence[Package]:
        """List all active packages available for sale."""
        if not get_flag("enable_packages"):
            return []
        all_packages = await package_repo.list(db)
        return [p for p in all_packages if p.is_active]

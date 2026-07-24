"""Package API router.

Routes::

    GET   /api/packages              → list active packages (cashier+)
    POST  /api/members/{id}/packages → sell package to member (cashier+)
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, Body, Depends, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import require_cashier
from backend.core.database import get_db
from backend.core.feature_flags import require_feature
from backend.models._enums import PaymentMethod
from backend.models.staff import Staff
from backend.schemas.package import (
    MemberPackageEntitlementResponse,
    PackageResponse,
    SellPackageRequest,
)
from backend.services.package_service import PackageService

router = APIRouter(prefix="/packages", tags=["packages"])

# Apply feature flag to all routes in this router
router.dependencies.append(Depends(require_feature("enable_packages")))


@router.get(
    "",
    response_model=Sequence[PackageResponse],
    summary="List all active packages available for sale",
)
async def list_packages(
    db: AsyncSession = Depends(get_db),  # noqa: B008
    _staff: Annotated[Staff | None, Depends(require_cashier)] = None,  # noqa: B008
) -> Sequence[PackageResponse]:
    """Return all active packages that can be sold to members."""
    packages = await PackageService.list_packages(db)
    return [PackageResponse.model_validate(p) for p in packages]


@router.post(
    "/members/{member_id}/packages",
    response_model=MemberPackageEntitlementResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Sell a package to a member",
)
async def sell_package_to_member(
    member_id: Annotated[str, Path(description="Member ID")],
    body: Annotated[SellPackageRequest, Body(description="Package sale details")],
    db: AsyncSession = Depends(get_db),  # noqa: B008
    staff: Annotated[Staff | None, Depends(require_cashier)] = None,  # noqa: B008
) -> MemberPackageEntitlementResponse:
    """Sell a package to a member.

    Deducts from wallet if payment_method=WALLET, otherwise records cash/card payment.
    Creates MemberPackageEntitlement with full minutes and optional expiry.
    """
    entitlement = await PackageService.sell_package(
        db,
        member_id=member_id,
        package_id=body.package_id,
        payment_method=(
            body.payment_method.value
            if isinstance(body.payment_method, PaymentMethod)
            else body.payment_method
        ),
        staff=staff,
    )
    return MemberPackageEntitlementResponse.model_validate(entitlement)

"""Voucher API router.

Routes::
    POST  /api/vouchers/batch      → generate voucher batch (Admin)
    POST  /api/vouchers/redeem     → redeem voucher for member (Cashier+)
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Body, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import require_admin, require_cashier
from backend.core.database import get_db
from backend.core.feature_flags import require_feature
from backend.models.staff import Staff
from backend.schemas.member import MemberResponse
from backend.schemas.voucher import (
    VoucherBatchCreate,
    VoucherBatchResponse,
    VoucherRedeemRequest,
)
from backend.services.voucher_service import VoucherService

router = APIRouter(prefix="/vouchers", tags=["vouchers"])

# Apply feature flag to all routes in this router
router.dependencies.append(Depends(require_feature("enable_vouchers")))


@router.post(
    "/batch",
    response_model=VoucherBatchResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate a batch of vouchers",
)
async def generate_voucher_batch(
    body: Annotated[
        VoucherBatchCreate, Body(description="Batch generation parameters")
    ],
    db: AsyncSession = Depends(get_db),  # noqa: B008
    staff: Annotated[Staff | None, Depends(require_admin)] = None,  # noqa: B008
) -> VoucherBatchResponse:
    """Generate a batch of vouchers with unique codes. Admin only.

    Vouchers can have either monetary value (value_paise) or time value (value_minutes).
    All vouchers in a batch share the same value and expiry.
    """
    return await VoucherService.generate_batch(
        db,
        count=body.count,
        value_paise=body.value_paise,
        value_minutes=body.value_minutes,
        expires_in_days=body.expires_in_days,
        staff=staff,
    )


@router.post(
    "/redeem",
    response_model=MemberResponse,
    summary="Redeem a voucher for a member",
)
async def redeem_voucher(
    body: Annotated[
        VoucherRedeemRequest, Body(description="Voucher code and member ID")
    ],
    db: AsyncSession = Depends(get_db),  # noqa: B008
    staff: Annotated[Staff | None, Depends(require_cashier)] = None,  # noqa: B008
) -> MemberResponse:
    """Redeem a voucher code for a member.

    Validates voucher is unused and not expired. If the voucher has monetary
    value (value_paise), credits the member's wallet. Time vouchers
    (value_minutes) are handled via package drawdown at session checkout.

    Cashier or Admin required.
    """
    member = await VoucherService.redeem(
        db,
        code=body.code,
        member_id=body.member_id,
    )
    return MemberResponse.model_validate(member)
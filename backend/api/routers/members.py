"""Member API router.

Routes::

    GET   /api/members?q=        → search members (cashier+)
    POST  /api/members           → create member (cashier+)
    GET   /api/members/{id}      → get member by ID (cashier+)
    POST  /api/members/{id}/topup → top up wallet (cashier+)
    GET   /api/members/{id}/sessions → member session history (cashier+)
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import require_cashier
from backend.core.database import get_db
from backend.core.feature_flags import require_feature
from backend.models.staff import Staff
from backend.repositories import session_repo
from backend.schemas.member import MemberCreate, MemberResponse, TopupRequest
from backend.schemas.session import SessionResponse
from backend.services.member_service import MemberService

router = APIRouter(prefix="/members", tags=["members"])

# Apply feature flag to all routes in this router
router.dependencies.append(Depends(require_feature("enable_members")))


@router.get(
    "",
    response_model=Sequence[MemberResponse],
    summary="Search members by name or phone",
)
async def search_members(
    q: str = Query("", description="Search query (name or phone)"),
    db: AsyncSession = Depends(get_db),  # noqa: B008
    _staff: Annotated[Staff | None, Depends(require_cashier)] = None,  # noqa: B008
) -> Sequence[MemberResponse]:
    """Search members by name or phone (case-insensitive)."""
    members = await MemberService.search_members(db, q)
    return [MemberResponse.model_validate(m) for m in members]


@router.post(
    "",
    response_model=MemberResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new member",
)
async def create_member(
    body: MemberCreate,
    db: AsyncSession = Depends(get_db),  # noqa: B008
    _staff: Annotated[Staff | None, Depends(require_cashier)] = None,  # noqa: B008
) -> MemberResponse:
    """Create a new member with BRONZE tier."""
    member = await MemberService.create_member(db, name=body.name, phone=body.phone)
    return MemberResponse.model_validate(member)


@router.get(
    "/{member_id}",
    response_model=MemberResponse,
    summary="Get member by ID",
)
async def get_member(
    member_id: str,
    db: AsyncSession = Depends(get_db),  # noqa: B008
    _staff: Annotated[Staff | None, Depends(require_cashier)] = None,  # noqa: B008
) -> MemberResponse:
    """Get a single member by ID."""
    member = await MemberService.get_member(db, member_id)
    return MemberResponse.model_validate(member)


@router.post(
    "/{member_id}/topup",
    response_model=MemberResponse,
    summary="Top up member wallet",
)
async def topup_wallet(
    member_id: str,
    body: TopupRequest,
    db: AsyncSession = Depends(get_db),  # noqa: B008
    staff: Annotated[Staff | None, Depends(require_cashier)] = None,  # noqa: B008
) -> MemberResponse:
    """Add funds to member wallet and log audit entry."""
    updated = await MemberService.topup_wallet(
        db,
        member_id=member_id,
        amount_paise=body.amount_paise,
        payment_method=body.payment_method.value,
        staff=staff,
    )
    return MemberResponse.model_validate(updated)


@router.get(
    "/{member_id}/sessions",
    response_model=Sequence[SessionResponse],
    summary="Get member session history",
)
async def get_member_sessions(
    member_id: str,
    db: AsyncSession = Depends(get_db),  # noqa: B008
    _staff: Annotated[Staff | None, Depends(require_cashier)] = None,  # noqa: B008
) -> Sequence[SessionResponse]:
    """Get session history for a member."""
    # Verify member exists
    _ = await MemberService.get_member(db, member_id)

    sessions = await session_repo.list_by_member(db, member_id)
    return [SessionResponse.model_validate(s) for s in sessions]

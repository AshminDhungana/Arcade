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
from datetime import UTC, datetime
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
from backend.schemas.wallet_transaction import WalletTransactionResponse
from backend.services.member_service import MemberService
from backend.services.wallet_service import WalletService


def _ensure_tz(dt: datetime | None) -> datetime | None:
    """Ensure a timezone-aware datetime.

    SQLite sometimes strips timezone info from DateTime(timezone=True).
    """
    if dt is not None and (dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None):
        return dt.replace(tzinfo=UTC)
    return dt


router = APIRouter(prefix="/members", tags=["members"])

# Apply feature flag to all routes in this router
router.dependencies.append(Depends(require_feature("enable_members")))


@router.get(
    "",
    response_model=Sequence[MemberResponse],
    summary="List or search members (paginated)",
)
async def search_members(
    q: str = Query("", description="Search query (name or phone); empty lists all"),
    limit: int = Query(50, ge=1, le=200, description="Page size"),
    offset: int = Query(0, ge=0, description="Page offset"),
    db: AsyncSession = Depends(get_db),  # noqa: B008
    _staff: Annotated[Staff | None, Depends(require_cashier)] = None,  # noqa: B008
) -> Sequence[MemberResponse]:
    """List all members (q empty) or search by name/phone (q set)."""
    if q and q.strip():
        members = await MemberService.search_members(db, q, limit=limit, offset=offset)
    else:
        members = await MemberService.list_members(db, limit=limit, offset=offset)

    # SQLite strips timezone info; restore UTC for Pydantic AwareDatetime validation
    for m in members:
        m.created_at = _ensure_tz(m.created_at)  # type: ignore[assignment]
        m.updated_at = _ensure_tz(m.updated_at)  # type: ignore[assignment]
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
    member.created_at = _ensure_tz(member.created_at)  # type: ignore[assignment]
    member.updated_at = _ensure_tz(member.updated_at)  # type: ignore[assignment]
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
    member.created_at = _ensure_tz(member.created_at)  # type: ignore[assignment]
    member.updated_at = _ensure_tz(member.updated_at)  # type: ignore[assignment]
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
    updated.created_at = _ensure_tz(updated.created_at)  # type: ignore[assignment]
    updated.updated_at = _ensure_tz(updated.updated_at)  # type: ignore[assignment]
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


@router.get(
    "/{member_id}/transactions",
    response_model=Sequence[WalletTransactionResponse],
    summary="Wallet transaction history for a member",
)
async def list_transactions(
    member_id: str,
    limit: int = Query(50, ge=1, le=200, description="Page size"),
    offset: int = Query(0, ge=0, description="Page offset"),
    db: AsyncSession = Depends(get_db),  # noqa: B008
    _staff: Annotated[Staff | None, Depends(require_cashier)] = None,  # noqa: B008
) -> Sequence[WalletTransactionResponse]:
    """List a member's wallet transactions, newest first."""
    await MemberService.get_member(db, member_id)  # 404 if missing
    txns = await WalletService.list_transactions(
        db, member_id, limit=limit, offset=offset
    )
    for t in txns:
        t.created_at = _ensure_tz(t.created_at)  # type: ignore[assignment]
    return [WalletTransactionResponse.model_validate(t) for t in txns]

"""Events / Tournament API router (feature-flagged: enable_tournaments)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import require_admin, require_cashier
from backend.core.database import get_db
from backend.core.feature_flags import require_feature
from backend.models.staff import Staff
from backend.schemas.event import (
    EventCreate,
    EventMatchResponse,
    EventMatchResultRequest,
    EventRegisterRequest,
    EventResponse,
    EventSummaryResponse,
)
from backend.services import event_service

router = APIRouter(prefix="/events", tags=["events"])

# Gate the entire router behind the feature flag -> 503 when off.
router.dependencies.append(Depends(require_feature("enable_tournaments")))

DbDep = Annotated[AsyncSession, Depends(get_db)]
AdminDep = Annotated[Staff, Depends(require_admin)]
CashierDep = Annotated[Staff, Depends(require_cashier)]


def _ensure_tz(dt: datetime | None) -> datetime | None:
    if dt is not None and (dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None):
        return dt.replace(tzinfo=UTC)
    return dt


@router.get("", response_model=list[EventResponse])
async def list_events(db: DbDep, staff: AdminDep) -> list[EventResponse]:
    events = await event_service.EventService._list_events(db)
    for e in events:
        e.event_date = _ensure_tz(e.event_date)  # type: ignore[assignment]
    return [EventResponse.model_validate(e) for e in events]


@router.post("", response_model=EventResponse, status_code=status.HTTP_201_CREATED)
async def create_event(body: EventCreate, db: DbDep, staff: AdminDep) -> EventResponse:
    event = await event_service.EventService.create_event(
        db,
        name=body.name,
        game_title=body.game_title,
        event_date=body.event_date,
        entry_fee_paise=body.entry_fee_paise,
        prize_pool_paise=body.prize_pool_paise,
        bracket_type=body.bracket_type,
        staff=staff,
    )
    event.event_date = _ensure_tz(event.event_date)  # type: ignore[assignment]
    return EventResponse.model_validate(event)


@router.post("/{event_id}/register", response_model=EventResponse)
async def register_participant(
    event_id: str,
    body: EventRegisterRequest,
    db: DbDep,
    staff: CashierDep,
) -> EventResponse:
    await event_service.EventService.register_participant(
        db,
        event_id=event_id,
        member_id=body.member_id,
        seat_id=body.seat_id,
        name=body.name,
        staff=staff,
    )
    event = await event_service.EventService._get_event_or_404(db, event_id)
    event.event_date = _ensure_tz(event.event_date)  # type: ignore[assignment]
    return EventResponse.model_validate(event)


@router.patch("/{event_id}/match", response_model=EventMatchResponse)
async def record_match(
    event_id: str,
    body: EventMatchResultRequest,
    db: DbDep,
    staff: AdminDep,
) -> EventMatchResponse:
    match = await event_service.EventService.record_match_result(
        db,
        event_id=event_id,
        match_id=body.match_id,
        winner_id=body.winner_id,
        staff=staff,
    )
    return EventMatchResponse.model_validate(match)


@router.get("/{event_id}/summary", response_model=EventSummaryResponse)
async def get_summary(
    event_id: str, db: DbDep, staff: AdminDep
) -> EventSummaryResponse:
    summary = await event_service.EventService.get_event_summary(db, event_id=event_id)
    # _ensure_tz on the nested event datetime before validation
    summary["event"].event_date = _ensure_tz(summary["event"].event_date)
    return EventSummaryResponse.model_validate(summary)

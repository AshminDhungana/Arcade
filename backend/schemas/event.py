"""Pydantic schemas for Event and EventParticipant models."""

from __future__ import annotations

from pydantic import AwareDatetime, Field

from backend.models._enums import (
    EventBracketGroup,
    EventBracketType,
    EventMatchStatus,
    EventStatus,
)
from backend.schemas.base import BaseCreateSchema, BaseResponseSchema


class EventBase(BaseCreateSchema):
    name: str = Field(..., max_length=255)
    game_title: str = Field(..., max_length=255)
    event_date: AwareDatetime
    entry_fee_paise: int = Field(0, ge=0)
    prize_pool_paise: int = Field(0, ge=0)
    bracket_type: EventBracketType = EventBracketType.SINGLE_ELIMINATION
    status: EventStatus = EventStatus.UPCOMING


class EventCreate(EventBase):
    pass


class EventUpdate(BaseCreateSchema):
    name: str | None = Field(None, max_length=255)
    game_title: str | None = Field(None, max_length=255)
    event_date: AwareDatetime | None = None
    entry_fee_paise: int | None = Field(None, ge=0)
    prize_pool_paise: int | None = Field(None, ge=0)
    bracket_type: EventBracketType | None = None
    status: EventStatus | None = None


class EventResponse(EventBase, BaseResponseSchema):
    id: str


class EventParticipantBase(BaseCreateSchema):
    event_id: str
    member_id: str | None = None
    name: str = Field(..., max_length=255)
    seat_id: str | None = None
    bracket_position: int | None = None
    eliminated: bool = False


class EventParticipantCreate(EventParticipantBase):
    pass


class EventParticipantUpdate(BaseCreateSchema):
    seat_id: str | None = None
    bracket_position: int | None = None
    eliminated: bool | None = None


class EventParticipantResponse(EventParticipantBase, BaseResponseSchema):
    id: str


class EventRegisterRequest(BaseCreateSchema):
    """Body for POST /api/events/{id}/register."""

    member_id: str | None = None
    name: str | None = Field(None, max_length=255)
    seat_id: str | None = None


class EventMatchResultRequest(BaseCreateSchema):
    """Body for PATCH /api/events/{id}/match."""

    match_id: str
    winner_id: str


class EventMatchResponse(BaseResponseSchema):
    id: str
    event_id: str
    bracket_group: EventBracketGroup
    round: int
    slot_a_id: str | None
    slot_b_id: str | None
    winner_id: str | None
    status: EventMatchStatus
    next_match_id: str | None
    next_loser_match_id: str | None


class EventSummaryResponse(BaseResponseSchema):
    event: EventResponse
    participant_count: int
    participants: list[EventParticipantResponse]
    match_count: int
    completed_match_count: int
    prize_pool_paise: int
    entry_fee_paise: int
    entry_fee_revenue_paise: int
    champion_participant_id: str | None
    is_complete: bool
    matches: list[EventMatchResponse] = []

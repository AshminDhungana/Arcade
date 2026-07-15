"""EventService — tournament lifecycle: create, register, record results, summarize.

Bracket generation is delegated to :func:`_ensure_bracket` (implemented in the
next task); for now create/register store data and registration is open until
the first match result is recorded.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models._enums import (
    AuditAction,
    EventBracketType,
    EventStatus,
    PaymentMethod,
)
from backend.models.staff import Staff
from backend.repositories import (
    event_match_repo,
    event_repo,
    member_repo,
    wallet_transaction_repo,
)
from backend.services import audit_service

if TYPE_CHECKING:
    from backend.models.event import Event
    from backend.models.event_participant import EventParticipant

logger = logging.getLogger(__name__)


class EventNotFoundError(HTTPException):
    def __init__(self, event_id: str) -> None:
        super().__init__(status_code=404, detail=f"Event {event_id} not found")


class EventParticipantNotFoundError(HTTPException):
    def __init__(self, participant_id: str) -> None:
        super().__init__(
            status_code=404, detail=f"Participant {participant_id} not found"
        )


class EventMatchNotFoundError(HTTPException):
    def __init__(self, match_id: str) -> None:
        super().__init__(status_code=404, detail=f"Match {match_id} not found")


class InsufficientFundsError(HTTPException):
    def __init__(self, needed: int, have: int) -> None:
        super().__init__(
            status_code=400,
            detail=(
                f"Insufficient wallet balance: need {needed} paise, "
                f"have {have} paise"
            ),
        )


class EventAlreadyStartedError(HTTPException):
    def __init__(self, event_id: str) -> None:
        super().__init__(
            status_code=409,
            detail=f"Event {event_id} has started; registration is closed",
        )


class EventService:
    @staticmethod
    async def create_event(
        db: AsyncSession,
        *,
        name: str,
        game_title: str,
        event_date: datetime,
        entry_fee_paise: int = 0,
        prize_pool_paise: int = 0,
        bracket_type: EventBracketType = EventBracketType.SINGLE_ELIMINATION,
        staff: Staff | None = None,
    ) -> Event:
        event = await event_repo.create_event(
            db,
            name=name,
            game_title=game_title,
            event_date=event_date,
            entry_fee_paise=entry_fee_paise,
            prize_pool_paise=prize_pool_paise,
            bracket_type=bracket_type.value,
            status=EventStatus.UPCOMING.value,
        )
        await audit_service.log(
            db,
            action=AuditAction.EVENT_CREATED,
            entity_type="event",
            entity_id=event.id,
            staff_id=staff.id if staff else None,
            detail=f"Created {bracket_type.value} event '{name}'",
        )
        return event

    @staticmethod
    async def register_participant(
        db: AsyncSession,
        *,
        event_id: str,
        member_id: str | None = None,
        seat_id: str | None = None,
        name: str | None = None,
        staff: Staff | None = None,
    ) -> EventParticipant:
        event = await event_repo.get_event_by_id(db, event_id)
        if event is None:
            raise EventNotFoundError(event_id)
        # Registration closes once any match result exists.
        existing_matches = await event_match_repo.list_matches_by_event(db, event.id)
        if existing_matches and any(
            m.status.value == "COMPLETED" for m in existing_matches
        ):
            raise EventAlreadyStartedError(event_id)

        resolved_name = name
        if member_id is not None:
            member = await member_repo.get_by_id(db, member_id)
            if member is None:
                raise HTTPException(
                    status_code=404, detail=f"Member {member_id} not found"
                )
            if resolved_name is None:
                resolved_name = member.name
            # Deduct entry fee from wallet (cash collected at counter for walk-ins).
            if event.entry_fee_paise > 0:
                if member.wallet_balance_paise < event.entry_fee_paise:
                    raise InsufficientFundsError(
                        event.entry_fee_paise, member.wallet_balance_paise
                    )
                member.wallet_balance_paise -= event.entry_fee_paise
                member = await member_repo.update(db, member)
                await wallet_transaction_repo.create(
                    db,
                    member_id=member.id,
                    type="EVENT_ENTRY",
                    amount_paise=-event.entry_fee_paise,
                    balance_after_paise=member.wallet_balance_paise,
                    payment_method=PaymentMethod.WALLET.value,
                    staff_id=staff.id if staff else None,
                    reference_id=event.id,
                )
        elif not resolved_name:
            raise HTTPException(
                status_code=400,
                detail="name is required for walk-in participants (no member_id)",
            )

        bracket_position = len(await event_repo.list_participants(db, event.id))
        participant = await event_repo.create_participant(
            db,
            event_id=event.id,
            name=resolved_name,
            member_id=member_id,
            seat_id=seat_id,
            bracket_position=bracket_position,
        )
        await audit_service.log(
            db,
            action=AuditAction.EVENT_PARTICIPANT_REGISTERED,
            entity_type="event",
            entity_id=event.id,
            staff_id=staff.id if staff else None,
            detail=f"Registered participant {participant.id} ({resolved_name})",
        )
        # Lazily build/refresh the bracket (no-op until implemented next task).
        await EventService._ensure_bracket(db, event)
        return participant

    @staticmethod
    async def _ensure_bracket(db: AsyncSession, event: Event) -> None:
        """Build/refresh the tournament bracket.

        Intentionally a no-op stub in this task (Task 6). Full bracket
        generation lands in Task 7.
        """
        return None

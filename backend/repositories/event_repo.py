"""Event & participant repository — CRUD."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import Event, EventParticipant

# -- Event CRUD --


async def create_event(
    db: AsyncSession,
    *,
    name: str,
    game_title: str,
    event_date: datetime,
    entry_fee_paise: int = 0,
    prize_pool_paise: int = 0,
    bracket_type: str | None = None,
    status: str | None = None,
) -> Event:
    event = Event(
        name=name,
        game_title=game_title,
        event_date=event_date,
        entry_fee_paise=entry_fee_paise,
        prize_pool_paise=prize_pool_paise,
        bracket_type=bracket_type,
        status=status,
    )
    db.add(event)
    await db.flush()
    await db.refresh(event)
    return event


async def get_event_by_id(db: AsyncSession, event_id: str) -> Event | None:
    result = await db.execute(select(Event).where(Event.id == event_id))
    return result.scalar_one_or_none()


async def list_events(db: AsyncSession) -> Sequence[Event]:
    result = await db.execute(select(Event))
    return result.scalars().all()


async def update_event(db: AsyncSession, event: Event) -> Event:
    db.add(event)
    await db.flush()
    await db.refresh(event)
    return event


async def delete_event(db: AsyncSession, event_id: str) -> bool:
    event = await get_event_by_id(db, event_id)
    if event is None:
        return False
    await db.delete(event)
    await db.flush()
    return True


# -- EventParticipant CRUD --


async def create_participant(
    db: AsyncSession,
    *,
    event_id: str,
    name: str,
    member_id: str | None = None,
    seat_id: str | None = None,
    bracket_position: int | None = None,
) -> EventParticipant:
    participant = EventParticipant(
        event_id=event_id,
        name=name,
        member_id=member_id,
        seat_id=seat_id,
        bracket_position=bracket_position,
    )
    db.add(participant)
    await db.flush()
    await db.refresh(participant)
    return participant


async def get_participant_by_id(
    db: AsyncSession, participant_id: str
) -> EventParticipant | None:
    result = await db.execute(
        select(EventParticipant).where(EventParticipant.id == participant_id)
    )
    return result.scalar_one_or_none()


async def list_participants(
    db: AsyncSession, event_id: str
) -> Sequence[EventParticipant]:
    result = await db.execute(
        select(EventParticipant).where(EventParticipant.event_id == event_id)
    )
    return result.scalars().all()

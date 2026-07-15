"""EventMatch repository — CRUD for bracket nodes."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.event_match import EventMatch


async def create_match(
    db: AsyncSession,
    *,
    event_id: str,
    bracket_group: str,
    round: int = 1,
    slot_a_id: str | None = None,
    slot_b_id: str | None = None,
    winner_id: str | None = None,
    status: str | None = None,
    next_match_id: str | None = None,
    next_loser_match_id: str | None = None,
) -> EventMatch:
    match = EventMatch(
        event_id=event_id,
        bracket_group=bracket_group,
        round=round,
        slot_a_id=slot_a_id,
        slot_b_id=slot_b_id,
        winner_id=winner_id,
        status=status,
        next_match_id=next_match_id,
        next_loser_match_id=next_loser_match_id,
    )
    db.add(match)
    await db.flush()
    await db.refresh(match)
    return match


async def bulk_create_matches(
    db: AsyncSession, *, matches: Sequence[EventMatch]
) -> list[EventMatch]:
    db.add_all(matches)
    await db.flush()
    for m in matches:
        await db.refresh(m)
    return list(matches)


async def get_match_by_id(db: AsyncSession, match_id: str) -> EventMatch | None:
    result = await db.execute(select(EventMatch).where(EventMatch.id == match_id))
    return result.scalar_one_or_none()


async def list_matches_by_event(
    db: AsyncSession, event_id: str
) -> Sequence[EventMatch]:
    result = await db.execute(
        select(EventMatch)
        .where(EventMatch.event_id == event_id)
        .order_by(EventMatch.round, EventMatch.bracket_group)
    )
    return result.scalars().all()


async def update_match(db: AsyncSession, match: EventMatch) -> EventMatch:
    db.add(match)
    await db.flush()
    await db.refresh(match)
    return match


async def delete_matches_by_event(db: AsyncSession, event_id: str) -> int:
    result = await db.execute(select(EventMatch).where(EventMatch.event_id == event_id))
    matches = result.scalars().all()
    for m in matches:
        await db.delete(m)
    await db.flush()
    return len(matches)

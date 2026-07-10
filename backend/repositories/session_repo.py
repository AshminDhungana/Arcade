"""Session repository — CRUD + active-session helpers."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import GamingSession, SessionStatus
from backend.models._enums import PricingModel


async def create(
    db: AsyncSession,
    *,
    seat_id: str,
    member_id: str | None = None,
    started_at: datetime | None = None,
    locked_rate_paise: int = 0,
    locked_pricing_model: PricingModel | None = None,
    package_entitlement_id: str | None = None,
    promotion_id: str | None = None,
) -> GamingSession:
    session = GamingSession(
        seat_id=seat_id,
        member_id=member_id,
        started_at=started_at or datetime.now(UTC),
        locked_rate_paise=locked_rate_paise,
        locked_pricing_model=locked_pricing_model,
        package_entitlement_id=package_entitlement_id,
        promotion_id=promotion_id,
    )
    db.add(session)
    await db.flush()
    await db.refresh(session)
    return session


async def get_by_id(db: AsyncSession, session_id: str) -> GamingSession | None:
    result = await db.execute(
        select(GamingSession).where(GamingSession.id == session_id)
    )
    return result.scalar_one_or_none()


async def list(db: AsyncSession) -> Sequence[GamingSession]:
    result = await db.execute(select(GamingSession))
    return result.scalars().all()


async def update(db: AsyncSession, session: GamingSession) -> GamingSession:
    db.add(session)
    await db.flush()
    await db.refresh(session)
    return session


async def delete_by_id(db: AsyncSession, session_id: str) -> bool:
    session = await get_by_id(db, session_id)
    if session is None:
        return False
    await db.delete(session)
    await db.flush()
    return True


async def get_active_by_seat(db: AsyncSession, seat_id: str) -> GamingSession | None:
    result = await db.execute(
        select(GamingSession).where(
            and_(
                GamingSession.seat_id == seat_id,
                GamingSession.status.in_([SessionStatus.ACTIVE, SessionStatus.PAUSED]),
            )
        )
    )
    return result.scalar_one_or_none()


async def list_active(db: AsyncSession) -> Sequence[GamingSession]:
    result = await db.execute(
        select(GamingSession).where(
            GamingSession.status.in_([SessionStatus.ACTIVE, SessionStatus.PAUSED])
        )
    )
    return result.scalars().all()


async def list_by_shift(db: AsyncSession, shift_id: str) -> Sequence[GamingSession]:
    result = await db.execute(
        select(GamingSession).where(GamingSession.shift_id == shift_id)
    )
    return result.scalars().all()


async def list_by_member(db: AsyncSession, member_id: str) -> Sequence[GamingSession]:
    result = await db.execute(
        select(GamingSession)
        .where(GamingSession.member_id == member_id)
        .order_by(GamingSession.started_at.desc())
    )
    return result.scalars().all()

"""Member repository — CRUD + phone / search helpers."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import Member


async def create(
    db: AsyncSession,
    *,
    name: str,
    phone: str,
    wallet_balance_paise: int = 0,
    loyalty_points: int = 0,
    tier: str | None = None,
    birth_month: int | None = None,
) -> Member:
    member = Member(
        name=name,
        phone=phone,
        wallet_balance_paise=wallet_balance_paise,
        loyalty_points=loyalty_points,
        tier=tier,
        birth_month=birth_month,
    )
    db.add(member)
    await db.flush()
    await db.refresh(member)
    return member


async def get_by_id(db: AsyncSession, member_id: str) -> Member | None:
    result = await db.execute(select(Member).where(Member.id == member_id))
    return result.scalar_one_or_none()


async def list(db: AsyncSession) -> Sequence[Member]:
    result = await db.execute(select(Member))
    return result.scalars().all()


async def update(db: AsyncSession, member: Member) -> Member:
    db.add(member)
    await db.flush()
    await db.refresh(member)
    return member


async def delete_by_id(db: AsyncSession, member_id: str) -> bool:
    member = await get_by_id(db, member_id)
    if member is None:
        return False
    await db.delete(member)
    await db.flush()
    return True


async def get_by_phone(db: AsyncSession, phone: str) -> Member | None:
    result = await db.execute(select(Member).where(Member.phone == phone))
    return result.scalar_one_or_none()


async def search(db: AsyncSession, query: str) -> Sequence[Member]:
    like = f"%{query}%"
    result = await db.execute(
        select(Member).where(
            or_(
                Member.name.ilike(like),
                Member.phone.ilike(like),
            )
        )
    )
    return result.scalars().all()

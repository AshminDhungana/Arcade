"""Reservation repository — CRUD."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import Reservation


async def create(
    db: AsyncSession,
    *,
    seat_id: str,
    customer_name: str,
    reserved_from: str,
    reserved_until: str | None = None,
    member_id: str | None = None,
    group_reservation_id: str | None = None,
    status: str | None = None,
    created_by_staff_id: str = "",
) -> Reservation:
    reservation = Reservation(
        seat_id=seat_id,
        customer_name=customer_name,
        reserved_from=reserved_from,
        reserved_until=reserved_until,
        member_id=member_id,
        group_reservation_id=group_reservation_id,
        status=status,
        created_by_staff_id=created_by_staff_id,
    )
    db.add(reservation)
    await db.flush()
    await db.refresh(reservation)
    return reservation


async def get_by_id(db: AsyncSession, reservation_id: str) -> Reservation | None:
    result = await db.execute(
        select(Reservation).where(Reservation.id == reservation_id)
    )
    return result.scalar_one_or_none()


async def list(db: AsyncSession) -> Sequence[Reservation]:
    result = await db.execute(select(Reservation))
    return result.scalars().all()


async def update(db: AsyncSession, reservation: Reservation) -> Reservation:
    db.add(reservation)
    await db.flush()
    await db.refresh(reservation)
    return reservation


async def delete_by_id(db: AsyncSession, reservation_id: str) -> bool:
    reservation = await get_by_id(db, reservation_id)
    if reservation is None:
        return False
    await db.delete(reservation)
    await db.flush()
    return True

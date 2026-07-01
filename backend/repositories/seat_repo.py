"""Seat repository — CRUD + status helpers."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import Seat, SeatStatus


async def create(
    db: AsyncSession,
    *,
    name: str,
    zone_id: str,
    mac_address: str | None = None,
    plug_id: str | None = None,
    is_console: bool = False,
    notes: str | None = None,
) -> Seat:
    seat = Seat(
        name=name,
        zone_id=zone_id,
        mac_address=mac_address,
        plug_id=plug_id,
        is_console=is_console,
        notes=notes,
    )
    db.add(seat)
    await db.flush()
    await db.refresh(seat)
    return seat


async def get_by_id(db: AsyncSession, seat_id: str) -> Seat | None:
    result = await db.execute(select(Seat).where(Seat.id == seat_id))
    return result.scalar_one_or_none()


async def list(db: AsyncSession) -> Sequence[Seat]:
    result = await db.execute(select(Seat))
    return result.scalars().all()


async def update(db: AsyncSession, seat: Seat) -> Seat:
    db.add(seat)
    await db.flush()
    await db.refresh(seat)
    return seat


async def delete_by_id(db: AsyncSession, seat_id: str) -> bool:
    seat = await get_by_id(db, seat_id)
    if seat is None:
        return False
    await db.delete(seat)
    await db.flush()
    return True


async def list_with_mac(db: AsyncSession) -> Sequence[Seat]:
    result = await db.execute(select(Seat).where(Seat.mac_address.isnot(None)))
    return result.scalars().all()


async def update_status(
    db: AsyncSession, seat_id: str, new_status: SeatStatus
) -> Seat | None:
    seat = await get_by_id(db, seat_id)
    if seat is None:
        return None
    seat.status = new_status
    db.add(seat)
    await db.flush()
    await db.refresh(seat)
    return seat

"""Reservation repository — CRUD and time-window queries."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import Reservation, ReservationStatus


async def create(
    db: AsyncSession,
    *,
    seat_id: str,
    customer_name: str,
    reserved_from: datetime,
    reserved_until: datetime | None = None,
    member_id: str | None = None,
    group_reservation_id: str | None = None,
    notes: str | None = None,
    status: ReservationStatus = ReservationStatus.PENDING,
    created_by_staff_id: str,
) -> Reservation:
    reservation = Reservation(
        seat_id=seat_id,
        customer_name=customer_name,
        reserved_from=reserved_from,
        reserved_until=reserved_until,
        member_id=member_id,
        group_reservation_id=group_reservation_id,
        notes=notes,
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


async def list_reservations(
    db: AsyncSession,
    *,
    seat_id: str | None = None,
    member_id: str | None = None,
    status: ReservationStatus | None = None,
) -> Sequence[Reservation]:
    conditions = []
    if seat_id is not None:
        conditions.append(Reservation.seat_id == seat_id)
    if member_id is not None:
        conditions.append(Reservation.member_id == member_id)
    if status is not None:
        conditions.append(Reservation.status == status)
    stmt = select(Reservation)
    if conditions:
        stmt = stmt.where(and_(*conditions))
    result = await db.execute(stmt)
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


async def find_conflicting(
    db: AsyncSession,
    *,
    seat_id: str,
    reserved_from: datetime,
    reserved_until: datetime | None,
    exclude_id: str | None = None,
    statuses: Sequence[ReservationStatus] | None = None,
) -> Sequence[Reservation]:
    """Return reservations for ``seat_id`` whose window overlaps
    [reserved_from, reserved_until], excluding ``exclude_id``.

    Overlap rule: existing.start < new.end AND (existing.end IS NULL OR
    existing.end > new.start). An open-ended new window (reserved_until is
    None) overlaps any existing reservation that does not end before new.start.
    """
    if statuses is None:
        statuses = (ReservationStatus.PENDING, ReservationStatus.CONFIRMED)
    conditions = [
        Reservation.seat_id == seat_id,
        Reservation.status.in_(statuses),
    ]
    if exclude_id is not None:
        conditions.append(Reservation.id != exclude_id)
    if reserved_until is None:
        conditions.append(
            or_(
                Reservation.reserved_until.is_(None),
                Reservation.reserved_until > reserved_from,
            )
        )
    else:
        conditions.append(Reservation.reserved_from < reserved_until)
        conditions.append(
            or_(
                Reservation.reserved_until.is_(None),
                Reservation.reserved_until > reserved_from,
            )
        )
    result = await db.execute(select(Reservation).where(and_(*conditions)))
    return tuple(result.scalars().all())


async def find_due(
    db: AsyncSession,
    *,
    window_start: datetime,
    window_end: datetime,
    statuses: Sequence[ReservationStatus] | None = None,
) -> Sequence[Reservation]:
    """Return reservations whose ``reserved_from`` is within
    [window_start, window_end] and whose status is in ``statuses``.
    """
    if statuses is None:
        statuses = (ReservationStatus.PENDING, ReservationStatus.CONFIRMED)
    stmt = (
        select(Reservation)
        .where(Reservation.reserved_from >= window_start)
        .where(Reservation.reserved_from <= window_end)
        .where(Reservation.status.in_(statuses))
    )
    result = await db.execute(stmt)
    return tuple(result.scalars().all())

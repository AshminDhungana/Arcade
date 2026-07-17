"""Seat repository — CRUD + status helpers."""

from __future__ import annotations

import secrets
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.security import hash_pin
from backend.models import GamingSession, Seat, SeatStatus, SessionStatus


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


async def assigned_end_at_by_seat(
    db: AsyncSession, seat_ids: Sequence[str]
) -> dict[str, datetime]:
    """Map seat_id -> assigned_end_at for the active session on each seat (6.5.4)."""
    if not seat_ids:
        return {}
    result = await db.execute(
        select(GamingSession.seat_id, GamingSession.assigned_end_at).where(
            GamingSession.seat_id.in_(seat_ids),
            GamingSession.status.in_([SessionStatus.ACTIVE, SessionStatus.PAUSED]),
            GamingSession.assigned_end_at.is_not(None),
        )
    )
    return {row.seat_id: row.assigned_end_at for row in result.all()}


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


async def set_enroll_code(
    db: AsyncSession, seat_id: str, code_hash: str, expires_at: datetime
) -> None:
    seat = await db.get(Seat, seat_id)
    if seat is None:
        raise ValueError(f"Unknown seat_id: {seat_id}")
    seat.enroll_code_hash = code_hash
    seat.enroll_code_expires_at = expires_at
    await db.commit()


async def get_by_enroll_code(db: AsyncSession, code_hash: str) -> Seat | None:
    result = await db.execute(select(Seat).where(Seat.enroll_code_hash == code_hash))
    return result.scalars().first()


async def set_agent_secret(db: AsyncSession, seat_id: str, secret: str) -> None:
    seat = await db.get(Seat, seat_id)
    if seat is None:
        raise ValueError(f"Unknown seat_id: {seat_id}")
    seat.agent_secret = secret
    await db.commit()


async def clear_enroll_code(db: AsyncSession, seat_id: str) -> None:
    seat = await db.get(Seat, seat_id)
    if seat is None:
        return
    seat.enroll_code_hash = None
    seat.enroll_code_expires_at = None
    await db.commit()


async def get_agent_secret(db: AsyncSession, seat_id: str) -> str | None:
    seat = await db.get(Seat, seat_id)
    return seat.agent_secret if seat else None


async def set_override_pin_hash(db: AsyncSession, seat_id: str, pin_hash: str) -> None:
    seat = await db.get(Seat, seat_id)
    if seat is None:
        raise ValueError(f"Unknown seat_id: {seat_id}")
    seat.override_code_hash = pin_hash
    await db.commit()


async def get_override_pin_hash(db: AsyncSession, seat_id: str) -> str | None:
    seat = await db.get(Seat, seat_id)
    return seat.override_code_hash if seat else None


async def auto_mint_override_pin(db: AsyncSession, seat_id: str) -> str | None:
    """Mint a default 6-digit override PIN if the seat has none; return its hash."""
    seat = await db.get(Seat, seat_id)
    if seat is None:
        raise ValueError(f"Unknown seat_id: {seat_id}")
    if seat.override_code_hash:
        return seat.override_code_hash
    pin = f"{secrets.randbelow(1_000_000):06d}"
    seat.override_code_hash = hash_pin(pin)
    await db.commit()
    return seat.override_code_hash

"""Wake-on-LAN service — magic packets, watchdogs, and per-seat counters."""

from __future__ import annotations

import asyncio
import logging
import socket
from datetime import UTC
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import AsyncSessionLocal
from backend.core.ws_manager import manager as ws_manager
from backend.models._enums import AuditAction, SeatStatus
from backend.models.seat import Seat
from backend.repositories import audit_repo, seat_repo
from backend.schemas.seat import SeatResponse

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Watchdog state
# ---------------------------------------------------------------------------

WATCHDOG_DELAY: int = 60  # seconds (monkeypatch for tests)
_watchdogs: dict[str, asyncio.Task[None]] = {}


def _cancel_watchdog(seat_id: str) -> None:
    """Cancel and remove an active watchdog for *seat_id*."""
    task = _watchdogs.pop(seat_id, None)
    if task is not None:
        task.cancel()


# ---------------------------------------------------------------------------
# Broadcasting helper
# ---------------------------------------------------------------------------


def _seat_to_response(seat: Seat) -> SeatResponse:
    """Convert a Seat ORM instance to a SeatResponse Pydantic model."""
    # Ensure timezone-aware datetimes so Pydantic doesn't complain
    created = seat.created_at
    updated = seat.updated_at
    if created is not None and getattr(created, "tzinfo", None) is None:
        created = created.replace(tzinfo=UTC)
    if updated is not None and getattr(updated, "tzinfo", None) is None:
        updated = updated.replace(tzinfo=UTC)
    return SeatResponse(
        id=seat.id,
        name=seat.name,
        zone_id=seat.zone_id,
        mac_address=seat.mac_address,
        status=seat.status,
        plug_id=seat.plug_id,
        is_console=seat.is_console,
        notes=seat.notes,
        wol_attempts=seat.wol_attempts,
        wol_successes=seat.wol_successes,
        wol_failures=seat.wol_failures,
        created_at=created,
        updated_at=updated,
    )


async def _broadcast_seat_update(seat: Seat) -> None:
    """Broadcast seat status change to all dashboards."""
    await ws_manager.broadcast_to_dashboards(
        "seat_updated",
        {
            "seat_id": seat.id,
            "status": seat.status.name
            if hasattr(seat.status, "name")
            else str(seat.status),
        },
    )


# ---------------------------------------------------------------------------
# Low-level WoL
# ---------------------------------------------------------------------------


def send_magic_packet(
    mac_address: str, *, broadcast: str = "255.255.255.255", port: int = 9
) -> None:
    """Send a Wake-on-LAN magic packet to *mac_address*.

    Args:
        mac_address: Colon- or hyphen-separated MAC address (e.g. 'aa:bb:cc:dd:ee:ff').
        broadcast: Target broadcast address. Defaults to the global broadcast.
        port: Target UDP port. Defaults to 9 (discard).
    """
    # Normalise MAC address to bytes
    clean = mac_address.replace(":", "").replace("-", "").replace(".", "")
    if len(clean) != 12:
        raise ValueError(f"Invalid MAC address: {mac_address}")

    mac_bytes = bytes.fromhex(clean)
    packet = b"\xff" * 6 + mac_bytes * 16

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    try:
        sock.sendto(packet, (broadcast, port))
        logger.info(
            "Sent WoL magic packet to %s via %s:%d", mac_address, broadcast, port
        )
    finally:
        sock.close()


# ---------------------------------------------------------------------------
# Core WoL logic
# ---------------------------------------------------------------------------


async def _wakeup_seat(
    db: AsyncSession, seat: Seat, *, triggered_by: str | None = None
) -> None:
    """Send magic packet, update counters, schedule watchdog, broadcast, and audit."""
    if seat.mac_address is None:
        raise ValueError("Seat has no MAC address configured")

    # 1. Send the magic packet
    send_magic_packet(seat.mac_address)

    # 2. Update counters & status
    seat.wol_attempts += 1
    seat.status = SeatStatus.BOOTING
    await seat_repo.update(db, seat)

    # 3. Schedule or reschedule watchdog (60-second timeout)
    _cancel_watchdog(seat.id)
    _watchdogs[seat.id] = asyncio.create_task(_watchdog(seat.id, delay=WATCHDOG_DELAY))

    # 4. Broadcast to dashboards
    await _broadcast_seat_update(seat)

    # 5. Audit log
    await audit_repo.create(
        db,
        action=AuditAction.WOL_SENT.name,
        entity_type="seat",
        entity_id=seat.id,
        staff_id=triggered_by,
        detail=f"Wake-on-LAN triggered for seat {seat.name}",
    )


async def _watchdog(
    seat_id: str, *, delay: int = 60, db: AsyncSession | None = None
) -> None:
    """Wait *delay* seconds, then mark seat as UNREACHABLE if still BOOTING."""
    try:
        await asyncio.sleep(delay)
    except asyncio.CancelledError:
        return

    async def _check(session: AsyncSession) -> None:
        seat = await seat_repo.get_by_id(session, seat_id)
        if seat is None:
            logger.warning("Watchdog fired for unknown seat_id %s", seat_id)
            return
        if seat.status == SeatStatus.BOOTING:
            seat.status = SeatStatus.UNREACHABLE
            seat.wol_failures += 1
            await seat_repo.update(session, seat)
            await _broadcast_seat_update(seat)
            await audit_repo.create(
                session,
                action=AuditAction.WOL_TIMEOUT.name,
                entity_type="seat",
                entity_id=seat.id,
                detail=f"Wake-on-LAN timed out for seat {seat.name}",
            )
            logger.info(
                "WoL watchdog: seat %s moved from BOOTING to UNREACHABLE", seat_id
            )

    if db is not None:
        await _check(db)
    else:
        async with AsyncSessionLocal() as db:
            await _check(db)

    # Clean up reference
    _watchdogs.pop(seat_id, None)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def boot_all_seats(db: AsyncSession) -> list[str]:
    """Send WoL magic packets to all seats with a registered MAC address.

    Returns the list of seat IDs that received packets.
    """
    seats = await seat_repo.list_with_mac(db)
    triggered: list[str] = []
    for seat in seats:
        if not seat.mac_address:
            logger.warning("Seat %s has no MAC address, skipping", seat.id)
            continue
        try:
            await _wakeup_seat(db, seat)
            triggered.append(seat.id)
        except Exception:
            logger.exception("Failed to send WoL to seat %s", seat.id)
    return triggered


async def send_wol_to_seat(
    db: AsyncSession, seat_id: str, staff: Any = None
) -> SeatResponse:
    """Trigger Wake-on-LAN for a single seat.

    Raises:
        HTTPException: 404 if seat not found, 422 if no MAC configured.
    """
    seat = await seat_repo.get_by_id(db, seat_id)
    if seat is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Seat not found"
        )
    if seat.mac_address is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Seat has no MAC address configured",
        )
    triggered_by = getattr(staff, "id", None) if staff else None
    await _wakeup_seat(db, seat, triggered_by=triggered_by)
    # Refresh after potential flush
    await db.refresh(seat)
    return _seat_to_response(seat)


async def override_seat_online(
    db: AsyncSession, seat_id: str, staff: Any = None
) -> SeatResponse:
    """Manually mark a seat as online (admin override).

    Cancels any pending watchdog and sets the seat to AVAILABLE.
    """
    seat = await seat_repo.get_by_id(db, seat_id)
    if seat is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Seat not found"
        )

    _cancel_watchdog(seat_id)

    seat.status = SeatStatus.AVAILABLE
    await seat_repo.update(db, seat)
    await _broadcast_seat_update(seat)

    triggered_by = getattr(staff, "id", None) if staff else None
    await audit_repo.create(
        db,
        action=AuditAction.WOL_OVERRIDE.name,
        entity_type="seat",
        entity_id=seat.id,
        staff_id=triggered_by,
        detail=f"Seat {seat.name} manually brought online (override)",
    )

    return _seat_to_response(seat)


async def wol_success_callback(seat_id: str, *, db: AsyncSession | None = None) -> None:
    """Called when an agent registers while the seat is in BOOTING state.

    Cancels the watchdog, marks the seat as AVAILABLE, and records success.
    """
    _cancel_watchdog(seat_id)

    async def _check(session: AsyncSession) -> None:
        seat = await seat_repo.get_by_id(session, seat_id)
        if seat is None:
            logger.warning("WoL success callback for unknown seat_id %s", seat_id)
            return
        if seat.status != SeatStatus.BOOTING:
            return
        seat.status = SeatStatus.AVAILABLE
        seat.wol_successes += 1
        await seat_repo.update(session, seat)
        await _broadcast_seat_update(seat)
        await audit_repo.create(
            session,
            action=AuditAction.WOL_SUCCESS.name,
            entity_type="seat",
            entity_id=seat.id,
            detail=f"Seat {seat.name} came online after WoL",
        )
        logger.info("WoL success: seat %s (%s) is now ONLINE", seat_id, seat.name)

    if db is not None:
        await _check(db)
    else:
        async with AsyncSessionLocal() as db:
            await _check(db)

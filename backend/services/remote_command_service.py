"""RemoteCommandService — dashboard-to-agent remote commands.

Business logic for pushing commands to a seat's agent over WebSocket:

- ``send_message``     → ``SHOW_MESSAGE`` (best-effort display)
- ``request_screenshot`` → ``TAKE_SCREENSHOT`` (request/response, rate-limited)
- ``restart_seat``     → ``RESTART``
- ``shutdown_seat``    → ``SHUTDOWN``

Screenshot rate-limiting (AC-18) is enforced HERE, at the service layer,
not in the HTTP route: an in-memory ``set`` of in-flight ``seat_id``s
guards against a 2nd concurrent request per seat (which is rejected with
409 rather than queued).
"""

from __future__ import annotations

import asyncio
import uuid

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.ws_manager import AgentOfflineError, Msg
from backend.core.ws_manager import manager as ws_manager
from backend.models._enums import AuditAction, SeatStatus
from backend.models.seat import Seat
from backend.models.staff import Staff
from backend.repositories import seat_repo
from backend.services import audit_service, seat_service

# ---------------------------------------------------------------------------
# Errors (all HTTPException subclasses so FastAPI renders JSON via main.py)
# ---------------------------------------------------------------------------


class SeatNotFoundError(HTTPException):
    def __init__(self, seat_id: str) -> None:
        super().__init__(status_code=404, detail=f"Seat {seat_id} not found")


class AgentOfflineHttpError(HTTPException):
    def __init__(self, seat_id: str) -> None:
        super().__init__(status_code=503, detail=f"Agent for seat {seat_id} is offline")


class ScreenshotInFlightError(HTTPException):
    def __init__(self, seat_id: str) -> None:
        super().__init__(
            status_code=409,
            detail=f"A screenshot request is already in-flight for seat {seat_id}",
        )


class ScreenshotTimeoutError(HTTPException):
    def __init__(self, seat_id: str) -> None:
        super().__init__(
            status_code=504,
            detail=f"Screenshot request for seat {seat_id} timed out",
        )


class ScreenshotInvalidImageError(HTTPException):
    def __init__(self) -> None:
        super().__init__(status_code=502, detail="Agent returned invalid image data")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SCREENSHOT_TIMEOUT = 3.0  # seconds (AC-18: delivered within 3s)
MESSAGE_DEFAULT_DURATION = 30  # seconds on-screen
COMMAND_DELAY_SECONDS = 10  # restart/shutdown grace (SDD §9.3)

# In-flight screenshot rate-limit state (AC-18). Service-level, not route-level.
_screenshot_inflight: set[str] = set()
_screenshot_inflight_lock = asyncio.Lock()


async def _send_to_agent_or_503(seat_id: str, command: dict[str, object]) -> None:
    """Send a command to the agent, mapping offline → 503."""
    try:
        await ws_manager.send_to_agent(seat_id, command)
    except AgentOfflineError:
        raise AgentOfflineHttpError(seat_id) from None


async def _get_seat_or_404(db: AsyncSession, seat_id: str) -> Seat:
    seat = await seat_repo.get_by_id(db, seat_id)
    if seat is None:
        raise SeatNotFoundError(seat_id)
    return seat


# ---------------------------------------------------------------------------
# Public API — Task 2
# ---------------------------------------------------------------------------


async def send_message(
    db: AsyncSession,
    seat_id: str,
    message: str,
    staff: Staff | None = None,
) -> None:
    """Send a ``SHOW_MESSAGE`` command to the seat's agent and audit it.

    Raises:
        HTTPException(404): If the seat does not exist.
        HTTPException(503): If the agent is offline.
    """
    seat = await _get_seat_or_404(db, seat_id)
    await _send_to_agent_or_503(
        seat_id,
        {
            "type": Msg.SHOW_MESSAGE,
            "payload": {
                "text": message,
                "duration_seconds": MESSAGE_DEFAULT_DURATION,
            },
        },
    )
    await audit_service.log(
        db,
        action=AuditAction.MESSAGE_SENT,
        entity_type="seat",
        entity_id=seat.id,
        staff_id=staff.id if staff else None,
        detail=message,
    )


# ---------------------------------------------------------------------------
# Public API — Task 3
# ---------------------------------------------------------------------------


async def request_screenshot(
    db: AsyncSession,
    seat_id: str,
    staff: Staff | None = None,
) -> bytes:
    """Request a screenshot from the seat's agent and return the JPEG bytes.

    Sends a ``TAKE_SCREENSHOT`` command to the agent and awaits the
    ``SCREENSHOT_RESULT`` response (correlated by ``request_id``).

    Enforces a per-seat in-flight limit of 1 (AC-18). Timeouts after
    ``SCREENSHOT_TIMEOUT`` seconds (3s, per AC-18).

    Args:
        db: Database session for seat lookup and audit logging.
        seat_id: Target seat ID.
        staff: Optional staff member for audit logging.

    Returns:
        JPEG image bytes (base64-decoded from the agent's response).

    Raises:
        HTTPException(404): If the seat does not exist.
        HTTPException(409): If a screenshot request is already in-flight for this seat.
        HTTPException(503): If the agent is offline.
        HTTPException(504): If the agent does not respond within 3 seconds.
        HTTPException(502): If the agent returns invalid/missing image data.
    """
    await _get_seat_or_404(db, seat_id)

    # Enforce per-seat in-flight limit (1 screenshot at a time)
    async with _screenshot_inflight_lock:
        if seat_id in _screenshot_inflight:
            raise ScreenshotInFlightError(seat_id)
        _screenshot_inflight.add(seat_id)

    request_id = uuid.uuid4().hex
    try:
        # Send the TAKE_SCREENSHOT command to the agent
        await _send_to_agent_or_503(
            seat_id,
            {
                "type": Msg.TAKE_SCREENSHOT,
                "payload": {"request_id": request_id},
            },
        )

        # Wait for the agent's SCREENSHOT_RESULT response
        try:
            image_bytes = await ws_manager.wait_for_screenshot(
                request_id, seat_id=seat_id, timeout=SCREENSHOT_TIMEOUT
            )
        except asyncio.TimeoutError as err:  # noqa: UP041
            raise ScreenshotTimeoutError(seat_id) from err
        except asyncio.CancelledError as err:
            # Agent disconnected; treat as timeout per AC-18
            raise ScreenshotTimeoutError(seat_id) from err

        # Validate JPEG SOI marker (\xff\xd8)
        if not image_bytes.startswith(b"\xff\xd8"):
            raise ScreenshotInvalidImageError()

        # Audit the screenshot request
        await audit_service.log(
            db,
            action=AuditAction.SCREENSHOT_TAKEN,
            entity_type="seat",
            entity_id=seat_id,
            staff_id=staff.id if staff else None,
            detail=f"Screenshot request_id={request_id}",
        )

        return image_bytes
    finally:
        # Always release the in-flight slot
        async with _screenshot_inflight_lock:
            _screenshot_inflight.discard(seat_id)


# ---------------------------------------------------------------------------
# Public API — Task 4
# ---------------------------------------------------------------------------


async def restart_seat(
    db: AsyncSession,
    seat_id: str,
    staff: Staff | None = None,
) -> None:
    """Send ``RESTART`` to the seat's agent and audit ``SEAT_RESTARTED`` (AC-06).

    Raises:
        HTTPException(404): If the seat does not exist.
        HTTPException(503): If the agent is offline.
    """
    seat = await _get_seat_or_404(db, seat_id)
    await _send_to_agent_or_503(
        seat_id,
        {
            "type": Msg.RESTART,
            "payload": {"delay_seconds": COMMAND_DELAY_SECONDS},
        },
    )
    await audit_service.log(
        db,
        action=AuditAction.SEAT_RESTARTED,
        entity_type="seat",
        entity_id=seat.id,
        staff_id=staff.id if staff else None,
        detail=f"seat {seat.name}",
    )


async def shutdown_seat(
    db: AsyncSession,
    seat_id: str,
    staff: Staff | None = None,
) -> None:
    """Send ``SHUTDOWN`` to the seat's agent and audit ``SEAT_SHUTDOWN``.

    Raises:
        HTTPException(404): If the seat does not exist.
        HTTPException(503): If the agent is offline.
    """
    seat = await _get_seat_or_404(db, seat_id)
    await _send_to_agent_or_503(
        seat_id,
        {
            "type": Msg.SHUTDOWN,
            "payload": {"delay_seconds": COMMAND_DELAY_SECONDS},
        },
    )
    await audit_service.log(
        db,
        action=AuditAction.SEAT_SHUTDOWN,
        entity_type="seat",
        entity_id=seat.id,
        staff_id=staff.id if staff else None,
        detail=f"seat {seat.name}",
    )


# ---------------------------------------------------------------------------
# Public API — Task 3
# ---------------------------------------------------------------------------


async def force_overlay(
    db: AsyncSession,
    seat_id: str,
    show: bool,
    staff: Staff | None = None,
) -> None:
    """Send ``FORCE_OVERLAY_ON``/``OFF`` to the agent and flip ``overlay_forced``.

    The send happens first: if the agent is offline (503) no DB column is
    mutated. The broadcast is performed by ``seat_service.set_overlay_forced``.

    Raises:
        HTTPException(404): If the seat does not exist.
        HTTPException(503): If the agent is offline.
    """
    seat = await _get_seat_or_404(db, seat_id)
    await _send_to_agent_or_503(
        seat_id,
        {
            "type": Msg.FORCE_OVERLAY_ON if show else Msg.FORCE_OVERLAY_OFF,
            "payload": {},
        },
    )
    await seat_service.set_overlay_forced(db, seat_id, show)
    await audit_service.log(
        db,
        action=(
            AuditAction.OVERLAY_FORCED_ON if show else AuditAction.OVERLAY_FORCED_OFF
        ),
        entity_type="seat",
        entity_id=seat.id,
        staff_id=staff.id if staff else None,
        detail=f"overlay forced={'on' if show else 'off'}",
    )


# ---------------------------------------------------------------------------
# Public API — Task 4 (bulk force overlay)
# ---------------------------------------------------------------------------


async def bulk_force_overlay(
    db: AsyncSession,
    show: bool,
    staff: Staff | None = None,
) -> dict[str, object]:
    """Force overlay on/off for many seats; returns a success/failure summary.

    ``show=True`` targets AVAILABLE seats; ``show=False`` targets seats whose
    ``overlay_forced`` is already true. An offline agent is recorded in
    ``failed`` rather than aborting the whole batch.
    """
    seats = await seat_repo.list(db)
    if show:
        targets = [s for s in seats if s.status == SeatStatus.AVAILABLE]
    else:
        targets = [s for s in seats if s.overlay_forced]
    succeeded: list[str] = []
    failed: list[dict[str, str]] = []
    for seat in targets:
        try:
            await force_overlay(db, seat.id, show, staff)
            succeeded.append(seat.id)
        except AgentOfflineHttpError:
            failed.append({"seat_id": seat.id, "detail": "Agent offline"})
    return {"succeeded": succeeded, "failed": failed}

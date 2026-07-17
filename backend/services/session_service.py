"""Session Service — business logic for session lifecycle.

All public functions are ``async def`` and accept ``db: AsyncSession`` as their
first parameter.  Status transitions, WebSocket broadcasts, and audit logging
are handled in this module.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.feature_flags import get_flag
from backend.core.ws_manager import AgentOfflineError
from backend.core.ws_manager import manager as ws_manager
from backend.models import GamingSession, SeatStatus, SessionStatus
from backend.models._enums import AuditAction
from backend.repositories import package_repo, seat_repo, session_repo, shift_repo
from backend.schemas.session import SessionResponse
from backend.services import audit_service
from backend.services.billing_service import resolve_rate
from backend.services.promotion_service import PromotionService

if TYPE_CHECKING:
    from backend.models.staff import Staff


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
#  Custom exceptions
# ---------------------------------------------------------------------------


class SessionNotFoundError(HTTPException):
    """Raised when a session lookup fails."""

    def __init__(self, session_id: str) -> None:
        super().__init__(status_code=404, detail=f"Session {session_id} not found")


class SeatUnavailableError(HTTPException):
    """Raised when a seat is not AVAILABLE or RESERVED."""

    def __init__(self) -> None:
        super().__init__(status_code=409, detail="SEAT_UNAVAILABLE")


class SessionConflictError(HTTPException):
    """Raised when an seat already has an active session."""

    def __init__(self) -> None:
        super().__init__(status_code=409, detail="ACTIVE_SESSION_EXISTS")


class InvalidSessionStateError(HTTPException):
    """Raised when a session is not in the expected status."""

    def __init__(self, action: str, expected: str) -> None:
        super().__init__(
            status_code=409, detail=f"Expected status {expected} to {action}"
        )


# ---------------------------------------------------------------------------
#  Helpers
# ---------------------------------------------------------------------------


def _ensure_tz(dt: datetime | None) -> datetime | None:
    """Ensure a timezone-aware datetime.

    SQLite sometimes strips timezone info; re-attach UTC when missing.
    """
    if dt is not None and (dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None):
        return dt.replace(tzinfo=UTC)
    return dt


def _session_to_response(session: GamingSession) -> SessionResponse:
    """Convert a ``GamingSession`` ORM object to a Pydantic ``SessionResponse``."""
    session.created_at = _ensure_tz(session.created_at)  # type: ignore[assignment]
    session.updated_at = _ensure_tz(session.updated_at)  # type: ignore[assignment]
    session.started_at = _ensure_tz(session.started_at)  # type: ignore[assignment]
    session.ended_at = _ensure_tz(session.ended_at)
    session.paused_at = _ensure_tz(session.paused_at)
    session.assigned_end_at = _ensure_tz(session.assigned_end_at)
    return SessionResponse.model_validate(session)


def _begin_pause(session: GamingSession, now: datetime) -> None:
    """Record pause start. No-op unless the session is ACTIVE.

    Guards against double-pause: a session already PAUSED keeps its original
    ``paused_at`` (e.g. a forced overlay on a manually-paused seat).
    """
    if session.status != SessionStatus.ACTIVE:
        return
    session.status = SessionStatus.PAUSED
    session.paused_at = now


def _accrue_pause(session: GamingSession, now: datetime) -> None:
    """Add (now - paused_at) to total_paused_seconds; clear paused_at.

    No-op if ``paused_at`` is already ``None`` (nothing to accrue).
    """
    paused_at = _ensure_tz(session.paused_at)
    if paused_at is None:
        return
    duration = (now - paused_at).total_seconds()
    session.total_paused_seconds = (session.total_paused_seconds or 0) + int(duration)
    session.paused_at = None


# ---------------------------------------------------------------------------
#  Public API
# ---------------------------------------------------------------------------


async def start_session(
    db: AsyncSession,
    /,  # noqa: W504
    seat_id: str,
    member_id: str | None = None,
    staff: Staff | None = None,
    time_now: datetime | None = None,
    assigned_minutes: int | None = None,
) -> SessionResponse:
    """Start a new session on an available seat.

    Steps:
        1. Validate seat exists.
        2. Check ``require_member_for_session`` feature flag.
        3. Ensure no other active session exists for this seat.
        4. Validate seat status is ``AVAILABLE`` / ``RESERVED``.
        5. Stub-resolve the billing rate (Phase 3 will be real).
        6. Create ``GamingSession`` record with ``status=ACTIVE``.
        7. Update seat status → ``IN_USE``.
        8. Broadcast ``seat_updated`` to dashboards.
        9. Send ``HIDE_OVERLAY`` to the agent (non-blocking).
        10. Write audit log entry ``SESSION_START``.
        11. Power the console ON via Tuya (non-blocking, best-effort).
        12. Return ``SessionResponse``.
    """
    # 1. Validate seat exists
    seat = await seat_repo.get_by_id(db, seat_id)
    if seat is None:
        raise HTTPException(status_code=404, detail="Seat not found")

    # 2. Feature flag check
    if get_flag("require_member_for_session") and not member_id:
        raise HTTPException(status_code=400, detail="Member required for session")

    # 3. No duplicate active session for this seat
    existing = await session_repo.get_active_by_seat(db, seat_id)
    if existing:
        raise SessionConflictError()

    # 4. Validate seat status
    if seat.status not in (SeatStatus.AVAILABLE, SeatStatus.RESERVED):
        raise SeatUnavailableError()

    # 4. Billing rate
    locked_rate = await resolve_rate(db, seat_id=seat_id, member_id=member_id)

    # 4a. Associate the session with the currently open shift (if any)
    current_shift = await shift_repo.get_open_shift(db)
    shift_id: str | None = current_shift.id if current_shift else None

    # 4b. Check for active package entitlement
    package_entitlement_id: str | None = None
    if member_id:
        entitlement = await package_repo.get_active_entitlement(db, member_id)
        if entitlement:
            package_entitlement_id = entitlement.id

    # 4c. Check for applicable promotion
    promotion_id: str | None = None
    now = time_now if time_now is not None else datetime.now(UTC)
    if now.tzinfo is None or now.tzinfo.utcoffset(now) is None:
        now = now.replace(tzinfo=UTC)
    applicable_promo = await PromotionService.get_applicable_promotion(
        db, seat_id=seat_id, member_id=member_id, time_now=now
    )
    if applicable_promo:
        promotion_id = applicable_promo.id

    # 4d. Assigned-time limit (Epic 6.5.4)
    assigned_end_at: datetime | None = None
    if assigned_minutes and assigned_minutes > 0:
        assigned_end_at = now + timedelta(minutes=assigned_minutes)
        tz = assigned_end_at.tzinfo
        if tz is None or tz.utcoffset(assigned_end_at) is None:
            assigned_end_at = assigned_end_at.replace(tzinfo=UTC)

    # 5. Create session
    session = await session_repo.create(
        db,
        seat_id=seat_id,
        member_id=member_id,
        started_at=now,
        locked_rate_paise=locked_rate.rate_paise,
        locked_pricing_model=locked_rate.pricing_model,
        package_entitlement_id=package_entitlement_id,
        promotion_id=promotion_id,
        discount_paise=0,  # calculated at checkout
        shift_id=shift_id,
        assigned_end_at=assigned_end_at,
    )

    # 6. Update seat → IN_USE
    seat.status = SeatStatus.IN_USE
    await seat_repo.update(db, seat)

    # 7. Broadcast
    payload = {
        "id": seat.id,
        "name": seat.name,
        "status": seat.status.value,
        "current_session_id": session.id,
    }
    try:
        await ws_manager.broadcast_to_dashboards("seat_updated", payload)
    except Exception:
        logger.warning(
            "Failed to broadcast seat_updated for %s", seat_id, exc_info=True
        )

    # 8. Agent command (non-blocking)
    try:
        await ws_manager.send_to_agent(seat_id, {"type": "HIDE_OVERLAY"})
    except AgentOfflineError:
        logger.warning("Agent offline for seat %s — HIDE_OVERLAY not sent", seat_id)

    # 9. Audit
    await audit_service.log(
        db,
        action=AuditAction.SESSION_START,
        entity_type="session",
        entity_id=session.id,
        staff_id=staff.id if staff else None,
        detail="",
    )

    # 10. Console power-on (non-blocking; failure logged, never fatal)
    try:
        from backend.services import tuya_service

        await tuya_service.power_on(db, seat_id)
    except Exception:
        logger.warning("Tuya power-on raised for seat %s", seat_id, exc_info=True)

    # Self-correcting: clear overlay_forced when session starts (HIDE_OVERLAY was sent)
    try:
        from backend.services import seat_service

        await seat_service.set_overlay_forced(db, seat_id, False)
    except Exception:
        logger.warning(
            "Failed to clear overlay_forced for seat %s on session start",
            seat_id,
            exc_info=True,
        )

    return _session_to_response(session)


async def pause_session(
    db: AsyncSession,
    /,  # noqa: W504
    session_id: str,
    staff: Staff | None = None,
) -> SessionResponse:
    """Pause an active session.

    Validates the session is ``ACTIVE``, records ``paused_at``, updates the
    seat to ``PAUSED``, and sends ``SHOW_OVERLAY`` to the agent.
    """
    # Load session
    session = await session_repo.get_by_id(db, session_id)
    if session is None:
        raise SessionNotFoundError(session_id)
    if session.status != SessionStatus.ACTIVE:
        raise InvalidSessionStateError("pause", "ACTIVE")

    # Update session
    _begin_pause(session, datetime.now(UTC))
    session = await session_repo.update(db, session)

    # Update seat
    seat = await seat_repo.get_by_id(db, session.seat_id)
    if seat:
        seat.status = SeatStatus.PAUSED
        await seat_repo.update(db, seat)
        # Broadcast
        try:
            await ws_manager.broadcast_to_dashboards(
                "seat_updated",
                {
                    "id": seat.id,
                    "name": seat.name,
                    "status": seat.status.value,
                    "current_session_id": session.id,
                },
            )
        except Exception:
            logger.warning(
                "Failed to broadcast seat_updated for %s", seat.id, exc_info=True
            )

    # Agent command
    try:
        await ws_manager.send_to_agent(session.seat_id, {"type": "SHOW_OVERLAY"})
    except AgentOfflineError:
        logger.warning(
            "Agent offline for seat %s — SHOW_OVERLAY not sent", session.seat_id
        )

    # Audit
    await audit_service.log(
        db,
        action=AuditAction.SESSION_PAUSE,
        entity_type="session",
        entity_id=session.id,
        staff_id=staff.id if staff else None,
        detail="paused",
    )

    return _session_to_response(session)


async def resume_session(
    db: AsyncSession,
    /,  # noqa: W504
    session_id: str,
    staff: Staff | None = None,
) -> SessionResponse:
    """Resume a paused session.

    Validates the session is ``PAUSED``, accumulates pause duration into
    ``total_paused_seconds``, updates seat to ``IN_USE``, and sends
    ``HIDE_OVERLAY`` to the agent.
    """
    # Load session
    session = await session_repo.get_by_id(db, session_id)
    if session is None:
        raise SessionNotFoundError(session_id)
    if session.status != SessionStatus.PAUSED:
        raise InvalidSessionStateError("resume", "PAUSED")

    # Accumulate pause duration
    _accrue_pause(session, datetime.now(UTC))

    session.status = SessionStatus.ACTIVE
    session = await session_repo.update(db, session)

    # Update seat
    seat = await seat_repo.get_by_id(db, session.seat_id)
    if seat:
        seat.status = SeatStatus.IN_USE
        await seat_repo.update(db, seat)
        try:
            await ws_manager.broadcast_to_dashboards(
                "seat_updated",
                {
                    "id": seat.id,
                    "name": seat.name,
                    "status": seat.status.value,
                    "current_session_id": session.id,
                },
            )
        except Exception:
            logger.warning(
                "Failed to broadcast seat_updated for %s", seat.id, exc_info=True
            )

    # Agent command
    try:
        await ws_manager.send_to_agent(session.seat_id, {"type": "HIDE_OVERLAY"})
    except AgentOfflineError:
        logger.warning(
            "Agent offline for seat %s — HIDE_OVERLAY not sent", session.seat_id
        )

    # Audit
    await audit_service.log(
        db,
        action=AuditAction.SESSION_RESUME,
        entity_type="session",
        entity_id=session.id,
        staff_id=staff.id if staff else None,
        detail="resumed",
    )

    # Self-correcting: clear overlay_forced when session resumes (HIDE_OVERLAY was sent)
    try:
        from backend.services import seat_service

        await seat_service.set_overlay_forced(db, session.seat_id, False)
    except Exception:
        logger.warning(
            "Failed to clear overlay_forced for seat %s on session resume",
            session.seat_id,
            exc_info=True,
        )

    return _session_to_response(session)


async def get_session(db: AsyncSession, /, session_id: str) -> SessionResponse:
    """Get a single session by ID.  Raises 404 if not found."""
    session = await session_repo.get_by_id(db, session_id)
    if session is None:
        raise SessionNotFoundError(session_id)
    return _session_to_response(session)


async def list_active_sessions(db: AsyncSession) -> list[SessionResponse]:
    """Return all sessions with ``ACTIVE`` or ``PAUSED`` status."""
    sessions = await session_repo.list_active(db)
    return [_session_to_response(s) for s in sessions]


async def recover_active_sessions(db: AsyncSession) -> None:
    """Recover any sessions that were active during an unclean shutdown.

    Called at server startup.  Loads all ``ACTIVE`` / ``PAUSED`` sessions from
    the database, ensures their seat statuses are consistent, and broadcasts
    the current state to all dashboards.
    """
    active_sessions = await session_repo.list_active(db)
    for session in active_sessions:
        seat = await seat_repo.get_by_id(db, session.seat_id)
        if seat is None:
            logger.warning(
                "Active session %s references missing seat %s",
                session.id,
                session.seat_id,
            )
            continue

        # Ensure seat status reflects the session state
        expected_status = (
            SeatStatus.PAUSED
            if session.status == SessionStatus.PAUSED
            else SeatStatus.IN_USE
        )
        if seat.status != expected_status:
            seat.status = expected_status
            await seat_repo.update(db, seat)

        try:
            await ws_manager.broadcast_to_dashboards(
                "seat_updated",
                {
                    "id": seat.id,
                    "name": seat.name,
                    "status": seat.status.value,
                    "current_session_id": session.id,
                },
            )
        except Exception:
            logger.warning(
                "Failed to broadcast seat_updated for %s", seat.id, exc_info=True
            )

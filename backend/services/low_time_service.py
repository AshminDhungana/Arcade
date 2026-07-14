"""Low-time warning emission for active sessions (Epic 5.5).

Computes live remaining minutes for each active, package-backed session and
emits a ``LOW_TIME_WARNING`` WebSocket command to the seat's agent once
per session when remaining time crosses ``low_time_warning_minutes``.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import get_config
from backend.core.ws_manager import AgentOfflineError, Msg
from backend.core.ws_manager import manager as ws_manager
from backend.repositories import package_repo, session_repo

logger = logging.getLogger(__name__)

# Sessions already warned in this process; emit LOW_TIME_WARNING once each.
_warned_sessions: set[str] = set()


def compute_remaining_minutes(
    started_at: datetime,
    total_paused_seconds: float | None,
    entitlement_remaining_minutes: int | None,
    now: datetime | None = None,
) -> int:
    """Return remaining minutes = purchased - elapsed (clamped to >= 0)."""
    if now is None:
        now = datetime.now(UTC)
    if started_at.tzinfo is None:
        started_at = started_at.replace(tzinfo=UTC)
    elapsed_seconds = (now - started_at).total_seconds() - (total_paused_seconds or 0)
    elapsed_minutes = max(0, int(elapsed_seconds // 60))
    remaining = (entitlement_remaining_minutes or 0) - elapsed_minutes
    return max(0, remaining)


async def emit_low_time_warnings(db: AsyncSession) -> None:
    """Emit LOW_TIME_WARNING to any active session crossing the threshold."""
    threshold = get_config().low_time_warning_minutes
    active = await session_repo.list_active(db)

    # Drop warned sessions that are no longer active.
    _warned_sessions.intersection_update({s.id for s in active})

    for session in active:
        if session.id in _warned_sessions:
            continue
        if not session.package_entitlement_id:
            # No package cap -> nothing to warn about.
            continue
        entitlement = await package_repo.get_entitlement_by_id(
            db, session.package_entitlement_id
        )
        if entitlement is None or entitlement.remaining_minutes <= 0:
            continue
        remaining = compute_remaining_minutes(
            session.started_at,
            session.total_paused_seconds,
            entitlement.remaining_minutes,
        )
        if remaining > threshold:
            continue
        try:
            await ws_manager.send_to_agent(
                session.seat_id,
                {
                    "type": Msg.LOW_TIME_WARNING,
                    "payload": {"minutes_remaining": remaining},
                },
            )
        except AgentOfflineError:
            logger.warning(
                "Agent offline for seat %s; LOW_TIME_WARNING skipped", session.seat_id
            )
            continue
        _warned_sessions.add(session.id)

"""Session API router.

Routes::

    POST  /api/sessions                → start a new session (cashier+)
    PATCH /api/sessions/{id}/pause       → pause a session (cashier+)
    PATCH /api/sessions/{id}/resume      → resume a session (cashier+)
    GET   /api/sessions/{id}            → get a single session (cashier+)
    GET   /api/sessions/active           → list all active/paused sessions (cashier+)
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import require_cashier
from backend.core.database import get_db
from backend.models.staff import Staff
from backend.schemas.session import SessionResponse
from backend.services import session_service

router = APIRouter(prefix="/sessions", tags=["sessions"])


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class _SessionStartBody(BaseModel):
    """Request body for POST /sessions."""

    seat_id: str
    member_id: str | None = None


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.post("", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    body: _SessionStartBody,
    db: AsyncSession = Depends(get_db),  # noqa: B008
    staff: Annotated[Staff | None, Depends(require_cashier)] = None,  # noqa: B008
) -> SessionResponse:
    """Start a new session on an available seat (cashier+)."""
    return await session_service.start_session(db, body.seat_id, body.member_id, staff)


@router.patch("/{session_id}/pause", response_model=SessionResponse)
async def pause_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),  # noqa: B008
    staff: Annotated[Staff | None, Depends(require_cashier)] = None,  # noqa: B008
) -> SessionResponse:
    """Pause an active session (cashier+)."""
    return await session_service.pause_session(db, session_id, staff)


@router.patch("/{session_id}/resume", response_model=SessionResponse)
async def resume_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),  # noqa: B008
    staff: Annotated[Staff | None, Depends(require_cashier)] = None,  # noqa: B008
) -> SessionResponse:
    """Resume a paused session (cashier+)."""
    return await session_service.resume_session(db, session_id, staff)


@router.get("/active", response_model=Sequence[SessionResponse])
async def list_active_sessions(
    db: AsyncSession = Depends(get_db),  # noqa: B008
    _staff: Annotated[Staff | None, Depends(require_cashier)] = None,  # noqa: B008
) -> Sequence[SessionResponse]:
    """List all active/paused sessions (cashier+)."""
    return await session_service.list_active_sessions(db)


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: str,
    db: AsyncSession = Depends(get_db),  # noqa: B008
    _staff: Annotated[Staff | None, Depends(require_cashier)] = None,  # noqa: B008
) -> SessionResponse:
    """Get a single session by ID (cashier+)."""
    return await session_service.get_session(db, session_id)

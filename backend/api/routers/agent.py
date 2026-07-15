"""Public agent enrollment router.

Routes::

    POST /api/agent/enroll → enroll a freshly-installed agent with a one-time code
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import get_config
from backend.core.database import get_db
from backend.core.lan_discovery import discovery_payload
from backend.core.security import is_ip_locked, record_failed_attempt
from backend.models.seat import Seat
from backend.repositories import seat_repo
from backend.services.enrollment_service import verify_and_consume_enroll_code

router = APIRouter(prefix="/agent", tags=["agent"])


class _EnrollBody(BaseModel):
    """Request body for POST /agent/enroll."""

    code: str
    mac_address: str = ""
    hostname: str = ""


class _EnrollResponse(BaseModel):
    """Response for POST /agent/enroll."""

    seat_id: str
    agent_secret: str
    cafe_name: str
    override_code_hash: str | None


@router.post("/enroll", response_model=_EnrollResponse)
async def enroll_agent(
    body: _EnrollBody,
    request: Request,
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> _EnrollResponse:
    """Enroll a freshly-installed agent by presenting a one-time enroll code.

    Code-gated and rate-limited (reuses the login brute-force limiter:
    5 failures → 15-minute IP lockout). No JWT required. Auto-mints a
    default staff override PIN if the seat has none, so the agent always
    receives one (server-provisioned, pushed on regenerate).
    """
    client_ip = request.client.host if request.client else "unknown"
    locked, _secs = is_ip_locked(client_ip)
    if locked:
        raise HTTPException(status_code=429, detail="Too many attempts; try later")

    ok, seat_id = await verify_and_consume_enroll_code(db, body.code)
    if not ok or seat_id is None:
        record_failed_attempt(client_ip)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired enroll code",
        )

    seat = await db.get(Seat, seat_id)
    if seat is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired enroll code",
        )
    override_hash = await seat_repo.auto_mint_override_pin(db, seat_id)
    return _EnrollResponse(
        seat_id=seat.id,
        agent_secret=seat.agent_secret,
        cafe_name=get_config().cafe_name,
        override_code_hash=override_hash,
    )


@router.get("/discovery")
async def discovery() -> dict[str, Any]:
    """Fallback discovery: returns server address when UDP beacon is blocked."""
    return discovery_payload()

"""Authentication API router.

Routes::

    POST /api/auth/login    → authenticate with staff_id + PIN
    POST /api/auth/refresh  → extend JWT expiry with a valid token
    POST /api/auth/logout   → client-side token discard (stateless)
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.schemas.staff import StaffPinCheck, TokenResponse
from backend.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


def _get_client_ip(request: Request) -> str:
    """Extract the best-effort client IP from the request.

    Checks ``X-Forwarded-For`` first (useful behind a reverse proxy in LANs),
    falls back to the transport peer.
    """
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


# ---------------------------------------------------------------------------
# POST /api/auth/login
# ---------------------------------------------------------------------------


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
)
async def login(
    body: StaffPinCheck,
    request: Request,
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> TokenResponse:
    """Authenticate a staff member and return a JWT.

    Rate limited: 5 failed attempts per IP triggers a 15-minute lockout.
    """
    client_ip = _get_client_ip(request)
    return await auth_service.login(db, body.staff_id, body.pin, client_ip)


# ---------------------------------------------------------------------------
# POST /api/auth/refresh
# ---------------------------------------------------------------------------


@router.post("/refresh", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def refresh(
    request: Request,
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> TokenResponse:
    """Refresh a valid JWT, extending its expiry.

    Validates ``token_version`` against the database — stale tokens
    (e.g., after PIN change or deactivation) are rejected with 401.
    """
    auth = request.headers.get("Authorization", "")
    parts = auth.split(None, 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=401,
            detail="Missing or invalid Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return await auth_service.refresh_token(parts[1], db)


# ---------------------------------------------------------------------------
# POST /api/auth/logout
# ---------------------------------------------------------------------------


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    db: AsyncSession = Depends(get_db),  # noqa: B008
) -> dict[str, str]:  # noqa: D401
    """Client-side token discard (stateless).

    Tokens are invalidated only by PIN change or deactivation (``token_version``
    bump). This endpoint exists for API symmetry and to let clients
    explicitly signal a logout (useful for analytics).
    """
    return {"detail": "Logged out successfully"}

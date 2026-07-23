"""Arcade FastAPI dependencies.

Shared dependency-injection helpers for auth, database sessions, and role
enforcement used across all API routers.
"""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import get_db
from backend.core.security import (
    get_current_staff as _get_current_staff,
)
from backend.core.security import (
    require_admin as _require_admin,
)
from backend.core.security import (
    require_cashier as _require_cashier,
)
from backend.models._enums import StaffRole
from backend.models.staff import Staff
from backend.repositories import staff_zone_repo


def _extract_bearer_token(request: Request) -> str:
    """Extract the Bearer token from the ``Authorization`` header.

    Raises:
        HTTPException(401): If the header is missing or malformed.
    """
    auth = request.headers.get("Authorization", "")
    parts = auth.split(None, 1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=401,
            detail="Missing or invalid Authorization header. Expected: Bearer <token>",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return parts[1]


async def get_current_staff(
    request: Request,
    db: AsyncSession = Depends(get_db),  # noqa: B008 – FastAPI DI idiom
) -> Staff:
    """FastAPI dependency that resolves the current authenticated staff.

    Validates the Bearer token from the ``Authorization`` header and
    ensures ``token_version`` matches the database.
    """
    token = _extract_bearer_token(request)
    return await _get_current_staff(token, db)


async def require_admin(
    staff: Staff = Depends(get_current_staff),  # noqa: B008 – FastAPI DI idiom
) -> Staff:
    """FastAPI dependency that enforces Admin role.

    Raises:
        HTTPException(403): If the staff member is not an Admin.
    """
    return _require_admin(staff)


async def require_cashier(
    staff: Staff = Depends(get_current_staff),  # noqa: B008 – FastAPI DI idiom
) -> Staff:
    """FastAPI dependency that enforces Cashier or Admin role.

    Raises:
        HTTPException(403): If the staff member is not a Cashier or Admin.
    """
    return _require_cashier(staff)


async def require_self_or_admin(
    staff_id: str,
    staff: Staff = Depends(get_current_staff),  # noqa: B008 – FastAPI DI idiom
) -> Staff:
    """FastAPI dependency that enforces Admin OR the account owner.

    Used for PIN changes: an Admin may change any PIN; a non-admin staff
    member may only change their own.

    Raises:
        HTTPException(403): If the caller is neither an Admin nor the
            staff member identified by *staff_id*.
    """
    if staff.role != StaffRole.ADMIN and staff.id != staff_id:
        raise HTTPException(
            status_code=403, detail="Admin or account owner access required"
        )
    return staff


async def require_zone_access(
    zone_id: str,
    staff: Staff = Depends(get_current_staff),  # noqa: B008 – FastAPI DI idiom
    db: AsyncSession = Depends(get_db),  # noqa: B008 – FastAPI DI idiom
) -> Staff:
    """FastAPI dependency that enforces zone access for the current staff.

    - Admins always pass (they have access to all zones)
    - Cashiers must have an active StaffZone assignment for the zone_id

    Raises:
        HTTPException(403): If the cashier is not assigned to the zone.
    """
    if staff.role == StaffRole.ADMIN:
        return staff

    has_access = await staff_zone_repo.is_staff_assigned_to_zone(
        db, staff_id=staff.id, zone_id=zone_id
    )
    if not has_access:
        raise HTTPException(
            status_code=403, detail="Access denied: not authorized for this zone"
        )
    return staff

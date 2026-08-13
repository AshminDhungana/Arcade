"""License verification API router — admin-only license health check.

Routes::

    POST /api/license/verify → run the offline license check and audit it
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import require_admin
from backend.core.database import get_db
from backend.licensing.verify import check_license
from backend.models._enums import AuditAction
from backend.models.staff import Staff
from backend.services import audit_service

router = APIRouter(prefix="/license", tags=["license"])


@router.post("/verify")
async def verify_license(
    db: AsyncSession = Depends(get_db),  # noqa: B008
    staff: Annotated[Staff | None, Depends(require_admin)] = None,  # noqa: B008
) -> dict[str, object]:
    """Verify the local ``license.key`` and audit the result (B.8)."""
    try:
        result = check_license()
    except Exception as exc:  # safety net — check_license() never raises
        raise HTTPException(
            status_code=500, detail=f"License check failed: {exc}"
        ) from exc

    hw_id = result.payload.get("hardware_id") if result.payload else None
    error_reason = result.error.value if result.error else "unknown"
    detail = "status=ok" if result.ok else f"status=error:{error_reason}"
    await audit_service.log(
        db,
        action=AuditAction.LICENSE_CHECK,
        entity_type="license",
        entity_id=hw_id or "unknown",
        staff_id=staff.id if staff else None,
        detail=detail,
    )
    return {
        "ok": result.ok,
        "error": result.error.value if result.error else None,
        "payload": result.payload,
    }

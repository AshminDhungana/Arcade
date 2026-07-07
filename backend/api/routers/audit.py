"""Audit log API router — read-only, Admin only.

Endpoints::

    GET /api/audit  → paginated, filterable list of audit log entries
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import require_admin
from backend.core.database import get_db
from backend.models._enums import AuditAction
from backend.schemas.audit import AuditLogResponse
from backend.services import audit_service

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get(
    "",
    response_model=list[AuditLogResponse],
    status_code=status.HTTP_200_OK,
)
async def list_audit_logs(
    db: AsyncSession = Depends(get_db),  # noqa: B008
    staff: object = Depends(require_admin),  # noqa: B008
    start_date: str | None = Query(
        None, description="Filter by start date (YYYY-MM-DD)"
    ),
    end_date: str | None = Query(None, description="Filter by end date (YYYY-MM-DD)"),
    action: AuditAction | None = Query(None, description="Filter by action type"),  # noqa: B008
    staff_id: str | None = Query(None, description="Filter by staff ID"),
    limit: int = Query(50, ge=1, le=500, description="Number of records per page"),
    offset: int = Query(0, ge=0, description="Page offset"),
) -> list[AuditLogResponse]:
    """List audit log entries.

    Requires Admin role. Supports pagination via ``limit``/``offset`` and
    optional date/action/staff filters.
    """
    logs = await audit_service.list_logs(
        db,
        start_date=start_date,
        end_date=end_date,
        action=action,
        staff_id=staff_id,
        limit=limit,
        offset=offset,
    )
    return [AuditLogResponse.model_validate(l) for l in logs]  # noqa: E741

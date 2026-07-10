"""AuditService -- thin, stateless wrapper around the immutable audit repository.

All audit logging should go through this module so callers do not need to
remember repository details or enum value extraction.
"""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from backend.models._enums import AuditAction
from backend.models.audit_log import AuditLog
from backend.repositories import audit_repo


async def log(
    db: AsyncSession,
    *,
    action: AuditAction,
    entity_type: str,
    entity_id: str,
    staff_id: str | None = None,
    detail: str | None = None,
) -> AuditLog:
    """Write an immutable audit log entry.

    Parameters
    ----------
    db: AsyncSession
        Active SQLAlchemy async session.
    action: AuditAction
        The action enum member (e.g., ``AuditAction.SESSION_START``).
    entity_type: str
        Domain name of the affected entity (e.g., ``"session"``).
    entity_id: str
        UUID of the affected entity.
    staff_id: str | None
        UUID of the staff member who triggered the action.
    detail: str | None
        Optional JSON string or human-readable description.

    Returns
    -------
    AuditLog
        The newly created log record.
    """
    return await audit_repo.create(
        db,
        action=action.value,
        entity_type=entity_type,
        entity_id=entity_id,
        staff_id=staff_id,
        detail=detail,
    )


async def list_logs(
    db: AsyncSession,
    *,
    start_date: str | None = None,
    end_date: str | None = None,
    action: AuditAction | None = None,
    staff_id: str | None = None,
    entity_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> Sequence[AuditLog]:
    """List audit log entries with optional filters.

    Parameters
    ----------
    start_date: str | None
        ``YYYY-MM-DD`` inclusive.
    end_date: str | None
        ``YYYY-MM-DD`` inclusive.
    action: AuditAction | None
        Filter to a specific action type.
    staff_id: str | None
        Filter to a specific staff member.
    entity_id: str | None
        Filter to a specific entity ID.
    limit: int
        Max records per page (default 50, max 500).
    offset: int
        Page offset (default 0).

    Returns
    -------
    Sequence[AuditLog]
        Ordered by ``timestamp DESC``.
    """
    return await audit_repo.list(
        db,
        start_date=start_date,
        end_date=end_date,
        action=action.value if action else None,
        staff_id=staff_id,
        entity_id=entity_id,
        limit=limit,
        offset=offset,
    )

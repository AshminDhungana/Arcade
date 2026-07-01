"""AuditLog repository — immutable: create & list only.

No update or delete methods are provided; the audit log is
append-only by design (SDD §4.4, §11.6).
"""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import AuditLog


async def create(
    db: AsyncSession,
    *,
    action: str,
    entity_type: str,
    entity_id: str,
    staff_id: str | None = None,
    detail: str | None = None,
) -> AuditLog:
    log = AuditLog(
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        staff_id=staff_id,
        detail=detail,
    )
    db.add(log)
    await db.flush()
    await db.refresh(log)
    return log


async def get_by_id(db: AsyncSession, audit_log_id: str) -> AuditLog | None:
    result = await db.execute(select(AuditLog).where(AuditLog.id == audit_log_id))
    return result.scalar_one_or_none()


async def list(db: AsyncSession) -> Sequence[AuditLog]:
    result = await db.execute(select(AuditLog))
    return result.scalars().all()

"""AuditLog repository — immutable: create & list only.

No update or delete methods are provided; the audit log is
append-only by design (SDD §4.4, §11.6).
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC

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


async def list(
    db: AsyncSession,
    *,
    start_date: str | None = None,
    end_date: str | None = None,
    action: str | None = None,
    staff_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> Sequence[AuditLog]:
    from datetime import datetime

    from sqlalchemy import and_

    stmt = select(AuditLog)
    conditions = []
    if start_date:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=UTC)
        conditions.append(AuditLog.timestamp >= start_dt)
    if end_date:
        end_dt = datetime.strptime(end_date, "%Y-%m-%d").replace(
            hour=23, minute=59, second=59, tzinfo=UTC
        )
        conditions.append(AuditLog.timestamp <= end_dt)
    if action:
        conditions.append(AuditLog.action == action)
    if staff_id:
        conditions.append(AuditLog.staff_id == staff_id)
    if conditions:
        stmt = stmt.where(and_(*conditions))
    stmt = stmt.order_by(AuditLog.timestamp.desc()).offset(offset).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()

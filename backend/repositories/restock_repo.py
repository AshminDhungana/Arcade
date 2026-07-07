"""RestockLog repository — create and list only.

No update or delete; the restock log is append-only by design.
"""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import RestockLog


async def create(
    db: AsyncSession,
    *,
    menu_item_id: str,
    quantity_added: int,
    logged_by_staff_id: str,
) -> RestockLog:
    log = RestockLog(
        menu_item_id=menu_item_id,
        quantity_added=quantity_added,
        logged_by_staff_id=logged_by_staff_id,
    )
    db.add(log)
    await db.flush()
    await db.refresh(log)
    return log


async def get_by_id(db: AsyncSession, restock_log_id: str) -> RestockLog | None:
    result = await db.execute(select(RestockLog).where(RestockLog.id == restock_log_id))
    return result.scalar_one_or_none()


async def list_by_menu_item(
    db: AsyncSession, menu_item_id: str
) -> Sequence[RestockLog]:
    result = await db.execute(
        select(RestockLog).where(RestockLog.menu_item_id == menu_item_id)
    )
    return result.scalars().all()


async def list_all(db: AsyncSession) -> Sequence[RestockLog]:
    result = await db.execute(select(RestockLog))
    return result.scalars().all()

"""POS item repository — CRUD."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import SessionPOSItem


async def create(
    db: AsyncSession,
    *,
    session_id: str,
    menu_item_id: str,
    quantity: int = 1,
    unit_price_paise: int = 0,
) -> SessionPOSItem:
    item = SessionPOSItem(
        session_id=session_id,
        menu_item_id=menu_item_id,
        quantity=quantity,
        unit_price_paise=unit_price_paise,
    )
    db.add(item)
    await db.flush()
    await db.refresh(item)
    return item


async def get_by_id(db: AsyncSession, pos_item_id: str) -> SessionPOSItem | None:
    result = await db.execute(
        select(SessionPOSItem).where(SessionPOSItem.id == pos_item_id)
    )
    return result.scalar_one_or_none()


async def list(db: AsyncSession) -> Sequence[SessionPOSItem]:
    result = await db.execute(select(SessionPOSItem))
    return result.scalars().all()


async def update(db: AsyncSession, pos_item: SessionPOSItem) -> SessionPOSItem:
    db.add(pos_item)
    await db.flush()
    await db.refresh(pos_item)
    return pos_item


async def delete_by_id(db: AsyncSession, pos_item_id: str) -> bool:
    item = await get_by_id(db, pos_item_id)
    if item is None:
        return False
    await db.delete(item)
    await db.flush()
    return True

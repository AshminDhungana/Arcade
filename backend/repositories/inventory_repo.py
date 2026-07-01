"""Inventory (MenuItem) repository — CRUD."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import MenuItem


async def create(
    db: AsyncSession,
    *,
    name: str,
    category: str | None = None,
    price_paise: int = 0,
    stock_quantity: int | None = None,
    low_stock_threshold: int | None = None,
    is_available: bool = True,
) -> MenuItem:
    item = MenuItem(
        name=name,
        category=category,
        price_paise=price_paise,
        stock_quantity=stock_quantity,
        low_stock_threshold=low_stock_threshold,
        is_available=is_available,
    )
    db.add(item)
    await db.flush()
    await db.refresh(item)
    return item


async def get_by_id(db: AsyncSession, menu_item_id: str) -> MenuItem | None:
    result = await db.execute(select(MenuItem).where(MenuItem.id == menu_item_id))
    return result.scalar_one_or_none()


async def list(db: AsyncSession) -> Sequence[MenuItem]:
    result = await db.execute(select(MenuItem))
    return result.scalars().all()


async def update(db: AsyncSession, menu_item: MenuItem) -> MenuItem:
    db.add(menu_item)
    await db.flush()
    await db.refresh(menu_item)
    return menu_item


async def delete_by_id(db: AsyncSession, menu_item_id: str) -> bool:
    item = await get_by_id(db, menu_item_id)
    if item is None:
        return False
    await db.delete(item)
    await db.flush()
    return True

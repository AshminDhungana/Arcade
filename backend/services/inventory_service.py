"""InventoryService — business logic for inventory restocking and queries."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.ws_manager import manager as ws_manager
from backend.models import MenuItem
from backend.repositories import audit_repo, inventory_repo, restock_repo


async def restock(
    db: AsyncSession,
    *,
    menu_item_id: str,
    quantity: int,
    logged_by_staff_id: str,
    note: str | None = None,
) -> MenuItem:
    """Restock a menu item, creating an audit trail.

    1. Validate the menu item exists.
    2. Increment ``stock_quantity``.
    3. If the item was unavailable due to zero stock, re-enable it.
    4. Log the restock event.
    5. Audit log and broadcast dashboard update.

    :raises HTTPException: 404 if menu item not found.
    :returns: The updated ``MenuItem``.
    """
    menu_item = await inventory_repo.get_by_id(db, menu_item_id)
    if menu_item is None:
        raise HTTPException(
            status_code=404, detail=f"Menu item {menu_item_id} not found"
        )

    # 2. Increment stock quantity
    if menu_item.stock_quantity is None:
        menu_item.stock_quantity = 0
    menu_item.stock_quantity += quantity

    # 3. Re-enable is_available if it was disabled due to zero stock
    if not menu_item.is_available and menu_item.stock_quantity > 0:
        menu_item.is_available = True

    # Update timestamp
    menu_item.updated_at = datetime.now(UTC)
    await inventory_repo.update(db, menu_item)

    # 4. Log the restock event
    await restock_repo.create(
        db,
        menu_item_id=menu_item_id,
        quantity_added=quantity,
        logged_by_staff_id=logged_by_staff_id,
    )

    # 5. Audit log and broadcast
    detail = f"Restocked {quantity} units of {menu_item.name}"
    if note:
        detail += f" — Note: {note}"

    await audit_repo.create(
        db,
        action="INVENTORY_RESTOCK",
        entity_type="MenuItem",
        entity_id=menu_item_id,
        staff_id=logged_by_staff_id,
        detail=detail,
    )

    await ws_manager.broadcast_to_dashboards(
        "inventory_updated", {"menu_item_id": menu_item_id}
    )

    return menu_item


async def get_low_stock_items(db: AsyncSession) -> list[MenuItem]:
    """Return all menu items where stock is at or below the low-stock threshold.

    Items with ``NULL`` stock quantity or ``NULL`` threshold are excluded.
    """
    return list(await inventory_repo.get_low_stock_items(db))

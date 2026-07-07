"""POSService — business logic for adding and removing POS items from sessions."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.feature_flags import get_flag
from backend.core.ws_manager import manager as ws_manager
from backend.models import SessionPOSItem
from backend.models._enums import AuditAction, SessionStatus
from backend.repositories import inventory_repo, pos_repo, session_repo
from backend.services import audit_service


class POSServiceError(HTTPException):
    """Base exception for POS service errors."""

    def __init__(self, detail: str, status_code: int = 400) -> None:
        super().__init__(status_code=status_code, detail=detail)


async def add_item(
    db: AsyncSession,
    *,
    session_id: str,
    menu_item_id: str,
    quantity: int,
    staff_id: str | None = None,
) -> SessionPOSItem:
    """Add a POS item to an active session.

    1. Validate session is active.
    2. Validate menu item exists and is available.
    3. Lock ``unit_price_paise`` at the *current* menu item price.
    4. If ``enable_inventory`` is ON, decrement stock and handle
       low-stock / out-of-stock side effects.
    5. Create the :class:`SessionPOSItem` record.
    6. Audit log and broadcast.

    :raises HTTPException: 404/400 for invalid session or item.
    :returns: The created ``SessionPOSItem``.
    """
    # 1. Session validation
    session = await session_repo.get_by_id(db, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")
    if session.status not in (SessionStatus.ACTIVE, SessionStatus.PAUSED):
        raise HTTPException(
            status_code=400, detail="Session must be active to add items"
        )

    # 2. Menu item validation
    menu_item = await inventory_repo.get_by_id(db, menu_item_id)
    if menu_item is None:
        raise HTTPException(
            status_code=404, detail=f"Menu item {menu_item_id} not found"
        )
    if not menu_item.is_available:
        raise HTTPException(status_code=400, detail="Item is not available")

    # 3. Lock unit_price_paise at current menu item price
    unit_price = menu_item.price_paise

    # 4. Inventory handling (feature-flagged)
    if get_flag("enable_inventory"):
        if menu_item.stock_quantity is not None:
            if menu_item.stock_quantity < quantity:
                raise HTTPException(
                    status_code=400, detail="Insufficient stock for this item"
                )
            menu_item.stock_quantity -= quantity
            # Low-stock / out-of-stock side effects
            if menu_item.stock_quantity == 0:
                menu_item.is_available = False
            menu_item.updated_at = datetime.now(UTC)
            await inventory_repo.update(db, menu_item)

    # 5. Create the POS item record
    item = await pos_repo.create(
        db,
        session_id=session_id,
        menu_item_id=menu_item_id,
        quantity=quantity,
        unit_price_paise=unit_price,
    )

    # 6. Audit log
    await audit_service.log(
        db,
        action=AuditAction.POS_ITEM_ADDED,
        entity_type="SessionPOSItem",
        entity_id=item.id,
        staff_id=staff_id,
        detail=f"Added {quantity} x {menu_item.name} to session {session_id}",
    )

    # 7. Broadcast real-time update
    await ws_manager.broadcast_to_dashboards(
        "session_updated", {"session_id": session_id}
    )

    return item


async def remove_item(
    db: AsyncSession,
    *,
    pos_item_id: str,
    session_id: str,
    staff_id: str | None = None,
) -> bool:
    """Remove a POS item from a session.

    :param pos_item_id: The ``SessionPOSItem.id`` to remove.
    :param session_id: The parent session ID (for validation).
    :returns: ``True`` if the item was removed, ``False`` if not found.
    """
    item = await pos_repo.get_by_id(db, pos_item_id)
    if item is None:
        return False
    if item.session_id != session_id:
        raise HTTPException(
            status_code=400, detail="Item does not belong to this session"
        )

    deleted = await pos_repo.delete_by_id(db, pos_item_id)
    if deleted:
        await audit_service.log(
            db,
            action=AuditAction.POS_ITEM_REMOVED,
            entity_type="SessionPOSItem",
            entity_id=pos_item_id,
            staff_id=staff_id,
            detail=f"Removed item {pos_item_id} from session {session_id}",
        )
        await ws_manager.broadcast_to_dashboards(
            "session_updated", {"session_id": session_id}
        )
    return deleted


async def list_session_items(
    db: AsyncSession, *, session_id: str
) -> list[SessionPOSItem]:
    """Return all POS items for a given session."""
    return list(await pos_repo.list_by_session(db, session_id))

"""Menu item admin API router.

Routes::

    POST   /api/menu-items        -> create menu item (Admin)
    GET    /api/menu-items/{id}   -> get one (Admin)
    PUT    /api/menu-items/{id}   -> update (Admin)
    DELETE /api/menu-items/{id}   -> delete (Admin)

Reads for the POS UI remain at ``GET /api/pos/menu`` (cashier+).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Body, Depends, Path, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import require_admin
from backend.core.database import get_db
from backend.models.menu_item import MenuItem
from backend.repositories import inventory_repo
from backend.schemas.pos import MenuItemCreate, MenuItemResponse, MenuItemUpdate

router = APIRouter(prefix="/menu-items", tags=["menu-items"])


def _ensure_tz(dt: datetime | None) -> datetime | None:
    """SQLite may strip tzinfo; re-attach UTC so AwareDatetime validates."""
    if dt is not None and (dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None):
        return dt.replace(tzinfo=UTC)
    return dt


def _to_response(item: MenuItem) -> MenuItemResponse:
    """Normalise ``updated_at`` timezone and build a ``MenuItemResponse``."""
    item.updated_at = _ensure_tz(item.updated_at)  # type: ignore[assignment]
    return MenuItemResponse.model_validate(item)


@router.post(
    "",
    response_model=MenuItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a menu item",
)
async def create_menu_item(
    body: Annotated[MenuItemCreate, Body(description="New menu item")],
    db: AsyncSession = Depends(get_db),  # noqa: B008
    _staff: Annotated[None, Depends(require_admin)] = None,  # noqa: B008
) -> MenuItemResponse:
    """Create a menu item. Admin only."""
    created = await inventory_repo.create(
        db,
        name=body.name,
        category=body.category,
        price_paise=body.price_paise,
        stock_quantity=body.stock_quantity,
        low_stock_threshold=body.low_stock_threshold,
        is_available=body.is_available,
    )
    return _to_response(created)


@router.get(
    "/{menu_item_id}",
    response_model=MenuItemResponse,
    summary="Get a menu item",
)
async def get_menu_item(
    menu_item_id: Annotated[str, Path(..., description="Menu item ID")],
    db: AsyncSession = Depends(get_db),  # noqa: B008
    _staff: Annotated[None, Depends(require_admin)] = None,  # noqa: B008
) -> MenuItemResponse:
    """Get one menu item. Admin only."""
    item = await inventory_repo.get_by_id(db, menu_item_id)
    if item is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Menu item not found")
    return _to_response(item)


@router.put(
    "/{menu_item_id}",
    response_model=MenuItemResponse,
    summary="Update a menu item",
)
async def update_menu_item(
    menu_item_id: Annotated[str, Path(..., description="Menu item ID")],
    body: Annotated[MenuItemUpdate, Body(description="Fields to update")],
    db: AsyncSession = Depends(get_db),  # noqa: B008
    _staff: Annotated[None, Depends(require_admin)] = None,  # noqa: B008
) -> MenuItemResponse:
    """Update a menu item (PATCH semantics — only provided fields). Admin only."""
    item = await inventory_repo.get_by_id(db, menu_item_id)
    if item is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Menu item not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    updated = await inventory_repo.update(db, item)
    return _to_response(updated)


@router.delete(
    "/{menu_item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a menu item",
)
async def delete_menu_item(
    menu_item_id: Annotated[str, Path(..., description="Menu item ID")],
    db: AsyncSession = Depends(get_db),  # noqa: B008
    _staff: Annotated[None, Depends(require_admin)] = None,  # noqa: B008
) -> Response:
    """Delete a menu item. Admin only."""
    ok = await inventory_repo.delete_by_id(db, menu_item_id)
    if not ok:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Menu item not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)

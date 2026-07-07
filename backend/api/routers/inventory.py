"""Inventory API router.

Routes::

    POST /api/inventory/restock           → restock a menu item (admin)
    GET  /api/inventory/low-stock          → list low-stock items (cashier+)
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import require_admin, require_cashier
from backend.core.database import get_db
from backend.core.feature_flags import require_feature
from backend.models.staff import Staff
from backend.schemas.pos import MenuItemResponse
from backend.services import inventory_service

router = APIRouter(
    prefix="/inventory",
    tags=["Inventory"],
    dependencies=[Depends(require_feature("enable_inventory"))],
)


# ── Request / response models ──────────────────────────────────────────


class _RestockBody(BaseModel):
    """Request body for POST /inventory/restock."""

    menu_item_id: str
    quantity: int = Field(..., gt=0)
    note: str | None = None


# ── Routes ───────────────────────────────────────────────────────────────


@router.post("/restock", status_code=status.HTTP_200_OK)
async def restock_item(
    body: _RestockBody,
    db: AsyncSession = Depends(get_db),  # noqa: B008 – FastAPI DI idiom
    staff: Annotated[Staff | None, Depends(require_admin)] = None,  # noqa: B008
) -> MenuItemResponse:
    """Restock a menu item, re-enabling it if it was out of stock (admin only)."""
    if staff is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    result = await inventory_service.restock(
        db,
        menu_item_id=body.menu_item_id,
        quantity=body.quantity,
        logged_by_staff_id=staff.id,
        note=body.note,
    )
    return MenuItemResponse.model_validate(result)


@router.get("/low-stock", status_code=status.HTTP_200_OK)
async def get_low_stock_items(
    db: AsyncSession = Depends(get_db),  # noqa: B008
    _staff: Annotated[Staff | None, Depends(require_cashier)] = None,  # noqa: B008
) -> list[MenuItemResponse]:
    """Return all menu items at or below their low-stock threshold (cashier+)."""
    items = await inventory_service.get_low_stock_items(db)
    return [MenuItemResponse.model_validate(i) for i in items]

"""POS API router.

Routes::

    GET   /api/pos/menu                → list all menu items (cashier+)
    POST  /api/pos/items               → add item to session (cashier+)
    DELETE /api/pos/items/{id}          → remove item from session (cashier+)
    GET   /api/pos/items/{session_id}  → list session items (cashier+)
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import require_cashier
from backend.core.database import get_db
from backend.core.feature_flags import require_feature
from backend.models.staff import Staff
from backend.repositories import inventory_repo
from backend.schemas.pos import MenuItemResponse, SessionPOSItemResponse
from backend.services import pos_service

router = APIRouter(
    prefix="/pos",
    tags=["POS"],
    dependencies=[Depends(require_feature("enable_pos"))],
)


# ── Request / response models ──────────────────────────────────────────


class _AddItemBody(BaseModel):
    """Request body for POST /pos/items."""

    session_id: str
    menu_item_id: str
    quantity: int = Field(1, ge=1)


# ── Routes ───────────────────────────────────────────────────────────────


@router.post("/items", status_code=status.HTTP_201_CREATED)
async def add_pos_item(
    body: _AddItemBody,
    db: AsyncSession = Depends(get_db),  # noqa: B008 – FastAPI DI idiom
    staff: Annotated[Staff | None, Depends(require_cashier)] = None,  # noqa: B008
) -> SessionPOSItemResponse:
    """Add a POS item to an active session."""
    result = await pos_service.add_item(
        db,
        session_id=body.session_id,
        menu_item_id=body.menu_item_id,
        quantity=body.quantity,
        staff_id=staff.id if staff else None,
    )
    return SessionPOSItemResponse.model_validate(result)


@router.delete("/items/{pos_item_id}", status_code=status.HTTP_200_OK)
async def remove_pos_item(
    pos_item_id: str,
    session_id: str,
    db: AsyncSession = Depends(get_db),  # noqa: B008
    staff: Annotated[Staff | None, Depends(require_cashier)] = None,  # noqa: B008
) -> dict[str, bool | str]:
    """Remove a POS item from a session (cashier+)."""
    deleted = await pos_service.remove_item(
        db,
        pos_item_id=pos_item_id,
        session_id=session_id,
        staff_id=staff.id if staff else None,
    )
    return {"deleted": deleted, "pos_item_id": pos_item_id}


@router.get("/items/{session_id}")
async def list_session_items(
    session_id: str,
    db: AsyncSession = Depends(get_db),  # noqa: B008
    _staff: Annotated[Staff | None, Depends(require_cashier)] = None,  # noqa: B008
) -> list[SessionPOSItemResponse]:
    """List all POS items for a given session."""
    items = await pos_service.list_session_items(db, session_id=session_id)
    return [SessionPOSItemResponse.model_validate(i) for i in items]


@router.get("/menu")
async def list_menu_items(
    db: AsyncSession = Depends(get_db),  # noqa: B008
    _staff: Annotated[Staff | None, Depends(require_cashier)] = None,  # noqa: B008
) -> list[MenuItemResponse]:
    """List all menu items for POS display (cashier+)."""
    items = await inventory_repo.list(db)
    return [MenuItemResponse.model_validate(i) for i in items]

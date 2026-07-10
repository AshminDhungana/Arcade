"""Promotions API router.

Routes:
    GET    /api/promotions           → list all promotions (admin)
    POST   /api/promotions           → create promotion (admin)
    GET    /api/promotions/{id}      → get promotion by ID (admin)
    PATCH  /api/promotions/{id}      → update promotion (admin)
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Annotated

from fastapi import APIRouter, Body, Depends, Path, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import require_admin
from backend.core.database import get_db
from backend.core.feature_flags import require_feature
from backend.models.staff import Staff
from backend.repositories import promotion_repo
from backend.schemas.promotion import (
    PromotionCreate,
    PromotionResponse,
    PromotionUpdate,
)

router = APIRouter(prefix="/promotions", tags=["promotions"])

# Feature flag: entire router disabled when enable_promotions=false
router.dependencies.append(Depends(require_feature("enable_promotions")))


@router.get(
    "",
    response_model=Sequence[PromotionResponse],
    summary="List all promotions",
)
async def list_promotions(
    db: AsyncSession = Depends(get_db),  # noqa: B008
    _staff: Annotated[Staff | None, Depends(require_admin)] = None,  # noqa: B008
) -> Sequence[PromotionResponse]:
    """Return all promotions (active and inactive). Admin only."""
    promotions = await promotion_repo.list(db)
    return [PromotionResponse.model_validate(p) for p in promotions]


@router.post(
    "",
    response_model=PromotionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new promotion",
)
async def create_promotion(
    body: Annotated[PromotionCreate, Body(description="Promotion details")],
    db: AsyncSession = Depends(get_db),  # noqa: B008
    _staff: Annotated[Staff | None, Depends(require_admin)] = None,  # noqa: B008
) -> PromotionResponse:
    """Create a new promotion. Admin only."""
    promo = await promotion_repo.create(
        db,
        name=body.name,
        type=body.type.value,
        discount_type=body.discount_type.value,
        discount_value=body.discount_value,
        active_days=body.active_days,
        active_from_hour=body.active_from_hour,
        active_to_hour=body.active_to_hour,
        min_group_size=body.min_group_size,
        zone_restriction_id=body.zone_restriction_id,
        is_active=body.is_active,
        valid_from=body.valid_from,
        valid_until=body.valid_until,
    )
    return PromotionResponse.model_validate(promo)


@router.get(
    "/{promotion_id}",
    response_model=PromotionResponse,
    summary="Get a promotion by ID",
)
async def get_promotion(
    promotion_id: Annotated[str, Path(description="Promotion ID")],
    db: AsyncSession = Depends(get_db),  # noqa: B008
    _staff: Annotated[Staff | None, Depends(require_admin)] = None,  # noqa: B008
) -> PromotionResponse:
    """Return a single promotion by ID. Admin only."""
    promo = await promotion_repo.get_by_id(db, promotion_id)
    if promo is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Promotion not found")
    return PromotionResponse.model_validate(promo)


@router.patch(
    "/{promotion_id}",
    response_model=PromotionResponse,
    summary="Update a promotion",
)
async def update_promotion(
    promotion_id: Annotated[str, Path(description="Promotion ID")],
    body: Annotated[PromotionUpdate, Body(description="Fields to update")],
    db: AsyncSession = Depends(get_db),  # noqa: B008
    _staff: Annotated[Staff | None, Depends(require_admin)] = None,  # noqa: B008
) -> PromotionResponse:
    """Update promotion fields. Admin only."""
    promo = await promotion_repo.get_by_id(db, promotion_id)
    if promo is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Promotion not found")

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field in ("type", "discount_type") and value is not None:
            value = value.value  # Enum → string
        setattr(promo, field, value)

    updated = await promotion_repo.update(db, promo)
    return PromotionResponse.model_validate(updated)

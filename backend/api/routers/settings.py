"""Settings API router.

Routes::

    GET /api/settings  → return all settings as flat key-value dict (cashier+)
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import require_cashier
from backend.core.database import get_db
from backend.models.settings import AppSettings
from backend.models.staff import Staff

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("")
async def get_settings(
    db: AsyncSession = Depends(get_db),  # noqa: B008
    _staff: Annotated[Staff | None, Depends(require_cashier)] = None,  # noqa: B008
) -> dict[str, str]:
    """Return all settings as a flat {key: value} dict (cashier+)."""
    result = await db.execute(select(AppSettings))
    rows = result.scalars().all()
    return {row.key: row.value for row in rows}

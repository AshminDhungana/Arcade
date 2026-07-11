"""Settings API router.

Routes::

    GET /api/settings  → return all settings as flat key-value dict (cashier+)
    PATCH /api/settings → update one or more settings (admin), refreshes flag cache
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import require_admin, require_cashier
from backend.core.database import get_db
from backend.core.feature_flags import refresh_flags
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


@router.patch("")
async def patch_settings(
    updates: dict[str, str],
    db: AsyncSession = Depends(get_db),  # noqa: B008
    _staff: Annotated[Staff | None, Depends(require_admin)] = None,  # noqa: B008
) -> dict[str, str]:
    """Update one or more settings rows (admin). Refreshes the flag cache so
    503 gating flips live."""
    if not updates:
        raise HTTPException(status_code=400, detail="No settings provided.")
    for key, value in updates.items():
        stmt = select(AppSettings).where(AppSettings.key == key)
        row = (await db.execute(stmt)).scalar_one_or_none()
        if row is None:
            row = AppSettings(key=key, value=str(value))
            db.add(row)
        else:
            row.value = str(value)
    await db.commit()
    await refresh_flags(db)
    result = await db.execute(select(AppSettings))
    return {r.key: r.value for r in result.scalars().all()}

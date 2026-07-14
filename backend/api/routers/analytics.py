# backend/api/routers/analytics.py
"""Analytics API router -- admin-only summary endpoint."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import require_admin
from backend.core.database import get_db
from backend.models.staff import Staff
from backend.schemas.analytics import AnalyticsSummary
from backend.services import analytics_service

router = APIRouter(prefix="/analytics", tags=["analytics"])

DbDep = Annotated[AsyncSession, Depends(get_db)]
AdminDep = Annotated[Staff, Depends(require_admin)]


@router.get("/summary", response_model=AnalyticsSummary)
async def get_summary(db: DbDep, staff: AdminDep) -> AnalyticsSummary:
    return await analytics_service.get_summary(db)

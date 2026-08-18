"""P&L Reports router — Admin only."""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.deps import require_admin
from backend.core.database import get_db
from backend.models.staff import Staff
from backend.schemas.reports import PLSummaryResponse
from backend.services import pl_service

router = APIRouter(prefix="/reports/pl", tags=["reports"])

DbDep = Annotated[AsyncSession, Depends(get_db)]
AdminDep = Annotated[Staff, Depends(require_admin)]


@router.get("/summary", response_model=PLSummaryResponse)
async def pl_summary(
    db: DbDep,
    staff: AdminDep,
    start: Annotated[
        date | None,
        Query(
            description="Start date (inclusive), "
            "defaults to first day of current month"
        ),
    ] = None,
    end: Annotated[
        date | None,
        Query(description="End date (inclusive), defaults to today"),
    ] = None,
) -> PLSummaryResponse:
    today = date.today()
    if start is None:
        start = today.replace(day=1)
    if end is None:
        end = today
    summary = await pl_service.get_pl_summary(db, start, end)
    # Convert ExpenseCategory keys to strings for JSON serialization
    expenses_by_cat = {
        cat.value: amount for cat, amount in summary.expenses_by_category.items()
    }
    return PLSummaryResponse(
        period_start=summary.period_start,
        period_end=summary.period_end,
        session_revenue_paise=summary.session_revenue_paise,
        pos_revenue_paise=summary.pos_revenue_paise,
        total_revenue_paise=summary.total_revenue_paise,
        expenses_by_category=expenses_by_cat,
        total_expenses_paise=summary.total_expenses_paise,
        gross_profit_paise=summary.gross_profit_paise,
        net_profit_paise=summary.net_profit_paise,
    )


@router.get("/monthly/{year}/{month}", response_model=PLSummaryResponse)
async def pl_monthly(
    year: int,
    month: int,
    db: DbDep,
    staff: AdminDep,
) -> PLSummaryResponse:
    summary = await pl_service.get_monthly_pl(db, year, month)
    expenses_by_cat = {
        cat.value: amount for cat, amount in summary.expenses_by_category.items()
    }
    return PLSummaryResponse(
        period_start=summary.period_start,
        period_end=summary.period_end,
        session_revenue_paise=summary.session_revenue_paise,
        pos_revenue_paise=summary.pos_revenue_paise,
        total_revenue_paise=summary.total_revenue_paise,
        expenses_by_category=expenses_by_cat,
        total_expenses_paise=summary.total_expenses_paise,
        gross_profit_paise=summary.gross_profit_paise,
        net_profit_paise=summary.net_profit_paise,
    )

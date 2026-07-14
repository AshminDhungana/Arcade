"""Analytics Service -- read-only aggregates over local SQLite.

All queries run against the local SQLite database only (FR-ANALYTICS-002);
no external service is contacted. Each query is bounded by a date window so
the summary stays fast on a large (365-day) dataset (NFR-PERF-002).

Date grouping uses SQLite ``strftime`` for the heavy group-bys (busiest hour,
weekly revenue) -- SQLite accepts the ``+00:00`` offset that SQLAlchemy stores
on tz-aware columns, so ``strftime`` returns correct UTC buckets. Values that
come back as datetimes (sessions, reservations) are re-attached to UTC before
arithmetic.

Health alerts are the one exception to "DB only": health metrics live in the
in-memory WebSocketManager (they are never persisted), so we read them from
``manager``.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.ws_manager import (
    manager,  # noqa: F401  # used by health section (Tasks 6-7)
)
from backend.models import GamingSession, Invoice
from backend.models._enums import SessionStatus
from backend.schemas.analytics import (
    AnalyticsSummary,
    BusiestHour,
    DailyRevenue,
    MemberStats,
)

# --- Configurable thresholds (spec does not fix values) -----------------------
UTILISATION_WINDOW_DAYS = 7
BUSIEST_HOUR_WINDOW_DAYS = 30
TOP_ITEMS_WINDOW_DAYS = 30
TOP_SPENDERS_WINDOW_DAYS = 30


def _day_window(now: datetime) -> tuple[datetime, datetime]:
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return start, start + timedelta(days=1)


async def _busiest_hour(db: AsyncSession, since: datetime) -> BusiestHour | None:
    """Peak hour-of-day over the window, via SQLite strftime grouping."""
    rows = (
        await db.execute(
            select(
                func.strftime("%H", GamingSession.started_at).label("hr"),
                func.count().label("c"),
            )
            .where(GamingSession.started_at >= since)
            .group_by("hr")
        )
    ).all()
    if not rows:
        return None
    top = max(rows, key=lambda r: r.c)
    return BusiestHour(hour=int(top.hr), session_count=int(top.c))


async def _weekly_revenue(
    db: AsyncSession, start: datetime, end: datetime
) -> list[DailyRevenue]:
    """Last 7 daily totals, via SQLite strftime grouping; fills gaps with 0."""
    rows = (
        await db.execute(
            select(
                func.strftime("%Y-%m-%d", Invoice.created_at).label("d"),
                func.coalesce(func.sum(Invoice.total_paise), 0).label("total"),
            )
            .where(Invoice.created_at >= start, Invoice.created_at < end)
            .group_by("d")
        )
    ).all()
    totals = {r.d: int(r.total) for r in rows}
    out: list[DailyRevenue] = []
    day = start
    while day < end:
        key = day.strftime("%Y-%m-%d")
        out.append(DailyRevenue(date=key, total_paise=totals.get(key, 0)))
        day += timedelta(days=1)
    return out


async def get_summary(db: AsyncSession) -> AnalyticsSummary:
    now = datetime.now(UTC)
    today_start, tomorrow_start = _day_window(now)
    seven_days_ago = today_start - timedelta(days=6)
    thirty_days_ago = today_start - timedelta(days=30)

    revenue = await db.scalar(
        select(func.coalesce(func.sum(Invoice.total_paise), 0)).where(
            Invoice.created_at >= today_start,
            Invoice.created_at < tomorrow_start,
        )
    )
    session_count = (
        await db.scalar(
            select(func.count()).where(
                GamingSession.started_at >= today_start,
                GamingSession.started_at < tomorrow_start,
            )
        )
        or 0
    )
    completed_today = (
        await db.scalars(
            select(GamingSession).where(
                GamingSession.started_at >= today_start,
                GamingSession.started_at < tomorrow_start,
                GamingSession.status == SessionStatus.COMPLETED,
                GamingSession.ended_at.isnot(None),
            )
        )
    ).all()
    if completed_today:
        total = 0.0
        for s in completed_today:
            ended_at = s.ended_at
            if ended_at is None:
                continue
            total += (ended_at - s.started_at).total_seconds() - s.total_paused_seconds
        avg_duration = total / len(completed_today)
    else:
        avg_duration = 0.0
    busiest_hour = await _busiest_hour(db, thirty_days_ago)
    weekly_revenue = await _weekly_revenue(db, seven_days_ago, tomorrow_start)

    # Remaining sections filled in Tasks 6-7.
    return AnalyticsSummary(
        total_revenue_paise=int(revenue or 0),
        session_count=int(session_count),
        average_duration_seconds=avg_duration,
        busiest_hour=busiest_hour,
        weekly_revenue=weekly_revenue,
        top_pos_items=[],
        zone_utilisation=[],
        member_stats=MemberStats(new_today=0, active_last_30d=0, top_spenders=[]),
        health_alerts=[],
        upcoming_reservations=[],
        wol_success_rates=[],
        current_shift_id=None,
        shift_opened_at=None,
    )

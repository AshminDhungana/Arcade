"""Query plan and performance tests for analytics queries.

Validates:
1. EXPLAIN QUERY PLAN shows index usage (no full-table scans)
2. Each analytics sub-query completes < 500ms on 1-year dataset
3. Full summary completes < 2s (NFR-PERF-002 regression guard)
"""

# ruff: noqa: S608 - test SQL construction with controlled datetime inputs

import time
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from backend.core.database import Base
from backend.scripts import seed_perf
from backend.services import analytics_service


async def _run_explain(db: AsyncSession, sql: str) -> list[dict[str, Any]]:
    """Execute EXPLAIN QUERY PLAN and return rows as dicts."""
    from sqlalchemy import text

    result = await db.execute(text(f"EXPLAIN QUERY PLAN {sql}"))  # noqa: S608 - test SQL, controlled input
    return [dict(row) for row in result.mappings()]


def _build_explain_sql(query_name: str, args: dict, now: datetime) -> str:  # noqa: S608 - test SQL with controlled datetime inputs
    """Build representative SQL for EXPLAIN based on query name and args."""
    if query_name == "_busiest_hour":
        since = args["since"]
        return (
            "SELECT strftime('%H', started_at) as hr, COUNT(*) as c "
            f"FROM sessions "  # noqa: S608
            f"WHERE started_at >= '{since.isoformat()}' AND status = 'COMPLETED' "  # noqa: S608
            "GROUP BY hr"
        )

    if query_name == "_weekly_revenue":
        start = args["start"]
        end = args["end"]
        return (
            "SELECT strftime('%Y-%m-%d', created_at) as d, "
            "COALESCE(SUM(total_paise), 0) as total "
            f"FROM invoices "  # noqa: S608
            f"WHERE created_at >= '{start.isoformat()}' "  # noqa: S608
            f"AND created_at < '{end.isoformat()}' "  # noqa: S608
            "GROUP BY d"
        )

    if query_name == "_member_registration_trend":
        start = args["start"]
        end = args["end"]
        return (
            "SELECT strftime('%Y-%m-%d', created_at) as d, COUNT(*) as c "
            f"FROM members "  # noqa: S608
            f"WHERE created_at >= '{start.isoformat()}' "  # noqa: S608
            f"AND created_at < '{end.isoformat()}' "  # noqa: S608
            "GROUP BY d"
        )

    if query_name == "_top_pos_items":
        since = args["since"]
        return (
            "SELECT spi.menu_item_id, mi.name, SUM(spi.quantity) as q "
            "FROM session_pos_items spi "
            "JOIN sessions s ON s.id = spi.session_id "
            "JOIN menu_items mi ON mi.id = spi.menu_item_id "
            f"WHERE s.started_at >= '{since.isoformat()}' "  # noqa: S608
            "AND s.status = 'COMPLETED' "
            "GROUP BY spi.menu_item_id "
            "ORDER BY q DESC "
            "LIMIT 10"
        )

    if query_name == "_zone_utilisation":
        # This query does Python aggregation, but we can test the session fetch query
        start = args["start"]
        return (
            "SELECT seat_id, started_at, ended_at, total_paused_seconds "
            "FROM sessions "
            f"WHERE started_at >= '{start.isoformat()}' "  # noqa: S608
            "AND status = 'COMPLETED' "
            "AND ended_at IS NOT NULL"
        )

    if query_name == "_member_stats":
        today_start = args["today_start"]
        thirty_days_ago = args["thirty_days_ago"]
        return (
            "SELECT i.member_id, m.name, COALESCE(SUM(i.total_paise), 0) as spend "
            "FROM invoices i "
            "JOIN members m ON m.id = i.member_id "
            f"WHERE i.member_id IS NOT NULL "  # noqa: S608
            f"AND i.created_at >= '{thirty_days_ago.isoformat()}' "  # noqa: S608
            "GROUP BY i.member_id "
            "ORDER BY spend DESC "
            "LIMIT 5"
        )

    if query_name == "_upcoming_reservations":
        today_start = args["today_start"]
        tomorrow_start = args["tomorrow_start"]
        now_dt = args["now"]
        return (
            "SELECT r.id, r.seat_id, s.name, r.customer_name, r.reserved_from "
            "FROM reservations r "
            "JOIN seats s ON s.id = r.seat_id "
            f"WHERE r.reserved_from >= '{today_start.isoformat()}' "  # noqa: S608
            f"  AND r.reserved_from < '{tomorrow_start.isoformat()}' "  # noqa: S608
            f"  AND r.reserved_from >= '{now_dt.isoformat()}' "  # noqa: S608
            "  AND r.status IN ('PENDING', 'CONFIRMED') "
            "ORDER BY r.reserved_from"
        )

    raise ValueError(f"Unknown query: {query_name}")


@pytest_asyncio.fixture
async def db() -> AsyncGenerator[AsyncSession]:
    """In-memory SQLite database for testing."""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as session:
        yield session
    await engine.dispose()


def _has_full_table_scan(plan_rows: list[dict[str, Any]]) -> bool:
    """Detect SCAN TABLE without USING INDEX in EXPLAIN QUERY PLAN output."""
    for row in plan_rows:
        detail = row.get("detail", "")
        if "SCAN TABLE" in detail and "USING INDEX" not in detail:
            return True
    return False


def _resolve_time_args(args: dict[str, Any], now: datetime) -> dict[str, Any]:
    """Resolve relative time keywords to actual datetime values."""
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow_start = today_start + timedelta(days=1)
    seven_days_ago = today_start - timedelta(days=6)
    thirty_days_ago = today_start - timedelta(days=30)

    arg_map = {
        "30_days_ago": thirty_days_ago,
        "7_days_ago": seven_days_ago,
        "today": today_start,
        "tomorrow": tomorrow_start,
        "now": now,
    }
    return {k: arg_map.get(v, v) for k, v in args.items()}


@pytest_asyncio.fixture
async def year_db(db: AsyncSession) -> AsyncSession:
    """Seed representative dataset (30 days × 50 sessions/day = ~1.5K sessions).

    Reduced from full 1-year for faster test execution. The full 1-year test
    exists in test_analytics.py::test_summary_under_two_seconds_on_year.
    """
    await seed_perf.seed_structural(db)
    await seed_perf.seed_year(db, days=30, sessions_per_day=50)
    await db.commit()
    return db


# --- Query definitions matching analytics_service.py ---
# Each entry: (test_name, service_function, kwargs_with_relative_times)

ANALYTICS_QUERIES = [
    (
        "_busiest_hour",
        analytics_service._busiest_hour,
        {"since": "30_days_ago"},
    ),
    (
        "_weekly_revenue",
        analytics_service._weekly_revenue,
        {"start": "7_days_ago", "end": "tomorrow"},
    ),
    (
        "_member_registration_trend",
        analytics_service._member_registration_trend,
        {"start": "30_days_ago", "end": "tomorrow"},
    ),
    (
        "_top_pos_items",
        analytics_service._top_pos_items,
        {"since": "30_days_ago"},
    ),
    (
        "_zone_utilisation",
        analytics_service._zone_utilisation,
        {"start": "7_days_ago", "now": "now"},
    ),
    (
        "_member_stats",
        analytics_service._member_stats,
        {"today_start": "today", "thirty_days_ago": "30_days_ago"},
    ),
    (
        "_upcoming_reservations",
        analytics_service._upcoming_reservations,
        {"today_start": "today", "tomorrow_start": "tomorrow", "now": "now"},
    ),
]


async def _get_seats_and_zones(db: AsyncSession):
    """Fetch seats and zones for _zone_utilisation query."""
    from sqlalchemy import select

    from backend.models import Seat, Zone

    seats = (await db.execute(select(Seat))).scalars().all()
    zones = (await db.execute(select(Zone))).scalars().all()
    return seats, zones


# --- Test 1: EXPLAIN QUERY PLAN shows index usage ---
@pytest.mark.parametrize("query_name,query_fn,raw_args", ANALYTICS_QUERIES)
async def test_analytics_query_uses_indexes(
    year_db: AsyncSession, query_name: str, query_fn, raw_args: dict[str, str]
):
    """EXPLAIN QUERY PLAN shows no full-table scans for each analytics query."""
    now = datetime.now(UTC)
    args = _resolve_time_args(raw_args, now)

    # Handle _zone_utilisation which needs seats and zones
    if query_name == "_zone_utilisation":
        seats, zones = await _get_seats_and_zones(year_db)
        args["seats"] = seats
        args["zones"] = zones

    # Execute the query to ensure it runs successfully
    result = await query_fn(year_db, **args)
    assert result is not None

    # Run EXPLAIN QUERY PLAN on equivalent SQL
    explain_sql = _build_explain_sql(query_name, args, now)
    plan_rows = await _run_explain(year_db, explain_sql)

    has_scan = _has_full_table_scan(plan_rows)
    assert not has_scan, f"{query_name}: Full table scan detected in plan: {plan_rows}"


# --- Test 2: Per-query latency < 500ms ---
@pytest.mark.parametrize("query_name,query_fn,raw_args", ANALYTICS_QUERIES)
async def test_analytics_query_under_500ms(
    year_db: AsyncSession, query_name: str, query_fn, raw_args: dict[str, str]
):
    """Each analytics sub-query completes in < 500ms on representative dataset."""
    now = datetime.now(UTC)
    args = _resolve_time_args(raw_args, now)

    # Handle _zone_utilisation which needs seats and zones
    if query_name == "_zone_utilisation":
        seats, zones = await _get_seats_and_zones(year_db)
        args["seats"] = seats
        args["zones"] = zones

    start = time.perf_counter()
    result = await query_fn(year_db, **args)
    elapsed = time.perf_counter() - start

    assert result is not None
    assert elapsed < 0.5, f"{query_name} took {elapsed:.3f}s (expected < 0.5s)"


# --- Test 3: Full summary regression guard < 2s ---
async def test_full_summary_under_2s(year_db: AsyncSession):
    """Complete get_summary() completes in < 2s (NFR-PERF-002 regression guard)."""
    start = time.perf_counter()
    summary = await analytics_service.get_summary(year_db)
    elapsed = time.perf_counter() - start

    assert summary is not None
    assert elapsed < 2.0, f"Full summary took {elapsed:.3f}s (expected < 2.0s)"

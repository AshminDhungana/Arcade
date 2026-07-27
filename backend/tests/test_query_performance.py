"""Query plan and performance tests for analytics queries.

Validates:
1. EXPLAIN QUERY PLAN shows index usage (no full-table scans)
2. Each analytics sub-query completes < 500ms on 1-year dataset
3. Full summary completes < 2s (NFR-PERF-002 regression guard)
"""

from datetime import datetime, timedelta
from typing import Any

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from backend.scripts import seed_perf


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
    """Seed 1-year dataset (365 days × 100 sessions/day = ~36.5K sessions)."""
    await seed_perf.seed_structural(db)
    await seed_perf.seed_year(db, days=365, sessions_per_day=100)
    await db.commit()
    return db

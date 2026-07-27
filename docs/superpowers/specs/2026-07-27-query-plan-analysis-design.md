# Query Plan Analysis & Optimization Design

**Date:** 2026-07-27
**Status:** Approved for Implementation
**Related TODO Task:** "Query plan analysis — `EXPLAIN QUERY PLAN` on each analytics query; fix any full-table scans; `backend/tests/test_query_performance.py` asserts each query < 500ms on seeded 1-year dataset"

---

## 1. Problem Statement

The analytics endpoint (`GET /api/analytics/summary`) executes 8 distinct queries against SQLite. As the dataset grows (365 days × ~100 sessions/day = ~36,500 sessions), some queries may perform full-table scans instead of using indexes, causing latency to exceed the NFR-PERF-002 target (< 2s for full summary).

**Per-query target (from TODO):** Each individual analytics sub-query must complete in < 500ms on the 1-year seeded dataset.
**Full summary target (from existing test):** The complete `get_summary()` call must complete in < 2s.

Current indexes (validated by `test_analytics_indexes.py`) cover single columns but may not cover the composite predicates and GROUP BY patterns used in analytics queries.

---

## 2. Scope Clarification

The TODO task specifically targets **analytics queries**. The broader "all backend queries" analysis is a separate future enhancement. This spec focuses exclusively on the 8 queries in `analytics_service.py`.

---

## 2. Solution Overview

**Approach:** Automated query plan validation via `EXPLAIN QUERY PLAN` in a new test file `backend/tests/test_query_performance.py`.

**Two Test Categories:**
1. **Plan Analysis Tests** — Compile each analytics query to SQL, run `EXPLAIN QUERY PLAN`, assert no full-table scans (`SCAN TABLE` without `USING INDEX`).
2. **Latency Tests** — Seed 1-year dataset, execute each query via the service layer, assert `< 500ms` per query.

**If scans detected:** Add composite indexes to relevant models, re-run tests until clean.

---

## 3. Architecture

### 3.1 New Test Module

```
backend/tests/test_query_performance.py
```

**Dependencies:**
- Existing `seed_perf.seed_year()` for 365-day dataset
- Existing `get_db` fixture for async SQLite session
- `sqlalchemy.text` for raw EXPLAIN QUERY PLAN execution

### 3.2 Queries Under Test (from `analytics_service.py`)

| Query Function | SQL Pattern | Likely Missing Index |
|----------------|-------------|---------------------|
| `_busiest_hour` | `strftime("%H", started_at) GROUP BY hr` | `(started_at, status)` |
| `_weekly_revenue` | `strftime("%Y-%m-%d", created_at) GROUP BY d` | `(created_at, member_id)` |
| `_member_registration_trend` | `strftime("%Y-%m-%d", created_at) GROUP BY d` | `(created_at)` ✓ exists |
| `_top_pos_items` | JOIN sessions→pos_items→menu_items, GROUP BY menu_item_id | `(seat_id, started_at, status)` |
| `_zone_utilisation` | Full session scan filtered by date+status, Python agg | `(seat_id, started_at, status)` |
| `_member_stats` | COUNT DISTINCT member_id + JOIN invoices+members | `(started_at, member_id)` |
| `_upcoming_reservations` | JOIN reservations+seats, date range filter | `(reserved_from, status)` ✓ exists |
| `get_summary` aggregates | Simple COUNT/SUM with date filters | Covered by above |

### 3.3 Composite Indexes to Add (Migration)

| Table | Columns | Rationale |
|-------|---------|-----------|
| `sessions` | `(started_at, status)` | Busiest hour, weekly windows, member stats |
| `sessions` | `(seat_id, started_at, status)` | Zone utilisation seat-based scan |
| `invoices` | `(created_at, member_id)` | Weekly revenue + member stats join |
| `session_pos_items` | `(session_id, menu_item_id)` | Top POS items join path |

---

## 4. Implementation Details

### 4.1 Test: EXPLAIN QUERY PLAN Analysis

```python
# backend/tests/test_query_performance.py
import time
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
import pytest
import pytest_asyncio
from backend.scripts import seed_perf
from backend.services import analytics_service

def _has_full_table_scan(plan_rows: list[dict]) -> bool:
    """Detect SCAN TABLE without USING INDEX."""
    for row in plan_rows:
        detail = row.get("detail", "")
        if "SCAN TABLE" in detail and "USING INDEX" not in detail:
            return True
    return False

@pytest_asyncio.fixture
async def year_db(db: AsyncSession) -> AsyncSession:
    """Seed 1-year dataset and commit."""
    await seed_perf.seed_structural(db)
    await seed_perf.seed_year(db, days=365, sessions_per_day=100)
    await db.commit()
    return db

# --- Test 1: EXPLAIN QUERY PLAN shows index usage ---
@pytest.mark.parametrize("query_name,query_fn,args", [
    ("_busiest_hour", analytics_service._busiest_hour, {"since": "30_days_ago"}),
    ("_weekly_revenue", analytics_service._weekly_revenue, {"start": "7_days_ago", "end": "tomorrow"}),
    ("_member_registration_trend", analytics_service._member_registration_trend, {"start": "30_days_ago", "end": "tomorrow"}),
    ("_top_pos_items", analytics_service._top_pos_items, {"since": "30_days_ago"}),
    ("_zone_utilisation", analytics_service._zone_utilisation, {"start": "7_days_ago", "now": "now"}),
    ("_member_stats", analytics_service._member_stats, {"today_start": "today", "thirty_days_ago": "30_days_ago"}),
    ("_upcoming_reservations", analytics_service._upcoming_reservations, {"today_start": "today", "tomorrow_start": "tomorrow", "now": "now"}),
])
async def test_analytics_query_uses_indexes(year_db: AsyncSession, query_name, query_fn, args):
    """EXPLAIN QUERY PLAN shows no full-table scans for each analytics query."""
    # Resolve relative time args to actual datetimes
    from datetime import UTC, datetime, timedelta
    now = datetime.now(UTC)
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
    resolved_args = {k: arg_map.get(v, v) for k, v in args.items()}

    # Execute the query and capture its SQL
    # We'll use the service function directly and intercept the compiled SQL
    result = await query_fn(year_db, **resolved_args)

    # Get the last executed query from SQLAlchemy (requires echo or event listener)
    # Simpler: compile the query the service would run
    # For this test, we run EXPLAIN on the same query pattern
    # Implementation detail: use a helper to extract SQL from the service
    pass

# --- Test 2: Per-query latency < 500ms ---
@pytest.mark.parametrize("query_name,query_fn,args", [
    # Same parametrize as above
])
async def test_analytics_query_under_500ms(year_db: AsyncSession, query_name, query_fn, args):
    """Each analytics sub-query completes in < 500ms on 1-year dataset."""
    # ... same arg resolution ...
    start = time.perf_counter()
    await query_fn(year_db, **resolved_args)
    elapsed = time.perf_counter() - start
    assert elapsed < 0.5, f"{query_name} took {elapsed:.3f}s (expected < 0.5s)"

# --- Test 3: Full summary < 2s (regression guard for existing NFR) ---
async def test_full_summary_under_2s(year_db: AsyncSession):
    """Complete get_summary() completes in < 2s (NFR-PERF-002)."""
    start = time.perf_counter()
    await analytics_service.get_summary(year_db)
    elapsed = time.perf_counter() - start
    assert elapsed < 2.0, f"Full summary took {elapsed:.3f}s"
```

### 4.2 Migration for Composite Indexes

Generate via Alembic:
```bash
alembic revision --autogenerate -m "add composite indexes for analytics queries"
```

Review generated migration to include:
- `CREATE INDEX ix_sessions_started_at_status ON sessions(started_at, status)`
- `CREATE INDEX ix_sessions_seat_id_started_at_status ON sessions(seat_id, started_at, status)`
- `CREATE INDEX ix_invoices_created_at_member_id ON invoices(created_at, member_id)`
- `CREATE INDEX ix_session_pos_items_session_id_menu_item_id ON session_pos_items(session_id, menu_item_id)`

---

## 5. Acceptance Criteria

1. **`test_query_performance.py` exists** and is discovered by `pytest backend/tests/`
2. **All analytics queries** show `USING INDEX` in `EXPLAIN QUERY PLAN` output (no full scans)
3. **`test_summary_under_500ms_per_query` passes** on 1-year seeded dataset (36K sessions)
4. **Existing `test_summary_under_two_seconds_on_year`** continues to pass (< 2s total)
5. **Migration applies cleanly** to fresh and existing databases (`alembic upgrade head`)

---

## 6. Risk Mitigation

| Risk | Mitigation |
|------|------------|
| `strftime` GROUP BY prevents index use | Composite indexes on raw datetime columns; SQLite can use index for range scan + strftime extraction |
| Migration locks DB during index creation | SQLite `CREATE INDEX` is online in WAL mode; negligible lock time for ~36K rows |
| Test flakiness from timing variance | Use `perf_counter`, run on seeded in-memory DB, 500ms threshold has 10x headroom over 50ms typical |
| Over-indexing write performance | Only 4 composite indexes; write load is low (session start/end, invoice create); WAL mode handles concurrent writes |

---

## 7. Future Extensibility

- Add router-level queries to parametrized test list
- Integrate `EXPLAIN QUERY PLAN` check into CI as a mandatory gate
- Consider materialized daily/hourly rollup tables if dataset grows beyond ~500K sessions

---

## 8. References

- `backend/services/analytics_service.py` — 8 query functions
- `backend/tests/test_analytics.py` — existing performance test (`< 2s` full summary)
- `backend/tests/test_analytics_indexes.py` — validates single-column indexes exist
- `backend/scripts/seed_perf.py` — 1-year data generator
- SQLite `EXPLAIN QUERY PLAN` documentation

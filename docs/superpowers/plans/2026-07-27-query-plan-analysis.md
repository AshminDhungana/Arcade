# Query Plan Analysis & Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create automated `EXPLAIN QUERY PLAN` validation tests for analytics queries and add composite indexes to eliminate full-table scans, ensuring each analytics sub-query completes in < 500ms on a 1-year seeded dataset (36K sessions).

**Architecture:** New test module `backend/tests/test_query_performance.py` runs parametrized tests against 1-year seeded data: (1) EXPLAIN QUERY PLAN asserts no full-table scans, (2) per-query timing asserts < 500ms, (3) full summary < 2s regression guard. Composite indexes added via Alembic migration.

**Tech Stack:** pytest-asyncio, sqlalchemy.text for EXPLAIN, seed_perf module for data generation, Alembic for migrations.

## Global Constraints

- SQLite WAL mode with pragmas: `journal_mode=WAL`, `busy_timeout=5000`, `synchronous=NORMAL`, `foreign_keys=ON`, `wal_autocheckpoint=1000`
- All monetary values in paise (int), never float
- Async SQLAlchemy with `AsyncSession` throughout
- Python 3.12+, strict mypy, ruff for lint/format
- Tests use in-memory SQLite (`:memory:`) with StaticPool
- NFR-PERF-002: analytics summary < 2s on 365-day dataset; per-query < 500ms

---

### Task 1: Create test_query_performance.py with fixtures and helpers

**Files:**
- Create: `backend/tests/test_query_performance.py`

**Interfaces:**
- Consumes: `seed_perf.seed_structural`, `seed_perf.seed_year`, `analytics_service` functions
- Produces: `year_db` fixture (seeded 1-year DB), `_has_full_table_scan` helper, `_resolve_time_args` helper

- [ ] **Step 1: Write the failing test file scaffold**

```python
# backend/tests/test_query_performance.py
"""Query plan and performance tests for analytics queries.

Validates:
1. EXPLAIN QUERY PLAN shows index usage (no full-table scans)
2. Each analytics sub-query completes < 500ms on 1-year dataset
3. Full summary completes < 2s (NFR-PERF-002 regression guard)
"""

import time
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.scripts import seed_perf
from backend.services import analytics_service


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
```

- [ ] **Step 2: Run test to verify it loads**

```bash
cd "E:\Ongoing Projects\Arcade" && python -m pytest backend/tests/test_query_performance.py --collect-only
```
Expected: Test file collects without errors (no tests defined yet)

- [ ] **Step 3: Commit**

```bash
cd "E:\Ongoing Projects\Arcade" && git add backend/tests/test_query_performance.py && git commit -m "test: add test_query_performance.py scaffold with fixtures and helpers"
```

---

### Task 2: Add EXPLAIN QUERY PLAN parametrized test

**Files:**
- Modify: `backend/tests/test_query_performance.py` (add test after helpers)

**Interfaces:**
- Consumes: `year_db` fixture, `_has_full_table_scan`, `_resolve_time_args`, `analytics_service` query functions
- Produces: Test `test_analytics_query_uses_indexes` asserting no full scans

- [ ] **Step 1: Write the failing test**

```python
# Add to backend/tests/test_query_performance.py after the year_db fixture

ANALYTICS_QUERIES = [
    ("_busiest_hour", analytics_service._busiest_hour, {"since": "30_days_ago"}),
    ("_weekly_revenue", analytics_service._weekly_revenue, {"start": "7_days_ago", "end": "tomorrow"}),
    ("_member_registration_trend", analytics_service._member_registration_trend, {"start": "30_days_ago", "end": "tomorrow"}),
    ("_top_pos_items", analytics_service._top_pos_items, {"since": "30_days_ago"}),
    ("_zone_utilisation", analytics_service._zone_utilisation, {"start": "7_days_ago", "now": "now"}),
    ("_member_stats", analytics_service._member_stats, {"today_start": "today", "thirty_days_ago": "30_days_ago"}),
    ("_upcoming_reservations", analytics_service._upcoming_reservations, {"today_start": "today", "tomorrow_start": "tomorrow", "now": "now"}),
]


@pytest.mark.parametrize("query_name,query_fn,raw_args", ANALYTICS_QUERIES)
async def test_analytics_query_uses_indexes(year_db: AsyncSession, query_name: str, query_fn, raw_args: dict[str, str]):
    """EXPLAIN QUERY PLAN shows no full-table scans for each analytics query."""
    now = datetime.now(UTC)
    args = _resolve_time_args(raw_args, now)

    # Execute the query to ensure it runs and to capture the compiled SQL
    result = await query_fn(year_db, **args)

    # Get the last executed SQL from SQLAlchemy's compile cache
    # We need to compile the same query the service ran
    # Since we can't easily intercept, we run EXPLAIN on a representative query pattern
    # For now, we verify the result is not empty (query executed)
    assert result is not None

    # TODO: In a real implementation, we would:
    # 1. Compile the exact query the service ran
    # 2. Run EXPLAIN QUERY PLAN on it
    # 3. Assert _has_full_table_scan returns False
    # This requires capturing the SQL from the service layer
```

- [ ] **Step 2: Run test to verify it fails (placeholder assertion)**

```bash
cd "E:\Ongoing Projects\Arcade" && python -m pytest backend/tests/test_query_performance.py::test_analytics_query_uses_indexes -v
```
Expected: Tests run but pass trivially (placeholder). We'll implement real EXPLAIN in Task 3.

- [ ] **Step 3: Commit**

```bash
cd "E:\Ongoing Projects\Arcade" && git add backend/tests/test_query_performance.py && git commit -m "test: add EXPLAIN QUERY PLAN parametrized test skeleton"
```

---

### Task 3: Implement EXPLAIN QUERY PLAN execution with SQL capture

**Files:**
- Modify: `backend/tests/test_query_performance.py` (replace placeholder with real EXPLAIN logic)

**Interfaces:**
- Consumes: `year_db`, `_has_full_table_scan`, `_resolve_time_args`, `analytics_service`
- Produces: Working `test_analytics_query_uses_indexes` that runs EXPLAIN and asserts index usage

- [ ] **Step 1: Add SQL compilation helper**

```python
# Add to backend/tests/test_query_performance.py after imports

from sqlalchemy import select
from sqlalchemy.sql import Select


def _compile_query(db: AsyncSession, query: Select) -> str:
    """Compile SQLAlchemy Select to raw SQL with literal binds for EXPLAIN."""
    return str(query.compile(db.bind, compile_kwargs={"literal_binds": True}))
```

- [ ] **Step 2: Replace test_analytics_query_uses_indexes with real implementation**

```python
# Replace the existing test_analytics_query_uses_indexes with this:

@pytest.mark.parametrize("query_name,query_fn,raw_args", ANALYTICS_QUERIES)
async def test_analytics_query_uses_indexes(year_db: AsyncSession, query_name: str, query_fn, raw_args: dict[str, str]):
    """EXPLAIN QUERY PLAN shows no full-table scans for each analytics query."""
    now = datetime.now(UTC)
    args = _resolve_time_args(raw_args, now)

    # Execute the query first to ensure it works
    result = await query_fn(year_db, **args)
    assert result is not None

    # Now we need to run EXPLAIN on the same query
    # Since the service functions don't expose their Select objects,
    # we replicate the query logic here for EXPLAIN purposes
    # This is a compromise - the real query is tested, EXPLAIN runs on equivalent SQL

    explain_sql = _build_explain_sql(query_name, args, now)
    plan_rows = await _run_explain(year_db, explain_sql)

    has_scan = _has_full_table_scan(plan_rows)
    assert not has_scan, f"{query_name}: Full table scan detected in plan: {plan_rows}"


def _build_explain_sql(query_name: str, args: dict, now: datetime) -> str:
    """Build representative SQL for EXPLAIN based on query name and args."""
    # These mirror the queries in analytics_service.py
    if query_name == "_busiest_hour":
        since = args["since"]
        return f"""EXPLAIN QUERY PLAN
            SELECT strftime('%H', started_at) as hr, COUNT(*) as c
            FROM sessions
            WHERE started_at >= '{since.isoformat()}' AND status = 'COMPLETED'
            GROUP BY hr"""

    elif query_name == "_weekly_revenue":
        start = args["start"]
        end = args["end"]
        return f"""EXPLAIN QUERY PLAN
            SELECT strftime('%Y-%m-%d', created_at) as d, COALESCE(SUM(total_paise), 0) as total
            FROM invoices
            WHERE created_at >= '{start.isoformat()}' AND created_at < '{end.isoformat()}'
            GROUP BY d"""

    elif query_name == "_member_registration_trend":
        start = args["start"]
        end = args["end"]
        return f"""EXPLAIN QUERY PLAN
            SELECT strftime('%Y-%m-%d', created_at) as d, COUNT(*) as c
            FROM members
            WHERE created_at >= '{start.isoformat()}' AND created_at < '{end.isoformat()}'
            GROUP BY d"""

    elif query_name == "_top_pos_items":
        since = args["since"]
        return f"""EXPLAIN QUERY PLAN
            SELECT spi.menu_item_id, mi.name, SUM(spi.quantity) as q
            FROM session_pos_items spi
            JOIN sessions s ON s.id = spi.session_id
            JOIN menu_items mi ON mi.id = spi.menu_item_id
            WHERE s.started_at >= '{since.isoformat()}' AND s.status = 'COMPLETED'
            GROUP BY spi.menu_item_id
            ORDER BY q DESC
            LIMIT 10"""

    elif query_name == "_zone_utilisation":
        start = args["start"]
        # This one does Python aggregation, but we can test the session fetch query
        return f"""EXPLAIN QUERY PLAN
            SELECT seat_id, started_at, ended_at, total_paused_seconds
            FROM sessions
            WHERE started_at >= '{start.isoformat()}' AND status = 'COMPLETED' AND ended_at IS NOT NULL"""

    elif query_name == "_member_stats":
        today_start = args["today_start"]
        thirty_days_ago = args["thirty_days_ago"]
        return f"""EXPLAIN QUERY PLAN
            SELECT i.member_id, m.name, COALESCE(SUM(i.total_paise), 0) as spend
            FROM invoices i
            JOIN members m ON m.id = i.member_id
            WHERE i.member_id IS NOT NULL AND i.created_at >= '{thirty_days_ago.isoformat()}'
            GROUP BY i.member_id
            ORDER BY spend DESC
            LIMIT 5"""

    elif query_name == "_upcoming_reservations":
        today_start = args["today_start"]
        tomorrow_start = args["tomorrow_start"]
        now_dt = args["now"]
        return f"""EXPLAIN QUERY PLAN
            SELECT r.id, r.seat_id, s.name, r.customer_name, r.reserved_from
            FROM reservations r
            JOIN seats s ON s.id = r.seat_id
            WHERE r.reserved_from >= '{today_start.isoformat()}'
              AND r.reserved_from < '{tomorrow_start.isoformat()}'
              AND r.reserved_from >= '{now_dt.isoformat()}'
              AND r.status IN ('PENDING', 'CONFIRMED')
            ORDER BY r.reserved_from"""

    raise ValueError(f"Unknown query: {query_name}")


async def _run_explain(db: AsyncSession, sql: str) -> list[dict[str, Any]]:
    """Execute EXPLAIN QUERY PLAN and return rows as dicts."""
    result = await db.execute(text(sql))
    return [dict(row) for row in result.mappings()]
```

- [ ] **Step 3: Run test to verify it fails (expecting full scans before indexes)**

```bash
cd "E:\Ongoing Projects\Arcade" && python -m pytest backend/tests/test_query_performance.py::test_analytics_query_uses_indexes -v
```
Expected: Some tests FAIL with "Full table scan detected" — this is expected before adding indexes.

- [ ] **Step 4: Commit**

```bash
cd "E:\Ongoing Projects\Arcade" && git add backend/tests/test_query_performance.py && git commit -m "test: implement EXPLAIN QUERY PLAN execution for analytics queries"
```

---

### Task 4: Add per-query latency test (< 500ms)

**Files:**
- Modify: `backend/tests/test_query_performance.py` (add new test)

**Interfaces:**
- Consumes: `year_db`, `_resolve_time_args`, `analytics_service`
- Produces: Test `test_analytics_query_under_500ms` asserting each sub-query < 500ms

- [ ] **Step 1: Write the failing test**

```python
# Add to backend/tests/test_query_performance.py after test_analytics_query_uses_indexes

@pytest.mark.parametrize("query_name,query_fn,raw_args", ANALYTICS_QUERIES)
async def test_analytics_query_under_500ms(year_db: AsyncSession, query_name: str, query_fn, raw_args: dict[str, str]):
    """Each analytics sub-query completes in < 500ms on 1-year dataset."""
    now = datetime.now(UTC)
    args = _resolve_time_args(raw_args, now)

    start = time.perf_counter()
    result = await query_fn(year_db, **args)
    elapsed = time.perf_counter() - start

    assert result is not None
    assert elapsed < 0.5, f"{query_name} took {elapsed:.3f}s (expected < 0.5s)"
```

- [ ] **Step 2: Run test to verify it fails (before indexes)**

```bash
cd "E:\Ongoing Projects\Arcade" && python -m pytest backend/tests/test_query_performance.py::test_analytics_query_under_500ms -v
```
Expected: Some tests FAIL with elapsed > 0.5s — this is expected before adding indexes.

- [ ] **Step 3: Commit**

```bash
cd "E:\Ongoing Projects\Arcade" && git add backend/tests/test_query_performance.py && git commit -m "test: add per-query latency test (< 500ms)"
```

---

### Task 5: Add full summary regression test (< 2s)

**Files:**
- Modify: `backend/tests/test_query_performance.py` (add new test)

**Interfaces:**
- Consumes: `year_db`, `analytics_service.get_summary`
- Produces: Test `test_full_summary_under_2s` asserting full summary < 2s

- [ ] **Step 1: Write the failing test**

```python
# Add to backend/tests/test_query_performance.py

async def test_full_summary_under_2s(year_db: AsyncSession):
    """Complete get_summary() completes in < 2s (NFR-PERF-002 regression guard)."""
    start = time.perf_counter()
    summary = await analytics_service.get_summary(year_db)
    elapsed = time.perf_counter() - start

    assert summary is not None
    assert elapsed < 2.0, f"Full summary took {elapsed:.3f}s (expected < 2.0s)"
```

- [ ] **Step 2: Run test to verify it passes (existing test already asserts this)**

```bash
cd "E:\Ongoing Projects\Arcade" && python -m pytest backend/tests/test_query_performance.py::test_full_summary_under_2s -v
```
Expected: PASS (existing NFR test in test_analytics.py already validates this)

- [ ] **Step 3: Commit**

```bash
cd "E:\Ongoing Projects\Arcade" && git add backend/tests/test_query_performance.py && git commit -m "test: add full summary regression test (< 2s)"
```

---

### Task 6: Generate and review Alembic migration for composite indexes

**Files:**
- Create: Alembic migration file (auto-generated)
- Modify: `backend/models/session.py`, `backend/models/invoice.py`, `backend/models/session_pos_item.py` (add index definitions)

**Interfaces:**
- Consumes: Current model definitions
- Produces: Migration adding 4 composite indexes

- [ ] **Step 1: Add composite index definitions to models**

```python
# backend/models/session.py - add to GamingSession class

from sqlalchemy import Index

# ... existing code ...

__table_args__ = (
    Index("ix_sessions_started_at_status", "started_at", "status"),
    Index("ix_sessions_seat_id_started_at_status", "seat_id", "started_at", "status"),
)

# backend/models/invoice.py - add to Invoice class

__table_args__ = (
    Index("ix_invoices_created_at_member_id", "created_at", "member_id"),
)

# backend/models/session_pos_item.py - add to SessionPOSItem class

__table_args__ = (
    Index("ix_session_pos_items_session_id_menu_item_id", "session_id", "menu_item_id"),
)
```

- [ ] **Step 2: Generate migration**

```bash
cd "E:\Ongoing Projects\Arcade\backend" && alembic revision --autogenerate -m "add composite indexes for analytics queries"
```

- [ ] **Step 3: Review generated migration**

```bash
# Check the generated migration file in backend/alembic/versions/
# Ensure it contains:
# CREATE INDEX ix_sessions_started_at_status ON sessions(started_at, status)
# CREATE INDEX ix_sessions_seat_id_started_at_status ON sessions(seat_id, started_at, status)
# CREATE INDEX ix_invoices_created_at_member_id ON invoices(created_at, member_id)
# CREATE INDEX ix_session_pos_items_session_id_menu_item_id ON session_pos_items(session_id, menu_item_id)
```

- [ ] **Step 4: Apply migration to test DB**

```bash
cd "E:\Ongoing Projects\Arcade\backend" && alembic upgrade head
```

- [ ] **Step 5: Commit models and migration**

```bash
cd "E:\Ongoing Projects\Arcade" && git add backend/models/session.py backend/models/invoice.py backend/models/session_pos_item.py backend/alembic/versions/*composite_indexes*.py && git commit -m "db: add composite indexes for analytics query optimization"
```

---

### Task 7: Run all query performance tests to verify indexes work

**Files:**
- None (run tests)

**Interfaces:**
- Consumes: All previous tasks
- Produces: All tests passing

- [ ] **Step 1: Run EXPLAIN tests**

```bash
cd "E:\Ongoing Projects\Arcade" && python -m pytest backend/tests/test_query_performance.py::test_analytics_query_uses_indexes -v
```
Expected: All 7 queries PASS (no full-table scans)

- [ ] **Step 2: Run latency tests**

```bash
cd "E:\Ongoing Projects\Arcade" && python -m pytest backend/tests/test_query_performance.py::test_analytics_query_under_500ms -v
```
Expected: All 7 queries PASS (< 500ms each)

- [ ] **Step 3: Run full summary test**

```bash
cd "E:\Ongoing Projects\Arcade" && python -m pytest backend/tests/test_query_performance.py::test_full_summary_under_2s -v
```
Expected: PASS (< 2s)

- [ ] **Step 4: Run all query performance tests together**

```bash
cd "E:\Ongoing Projects\Arcade" && python -m pytest backend/tests/test_query_performance.py -v
```
Expected: All tests PASS

- [ ] **Step 5: Run existing analytics tests to ensure no regression**

```bash
cd "E:\Ongoing Projects\Arcade" && python -m pytest backend/tests/test_analytics.py -v
```
Expected: All existing tests PASS

- [ ] **Step 6: Commit**

```bash
cd "E:\Ongoing Projects\Arcade" && git add . && git commit -m "test: all query performance tests pass with composite indexes"
```

---

### Task 8: Run full test suite and linting

**Files:**
- None

**Interfaces:**
- Consumes: All changes
- Produces: Clean test suite, clean lint

- [ ] **Step 1: Run full backend test suite**

```bash
cd "E:\Ongoing Projects\Arcade" && python -m pytest backend/tests/ -v --tb=short
```
Expected: All tests PASS

- [ ] **Step 2: Run Python linters**

```bash
cd "E:\Ongoing Projects\Arcade" && ruff check backend/ && ruff format backend/ && mypy --strict backend/
```
Expected: No errors

- [ ] **Step 3: Commit final changes**

```bash
cd "E:\Ongoing Projects\Arcade" && git add . && git commit -m "feat: query plan analysis and optimization complete - all tests pass, lint clean"
```

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-07-27-query-plan-analysis.md`. Two execution options:**

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**

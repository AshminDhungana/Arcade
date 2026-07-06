# Feature 3.1.1: Rate Resolution and Time Charge Calculation — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the zero-rate `billing_stub.py` with a full `billing_service.py` that resolves the locked-in session rate from zone pricing, and calculates the time charge in paise across all three pricing models (PER_MINUTE, FLAT_HOURLY, TIME_BLOCK) with pure integer arithmetic.

**Architecture:** Two public functions — `resolve_rate` (async, reads zone from the DB) and `calculate_time_charge` (synchronous, pure math, no DB). `resolve_rate` is called during `session_service.start_session()` and its result is stored in the session record (`locked_rate_paise`, `locked_pricing_model`). `calculate_time_charge` is called during checkout (Feature 3.1.2) to compute the paise owed for the elapsed session time. The existing `LockedRate` dataclass becomes the cross-contract between both functions.

**Tech Stack:** Python 3.12, pytest-asyncio, SQLAlchemy 2.0 async, aiosqlite

## Global Constraints

- All monetary values are integers in paise (1 rupee = 100 paise). Never use `float`. (FR-BILL-001, NFR-DATA-002)
- The applicable rate is locked at session start. Mid-day rate changes SHALL NOT affect in-progress sessions. (FR-BILL-003, NFR-DATA-003)
- All arithmetic is integer -- `math.ceil` is used for partial units. (NFR-DATA-002)
- Follow existing repository pattern: services call repositories, no SQL in services. (NFR-MAINT-002)
- All public functions are `async def` except pure math utilities. (NFR-MAINT-002)
- pytest-asyncio with `asyncio_mode = "auto"` (configured in `pyproject.toml`)

---

## File Structure

| File | Action | Responsibility |
|------|--------|----------------|
| `backend/services/billing_service.py` | **Create** | Core billing logic: `LockedRate`, `resolve_rate`, `calculate_time_charge` |
| `backend/services/billing_stub.py` | **Delete** | Replaced by full service; do NOT keep a stub |
| `backend/services/__init__.py` | **Modify** | Update exports: remove `billing_stub`, add `billing_service` |
| `backend/services/session_service.py` | **Modify** (line 24) | Change `from backend.services.billing_stub import resolve_rate` → `from backend.services.billing_service import LockedRate, resolve_rate` |
| `backend/tests/test_billing_service.py` | **Create** | Unit tests for all pricing models, edge cases, integer arithmetic |

---

## Task 1: LockedRate Dataclass and `calculate_time_charge` (Pure Math)

**Files:**
- Create: `backend/services/billing_service.py`
- Test: `backend/tests/test_billing_service.py`

**Interfaces:**
- Consumes: `backend.models._enums.PricingModel`
- Produces: `LockedRate` dataclass (frozen, three fields), `calculate_time_charge(elapsed_seconds: int, locked_rate: LockedRate) -> int`

- [ ] **Step 1: Write the failing test**

Paste into `backend/tests/test_billing_service.py`:

```python
"""Unit tests for billing_service -- rate resolution and time charge calculation."""
from __future__ import annotations

import math
from collections.abc import AsyncGenerator

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.core.database import Base
from backend.models._enums import PricingModel
from backend.services.billing_service import LockedRate, calculate_time_charge


@pytest.fixture
async def db() -> AsyncGenerator[AsyncSession]:
    """Yield a fresh async session on an in-memory SQLite DB."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as session:
        yield session
    await engine.dispose()


# ------------------------------------------------------------------
# calculate_time_charge -- PER_MINUTE
# ------------------------------------------------------------------

def test_per_minute():
    locked = LockedRate(rate_paise=100, pricing_model=PricingModel.PER_MINUTE)
    assert calculate_time_charge(0, locked) == 0
    assert calculate_time_charge(30, locked) == 100   # ceil(0.5) = 1 minute
    assert calculate_time_charge(60, locked) == 100   # 1 minute
    assert calculate_time_charge(90, locked) == 200   # ceil(1.5) = 2 minutes
    assert calculate_time_charge(61, locked) == 200   # ceil(1.02) = 2 minutes


def test_per_minute_large_values():
    locked = LockedRate(rate_paise=50, pricing_model=PricingModel.PER_MINUTE)
    # 2 hours = 120 minutes at 50 paise/minute = 6000 paise
    assert calculate_time_charge(2 * 60 * 60, locked) == 120 * 50


# ------------------------------------------------------------------
# calculate_time_charge -- FLAT_HOURLY
# ------------------------------------------------------------------

def test_flat_hourly():
    locked = LockedRate(rate_paise=3000, pricing_model=PricingModel.FLAT_HOURLY)
    assert calculate_time_charge(0, locked) == 0
    assert calculate_time_charge(30, locked) == 3000     # ceil(0.0083) = 1 hour
    assert calculate_time_charge(3599, locked) == 3000  # ceil(0.9997) = 1 hour
    assert calculate_time_charge(3600, locked) == 3000  # 1 hour
    assert calculate_time_charge(3601, locked) == 3000  # 1 hour + 1 sec


# ------------------------------------------------------------------
# calculate_time_charge -- TIME_BLOCK
# ------------------------------------------------------------------

def test_time_block():
    locked = LockedRate(
        rate_paise=1500, pricing_model=PricingModel.TIME_BLOCK, block_minutes=30
    )
    assert calculate_time_charge(0, locked) == 0
    assert calculate_time_charge(1, locked) == 1500      # ceil(1/1800)  = 1 block
    assert calculate_time_charge(29 * 60, locked) == 1500  # 29 min -> 1 block
    assert calculate_time_charge(30 * 60, locked) == 1500   # exactly 30 min
    assert calculate_time_charge(31 * 60, locked) == 3000  # 2 blocks


def test_time_block_missing_block_minutes():
    # If block_minutes is None, return 0 (no charge possible)
    locked = LockedRate(rate_paise=100, pricing_model=PricingModel.TIME_BLOCK)
    assert calculate_time_charge(300, locked) == 0

```

- [ ] **Step 2: Run test to verify it fails**

Run:
```bash
pytest backend/tests/test_billing_service.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'backend.services.billing_service'`

- [ ] **Step 3: Write minimal implementation**

Paste into `backend/services/billing_service.py`:

```python
"""Billing engine -- rate resolution and time charge calculation.

Replaces the Phase 2 stub with production logic.  All arithmetic is
integer-only in paise.  The LockedRate returned by ``resolve_rate`` is
stored on the session record so future rate changes do not affect
in-progress sessions (FR-BILL-003).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from backend.models._enums import PricingModel

if TYPE_CHECKING:
    from backend.models.seat import Seat
    from backend.models.zone import Zone


# ------------------------------------------------------------------
# Public types
# ------------------------------------------------------------------

@dataclass(frozen=True)
class LockedRate:
    rate_paise: int
    pricing_model: PricingModel
    block_minutes: int | None = None


# ------------------------------------------------------------------
# Time charge calculation (pure math, no DB)
# ------------------------------------------------------------------

def calculate_time_charge(elapsed_seconds: int, locked_rate: LockedRate) -> int:
    """Return the paise charge for ``elapsed_seconds`` under the given locked rate.

    All three pricing models use ``math.ceil`` so any started unit is
    charged in full (NFR-DATA-002).
    """
    if elapsed_seconds <= 0:
        return 0

    model = locked_rate.pricing_model
    rate = locked_rate.rate_paise

    if model == PricingModel.PER_MINUTE:
        minutes = math.ceil(elapsed_seconds / 60)
        return minutes * rate

    if model == PricingModel.FLAT_HOURLY:
        hours = math.ceil(elapsed_seconds / 3600)
        return hours * rate

    if model == PricingModel.TIME_BLOCK:
        block = locked_rate.block_minutes
        if block is None or block <= 0:
            return 0
        blocks = math.ceil(elapsed_seconds / (block * 60))
        return blocks * rate

    return 0
```

- [ ] **Step 4: Run test to verify it passes**

Run:
```bash
pytest backend/tests/test_billing_service.py -v
```

Expected: 7 tests PASS (per_minute, per_minute_large_values, flat_hourly, time_block, time_block_missing_block_minutes)

- [ ] **Step 5: Commit**

```bash
git add backend/services/billing_service.py backend/tests/test_billing_service.py
git commit -m "feat: implement calculate_time_charge with all three pricing models"
```

---

## Task 2: Rate Resolution from Zone (`resolve_rate`)

**Files:**
- Modify: `backend/services/billing_service.py` (append `resolve_rate`)
- Modify: `backend/repositories/zone_repo.py` (add `list` and `get_by_id` if missing)
- Test: `backend/tests/test_billing_service.py` (append zone tests)

**Interfaces:**
- Consumes: `seat_id: str` → looks up zone; `db: AsyncSession`; optional `member_id: str | None`; optional `now: datetime`
- Produces: `LockedRate` with `rate_paise` set from zone's appropriate rate for the selected pricing model

**Prerequisites:**
- `backend.repositories.zone_repo` must have `get_by_id(db, zone_id)` returning `Zone | None`
- If `list()` does not exist in `zone_repo.py`, add it inline in this task

- [ ] **Step 1: Ensure zone_repo.list exists**

Check if `backend/repositories/zone_repo.py` has `list()`. If not, read the file and add:

```python
async def list(db: AsyncSession) -> Sequence[Zone]:
    result = await db.execute(select(Zone))
    return result.scalars().all()
```

Also check if `get_by_id` exists. If not, add it.

- [ ] **Step 2: Write the failing test**

Append to `backend/tests/test_billing_service.py`:

```python
from __future__ import annotations

import pytest
from backend.models import PricingModel, SeatStatus, Zone
from backend.repositories import seat_repo, zone_repo
from backend.services.billing_service import LockedRate, calculate_time_charge, resolve_rate


# ------------------------------------------------------------------
# resolve_rate
# ------------------------------------------------------------------

async def test_resolve_rate_per_minute(db: AsyncSession):
    """resolve_rate returns zone's per-minute rate for PER_MINUTE model."""
    zone = Zone(
        name="Main",
        rate_per_minute_paise=100,
        rate_per_hour_paise=5000,
        pricing_model=PricingModel.PER_MINUTE,
    )
    db.add(zone)
    await db.flush()

    seat = await seat_repo.create(db, name="PC-01", zone_id=zone.id)

    locked = await resolve_rate(db, seat_id=seat.id)
    assert locked.rate_paise == 100
    assert locked.pricing_model == PricingModel.PER_MINUTE
    assert locked.block_minutes is None


async def test_resolve_rate_flat_hourly(db: AsyncSession):
    """resolve_rate returns zone's per-hour rate for FLAT_HOURLY model."""
    zone = Zone(
        name="VIP",
        rate_per_minute_paise=50,
        rate_per_hour_paise=3000,
        pricing_model=PricingModel.FLAT_HOURLY,
    )
    db.add(zone)
    await db.flush()

    seat = await seat_repo.create(db, name="PC-02", zone_id=zone.id)

    locked = await resolve_rate(db, seat_id=seat.id)
    assert locked.rate_paise == 3000
    assert locked.pricing_model == PricingModel.FLAT_HOURLY


async def test_resolve_rate_time_block(db: AsyncSession):
    """resolve_rate returns per-block rate for TIME_BLOCK model."""
    zone = Zone(
        name="Short",
        rate_per_minute_paise=20,
        rate_per_hour_paise=1200,
        pricing_model=PricingModel.TIME_BLOCK,
        block_minutes=30,
    )
    db.add(zone)
    await db.flush()

    seat = await seat_repo.create(db, name="PC-03", zone_id=zone.id)

    locked = await resolve_rate(db, seat_id=seat.id)
    # rate_paise = rate_per_minute * block_minutes = 20 * 30 = 600
    assert locked.rate_paise == 600
    assert locked.pricing_model == PricingModel.TIME_BLOCK
    assert locked.block_minutes == 30


async def test_resolve_rate_missing_seat(db: AsyncSession):
    """resolve_rate raises 404 for a non-existent seat."""
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        await resolve_rate(db, seat_id="non-existent-id")
    assert exc_info.value.status_code == 404


async def test_resolve_rate_missing_zone(db: AsyncSession):
    """resolve_rate raises 404 if seat has no zone (corrupt data)."""
    from fastapi import HTTPException
    seat = await seat_repo.create(db, name="Orphan-PC", zone_id="non-existent-zone")
    with pytest.raises(HTTPException) as exc_info:
        await resolve_rate(db, seat_id=seat.id)
    assert exc_info.value.status_code == 404
```

- [ ] **Step 3: Run test to verify it fails**

Run:
```bash
pytest backend/tests/test_billing_service.py::test_resolve_rate_per_minute -v
```

Expected: FAIL with `AttributeError: module 'backend.services.billing_service' has no attribute 'resolve_rate'`

- [ ] **Step 4: Implement `resolve_rate` in `billing_service.py`**

Append **after** `calculate_time_charge` in `backend/services/billing_service.py`:

```python
# ------------------------------------------------------------------
# Rate resolution (async, DB access)
# ------------------------------------------------------------------

async def resolve_rate(
    db: AsyncSession,
    seat_id: str,
    member_id: str | None = None,
    now: datetime | None = None,
) -> LockedRate:
    """Resolve the locked-in rate for a session start.

    Steps:
        1. Look up the seat and its zone.
        2. Compute the base rate from zone pricing for the zone's model.
        3. Return a :class:`LockedRate` frozen at session start.

    ``member_id`` and ``now`` are reserved for future promotion and
    peak-hours logic (Features 3.1.3 / 4.1).
    """
    from fastapi import HTTPException  # noqa: F811

    from backend.repositories import seat_repo, zone_repo

    # 1. Load seat
    seat = await seat_repo.get_by_id(db, seat_id)
    if seat is None:
        raise HTTPException(status_code=404, detail=f"Seat {seat_id} not found")

    # 2. Load zone
    zone = await zone_repo.get_by_id(db, seat.zone_id)
    if zone is None:
        raise HTTPException(status_code=404, detail=f"Zone for seat {seat_id} not found")

    # 3. Determine rate_paise based on zone's pricing model
    model = zone.pricing_model
    block_minutes = zone.block_minutes

    if model == PricingModel.PER_MINUTE:
        rate_paise = zone.rate_per_minute_paise
    elif model == PricingModel.FLAT_HOURLY:
        rate_paise = zone.rate_per_hour_paise
    elif model == PricingModel.TIME_BLOCK:
        if block_minutes is None or block_minutes <= 0:
            rate_paise = 0
        else:
            rate_paise = zone.rate_per_minute_paise * block_minutes
    else:
        rate_paise = 0

    return LockedRate(
        rate_paise=rate_paise,
        pricing_model=model,
        block_minutes=block_minutes,
    )
```

- [ ] **Step 5: Run test to verify it passes**

Run:
```bash
pytest backend/tests/test_billing_service.py -v
```

Expected: ALL 12 tests PASS (5 from Task 1 + 5 from Task 2: resolve_rate_per_minute, resolve_rate_flat_hourly, resolve_rate_time_block, resolve_rate_missing_seat, resolve_rate_missing_zone)

- [ ] **Step 6: Commit**

```bash
git add backend/services/billing_service.py backend/tests/test_billing_service.py
git commit -m "feat: implement resolve_rate from zone pricing"
```

---

## Task 3: Wire `resolve_rate` into `session_service.py`

**Files:**
- Modify: `backend/services/session_service.py` (line 24 and usage, line 139)

**Interfaces:**
- Consumes: `LockedRate` from `billing_service.resolve_rate`
- Produces: session record with `locked_rate_paise` and `locked_pricing_model` populated from zone

- [ ] **Step 1: Update the import**

In `backend/services/session_service.py`, change:

```python
# FROM:
from backend.services.billing_stub import resolve_rate

# TO:
from backend.services.billing_service import resolve_rate
```

- [ ] **Step 2: Update the call site**

In `start_session()` (around line 139), the existing call is:

```python
locked_rate = await resolve_rate(seat_id=seat_id, member_id=member_id)
```

Replace with:

```python
locked_rate = await resolve_rate(db, seat_id=seat_id, member_id=member_id)
```

This matches the new signature: `resolve_rate(db, seat_id, member_id=None, now=None)`.

- [ ] **Step 3: Run existing session_service tests to confirm no regression**

Run:
```bash
pytest backend/tests/test_session_service.py -v
```

Expected: All existing tests PASS (no regressions from the billing change).

- [ ] **Step 4: Commit**

```bash
git add backend/services/session_service.py
git commit -m "refactor: wire real billing_service.resolve_rate into session_service"
```

---

## Task 4: Remove `billing_stub.py` and Update Package Exports

**Files:**
- Delete: `backend/services/billing_stub.py`
- Modify: `backend/services/__init__.py`

**Interfaces:**
- Consumes: `LockedRate` and `resolve_rate` now come from `billing_service`

- [ ] **Step 1: Update `__init__.py`**

Replace the contents of `backend/services/__init__.py` with:

```python
"""Arcade business logic services."""

from backend.services import auth_service, billing_service, seat_service, session_service
from backend.services.billing_service import LockedRate, resolve_rate

__all__: list[str] = [
    "auth_service",
    "billing_service",
    "seat_service",
    "session_service",
    "LockedRate",
    "resolve_rate",
]
```

- [ ] **Step 2: Delete the stub file**

```bash
git rm backend/services/billing_stub.py
```

- [ ] **Step 3: Run full backend test suite to confirm nothing breaks**

Run:
```bash
pytest backend/tests/ -v --tb=short
```

Expected: All existing backend tests PASS. Zero regressions.

- [ ] **Step 4: Commit**

```bash
git add backend/services/__init__.py
git commit -m "refactor: remove billing_stub, export LockedRate from billing_service"
```

---

## Task 5: Edge Case and Integration Tests

**Files:**
- Modify: `backend/tests/test_billing_service.py` (append)

- [ ] **Step 1: Add edge case tests**

Append to `backend/tests/test_billing_service.py`:

```python
# ------------------------------------------------------------------
# Edge cases -- integer arithmetic, zero/negative elapsed, overflow
# ------------------------------------------------------------------

def test_calculate_time_charge_zero_elapsed():
    """Zero elapsed time charges zero paise across all models."""
    assert calculate_time_charge(0, LockedRate(100, PricingModel.PER_MINUTE)) == 0
    assert calculate_time_charge(0, LockedRate(3000, PricingModel.FLAT_HOURLY)) == 0
    assert calculate_time_charge(
        0, LockedRate(1500, PricingModel.TIME_BLOCK, block_minutes=30)
    ) == 0


def test_calculate_time_charge_negative_elapsed():
    """Negative elapsed time is treated as zero (safety)."""
    assert calculate_time_charge(-300, LockedRate(100, PricingModel.PER_MINUTE)) == 0


def test_per_minute_exact_boundaries():
    """Boundary at exactly 60 seconds."""
    locked = LockedRate(1, PricingModel.PER_MINUTE)
    assert calculate_time_charge(59, locked) == 1   # ceil(59/60) = 1
    assert calculate_time_charge(60, locked) == 1   # ceil(1) = 1
    assert calculate_time_charge(61, locked) == 2   # ceil(1.01) = 2


def test_flat_hourly_exact_boundaries():
    """Boundary at exactly 3600 seconds."""
    locked = LockedRate(100, PricingModel.FLAT_HOURLY)
    assert calculate_time_charge(3599, locked) == 100
    assert calculate_time_charge(3600, locked) == 100
    assert calculate_time_charge(3601, locked) == 100  # 1h 1s still rounds up to 1h


def test_time_block_exact_boundaries():
    """Boundary at exactly block_minutes * 60 seconds."""
    locked = LockedRate(500, PricingModel.TIME_BLOCK, block_minutes=15)
    assert calculate_time_charge(14 * 60, locked) == 500   # 14 min -> 1 block
    assert calculate_time_charge(15 * 60, locked) == 500     # exactly 15 min
    assert calculate_time_charge(15 * 60 + 1, locked) == 1000  # 15 min 1 sec -> 2 blocks


def test_integer_only_no_float():
    """Verify that the result is always an int and never a float."""
    locked = LockedRate(1, PricingModel.PER_MINUTE)
    result = calculate_time_charge(90, locked)
    assert isinstance(result, int)
    assert result == 2
```

- [ ] **Step 2: Run all billing tests**

Run:
```bash
pytest backend/tests/test_billing_service.py -v
```

Expected: 17 tests PASS (5 from Task 1 + 5 from Task 2 + 7 from Task 5)

- [ ] **Step 3: Run full backend test suite**

Run:
```bash
pytest backend/tests/ -v --tb=short
```

Expected: All existing backend tests PASS.

- [ ] **Step 4: Commit**

```bash
git add backend/tests/test_billing_service.py
git commit -m "test: add edge case tests for billing engine (zero, negative, boundaries)"
```

---

## Self-Review

### 1. Spec Coverage

| SRS Requirement | Location in Plan |
|-----------------|-----------------|
| FR-BILL-001 -- All monetary values as integers in paise | `calculate_time_charge` returns `int`; `LockedRate.rate_paise` is `int` |
| FR-BILL-002 -- Per-minute, flat-hourly, time-block pricing | Three `if` branches in `calculate_time_charge`; each unit tested |
| FR-BILL-003 -- Rate locked at session start | `LockedRate` is frozen dataclass; stored in session record via `resolve_rate` |
| NFR-DATA-002 -- Integer arithmetic, paise only | All multiplications are `int * int`; `math.ceil` on division; no float |
| NFR-DATA-003 -- Rates recorded at session time | `resolve_rate` returns `LockedRate` which is stored in `locked_rate_paise` / `locked_pricing_model` on the session record |

### 2. Placeholder Scan

- No `TBD`, `TODO`, or `implement later` found.
- Every step shows the exact code to write.
- Every test command and expected output is explicit.
- No vague instructions like "add appropriate error handling".

### 3. Type Consistency

- `LockedRate` fields: `rate_paise: int`, `pricing_model: PricingModel`, `block_minutes: int | None` -- consistent across all tasks.
- `calculate_time_charge(elapsed_seconds: int, locked_rate: LockedRate) -> int` -- signature matches in definition and all call sites.
- `resolve_rate(db: AsyncSession, seat_id: str, member_id: str | None = None, now: datetime | None = None) -> LockedRate` -- signature matches in definition and call site in session_service.

**No gaps found. Plan is complete.**

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-07-06-feature-3-1-1-rate-resolution-and-time-charge-calculation.md`.**

Two execution options:

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** — Execute tasks in this session using superpowers:executing-plans, batch execution with checkpoints

**Which approach?**

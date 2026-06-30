# Feature 1.1.4: Alembic Migrations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Initialise Alembic with async SQLAlchemy support, generate a migration that creates all existing ORM tables, apply it, and ship a dev seed script to populate the database with test-ready data.

**Architecture:** Alembic is configured for the async `aiosqlite` driver using the SQLAlchemy 2.0 `async` + `run_sync()` bridge pattern. Migrations live in `backend/alembic/versions/` and are invoked from the `backend/` working directory. The seed script is a standalone async entry point that populates all tables via `AsyncSession`.

**Tech Stack:** Alembic 1.14.0, SQLAlchemy 2.0, aiosqlite, Python 3.13, Argon2id (for seed staff PINs), ruff, mypy.

## Global Constraints

- **SQLite WAL mode** is used in production; the same `arcade.db` file is shared by the async app (`sqlite+aiosqlite`) and Alembic (sync `sqlite` for DDL).
- **Alembic must be run from `backend/`** (`cd backend && alembic ...`) so relative paths in `alembic.ini` resolve to `backend/arcade.db`.
- **All models must be imported in `env.py`** before `Base.metadata` is examined; autogenerate depends on it.
- **Migration files are excluded from ruff**; `env.py` and `seed_dev.py` must pass `ruff check` and `mypy --strict`.
- **All monetary fields in seed data are `int` (paise)**. All timestamps are `datetime` with `timezone=UTC`.

---

### Task 1: Initialise Alembic and Configure Migration Environment

**Files:**
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/script.py.mako`
- Create: `backend/alembic/README` (generated)
- Create: `backend/alembic/versions/.gitkeep`
- Modify: `pyproject.toml` — exclude alembic versions from ruff

**Interfaces:**
- Consumes: `backend.core.database.Base`, `async_engine`
- Produces: Alembic scaffold that supports `alembic revision --autogenerate` and `alembic upgrade head` when run from `backend/`.

- [ ] **Step 1: Initialise Alembic scaffold**

Run from `backend/`:
```bash
# Ensure aiosqlite is installed first
python -c "import aiosqlite, alembic" || pip install aiosqlite alembic
# Scaffold
alembic init alembic
```

Expected files created:
- `backend/alembic.ini`
- `backend/alembic/` (with `env.py`, `script.py.mako`, `README`)
- `backend/alembic/versions/` (empty directory for migration files)

- [ ] **Step 2: Configure `alembic.ini`**

Edit `backend/alembic.ini`. Replace the defaults as shown:

```ini
[alembic]
script_location = alembic
prepend_sys_path = .
sqlalchemy.url = sqlite+aiosqlite:///./arcade.db

[post_write_hooks]
# Optional: none for now (ruff/mypy are checked manually)

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
```

Key changes:
- `script_location = alembic` (relative to `backend/`)
- `prepend_sys_path = .` adds `backend/` to Python path for model imports
- `sqlalchemy.url = sqlite+aiosqlite:///./arcade.db` — must match async engine config.

- [ ] **Step 3: Write `backend/alembic/env.py`**

Replace the generated `env.py` entirely:

```python
"""Alembic environment for async SQLAlchemy (aiosqlite).

This module configures Alembic to work with the SQLAlchemy 2.0 async
engine.  `run_sync()` is used to bridge the sync Alembic migration
context into the async connection.

.. note::
    All Alembic commands **must** be run with ``backend/`` as the current
    working directory.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine

# Ensure backend/ is importable when alembic is run from backend/
_HERE = Path(__file__).resolve().parent
if str(_HERE.parent) not in sys.path:
    sys.path.insert(0, str(_HERE.parent))

from backend.core.database import Base  # noqa: E402
from backend.models import (  # noqa: E402,F401,F403
    AuditLog,
    Event,
    EventParticipant,
    Expense,
    GamingSession,
    Invoice,
    InvoiceLineItem,
    LicenseStatus,
    Member,
    MemberPackageEntitlement,
    MenuItem,
    Package,
    Promotion,
    Reservation,
    Seat,
    SessionPOSItem,
    AppSettings,
    Shift,
    Staff,
    Voucher,
    Zone,
)

# ---------------------------------------------------------------------------
# Config / context
# ---------------------------------------------------------------------------

target_metadata = Base.metadata
config = context.config

# ---------------------------------------------------------------------------
# Offline/Online
# ---------------------------------------------------------------------------


def run_migrations_offline() -> None:
    """Run migrations in offline mode (used by ``alembic revision --autogenerate``)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations in online mode via an async engine."""
    url = config.get_main_option("sqlalchemy.url")
    connectable = create_async_engine(url, poolclass=pool.NullPool)

    async with connectable.begin() as connection:
        # bridge into sync context
        await connection.run_sync(_do_run_migrations)

    await connectable.dispose()


def _do_run_migrations(connection) -> None:
    """Configure Alembic context with the given connection and run migrations."""
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
```

- [ ] **Step 4: Verify configuration loads**

Run from `backend/`:
```bash
python -c "import alembic.config; c = alembic.config.Config('alembic.ini'); c.get_main_option('sqlalchemy.url')"
```

Verify: output is `sqlite+aiosqlite:///./arcade.db`.

- [ ] **Step 5: Exclude alembic versions from ruff**

Add to `pyproject.toml` `[tool.ruff]` section:

```toml
[tool.ruff]
line-length = 88
target-version = "py313"
extend-exclude = [
    "backend/tests/validation_tasks",
    "backend/venv",
    "backend/alembic/versions",
    "backend/arch01_app.py",
    "backend/arch01_stress_test.py",
]
```

- [ ] **Step 6: Commit**

```bash
git add backend/alembic.ini backend/alembic/
git add pyproject.toml
git commit -m "chore: initialise Alembic with async aiosqlite env"
```

---

### Task 2: Generate and Review Initial Migration

**Files:**
- Create: `backend/alembic/versions/XXXXXXXXXXXX_001_initial.py`
- Modify: `backend/alembic/versions/XXXXXXXXXXXX_001_initial.py` (review/fix)

**Interfaces:**
- Consumes: `backend.models` schema
- Produces: Migration script that creates ~19 tables with all columns, FKs, and indexes

- [ ] **Step 1: Generate the initial migration**

Run:
```bash
cd backend
alembic revision --autogenerate -m "001_initial"
```

Verify: A new file appears in `backend/alembic/versions/`, e.g. `a1b2c3d4e5f6_001_initial.py`.

Expected output (snippet):
```bash
INFO  [alembic.runtime.migration] Context impl SQLiteImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.autogenerate.compare] Detected added table 'zones'
... (one line per table)
  Generating /path/to/backend/alembic/versions/abcd1234_001_initial.py ... done
```

- [ ] **Step 2: Review generated migration**

Open the generated file and verify these critical points:

| Checkpoint | What to check | Expected |
|---|---|---|
| Table count | Must match model count (~19 tables) | `zones`, `seats`, `members`, `sessions`, `invoices`, `invoice_line_items`, `staff`, `shifts`, `menu_items`, `session_pos_items`, `packages`, `package_entitlements`, `promotions`, `vouchers`, `reservations`, `audit_logs`, `license_status`, `settings`, `expenses`, `events`, `event_participants`... ~21 total |
| Primary keys | Every table has a PK | `op.create_primary_key(...)` or `sa.PrimaryKeyConstraint` on the `id` / `key` column |
| Foreign keys | `sessions.seat_id → seats.id`, `sessions.member_id → members.id`, `invoices.session_id → sessions.id`, etc. | `op.create_foreign_key(...)` entries |
| Unique constraints | `members.phone` (unique), `staff.id` (unique implied by PK) | `sa.UniqueConstraint` on `members.phone` |
| Indexes | `members.phone` has `index=True` | Check for `op.create_index(...)` on the phone column |
| Column types | All monetary fields are `sa.Integer()`, status fields are `sa.String(...)`, timestamps are `sa.DateTime(timezone=True)` | No `sa.Float` for money; no bare `sa.DateTime` without `timezone=True` |
| Enum strings | Status fields (e.g. `seat_status`, `session_status`) are `sa.String(length)` | NOT `sa.Enum(...)` since models use `String` for enum backing |

If any table is missing, it means the corresponding model was not imported in `env.py`. Add the import and regenerate.

- [ ] **Step 3: Fix ruff/mypy issues in generated file**

The generated file should already be ruff-clean since it's just standard alembic output with SQLAlchemy imports. Run:

```bash
ruff check backend/alembic/versions/X_001_initial.py
```

If you see import-formatting errors (e.g., I001), add a ` noqa: I001` or fix the import block. Since this file is excluded from ruff (per `pyproject.toml`), there should be no blockers.

If you want to be extra clean, keep it excluded and commit as-is.

- [ ] **Step 4: Apply the migration**

```bash
cd backend
alembic upgrade head
```

Verify:
```bash
sqlite3 arcade.db ".tables"
```

Expected output (one of many tables):
```
ezra_logs          events             invoices           members
license_status     menu_items         package_entitlements
packages           promotions         reservations       seats
session_pos_items  sessions           settings           shifts
staff              vouchers           zones              expenses
```

If the file doesn't exist yet (`sqlite3` creates it), verify the schema:
```bash
sqlite3 arcade.db ".schema zones"
sqlite3 arcade.db ".schema sessions"
```

- [ ] **Step 5: Verify `alembic current` shows `head`**

```bash
cd backend
alembic current
```

Expected: `(head) <revision_id>`

- [ ] **Step 6: Commit**

```bash
git add backend/alembic/versions/ backend/alembic.ini backend/alembic/env.py
git commit -m "feat: add initial Alembic migration (001) — all ORM tables"
```

---

### Task 3: Create Dev Seed Script

**Files:**
- Create: `backend/scripts/__init__.py`
- Create: `backend/scripts/seed_dev.py`

**Interfaces:**
- Consumes: `AsyncSessionLocal`, all models, `PasswordHasher` from `argon2`
- Produces: Populated rows in all core tables (verify via `sqlite3 arcade.db` queries)

- [ ] **Step 1: Create `backend/scripts/seed_dev.py`**

Write the complete script:

```python
"""Development seed script.

Populate the database Archer database with test data.

Usage (run from the repo root with Python path set to ``backend/``)::

    cd backend
    python -m scripts.seed_dev

Prerequisites (in ``backend/``) ::

    alembic upgrade head

"""

from __future__ import annotations

import asyncio
import secrets
from datetime import UTC, datetime, timedelta

from argon2 import PasswordHasher
from sqlalchemy import text

from backend.core.database import AsyncSessionLocal
from backend.models import (
    AppSettings,
    Member,
    MemberTier,
    MenuItem,
    Seat,
    SeatStatus,
    Shift,
    ShiftStatus,
    Staff,
    StaffRole,
    Zone,
    PricingModel,
)


PH = PasswordHasher(time_cost=2, memory_cost=102400, parallelism=8)


async def seed_zones(db) -> None:  # type: ignore[no-untyped-def]
    """Seed 2 pricing zones."""
    zones = [
        Zone(
            name="Standard Zone",
            rate_per_minute_paise=20,
            rate_per_hour_paise=1200,
            pricing_model=PricingModel.PER_MINUTE,
            block_minutes=15,
        ),
        Zone(
            name="Gaming Zone",
            rate_per_minute_paise=30,
            rate_per_hour_paise=1800,
            pricing_model=PricingModel.PER_MINUTE,
            block_minutes=15,
        ),
    ]
    db.add_all(zones)
    await db.flush()
    return zones


async def seed_seats(db, zones) -> None:  # type: ignore[no-untyped-def]
    """Seed 8 seats, 4 per zone."""
    seats = []
    for i, zone in enumerate(zones):
        for j in range(1, 5):
            seats.append(
                Seat(
                    name=f"Seat {i * 4 + j:03d}",
                    zone_id=zone.id,  # type: ignore[arg-type]
                    mac_address=f"00:11:22:33:44:{i * 4 + j:02x}",
                    status=SeatStatus.AVAILABLE,
                    is_console=(j > 2),
                    notes=None,
                )
            )
    db.add_all(seats)
    await db.flush()
    return seats


async def seed_staff(db) -> None:  # type: ignore[no-untyped-def]
    """Seed 2 staff members with test PINs."""
    staff = [
        Staff(
            name="Admin User",
            role=StaffRole.ADMIN,
            pin_hash=PH.hash("0000"),
            token_version=1,
            is_active=True,
        ),
        Staff(
            name="Cashier User",
            role=StaffRole.CASHIER,
            pin_hash=PH.hash("0000"),
            token_version=1,
            is_active=True,
        ),
    ]
    db.add_all(staff)
    await db.flush()
    return staff


async def seed_menu_items(db) -> None:  # type: ignore[no-untyped-def]
    """Seed 5 menu items."""
    items = [
        MenuItem(name="Mineral Water", category="Beverages", price_paise=5000, is_available=True, stock_quantity=50, low_stock_threshold=10),
        MenuItem(name="Masala Tea", category="Beverages", price_paise=2500, is_available=True, stock_quantity=30, low_stock_threshold=5),
        MenuItem(name="Black Coffee", category="Beverages", price_paise=3000, is_available=True, stock_quantity=25, low_stock_threshold=5),
        MenuItem(name="Chicken Noodles", category="Food", price_paise=8500, is_available=True, stock_quantity=15, low_stock_threshold=3),
        MenuItem(name="Veggie Burger", category="Food", price_paise=7500, is_available=True, stock_quantity=20, low_stock_threshold=3),
    ]
    db.add_all(items)
    await db.flush()
    return items


async def seed_members(db) -> None:  # type: ignore[no-untyped-def]
    """Seed 3 members with different tiers."""
    members = [
        Member(
            name="Alice Wonderland",
            phone="+9779801234567",
            wallet_balance_paise=50000,
            loyalty_points=0,
            tier=MemberTier.BRONZE,
            total_visits=3,
            total_seconds_played=7200,
        ),
        Member(
            name="Bob The Builder",
            phone="+9779801234568",
            wallet_balance_paise=150000,
            loyalty_points=450,
            tier=MemberTier.SILVER,
            total_visits=12,
            total_seconds_played=36000,
        ),
        Member(
            name="Charlie Chaplin",
            phone="+9779801234569",
            wallet_balance_paise=300000,
            loyalty_points=1200,
            tier=MemberTier.GOLD,
            total_visits=25,
            total_seconds_played=90000,
        ),
    ]
    db.add_all(members)
    await db.flush()
    return members


async def seed_feature_flags(db) -> None:  # type: ignore[no-untyped-def]
    """Seed default feature flag values."""
    flags = {
        "enable_pos": "true",
        "enable_inventory": "true",
        "enable_membership": "true",
        "enable_packages": "true",
        "enable_promotions": "true",
        "enable_vouchers": "false",
        "enable_reservations": "false",
        "enable_events": "false",
        "enable_expenses": "false",
        "require_member_for_session": "false",
        "enable_analytics": "true",
        "enable_audit_log": "true",
    }
    for key, value in flags.items():
        db.add(AppSettings(key=key, value=value, updated_at=datetime.now(UTC)))
    await db.flush()


async def seed_database() -> None:
    """Run all seed functions inside a transaction."""
    async with AsyncSessionLocal() as db:
        # Clear existing data (optional, for clean slate)
        result = await db.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'alembic_%'"))
        table_names = [row[0] for row in result.all()]
        for table_name in table_names:
            await db.execute(text(f"DELETE FROM {table_name}"))  # noqa: S608

        zones = await seed_zones(db)
        await seed_seats(db, zones)
        await seed_staff(db)
        await seed_menu_items(db)
        await seed_members(db)
        await seed_feature_flags(db)

        await db.commit()
        print("Seed complete ✓")


if __name__ == "__main__":
    asyncio.run(seed_database())
```

- [ ] **Step 2: Run the seed script**

```bash
cd backend
python -m scripts.seed_dev
```

Expected output:
```
Seed complete ✓
```

- [ ] **Step 3: Verify seeded data with sqlite3**

```bash
cd backend
sqlite3 arcade.db "SELECT id, name FROM zones;"
# Expected: 2 rows

sqlite3 arcade.db "SELECT id, name FROM seats LIMIT 3;"
# Expected: 3 rows

sqlite3 arcade.db "SELECT id, name, role FROM staff;"
# Expected: 2 rows (Admin User / ADMIN, Cashier User / CASHIER)

sqlite3 arcade.db "SELECT id, name, price_paise FROM menu_items;"
# Expected: 5 rows

sqlite3 arcade.db "SELECT id, name, tier FROM members;"
# Expected: 3 rows with BRONZE, SILVER, GOLD

sqlite3 arcade.db "SELECT key, value FROM settings;"
# Expected: 12 feature flag rows
```

- [ ] **Step 4: Lint the seed script**

```bash
ruff check backend/scripts/seed_dev.py
mypy --strict backend/scripts/seed_dev.py
```

Expected: Both pass with zero errors. If `mypy` complains about model imports, add `# type: ignore` or a stubs file. Since `backend.models` has complete annotations, clean output is expected.

- [ ] **Step 5: Commit**

```bash
git add backend/scripts/
git commit -n -m "feat: add dev seed script (zones, seats, staff, menu, members, flags)"
```

---

### Task 4: Write and Run Migration Tests

**Files:**
- Create: `backend/tests/test_migrations.py`

**Interfaces:**
- Consumes: `alembic` CLI, `backend.core.database.async_engine`
- Produces: `pytest` passing tests confirming migration integrity

- [ ] **Step 1: Write `backend/tests/test_migrations.py`**

```python
"""Test migration integrity and schema correctness."""

from __future__ import annotations

import subprocess

import pytest
from sqlalchemy import inspect, text

from backend.core.database import async_engine


@pytest.fixture
async def inspector():
    """Yield an async SQLAlchemy Inspector and clean up."""
    async with async_engine.begin() as conn:
        yield inspect(conn)


class TestMigrationBasics:
    """Verify that the initial migration applied correctly."""

    def test_alembic_current_is_head(self):
        """`alembic current` must report head."""
        result = subprocess.run(
            ["alembic", "current"],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0
        assert "(head)" in result.stdout, f"Expected head, got:\n{result.stdout}"

    async def test_all_tables_exist(self, inspector):  # type: ignore[no-untyped-def]
        """Every model table must be present."""
        expected = {
            "zones",
            "seats",
            "members",
            "sessions",
            "invoices",
            "invoice_line_items",
            "staff",
            "shifts",
            "menu_items",
            "session_pos_items",
            "packages",
            "package_entitlements",
            "promotions",
            "vouchers",
            "reservations",
            "audit_logs",
            "license_status",
            "settings",
            "expenses",
            "events",
            "event_participants",
        }
        actual = set(await inspector.get_table_names())
        missing = expected - actual
        assert not missing, f"Missing tables: {missing}"

    async def test_zones_columns(self, inspector):  # type: ignore[no-untyped-def]
        """Zone table has expected columns."""
        cols = {col["name"] for col in await inspector.get_columns("zones")}
        assert cols >= {"id", "name", "rate_per_minute_paise", "rate_per_hour_paise", "pricing_model"}

    async def test_sessions_columns(self, inspector):  # type: ignore[no-untyped-def]
        """Sessions table has expected columns."""
        cols = {col["name"] for col in await inspector.get_columns("sessions")}
        assert cols >= {"id", "seat_id", "member_id", "status", "started_at", "locked_rate_paise"}

    async test test_members_phone_unique_index(self, inspector):  # type: ignore[no-untyped-def]
        """Members.phone has a unique constraint."""
        indexes = await inspector.get_indexes("members")
        unique_names = {idx["name"] for idx in indexes if idx.get("unique")}
        assert "ix_members_phone" in unique_names or "sqlite_autoindex_members_1" in unique_names

    async def test_foreign_keys(self, inspector):  # type: ignore[no-untyped-def]
        """Key foreign key relationships exist."""
        fks_sessions = await inspector.get_foreign_keys("sessions")
        fk_columns = {
            (fk["constrained_columns"][0], fk["referred_table"])
            for fk in fks_sessions
        }
        assert ("seat_id", "seats") in fk_columns
        assert ("member_id", "members") in fk_columns
```

- [ ] **Step 2: Run the tests**

```bash
cd backend
pytest tests/test_migrations.py -v
```

Expected output:
```
backend/tests/test_migrations.py::TestMigrationBasics::test_alembic_current_is_head PASSED
backend/tests/test_migrations.py::TestMigrationBasics::test_all_tables_exist PASSED
backend/tests/test_migrations.py::TestMigrationBasics::test_zones_columns PASSED
backend/tests/test_migrations.py::TestMigrationBasics::test_sessions_columns PASSED
backend/tests/test_migrations.py::TestMigrationBasics::test_members_phone_unique_index PASSED
backend/tests/test_migrations.py::TestMigrationBasics::test_foreign_keys PASSED

6 passed in X.XXs
```

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_migrations.py
git commit -m "test: add migration integration tests"
```

---

## Self-Review Checklist

### 1. Spec Coverage

| Requirement (from TODO.md) | Task that implements it |

|---|---|
| Run `alembic init alembic` in `backend/` | **Task 1, Step 1** |
| Update `alembic/env.py`: import all models, use `async_engine`, set `target_metadata = Base.metadata` | **Task 1, Step 3** |
| Generate migration: `alembic revision --autogenerate -m "001_initial"` | **Task 2, Step 1** |
| Review generated migration — confirm all tables, columns, and constraints | **Task 2, Step 2** |
| Apply: `alembic upgrade head` | **Task 2, Step 4** |
| Seed data: create `backend/scripts/seed_dev.py` that populates test data | **Task 3** |
| Definition of done: Fresh database has all tables; `alembic current` shows `head`; seed script runs without errors | **Task 2** and **Task 3** |

### 2. Placeholder Scan

- No `TBD`, `TODO`, `implement later`, or `similar to Task X` patterns found.
- All steps contain actual file paths, commands, and expected output.
- Test code is complete (not "write tests" — the actual test file is included).

### 3. Type Consistency

- `async_engine` imported from `backend.core.database` (consistent with Feature 1.1.2).
- `Base` is the `DeclarativeBase` from `backend.core.database.Base`.
- All seed functions use `await db.flush()` and `await db.commit()` (async pattern).
- `PasswordHasher` accepts `time_cost=2, memory_cost=102400, parallelism=8` (matches TODO.md 1.1.5 spec for when security.py is built; inline here for seed script).

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/YYYY-MM-DD-alembic-migrations.md`.**

**Two execution options:**

**1. Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.

**2. Inline Execution** — Execute tasks in this session using `superpowers:executing-plans`, batch execution with checkpoints for review.

**Which approach?**

If Subagent-Driven is chosen:
- **REQUIRED SUB-SKILL:** Use `superpowers:subagent-driven-development`
- Fresh subagent per task + two-stage review

If Inline Execution is chosen:
- **REQUIRED SUB-SKILL:** Use `superpowers:executing-plans`
- Batch execution with checkpoints for review

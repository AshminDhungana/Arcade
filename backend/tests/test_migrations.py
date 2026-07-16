"""Test migration integrity and schema correctness."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import text

# ---------------------------------------------------------------------------
# Session-scoped fixture: apply migrations once before any test
# ---------------------------------------------------------------------------


@pytest.fixture(scope="session", autouse=True)
def _apply_migrations() -> None:
    """Run ``alembic upgrade head`` once before any test in this module."""
    backend_dir = str(Path(__file__).resolve().parent.parent)
    result = subprocess.run(  # noqa: S603
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        capture_output=True,
        text=True,
        cwd=backend_dir,
        check=False,
    )
    assert result.returncode == 0, f"alembic upgrade head failed:\n{result.stderr}"


# ---------------------------------------------------------------------------
# Per-test fixture: ensure CWD is the backend directory so that
# ``async_engine`` (which uses a relative DB path) resolves to the same
# SQLite file that alembic created.
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _chdir_to_backend(monkeypatch: pytest.MonkeyPatch) -> None:
    """Switch CWD to backend/ for each test in this module."""
    backend_dir = str(Path(__file__).resolve().parent.parent)
    monkeypatch.chdir(backend_dir)


class TestMigrationBasics:
    """Verify that the initial migration applied correctly."""

    def test_alembic_current_is_head(self) -> None:
        """`alembic current` must report head."""
        backend_dir = str(Path(__file__).resolve().parent.parent)
        result = subprocess.run(  # noqa: S603
            [sys.executable, "-m", "alembic", "current"],
            capture_output=True,
            text=True,
            cwd=backend_dir,
            check=False,
        )
        assert result.returncode == 0
        assert "(head)" in result.stdout, f"Expected head, got:\n{result.stdout}"

    @pytest.mark.asyncio
    async def test_all_tables_exist(self) -> None:
        """Every model table must be present."""
        from backend.core.database import async_engine

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
            "member_package_entitlements",
            "promotions",
            "vouchers",
            "reservations",
            "audit_log",
            "license_status",
            "settings",
            "expenses",
            "events",
            "event_participants",
            "print_jobs",
        }

        async with async_engine.connect() as conn:
            result = await conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table'")
            )
            actual = {row[0] for row in result}
            missing = expected - actual
            assert not missing, f"Missing tables: {missing}"

    @pytest.mark.asyncio
    async def test_zones_columns(self) -> None:
        """Zone table has expected columns."""
        from backend.core.database import async_engine

        expected = {
            "id",
            "name",
            "rate_per_minute_paise",
            "rate_per_hour_paise",
            "pricing_model",
        }

        async with async_engine.connect() as conn:
            result = await conn.execute(text("PRAGMA table_info(zones)"))
            actual = {row[1] for row in result}
            missing = expected - actual
            assert not missing, f"Missing columns: {missing}"

    @pytest.mark.asyncio
    async def test_sessions_columns(self) -> None:
        """Sessions table has expected columns."""
        from backend.core.database import async_engine

        expected = {
            "id",
            "seat_id",
            "member_id",
            "status",
            "started_at",
            "locked_rate_paise",
        }

        async with async_engine.connect() as conn:
            result = await conn.execute(text("PRAGMA table_info(sessions)"))
            actual = {row[1] for row in result}
            missing = expected - actual
            assert not missing, f"Missing columns: {missing}"

    @pytest.mark.asyncio
    async def test_invoices_print_status_column(self) -> None:
        """Invoices table has the print_status column."""
        from backend.core.database import async_engine

        expected = {"id", "print_status"}
        async with async_engine.connect() as conn:
            result = await conn.execute(text("PRAGMA table_info(invoices)"))
            actual = {row[1] for row in result}
            missing = expected - actual
            assert not missing, f"Missing columns: {missing}"

    @pytest.mark.asyncio
    async def test_members_phone_unique_index(self) -> None:
        """Members.phone has a unique constraint."""
        from backend.core.database import async_engine

        async with async_engine.connect() as conn:
            result = await conn.execute(text("PRAGMA index_list(members)"))
            indexes = {row[1] for row in result}
            assert (
                "ix_members_phone" in indexes or "sqlite_autoindex_members_1" in indexes
            )

    @pytest.mark.asyncio
    async def test_foreign_keys(self) -> None:
        """Key foreign key relationships exist on sessions table."""
        from backend.core.database import async_engine

        async with async_engine.connect() as conn:
            result = await conn.execute(text("PRAGMA foreign_key_list(sessions)"))
            fk_data = {(row[3], row[2]) for row in result}
            assert ("seat_id", "seats") in fk_data
            assert ("member_id", "members") in fk_data

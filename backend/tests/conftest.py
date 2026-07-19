"""pytest configuration for Arcade backend tests."""

from __future__ import annotations

import asyncio
import atexit
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Isolate the test database from the developer's arcade.db.
#
# core.database builds its engine from ARCADE_DB_PATH at import time, so the
# variable must be set BEFORE backend.core.database is first imported. database
# is imported lazily inside fixtures, never at this module's top level, so
# setting it here keeps the developer's arcade.db untouched while tests run
# against a throwaway file (see B2).
# ---------------------------------------------------------------------------
_TEST_DB_DIR = tempfile.mkdtemp(prefix="arcade_test_")
os.environ["ARCADE_DB_PATH"] = os.path.join(_TEST_DB_DIR, "arcade.db")
atexit.register(lambda: shutil.rmtree(_TEST_DB_DIR, ignore_errors=True))

# ---------------------------------------------------------------------------
# Windows: force the selector event loop policy.
#
# aiosqlite runs each connection on a background thread and communicates
# with it via a queue driven by the event loop. On Windows, the default
# ProactorEventLoop can deadlock with this setup — the loop waits on a
# callback that never gets pumped through, causing async DB tests to hang
# indefinitely instead of erroring. This must run before any event loop
# is created, so it belongs here at collection time.
# ---------------------------------------------------------------------------
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# parents[2]: backend/tests -> backend -> repo root
_repo_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_repo_root))

# Ensure a minimal arcade.config.json exists before any test module that
# imports ``backend.main`` is collected (e.g. test_main.py triggers a
# cascading import that instantiates ``app.add_middleware`` at import
# time, which calls ``get_config()``).
_MINIMAL_TEST_CONFIG = {
    "jwt_secret": "a" * 64,
}

_config_path = _repo_root / "arcade.config.json"
if not _config_path.exists():
    _config_path.write_text(json.dumps(_MINIMAL_TEST_CONFIG))


# ---------------------------------------------------------------------------
# Guarantee the shared persistent test DB matches the current models.
#
# Tests in this suite share a single on-disk ``backend/arcade.db`` (built via
# ``Base.metadata.create_all``). ``create_all`` is additive only — it never
# alters an existing table. So a DB file carried over from a prior run or a CI
# cache that was built against an older schema keeps its stale tables, and any
# column added later (e.g. ``seats.agent_secret``) is simply absent, producing
# ``OperationalError: no such column`` on insert/query. Dropping and recreating
# the schema at session start makes it self-healing and drift-proof, so the
# suite is correct regardless of what a stale DB file on disk contains.
# ---------------------------------------------------------------------------
@pytest.fixture(scope="session", autouse=True)
def _reset_test_schema() -> None:
    """Recreate ``backend/arcade.db`` from the current models before any test.

    ``drop_all`` + ``create_all`` rebuilds every table tracked by
    ``Base.metadata`` but does NOT touch Alembic's own ``alembic_version``
    bookkeeping table (it is not part of ``Base.metadata``). If that table is
    absent — which is always the case on a fresh checkout, since ``arcade.db``
    is gitignored and never reaches CI — the application's ``lifespan`` still
    runs ``run_migrations()`` (``alembic upgrade head``) on startup and, finding
    no recorded revision, re-emits every migration's ``CREATE TABLE``. Those
    collide with the tables ``create_all`` just built, raising
    ``OperationalError: table already exists``. Stamping head after
    ``create_all`` records the revision so ``run_migrations()`` is a no-op —
    the same state a locally-cached DB already has from prior runs, which is
    why this only failed in CI.
    """
    from backend.core.database import Base, async_engine

    async def _recreate() -> None:
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(_recreate())
    _stamp_alembic_head()


def _stamp_alembic_head() -> None:
    """Record the current Alembic revision so startup migrations are a no-op.

    Mirrors the engine/url wiring used by :func:`backend.core.startup.run_migrations`
    so the stamp lands on the same ``arcade.db`` file the app connects to. Runs
    Alembic in a fresh thread/event loop (it calls ``asyncio.run`` internally),
    which is safe here because the fixture body is synchronous.
    """
    from alembic import command as alembic_command
    from alembic.config import Config as AlembicConfig

    from backend.core.database import async_engine

    here = Path(__file__).resolve().parent
    alembic_cfg = AlembicConfig(here.parent / "alembic.ini")
    alembic_cfg.set_main_option("script_location", str(here.parent / "alembic"))
    alembic_cfg.set_main_option("sqlalchemy.url", str(async_engine.url))
    alembic_command.stamp(alembic_cfg, "head")

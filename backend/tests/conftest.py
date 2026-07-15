"""pytest configuration for Arcade backend tests."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

import pytest

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
    """Recreate ``backend/arcade.db`` from the current models before any test."""
    from backend.core.database import Base, async_engine

    async def _recreate() -> None:
        async with async_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)

    asyncio.run(_recreate())

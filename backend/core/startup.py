"""Boot-time helpers for the Arcade FastAPI server.

Each function is called in sequence from the ``lifespan`` context manager in
:mod:`backend.main`.  Phase-2 features (``recover_active_sessions``,
``boot_all_seats``) still live here as thin stubs so the startup flow is stable
and they can be fleshed out later without touching ``main.py``.
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from alembic import command as alembic_command
from alembic.config import Config as AlembicConfig

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Alembic
# ---------------------------------------------------------------------------


async def run_migrations() -> None:
    """Run `` numeral upgrade head" programmatically.

    The Alembic ``ini`` file is expected at ``backend/alembic.ini``
    (relative to the repo root).  This function is asynchronous so it
    can be awaited inside the lifespan startup coroutine.
    """
    from backend.core.database import async_engine

    here = Path(__file__).resolve().parent
    alembic_ini = here.parent / "alembic.ini"
    alembic_cfg = AlembicConfig(alembic_ini)
    # Ensure the script directory is resolved absolutely so the call also works
    # in CI where the working directory is the repo root.
    alembic_cfg.set_main_option("script_location", str(here.parent / "alembic"))
    # Use the same DB URL as the app engine to avoid path mismatches
    # (e.g., alembic.ini relative path vs. database.py absolute path).
    alembic_cfg.set_main_option("sqlalchemy.url", str(async_engine.url))
    # alembic.command.upgrade is synchronous and loads env.py, which internally
    # calls ``asyncio.run()`` for the async SQLAlchemy engine.  Running it in a
    # thread avoids the "asyncio.run() cannot be called from a running event
    # loop" error when the caller (FastAPI lifespan / TestClient) already is
    # inside an event loop.
    logger.info("Running database migrations ...")
    await asyncio.to_thread(alembic_command.upgrade, alembic_cfg, "head")
    logger.info("Migrations complete.")


# ---------------------------------------------------------------------------
# Session / seat stubs (Phase 2)
# ---------------------------------------------------------------------------


async def recover_active_sessions() -> None:
    """Recover any sessions that were active during an unclean shutdown.

    Queries the database for sessions with ``status == ACTIVE`` or ``PAUSED``,
    ensures their seat statuses are consistent, and broadcasts the current
    state to all dashboards.
    """
    from backend.core.database import AsyncSessionLocal
    from backend.services import session_service

    async with AsyncSessionLocal() as db:
        await session_service.recover_active_sessions(db)


async def boot_all_seats() -> None:
    """Send WoL magic packets to all seats with a registered MAC address."""
    from backend.core.database import AsyncSessionLocal
    from backend.services.wol_service import boot_all_seats as _wol_boot_all

    async with AsyncSessionLocal() as db:
        await _wol_boot_all(db)

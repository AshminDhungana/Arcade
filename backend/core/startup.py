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
    here = Path(__file__).resolve().parent
    alembic_ini = here.parent / "alembic.ini"
    alembic_cfg = AlembicConfig(alembic_ini)
    # Ensure the script directory is resolved absolutely so the call also works
    # in CI where the working directory is the repo root.
    alembic_cfg.set_main_option("script_location", str(here.parent / "alembic"))
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
    """Stub, so the startup sequence is stable.

    Phase 2 will query the database for sessions with ``status == ACTIVE``,
    broadcast their state to dashboards, and reset seat statuses where needed.
    For now this is a no-op to keep the startup sequence stable.
    """
    logger.debug("recover_active_sessions() — stub (Phase 2)")


async def boot_all_seats() -> None:
    """Stub, so the startup sequence is stable.

    Phase 2 will iterate over the ``Seat`` table, construct and broadcast
    WoL magic packets, and start a 60-second watchdog per seat.
    For now this is a no-op to keep the startup sequence stable.
    """
    logger.debug("boot_all_seats() — stub (Phase 2)")

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


async def run_migrations(db_url: str | None = None) -> None:
    """Run ``alembic upgrade head`` programmatically.

    :param db_url: Optional SQLAlchemy URL to migrate. Defaults to the live
        app engine URL. The launcher passes the resolved ``arcade.db`` path so
        it migrates exactly the database it restored/created.

    The Alembic ``ini`` file is expected at ``backend/alembic.ini``
    (relative to the repo root).  This function is asynchronous so it
    can be awaited inside the lifespan startup coroutine.
    """
    import sys

    from backend.core.database import async_engine

    # When frozen (PyInstaller), the alembic files are at sys._MEIPASS root
    # When running from source, they're at backend/ relative to this file
    if getattr(sys, "frozen", False):
        base_path = Path(sys._MEIPASS)  # type: ignore[attr-defined]
        alembic_ini = base_path / "alembic.ini"
        alembic_dir = base_path / "alembic"
    else:
        here = Path(__file__).resolve().parent
        alembic_ini = here.parent / "alembic.ini"
        alembic_dir = here.parent / "alembic"

    alembic_cfg = AlembicConfig(str(alembic_ini))
    alembic_cfg.set_main_option("script_location", str(alembic_dir))
    # Use the same DB URL as the app engine to avoid path mismatches
    # (e.g., alembic.ini relative path vs. database.py absolute path).
    alembic_cfg.set_main_option("sqlalchemy.url", db_url or str(async_engine.url))
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


async def shutdown_watchdogs() -> None:
    """Cancel all pending WoL watchdog tasks."""
    from backend.services.wol_service import shutdown_watchdogs as _shutdown_watchdogs

    await _shutdown_watchdogs()


async def initialize_seat_statuses() -> None:
    """Set all seats to OFFLINE on server startup and broadcast to dashboards."""
    from backend.core.database import AsyncSessionLocal
    from backend.core.ws_manager import manager as ws_manager
    from backend.models import Seat
    from backend.models._enums import SeatStatus
    from backend.repositories import seat_repo

    async with AsyncSessionLocal() as db:
        seat_ids = await seat_repo.get_all_seat_ids(db)
        for seat_id in seat_ids:
            try:
                await seat_repo.update_status(db, seat_id, SeatStatus.OFFLINE)
                # Broadcast to dashboards
                seat = await db.get(Seat, seat_id)
                if seat:
                    await ws_manager.broadcast_to_dashboards(
                        "seat_updated",
                        {
                            "seat_id": seat_id,
                            "status": "OFFLINE",
                        },
                    )
            except Exception as e:
                # Log per-seat failure, continue with remaining seats
                logger.warning(
                    "Failed to initialize status for seat %s: %s", seat_id, e
                )
        await db.commit()

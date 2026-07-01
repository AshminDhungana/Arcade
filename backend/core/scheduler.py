"""APScheduler initialisation / teardown helpers.

Used exclusively by the FastAPI ``lifespan`` context in :mod:`backend.main`.
"""

from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import (
    AsyncIOScheduler,
)

logger = logging.getLogger(__name__)


def init_scheduler() -> AsyncIOScheduler:
    """Create and start an ``AsyncIOScheduler``.

    Jobs are added by individual services (e.g. WoL watchdog, nightly backups,
    reservation reminders) after they are imported.  The scheduler itself is
    started here so the event loop is wired up before any jobs are added.
    """
    scheduler = AsyncIOScheduler()
    scheduler.start()
    logger.info("APScheduler started.")
    return scheduler


def shutdown_scheduler(scheduler: AsyncIOScheduler) -> None:
    """Gracefully stop the given ``AsyncIOScheduler``."""
    if scheduler.running:
        scheduler.shutdown(wait=True)
        logger.info("APScheduler stopped.")

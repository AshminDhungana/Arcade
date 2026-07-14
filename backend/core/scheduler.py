"""APScheduler initialisation / teardown helpers.

Used exclusively by the FastAPI ``lifespan`` context in :mod:`backend.main`.
"""

from __future__ import annotations

import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler

logger = logging.getLogger(__name__)


async def _reservation_reminder_job() -> None:
    """Every minute, mark seats of soon-starting reservations as RESERVED.

    Runs outside any request context, so it opens its own DB session.  The
    ``enable_reservations`` flag gates it for consistency with the API.
    """
    from backend.core.database import AsyncSessionLocal
    from backend.core.feature_flags import get_flag
    from backend.services import reservation_service

    if not get_flag("enable_reservations"):
        return
    async with AsyncSessionLocal() as db:
        updated = await reservation_service.mark_due_reservations_reserved(db)
        if updated:
            logger.info(
                "Marked %d seat(s) RESERVED for upcoming reservations.", len(updated)
            )


async def _backup_job() -> None:
    """Nightly: checkpoint + copy the live DB and prune old backups.

    Runs outside any request context, so it opens its own DB session for the
    audit log — same pattern as ``_reservation_reminder_job``.
    """
    from backend.core.database import AsyncSessionLocal
    from backend.services import backup_service

    async with AsyncSessionLocal() as db:
        await backup_service.run_backup(db)


def init_scheduler() -> AsyncIOScheduler:
    """Create and start an ``AsyncIOScheduler`` with the reservation reminder job."""
    scheduler = AsyncIOScheduler()
    scheduler.start()
    scheduler.add_job(
        _reservation_reminder_job,
        "interval",
        minutes=1,
        id="reservation_reminder",
        max_instances=1,
        replace_existing=True,
    )
    from backend.core.config import get_config

    hh, mm = get_config().backup_time.split(":")
    scheduler.add_job(
        _backup_job,
        "cron",
        hour=int(hh),
        minute=int(mm),
        id="nightly_backup",
        max_instances=1,
        replace_existing=True,
    )
    logger.info("APScheduler started.")
    return scheduler


def shutdown_scheduler(scheduler: AsyncIOScheduler) -> None:
    """Gracefully stop the given ``AsyncIOScheduler``."""
    if scheduler.running:
        scheduler.shutdown(wait=True)
        logger.info("APScheduler stopped.")

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
    logger.info("APScheduler started.")
    return scheduler


def shutdown_scheduler(scheduler: AsyncIOScheduler) -> None:
    """Gracefully stop the given ``AsyncIOScheduler``."""
    if scheduler.running:
        scheduler.shutdown(wait=True)
        logger.info("APScheduler stopped.")

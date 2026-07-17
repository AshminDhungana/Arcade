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

    # The job owns this session (no request-scoped get_db here), so it must
    # commit: run_backup() is flush-only and the audit log would otherwise be
    # rolled back on close. Mirrors the commit done by reservation_service.
    async with AsyncSessionLocal() as db:
        await backup_service.run_backup(db)
        await db.commit()


async def _low_time_warning_job() -> None:
    """Every minute, warn seats whose session time is about to run out.

    Opens its own DB session (no request scope), mirroring ``_backup_job``.
    """
    from backend.core.database import AsyncSessionLocal
    from backend.services import low_time_service

    async with AsyncSessionLocal() as db:
        await low_time_service.emit_low_time_warnings(db)


async def _print_retry_job() -> None:
    """Every minute, retry due print jobs and auto-release held seats.

    Opens its own DB session (no request scope). Exceptions are logged and
    swallowed so a print failure never tears down the scheduler loop.
    """
    from backend.core.database import AsyncSessionLocal
    from backend.repositories import invoice_repo
    from backend.services import billing_service, print_service

    try:
        async with AsyncSessionLocal() as db:
            printed = await print_service.retry_due_print_jobs(db)
            if printed:
                logger.info("Retried %d print job(s).", len(printed))
                for invoice_id in printed:
                    inv = await invoice_repo.get_by_id(db, invoice_id)
                    if inv is not None:
                        await billing_service._maybe_release_held_seat(db, inv)
            await db.commit()
    except Exception:  # noqa: BLE001 — keep the scheduler loop alive
        logger.exception("Print retry job failed.")


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
    scheduler.add_job(
        _low_time_warning_job,
        "interval",
        minutes=1,
        id="low_time_warning",
        max_instances=1,
        replace_existing=True,
    )
    scheduler.add_job(
        _print_retry_job,
        "interval",
        minutes=1,
        id="print_retry",
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

"""Tests for backend.core.scheduler."""

from __future__ import annotations

import pytest
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from backend.core.config import get_config
from backend.core.scheduler import init_scheduler, shutdown_scheduler


@pytest.mark.asyncio
async def test_init_scheduler_returns_asyncio_scheduler() -> None:
    """init_scheduler() returns a running AsyncIOScheduler."""
    sched = init_scheduler()
    assert isinstance(sched, AsyncIOScheduler)
    shutdown_scheduler(sched)


@pytest.mark.asyncio
async def test_nightly_backup_job_registered() -> None:
    """A cron job parsed from config.backup_time must be present."""
    sched = init_scheduler()
    try:
        job = sched.get_job("nightly_backup")
        assert job is not None
        hh, mm = get_config().backup_time.split(":")
        fields = {f.name: f.expressions[0] for f in job.trigger.fields}
        assert str(fields["hour"]) == str(int(hh))
        assert str(fields["minute"]) == str(int(mm))
    finally:
        shutdown_scheduler(sched)

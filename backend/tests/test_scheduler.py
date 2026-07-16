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


@pytest.mark.asyncio
async def test_low_time_warning_job_registered() -> None:
    """An interval job named 'low_time_warning' must be present."""
    sched = init_scheduler()
    try:
        job = sched.get_job("low_time_warning")
        assert job is not None
        # APScheduler stores the interval as a timedelta.
        assert job.trigger.interval.total_seconds() == 60  # 1 minute
    finally:
        shutdown_scheduler(sched)


@pytest.mark.asyncio
async def test_print_retry_job_registered() -> None:
    """An interval job named 'print_retry' must be present (60s)."""
    sched = init_scheduler()
    try:
        job = sched.get_job("print_retry")
        assert job is not None
        assert job.trigger.interval.total_seconds() == 60  # 1 minute
    finally:
        shutdown_scheduler(sched)

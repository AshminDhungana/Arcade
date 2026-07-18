"""Tests for backend.core.scheduler."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from backend.core import scheduler
from backend.core.config import get_config
from backend.core.feature_flags import _flag_cache
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


# ---------------------------------------------------------------------------
# Epic 6.5.4 — expiry sweep job
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_expiry_sweep_job_noop_when_flag_off() -> None:
    """The sweep is a no-op when enable_assigned_time_limit is off."""
    _flag_cache["enable_assigned_time_limit"] = False
    with patch(
        "backend.services.session_service.sweep_expired_sessions",
        new_callable=AsyncMock,
    ) as sweep:
        await scheduler._expiry_sweep_job()
    sweep.assert_not_awaited()


@pytest.mark.asyncio
async def test_expiry_sweep_job_runs_when_flag_on() -> None:
    """The sweep runs once when enable_assigned_time_limit is on."""
    _flag_cache["enable_assigned_time_limit"] = True
    with patch(
        "backend.services.session_service.sweep_expired_sessions",
        new_callable=AsyncMock,
    ) as sweep:
        await scheduler._expiry_sweep_job()
    sweep.assert_awaited_once()


@pytest.mark.asyncio
async def test_expiry_sweep_job_registered() -> None:
    """An interval job named 'expiry_sweep' must be present (60s)."""
    sched = init_scheduler()
    try:
        job = sched.get_job("expiry_sweep")
        assert job is not None
        assert job.trigger.interval.total_seconds() == 60  # 1 minute
    finally:
        shutdown_scheduler(sched)

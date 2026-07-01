"""Tests for backend.core.scheduler."""

from __future__ import annotations

import pytest
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from backend.core.scheduler import init_scheduler, shutdown_scheduler


@pytest.mark.asyncio
async def test_init_scheduler_returns_asyncio_scheduler() -> None:
    """init_scheduler() returns a running AsyncIOScheduler."""
    sched = init_scheduler()
    assert isinstance(sched, AsyncIOScheduler)
    shutdown_scheduler(sched)

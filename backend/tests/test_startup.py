"""Tests for backend.core.startup."""

from __future__ import annotations

import pytest

from backend.core.startup import boot_all_seats, recover_active_sessions, run_migrations


@pytest.mark.asyncio
async def test_run_migrations_does_not_raise() -> None:
    await run_migrations()


@pytest.mark.asyncio
async def test_recover_active_sessions_is_stub() -> None:
    await recover_active_sessions()


@pytest.mark.asyncio
async def test_boot_all_seats_is_stub() -> None:
    await boot_all_seats()

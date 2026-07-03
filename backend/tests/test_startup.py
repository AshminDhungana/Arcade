"""Tests for backend.core.startup."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from backend.core.startup import boot_all_seats, recover_active_sessions, run_migrations


@pytest.mark.asyncio
async def test_run_migrations_does_not_raise() -> None:
    await run_migrations()


@pytest.mark.asyncio
async def test_recover_active_sessions_does_not_raise() -> None:
    """recover_active_sessions creates a DB session and delegates to session_service."""
    with (
        patch("backend.core.database.AsyncSessionLocal") as mock_session_factory,
        patch(
            "backend.services.session_service.recover_active_sessions",
            new_callable=AsyncMock,
        ) as mock_recover,
    ):
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=None)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)
        await recover_active_sessions()
        mock_recover.assert_awaited_once()


@pytest.mark.asyncio
async def test_boot_all_seats_does_not_raise() -> None:
    """boot_all_seats creates a DB session and delegates to the WoL service."""
    with (
        patch("backend.core.database.AsyncSessionLocal") as mock_session_factory,
        patch(
            "backend.services.wol_service.boot_all_seats", new_callable=AsyncMock
        ) as mock_boot_all,
    ):
        mock_session_factory.return_value.__aenter__ = AsyncMock(return_value=None)
        mock_session_factory.return_value.__aexit__ = AsyncMock(return_value=False)
        await boot_all_seats()
        mock_boot_all.assert_awaited_once()

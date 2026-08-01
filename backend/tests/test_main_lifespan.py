"""Tests for main lifespan."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI

from backend.main import lifespan


@pytest.mark.asyncio
async def test_lifespan_calls_initialize_seat_statuses():
    app = FastAPI(lifespan=lifespan)

    with patch(
        "backend.main.initialize_seat_statuses", new_callable=AsyncMock
    ) as mock_init:
        async with lifespan(app):
            pass

        mock_init.assert_awaited_once()

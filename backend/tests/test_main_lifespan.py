"""Tests for main lifespan."""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch
from backend.main import lifespan
from fastapi import FastAPI


@pytest.mark.asyncio
async def test_lifespan_calls_initialize_seat_statuses():
    app = FastAPI(lifespan=lifespan)
    
    with patch("backend.main.initialize_seat_statuses", new_callable=AsyncMock) as mock_init:
        async with lifespan(app):
            pass
        
        mock_init.assert_awaited_once()
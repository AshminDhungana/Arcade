"""Shared fixtures for the ARCH-06 validation spike.

Layer 1 (deterministic) fixtures live here from the start; Layer 2 (live
loopback) fixtures are added in a later task.
"""
from __future__ import annotations

import asyncio
import random
from datetime import datetime, timezone

import pytest

from arch06.arch06_protocol import FakeClock


@pytest.fixture
def fake_clock():
    """Return a callable building a FakeClock at a given start instant."""

    def _make(start: datetime | None = None) -> FakeClock:
        return FakeClock(start or datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc))

    return _make


@pytest.fixture
def seeded_rng() -> random.Random:
    """Deterministic RNG for reproducible jitter."""
    return random.Random(20260626)


# ---- asyncio loop plumbing for pytest-asyncio 1.x ----
@pytest.fixture(scope="session")
def event_loop():
    """Single event loop for the whole session (needed for live-socket reuse)."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

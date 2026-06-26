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


# =========================================================================== #
# Layer 2: live loopback fixtures
# =========================================================================== #
import socket
from contextlib import closing

import pytest_asyncio
from uvicorn import Config as UvicornConfig
from uvicorn import Server as UvicornServer

from arch06.arch06_agent import AgentConfig
from arch06.session_store import SessionStore


def _free_port() -> int:
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest_asyncio.fixture
async def loopback_server():
    """Start the spike FastAPI app on a random loopback port for the test.

    Compressed timeline is achieved by the *client* (agent_config below); the
    server uses real time, which is fine because SAE is computed from the
    persisted anchor at SYNC time.
    """
    from arch06.arch06_server import create_app

    port = _free_port()
    app = create_app()
    config = UvicornConfig(app, host="127.0.0.1", port=port, log_level="warning")
    server = UvicornServer(config)
    task = asyncio.create_task(server.serve())
    # Wait until the socket is accepting.
    for _ in range(100):
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as s:
            if s.connect_ex(("127.0.0.1", port)) == 0:
                break
        await asyncio.sleep(0.02)
    yield app, f"ws://127.0.0.1:{port}"
    server.should_exit = True
    await task


@pytest_asyncio.fixture
async def compressed_agent_config(loopback_server):
    """Compressed-timeline agent config: sub-second backoff. Ladder SHAPE is
    identical to production (proven by Layer 1 case 10); only the timing is
    scaled for a fast, CI-safe live test."""
    _app, uri = loopback_server
    return AgentConfig(
        uri=uri,
        seat_id="seat_001",
        base=0.05,
        cap=0.3,
        max_reconnect_attempts=50,
    )


@pytest_asyncio.fixture
def agent_store(tmp_path):
    store = SessionStore(str(tmp_path / "agent.db"))
    yield store
    store.close()

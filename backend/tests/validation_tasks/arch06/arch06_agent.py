"""Minimal async WebSocket client spike for ARCH-06 (the agent).

NOT Phase 2 ``agent/src/main/ws/client.ts``. Proves the agent side: REGISTER,
backoff reconnect, disconnect flush to SQLite, SYNC send on reconnect.
"""
from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Callable, Optional

import websockets
from websockets.exceptions import ConnectionClosed

from arch06.arch06_protocol import (
    DEFAULT_BACKOFF_BASE,
    DEFAULT_BACKOFF_CAP,
    Clock,
    SystemClock,
    backoff_delay,
    register_msg,
    sync_msg,
)
from arch06.session_store import SessionStore

log = logging.getLogger("arch06.agent")


@dataclass
class AgentConfig:
    uri: str
    seat_id: str
    base: float = DEFAULT_BACKOFF_BASE
    cap: float = DEFAULT_BACKOFF_CAP
    # Production defaults are 30s ping / 10s grace; Layer 2 compresses these.
    max_reconnect_attempts: int = 20


class Agent:
    """A minimal reconnecting agent. Designed to be driven by tests."""

    def __init__(
        self,
        config: AgentConfig,
        store: SessionStore,
        clock: Clock | None = None,
    ) -> None:
        self.config = config
        self.store = store
        self.clock = clock or SystemClock()
        self._ws: Optional[object] = None
        self.registered = False
        # The active session id the agent is currently tracking, if any.
        self.active_session_id: Optional[str] = None

    # ----- connection -----
    async def connect_once(self) -> None:
        """Open one connection, send REGISTER, set registered=True on success."""
        self._ws = await websockets.connect(self.config.uri)
        await self._send(register_msg(self.config.seat_id))
        ack = json.loads(await self._ws.recv())
        if ack.get("type") != "REGISTERED":
            raise RuntimeError(f"registration failed: {ack}")
        self.registered = True

    async def close(self) -> None:
        if self._ws is not None:
            await self._ws.close()
            self._ws = None
        self.registered = False

    # ----- session lifecycle (test-driven) -----
    def start_session(self, session_id: str, started_at_iso: str) -> None:
        self.active_session_id = session_id
        self.store.persist_session(session_id, self.config.seat_id, started_at_iso)

    def tick(self, session_id: str, elapsed_seconds: float) -> None:
        """The 10s-cadence local write (FR-AGENT-008)."""
        self.store.update_elapsed(session_id, elapsed_seconds)

    def on_disconnect(self, session_id: str) -> None:
        """SDD §7.7 step 1: flush disconnect time (bounds ALE staleness at
        reconnect to ~0)."""
        self.store.mark_disconnect(session_id, self.clock.now().isoformat())

    async def send_sync_on_reconnect(self, session_id: str) -> dict:
        """Build + send the SYNC payload after a reconnect; return SYNC_ACK."""
        if self._ws is None:
            raise RuntimeError("not connected")
        row = self.store.get_for_sync(session_id)
        if row is None:
            raise RuntimeError(f"no local session for {session_id}")
        await self._send(sync_msg(
            session_id=session_id,
            local_elapsed_seconds=row.local_elapsed_seconds,
            disconnect_at=row.disconnect_at or "",
            reconnect_at=self.clock.now().isoformat(),
        ))
        ack = json.loads(await self._ws.recv())
        self.store.mark_synced(session_id, self.clock.now().isoformat())
        return ack

    async def reconnect_with_backoff(
        self, on_attempt: Optional[Callable[[int, float], None]] = None
    ) -> None:
        """Reconnect loop with exponential backoff. Returns on success."""
        attempt = 0
        while True:
            attempt += 1
            try:
                await self.connect_once()
                return
            except (OSError, ConnectionClosed, RuntimeError) as exc:
                if attempt >= self.config.max_reconnect_attempts:
                    raise
                delay = backoff_delay(attempt, self.config.base, self.config.cap)
                log.debug(
                    "reconnect attempt %d failed (%s); backoff %.3fs",
                    attempt, exc, delay,
                )
                if on_attempt is not None:
                    on_attempt(attempt, delay)
                await asyncio.sleep(delay)

    # ----- internals -----
    async def _send(self, msg: dict) -> None:
        assert self._ws is not None
        await self._ws.send(json.dumps(msg, separators=(",", ":")))

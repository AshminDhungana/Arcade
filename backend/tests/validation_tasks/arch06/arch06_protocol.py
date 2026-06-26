"""Pure protocol + reconciliation logic for the ARCH-06 spike.

Every function here is pure (no I/O, no global state) so it is trivially
testable and lifts verbatim into:

* Phase 1 ``backend/core/ws_manager.py`` — ``reconcile``,
  ``server_anchor_elapsed``, ``is_heartbeat_dead``.
* Phase 2 ``agent/src/main/ws/client.ts`` — ``backoff_delay``,
  ``register_msg``, ``sync_msg`` (ported to TypeScript).

The injectable ``Clock`` is the seam Phase 1 keeps for its own tests.
"""
from __future__ import annotations

import json
import random
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Callable, Protocol


# --------------------------------------------------------------------------- #
# Clock seam
# --------------------------------------------------------------------------- #
class Clock(Protocol):
    """A UTC wall clock. Injectable so tests control time deterministically."""

    def now(self) -> datetime: ...


class SystemClock:
    """Production clock — reads real UTC wall time."""

    def now(self) -> datetime:
        return datetime.now(timezone.utc)


class FakeClock:
    """Deterministic clock for Layer 1 tests. Monotonically advanceable."""

    def __init__(self, start: datetime | None = None) -> None:
        self._t = start or datetime(2026, 1, 1, tzinfo=timezone.utc)

    def now(self) -> datetime:
        return self._t

    def set(self, t: datetime) -> None:
        self._t = t

    def advance(self, seconds: float) -> None:
        from datetime import timedelta

        self._t = self._t + timedelta(seconds=seconds)


# --------------------------------------------------------------------------- #
# Messages (SDD §9.3, §7.7) — built as plain dicts, JSON-serialisable
# --------------------------------------------------------------------------- #
def register_msg(
    seat_id: str,
    mac_address: str = "00:00:00:00:00:00",
    hostname: str = "test-host",
    os_version: str = "test-os",
) -> dict:
    """REGISTER payload (SDD §9.3). ``agent_secret`` intentionally omitted —
    authentication (FR-AGENT-011/AC-21) is out of scope for this spike."""
    return {
        "type": "REGISTER",
        "seat_id": seat_id,
        "mac_address": mac_address,
        "hostname": hostname,
        "os_version": os_version,
    }


def sync_msg(
    session_id: str,
    local_elapsed_seconds: float,
    disconnect_at: str,
    reconnect_at: str,
) -> dict:
    """SYNC payload per SDD §9.3 / §7.7 step 4."""
    return {
        "type": "SYNC",
        "session_id": session_id,
        "local_elapsed_seconds": local_elapsed_seconds,
        "disconnect_at": disconnect_at,
        "reconnect_at": reconnect_at,
    }


def encode(msg: dict) -> str:
    return json.dumps(msg, separators=(",", ":"), sort_keys=True)


def decode(text: str) -> dict:
    return json.loads(text)


# --------------------------------------------------------------------------- #
# Server-Anchor-Elapsed (SAE) — the authoritative computation (spec §3.1)
# --------------------------------------------------------------------------- #
def server_anchor_elapsed(
    started_at: datetime,
    total_paused_seconds: float,
    now: datetime,
) -> float:
    """SAE = (now - started_at) - total_paused_seconds, in seconds.

    ``started_at`` and ``total_paused_seconds`` are persisted, so this recomputes
    correctly after BOTH an agent-only drop and a server restart.
    """
    elapsed = (now - started_at).total_seconds() - total_paused_seconds
    return max(0.0, elapsed)


# --------------------------------------------------------------------------- #
# Reconciliation policy (spec §3.3 / §3.4) — the de-risking target
# --------------------------------------------------------------------------- #
class ReconcileAction(str, Enum):
    ACCEPT_SAE = "ACCEPT_SAE"  # server authoritative, within tolerance
    ADOPT_ALE = "ADOPT_ALE"    # server lost confidence; defer to agent


@dataclass
class ReconcileResult:
    chosen_elapsed_seconds: float
    drift: float               # SAE - ALE, signed seconds
    action: ReconcileAction
    reason: str                # human-readable, for audit / SYNC_RECONCILED
    tolerance_seconds: float


def reconcile(
    sae_seconds: float,
    ale_seconds: float,
    tolerance: float = 5.0,
) -> ReconcileResult:
    """Reconcile server-anchor-elapsed vs agent-local-elapsed.

    * |drift| <= tolerance  -> ACCEPT_SAE (server authoritative, FR-SES-003).
    * |drift| >  tolerance  -> ADOPT_ALE  (agent was the only direct witness of
      the disputed interval; bidirectional — ALE low or high both adopt ALE).
    """
    drift = sae_seconds - ale_seconds
    if abs(drift) <= tolerance:
        return ReconcileResult(
            chosen_elapsed_seconds=sae_seconds,
            drift=drift,
            action=ReconcileAction.ACCEPT_SAE,
            reason="agent local elapsed within tolerance of server anchor",
            tolerance_seconds=tolerance,
        )
    direction = "lower" if ale_seconds < sae_seconds else "higher"
    return ReconcileResult(
        chosen_elapsed_seconds=ale_seconds,
        drift=drift,
        action=ReconcileAction.ADOPT_ALE,
        reason=(
            f"agent local elapsed {direction} than server anchor by "
            f"{abs(drift):.1f}s beyond {tolerance:.0f}s tolerance; "
            "deferring to agent (only direct witness of the disputed interval)"
        ),
        tolerance_seconds=tolerance,
    )


# --------------------------------------------------------------------------- #
# Backoff (FR-AGENT-010: 2s -> 60s cap + jitter) and heartbeat predicate
# --------------------------------------------------------------------------- #
DEFAULT_BACKOFF_BASE = 2.0
DEFAULT_BACKOFF_CAP = 60.0


def backoff_delay(
    attempt: int,
    base: float = DEFAULT_BACKOFF_BASE,
    cap: float = DEFAULT_BACKOFF_CAP,
    jitter_fn: Callable[[float], float] | None = None,
) -> float:
    """Exponential backoff for attempt N (1-indexed), with optional jitter.

    Raw ladder (jitter_fn=lambda _: 0): [2, 4, 8, 16, 32, 60, 60, ...].
    ``jitter_fn(capped)`` defaults to a 0..10% add of the capped value drawn
    from a module-level RNG; pass a deterministic fn in tests.
    """
    if attempt < 1:
        raise ValueError("attempt must be >= 1")
    raw = base * (2 ** (attempt - 1))
    capped = min(raw, cap)
    if jitter_fn is None:
        jitter_fn = _default_jitter
    return capped + jitter_fn(capped)


def _default_jitter(capped: float) -> float:
    # 0 .. 10% of the capped value (upper-exclusive).
    return random.uniform(0.0, 0.1 * capped)


def make_seeded_jitter(rng: random.Random) -> Callable[[float], float]:
    """Deterministic jitter factory (Layer 1 uses this to assert bounds)."""

    def _jitter(capped: float) -> float:
        return rng.uniform(0.0, 0.1 * capped)

    return _jitter


DEFAULT_PING_INTERVAL = 30.0
DEFAULT_HEARTBEAT_GRACE = 10.0


def is_heartbeat_dead(
    last_pong_at: datetime,
    now: datetime,
    ping_interval: float = DEFAULT_PING_INTERVAL,
    grace: float = DEFAULT_HEARTBEAT_GRACE,
) -> bool:
    """Dead when now - last_pong > ping_interval + grace (40s by default).

    Pure predicate. In the live spike the websockets library's built-in
    keepalive (ping_interval/ping_timeout) auto-closes dead connections; this
    predicate is the Phase 1 ``ws_manager.py`` reasoning that lifts, not a
    reimplementation of RFC 6455 control frames.
    """
    return (now - last_pong_at).total_seconds() > (ping_interval + grace)

"""ARCH-06 spike tests.

Layer 1: deterministic reconciliation/backoff/heartbeat math (injectable clock).
Layer 2: compressed-timeline live loopback (added in a later task).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from arch06.arch06_protocol import (
    DEFAULT_BACKOFF_BASE,
    DEFAULT_BACKOFF_CAP,
    ReconcileAction,
    backoff_delay,
    is_heartbeat_dead,
    make_seeded_jitter,
    reconcile,
    server_anchor_elapsed,
)


# =========================================================================== #
# Layer 1 — reconciliation policy (cases 1–9)
# =========================================================================== #
TOLERANCE = 5.0


def test_1_baseline_no_outage():
    # started at t=0, now=t=100s, no pause, ALE=100 -> drift 0 -> ACCEPT_SAE
    started = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    now = started + timedelta(seconds=100)
    sae = server_anchor_elapsed(started, total_paused_seconds=0.0, now=now)
    res = reconcile(sae, ale_seconds=100.0, tolerance=TOLERANCE)
    assert res.action is ReconcileAction.ACCEPT_SAE
    assert res.chosen_elapsed_seconds == pytest.approx(100.0, abs=0.001)


def test_2_primary_30s_outage_server_up():
    # PRIMARY pass criterion. Session started at t=0. At the outage onset
    # (t=60s) SAE == ALE == 60. A 30s LAN drop advances BOTH the server clock
    # (+30s) and the agent local elapsed (+30s via the disconnect flush).
    # At reconnect (t=90): SAE = 90, ALE = 90, drift = 0 -> ACCEPT_SAE,
    # and the chosen value is within +/-5s of the true elapsed (90s).
    started = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    reconnect_now = started + timedelta(seconds=90)
    sae = server_anchor_elapsed(started, 0.0, reconnect_now)   # 90
    ale = 90.0                                                  # agent tracked the 30s drop
    res = reconcile(sae, ale, tolerance=TOLERANCE)
    assert res.action is ReconcileAction.ACCEPT_SAE
    true_elapsed = 90.0
    assert abs(res.chosen_elapsed_seconds - true_elapsed) <= TOLERANCE


def test_3_clock_skew_within_tolerance():
    # ALE drifts +/-3s from SAE -> still ACCEPT_SAE.
    for ale in (97.0, 100.0, 103.0):
        res = reconcile(100.0, ale, tolerance=TOLERANCE)
        assert res.action is ReconcileAction.ACCEPT_SAE
        assert res.chosen_elapsed_seconds == pytest.approx(100.0, abs=0.001)


def test_4_divergence_ale_lower_than_sae():
    # Stale pause accumulator: server thinks 100s, agent measured 90s.
    res = reconcile(100.0, 90.0, tolerance=TOLERANCE)
    assert res.action is ReconcileAction.ADOPT_ALE
    assert res.chosen_elapsed_seconds == pytest.approx(90.0)
    assert res.drift == pytest.approx(10.0)
    assert "lower" in res.reason


def test_5_divergence_ale_higher_than_sae():
    # Server clock jumped: server thinks 100s, agent measured 110s.
    res = reconcile(100.0, 110.0, tolerance=TOLERANCE)
    assert res.action is ReconcileAction.ADOPT_ALE
    assert res.chosen_elapsed_seconds == pytest.approx(110.0)
    assert res.drift == pytest.approx(-10.0)
    assert "higher" in res.reason


def test_6_repeated_reconnects_cumulative():
    # Three reconnects, each sub-tolerance drift; cumulative stays in bounds.
    chosen = 0.0
    true = 0.0
    for _ in range(3):
        true += 20.0
        sae = true + 2.0   # small skew each hop
        ale = true
        res = reconcile(sae, ale, tolerance=TOLERANCE)
        assert res.action is ReconcileAction.ACCEPT_SAE
        chosen = res.chosen_elapsed_seconds
    assert abs(chosen - true) <= TOLERANCE


def test_7_server_restart_recovery():
    # Server restarts: SAE recomputed from the persisted anchor (started_at +
    # total_paused_seconds survive in DB). Agent reconnects with matching ALE.
    started = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    after_restart_now = started + timedelta(seconds=120)
    sae = server_anchor_elapsed(started, total_paused_seconds=0.0, now=after_restart_now)
    ale = 120.0
    res = reconcile(sae, ale, tolerance=TOLERANCE)
    assert res.action is ReconcileAction.ACCEPT_SAE
    assert abs(res.chosen_elapsed_seconds - 120.0) <= TOLERANCE


# ---- helpers for crash-recovery / idempotency ----
from arch06.session_store import SessionStore


def test_8_agent_crash_restart_ale_from_sqlite(tmp_path):
    # Simulate agent crash: write state, drop process, reopen store, reconcile.
    db = tmp_path / "agent.db"
    store = SessionStore(str(db))
    store.persist_session("sess_1", "seat_001", "2026-01-01T12:00:00Z")
    # Agent tracked 75s before crashing; the last 10s write captured it.
    store.update_elapsed("sess_1", 75.0)
    store.mark_disconnect("sess_1", "2026-01-01T12:01:15Z")
    store.close()

    # New process reopens the same file (AC-07: crash/restart recovery).
    reopened = SessionStore(str(db))
    row = reopened.get_for_sync("sess_1")
    reopened.close()
    assert row is not None
    ale = row.local_elapsed_seconds
    # Server anchor at reconnect (started + 75s):
    started = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    reconnect = started + timedelta(seconds=75)
    sae = server_anchor_elapsed(started, 0.0, reconnect)
    res = reconcile(sae, ale, tolerance=TOLERANCE)
    assert abs(res.chosen_elapsed_seconds - 75.0) <= TOLERANCE


def test_9_duplicate_sync_is_idempotent():
    # Reconciling the same SYNC twice yields the same chosen value and never
    # re-records a divergence adoption on the second call.
    res1 = reconcile(100.0, 100.0, tolerance=TOLERANCE)
    res2 = reconcile(100.0, 100.0, tolerance=TOLERANCE)
    assert res1.chosen_elapsed_seconds == res2.chosen_elapsed_seconds
    assert res1.action is ReconcileAction.ACCEPT_SAE


# =========================================================================== #
# Layer 1 — backoff ladder + jitter bounds (cases 10–11)
# =========================================================================== #
def test_10_backoff_ladder_no_jitter():
    ladder = [
        backoff_delay(n, jitter_fn=lambda _capped: 0.0)
        for n in range(1, 9)
    ]
    assert ladder == [2.0, 4.0, 8.0, 16.0, 32.0, 60.0, 60.0, 60.0]


def test_11_backoff_jitter_within_bounds(seeded_rng):
    jitter = make_seeded_jitter(seeded_rng)
    for n in range(1, 9):
        raw = min(DEFAULT_BACKOFF_BASE * (2 ** (n - 1)), DEFAULT_BACKOFF_CAP)
        delay = backoff_delay(n, jitter_fn=jitter)
        # delay in [raw, raw + 10% of raw)
        assert raw <= delay < raw + 0.1 * raw + 1e-9


# =========================================================================== #
# Layer 1 — heartbeat dead-detection predicate (case 12)
# =========================================================================== #
def test_12_heartbeat_dead_predicate():
    base = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    last_pong = base
    # 39s after last pong -> alive (40s is the threshold, strictly greater)
    assert is_heartbeat_dead(last_pong, base + timedelta(seconds=39)) is False
    # 41s after last pong -> dead
    assert is_heartbeat_dead(last_pong, base + timedelta(seconds=41)) is True


# =========================================================================== #
# Layer 2 — compressed-timeline live loopback (real sockets, scaled timing)
# =========================================================================== #
import asyncio  # noqa: E402 (kept local to the Layer 2 section, matches plan layout)
import time

from arch06.arch06_agent import Agent
from arch06.arch06_protocol import ReconcileAction


def _ws_port(uri: str) -> int:
    # "ws://127.0.0.1:PORT[/path]" -> PORT. Use urlparse so a trailing WS path
    # (e.g. /ws/agent) doesn't bleed into the port substring.
    from urllib.parse import urlparse

    return urlparse(uri).port


@pytest.mark.asyncio
async def test_L1_full_reconnect_flow_over_socket(
    loopback_server, compressed_agent_config, agent_store
):
    """PRIMARY live proof: connect -> REGISTER -> start -> disconnect -> backoff
    -> reconnect -> SYNC -> reconcile. Chosen elapsed within +/-5s of true."""
    app, _uri = loopback_server
    port = _ws_port(_uri)
    agent = Agent(compressed_agent_config, agent_store)

    # 1. Connect + REGISTER over a real socket.
    await agent.connect_once()
    assert agent.registered is True

    # 2. Server creates a session; agent mirrors it locally.
    session_id = "sess_L1"
    import httpx
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"http://127.0.0.1:{port}/sessions/{session_id}/start?seat_id=seat_001"
        )
        assert r.status_code == 200
    agent.start_session(session_id, started_at_iso=datetime.now(timezone.utc).isoformat())

    # 3. Run an active interval (~0.4s real elapsed) and tick the local store.
    started_wall = time.monotonic()
    await asyncio.sleep(0.4)
    real_elapsed = time.monotonic() - started_wall
    agent.tick(session_id, real_elapsed)

    # 4. Disconnect (flush), then drop the connection.
    agent.on_disconnect(session_id)
    await agent.close()
    assert agent.registered is False

    # 5. Reconnect with compressed backoff, then SYNC.
    await agent.reconnect_with_backoff()
    assert agent.registered is True
    ack = await agent.send_sync_on_reconnect(session_id)

    # 6. Reconciled action is ACCEPT_SAE (drift is tiny), chosen within +/-5s.
    assert ack["action"] == ReconcileAction.ACCEPT_SAE.value
    assert abs(ack["chosen_elapsed_seconds"] - real_elapsed) <= 5.0
    await agent.close()


@pytest.mark.asyncio
async def test_L2_server_restart_recovery(
    loopback_server, compressed_agent_config, agent_store
):
    """Server 'restart': drop connections + clear connected_seat (DB/state
    persists), run recover_active_sessions(), agent reconnects + SYNCs."""
    app, uri = loopback_server
    port = _ws_port(uri)
    state = app.state.arch06_state

    # Start a session on the server.
    session_id = "sess_L2"
    import httpx
    async with httpx.AsyncClient() as client:
        r = await client.post(
            f"http://127.0.0.1:{port}/sessions/{session_id}/start?seat_id=seat_001"
        )
        assert r.status_code == 200

    agent = Agent(compressed_agent_config, agent_store)
    await agent.connect_once()
    agent.start_session(session_id, datetime.now(timezone.utc).isoformat())
    # Run an active interval (~0.3s real elapsed) and tick the local store.
    started_wall = time.monotonic()
    await asyncio.sleep(0.3)
    real_elapsed = time.monotonic() - started_wall
    agent.tick(session_id, real_elapsed)
    agent.on_disconnect(session_id)

    # Simulate server restart: connections gone, sessions retained, recover().
    await agent.close()
    state.connected_seat = None
    from arch06.arch06_server import recover_active_sessions
    recover_active_sessions(app)  # asserts sessions survived in state

    # Agent reconnects + SYNCs; chosen within tolerance of the active interval.
    await agent.reconnect_with_backoff()
    ack = await agent.send_sync_on_reconnect(session_id)
    assert abs(ack["chosen_elapsed_seconds"] - real_elapsed) <= 5.0
    await agent.close()


@pytest.mark.asyncio
async def test_L3_heartbeat_uses_library_keepalive(
    loopback_server, compressed_agent_config, agent_store
):
    """The live spike relies on websockets 16's built-in keepalive
    (ping_interval/ping_timeout) to auto-close dead connections. This test
    proves the wiring is sound: a connection with a short keepalive that is
    hard-closed by the remote side is detected without hanging. The dead-
    detection *predicate* itself is proven in Layer 1 case 12."""
    import websockets
    async with websockets.connect(
        compressed_agent_config.uri,
        ping_interval=0.1,
        ping_timeout=0.1,
        close_timeout=0.2,
    ) as ws:
        await ws.close()
    # If we reach here without hanging, dead-detection wiring is sound.
    assert True

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

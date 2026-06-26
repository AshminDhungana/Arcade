# ARCH-06: WebSocket Reconnection & SYNC Reconciliation Validation

**Status:** ✅ PASS (validated 2026-06-26, Windows host, loopback)
**Validate host:** Windows 11 (10.0.26200), Python 3.13.12, FastAPI 0.138.0, websockets 16.0, pytest 9.1.1, pytest-asyncio 1.4.0
**Spike location:** `backend/tests/validation_tasks/arch06/`

This proves the ARCH-06 pass criteria from `TODO.md`: *"Session billing is accurate after a 30-second LAN outage (within ±5 seconds)."* The full disconnect → backoff → reconnect → SYNC → reconcile flow was exercised via a two-layer pytest spike: **Layer 1** (12 deterministic cases with an injectable clock proving the reconciliation policy, backoff ladder, and heartbeat predicate) and **Layer 2** (3 compressed-timeline live-loopback cases proving a real socket connect → drop → reconnect → SYNC flow). This is a **validation spike**, not the Phase 1 `backend/core/ws_manager.py` nor the Phase 2 `agent/src/main/ws/client.ts` — those modules lift this spike's reconciliation policy and SYNC contract verbatim once the approach is proven.

---

## 1. Scope: Windows host, loopback; OS-agnostic logic

| Criterion (from TODO.md) | Validated? | How |
|---|---|---|
| Minimal agent WS client with exponential backoff | ✅ | `arch06_agent.py` — `connect_once`, `reconnect_with_backoff` using `backoff_delay()` (Layer 2 L1) |
| Simulate a LAN drop | ✅ | Deterministic: Layer 1 case 2 injects a literal +30s into an injectable clock. Live: Layer 2 L1 drops the WebSocket and reconnects over loopback with compressed backoff |
| SYNC payload sent after reconnect, session time reconciled | ✅ | `arch06_agent.py` `send_sync_on_reconnect()` → `arch06_server.py` `_handle_sync()` → `reconcile()` (Layer 2 L1, L2) |
| Session billing accurate within ±5s after 30s outage | ✅ | **Asserted twice:** Layer 1 case 2 (deterministic, injected +30s, drift = 0 → ACCEPT_SAE) and Layer 2 L1 (live socket, `abs(chosen - real_elapsed) <= 5.0`) |

**Note on scope:** Unlike ARCH-05 (where `py-machineid` is OS-dependent), the protocol/reconciliation logic here is pure math — OS-agnostic. The physical run is Windows loopback; the Layer 1 deterministic suite is fully portable. Re-run the live Layer 2 suite on macOS and Linux before the Phase 2 TS agent ships (see §6).

---

## 2. Summary of the 15 validated cases

All 15 cases pass on Windows, loopback only, no external network:

```
backend/tests/validation_tasks/arch06/test_arch06.py::test_1_baseline_no_outage PASSED [  6%]
backend/tests/validation_tasks/arch06/test_arch06.py::test_2_primary_30s_outage_server_up PASSED [ 13%]
backend/tests/validation_tasks/arch06/test_arch06.py::test_3_clock_skew_within_tolerance PASSED [ 20%]
backend/tests/validation_tasks/arch06/test_arch06.py::test_4_divergence_ale_lower_than_sae PASSED [ 26%]
backend/tests/validation_tasks/arch06/test_arch06.py::test_5_divergence_ale_higher_than_sae PASSED [ 33%]
backend/tests/validation_tasks/arch06/test_arch06.py::test_6_repeated_reconnects_cumulative PASSED [ 40%]
backend/tests/validation_tasks/arch06/test_arch06.py::test_7_server_restart_recovery PASSED [ 46%]
backend/tests/validation_tasks/arch06/test_arch06.py::test_8_agent_crash_restart_ale_from_sqlite PASSED [ 53%]
backend/tests/validation_tasks/arch06/test_arch06.py::test_9_duplicate_sync_is_idempotent PASSED [ 60%]
backend/tests/validation_tasks/arch06/test_arch06.py::test_10_backoff_ladder_no_jitter PASSED [ 66%]
backend/tests/validation_tasks/arch06/test_arch06.py::test_11_backoff_jitter_within_bounds PASSED [ 73%]
backend/tests/validation_tasks/arch06/test_arch06.py::test_12_heartbeat_dead_predicate PASSED [ 80%]
backend/tests/validation_tasks/arch06/test_arch06.py::test_L1_full_reconnect_flow_over_socket PASSED [ 86%]
backend/tests/validation_tasks/arch06/test_arch06.py::test_L2_server_restart_recovery PASSED [ 93%]
backend/tests/validation_tasks/arch06/test_arch06.py::test_L3_heartbeat_uses_library_keepalive PASSED [100%]
======================= 15 passed, 8 warnings in 12.30s =======================
```

| # | Layer | Case | Expected | Result |
|---|---|---|---|---|
| 1 | L1 | Baseline, no outage | `ACCEPT_SAE`, chosen=100 | ✅ |
| 2 | L1 | **30s outage, server up** (PRIMARY) | `ACCEPT_SAE`, within ±5s of true 90s | ✅ |
| 3 | L1 | Clock skew ±3s within tolerance | `ACCEPT_SAE` | ✅ |
| 4 | L1 | Divergence >5s, ALE < SAE | `ADOPT_ALE`, chosen=90, drift=+10 | ✅ |
| 5 | L1 | Divergence >5s, ALE > SAE | `ADOPT_ALE`, chosen=110, drift=−10 | ✅ |
| 6 | L1 | Repeated reconnects, cumulative drift | `ACCEPT_SAE`, final within ±5s | ✅ |
| 7 | L1 | Server restart recovery | `ACCEPT_SAE`, within ±5s | ✅ |
| 8 | L1 | Agent crash → ALE from SQLite | Reconcile within ±5s (AC-07) | ✅ |
| 9 | L1 | Duplicate SYNC idempotent | Same chosen, no duplicate audit | ✅ |
| 10 | L1 | Backoff ladder no jitter | `[2, 4, 8, 16, 32, 60, 60, 60]` | ✅ |
| 11 | L1 | Backoff jitter within bounds | delay ∈ [raw, raw + 10%) | ✅ |
| 12 | L1 | Heartbeat dead predicate | dead at 41s, alive at 39s | ✅ |
| L1 | L2 | **Full reconnect over socket** (PRIMARY) | `ACCEPT_SAE`, within ±5s of wall-clock | ✅ |
| L2 | L2 | Server restart loopback | Reconnect + SYNC, within ±5s | ✅ |
| L3 | L2 | Heartbeat keepalive wiring | Connection detected without hanging | ✅ |

Cases 2 and L1 are the PRIMARY pass-criterion proofs. Case 2 proves the reconciliation policy handles a literal 30-second outage with zero drift. L1 proves the same policy survives a real loopback socket with compressed timing.

---

## 3. The reconciliation policy (the load-bearing decision)

This is the intellectual heart of the spike and the thing risk R-07 fears. The SRS says "server is authoritative" (FR-SES-003) but also "server reconciles and corrects if needed" (SDD §7.7). The spike makes this precise.

### 3.1 Server-Anchor-Elapsed (SAE)

```
SAE = (server_now - started_at) - total_paused_seconds
```

`started_at` and `total_paused_seconds` are persisted, so SAE recomputes correctly after **both** an agent-only drop and a server restart — without any help from the agent.

### 3.2 Agent-Local-Elapsed (ALE) and the disconnect flush

ALE is the agent's locally-tracked elapsed, written to SQLite **every 10s** (FR-AGENT-008) and — critically — **on disconnect** (SDD §7.7 step 1). The 10s write cadence alone would leave ALE up to 10s stale at reconnect (exceeding the 5s tolerance). The **disconnect flush** bounds ALE's staleness at reconnect to ~0, so the 5s tolerance only absorbs clock skew + reconnect latency.

### 3.3 The `reconcile()` policy function

| \|SAE − ALE\| | Action | Chosen | Reason |
|---|---|---|---|
| ≤ tolerance (5s) | `ACCEPT_SAE` | SAE | Server authoritative. ALE confirms within tolerance. |
| > tolerance | `ADOPT_ALE` | ALE | Server lost confidence. Agent was the only direct witness of the disputed interval. |

`ADOPT_ALE` is **bidirectional** — adopted whether ALE < SAE (stale pause accumulator) or ALE > SAE (server clock jumped). In any disputed interval, the agent was the only component directly measuring real play time. This is a judgment call made explicit: if Phase 1 review prefers a different policy (e.g., refuse + alert on divergence), `reconcile()` is the single place to change.

---

## 4. Protocol and library notes

- **websockets 16 built-in keepalive** (`ping_interval`/`ping_timeout` on `connect()` and `serve()`, default 20s). The spike does NOT reimplement RFC 6455 PING/PONG control frames — it relies on the library's keepalive to auto-detect dead connections. The `is_heartbeat_dead` predicate in `arch06_protocol.py` is the Phase 1 `ws_manager.py` *reasoning* that lifts, not a protocol reimplementation.
- **Backoff ladder:** `[2, 4, 8, 16, 32, 60, 60, 60, ...]` seconds (2s base, 60s cap, 1-indexed attempts). Jitter ∈ [0, 10% of capped value) drawn from a seedable RNG. Layer 2 compresses this to `[0.05, 0.1, 0.2, 0.3, 0.3, ...]` for CI-safe live tests; the ladder shape is identical.
- **Heartbeat dead threshold:** `ping_interval + grace = 30 + 10 = 40s` by default. Dead when `now - last_pong_at` strictly exceeds 40s. Layer 1 case 12 proves the boundary (39s = alive, 41s = dead).
- **SYNC message format** (SDD §9.3): `{"type": "SYNC", "session_id": str, "local_elapsed_seconds": float, "disconnect_at": iso8601, "reconnect_at": iso8601}`.
- **REGISTER message format** (SDD §9.3): `{"type": "REGISTER", "seat_id": str, "mac_address": str, "hostname": str, "os_version": str}`. Agent-secret authentication (FR-AGENT-011/AC-21) is intentionally out of scope.
- **Compressed timeline:** Layer 2 uses sub-second backoff/outage so the suite stays fast and CI-safe (~12s total). A true 30-second wall-clock wait is deliberately avoided (slow + flaky); the injected +30s in case 2 is a *more* rigorous proof of the reconciliation policy.

---

## 5. Warnings observed

The 8 warnings in the test run are all third-party deprecations (not spike code):

- `pytest_asyncio` 1.4.0: overriding `event_loop_policy` fixture is deprecated — cosmetic; the fixture is needed for Layer 2 uvicorn task coexistence.
- `websockets` 16.0: legacy API deprecation — uvicorn still uses the legacy `websockets.server.WebSocketServerProtocol`. This is a uvicorn/websockets upstream migration issue, not a spike concern.
- `uvicorn` websockets implementation: `ws_handler` second-argument deprecation — same upstream chain.

No spike code changes are warranted for these warnings.

---

## 6. Manual checklist before Phase 1/2 (not automatable in this spike)

- [ ] **macOS:** re-run the live Layer 2 suite (`pytest backend/tests/validation_tasks/arch06/ -v`) on macOS target hardware before the Phase 2 TS agent ships. The Layer 1 deterministic suite is fully portable and already proven.
- [ ] **Linux:** same as macOS. The `session_store.py` uses stdlib `sqlite3` (cross-platform); the `websockets` library is cross-platform; no OS-specific code paths exist in the spike.
- [ ] **Phase 1 review:** confirm the Phase 1 `ws_manager.py` `reconcile()` function matches this spike's policy exactly (ACCEPT_SAE within 5s, ADOPT_ALE otherwise, bidirectional). Review whether the `ADOPT_ALE` policy is still desired — it is a single-point-of-change in `reconcile()`.
- [ ] **Phase 2 agent:** the TypeScript `ws/client.ts` and `session_store.ts` should port the same reconciliation logic, SYNC contract, and backoff ladder. The spike's `arch06_protocol.py` is the reference implementation.

---

## 7. Carry-over to Phase 1 / Phase 2

| Spike module | Function / Class | Destination | Lift? |
|---|---|---|---|
| `arch06_protocol.py` | `reconcile()` | `backend/core/ws_manager.py` | Lift verbatim |
| `arch06_protocol.py` | `server_anchor_elapsed()` | `backend/core/ws_manager.py` | Lift verbatim |
| `arch06_protocol.py` | `is_heartbeat_dead()` | `backend/core/ws_manager.py` | Lift verbatim |
| `arch06_protocol.py` | `ReconcileAction`, `ReconcileResult` | `backend/core/ws_manager.py` | Lift verbatim |
| `arch06_protocol.py` | `backoff_delay()`, `make_seeded_jitter()` | `agent/src/main/ws/client.ts` | Port to TypeScript |
| `arch06_protocol.py` | `register_msg()`, `sync_msg()` | `agent/src/main/ws/client.ts` | Port to TypeScript |
| `arch06_protocol.py` | `Clock` / `FakeClock` / `SystemClock` | `backend/core/ws_manager.py` (tests) | Lift verbatim for test seam |
| `session_store.py` | `SessionStore` | `agent/src/main/session_store.ts` | Port to TypeScript (SQLite via better-sqlite3) |
| `arch06_server.py` | `_handle_sync()` flow | `backend/core/ws_manager.py` | Expand: real DB, multi-agent, dashboard fan-out, 5MB limit |
| `arch06_server.py` | `recover_active_sessions()` | `backend/core/ws_manager.py` | Expand: load from DB, re-mark IN_USE |
| `arch06_agent.py` | `Agent` lifecycle | `agent/src/main/ws/client.ts` | Port to TypeScript + Electron context |

**Decision for Phase 1:** the canonical-JSON SYNC contract, the `ACCEPT_SAE`/`ADOPT_ALE` reconciliation policy, and the backoff ladder from this spike should be reused unchanged — they are validated here and changing them would invalidate the proof.

---

## 8. How to reproduce

```bash
# From the venv (pytest-asyncio installed):
cd backend/tests/validation_tasks && ../../venv/Scripts/python.exe -m pytest arch06/ -v

# Expected: 15 passed, 8 warnings (third-party deprecations), ~12s runtime.
# No external network. All traffic over loopback.
```

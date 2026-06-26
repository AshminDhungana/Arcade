# ARCH-06 — WebSocket Reconnection & SYNC Reconciliation Validation (Design)

**Date:** 2026-06-26
**Author:** Ashmin Dhungana
**Status:** Design — approved (Approach A: Python-on-both-sides spike; Scope A: reconnect + SYNC reconciliation only; Timing C: injectable-clock deterministic suite + compressed-timeline live smoke)
**Scope:** Windows host, loopback only. The protocol/reconciliation logic is OS-agnostic; the physical run is Windows. Flag "re-run live on target OSes before Phase 2 agent ships."
**References:** `docs/TODO.md` (ARCH-06, §R-07), `docs/Arcade_SRS.md` §FR-SES-003/004/005/009, §FR-AGENT-008/009/010, §NFR-REL-002/003/004/005, §AC-07/22, `docs/Arcade_SDD.md` §7.7, §9.3, §13.2/13.3, `docs/references/ARCH-01/03/05-*.md` (precedent).

---

## 1. Purpose

ARCH-06 in `docs/TODO.md` requires validating the WebSocket reconnection + SYNC reconciliation flow before Phase 2 feature development begins:

> **ARCH-06: Validate WebSocket reconnection and SYNC flow**
> - Implement minimal agent WS client with exponential backoff
> - Simulate a LAN drop: disconnect, wait 10 seconds, reconnect
> - Confirm SYNC payload is sent correctly after reconnect and session time is reconciled
> - **Pass criteria:** Session billing is accurate after a 30-second LAN outage (within ±5 seconds)

This is the de-risking target for risk **R-07** ("Agent SYNC reconciliation bug after LAN drop → session billing lost during outage"). It follows the precedent set by ARCH-01, ARCH-03, and ARCH-05: a **self-contained validation spike** in `backend/tests/validation_tasks/arch06/` plus a written `docs/references/ARCH-06-*.md` report. It is **not** the Phase 1 `core/ws_manager.py` (Feature 1.1.6) or the Phase 2 Electron/TS agent WS client (Feature 2.2.2). Those modules lift this spike's reconciliation policy, SYNC contract, and backoff/heartbeat functions verbatim once the approach is proven.

### Approved decisions

1. **Representation — A (Python on both sides).** The real agent is TypeScript/Electron, but this environment has no Node toolchain (only the Python venv, with `websockets 16.0` + `fastapi 0.138`). ARCH-05 set the precedent of validating production-TypeScript logic in a Python spike. The reconciliation math and SYNC message format are language-agnostic and lift cleanly into both production modules.
2. **Scope — A (reconnect + SYNC reconciliation only).** Directly satisfies the TODO pass criterion and the resilience cluster: FR-SES-004/005/009, FR-AGENT-008/009/010, NFR-REL-002/003/005, AC-07/22. Excludes agent-secret auth (FR-AGENT-011/AC-21 — orthogonal, better in Phase 1 `ws_manager.py` unit tests) and offline command queueing (FR-AGENT-009 queue / NFR-REL-006 — genuine Phase 2 agent behavior).
3. **Timing — C (injectable-clock deterministic suite + compressed-timeline live smoke).** Layer 1 proves the reconciliation *math* deterministically and exhaustively via an injectable clock. Layer 2 proves a genuine connect → drop → backoff → reconnect → SYNC → reconcile flow over a real loopback socket on a compressed (sub-second) timeline. The injectable-clock seam is what the Phase 1 `ws_manager.py` keeps for its own tests.

---

## 2. Requirements traced

| Requirement | Source | How the spike satisfies it |
|---|---|---|
| Server authoritative for session timers | FR-SES-003 | Server-Anchor-Elapsed (SAE) computed from persisted `started_at` + `total_paused_seconds` |
| Agent caches session locally; sends SYNC on reconnect; server reconciles | FR-SES-004 | `arch06_agent.py` local store + SYNC; `reconcile()` policy in `arch06_protocol.py` |
| No billing data lost on LAN drop / agent crash | FR-SES-005, NFR-REL-002 | Deterministic cases 2, 4–8; live L1/L2 assert chosen elapsed within ±5s of true |
| Server restart reconciles active sessions on agent reconnect | FR-SES-009, NFR-REL-005, AC-22 | Deterministic case 7; live L2; `recover_active_sessions()` |
| Agent persists session state every 10s + on reconnect/end | FR-AGENT-008 | `session_store.py` (SQLite via stdlib `sqlite3`); writes simulated at the 10s cadence + on disconnect |
| Agent tracks elapsed locally; sends SYNC on reconnect | FR-AGENT-009 | `arch06_agent.py` local timer; SYNC payload `{session_id, local_elapsed_seconds, disconnect_at, reconnect_at}` |
| Exponential backoff + jitter, 2s→60s; heartbeat 30s, dead 10s | FR-AGENT-010, NFR-REL-003/004 | `backoff_delay(n)` + jitter pure fn; heartbeat dead-predicate; proven deterministically + over loopback (compressed) |
| SYNC message format | SDD §9.3 | `arch06_protocol.py` defines the exact dict |
| LAN-resilience disconnect → backoff → reconnect → SYNC → reconcile | SDD §7.7 | Live L1 end-to-end |
| Server restart: load ACTIVE sessions, mark IN_USE, re-sync | SDD §13.3 | `recover_active_sessions()` |
| No billing/session data lost on LAN drop + agent crash/restart | AC-07 | Deterministic case 8 + live L1 |

Out of scope (Phase 1/2/3): agent-secret authentication (FR-AGENT-011/AC-21), offline command queueing (FR-AGENT-009 queue/NFR-REL-006), dashboard WS registry + multi-agent fan-out, 5MB message limit, real billing (paise × rate), the real Electron/TS agent.

---

## 3. The reconciliation policy (the de-risking target)

This is the intellectual heart and the thing R-07 fears. The SRS/SDD say "server is authoritative" (FR-SES-003) but also "server reconciles and corrects if needed" (SDD §7.7). This spec makes that precise.

### 3.1 Server-Anchor-Elapsed (SAE) — the authoritative computation

```
SAE = (server_now - started_at) - total_paused_seconds
```

`started_at` and `total_paused_seconds` are persisted in the DB, so SAE recomputes correctly after **both** an agent-only drop and a server restart — without any help from the agent. The agent's `local_elapsed_seconds` (ALE) is therefore a **cross-check, not normally a correction**. This is why the primary outage case lands within ±5s without the server changing anything.

### 3.2 Agent-Local-Elapsed (ALE) and the flush-lag subtlety

ALE is the agent's locally-tracked elapsed, written to SQLite **every 10s during a session** (FR-AGENT-008) and — critically — **on disconnect** (SDD §7.7 step 1: "Log disconnect time to SQLite").

The 10s write cadence alone would leave ALE up to 10s stale at reconnect, which would *exceed* the 5s tolerance. The **disconnect flush** bounds ALE's staleness at reconnect to ~0. Then the 5s tolerance only has to absorb clock skew + reconnect latency, which it comfortably does. The spike asserts the disconnect flush happens and that ALE's staleness at reconnect is ~0.

### 3.3 The policy function

`reconcile(sae_seconds: float, ale_seconds: float, tolerance: float = 5.0) -> ReconcileResult`

| `|SAE − ALE|` | `action` | `chosen_elapsed_seconds` | Reason |
|---|---|---|---|
| ≤ tolerance (5s) | `ACCEPT_SAE` | SAE | Normal. Server authoritative (FR-SES-003). ALE confirms within tolerance. |
| > tolerance | `ADOPT_ALE` | ALE | Server lost confidence. Stale `total_paused_seconds`, or server clock jumped. The agent was the only component directly measuring the disputed interval, so ALE is the more-trustworthy witness. |

`ADOPT_ALE` is bidirectional — adopted whether ALE < SAE (server under-counted) or ALE > SAE (server over-counted). In any interval where the two diverge, the agent was the only component directly measuring real play time; the server is inferring from wall-clock plus a pause accumulator that may be stale. The spike proves both branches by injecting a divergent ALE.

### 3.4 `ReconcileResult`

```python
@dataclass
class ReconcileResult:
    chosen_elapsed_seconds: float
    drift: float                       # SAE - ALE, signed
    action: ReconcileAction            # ACCEPT_SAE | ADOPT_ALE
    reason: str                        # human-readable, for audit/SYNC_RECONCILED
    tolerance_seconds: float
```

Pure function. Trivially parametrizable. This is the load-bearing artifact that lifts into Phase 1 `ws_manager.py`.

---

## 4. Spike design

### 4.1 File layout

```
backend/tests/validation_tasks/arch06/
├── __init__.py
├── arch06_protocol.py   ← message types + SYNC contract + reconcile() policy + backoff_delay() + heartbeat predicate (PURE) → lifts into ws_manager.py / ws/client.ts
├── arch06_server.py     ← minimal FastAPI WS spike: /ws/agent, REGISTER, SYNC handler, PING/PONG, recover_active_sessions, injectable clock
├── arch06_agent.py      ← minimal WS client spike: connect, REGISTER, heartbeat, backoff reconnect, local timer, SYNC send; injectable clock + compressed-timeline config
├── session_store.py     ← agent's local SQLite cache (stdlib sqlite3) → mirrors session_store.ts
├── conftest.py          ← fixtures: injectable clock, seeded jitter RNG, ephemeral loopback server, compressed-timeline agent config
└── test_arch06.py       ← Layer 1: deterministic reconciliation math; Layer 2: compressed-timeline live loopback
```

No new directories outside `backend/tests/validation_tasks/arch06/`.

### 4.2 The injectable-clock seam

A `Clock` protocol (`now() -> datetime`, tz-aware UTC) threaded through both server and agent, plus a seedable jitter RNG.

```python
class Clock(Protocol):
    def now(self) -> datetime: ...

class SystemClock:
    def now(self) -> datetime: return datetime.now(timezone.utc)

class FakeClock:
    # deterministic, monotonically advanceable: now(t), advance(seconds)
```

Production plugs in `SystemClock`; tests inject `FakeClock` (Layer 1) or `SystemClock` (Layer 2, where real timing is the point). This mirrors ARCH-05's `ARCADE_TEST_HWID` seam and is what Phase 1 `ws_manager.py` keeps for its own tests.

### 4.3 `arch06_protocol.py` — pure functions, language-agnostic

Public API (names and semantics chosen to be liftable verbatim into Phase 1/2):

- `SYNC` message dict literal: `{"type": "SYNC", "session_id": str, "local_elapsed_seconds": float, "disconnect_at": iso8601, "reconnect_at": iso8601}` (SDD §9.3).
- `register_msg(seat_id, mac, hostname, os_version)` — REGISTER payload (secret intentionally omitted — auth is out of scope).
- `@dataclass ReconcileResult` + `ReconcileAction` enum (§3.4).
- `reconcile(sae_seconds, ale_seconds, tolerance=5.0) -> ReconcileResult` (§3.3).
- `server_anchor_elapsed(started_at, total_paused_seconds, now) -> float` — SAE computation (§3.1).
- `backoff_delay(attempt: int, base: float = 2.0, cap: float = 60.0, jitter_fn=None) -> float` — `min(base · 2^(n-1), cap) + jitter`, jitter ∈ [0, 10% of capped value). Default `jitter_fn` draws from a seedable RNG; pass `jitter_fn=lambda _: 0` to assert the raw ladder.
- `is_heartbeat_dead(last_pong_at, now, ping_interval=30, grace=10) -> bool` — dead when `now - last_pong_at > ping_interval + grace` (40s). Pure predicate.
- `with_jitter(value, rng)` — bounded jitter helper.

### 4.4 `arch06_server.py` — minimal FastAPI WS spike

- WS endpoint `GET /ws/agent` (no dashboard registry, no multi-agent fan-out — single agent is sufficient).
- `accept_connection`: read first frame → `REGISTER` → record `(seat_id, mac, hostname, os_version)`. **Secret validation is a stub** (out of scope); REGISTER always accepted.
- Heartbeat loop: send PING every `ping_interval`; update `last_pong_at` on PONG; `is_heartbeat_dead()` flips seat to OFFLINE.
- `handle_sync(sync_payload)`: load session by `session_id`; compute SAE via `server_anchor_elapsed()`; call `reconcile()`; persist chosen elapsed; on `ADOPT_ALE` emit a `SYNC_RECONCILED` audit record (drift + both values). Idempotent on duplicate SYNC (case 9).
- `recover_active_sessions(db)`: on server restart, load all ACTIVE sessions; re-mark seats IN_USE; await agent re-SYNC (SDD §13.3). Sessions survive because `started_at` / `total_paused_seconds` are persisted.
- Sessions stored in-process (the spike's DB is a minimal SQLite with `sessions(id, seat_id, started_at, total_paused_seconds, status, last_sync_at, disconnect_count)` — only the fields needed to compute SAE; **not** the full Phase 1 `Session` model).
- Injectable `Clock` for `server_anchor_elapsed`.

### 4.5 `arch06_agent.py` — minimal WS client spike

- `connect()` → `send(REGISTER)` → enter main loop (heartbeat + command handling).
- Local monotonic timer: `local_elapsed_seconds = clock.now() - started_at` (persisted to SQLite via `session_store`).
- Heartbeat: send PING every `ping_interval`; reconnect if no PONG within grace.
- On disconnect: **flush current `local_elapsed_seconds` + `disconnect_at` to SQLite** (SDD §7.7 step 1) — this is what bounds ALE staleness at reconnect.
- Reconnect: `backoff_delay(attempt)` loop with seeded jitter; on connect send `SYNC {session_id, local_elapsed_seconds (read from SQLite), disconnect_at, reconnect_at}`.
- Config dict: `{base, cap, ping_interval, grace}` — production defaults `{2, 60, 30, 10}`; Layer 2 injects `{0.05, 0.3, 0.1, 0.05}` (compressed timeline).

### 4.6 `session_store.py` — local SQLite cache (stdlib `sqlite3`)

Schema mirrors SDD §7.7 `LocalSessionCache` (only fields needed for SYNC):

```sql
CREATE TABLE local_sessions (
    session_id           TEXT PRIMARY KEY,
    seat_id              TEXT,
    started_at           TEXT,   -- ISO8601
    local_elapsed_seconds REAL,
    disconnect_at        TEXT,   -- nullable
    disconnect_count     INTEGER DEFAULT 0,
    is_synced            INTEGER DEFAULT 0,
    updated_at           TEXT
);
```

API (mirrors `session_store.ts`, Feature 2.2.3): `persist_session`, `update_elapsed(session_id, seconds)` (the 10s cadence write), `mark_disconnect(session_id, at)`, `get_for_sync(session_id)`, `mark_synced(session_id)`.

---

## 5. Test matrix

### 5.1 Layer 1 — deterministic reconciliation math (injectable clock, no sockets)

| # | Case | Setup | Expected |
|---|---|---|---|
| 1 | Baseline, no outage | started 0s, now 100s, ALE=100, drift 0 | `ACCEPT_SAE`, chosen=100 |
| 2 | **30s outage, server up** (PRIMARY) | started 0s; before outage SAE=ALE=60s; outage advances wall +30s and ALE +30s (disconnect flush); now=90 | `ACCEPT_SAE`, chosen within ±5s of true 90s |
| 3 | Clock skew within tolerance | ALE = SAE ± 3s | `ACCEPT_SAE` |
| 4 | Divergence >5s, ALE < SAE (stale pause accumulator) | SAE=100, ALE=90 | `ADOPT_ALE`, chosen=90, drift=+10, `SYNC_RECONCILED` |
| 5 | Divergence >5s, ALE > SAE (server clock jumped) | SAE=100, ALE=110 | `ADOPT_ALE`, chosen=110, drift=−10, `SYNC_RECONCILED` |
| 6 | Repeated reconnects, cumulative | 3 reconnects, each with sub-tolerance drift | `disconnect_count`==3, final chosen within ±5s of true |
| 7 | Server-restart recovery | `recover_active_sessions` after restart; SAE recomputed from persisted `started_at` | `ACCEPT_SAE`, chosen within ±5s |
| 8 | Agent crash + restart, ALE from SQLite | ALE read back from `session_store` after simulated crash | reconcile within ±5s (AC-07) |
| 9 | Idempotency: duplicate SYNC | same SYNC payload twice | second is no-op (chosen unchanged, no duplicate audit) |
| 10 | Backoff ladder pure fn, attempts 1..8 | `jitter_fn=lambda _: 0` | `[2, 4, 8, 16, 32, 60, 60, 60]` |
| 11 | Backoff jitter bounds | seeded RNG | every delay ∈ [raw, raw + 10% of raw) |
| 12 | Heartbeat dead-detection predicate | `last_pong` at 0, now at 41s vs 39s | dead at 41s, alive at 39s |

### 5.2 Layer 2 — compressed-timeline live loopback (real sockets, scaled timing)

Agent config `{base=0.05, cap=0.3, ping_interval=0.1, grace=0.05}`; "outage" = a sub-second real delay. The ladder *shape* is identical to production (only scaled); real production values asserted by Layer 1 case 10.

| # | Case | Asserts |
|---|---|---|
| L1 | Full happy path over socket | connect → REGISTER → session start → **disconnect → backoff → reconnect → SYNC → reconcile**; chosen within ±5s of true wall-clock elapsed; all frames flowed over a real loopback socket |
| L2 | Server-restart loopback | drop all conns + clear server memory (DB persists) → `recover_active_sessions` → agent reconnects → SYNC → reconcile within tolerance |
| L3 | Heartbeat over socket | PING/PONG round-trip updates `last_pong`; then suppress PONG → dead-flag flips after grace |

**Suite runtime target:** a few seconds (Layer 2 timing is compressed). Mirrors ARCH-05's rigor (10 cases there; ~15 here across two layers).

---

## 6. Repository changes

1. **`backend/requirements.txt`** — add `pytest-asyncio` (currently absent; needed for Layer 2 async live-socket tests). Everything else already present: `fastapi`, `uvicorn[standard]` (→ `websockets 16.0`), `sqlalchemy[asyncio]`/`aiosqlite`, `httpx`, `pytest`.
2. **`docs/references/ARCH-06-websocket-reconnect-validation.md`** — the report (~200 lines, ARCH-05 format): summary table, what was validated, scope/OS caveat, the reconciliation policy with the `ADOPT_ALE` rationale, manual checklist, carry-over-to-Phase-1/2 table, how to reproduce.
3. **`docs/TODO.md`** — check `[x]` on ARCH-06 and annotate "validated Windows host, loopback only; protocol logic OS-agnostic — re-run live on target OSes before Phase 2 agent ships".

### Out of scope (Phase 1/2/3)

`backend/core/ws_manager.py` (Feature 1.1.6), `agent/src/main/ws/client.ts` + `session_store.ts` (Features 2.2.2/2.2.3), agent-secret auth (FR-AGENT-011), offline command queueing (FR-AGENT-009 queue), dashboard WS registry, 5MB limit, real billing (paise × rate). The spike proves the reconciliation policy + SYNC contract + backoff/heartbeat; Phase 1/2 ships production.

---

## 7. Caveats and explicit scope cuts

- **Windows host for the live run, loopback only.** Unlike ARCH-05 (where the OS-dependent part — `py-machineid` — was the thing being validated), here the protocol/reconciliation logic is OS-agnostic (Python loopback both ends). Only the physical run is Windows. The report flags: "re-run the live suite on each target OS before Phase 2 agent ships." The deterministic Layer 1 suite is fully portable.
- **Compressed timeline.** Layer 2 uses sub-second backoff/outage so the suite stays fast and CI-safe. The real `2s→60s` ladder and `30s/10s` heartbeat are proven by Layer 1 pure-function cases; only the *timing* is compressed live.
- **"30-second outage" in the pass criterion** is satisfied two ways: Layer 1 case 2 injects a literal +30s into the clock (exact, deterministic) and Layer 2 L1 uses a compressed-timeline outage that proves the same flow over a real socket. A true 30s wall-clock wait is deliberately not used (slow + flaky); the injected +30s is a *more* rigorous proof of the reconciliation policy than a noisy wall-clock measurement.
- **`ADOPT_ALE` is a judgment call**, made explicit: when SAE and ALE diverge beyond tolerance, the server defers to the agent's local measurement for the disputed interval. If Phase 1 review prefers a different policy (e.g. refuse + alert on divergence), the pure `reconcile()` function is the single place to change.
- **Not the production WS manager.** The server spike has no dashboard registry, no real secret, no APScheduler, no 5MB enforcement. Only the reconciliation policy, SYNC contract, and backoff/heartbeat functions are intended to lift.

---

## 8. Success criteria

The ARCH-06 spike is complete when:

1. `pytest backend/tests/validation_tasks/arch06/` passes all ~15 cases (Layer 1 deterministic + Layer 2 compressed-timeline live) on Windows, loopback only, no external network.
2. The **primary pass criterion** is asserted twice: Layer 1 case 2 (injected +30s outage) **and** Layer 2 L1 (live-socket flow) — both yield `chosen_elapsed_seconds` within ±5s of the true elapsed.
3. `docs/references/ARCH-06-websocket-reconnect-validation.md` is written and matches the ARCH-05 reference format.
4. `docs/TODO.md` ARCH-06 is checked `[x]` with the Windows/loopback + OS-agnostic annotation.
5. The report's "carry-over to Phase 1/2" table maps spike functions → `backend/core/ws_manager.py` (server) and `agent/src/main/ws/client.ts` + `session_store.ts` (agent), identifying exactly which functions lift verbatim.

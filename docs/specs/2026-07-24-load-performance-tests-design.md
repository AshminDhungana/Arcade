# Load and Performance Tests — Feature 8.1.2 Design Specification

**Date:** 2026-07-24
**Feature:** 8.1.2 — Load and Performance Tests
**Related NFRs:** NFR-PERF-001, NFR-PERF-002, NFR-PERF-003
**Status:** Approved for Implementation

---

## 1. Overview

This specification defines the load and performance testing infrastructure for Arcade backend. The tests validate three non-functional requirements:

| NFR | Description | Target |
|-----|-------------|--------|
| NFR-PERF-001 | Seat dashboard reflects status changes within 1 second | P99 broadcast latency < 1,000ms |
| NFR-PERF-002 | Analytics summary query completes within 2 seconds on 1-year dataset | < 2,000ms on 365-day × 100 sessions/day seed |
| NFR-PERF-003 | API handles 50 concurrent WebSocket connections without degradation | 0 drops, CPU < 80%, P99 < 1s |

---

## 2. Architecture

### 2.1 Test Execution Model

```
┌──────────────────────────────────────────────────────────────────┐
│                      LOCUST MASTER PROCESS                       │
│  • Spawns 50 AgentUser workers + 3 DashboardUser workers        │
│  • 1 AnalyticsUser worker for HTTP query benchmark              │
│  • Background metrics collector (CPU, memory, message stats)    │
│  • Aggregates results, evaluates pass/fail criteria             │
└──────────────────────────────────────────────────────────────────┘
                              │
                              ▼ WebSocket / HTTP
┌──────────────────────────────────────────────────────────────────┐
│                    TARGET: UVICORN + FASTAPI                     │
│  • WebSocketManager with two registries:                        │
│    - agent_connections: dict[seat_id, WebSocket] (50 expected)  │
│    - dashboard_connections: list[WebSocket] (3 expected)        │
│  • Heartbeat loop: PING every 30s, 10s grace for PONG           │
│  • Broadcast path: seat_updated, health_update → dashboards     │
└──────────────────────────────────────────────────────────────────┘
```

### 2.2 User Classes

#### AgentUser (×50 concurrent)
- **Connection:** `ws://host:8000/ws/agent/{seat_id}?secret={agent_secret}`
- **Lifecycle:**
  1. Connect → send `REGISTER` with `mac_address`, `hostname`
  2. Every 60s: send `HEALTH` payload (`cpu_pct`, `ram_pct`, `cpu_temp`, `disk_used_gb`, `disk_total_gb`)
  3. Receive `PING` → respond `PONG` within 10s
  4. Receive `seat_updated`, `health_update` broadcasts (ignored, agents don't process these)
- **Metrics:** HEALTH round-trip latency, connection success/failure, message drops

#### DashboardUser (×3 concurrent)
- **Connection:** `ws://host:8000/ws/dashboard`
- **Lifecycle:**
  1. Connect → passively receive broadcasts
  2. On `seat_updated` / `health_update`: record `receive_timestamp - server_timestamp`
- **Metrics:** Broadcast latency (server → dashboard), messages received

#### AnalyticsUser (×1, periodic)
- **Request:** `GET /api/analytics/summary` with Admin JWT
- **Frequency:** Every 30 seconds during test
- **Metrics:** HTTP response latency, payload size

---

## 3. Test Data

### 3.1 Seeded Dataset

Re-use and extend `backend/scripts/seed_perf.py`:

```python
# Current: 365 days × 10 sessions/day = 3,650 sessions
# Target:  365 days × 100 sessions/day = 36,500 sessions
```

The script creates:
- 2 zones (Standard, Gaming)
- 8 seats (4 per zone)
- 5 menu items
- 3 members (Bronze, Silver, Gold)
- GamingSession + Invoice + SessionPOSItem (+ occasional Reservation) per session

### 3.2 Agent Secrets

The test generates 50 unique `agent_secret` values (matching `secrets.token_hex(32)` format) and pre-configures seats 1–50 in the database with these secrets before the Locust run starts.

---

## 4. Metrics & Pass Criteria

### 4.1 Real-Time Metrics (Collected During Locust Run)

| Metric | Source | Collection | Pass Threshold |
|--------|--------|------------|----------------|
| Broadcast latency (P99) | DashboardUser | `receive_ts - server_ts` per message | < 1,000ms |
| HEALTH round-trip (P99) | AgentUser | `send_ts → ack_ts` | < 500ms |
| Server CPU (avg) | MetricsCollector | `psutil.Process().cpu_percent(interval=None)` every 5s (time-average of process CPU %) | < 80% |
| Server memory (RSS) | MetricsCollector | `psutil.Process().memory_info().rss` every 5s | No leak (stable) |
| Messages dropped | AgentUser + DashboardUser | Count send/exceptions | 0 |
| WebSocket connections | Locust stats | Active connections at steady state | 50 agents + 3 dashboards |

### 4.2 Analytics Query Metrics

| Metric | Source | Pass Threshold |
|--------|--------|----------------|
| `GET /api/analytics/summary` latency (P99) | AnalyticsUser | < 2,000ms |

---

## 5. Implementation Files

```
backend/
├── tests/
│   ├── load/
│   │   ├── __init__.py
│   │   ├── locustfile.py              # Locust User classes + test orchestration
│   │   ├── metrics_collector.py       # Background CPU/memory sampler
│   │   ├── conftest.py                # Pytest fixtures for seeding (if run via pytest)
│   │   ├── seed_load_test.py          # One-time seed script for 50 seats + secrets
│   │   └── README.md                  # Run instructions
│   └── integration/
│       └── test_ac02_api_performance.py  # Add analytics perf test here
├── scripts/
│   └── seed_perf.py                   # Update: sessions_per_day=100
```

### 5.1 Key Dependencies (Add to `backend/requirements-dev.txt`)

```
locust==2.32.0
psutil==6.0.0
websockets==13.0
```

---

## 6. Running the Tests

### 6.1 One-Time Setup

```bash
cd backend

# 1. Install load test dependencies
pip install -r requirements-dev.txt

# 2. Seed the performance dataset (365 days × 100 sessions/day)
python -m scripts.seed_perf

# 3. Seed 50 agent seats with secrets for load test
python -m tests.load.seed_load_test
```

### 6.2 Execute Load Test

**Terminal 1 — Start Server:**
```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --ws-max-size 5242880
```

**Terminal 2 — Run Locust (Headless, 60s):**
```bash
cd backend/tests/load
locust -f locustfile.py --headless -u 54 -r 10 --run-time 60s --host http://localhost:8000
```

- `-u 54` = 50 agents + 3 dashboards + 1 analytics user
- `-r 10` = spawn rate 10 users/second
- `--run-time 60s` = sustained load for 60 seconds

### 6.3 CI Integration (Future)

Add a GitHub Actions job that:
1. Starts uvicorn in background
2. Runs Locust headless
3. Fails if pass criteria not met
4. Uploads Locust HTML report as artifact

---

## 7. Acceptance Criteria

| ID | Criterion | Verification |
|----|-----------|--------------|
| LT-01 | 50 agents connect, send HEALTH every 60s, receive PING/PONG | Locust stats: 50 agent connections established, 0 failures |
| LT-02 | 3 dashboards receive seat_updated broadcasts | Broadcast latency P99 < 1s (NFR-PERF-001) |
| LT-03 | Server CPU < 80% average during 60s sustained load | MetricsCollector avg CPU < 80% (NFR-PERF-003) |
| LT-04 | Zero messages dropped (send failures, timeouts) | Locust failure count = 0 |
| LT-05 | Analytics query < 2s on 36,500-session dataset | AnalyticsUser P99 < 2,000ms (NFR-PERF-002) |
| LT-06 | Memory stable (no unbounded growth) | RSS delta < 50MB over test duration (heuristic for "no leak"; `psutil.Process().memory_info().rss` start vs end) |

---

## 8. Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| WebSocket connection exhaustion (OS/file descriptor limits) | Test cannot reach 50 connections | Set `ulimit -n 65535`; use `uvicorn --ws-max-size` appropriately |
| SQLite contention under 50 concurrent writers | DB locked errors | WAL mode + `busy_timeout=5000` already configured; broadcast path is read-heavy |
| `seed_perf.py` runtime too long (36,500 sessions) | Setup delay | Script uses batched flushes; ~30s expected. Can pre-seed in CI cache. |
| Locust WebSocket support limitations | Cannot track per-message latency | Use `websockets` library directly in custom User classes for precise timing |

---

## 9. Future Extensions

- **Soak test:** 4-hour run to detect memory leaks
- **Chaos test:** Kill/restart server mid-load, verify agent reconnection + SYNC
- **Scale test:** Ramp to 100 agents (2× NFR) to find breaking point
- **Dashboard UI test:** Playwright load test for frontend rendering under 50 seats

---

## 10. Approval

**Designed by:** Claude Code (brainstorming session)
**Reviewed by:** [Pending user review]
**Approved:** [Pending]

---
*This spec will be committed to git. Implementation proceeds via `writing-plans` skill after approval.*

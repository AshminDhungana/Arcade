# Load Tests (Feature 8.1.2)

Validates NFR-PERF-001, NFR-PERF-002, NFR-PERF-003 using Locust.

## Prerequisites

```bash
cd backend
pip install -r requirements-dev.txt
python -m scripts.seed_perf      # Seeds 365 days × 100 sessions = 36,500 sessions
python -m tests.load.seed_load_test  # Creates 50 seats with agent secrets
```

## Running

**Terminal 1 — Start Server:**
```bash
uvicorn backend.main:app --host 0.0.0.0 --port 8000 --ws-max-size 5242880
```

**Terminal 2 — Run Locust (Headless, 60s):**
```bash
cd backend/tests/load
export AGENT_SECRETS="$(python -c 'import secrets; print(",".join(secrets.token_hex(32) for _ in range(50)))')"
locust -f locustfile.py --headless -u 54 -r 10 --run-time 60s --host ws://localhost:8000
```

- `-u 54` = 50 AgentUser + 3 DashboardUser + 1 AnalyticsUser
- `-r 10` = spawn rate 10 users/second
- `--run-time 60s` = sustained load for 60 seconds

## Pass Criteria

Exit code 0 = PASS, 1 = FAIL. Checks:
- Agent HEALTH round-trip P99 < 500ms
- Dashboard broadcast P99 < 1000ms (NFR-PERF-001)
- Zero message drops
- Analytics query P99 < 2000ms (NFR-PERF-002)
- Server CPU < 80% average (sampled via MetricsCollector, NFR-PERF-003)

## CI Integration

Add to `.github/workflows/ci.yml`:

```yaml
- name: Load Test
  run: |
    uvicorn backend.main:app --host 0.0.0.0 --port 8000 &
    sleep 5
    cd backend/tests/load
    export AGENT_SECRETS=$(python -c 'import secrets; print(",".join(secrets.token_hex(32) for _ in range(50)))')
    locust -f locustfile.py --headless -u 54 -r 10 --run-time 60s --host ws://localhost:8000
```

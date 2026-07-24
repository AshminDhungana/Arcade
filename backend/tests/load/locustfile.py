"""Locust load test for 50 WebSocket agents + 3 dashboards + analytics."""

import asyncio
import json
import os
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime

import websockets
from locust import User, events, task
from locust.env import Environment

# Configuration
HOST = os.getenv("LOCUST_HOST", "ws://localhost:8000")
SEAT_IDS = [f"Load-{i:03d}" for i in range(1, 51)]


# ---- Message builders ----
def ws_envelope(type_: str, payload: dict) -> str:
    return json.dumps(
        {"type": type_, "payload": payload, "timestamp": datetime.now(UTC).isoformat()}
    )


def register_msg(seat_id: str, secret: str) -> str:
    return ws_envelope(
        "REGISTER",
        {
            "seat_id": seat_id,
            "mac_address": f"02:00:00:00:{int(seat_id.split('-')[1]):02x}:00",
            "hostname": f"load-agent-{seat_id}",
            "agent_secret": secret,
        },
    )


def health_msg(seat_id: str) -> str:
    return ws_envelope(
        "HEALTH",
        {
            "seat_id": seat_id,
            "cpu_pct": 25.0,
            "ram_pct": 45.0,
            "cpu_temp": 55.0,
            "disk_used_gb": 100.0,
            "disk_total_gb": 500.0,
        },
    )


def pong_msg() -> str:
    return ws_envelope("PONG", {})


# ---- Metrics tracking ----
@dataclass
class LatencyTracker:
    latencies_ms: list[float] = field(default_factory=list)
    drops: int = 0
    connects: int = 0

    def record(self, ms: float) -> None:
        self.latencies_ms.append(ms)

    def p99(self) -> float:
        if not self.latencies_ms:
            return 0.0
        sorted_lat = sorted(self.latencies_ms)
        idx = int(len(sorted_lat) * 0.99)
        return sorted_lat[idx]


# Global trackers
agent_latencies = LatencyTracker()  # HEALTH round-trip
dashboard_latencies = LatencyTracker()  # broadcast delivery
analytics_latencies = LatencyTracker()  # HTTP analytics query


# ---- AgentUser ----
class AgentUser(User):
    """Simulates one agent: REGISTER -> HEALTH every 60s -> PING/PONG"""

    def wait_time(self):
        return 1

    def __init__(self, env: Environment):
        super().__init__(env)
        self.seat_id: str | None = None
        self.secret: str | None = None
        self.ws: websockets.WebSocketClientProtocol | None = None
        self._running = False

    def on_start(self):
        idx = sum(1 for u in self.environment.runner.users if isinstance(u, AgentUser))
        if idx >= len(SEAT_IDS):
            self.environment.runner.quit()
            return
        self.seat_id = SEAT_IDS[idx]
        secrets_env = os.getenv("AGENT_SECRETS", "")
        if secrets_env:
            self.secret = secrets_env.split(",")[idx]
        else:
            self.secret = f"test-secret-{self.seat_id}"
        self._running = True
        asyncio.create_task(self._run_agent())

    async def _run_agent(self):
        url = f"{HOST}/ws/agent/{self.seat_id}?secret={self.secret}"
        try:
            async with websockets.connect(url, max_size=5_242_880) as ws:
                self.ws = ws
                agent_latencies.connects += 1

                # REGISTER
                await ws.send(register_msg(self.seat_id, self.secret))
                await ws.recv()  # Expect REGISTERED

                # Main loop
                last_health = 0
                while self._running:
                    now = time.time()

                    # HEALTH every 60s
                    if now - last_health >= 60:
                        start = time.perf_counter()
                        await ws.send(health_msg(self.seat_id))
                        await asyncio.wait_for(ws.recv(), timeout=5.0)
                        latency = (time.perf_counter() - start) * 1000
                        agent_latencies.record(latency)
                        last_health = now

                    # Handle incoming (PING, broadcasts)
                    try:
                        msg = await asyncio.wait_for(ws.recv(), timeout=1.0)
                        data = json.loads(msg)
                        if data.get("type") == "PING":
                            await ws.send(pong_msg())
                    except TimeoutError:
                        pass
        except Exception as e:
            agent_latencies.drops += 1
            self.environment.events.request.fire(
                request_type="WS",
                name="agent_error",
                response_time=0,
                response_length=0,
                exception=e,
            )
        finally:
            agent_latencies.connects += 1  # count disconnect as event

    def on_stop(self):
        self._running = False


# ---- DashboardUser ----
class DashboardUser(User):
    """Simulates dashboard: connects to /ws/dashboard, receives broadcasts"""

    def wait_time(self):
        return 10

    def __init__(self, env: Environment):
        super().__init__(env)
        self.ws: websockets.WebSocketClientProtocol | None = None
        self._running = False

    def on_start(self):
        self._running = True
        asyncio.create_task(self._run_dashboard())

    async def _run_dashboard(self):
        url = f"{HOST}/ws/dashboard"
        try:
            async with websockets.connect(url, max_size=5_242_880) as ws:
                self.ws = ws
                dashboard_latencies.connects += 1
                while self._running:
                    try:
                        msg = await asyncio.wait_for(ws.recv(), timeout=30.0)
                        data = json.loads(msg)
                        if "timestamp" in data:
                            server_ts = datetime.fromisoformat(
                                data["timestamp"].replace("Z", "+00:00")
                            )
                            recv_ts = datetime.now(UTC)
                            latency = (recv_ts - server_ts).total_seconds() * 1000
                            dashboard_latencies.record(latency)
                    except TimeoutError:
                        pass
        except Exception as e:
            dashboard_latencies.drops += 1
            self.environment.events.request.fire(
                request_type="WS",
                name="dash_error",
                response_time=0,
                response_length=0,
                exception=e,
            )
        finally:
            dashboard_latencies.connects += 1

    def on_stop(self):
        self._running = False


# ---- AnalyticsUser ----
class AnalyticsUser(User):
    """Periodic HTTP GET /api/analytics/summary"""

    def wait_time(self):
        return 30

    def __init__(self, env: Environment):
        super().__init__(env)
        self._token: str | None = None

    def on_start(self):
        import httpx

        base = HOST.replace("ws://", "http://")
        client = httpx.Client(base_url=base)
        resp = client.post("/api/auth/login", json={"staff_id": "admin", "pin": "1234"})
        if resp.status_code == 200:
            self._token = resp.json()["access_token"]

    @task
    def get_analytics(self):
        if not self._token:
            analytics_latencies.drops += 1
            return
        import httpx

        base = HOST.replace("ws://", "http://")
        client = httpx.Client(
            base_url=base, headers={"Authorization": f"Bearer {self._token}"}
        )
        start = time.perf_counter()
        try:
            resp = client.get("/api/analytics/summary", timeout=10.0)
            latency = (time.perf_counter() - start) * 1000
            if resp.status_code == 200:
                analytics_latencies.record(latency)
            else:
                analytics_latencies.drops += 1
        except Exception:
            analytics_latencies.drops += 1


# ---- Test orchestration ----
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    print(f"Loaded {len(SEAT_IDS)} seat IDs")
    secrets = os.getenv("AGENT_SECRETS")
    if secrets:
        print(f"Using {len(secrets.split(','))} agent secrets from env")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    print("\n=== LOAD TEST RESULTS ===")
    print(f"Agent HEALTH P99 latency: {agent_latencies.p99():.1f}ms")
    print(f"Agent connects: {agent_latencies.connects}, drops: {agent_latencies.drops}")
    print(f"Dashboard broadcast P99 latency: {dashboard_latencies.p99():.1f}ms")
    print(
        "Dashboard connects: "
        f"{dashboard_latencies.connects}, drops: {dashboard_latencies.drops}"
    )

    # Analytics
    if analytics_latencies.latencies_ms:
        p99 = analytics_latencies.p99()
        print(f"Analytics P99 latency: {p99:.1f}ms")
        if p99 > 2000:
            print("FAIL: Analytics P99 > 2000ms (NFR-PERF-002)")
    else:
        print("Analytics: no samples")
        analytics_latencies.drops = 1  # fail if no data

    # Pass/fail
    passed = True
    if agent_latencies.p99() > 500:
        print("FAIL: Agent HEALTH P99 > 500ms")
        passed = False
    if dashboard_latencies.p99() > 1000:
        print("FAIL: Dashboard broadcast P99 > 1000ms (NFR-PERF-001)")
        passed = False
    if agent_latencies.drops > 0 or dashboard_latencies.drops > 0:
        print("FAIL: Messages dropped")
        passed = False
    if analytics_latencies.drops > 0 or (
        analytics_latencies.latencies_ms and analytics_latencies.p99() > 2000
    ):
        print("FAIL: Analytics P99 > 2000ms or drops (NFR-PERF-002)")
        passed = False

    # CPU check would be done by external MetricsCollector
    print(f"OVERALL: {'PASS' if passed else 'FAIL'}")
    os._exit(0 if passed else 1)

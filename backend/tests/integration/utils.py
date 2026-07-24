"""Shared test utilities for integration tests."""

import asyncio
import time
from typing import Any


def auth_headers(
    staff_id: str = "test-staff-id", role: str = "CASHIER", token_version: int = 0
) -> dict[str, str]:
    """Generate valid Bearer token headers using real create_access_token."""
    from backend.core.security import create_access_token

    token = create_access_token(staff_id, role, token_version)
    return {"Authorization": f"Bearer {token}"}


class MockWebSocketManager:
    """Lightweight WS manager mock for testing command delivery without real sockets."""

    def __init__(self):
        self.sent_messages: list[dict[str, Any]] = []
        self.agent_connected: dict[str, bool] = {}

    async def send_to_agent(self, seat_id: str, message: dict) -> None:
        if not self.agent_connected.get(seat_id):
            from backend.services.remote_command_service import AgentOfflineHttpError

            raise AgentOfflineHttpError(seat_id)
        self.sent_messages.append({"seat_id": seat_id, "message": message})

    async def broadcast_to_dashboards(self, event: str, data: dict) -> None:
        self.sent_messages.append(
            {"event": event, "data": data, "target": "dashboards"}
        )

    def get_last_message_to_agent(self, seat_id: str, msg_type: str) -> dict | None:
        for msg in reversed(self.sent_messages):
            if msg.get("seat_id") == seat_id and msg["message"].get("type") == msg_type:
                return msg["message"]
        return None


class TimingCapture:
    """Capture timestamps for latency measurements."""

    def __init__(self):
        self.marks: dict[str, float] = {}

    def mark(self, name: str) -> None:
        self.marks[name] = time.perf_counter()

    def elapsed_ms(self, start: str, end: str) -> float:
        return (self.marks[end] - self.marks[start]) * 1000


async def wait_for_condition(coro, timeout: float = 5.0, interval: float = 0.1):
    """Poll an async condition until true or timeout."""
    start = time.monotonic()
    while time.monotonic() - start < timeout:
        result = coro()
        if asyncio.iscoroutine(result):
            result = await result
        if result:
            return
        await asyncio.sleep(interval)
    raise TimeoutError(f"Condition not met within {timeout}s")


async def seed_minimal_analytics_data(db):
    """Seed minimal data for analytics summary endpoint."""
    from backend.models import PricingModel, Zone
    from backend.repositories import seat_repo

    zone = Zone(
        name="Test Zone",
        rate_per_minute_paise=100,
        rate_per_hour_paise=5000,
        pricing_model=PricingModel.PER_MINUTE,
    )
    db.add(zone)
    await db.flush()
    await seat_repo.create(db, name="PC-01", zone_id=zone.id)
    await db.commit()

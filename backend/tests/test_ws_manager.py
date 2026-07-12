"""Tests for backend.core.ws_manager.

Covers: message envelope, reconciliation, registries, heartbeat,
agent message dispatch, and WebSocket endpoint wiring.
"""

from __future__ import annotations

import asyncio
import json as _json
from datetime import UTC, datetime
from typing import Any, cast

import pytest

from backend.core.ws_manager import (
    HEARTBEAT_INTERVAL,
    HEARTBEAT_TIMEOUT,
    MAX_MESSAGE_SIZE,
    AgentOfflineError,
    ReconcileResult,
    WebSocketManager,
    reconcile,
    server_anchor_elapsed,
    ws_envelope,
)

# ---------------------------------------------------------------------------
# Protocol helpers (Task 1)
# ---------------------------------------------------------------------------


class TestWsEnvelope:
    def test_returns_dict_with_type_payload_and_timestamp(self) -> None:
        result = ws_envelope("seat_updated", {"seat_id": "s1", "status": "IN_USE"})
        assert result["type"] == "seat_updated"
        assert result["payload"] == {"seat_id": "s1", "status": "IN_USE"}
        assert "timestamp" in result
        # Timestamp must parse as ISO 8601 (contains T and timezone info)
        assert "T" in result["timestamp"]

    def test_constants_exist(self) -> None:
        assert HEARTBEAT_INTERVAL == 30.0
        assert HEARTBEAT_TIMEOUT == 10.0
        assert MAX_MESSAGE_SIZE == 5 * 1024 * 1024


class TestReconcileResult:
    def test_dataclass_fields(self) -> None:
        result = ReconcileResult(
            chosen_elapsed_seconds=60.0,
            drift=2.0,
            action="ACCEPT_SAE",
            reason="within tolerance",
            tolerance_seconds=5.0,
        )
        assert result.chosen_elapsed_seconds == 60.0
        assert result.drift == 2.0
        assert result.action == "ACCEPT_SAE"
        assert result.reason == "within tolerance"
        assert result.tolerance_seconds == 5.0


class TestReconcile:
    def test_accepts_sae_when_within_tolerance(self) -> None:
        result = reconcile(sae_seconds=60.0, ale_seconds=62.0, tolerance=5.0)
        assert result.action == "ACCEPT_SAE"
        assert result.chosen_elapsed_seconds == 60.0
        assert result.drift == -2.0

    def test_adopts_ale_when_agent_is_much_lower(self) -> None:
        result = reconcile(sae_seconds=60.0, ale_seconds=10.0, tolerance=5.0)
        assert result.action == "ADOPT_ALE"
        assert result.chosen_elapsed_seconds == 10.0

    def test_adopts_ale_when_agent_is_much_higher(self) -> None:
        result = reconcile(sae_seconds=60.0, ale_seconds=80.0, tolerance=5.0)
        assert result.action == "ADOPT_ALE"
        assert result.chosen_elapsed_seconds == 80.0

    def test_exact_tolerance_boundary(self) -> None:
        result = reconcile(sae_seconds=60.0, ale_seconds=65.0, tolerance=5.0)
        assert result.action == "ACCEPT_SAE"
        result2 = reconcile(sae_seconds=60.0, ale_seconds=65.1, tolerance=5.0)
        assert result2.action == "ADOPT_ALE"


class TestServerAnchorElapsed:
    def test_basic(self) -> None:
        started = datetime(2026, 6, 1, 10, 0, 0, tzinfo=UTC)
        now = datetime(2026, 6, 1, 10, 5, 0, tzinfo=UTC)
        result = server_anchor_elapsed(started, 0.0, now)
        assert result == pytest.approx(300.0)

    def test_with_pause(self) -> None:
        started = datetime(2026, 6, 1, 10, 0, 0, tzinfo=UTC)
        now = datetime(2026, 6, 1, 10, 5, 0, tzinfo=UTC)
        result = server_anchor_elapsed(started, 60.0, now)
        assert result == pytest.approx(240.0)

    def test_negative_result_clamped_to_zero(self) -> None:
        started = datetime(2026, 6, 1, 10, 0, 0, tzinfo=UTC)
        now = datetime(2026, 6, 1, 10, 2, 0, tzinfo=UTC)
        # More paused time than elapsed -> result should be 0
        result = server_anchor_elapsed(started, 300.0, now)
        assert result == 0.0


# ---------------------------------------------------------------------------
# Fake WebSocket for unit tests (shared fixture)  (Task 2)
# ---------------------------------------------------------------------------


class FakeWebSocket:
    """Stand-in for fastapi.WebSocket that records outbound messages."""

    def __init__(self) -> None:
        self.sent_messages: list[dict[str, Any]] = []
        self.is_closed = False
        self.close_code: int | None = None
        self.close_reason: str = ""
        self._accept_called = False

    async def accept(self) -> None:
        self._accept_called = True

    async def receive_text(self) -> str:
        return ""

    async def receive_json(self) -> dict[str, Any]:
        return cast(dict[str, Any], _json.loads(await self.receive_text()))

    async def send_text(self, text: str) -> None:
        self.sent_messages.append(_json.loads(text))

    async def send_json(self, data: dict[str, Any]) -> None:
        self.sent_messages.append(data)

    async def close(self, code: int = 1000, reason: str = "") -> None:
        self.is_closed = True
        self.close_code = code
        self.close_reason = reason


def _fake_ws() -> Any:
    """Return a FakeWebSocket typed as ``Any`` to bypass WebSocket[State] strictness."""
    return FakeWebSocket()


@pytest.fixture
def mock_config(monkeypatch):  # type: ignore[no-untyped-def]
    """Temporarily replace get_config to return a config with known agent secrets."""
    from backend.core.config import Settings

    fake_config = Settings.model_validate(
        {
            "jwt_secret": "a" * 64,
            "agent_secrets": {
                "seat_001": "secret_001",
                "seat_002": "secret_002",
            },
        }
    )
    monkeypatch.setattr("backend.core.ws_manager.get_config", lambda: fake_config)
    return fake_config


# ---------------------------------------------------------------------------
# Dashboard registry (Task 2)
# ---------------------------------------------------------------------------


class TestDashboardRegistry:
    async def test_connect_dashboard_adds_to_registry(  # type: ignore[no-untyped-def]
        self,
        mock_config,  # noqa: ARG002
    ) -> None:
        mgr = WebSocketManager()
        ws = _fake_ws()
        await mgr.connect_dashboard(ws)
        assert ws in mgr.dashboard_connections

    async def test_disconnect_dashboard_removes_from_registry(  # type: ignore[no-untyped-def]
        self,
        mock_config,  # noqa: ARG002
    ) -> None:
        mgr = WebSocketManager()
        ws = _fake_ws()
        await mgr.connect_dashboard(ws)
        await mgr.disconnect_dashboard(ws)
        assert ws not in mgr.dashboard_connections


# ---------------------------------------------------------------------------
# Agent registry (Task 2)
# ---------------------------------------------------------------------------


class TestAgentRegistry:
    async def test_connect_agent_valid_secret_accepts(  # type: ignore[no-untyped-def]
        self,
        mock_config,  # noqa: ARG002
    ) -> None:
        mgr = WebSocketManager()
        ws = _fake_ws()
        ok = await mgr.connect_agent("seat_001", "secret_001", ws)
        assert ok is True
        assert "seat_001" in mgr.agent_connections
        assert mgr.agent_connections["seat_001"] is ws

    async def test_connect_agent_invalid_secret_rejects(  # type: ignore[no-untyped-def]
        self,
        mock_config,  # noqa: ARG002
    ) -> None:
        mgr = WebSocketManager()
        ws = _fake_ws()
        ok = await mgr.connect_agent("seat_001", "wrong_secret", ws)
        assert ok is False
        assert ws.is_closed
        assert "seat_001" not in mgr.agent_connections

    async def test_connect_agent_unknown_seat_rejects(  # type: ignore[no-untyped-def]
        self,
        mock_config,  # noqa: ARG002
    ) -> None:
        mgr = WebSocketManager()
        ws = _fake_ws()
        ok = await mgr.connect_agent("seat_999", "anything", ws)
        assert ok is False

    async def test_disconnect_agent_removes(  # type: ignore[no-untyped-def]
        self,
        mock_config,  # noqa: ARG002
    ) -> None:
        mgr = WebSocketManager()
        ws = _fake_ws()
        await mgr.connect_agent("seat_001", "secret_001", ws)
        await mgr.disconnect_agent("seat_001")
        assert "seat_001" not in mgr.agent_connections


# ---------------------------------------------------------------------------
# Send and broadcast (Task 2)
# ---------------------------------------------------------------------------


class TestSendAndBroadcast:
    async def test_send_to_agent_delivers_message(  # type: ignore[no-untyped-def]
        self,
        mock_config,  # noqa: ARG002
    ) -> None:
        mgr = WebSocketManager()
        ws = _fake_ws()
        await mgr.connect_agent("seat_001", "secret_001", ws)
        await mgr.send_to_agent("seat_001", {"type": "HIDE_OVERLAY", "payload": {}})
        assert any(msg.get("type") == "HIDE_OVERLAY" for msg in ws.sent_messages)

    async def test_send_to_agent_offline_raises_error(  # type: ignore[no-untyped-def]
        self,
        mock_config,  # noqa: ARG002
    ) -> None:
        mgr = WebSocketManager()
        with pytest.raises(AgentOfflineError):
            await mgr.send_to_agent("seat_001", {"type": "SHOW_OVERLAY", "payload": {}})

    async def test_broadcast_to_dashboards_sends_to_all(  # type: ignore[no-untyped-def]
        self,
        mock_config,  # noqa: ARG002
    ) -> None:
        mgr = WebSocketManager()
        ws1 = _fake_ws()
        ws2 = _fake_ws()
        await mgr.connect_dashboard(ws1)
        await mgr.connect_dashboard(ws2)
        await mgr.broadcast_to_dashboards(
            "seat_updated", {"seat_id": "s1", "status": "IN_USE"}
        )
        assert any(msg.get("type") == "seat_updated" for msg in ws1.sent_messages)
        assert any(msg.get("type") == "seat_updated" for msg in ws2.sent_messages)

    async def test_broadcast_skips_disconnected_dashboards(  # type: ignore[no-untyped-def]
        self,
        mock_config,  # noqa: ARG002
    ) -> None:
        mgr = WebSocketManager()
        ws1 = _fake_ws()
        ws2 = _fake_ws()
        await mgr.connect_dashboard(ws1)
        await mgr.connect_dashboard(ws2)
        # Disconnect ws2
        mgr.dashboard_connections.remove(ws2)
        await mgr.broadcast_to_dashboards("test_event", {"data": 1})
        assert any(msg.get("type") == "test_event" for msg in ws1.sent_messages)


# ---------------------------------------------------------------------------
# Heartbeat (Task 3)
# ---------------------------------------------------------------------------


class TestHeartbeat:
    async def test_heartbeat_sends_ping_after_interval(  # type: ignore[no-untyped-def]
        self,
        mock_config,  # noqa: ARG002
    ) -> None:
        """After HEARTBEAT_INTERVAL, the manager sends PING to all agents."""
        mgr = WebSocketManager()
        # Patch the interval to something tiny for test speed
        import backend.core.ws_manager as _ws

        old_interval = _ws.HEARTBEAT_INTERVAL
        _ws.HEARTBEAT_INTERVAL = 0.05  # 50 ms
        try:
            ws = _fake_ws()
            await mgr.connect_agent("seat_001", "secret_001", ws)
            # Wait for two heartbeat intervals
            await asyncio.sleep(0.12)
            assert any(msg.get("type") == "PING" for msg in ws.sent_messages)
        finally:
            _ws.HEARTBEAT_INTERVAL = old_interval
            await mgr.close_all()

    async def test_pong_clears_pending_state(  # type: ignore[no-untyped-def]
        self,
        mock_config,  # noqa: ARG002
    ) -> None:
        mgr = WebSocketManager()
        ws = _fake_ws()
        await mgr.connect_agent("seat_001", "secret_001", ws)
        # Simulate receiving a PONG
        await mgr.handle_pong("seat_001")
        assert "seat_001" not in mgr._pending_pongs

    async def test_missing_pong_disconnects_agent(  # type: ignore[no-untyped-def]
        self,
        mock_config,  # noqa: ARG002
    ) -> None:
        """An agent that never responds to PING is disconnected next tick."""
        mgr = WebSocketManager()
        # Speed up heartbeat
        import backend.core.ws_manager as _ws

        old_interval = _ws.HEARTBEAT_INTERVAL
        _ws.HEARTBEAT_INTERVAL = 0.03
        try:
            ws = _fake_ws()
            await mgr.connect_agent("seat_001", "secret_001", ws)
            # Wait for two ticks (first tick sends PING, second tick detects no PONG)
            await asyncio.sleep(0.08)
            # Agent should have been closed
            assert ws.is_closed
            assert "seat_001" not in mgr.agent_connections
        finally:
            _ws.HEARTBEAT_INTERVAL = old_interval
            await mgr.close_all()


# ---------------------------------------------------------------------------
# Agent message handlers (Task 4)
# ---------------------------------------------------------------------------


class TestAgentHandlers:
    async def test_handle_register(self, mock_config):  # type: ignore[no-untyped-def]
        del mock_config
        mgr = WebSocketManager()
        result = await mgr.handle_agent_message(
            "seat_001",
            {
                "type": "REGISTER",
                "payload": {
                    "seat_id": "seat_001",
                    "mac_address": "aa:bb:cc:dd:ee:ff",
                    "hostname": "test-pc",
                },
            },
        )
        assert result.get("type") == "REGISTERED"

    async def test_handle_health_broadcasts_to_dashboards(self, mock_config):  # type: ignore[no-untyped-def]
        del mock_config
        mgr = WebSocketManager()
        dash = _fake_ws()
        await mgr.connect_dashboard(dash)
        await mgr.handle_agent_message(
            "seat_001",
            {
                "type": "HEALTH",
                "payload": {"cpu_percent": 45.0, "ram_percent": 60.0},
            },
        )
        assert any(msg.get("type") == "health_update" for msg in dash.sent_messages)

    async def test_handle_staff_override_broadcasts_alert(self, mock_config):  # type: ignore[no-untyped-def]
        del mock_config
        mgr = WebSocketManager()
        dash = _fake_ws()
        await mgr.connect_dashboard(dash)
        await mgr.handle_agent_message(
            "seat_001",
            {
                "type": "STAFF_OVERRIDE",
                "payload": {"staff_id": "s001"},
            },
        )
        assert any(msg.get("type") == "alert" for msg in dash.sent_messages)

    async def test_handle_pong_response(self, mock_config):  # type: ignore[no-untyped-def]
        del mock_config
        mgr = WebSocketManager()
        mgr._pending_pongs.add("seat_001")
        await mgr.handle_pong("seat_001")
        assert "seat_001" not in mgr._pending_pongs


# ---------------------------------------------------------------------------
# WebSocket endpoints (Task 5)
# ---------------------------------------------------------------------------


# --- Screenshot response correlation ---------------------------------


async def test_wait_for_screenshot_resolves_on_result() -> None:
    """A registered waiter future resolves when resolve_screenshot is called."""
    mgr = WebSocketManager()
    fut = asyncio.get_event_loop().create_future()
    async with mgr._screenshot_lock:
        mgr._screenshot_waiters["req-1"] = fut
        mgr._screenshot_seat["req-1"] = "seat_001"
    await mgr.resolve_screenshot("req-1", b"\xff\xd8\xff\xff\xd9")
    assert fut.done()
    assert fut.result() == b"\xff\xd8\xff\xff\xd9"


async def test_wait_for_screenshot_unknown_id_noop() -> None:
    """Resolving an unknown request_id does not raise and drops nothing."""
    mgr = WebSocketManager()
    # Must not raise
    await mgr.resolve_screenshot("ghost", b"data")


async def test_disconnect_cancels_pending_screenshot() -> None:
    """disconnect_agent cancels any pending screenshot future for that seat."""
    mgr = WebSocketManager()
    fut = asyncio.get_event_loop().create_future()
    async with mgr._screenshot_lock:
        mgr._screenshot_waiters["req-2"] = fut
        mgr._screenshot_seat["req-2"] = "seat_001"
    await mgr.disconnect_agent("seat_001")
    assert fut.cancelled()
    async with mgr._screenshot_lock:
        assert "req-2" not in mgr._screenshot_waiters

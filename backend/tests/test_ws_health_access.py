import asyncio

from backend.core.ws_manager import WebSocketManager


def test_health_received_at_tracked() -> None:
    async def go() -> None:
        m = WebSocketManager()
        await m._handle_health("seat-1", {"cpu_temp": 70.0})
        assert m.all_health_data() == {"seat-1": {"cpu_temp": 70.0}}
        recv = m.health_received_at_map()
        assert "seat-1" in recv
        assert recv["seat-1"].tzinfo is not None  # stored in UTC

    asyncio.run(go())


def test_health_tracks_all_metric_fields() -> None:
    async def go() -> None:
        m = WebSocketManager()
        payload = {
            "cpu_percent": 42,
            "ram_percent": 67,
            "cpu_temp_celsius": 71.5,
            "disk_used_gb": 120,
            "disk_total_gb": 512,
        }
        await m._handle_health("seat-2", payload)
        data = m.all_health_data()["seat-2"]
        assert data["cpu_percent"] == 42
        assert data["ram_percent"] == 67
        assert data["cpu_temp_celsius"] == 71.5
        assert data["disk_used_gb"] == 120
        assert data["disk_total_gb"] == 512
        recv = m.health_received_at_map()
        assert "seat-2" in recv
        assert recv["seat-2"].tzinfo is not None  # stored in UTC

    asyncio.run(go())

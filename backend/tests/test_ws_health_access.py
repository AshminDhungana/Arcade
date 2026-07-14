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

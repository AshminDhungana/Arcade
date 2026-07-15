# backend/tests/test_ws_secret_db.py
import pytest

from backend.core.database import AsyncSessionLocal
from backend.core.ws_manager import WebSocketManager
from backend.models.seat import Seat


@pytest.mark.asyncio
async def test_connect_rejects_unknown_secret(monkeypatch):
    # A minimal fake WebSocket that records close code/reason.
    class FakeWS:
        def __init__(self):
            self.closed = None
            self.accepted = False

        async def accept(self):
            self.accepted = True

        async def close(self, code=None, reason=None):
            self.closed = (code, reason)

    async with AsyncSessionLocal() as db:
        db.add(Seat(id="seat_ws", name="seat_ws", zone_id="z1", agent_secret="right"))
        await db.commit()

    mgr = WebSocketManager()
    ws = FakeWS()
    ok = await mgr.connect_agent("seat_ws", "wrong", ws)
    assert ok is False
    assert ws.closed[0] == 1008

    ws2 = FakeWS()
    ok2 = await mgr.connect_agent("seat_ws", "right", ws2)
    assert ok2 is True and ws2.accepted is True

# backend/tests/test_ws_secret_db.py
import uuid

import pytest

from backend.core.database import AsyncSessionLocal
from backend.core.ws_manager import WebSocketManager
from backend.models import Seat, Zone
from backend.models._enums import PricingModel

pytestmark = pytest.mark.asyncio


async def _ensure_zone_z1() -> None:
    """Make sure the FK target zone ``z1`` exists in the (persistent) test DB.

    Inserted via the ORM so model defaults (``created_at``/``updated_at``) and
    any future columns are applied automatically — the schema is always current
    thanks to the session-scoped ``_reset_test_schema`` fixture in conftest.
    """
    async with AsyncSessionLocal() as db:
        if await db.get(Zone, "z1") is None:
            db.add(
                Zone(
                    id="z1",
                    name="Test Zone",
                    rate_per_minute_paise=1,
                    rate_per_hour_paise=60,
                    pricing_model=PricingModel.PER_MINUTE,
                    block_minutes=15,
                )
            )
            await db.commit()


@pytest.mark.asyncio
async def test_connect_rejects_unknown_secret():
    # A minimal fake WebSocket that records close code/reason.
    class FakeWS:
        def __init__(self):
            self.closed = None
            self.accepted = False

        async def accept(self):
            self.accepted = True

        async def close(self, code=None, reason=None):
            self.closed = (code, reason)

    # Unique seat id per run so a leftover row from a prior (crashed) run
    # cannot raise UNIQUE constraint failed on rerun.
    seat_id = f"seat_ws_{uuid.uuid4().hex[:12]}"
    async with AsyncSessionLocal() as db:
        await _ensure_zone_z1()
        db.add(Seat(id=seat_id, name=seat_id, zone_id="z1", agent_secret="right"))
        await db.commit()

    mgr = WebSocketManager()
    try:
        ws = FakeWS()
        ok = await mgr.connect_agent(seat_id, "wrong", ws)
        assert ok is False
        assert ws.closed[0] == 1008

        ws2 = FakeWS()
        ok2 = await mgr.connect_agent(seat_id, "right", ws2)
        assert ok2 is True and ws2.accepted is True
    finally:
        await mgr.close_all()
        async with AsyncSessionLocal() as db:
            seat = await db.get(Seat, seat_id)
            if seat is not None:
                await db.delete(seat)
                await db.commit()

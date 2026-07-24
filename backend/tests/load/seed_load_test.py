"""Seeds 50 agent seats with unique secrets for load testing."""

import asyncio
import secrets

from sqlalchemy import delete, select

from backend.core.database import AsyncSessionLocal
from backend.models import PricingModel, Seat, SeatStatus, Zone


async def seed_load_test() -> None:
    """Create 50 load test seats with unique agent secrets."""
    async with AsyncSessionLocal() as db:
        # Ensure zones exist
        zones = await db.execute(select(Zone))
        zone_list = zones.scalars().all()
        if len(zone_list) < 2:
            # Create zones if missing
            zone1 = Zone(
                name="Standard Zone",
                rate_per_minute_paise=20,
                rate_per_hour_paise=1200,
                pricing_model=PricingModel.PER_MINUTE,
                block_minutes=15,
            )
            zone2 = Zone(
                name="Gaming Zone",
                rate_per_minute_paise=30,
                rate_per_hour_paise=1800,
                pricing_model=PricingModel.PER_MINUTE,
                block_minutes=15,
            )
            db.add_all([zone1, zone2])
            await db.flush()
            zone_list = [zone1, zone2]

        # Delete existing load test seats (idempotent)
        await db.execute(delete(Seat).where(Seat.name.like("Load-%")))

        # Create 50 seats
        seats = []
        for i in range(1, 51):
            zone = zone_list[(i - 1) // 25]
            agent_secret = secrets.token_hex(32)
            seat = Seat(
                name=f"Load-{i:03d}",
                zone_id=zone.id,
                mac_address=f"02:00:00:00:{i:02x}:00",
                status=SeatStatus.AVAILABLE,
                agent_secret=agent_secret,
            )
            seats.append(seat)

        db.add_all(seats)
        await db.commit()

        # Verify
        for seat in seats:
            await db.refresh(seat)
            print(f"Created {seat.name}: secret={seat.agent_secret[:8]}...")


if __name__ == "__main__":
    asyncio.run(seed_load_test())

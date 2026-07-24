"""Seeds 50 agent seats with unique secrets for load testing."""

import asyncio
import secrets

from sqlalchemy import delete, select

from backend.core.database import AsyncSessionLocal
from backend.models import GamingSession, PricingModel, Seat, SeatStatus, Zone


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

        # Check if load test seats already exist
        existing_seats = await db.execute(select(Seat).where(Seat.name.like("Load-%")))
        existing = existing_seats.scalars().all()

        if len(existing) >= 50:
            print(
                f"Found {len(existing)} existing load test seats, updating secrets..."
            )
            for seat in existing[:50]:
                if not seat.agent_secret:
                    seat.agent_secret = secrets.token_hex(32)
            await db.commit()
            for seat in existing[:50]:
                await db.refresh(seat)
                print(f"Updated {seat.name}: secret={seat.agent_secret[:8]}...")
            return

        # Clean up old Load-* seats and their dependent sessions
        # (FK constraints prevent direct delete if sessions reference them)
        old_seats = await db.execute(select(Seat).where(Seat.name.like("Load-%")))
        old_seat_list = old_seats.scalars().all()
        if old_seat_list:
            old_ids = [s.id for s in old_seat_list]
            await db.execute(
                delete(GamingSession).where(GamingSession.seat_id.in_(old_ids))
            )
            await db.flush()
            for s in old_seat_list:
                await db.delete(s)
            await db.flush()

        # Create 50 seats with unique agent secrets
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

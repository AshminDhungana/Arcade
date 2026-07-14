"""Performance seed -- one year of sessions/invoices/reservations.

Generates a deterministic 365-day dataset for the analytics performance test
(NFR-PERF-002: summary < 2s on a 365-day seeded dataset).

Run:  python -m scripts.seed_perf   (after `alembic upgrade head`)
"""

# ruff: noqa: S311  # deterministic seed RNG (random.seed(42)); not used for crypto
from __future__ import annotations

import asyncio
import random
import time
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.database import AsyncSessionLocal
from backend.models import (
    GamingSession,
    Invoice,
    Member,
    MenuItem,
    Reservation,
    Seat,
    SessionPOSItem,
    Zone,
)
from backend.models._enums import (
    MemberTier,
    PaymentMethod,
    ReservationStatus,
    SeatStatus,
    SessionStatus,
)

random.seed(42)

ZONE_NAMES = ["Standard Zone", "Gaming Zone"]
MENU = [
    ("Mineral Water", "Beverages", 5000),
    ("Masala Tea", "Beverages", 2500),
    ("Black Coffee", "Beverages", 3000),
    ("Chicken Noodles", "Food", 8500),
    ("Veggie Burger", "Food", 7500),
]


async def seed_structural(db) -> None:  # type: ignore[no-untyped-def]
    """Create 2 zones, 8 seats, 5 menu items, 3 members."""
    zones = [
        Zone(
            name=ZONE_NAMES[0],
            rate_per_minute_paise=20,
            rate_per_hour_paise=1200,
            pricing_model="PER_MINUTE",
            block_minutes=15,
        ),
        Zone(
            name=ZONE_NAMES[1],
            rate_per_minute_paise=30,
            rate_per_hour_paise=1800,
            pricing_model="PER_MINUTE",
            block_minutes=15,
        ),
    ]
    db.add_all(zones)
    await db.flush()
    seats = []
    for i, zone in enumerate(zones):
        for j in range(1, 5):
            seats.append(
                Seat(
                    name=f"Seat {i*4+j:03d}",
                    zone_id=zone.id,
                    mac_address=f"00:11:22:33:44:{i*4+j:02x}",
                    status=SeatStatus.AVAILABLE.value,
                    is_console=(j > 2),
                )
            )
    db.add_all(seats)
    db.add_all(
        [
            Member(name="Alice", phone="+9779800000001", tier=MemberTier.BRONZE.value),
            Member(name="Bob", phone="+9779800000002", tier=MemberTier.SILVER.value),
            Member(name="Charlie", phone="+9779800000003", tier=MemberTier.GOLD.value),
        ]
    )
    db.add_all(
        [
            MenuItem(name=n, category=c, price_paise=p, is_available=True)
            for n, c, p in MENU
        ]
    )
    await db.flush()


async def seed_year(
    db: AsyncSession, *, days: int = 365, sessions_per_day: int = 10
) -> None:
    """Generate *days* of completed sessions across the seats.

    Each ``GamingSession`` is flushed before its dependent ``Invoice`` /
    ``SessionPOSItem`` are built, so the foreign keys reference a real ``sess.id``
    (the brief's original shape constructed dependents before the flush, which
    would have seeded NULL FKs).
    """
    seats = (await db.scalars(select(Seat))).all()
    members_list = list((await db.scalars(select(Member))).all())
    menu = (await db.scalars(select(MenuItem))).all()
    now = datetime.now(UTC)
    for d in range(days, 0, -1):
        day_start = (now - timedelta(days=d)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        objs: list[object] = []
        for _ in range(sessions_per_day):
            seat = random.choice(seats)
            start = day_start.replace(
                hour=random.randint(8, 23), minute=random.randint(0, 59)
            )
            duration_min = random.randint(20, 240)
            ended_at = start + timedelta(minutes=duration_min)
            member = (
                random.choice(members_list + [None]) if random.random() < 0.8 else None
            )
            sess = GamingSession(
                seat_id=seat.id,
                member_id=member.id if member else None,
                status=SessionStatus.COMPLETED,
                started_at=start,
                ended_at=ended_at,
                total_paused_seconds=0,
                locked_rate_paise=20,
                locked_pricing_model="PER_MINUTE",
                payment_method=PaymentMethod.CASH,
            )
            db.add(sess)
            await db.flush()  # <-- assign sess.id BEFORE dependents reference it
            objs.append(sess)
            objs.append(
                Invoice(
                    session_id=sess.id,
                    member_id=member.id if member else None,
                    total_paise=duration_min * 20,
                    payment_method=PaymentMethod.CASH,
                    created_at=ended_at,
                )
            )
            if random.random() < 0.5:
                item = random.choice(menu)
                objs.append(
                    SessionPOSItem(
                        session_id=sess.id,
                        menu_item_id=item.id,
                        quantity=random.randint(1, 3),
                        unit_price_paise=item.price_paise,
                    )
                )
            if random.random() < 0.05:
                objs.append(
                    Reservation(
                        seat_id=seat.id,
                        customer_name=f"Cust{d}",
                        reserved_from=start,
                        reserved_until=ended_at,
                        status=ReservationStatus.CONFIRMED.value,
                        created_by_staff_id="seed",
                    )
                )
            seat.wol_attempts += 1
            if random.random() < 0.9:
                seat.wol_successes += 1
        # Add dependents (Invoice/POS/Reservation) built after the per-session flush.
        db.add_all(objs)
        await db.flush()


async def seed_perf(db) -> None:  # type: ignore[no-untyped-def]
    await seed_structural(db)
    await seed_year(db)
    await db.commit()


if __name__ == "__main__":

    async def _main() -> None:
        t0 = time.perf_counter()
        async with AsyncSessionLocal() as db:
            await seed_perf(db)
        print(f"Performance seed complete in {time.perf_counter() - t0:.1f}s")  # noqa: T201

    asyncio.run(_main())

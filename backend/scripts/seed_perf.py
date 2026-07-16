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


async def seed_30_day(db: AsyncSession) -> None:
    """Deterministic ~30-day dataset for analytics-summary correctness tests.

    Spans every analytics window so a single ``get_summary`` call can be asserted
    field-by-field with exact values:

    * today-only:   S1 (10:00-11:00, CASH 5000) + S2 (12:00-12:30, CASH 3000)
      -> total_revenue 8000, session_count 2, avg_duration 2700s.
    * 7-day:        only today has revenue -> weekly_revenue sum 8000.
    * 30-day:       S3 (member Alice, exactly 30 days ago at 10:00, WALLET 2000)
      makes hour 10 the busiest (2 sessions) and Alice the top spender / active.
    * member trend: Alice registered 29 days ago (trend[0]), Newbie today
      (trend[-1] and new_today).
    * POS:          Tea x2 (S1) + x3 (S2) = 5.
    * WoL:          Seat 001 = 8/10 successes -> 80.0%.
    * reservation:  Bob today (upcoming).
    """
    now = datetime.now(UTC)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    zone = Zone(
        name="Z",
        rate_per_minute_paise=20,
        rate_per_hour_paise=1200,
        pricing_model="PER_MINUTE",
        block_minutes=15,
    )
    db.add(zone)
    await db.flush()
    seat = Seat(name="Seat 001", zone_id=zone.id, status=SeatStatus.OFFLINE.value)
    seat.wol_attempts = 10
    seat.wol_successes = 8
    db.add(seat)
    await db.flush()
    tea = MenuItem(
        name="Tea", category="Beverages", price_paise=2500, is_available=True
    )
    db.add(tea)
    await db.flush()

    alice = Member(
        name="Alice",
        phone="+9779800000999",
        tier=MemberTier.BRONZE.value,
        wallet_balance_paise=0,
        created_at=today_start - timedelta(days=29),
    )
    newbie = Member(
        name="Newbie",
        phone="+9779800000888",
        tier=MemberTier.BRONZE.value,
        wallet_balance_paise=0,
        created_at=now.replace(hour=9, minute=0, second=0, microsecond=0),
    )
    db.add_all([alice, newbie])
    await db.flush()

    s1 = GamingSession(
        seat_id=seat.id,
        member_id=None,
        status=SessionStatus.COMPLETED,
        started_at=now.replace(hour=10, minute=0, second=0, microsecond=0),
        ended_at=now.replace(hour=11, minute=0, second=0, microsecond=0),
        total_paused_seconds=0,
        locked_rate_paise=20,
        locked_pricing_model="PER_MINUTE",
        payment_method=PaymentMethod.CASH,
    )
    s2 = GamingSession(
        seat_id=seat.id,
        member_id=None,
        status=SessionStatus.COMPLETED,
        started_at=now.replace(hour=12, minute=0, second=0, microsecond=0),
        ended_at=now.replace(hour=12, minute=30, second=0, microsecond=0),
        total_paused_seconds=0,
        locked_rate_paise=20,
        locked_pricing_model="PER_MINUTE",
        payment_method=PaymentMethod.CASH,
    )
    s3 = GamingSession(
        seat_id=seat.id,
        member_id=alice.id,
        status=SessionStatus.COMPLETED,
        started_at=(today_start - timedelta(days=30)) + timedelta(hours=10),
        ended_at=(today_start - timedelta(days=30)) + timedelta(hours=11),
        total_paused_seconds=0,
        locked_rate_paise=20,
        locked_pricing_model="PER_MINUTE",
        payment_method=PaymentMethod.WALLET,
    )
    db.add_all([s1, s2, s3])
    await db.flush()

    db.add_all(
        [
            Invoice(
                session_id=s1.id,
                member_id=None,
                total_paise=5000,
                payment_method=PaymentMethod.CASH,
                created_at=s1.ended_at,
            ),
            Invoice(
                session_id=s2.id,
                member_id=None,
                total_paise=3000,
                payment_method=PaymentMethod.CASH,
                created_at=s2.ended_at,
            ),
            Invoice(
                session_id=s3.id,
                member_id=alice.id,
                total_paise=2000,
                payment_method=PaymentMethod.WALLET,
                created_at=s3.ended_at,
            ),
            SessionPOSItem(
                session_id=s1.id,
                menu_item_id=tea.id,
                quantity=2,
                unit_price_paise=tea.price_paise,
            ),
            SessionPOSItem(
                session_id=s2.id,
                menu_item_id=tea.id,
                quantity=3,
                unit_price_paise=tea.price_paise,
            ),
            Reservation(
                seat_id=seat.id,
                customer_name="Bob",
                reserved_from=now + timedelta(hours=2),
                reserved_until=now + timedelta(hours=3),
                status=ReservationStatus.CONFIRMED.value,
                created_by_staff_id="seed",
            ),
        ]
    )
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
        print(f"Performance seed complete in {time.perf_counter() - t0:.1f}s")

    asyncio.run(_main())

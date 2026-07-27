"""1-Year Realistic Data Seed Script.

Generates 365 days of realistic gaming cafe data for analytics performance testing.

- ~100 sessions/day (varies by weekday/weekend, peak hours)
- ~5 POS items/session
- 200 members with varied tiers and visit patterns
- 3 zones with different pricing models (PER_MINUTE, FLAT_HOURLY, TIME_BLOCK)
- Realistic session durations, member behavior, POS purchases

Usage (from backend/ directory):
    python -m scripts.seed_year_data

Prerequisites:
    alembic upgrade head
"""

# ruff: noqa: S311  # deterministic seed RNG for reproducible data
from __future__ import annotations

import asyncio
import random
import sys
import time
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import select

# Ensure project root is on sys.path so backend.* imports resolve
_HERE = Path(__file__).resolve().parent
_PROJECT_ROOT = _HERE.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from argon2 import PasswordHasher  # noqa: E402

from backend.core.database import AsyncSessionLocal, Base  # noqa: E402
from backend.models import (  # noqa: E402
    AppSettings,
    Invoice,
    Member,
    MemberTier,
    MenuItem,
    Package,
    PackageType,
    PricingModel,
    Seat,
    SeatStatus,
    SessionPOSItem,
    Shift,
    ShiftStatus,
    Staff,
    StaffRole,
    Zone,
)
from backend.models._enums import (  # noqa: E402
    PaymentMethod,
    SessionStatus,
)
from backend.models.session import GamingSession  # noqa: E402

# ── Deterministic RNG ──────────────────────────────────────────────────────
random.seed(42)

# ── Constants ──────────────────────────────────────────────────────────────
DAYS = 365
AVG_SESSIONS_PER_DAY = 100
POS_ITEMS_PER_SESSION = 5
NUM_MEMBERS = 200
NUM_STAFF = 5
NUM_MENU_ITEMS = 15

# Zones with different pricing models
ZONES_CONFIG = [
    {
        "name": "Standard Zone",
        "rate_per_minute_paise": 20,
        "rate_per_hour_paise": 1200,
        "pricing_model": PricingModel.PER_MINUTE.value,
        "block_minutes": 15,
    },
    {
        "name": "Gaming Zone",
        "rate_per_minute_paise": 30,
        "rate_per_hour_paise": 1800,
        "pricing_model": PricingModel.FLAT_HOURLY.value,
        "block_minutes": 60,
    },
    {
        "name": "VIP Zone",
        "rate_per_minute_paise": 50,
        "rate_per_hour_paise": 3000,
        "pricing_model": PricingModel.TIME_BLOCK.value,
        "block_minutes": 30,
    },
]

# Hourly session probability (higher during peak hours 14:00-23:00)
HOUR_WEIGHTS = {
    6: 0.5,
    7: 0.8,
    8: 1.2,
    9: 1.5,
    10: 1.8,
    11: 2.0,
    12: 2.2,
    13: 2.0,
    14: 2.5,
    15: 3.0,
    16: 3.5,
    17: 4.0,
    18: 4.5,
    19: 5.0,
    20: 4.8,
    21: 4.0,
    22: 3.0,
    23: 2.0,
    0: 1.0,
    1: 0.5,
}

# Weekday multipliers (Mon=0 ... Sun=6)
WEEKDAY_MULTIPLIERS = [0.8, 0.7, 0.8, 0.9, 1.2, 1.5, 1.3]

# Session duration distributions (minutes)
DURATION_CHOICES = [30, 45, 60, 90, 120, 180, 240]
DURATION_WEIGHTS = [0.1, 0.15, 0.25, 0.2, 0.15, 0.1, 0.05]

# Member tier distribution
TIER_DISTRIBUTION = {
    MemberTier.BRONZE: 0.6,
    MemberTier.SILVER: 0.3,
    MemberTier.GOLD: 0.1,
}

# Member visit frequency (sessions per week by tier)
VISITS_PER_WEEK = {
    MemberTier.BRONZE: (1, 3),
    MemberTier.SILVER: (3, 6),
    MemberTier.GOLD: (5, 10),
}

# Menu items
MENU_ITEMS = [
    ("Mineral Water 500ml", "Beverages", 3000),
    ("Mineral Water 1L", "Beverages", 5000),
    ("Coca Cola", "Beverages", 4500),
    ("Sprite", "Beverages", 4500),
    ("Masala Tea", "Beverages", 2500),
    ("Black Coffee", "Beverages", 3000),
    ("Cappuccino", "Beverages", 5500),
    ("Chicken Noodles", "Food", 8500),
    ("Veg Noodles", "Food", 7500),
    ("Chicken Burger", "Food", 7000),
    ("Veggie Burger", "Food", 6000),
    ("French Fries", "Food", 4500),
    ("Chicken Wings (6pc)", "Food", 9500),
    ("Onion Rings", "Food", 4000),
    ("Chocolate Brownie", "Dessert", 5000),
]

# Staff names
STAFF_NAMES = [
    ("Admin User", StaffRole.ADMIN),
    ("Cashier One", StaffRole.CASHIER),
    ("Cashier Two", StaffRole.CASHIER),
    ("Shift Lead", StaffRole.CASHIER),
    ("Weekend Staff", StaffRole.CASHIER),
]

# Member names (Indian/Nepali context)
FIRST_NAMES = [
    "Aarav",
    "Aditi",
    "Amit",
    "Anjali",
    "Arjun",
    "Asha",
    "Bhavya",
    "Chetan",
    "Deepak",
    "Divya",
    "Gaurav",
    "Isha",
    "Karan",
    "Kavya",
    "Manish",
    "Meera",
    "Nikhil",
    "Neha",
    "Priya",
    "Rahul",
    "Rajesh",
    "Riya",
    "Rohan",
    "Saanvi",
    "Sanjay",
    "Shreya",
    "Siddharth",
    "Simran",
    "Sunil",
    "Tanvi",
    "Varun",
    "Vikram",
    "Pooja",
    "Rohit",
    "Sneha",
    "Amitabh",
    "Jaya",
    "Raj",
    "Simran",
    "Abhishek",
    "Ankit",
    "Bhavana",
    "Chitra",
    "Dinesh",
    "Esha",
    "Farhan",
    "Gayatri",
    "Harsh",
    "Indira",
    "Jatin",
    "Kritika",
    "Lakshay",
    "Maya",
    "Nitin",
    "Omkar",
    "Pallavi",
    "Qasim",
    "Rashmi",
    "Sachin",
    "Tara",
    "Uday",
    "Vivek",
    "Yash",
    "Zara",
]

LAST_NAMES = [
    "Sharma",
    "Patel",
    "Singh",
    "Kumar",
    "Gupta",
    "Joshi",
    "Mehta",
    "Reddy",
    "Nair",
    "Iyer",
    "Rao",
    "Chopra",
    "Kapoor",
    "Malhotra",
    "Verma",
    "Yadav",
    "Thapa",
    "Rai",
    "Gurung",
    "Tamang",
    "Sherpa",
    "Lama",
    "Bhattarai",
    "Adhikari",
    "Pokhrel",
    "Subedi",
    "Karki",
    "Bhandari",
    "Poudel",
    "Dhakal",
    "Ghimire",
]

PHONE_PREFIXES = ["+97798", "+97797", "+97796"]


# ── Helper Functions ───────────────────────────────────────────────────────
def random_phone() -> str:
    prefix = random.choice(PHONE_PREFIXES)
    suffix = "".join(str(random.randint(0, 9)) for _ in range(7))
    return f"{prefix}{suffix}"


def random_member_name() -> str:
    return f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"


def pick_tier() -> MemberTier:
    r = random.random()
    cum = 0.0
    for tier, prob in TIER_DISTRIBUTION.items():
        cum += prob
        if r < cum:
            return tier
    return MemberTier.BRONZE


def random_duration() -> int:
    return random.choices(DURATION_CHOICES, weights=DURATION_WEIGHTS, k=1)[0]


def sessions_for_day(
    day_of_week: int, base_sessions: int = AVG_SESSIONS_PER_DAY
) -> int:
    """Calculate sessions for a given day with some randomness."""
    multiplier = WEEKDAY_MULTIPLIERS[day_of_week]
    # Add some day-to-day variance
    variance = random.uniform(0.85, 1.15)
    return max(10, int(base_sessions * multiplier * variance))


def pick_hour() -> int:
    """Pick hour weighted by peak hours."""
    hours = list(HOUR_WEIGHTS.keys())
    weights = list(HOUR_WEIGHTS.values())
    return random.choices(hours, weights=weights, k=1)[0]


def pick_zone_and_rate(seat: Seat, zones: list[Zone]) -> tuple[Zone, int, PricingModel]:
    """Get zone and locked rate for a seat."""
    zone = next(z for z in zones if z.id == seat.zone_id)
    if zone.pricing_model == PricingModel.PER_MINUTE:
        return zone, zone.rate_per_minute_paise, zone.pricing_model
    if zone.pricing_model == PricingModel.FLAT_HOURLY:
        return zone, zone.rate_per_hour_paise, zone.pricing_model
    # TIME_BLOCK
    return zone, zone.rate_per_minute_paise, zone.pricing_model


def calculate_session_cost(
    duration_min: int,
    rate_paise: int,
    pricing_model: PricingModel,
    block_minutes: int = 15,
) -> int:
    """Calculate session cost based on pricing model."""
    if pricing_model == PricingModel.PER_MINUTE:
        return duration_min * rate_paise
    if pricing_model == PricingModel.FLAT_HOURLY:
        hours = (duration_min + 59) // 60
        return hours * rate_paise
    # TIME_BLOCK
    blocks = (duration_min + block_minutes - 1) // block_minutes
    return blocks * rate_paise * block_minutes


async def clear_data(db: Any) -> None:
    """Remove all existing data except alembic_version."""
    from sqlalchemy import delete

    for tbl in reversed(Base.metadata.sorted_tables):
        if tbl.name == "alembic_version":
            continue
        await db.execute(delete(tbl))
    await db.flush()


async def seed_structural(
    db: Any,
) -> tuple[list[Zone], list[Seat], list[MenuItem], list[Member], list[Staff]]:
    """Create zones, seats, menu items, members, staff - idempotent."""
    # Zones
    existing_zones = (await db.scalars(select(Zone))).all()
    if not existing_zones:
        zones = [Zone(**z) for z in ZONES_CONFIG]
        db.add_all(zones)
        await db.flush()
    else:
        zones = existing_zones

    # Seats (12 per zone = 36 total)
    existing_seats = (await db.scalars(select(Seat))).all()
    if not existing_seats:
        seats = []
        for zone in zones:
            for i in range(1, 13):
                seat_num = zones.index(zone) * 12 + i
                seats.append(
                    Seat(
                        name=f"Seat {seat_num:03d}",
                        zone_id=zone.id,
                        mac_address=f"00:11:22:33:44:{seat_num:02x}",
                        status=SeatStatus.AVAILABLE.value,
                        is_console=(i > 8),  # Last 4 seats are consoles
                    )
                )
        db.add_all(seats)
        await db.flush()
    else:
        seats = existing_seats

    # Menu Items
    existing_menu = (await db.scalars(select(MenuItem))).all()
    if not existing_menu:
        menu_items = [
            MenuItem(
                name=n,
                category=c,
                price_paise=p,
                is_available=True,
                stock_quantity=100,
                low_stock_threshold=10,
            )
            for n, c, p in MENU_ITEMS
        ]
        db.add_all(menu_items)
        await db.flush()
    else:
        menu_items = existing_menu

    # Staff
    existing_staff = (await db.scalars(select(Staff))).all()
    if not existing_staff:
        PH = PasswordHasher(time_cost=2, memory_cost=102400, parallelism=8)
        staff_list = [
            Staff(
                name=name,
                role=role.value,
                pin_hash=PH.hash("0000"),
                token_version=1,
                is_active=True,
            )
            for name, role in STAFF_NAMES
        ]
        db.add_all(staff_list)
        await db.flush()
    else:
        staff_list = existing_staff

    # Members (200 with varied tiers)
    existing_members = (await db.scalars(select(Member))).all()
    if len(existing_members) < NUM_MEMBERS:
        members_to_create = NUM_MEMBERS - len(existing_members)
        members = []
        for _ in range(members_to_create):
            tier = pick_tier()
            visits_per_week = random.randint(*VISITS_PER_WEEK[tier])
            total_visits = visits_per_week * random.randint(
                4, 52
            )  # 1-12 months of data
            # Wallet balance correlates with tier and visits
            base_balance = {
                MemberTier.BRONZE: 10000,
                MemberTier.SILVER: 50000,
                MemberTier.GOLD: 200000,
            }[tier]
            wallet_balance = base_balance + random.randint(-5000, 50000)
            # Loyalty points ~ 1 point per 100 rupees spent
            loyalty_points = max(
                0, total_visits * random.randint(5, 20) + random.randint(-100, 500)
            )

            member = Member(
                name=random_member_name(),
                phone=random_phone(),
                wallet_balance_paise=wallet_balance,
                loyalty_points=loyalty_points,
                tier=tier.value,
                total_visits=total_visits,
                total_seconds_played=total_visits * random_duration() * 60,
            )
            members.append(member)
        db.add_all(members)
        await db.flush()
        all_members = existing_members + members
    else:
        all_members = existing_members

    # Feature flags
    existing_flags = (await db.scalars(select(AppSettings))).all()
    if not existing_flags:
        DEFAULT_FEATURE_FLAGS = {
            "enable_members": "true",
            "enable_packages": "true",
            "enable_pos": "true",
            "enable_inventory": "false",
            "enable_reservations": "true",
            "enable_vouchers": "false",
            "enable_tournaments": "false",
            "enable_expense_tracking": "false",
            "enable_health_monitoring": "true",
            "require_member_for_session": "false",
            "enable_tuya": "false",
            "require_print_before_release": "false",
            "block_shift_close_unprinted": "false",
            "overlay_pauses_billing": "true",
            "enable_assigned_time_limit": "false",
        }
        for key, value in DEFAULT_FEATURE_FLAGS.items():
            db.add(AppSettings(key=key, value=value, updated_at=datetime.now(UTC)))
        await db.flush()

    # Packages
    existing_packages = (await db.scalars(select(Package))).all()
    if not existing_packages:
        packages = [
            Package(
                name="10 Hour Bundle",
                type=PackageType.HOUR_BUNDLE.value,
                total_minutes=600,
                price_paise=100000,
                valid_days=30,
                is_active=True,
            ),
            Package(
                name="25 Hour Bundle",
                type=PackageType.HOUR_BUNDLE.value,
                total_minutes=1500,
                price_paise=225000,
                valid_days=60,
                is_active=True,
            ),
            Package(
                name="Day Pass",
                type=PackageType.DAY_PASS.value,
                total_minutes=480,
                price_paise=80000,
                valid_days=1,
                is_active=True,
            ),
            Package(
                name="Night Pass (6PM-6AM)",
                type=PackageType.NIGHT_PASS.value,
                total_minutes=720,
                price_paise=50000,
                valid_days=1,
                is_active=True,
            ),
            Package(
                name="Monthly Unlimited",
                type=PackageType.MONTHLY.value,
                total_minutes=10000,
                price_paise=500000,
                valid_days=30,
                is_active=True,
            ),
        ]
        db.add_all(packages)
        await db.flush()

    return zones, seats, menu_items, all_members, staff_list


async def seed_year_data(
    db: Any,
    zones: list[Zone],
    seats: list[Seat],
    menu_items: list[MenuItem],
    members: list[Member],
    staff_list: list[Staff],
) -> None:
    """Generate 365 days of sessions, invoices, POS items."""
    now = datetime.now(UTC)
    total_sessions = 0
    total_pos_items = 0
    total_invoices = 0

    # Pre-fetch seat objects with zone info
    seat_zone_map = {s.id: next(z for z in zones if z.id == s.zone_id) for s in seats}

    for day_offset in range(DAYS, 0, -1):
        day_start = (now - timedelta(days=day_offset)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        day_of_week = day_start.weekday()  # Mon=0

        num_sessions = sessions_for_day(day_of_week)
        total_sessions += num_sessions

        for _ in range(num_sessions):
            # Pick random seat
            seat = random.choice(seats)
            zone = seat_zone_map[seat.id]

            # Pick start hour (weighted)
            hour = pick_hour()
            minute = random.randint(0, 59)
            start = day_start.replace(hour=hour, minute=minute)

            # Duration
            duration_min = random_duration()
            ended_at = start + timedelta(minutes=duration_min)

            # Member assignment (70% members, 30% walk-ins)
            member = (
                random.choice(members + [None] * int(len(members) * 0.43))
                if random.random() < 0.7
                else None
            )

            # Calculate pricing
            if zone.pricing_model == PricingModel.PER_MINUTE:
                locked_rate = zone.rate_per_minute_paise
            elif zone.pricing_model == PricingModel.FLAT_HOURLY:
                locked_rate = zone.rate_per_hour_paise
            else:
                locked_rate = zone.rate_per_minute_paise

            locked_pricing_model = zone.pricing_model

            # Payment method (weighted)
            if member and member.wallet_balance_paise > 10000 and random.random() < 0.3:
                payment_method = PaymentMethod.WALLET
            elif random.random() < 0.1:
                payment_method = PaymentMethod.CARD
            else:
                payment_method = PaymentMethod.CASH

            # Paused time (5% chance of pause, 0-15 min)
            total_paused_seconds = 0
            if random.random() < 0.05:
                total_paused_seconds = random.randint(60, 900)

            # Create session
            sess = GamingSession(
                seat_id=seat.id,
                member_id=member.id if member else None,
                shift_id=None,  # Will assign shifts in Phase 5
                status=SessionStatus.COMPLETED,
                started_at=start,
                ended_at=ended_at,
                paused_at=None,
                total_paused_seconds=total_paused_seconds,
                assigned_end_at=None,
                expiry_warned=False,
                locked_rate_paise=locked_rate,
                locked_pricing_model=locked_pricing_model,
                payment_method=payment_method,
            )
            db.add(sess)
            await db.flush()  # Get sess.id

            # Calculate total
            billable_minutes = duration_min - (total_paused_seconds // 60)
            block_min = zone.block_minutes or 15
            total_paise = calculate_session_cost(
                billable_minutes, locked_rate, locked_pricing_model, block_min
            )

            # Add POS items (0-8 items, avg ~5)
            num_pos = max(0, int(random.gauss(POS_ITEMS_PER_SESSION, 1.5)))
            pos_items = []
            pos_total = 0
            for _ in range(num_pos):
                item = random.choice(menu_items)
                qty = random.randint(1, 3)
                pos_items.append(
                    SessionPOSItem(
                        session_id=sess.id,
                        menu_item_id=item.id,
                        quantity=qty,
                        unit_price_paise=item.price_paise,
                    )
                )
                pos_total += qty * item.price_paise

            total_paise += pos_total

            # Create Invoice
            invoice = Invoice(
                session_id=sess.id,
                member_id=member.id if member else None,
                total_paise=total_paise,
                payment_method=payment_method,
                created_at=ended_at,
            )
            db.add(invoice)
            total_invoices += 1

            # Add POS items
            if pos_items:
                db.add_all(pos_items)
                total_pos_items += len(pos_items)

            # Update member stats if member
            if member:
                member.total_visits += 1
                member.total_seconds_played += billable_minutes * 60
                if payment_method == PaymentMethod.WALLET:
                    member.wallet_balance_paise = max(
                        0, member.wallet_balance_paise - total_paise
                    )
                # Add loyalty points (1 point per 100 rupees)
                member.loyalty_points += total_paise // 10000

            # Update seat stats
            seat.wol_attempts += 1
            if random.random() < 0.85:
                seat.wol_successes += 1

        # Batch flush every day
        if day_offset % 10 == 0 or day_offset == 1:
            await db.flush()
            print(
                f"  Day {DAYS - day_offset + 1}/{DAYS}: {num_sessions} sessions, "
                f"total so far: {total_sessions}"
            )

    await db.flush()
    print("\nYear seeding complete!")
    print(f"  Total sessions: {total_sessions}")
    print(f"  Total invoices: {total_invoices}")
    print(f"  Total POS items: {total_pos_items}")
    print(f"  Avg POS/session: {total_pos_items / max(1, total_sessions):.1f}")


async def seed_shifts(db: Any, staff_list: list[Staff]) -> None:
    """Create shifts for the year (one per day, 12-hour shifts)."""
    now = datetime.now(UTC)

    for day_offset in range(DAYS, 0, -1):
        day_start = (now - timedelta(days=day_offset)).replace(
            hour=10, minute=0, second=0, microsecond=0
        )
        day_end = day_start + timedelta(hours=12)

        # Rotate staff
        staff = staff_list[day_offset % len(staff_list)]

        # Opening float cash varies
        float_paise = random.randint(50000, 200000)  # 500-2000 rupees

        # Expected cash = opening + session revenue (rough estimate)
        expected_sessions = sessions_for_day(day_start.weekday())
        expected_revenue = expected_sessions * 50000  # ~500 rupees avg session
        expected_cash = float_paise + expected_revenue

        # Actual closing cash (small variance)
        variance = random.uniform(-0.02, 0.02)
        counted_paise = int(expected_cash * (1 + variance))

        shift = Shift(
            opened_by_staff_id=staff.id,
            closed_by_staff_id=staff.id,
            opened_at=day_start,
            closed_at=day_end,
            float_paise=float_paise,
            counted_paise=counted_paise,
            status=ShiftStatus.CLOSED.value,
        )
        db.add(shift)

    await db.flush()
    print(f"Created {DAYS} shifts")


async def main() -> None:
    t0 = time.perf_counter()
    print("Starting 1-year data seed...")

    async with AsyncSessionLocal() as db:
        # Clear existing data
        print("Clearing existing data...")
        await clear_data(db)
        print("Done.")

        # Seed structural data
        print("Seeding structural data (zones, seats, menu, members, staff)...")
        zones, seats, menu_items, members, staff_list = await seed_structural(db)
        print(f"  Zones: {len(zones)}")
        print(f"  Seats: {len(seats)}")
        print(f"  Menu items: {len(menu_items)}")
        print(f"  Members: {len(members)}")
        print(f"  Staff: {len(staff_list)}")

        # Seed year of session data
        msg = (
            f"\nSeeding {DAYS} days of session data "
            f"(~{AVG_SESSIONS_PER_DAY} sessions/day)..."
        )
        print(msg)
        await seed_year_data(db, zones, seats, menu_items, members, staff_list)

        # Seed shifts
        print("\nSeeding shifts...")
        await seed_shifts(db, staff_list)

        await db.commit()

    elapsed = time.perf_counter() - t0
    print(f"\nSeed complete in {elapsed:.1f}s")


if __name__ == "__main__":
    asyncio.run(main())

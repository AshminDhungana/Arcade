"""Development seed script.

Populate the database with a sensible set of test data.

Usage (run from the ``backend/`` directory)::

    python -m scripts.seed_dev

Prerequisites::

    alembic upgrade head

"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

# Ensure project root is on sys.path so backend.* imports resolve
_HERE = Path(__file__).resolve().parent
_PROJECT_ROOT = _HERE.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from argon2 import PasswordHasher  # noqa: E402

from backend.core.database import AsyncSessionLocal, Base  # noqa: E402
from backend.models import (  # noqa: E402
    AppSettings,
    Member,
    MemberTier,
    MenuItem,
    PricingModel,
    Seat,
    SeatStatus,
    Staff,
    StaffRole,
    Zone,
)

PH = PasswordHasher(time_cost=2, memory_cost=102400, parallelism=8)


async def clear_data(db) -> None:  # type: ignore[no-untyped-def]
    """Remove all existing data (except alembic_version)."""
    from sqlalchemy import delete

    for tbl in reversed(Base.metadata.sorted_tables):
        if tbl.name == "alembic_version":
            continue
        await db.execute(delete(tbl))
    await db.flush()


async def seed_zones(db) -> list[Zone]:  # type: ignore[no-untyped-def]
    """Seed 2 pricing zones."""
    zones = [
        Zone(
            name="Standard Zone",
            rate_per_minute_paise=20,
            rate_per_hour_paise=1200,
            pricing_model=PricingModel.PER_MINUTE.value,
            block_minutes=15,
        ),
        Zone(
            name="Gaming Zone",
            rate_per_minute_paise=30,
            rate_per_hour_paise=1800,
            pricing_model=PricingModel.PER_MINUTE.value,
            block_minutes=15,
        ),
    ]
    db.add_all(zones)
    await db.flush()
    return zones


async def seed_seats(db, zones: list[Zone]) -> None:  # type: ignore[no-untyped-def]
    """Seed 8 seats, 4 per zone."""
    seats = []
    for i, zone in enumerate(zones):
        for j in range(1, 5):
            seats.append(
                Seat(
                    name=f"Seat {i * 4 + j:03d}",
                    zone_id=zone.id,
                    mac_address=f"00:11:22:33:44:{i * 4 + j:02x}",
                    status=SeatStatus.AVAILABLE.value,
                    is_console=(j > 2),
                    notes=None,
                )
            )
    db.add_all(seats)
    await db.flush()


async def seed_staff(db) -> None:  # type: ignore[no-untyped-def]
    """Seed 2 staff members with test PINs."""
    db.add_all(
        [
            Staff(
                name="Admin User",
                role=StaffRole.ADMIN.value,
                pin_hash=PH.hash("0000"),
                token_version=1,
                is_active=True,
            ),
            Staff(
                name="Cashier User",
                role=StaffRole.CASHIER.value,
                pin_hash=PH.hash("0000"),
                token_version=1,
                is_active=True,
            ),
        ]
    )
    await db.flush()


async def seed_menu_items(db) -> None:  # type: ignore[no-untyped-def]
    """Seed 5 menu items."""
    db.add_all(
        [
            MenuItem(
                name="Mineral Water",
                category="Beverages",
                price_paise=5000,
                is_available=True,
                stock_quantity=50,
                low_stock_threshold=10,
            ),
            MenuItem(
                name="Masala Tea",
                category="Beverages",
                price_paise=2500,
                is_available=True,
                stock_quantity=30,
                low_stock_threshold=5,
            ),
            MenuItem(
                name="Black Coffee",
                category="Beverages",
                price_paise=3000,
                is_available=True,
                stock_quantity=25,
                low_stock_threshold=5,
            ),
            MenuItem(
                name="Chicken Noodles",
                category="Food",
                price_paise=8500,
                is_available=True,
                stock_quantity=15,
                low_stock_threshold=3,
            ),
            MenuItem(
                name="Veggie Burger",
                category="Food",
                price_paise=7500,
                is_available=True,
                stock_quantity=20,
                low_stock_threshold=3,
            ),
        ]
    )
    await db.flush()


async def seed_members(db) -> None:  # type: ignore[no-untyped-def]
    """Seed 3 members with different tiers."""
    db.add_all(
        [
            Member(
                name="Alice Wonderland",
                phone="+9779801234567",
                wallet_balance_paise=50000,
                loyalty_points=0,
                tier=MemberTier.BRONZE.value,
                total_visits=3,
                total_seconds_played=7200,
            ),
            Member(
                name="Bob The Builder",
                phone="+9779801234568",
                wallet_balance_paise=150000,
                loyalty_points=450,
                tier=MemberTier.SILVER.value,
                total_visits=12,
                total_seconds_played=36000,
            ),
            Member(
                name="Charlie Chaplin",
                phone="+9779801234569",
                wallet_balance_paise=300000,
                loyalty_points=1200,
                tier=MemberTier.GOLD.value,
                total_visits=25,
                total_seconds_played=90000,
            ),
        ]
    )
    await db.flush()


async def seed_feature_flags(db) -> None:  # type: ignore[no-untyped-def]
    """Seed default feature flag values."""
    from datetime import UTC, datetime

    flags = {
        "enable_pos": "true",
        "enable_inventory": "true",
        "enable_membership": "true",
        "enable_packages": "true",
        "enable_promotions": "true",
        "enable_vouchers": "false",
        "enable_reservations": "false",
        "enable_events": "false",
        "enable_expenses": "false",
        "require_member_for_session": "false",
        "enable_analytics": "true",
        "enable_audit_log": "true",
    }
    for key, value in flags.items():
        db.add(AppSettings(key=key, value=value, updated_at=datetime.now(UTC)))
    await db.flush()


async def seed_database() -> None:
    """Run all seed functions inside a transaction."""
    async with AsyncSessionLocal() as db:
        await clear_data(db)
        zones = await seed_zones(db)
        await seed_seats(db, zones)
        await seed_staff(db)
        await seed_menu_items(db)
        await seed_members(db)
        await seed_feature_flags(db)

        await db.commit()
        print("Seed complete")  # noqa: T201


if __name__ == "__main__":
    asyncio.run(seed_database())

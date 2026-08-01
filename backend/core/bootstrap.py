"""First-run bootstrap: ensure default admin + cashier, zone, and seats exist.

The launcher Setup Wizard writes credentials and agent_secrets to
``arcade.config.json`` but nothing previously turned them into DB rows.
These functions reconcile config -> DB exactly once (when tables are empty)
and are safe to call on every startup.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import Settings, get_config
from backend.core.security import hash_pin
from backend.models import Seat, Staff, Zone
from backend.models._enums import PricingModel, SeatStatus, StaffRole
from backend.repositories import staff_repo, zone_repo, seat_repo

_ADMIN_DEFAULT_ID = "admin"
_ADMIN_DEFAULT_PIN = "admin"
_CASHIER_DEFAULT_ID = "cashier"
_CASHIER_DEFAULT_PIN = "cashier"

_DEFAULT_ZONE_NAME = "Standard PC"
_DEFAULT_ZONE_RATE_PER_MINUTE = 200  # 200 paise/min = ₹12/hr
_DEFAULT_ZONE_RATE_PER_HOUR = 12000  # 12000 paise/hr = ₹120/hr


async def ensure_default_staff(
    db: AsyncSession, settings: Settings | None = None
) -> None:
    """Insert default admin + cashier Staff rows only when the table is empty.

    Reads ids/PIN hashes from *settings* (defaults to the cached app config).
    Staff rows are created with explicit ids so login with the human-typed id
    (e.g. ``admin``) matches ``Staff.id``.
    """
    if await staff_repo.list(db):
        return  # already seeded; never overwrite or resurrect deleted accounts

    cfg = settings if settings is not None else get_config()

    admin_id = cfg.admin_staff_id or _ADMIN_DEFAULT_ID
    admin_pin_hash = cfg.admin_pin_hash or hash_pin(_ADMIN_DEFAULT_PIN)
    cashier_id = cfg.cashier_staff_id or _CASHIER_DEFAULT_ID
    cashier_pin_hash = cfg.cashier_pin_hash or hash_pin(_CASHIER_DEFAULT_PIN)

    db.add(
        Staff(
            id=admin_id,
            name="Administrator",
            role=StaffRole.ADMIN,
            pin_hash=admin_pin_hash,
            is_active=True,
        )
    )
    db.add(
        Staff(
            id=cashier_id,
            name="Cashier",
            role=StaffRole.CASHIER,
            pin_hash=cashier_pin_hash,
            is_active=True,
        )
    )
    await db.flush()


async def ensure_default_zone_and_seats(
    db: AsyncSession, settings: Settings | None = None
) -> None:
    """Create a default zone and seats matching config.agent_secrets if empty.

    - Creates one zone (``Standard PC`` with per-minute pricing) if no zones exist.
    - Creates a seat for each key in ``settings.agent_secrets`` (e.g. seat_1,
      seat_2...) if the seats table is empty. Seat IDs match the config keys so
      agent_secret linkage works immediately.
    """
    cfg = settings if settings is not None else get_config()

    # 1. Ensure at least one zone exists
    zones = await zone_repo.list(db)
    default_zone: Zone | None = None

    if not zones:
        default_zone = await zone_repo.create(
            db,
            name=_DEFAULT_ZONE_NAME,
            rate_per_minute_paise=_DEFAULT_ZONE_RATE_PER_MINUTE,
            rate_per_hour_paise=_DEFAULT_ZONE_RATE_PER_HOUR,
            pricing_model=PricingModel.PER_MINUTE,
        )
    else:
        default_zone = zones[0]

    # 2. Ensure seats exist for each agent_secret
    existing_seats = await seat_repo.list(db)
    if existing_seats:
        return  # already seeded

    agent_secrets = getattr(cfg, "agent_secrets", {}) or {}
    if not agent_secrets:
        return  # no secrets configured (shouldn't happen post-wizard)

    for idx, (seat_id, secret) in enumerate(sorted(agent_secrets.items()), 1):
        seat = Seat(
            id=seat_id,
            name=f"PC {idx}",
            zone_id=default_zone.id,
            status=SeatStatus.AVAILABLE,
            agent_secret=secret,
        )
        db.add(seat)

    await db.flush()

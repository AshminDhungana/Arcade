"""First-run bootstrap: ensure a default admin + cashier exist.

The launcher Setup Wizard writes credentials to ``arcade.config.json`` but
nothing previously turned them into ``Staff`` rows, so login failed on a fresh
setup. ``ensure_default_staff`` reconciles config -> DB exactly once (when the
staff table is empty) and is safe to call on every startup.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.config import Settings, get_config
from backend.core.security import hash_pin
from backend.models import Staff
from backend.models._enums import StaffRole
from backend.repositories import staff_repo

_ADMIN_DEFAULT_ID = "admin"
_ADMIN_DEFAULT_PIN = "admin"
_CASHIER_DEFAULT_ID = "cashier"
_CASHIER_DEFAULT_PIN = "cashier"


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

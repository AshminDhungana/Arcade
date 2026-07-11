"""Arcade data access repositories.

All repository functions accept an ``AsyncSession`` as their first parameter
and return SQLAlchemy model instances.  Business logic lives in services,
not repositories.
"""

from backend.repositories import (
    audit_repo,
    device_type_repo,
    event_repo,
    expense_repo,
    inventory_repo,
    invoice_repo,
    member_repo,
    package_repo,
    peak_schedule_repo,
    pos_repo,
    promotion_repo,
    reservation_repo,
    restock_repo,
    seat_repo,
    session_repo,
    shift_repo,
    staff_repo,
    voucher_repo,
    wallet_transaction_repo,
)

__all__: list[str] = [
    "audit_repo",
    "device_type_repo",
    "event_repo",
    "expense_repo",
    "inventory_repo",
    "invoice_repo",
    "member_repo",
    "package_repo",
    "peak_schedule_repo",
    "pos_repo",
    "promotion_repo",
    "reservation_repo",
    "restock_repo",
    "seat_repo",
    "session_repo",
    "shift_repo",
    "staff_repo",
    "voucher_repo",
    "wallet_transaction_repo",
]

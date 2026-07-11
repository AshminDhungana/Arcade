"""Arcade SQLAlchemy ORM models.

All models inherit from :class:`~backend.core.database.Base` and use
`Mapped[]` / `mapped_column()` (SQLAlchemy 2.0 style).  Enum fields are
stored as strings in the database.  UUID primary keys are 32-char hex.
"""

from backend.models._enums import (
    AuditAction,
    DiscountType,
    EntitlementStatus,
    EventBracketType,
    EventStatus,
    ExpenseCategory,
    InvoiceLineItemType,
    LicenseType,
    MemberTier,
    PackageType,
    PaymentMethod,
    PricingModel,
    PromotionType,
    ReservationStatus,
    SeatStatus,
    SessionStatus,
    ShiftStatus,
    StaffRole,
    VoucherStatus,
)
from backend.models.audit_log import AuditLog
from backend.models.device_type import DeviceType
from backend.models.event import Event
from backend.models.event_participant import EventParticipant
from backend.models.expense import Expense
from backend.models.invoice import Invoice
from backend.models.invoice_line_item import InvoiceLineItem
from backend.models.license_status import LicenseStatus
from backend.models.member import Member
from backend.models.menu_item import MenuItem
from backend.models.package import Package
from backend.models.package_entitlement import MemberPackageEntitlement
from backend.models.peak_schedule import PeakSchedule
from backend.models.promotion import Promotion
from backend.models.reservation import Reservation
from backend.models.restock_log import RestockLog
from backend.models.seat import Seat
from backend.models.session import GamingSession
from backend.models.session_pos_item import SessionPOSItem
from backend.models.settings import AppSettings
from backend.models.shift import Shift
from backend.models.staff import Staff
from backend.models.voucher import Voucher
from backend.models.wallet_transaction import WalletTransaction
from backend.models.zone import Zone

__all__: list[str] = [
    # enums
    "AuditAction",
    "DiscountType",
    "EntitlementStatus",
    "EventBracketType",
    "EventStatus",
    "ExpenseCategory",
    "InvoiceLineItemType",
    "LicenseType",
    "MemberTier",
    "PackageType",
    "PaymentMethod",
    "PricingModel",
    "PromotionType",
    "ReservationStatus",
    "SeatStatus",
    "SessionStatus",
    "ShiftStatus",
    "StaffRole",
    "VoucherStatus",
    # models
    "AuditLog",
    "Event",
    "EventParticipant",
    "Expense",
    "GamingSession",
    "Invoice",
    "InvoiceLineItem",
    "LicenseStatus",
    "Member",
    "MemberPackageEntitlement",
    "MenuItem",
    "Package",
    "Promotion",
    "Reservation",
    "RestockLog",
    "Seat",
    "SessionPOSItem",
    "AppSettings",
    "Shift",
    "Staff",
    "Voucher",
    "WalletTransaction",
    "Zone",
    "DeviceType",
    "PeakSchedule",
]

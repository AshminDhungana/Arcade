"""Reusable Enum classes for all ORM model fields.

All enums are stored as their member *name* in the database (string-backed),
making the schema portable and human-readable.
"""

from __future__ import annotations

from enum import Enum

# ── Seat / Zone ──────────────────────────────────────────────────────────


class SeatStatus(Enum):
    AVAILABLE = "AVAILABLE"
    IN_USE = "IN_USE"
    RESERVED = "RESERVED"
    PAUSED = "PAUSED"
    MAINTENANCE = "MAINTENANCE"
    OFFLINE = "OFFLINE"
    BOOTING = "BOOTING"
    UNREACHABLE = "UNREACHABLE"


class PricingModel(Enum):
    PER_MINUTE = "PER_MINUTE"
    FLAT_HOURLY = "FLAT_HOURLY"
    TIME_BLOCK = "TIME_BLOCK"


# ── Session ────────────────────────────────────────────────────────────────


class SessionStatus(Enum):
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    COMPLETED = "COMPLETED"
    ABANDONED = "ABANDONED"


# ── Member ───────────────────────────────────────────────────────────────


class MemberTier(Enum):
    BRONZE = "BRONZE"
    SILVER = "SILVER"
    GOLD = "GOLD"


# ── Staff ────────────────────────────────────────────────────────────────


class StaffRole(Enum):
    ADMIN = "ADMIN"
    CASHIER = "CASHIER"


# ── Shift ────────────────────────────────────────────────────────────────


class ShiftStatus(Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"


# ── Payment / Invoicing ──────────────────────────────────────────────────


class PaymentMethod(Enum):
    CASH = "CASH"
    CARD = "CARD"
    WALLET = "WALLET"
    PACKAGE = "PACKAGE"


class InvoiceLineItemType(Enum):
    TIME_CHARGE = "TIME_CHARGE"
    POS_ITEM = "POS_ITEM"
    DISCOUNT = "DISCOUNT"
    PACKAGE_CREDIT = "PACKAGE_CREDIT"


class InvoicePrintStatus(Enum):
    PENDING = "PENDING"
    PRINTED = "PRINTED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


# ── Package ──────────────────────────────────────────────────────────────


class PackageType(Enum):
    HOUR_BUNDLE = "HOUR_BUNDLE"
    DAY_PASS = "DAY_PASS"  # noqa: S105
    NIGHT_PASS = "NIGHT_PASS"  # noqa: S105
    MONTHLY = "MONTHLY"


class EntitlementStatus(Enum):
    ACTIVE = "ACTIVE"
    EXHAUSTED = "EXHAUSTED"
    EXPIRED = "EXPIRED"


# ── Promotion ──────────────────────────────────────────────────────────────


class PromotionType(Enum):
    HAPPY_HOUR = "HAPPY_HOUR"
    FLASH = "FLASH"
    FIRST_VISIT = "FIRST_VISIT"
    GROUP = "GROUP"
    BIRTHDAY = "BIRTHDAY"


class DiscountType(Enum):
    PERCENTAGE = "PERCENTAGE"
    FIXED_PAISE = "FIXED_PAISE"
    BONUS_MINUTES = "BONUS_MINUTES"


# ── Voucher ──────────────────────────────────────────────────────────────


class VoucherStatus(Enum):
    UNUSED = "UNUSED"
    REDEEMED = "REDEEMED"
    EXPIRED = "EXPIRED"


# ── Reservation ────────────────────────────────────────────────────────────


class ReservationStatus(Enum):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


# ── Expense ──────────────────────────────────────────────────────────────


class ExpenseCategory(Enum):
    RENT = "RENT"
    ELECTRICITY = "ELECTRICITY"
    INTERNET = "INTERNET"
    RESTOCK = "RESTOCK"
    HARDWARE = "HARDWARE"
    MAINTENANCE = "MAINTENANCE"
    WAGES = "WAGES"
    OTHER = "OTHER"


# ── Event ────────────────────────────────────────────────────────────────


class EventBracketType(Enum):
    SINGLE_ELIMINATION = "SINGLE_ELIMINATION"
    DOUBLE_ELIMINATION = "DOUBLE_ELIMINATION"


class EventStatus(Enum):
    UPCOMING = "UPCOMING"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"


class EventBracketGroup(Enum):
    WINNERS = "WINNERS"
    LOSERS = "LOSERS"
    GRAND_FINAL = "GRAND_FINAL"


class EventMatchStatus(Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"


# ── Audit ────────────────────────────────────────────────────────────────


class AuditAction(Enum):
    SESSION_START = "SESSION_START"
    SESSION_PAUSE = "SESSION_PAUSE"
    SESSION_RESUME = "SESSION_RESUME"
    SESSION_END = "SESSION_END"
    PAYMENT = "PAYMENT"
    WALLET_TOPUP = "WALLET_TOPUP"
    VOUCHER_GENERATED = "VOUCHER_GENERATED"
    VOUCHER_REDEEMED = "VOUCHER_REDEEMED"
    SETTINGS_CHANGED = "SETTINGS_CHANGED"
    SCREENSHOT_TAKEN = "SCREENSHOT_TAKEN"
    STAFF_LOGIN = "STAFF_LOGIN"
    STAFF_LOGOUT = "STAFF_LOGOUT"
    SEAT_MAINTENANCE_ON = "SEAT_MAINTENANCE_ON"
    SEAT_MAINTENANCE_OFF = "SEAT_MAINTENANCE_OFF"
    SHIFT_OPEN = "SHIFT_OPEN"
    SHIFT_CLOSE = "SHIFT_CLOSE"
    SEAT_RESTARTED = "SEAT_RESTARTED"
    SEAT_SHUTDOWN = "SEAT_SHUTDOWN"
    BACKUP_CREATED = "BACKUP_CREATED"
    BACKUP_PRUNED = "BACKUP_PRUNED"
    MESSAGE_SENT = "MESSAGE_SENT"
    AUDIT_IMMUTABLE = "AUDIT_IMMUTABLE"
    CHECKOUT = "CHECKOUT"
    INVENTORY_RESTOCK = "INVENTORY_RESTOCK"
    POS_ITEM_ADDED = "POS_ITEM_ADDED"
    POS_ITEM_REMOVED = "POS_ITEM_REMOVED"
    RESERVATION_CREATED = "RESERVATION_CREATED"
    RESERVATION_CANCELLED = "RESERVATION_CANCELLED"
    RESERVATION_CONFIRMED = "RESERVATION_CONFIRMED"
    RESERVATION_DELETED = "RESERVATION_DELETED"
    RESERVATION_UPDATED = "RESERVATION_UPDATED"
    WOL_SENT = "WOL_SENT"
    WOL_SUCCESS = "WOL_SUCCESS"
    WOL_TIMEOUT = "WOL_TIMEOUT"
    WOL_OVERRIDE = "WOL_OVERRIDE"
    PACKAGE_SOLD = "PACKAGE_SOLD"
    PROMOTION_APPLIED = "PROMOTION_APPLIED"
    STAFF_CREATED = "STAFF_CREATED"
    STAFF_PIN_CHANGED = "STAFF_PIN_CHANGED"
    STAFF_DEACTIVATED = "STAFF_DEACTIVATED"
    STAFF_REACTIVATED = "STAFF_REACTIVATED"
    TUYA_POWER_ON = "TUYA_POWER_ON"
    TUYA_POWER_OFF = "TUYA_POWER_OFF"
    EVENT_CREATED = "EVENT_CREATED"
    EVENT_PARTICIPANT_REGISTERED = "EVENT_PARTICIPANT_REGISTERED"
    EVENT_MATCH_RECORDED = "EVENT_MATCH_RECORDED"
    CHECKOUT_FORCED_UNPRINTED = "CHECKOUT_FORCED_UNPRINTED"
    SHIFT_CLOSE_UNPRINTED = "SHIFT_CLOSE_UNPRINTED"


# ── License ──────────────────────────────────────────────────────────────


class LicenseType(Enum):
    PERPETUAL = "PERPETUAL"
    TRIAL = "TRIAL"

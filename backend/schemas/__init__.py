"""Arcade Pydantic schemas."""

from backend.schemas.analytics import (
    AnalyticsSummary,
    BusiestHour,
    DailyRevenue,
    HealthAlert,
    MemberStats,
    TopPosItem,
    TopSpender,
    UpcomingReservation,
    WolSuccessRate,
    ZoneUtilisation,
)

# Audit / Settings
from backend.schemas.audit import AuditLogResponse
from backend.schemas.base import BaseCreateSchema, BaseResponseSchema, BaseSchema
from backend.schemas.device_type import (
    DeviceTypeCreate,
    DeviceTypeResponse,
    DeviceTypeUpdate,
)

# Event
from backend.schemas.event import (
    EventCreate,
    EventParticipantCreate,
    EventParticipantResponse,
    EventParticipantUpdate,
    EventResponse,
    EventUpdate,
)

# Health / Analytics
from backend.schemas.health import HealthMetricsRequest, HealthMetricsResponse

# Invoice / Shift
from backend.schemas.invoice import (
    InvoiceCreate,
    InvoiceLineItemCreate,
    InvoiceLineItemResponse,
    InvoiceResponse,
    InvoiceUpdate,
)

# Member / Staff
from backend.schemas.member import MemberCreate, MemberResponse, MemberUpdate

# Package
from backend.schemas.package import (
    MemberPackageEntitlementCreate,
    MemberPackageEntitlementResponse,
    MemberPackageEntitlementUpdate,
    PackageCreate,
    PackageResponse,
    PackageUpdate,
    SellPackageRequest,
)
from backend.schemas.peak_schedule import (
    PeakScheduleCreate,
    PeakScheduleResponse,
    PeakScheduleUpdate,
)

# POS
from backend.schemas.pos import (
    MenuItemCreate,
    MenuItemResponse,
    MenuItemUpdate,
    SessionPOSItemCreate,
    SessionPOSItemResponse,
)

# Promotion / Voucher
from backend.schemas.promotion import (
    PromotionCreate,
    PromotionResponse,
    PromotionUpdate,
)

# Reservation
from backend.schemas.reservation import (
    ReservationCreate,
    ReservationResponse,
    ReservationUpdate,
)

# Seat / Zone
from backend.schemas.seat import SeatCreate, SeatResponse, SeatUpdate

# Session
from backend.schemas.session import SessionCreate, SessionResponse, SessionUpdate
from backend.schemas.settings import (
    AppSettingsCreate,
    AppSettingsResponse,
    AppSettingsUpdate,
)
from backend.schemas.shift import ShiftCreate, ShiftResponse, ShiftUpdate
from backend.schemas.staff import (
    StaffCreate,
    StaffPinCheck,
    StaffResponse,
    StaffUpdate,
    TokenResponse,
)
from backend.schemas.voucher import VoucherCreate, VoucherResponse, VoucherUpdate
from backend.schemas.wallet_transaction import WalletTransactionResponse
from backend.schemas.zone import ZoneCreate, ZoneResponse, ZoneUpdate

__all__ = [
    # Base
    "BaseSchema",
    "BaseCreateSchema",
    "BaseResponseSchema",
    # Seat / Zone / Device Type
    "SeatCreate",
    "SeatUpdate",
    "SeatResponse",
    "ZoneCreate",
    "ZoneUpdate",
    "ZoneResponse",
    "PeakScheduleCreate",
    "PeakScheduleUpdate",
    "PeakScheduleResponse",
    "DeviceTypeCreate",
    "DeviceTypeUpdate",
    "DeviceTypeResponse",
    # Session
    "SessionCreate",
    "SessionUpdate",
    "SessionResponse",
    # Member / Staff
    "MemberCreate",
    "MemberUpdate",
    "MemberResponse",
    "WalletTransactionResponse",
    "StaffCreate",
    "StaffUpdate",
    "StaffResponse",
    "StaffPinCheck",
    "TokenResponse",
    # Invoice / Shift
    "InvoiceCreate",
    "InvoiceUpdate",
    "InvoiceResponse",
    "InvoiceLineItemCreate",
    "InvoiceLineItemResponse",
    "ShiftCreate",
    "ShiftUpdate",
    "ShiftResponse",
    # POS
    "MenuItemCreate",
    "MenuItemUpdate",
    "MenuItemResponse",
    "SessionPOSItemCreate",
    "SessionPOSItemResponse",
    # Package
    "PackageCreate",
    "PackageUpdate",
    "PackageResponse",
    "MemberPackageEntitlementCreate",
    "MemberPackageEntitlementUpdate",
    "MemberPackageEntitlementResponse",
    "SellPackageRequest",
    # Promotion / Voucher
    "PromotionCreate",
    "PromotionUpdate",
    "PromotionResponse",
    "VoucherCreate",
    "VoucherUpdate",
    "VoucherResponse",
    # Reservation
    "ReservationCreate",
    "ReservationUpdate",
    "ReservationResponse",
    # Audit / Settings
    "AuditLogResponse",
    "AppSettingsCreate",
    "AppSettingsUpdate",
    "AppSettingsResponse",
    # Health / Analytics
    "HealthMetricsRequest",
    "HealthMetricsResponse",
    "AnalyticsSummary",
    "BusiestHour",
    "DailyRevenue",
    "TopPosItem",
    "ZoneUtilisation",
    "TopSpender",
    "MemberStats",
    "HealthAlert",
    "UpcomingReservation",
    "WolSuccessRate",
    # Event
    "EventCreate",
    "EventUpdate",
    "EventResponse",
    "EventParticipantCreate",
    "EventParticipantUpdate",
    "EventParticipantResponse",
]

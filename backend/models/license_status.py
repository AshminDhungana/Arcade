"""LicenseStatus model — read-only cache for display.

This table is a **read-only cache** for display purposes (FR-LIC-014).
It is populated by the Launcher after a successful license check and
surfaced at ``GET /api/settings/license``. It is *never* the source of
truth — that is always the signed license.key file plus the embedded
public key, verified by the Launcher before the database or server
process even start.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import Date, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database import Base
from backend.models._enums import LicenseType
from backend.models._types import StrEnumColumn


class LicenseStatus(Base):
    __tablename__ = "license_status"

    id: Mapped[str] = mapped_column(
        String(32), primary_key=True, default=lambda: "current"
    )
    cafe_name: Mapped[str] = mapped_column(String(255), nullable=False)
    hardware_id: Mapped[str] = mapped_column(String(64), nullable=False)
    license_type: Mapped[LicenseType] = mapped_column(
        StrEnumColumn(LicenseType, 10), nullable=False
    )
    issue_date: Mapped[date] = mapped_column(Date, nullable=False)
    trial_expires_at: Mapped[date | None] = mapped_column(Date)
    last_verified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

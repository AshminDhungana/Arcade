"""MemberPackageEntitlement model — a member's purchased time package."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database import Base
from backend.models._enums import EntitlementStatus


class MemberPackageEntitlement(Base):
    __tablename__ = "member_package_entitlements"

    id: Mapped[str] = mapped_column(
        String(32), primary_key=True, default=lambda: __import__("uuid").uuid4().hex
    )
    member_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("members.id"), nullable=False
    )
    package_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("packages.id"), nullable=False
    )
    remaining_minutes: Mapped[int]
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    purchased_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    status: Mapped[EntitlementStatus] = mapped_column(
        String(10), nullable=False, default=EntitlementStatus.ACTIVE
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )

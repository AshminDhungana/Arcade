"""Staff model — cafe staff with PIN-based auth."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.database import Base
from backend.models._enums import StaffRole
from backend.models._types import StrEnumColumn

if TYPE_CHECKING:
    from backend.models.staff_zone import StaffZone


class Staff(Base):
    __tablename__ = "staff"

    id: Mapped[str] = mapped_column(
        String(32), primary_key=True, default=lambda: __import__("uuid").uuid4().hex
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[StaffRole] = mapped_column(
        StrEnumColumn(StaffRole, 10), nullable=False
    )
    pin_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    token_version: Mapped[int] = mapped_column(default=0)
    failed_attempts: Mapped[int] = mapped_column(default=0)
    lockout_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(default=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )

    # Relationships
    assigned_zones: Mapped[list[StaffZone]] = relationship(
        "StaffZone",
        foreign_keys="StaffZone.staff_id",
        back_populates="staff",
        cascade="all, delete-orphan",
    )

"""Zone model — defines seating areas and their pricing."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.database import Base
from backend.models._enums import PricingModel
from backend.models._types import StrEnumColumn

if TYPE_CHECKING:
    from backend.models.staff_zone import StaffZone


class Zone(Base):
    __tablename__ = "zones"

    id: Mapped[str] = mapped_column(
        String(32), primary_key=True, default=lambda: __import__("uuid").uuid4().hex
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    rate_per_minute_paise: Mapped[int]
    rate_per_hour_paise: Mapped[int]
    pricing_model: Mapped[PricingModel] = mapped_column(
        StrEnumColumn(PricingModel, 25), nullable=False, default=PricingModel.PER_MINUTE
    )
    block_minutes: Mapped[int | None]
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationships
    staff_assignments: Mapped[list[StaffZone]] = relationship(
        "StaffZone", back_populates="zone", passive_deletes=True
    )

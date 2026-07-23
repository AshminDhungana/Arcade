"""Staff-Zone assignment — links staff to zones they can access."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.core.database import Base

if TYPE_CHECKING:
    from backend.models.staff import Staff
    from backend.models.zone import Zone


class StaffZone(Base):
    __tablename__ = "staff_zones"

    staff_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("staff.id", ondelete="CASCADE"), primary_key=True
    )
    zone_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("zones.id", ondelete="CASCADE"), primary_key=True
    )
    granted_by: Mapped[str] = mapped_column(
        String(32), ForeignKey("staff.id"), nullable=False
    )
    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    # Relationships
    staff: Mapped[Staff] = relationship(
        "Staff", foreign_keys=[staff_id], back_populates="assigned_zones"
    )
    zone: Mapped[Zone] = relationship("Zone", back_populates="staff_assignments")
    granter: Mapped[Staff] = relationship("Staff", foreign_keys=[granted_by])

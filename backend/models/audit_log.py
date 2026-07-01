"""AuditLog model — immutable activity trail.

The audit log has no update or delete operations exposed at the repository layer.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database import Base
from backend.models._enums import AuditAction
from backend.models._types import StrEnumColumn


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[str] = mapped_column(
        String(32), primary_key=True, default=lambda: __import__("uuid").uuid4().hex
    )
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
        index=True,
    )
    staff_id: Mapped[str | None] = mapped_column(String(32), ForeignKey("staff.id"))
    action: Mapped[AuditAction] = mapped_column(
        StrEnumColumn(AuditAction, 25), nullable=False, index=True
    )
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[str] = mapped_column(String(32), nullable=False)
    detail: Mapped[str | None] = mapped_column(Text)

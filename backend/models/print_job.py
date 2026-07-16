"""Print-job outbox model.

One row per invoice that still needs (or needed) a receipt print. The
background scheduler retries rows whose ``next_retry_at`` is due. A row is
deleted once the print succeeds (or the invoice is marked SKIPPED).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database import Base
from backend.models._types import UTCDatetime


class PrintJob(Base):
    __tablename__ = "print_jobs"

    id: Mapped[str] = mapped_column(
        String(32), primary_key=True, default=lambda: uuid.uuid4().hex
    )
    invoice_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("invoices.id"), nullable=False, unique=True, index=True
    )
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    next_retry_at: Mapped[datetime | None] = mapped_column(UTCDatetime, nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        UTCDatetime, default=lambda: datetime.now(UTC), nullable=False
    )

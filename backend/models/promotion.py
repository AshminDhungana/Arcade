"""Promotion model — discounts and special offers."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database import Base
from backend.models._enums import DiscountType, PromotionType
from backend.models._types import StrEnumColumn


class Promotion(Base):
    __tablename__ = "promotions"

    id: Mapped[str] = mapped_column(
        String(32), primary_key=True, default=lambda: __import__("uuid").uuid4().hex
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[PromotionType] = mapped_column(
        StrEnumColumn(PromotionType, 20), nullable=False
    )
    discount_type: Mapped[DiscountType] = mapped_column(
        StrEnumColumn(DiscountType, 15), nullable=False
    )
    discount_value: Mapped[int] = mapped_column(default=0)
    active_days: Mapped[str | None] = mapped_column(String(255))
    active_from_hour: Mapped[int | None]
    active_to_hour: Mapped[int | None]
    min_group_size: Mapped[int | None]
    zone_restriction_id: Mapped[str | None] = mapped_column(String(32))
    is_active: Mapped[bool] = mapped_column(default=True)
    valid_from: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    valid_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

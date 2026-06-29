"""Zone model — defines seating areas and their pricing."""

from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database import Base
from backend.models._enums import PricingModel


class Zone(Base):
    __tablename__ = "zones"

    id: Mapped[str] = mapped_column(
        String(32), primary_key=True, default=lambda: __import__("uuid").uuid4().hex
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    rate_per_minute_paise: Mapped[int]
    rate_per_hour_paise: Mapped[int]
    pricing_model: Mapped[PricingModel] = mapped_column(
        String(25), nullable=False, default=PricingModel.PER_MINUTE
    )
    block_minutes: Mapped[int | None]

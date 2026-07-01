"""Package model — time bundle types sold to members."""

from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database import Base
from backend.models._enums import PackageType
from backend.models._types import StrEnumColumn


class Package(Base):
    __tablename__ = "packages"

    id: Mapped[str] = mapped_column(
        String(32), primary_key=True, default=lambda: __import__("uuid").uuid4().hex
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[PackageType] = mapped_column(
        StrEnumColumn(PackageType, 20), nullable=False
    )
    total_minutes: Mapped[int]
    price_paise: Mapped[int]
    valid_days: Mapped[int | None]
    zone_restriction_id: Mapped[str | None] = mapped_column(String(32))
    is_active: Mapped[bool] = mapped_column(default=True)

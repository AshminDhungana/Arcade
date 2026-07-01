"""Member model — gaming cafe members with wallet and loyalty."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database import Base
from backend.models._enums import MemberTier
from backend.models._types import StrEnumColumn


class Member(Base):
    __tablename__ = "members"

    id: Mapped[str] = mapped_column(
        String(32), primary_key=True, default=lambda: __import__("uuid").uuid4().hex
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )
    wallet_balance_paise: Mapped[int] = mapped_column(default=0)
    loyalty_points: Mapped[int] = mapped_column(default=0)
    tier: Mapped[MemberTier] = mapped_column(
        StrEnumColumn(MemberTier, 10), nullable=False, default=MemberTier.BRONZE
    )
    birth_month: Mapped[int | None]
    total_visits: Mapped[int] = mapped_column(default=0)
    total_seconds_played: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )

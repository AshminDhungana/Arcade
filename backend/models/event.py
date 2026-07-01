"""Event model — tournaments and special events."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database import Base
from backend.models._enums import EventBracketType, EventStatus
from backend.models._types import StrEnumColumn


class Event(Base):
    __tablename__ = "events"

    id: Mapped[str] = mapped_column(
        String(32), primary_key=True, default=lambda: __import__("uuid").uuid4().hex
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    game_title: Mapped[str] = mapped_column(String(255), nullable=False)
    event_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    entry_fee_paise: Mapped[int] = mapped_column(default=0)
    prize_pool_paise: Mapped[int] = mapped_column(default=0)
    bracket_type: Mapped[EventBracketType] = mapped_column(
        StrEnumColumn(EventBracketType, 25),
        nullable=False,
        default=EventBracketType.SINGLE_ELIMINATION,
    )
    status: Mapped[EventStatus] = mapped_column(
        StrEnumColumn(EventStatus, 10), nullable=False, default=EventStatus.UPCOMING
    )

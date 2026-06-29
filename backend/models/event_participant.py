"""EventParticipant model — participants in an event/tournament."""

from __future__ import annotations

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database import Base


class EventParticipant(Base):
    __tablename__ = "event_participants"

    id: Mapped[str] = mapped_column(
        String(32), primary_key=True, default=lambda: __import__("uuid").uuid4().hex
    )
    event_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("events.id"), nullable=False
    )
    member_id: Mapped[str | None] = mapped_column(String(32))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    seat_id: Mapped[str | None] = mapped_column(String(32))
    bracket_position: Mapped[int | None]
    eliminated: Mapped[bool] = mapped_column(default=False)

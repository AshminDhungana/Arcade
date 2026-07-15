"""EventMatch model — a single node in a tournament bracket (DAG).

Each match has up to two participant slots. Recording a result sets
``winner_id`` and advances the winner to ``next_match_id`` (and, in double
elimination, drops the loser to ``next_loser_match_id``).
"""

from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from backend.core.database import Base
from backend.models._enums import EventBracketGroup, EventMatchStatus
from backend.models._types import StrEnumColumn


class EventMatch(Base):
    __tablename__ = "event_matches"

    id: Mapped[str] = mapped_column(
        String(32), primary_key=True, default=lambda: __import__("uuid").uuid4().hex
    )
    event_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("events.id"), nullable=False, index=True
    )
    bracket_group: Mapped[EventBracketGroup] = mapped_column(
        StrEnumColumn(EventBracketGroup, 15),
        nullable=False,
        default=EventBracketGroup.WINNERS,
    )
    round: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    slot_a_id: Mapped[str | None] = mapped_column(
        String(32), ForeignKey("event_participants.id"), nullable=True
    )
    slot_b_id: Mapped[str | None] = mapped_column(
        String(32), ForeignKey("event_participants.id"), nullable=True
    )
    winner_id: Mapped[str | None] = mapped_column(
        String(32), ForeignKey("event_participants.id"), nullable=True
    )
    status: Mapped[EventMatchStatus] = mapped_column(
        StrEnumColumn(EventMatchStatus, 10),
        nullable=False,
        default=EventMatchStatus.PENDING,
    )
    next_match_id: Mapped[str | None] = mapped_column(
        String(32), ForeignKey("event_matches.id"), nullable=True
    )
    next_loser_match_id: Mapped[str | None] = mapped_column(
        String(32), ForeignKey("event_matches.id"), nullable=True
    )

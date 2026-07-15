from backend.models._enums import (
    AuditAction,
    EventBracketGroup,
    EventMatchStatus,
)
from backend.models.event_match import EventMatch


def test_event_enums_exist() -> None:
    assert EventBracketGroup.WINNERS.value == "WINNERS"
    assert EventMatchStatus.PENDING.value == "PENDING"
    assert AuditAction.EVENT_CREATED.value == "EVENT_CREATED"


def test_event_match_model_columns() -> None:
    cols = {c.name for c in EventMatch.__table__.columns}
    for expected in {
        "id",
        "event_id",
        "bracket_group",
        "round",
        "slot_a_id",
        "slot_b_id",
        "winner_id",
        "status",
        "next_match_id",
        "next_loser_match_id",
    }:
        assert expected in cols
    assert EventMatch.__tablename__ == "event_matches"

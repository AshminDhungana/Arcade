from backend.models._enums import (
    AuditAction,
    EventBracketGroup,
    EventMatchStatus,
)


def test_event_enums_exist() -> None:
    assert EventBracketGroup.WINNERS.value == "WINNERS"
    assert EventMatchStatus.PENDING.value == "PENDING"
    assert AuditAction.EVENT_CREATED.value == "EVENT_CREATED"

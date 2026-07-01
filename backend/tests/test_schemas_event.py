from datetime import UTC, datetime

from backend.models._enums import EventBracketType, EventStatus
from backend.schemas.event import EventCreate, EventResponse


class TestEventCreate:
    def test_valid(self) -> None:
        now = datetime.now(UTC)
        e = EventCreate(
            name="Summer Tournament",
            game_title="CS2",
            event_date=now,
        )
        assert e.name == "Summer Tournament"
        assert e.bracket_type == EventBracketType.SINGLE_ELIMINATION
        assert e.status == EventStatus.UPCOMING


class TestEventResponse:
    def test_from_orm(self) -> None:
        now = datetime.now(UTC)

        class FakeEvent:
            id = "event1"
            name = "Summer Tournament"
            game_title = "CS2"
            event_date = now
            entry_fee_paise = 0
            prize_pool_paise = 0
            bracket_type = EventBracketType.SINGLE_ELIMINATION
            status = EventStatus.UPCOMING

        r = EventResponse.model_validate(FakeEvent())
        assert r.id == "event1"

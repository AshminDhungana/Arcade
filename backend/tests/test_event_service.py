import datetime

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from backend.core.database import Base
from backend.models._enums import AuditAction, EventBracketGroup, EventMatchStatus
from backend.models.event_match import EventMatch
from backend.repositories import event_match_repo, event_repo


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


@pytest_asyncio.fixture
async def db() -> AsyncSession:
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as session:
        yield session
    await engine.dispose()


@pytest.mark.asyncio
async def test_match_repo_roundtrip(db: AsyncSession) -> None:
    event = await event_repo.create_event(
        db,
        name="Cup",
        game_title="Tekken",
        event_date=datetime.datetime(2026, 8, 1, 18, 0, 0, tzinfo=datetime.UTC),
    )
    p1 = await event_repo.create_participant(db, event_id=event.id, name="A")
    p2 = await event_repo.create_participant(db, event_id=event.id, name="B")
    m = await event_match_repo.create_match(
        db,
        event_id=event.id,
        bracket_group="WINNERS",
        round=1,
        slot_a_id=p1.id,
        slot_b_id=p2.id,
    )
    fetched = await event_match_repo.get_match_by_id(db, m.id)
    assert fetched is not None and fetched.slot_a_id == p1.id
    matches = await event_match_repo.list_matches_by_event(db, event.id)
    assert len(matches) == 1

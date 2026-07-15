import datetime as dt
from datetime import UTC, datetime

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from backend.core.database import Base
from backend.models._enums import (
    AuditAction,
    EventBracketGroup,
    EventBracketType,
    EventMatchStatus,
    EventStatus,
)
from backend.models.event_match import EventMatch
from backend.models.staff import Staff
from backend.repositories import event_match_repo, event_repo, member_repo, staff_repo
from backend.services import event_service


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
        event_date=dt.datetime(2026, 8, 1, 18, 0, 0, tzinfo=dt.UTC),
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


async def _make_staff(db: AsyncSession, role: str = "ADMIN") -> Staff:
    return await staff_repo.create(
        db,
        name="S",
        pin_hash="$argon2id$v=19$m=102400,t=2,p=8$abc",
        role=role,
    )


@pytest.mark.asyncio
async def test_create_event(db: AsyncSession) -> None:
    staff = await _make_staff(db)
    event = await event_service.EventService.create_event(
        db,
        name="Spring Cup",
        game_title="Tekken 8",
        event_date=datetime(2026, 8, 1, 18, 0, tzinfo=UTC),
        entry_fee_paise=5000,
        prize_pool_paise=20000,
        bracket_type=EventBracketType.SINGLE_ELIMINATION,
        staff=staff,
    )
    assert event.id
    assert event.status == EventStatus.UPCOMING
    assert event.entry_fee_paise == 5000


@pytest.mark.asyncio
async def test_register_deducts_from_member_wallet(db: AsyncSession) -> None:
    staff = await _make_staff(db)
    member = await member_repo.create(
        db, name="Mem", phone="9800000001", wallet_balance_paise=10000
    )
    event = await event_service.EventService.create_event(
        db,
        name="Cup",
        game_title="Game",
        event_date=datetime(2026, 8, 1, 18, 0, tzinfo=UTC),
        entry_fee_paise=3000,
        bracket_type=EventBracketType.SINGLE_ELIMINATION,
        staff=staff,
    )
    part = await event_service.EventService.register_participant(
        db, event_id=event.id, member_id=member.id, seat_id=None, name=None, staff=staff
    )
    refreshed = await member_repo.get_by_id(db, member.id)
    assert refreshed.wallet_balance_paise == 7000
    assert part.member_id == member.id
    assert part.name == "Mem"


@pytest.mark.asyncio
async def test_register_walkin_no_deduction(db: AsyncSession) -> None:
    staff = await _make_staff(db)
    event = await event_service.EventService.create_event(
        db,
        name="Cup",
        game_title="Game",
        event_date=datetime(2026, 8, 1, 18, 0, tzinfo=UTC),
        entry_fee_paise=3000,
        bracket_type=EventBracketType.SINGLE_ELIMINATION,
        staff=staff,
    )
    part = await event_service.EventService.register_participant(
        db,
        event_id=event.id,
        member_id=None,
        seat_id=None,
        name="Walk-in Wilma",
        staff=staff,
    )
    assert part.member_id is None and part.name == "Walk-in Wilma"


@pytest.mark.asyncio
async def test_register_insufficient_funds(db: AsyncSession) -> None:
    staff = await _make_staff(db)
    member = await member_repo.create(
        db, name="Broke", phone="9800000002", wallet_balance_paise=1000
    )
    event = await event_service.EventService.create_event(
        db,
        name="Cup",
        game_title="Game",
        event_date=datetime(2026, 8, 1, 18, 0, tzinfo=UTC),
        entry_fee_paise=3000,
        bracket_type=EventBracketType.SINGLE_ELIMINATION,
        staff=staff,
    )
    with pytest.raises(event_service.InsufficientFundsError):
        await event_service.EventService.register_participant(
            db,
            event_id=event.id,
            member_id=member.id,
            seat_id=None,
            name=None,
            staff=staff,
        )


async def _register_n(db, staff, event, n, with_members=False):
    parts = []
    for i in range(n):
        if with_members:
            m = await member_repo.create(
                db, name=f"M{i}", phone=f"9800001{i:03d}", wallet_balance_paise=100000
            )
            p = await event_service.EventService.register_participant(
                db,
                event_id=event.id,
                member_id=m.id,
                seat_id=None,
                name=None,
                staff=staff,
            )
        else:
            p = await event_service.EventService.register_participant(
                db,
                event_id=event.id,
                member_id=None,
                seat_id=None,
                name=f"P{i}",
                staff=staff,
            )
        parts.append(p)
    return parts


@pytest.mark.asyncio
async def test_single_elim_4player_playthrough(db: AsyncSession) -> None:
    staff = await _make_staff(db)
    event = await event_service.EventService.create_event(
        db,
        name="Cup",
        game_title="G",
        event_date=datetime(2026, 8, 1, 18, 0, tzinfo=UTC),
        entry_fee_paise=0,
        bracket_type=EventBracketType.SINGLE_ELIMINATION,
        staff=staff,
    )
    parts = await _register_n(db, staff, event, 4)
    matches = await event_match_repo.list_matches_by_event(db, event.id)
    assert len(matches) == 3  # 4 players -> 3 matches

    # Play round 1: parts[0] and parts[2] win.
    r1 = [m for m in matches if m.round == 1]
    for m in r1:
        winner = (
            m.slot_a_id
            if m.slot_a_id == parts[0].id or m.slot_a_id == parts[2].id
            else m.slot_b_id
        )
        await event_service.EventService.record_match_result(
            db, event_id=event.id, match_id=m.id, winner_id=winner, staff=staff
        )
    # Final: the winner between parts[0] and parts[2].
    final = [m for m in matches if m.next_match_id is None][0]
    await event_service.EventService.record_match_result(
        db, event_id=event.id, match_id=final.id, winner_id=parts[0].id, staff=staff
    )
    summary = await event_service.EventService.get_event_summary(db, event_id=event.id)
    assert summary["is_complete"] is True
    assert summary["champion_participant_id"] == parts[0].id
    # Exactly one champion; the other three eliminated.
    survivors = [p for p in parts if not p.eliminated]
    assert survivors == [parts[0]]


@pytest.mark.asyncio
async def test_double_elim_4player_playthrough(db: AsyncSession) -> None:
    staff = await _make_staff(db)
    event = await event_service.EventService.create_event(
        db,
        name="DE",
        game_title="G",
        event_date=datetime(2026, 8, 1, 18, 0, tzinfo=UTC),
        entry_fee_paise=0,
        bracket_type=EventBracketType.DOUBLE_ELIMINATION,
        staff=staff,
    )
    parts = await _register_n(db, staff, event, 4)
    matches = await event_match_repo.list_matches_by_event(db, event.id)
    # 4 players double elim: WB 3 + LB 2 + GF 1 = 6 matches.
    assert len(matches) == 6

    # Drive every match: always advance parts[0] (the eventual champion).
    # Repeat until the event is COMPLETED.
    for _ in range(20):
        pending = [
            m
            for m in await event_match_repo.list_matches_by_event(db, event.id)
            if m.status.value == "PENDING"
            and m.slot_a_id is not None
            and m.slot_b_id is not None
        ]
        if not pending:
            break
        m = pending[0]
        winner = m.slot_a_id if m.slot_a_id == parts[0].id else m.slot_b_id
        await event_service.EventService.record_match_result(
            db, event_id=event.id, match_id=m.id, winner_id=winner, staff=staff
        )
    summary = await event_service.EventService.get_event_summary(db, event_id=event.id)
    assert summary["is_complete"] is True
    assert summary["champion_participant_id"] == parts[0].id
    assert len([p for p in parts if not p.eliminated]) == 1


@pytest.mark.asyncio
async def test_summary_revenue_and_counts(db: AsyncSession) -> None:
    staff = await _make_staff(db)
    event = await event_service.EventService.create_event(
        db,
        name="Cup",
        game_title="G",
        event_date=datetime(2026, 8, 1, 18, 0, tzinfo=UTC),
        entry_fee_paise=1000,
        prize_pool_paise=5000,
        bracket_type=EventBracketType.SINGLE_ELIMINATION,
        staff=staff,
    )
    await _register_n(db, staff, event, 2, with_members=True)
    summary = await event_service.EventService.get_event_summary(db, event_id=event.id)
    assert summary["participant_count"] == 2
    assert summary["entry_fee_paise"] == 1000
    assert summary["entry_fee_revenue_paise"] == 2000  # 2 * 1000
    assert summary["prize_pool_paise"] == 5000

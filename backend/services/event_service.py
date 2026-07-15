"""EventService — tournament lifecycle: create, register, record results, summarize.

Bracket generation is delegated to :func:`_ensure_bracket` (implemented in the
next task); for now create/register store data and registration is open until
the first match result is recorded.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import TYPE_CHECKING, Any

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models._enums import (
    AuditAction,
    EventBracketGroup,
    EventBracketType,
    EventMatchStatus,
    EventStatus,
    PaymentMethod,
)
from backend.models.event_match import EventMatch
from backend.models.staff import Staff
from backend.repositories import (
    event_match_repo,
    event_repo,
    member_repo,
    wallet_transaction_repo,
)
from backend.services import audit_service

if TYPE_CHECKING:
    from backend.models.event import Event
    from backend.models.event_participant import EventParticipant

logger = logging.getLogger(__name__)


class EventNotFoundError(HTTPException):
    def __init__(self, event_id: str) -> None:
        super().__init__(status_code=404, detail=f"Event {event_id} not found")


class EventParticipantNotFoundError(HTTPException):
    def __init__(self, participant_id: str) -> None:
        super().__init__(
            status_code=404, detail=f"Participant {participant_id} not found"
        )


class EventMatchNotFoundError(HTTPException):
    def __init__(self, match_id: str) -> None:
        super().__init__(status_code=404, detail=f"Match {match_id} not found")


class InsufficientFundsError(HTTPException):
    def __init__(self, needed: int, have: int) -> None:
        super().__init__(
            status_code=400,
            detail=(
                f"Insufficient wallet balance: need {needed} paise, have {have} paise"
            ),
        )


class EventAlreadyStartedError(HTTPException):
    def __init__(self, event_id: str) -> None:
        super().__init__(
            status_code=409,
            detail=f"Event {event_id} has started; registration is closed",
        )


class EventService:
    @staticmethod
    async def create_event(
        db: AsyncSession,
        *,
        name: str,
        game_title: str,
        event_date: datetime,
        entry_fee_paise: int = 0,
        prize_pool_paise: int = 0,
        bracket_type: EventBracketType = EventBracketType.SINGLE_ELIMINATION,
        staff: Staff | None = None,
    ) -> Event:
        event = await event_repo.create_event(
            db,
            name=name,
            game_title=game_title,
            event_date=event_date,
            entry_fee_paise=entry_fee_paise,
            prize_pool_paise=prize_pool_paise,
            bracket_type=bracket_type.value,
            status=EventStatus.UPCOMING.value,
        )
        await audit_service.log(
            db,
            action=AuditAction.EVENT_CREATED,
            entity_type="event",
            entity_id=event.id,
            staff_id=staff.id if staff else None,
            detail=f"Created {bracket_type.value} event '{name}'",
        )
        return event

    @staticmethod
    async def _list_events(db: AsyncSession) -> list[Event]:
        return list(await event_repo.list_events(db))

    @staticmethod
    async def _get_event_or_404(db: AsyncSession, event_id: str) -> Event:
        event = await event_repo.get_event_by_id(db, event_id)
        if event is None:
            raise EventNotFoundError(event_id)
        return event

    @staticmethod
    async def register_participant(
        db: AsyncSession,
        *,
        event_id: str,
        member_id: str | None = None,
        seat_id: str | None = None,
        name: str | None = None,
        staff: Staff | None = None,
    ) -> EventParticipant:
        event = await event_repo.get_event_by_id(db, event_id)
        if event is None:
            raise EventNotFoundError(event_id)
        # Registration closes once any match result exists.
        existing_matches = await event_match_repo.list_matches_by_event(db, event.id)
        if existing_matches and any(
            m.status.value == "COMPLETED" for m in existing_matches
        ):
            raise EventAlreadyStartedError(event_id)

        resolved_name = name
        if member_id is not None:
            member = await member_repo.get_by_id(db, member_id)
            if member is None:
                raise HTTPException(
                    status_code=404, detail=f"Member {member_id} not found"
                )
            if resolved_name is None:
                resolved_name = member.name
            # Deduct entry fee from wallet (cash collected at counter for walk-ins).
            if event.entry_fee_paise > 0:
                if member.wallet_balance_paise < event.entry_fee_paise:
                    raise InsufficientFundsError(
                        event.entry_fee_paise, member.wallet_balance_paise
                    )
                member.wallet_balance_paise -= event.entry_fee_paise
                member = await member_repo.update(db, member)
                await wallet_transaction_repo.create(
                    db,
                    member_id=member.id,
                    type="EVENT_ENTRY",
                    amount_paise=-event.entry_fee_paise,
                    balance_after_paise=member.wallet_balance_paise,
                    payment_method=PaymentMethod.WALLET.value,
                    staff_id=staff.id if staff else None,
                    reference_id=event.id,
                )
        elif not resolved_name:
            raise HTTPException(
                status_code=400,
                detail="name is required for walk-in participants (no member_id)",
            )

        bracket_position = len(await event_repo.list_participants(db, event.id))
        participant = await event_repo.create_participant(
            db,
            event_id=event.id,
            name=resolved_name,
            member_id=member_id,
            seat_id=seat_id,
            bracket_position=bracket_position,
        )
        await audit_service.log(
            db,
            action=AuditAction.EVENT_PARTICIPANT_REGISTERED,
            entity_type="event",
            entity_id=event.id,
            staff_id=staff.id if staff else None,
            detail=f"Registered participant {participant.id} ({resolved_name})",
        )
        # Lazily build/refresh the bracket (no-op until implemented next task).
        await EventService._ensure_bracket(db, event)
        return participant

    @staticmethod
    async def _ensure_bracket(db: AsyncSession, event: Event) -> None:
        """Lazily build the bracket when it becomes knowable.

        - Single elimination: as soon as >=2 participants exist (byes pad to a
          power of 2). Regenerated if more join before the first result.
        - Double elimination: only when the count is a power of 2 (else defer; the
          400 is raised at record time if still not a power of 2).
        """
        participants = await event_repo.list_participants(db, event.id)
        matches = await event_match_repo.list_matches_by_event(db, event.id)
        started = bool(matches) and any(m.status.value == "COMPLETED" for m in matches)
        if started:
            return
        ids = [p.id for p in participants]
        if event.bracket_type == EventBracketType.SINGLE_ELIMINATION:
            if len(ids) < 2:
                return
        else:  # double elimination requires power of 2
            if len(ids) < 2 or (len(ids) & (len(ids) - 1)) != 0:
                return
        if matches:
            await event_match_repo.delete_matches_by_event(db, event.id)
        await _instantiate_bracket(db, event, ids)

    @staticmethod
    async def record_match_result(
        db: AsyncSession,
        *,
        event_id: str,
        match_id: str,
        winner_id: str,
        staff: Staff | None = None,
    ) -> EventMatch | None:
        event = await event_repo.get_event_by_id(db, event_id)
        if event is None:
            raise EventNotFoundError(event_id)
        match = await event_match_repo.get_match_by_id(db, match_id)
        if match is None or match.event_id != event_id:
            raise EventMatchNotFoundError(match_id)
        if match.status.value == "COMPLETED":
            raise MatchAlreadyRecordedError(match_id)
        slot_a = match.slot_a_id
        slot_b = match.slot_b_id
        if slot_a is None or slot_b is None:
            raise HTTPException(
                status_code=400, detail="Match is not ready (a slot is empty/bye)"
            )
        if winner_id != slot_a and winner_id != slot_b:
            raise HTTPException(
                status_code=400,
                detail="winner_id must be one of the two match participants",
            )
        loser_id = slot_b if slot_a == winner_id else slot_a
        match.winner_id = winner_id
        match.status = EventMatchStatus.COMPLETED
        await event_match_repo.update_match(db, match)

        await _advance(db, match, winner_id, is_winner=True)
        if match.next_loser_match_id is not None:
            await _advance(db, match, loser_id, is_winner=False)
        else:
            loser = await event_repo.get_participant_by_id(db, loser_id)
            if loser is not None:
                loser.eliminated = True
                await event_repo.update_participant(db, loser)

        if match.next_match_id is None:
            event.status = EventStatus.COMPLETED
            await event_repo.update_event(db, event)

        await audit_service.log(
            db,
            action=AuditAction.EVENT_MATCH_RECORDED,
            entity_type="event",
            entity_id=event.id,
            staff_id=staff.id if staff else None,
            detail=f"Match {match.id}: winner {winner_id}, loser {loser_id}",
        )
        return match

    @staticmethod
    async def get_event_summary(db: AsyncSession, *, event_id: str) -> dict[str, Any]:
        event = await event_repo.get_event_by_id(db, event_id)
        if event is None:
            raise EventNotFoundError(event_id)
        participants = list(await event_repo.list_participants(db, event_id))
        matches = list(await event_match_repo.list_matches_by_event(db, event_id))
        completed = [m for m in matches if m.status.value == "COMPLETED"]
        champion = None
        for m in matches:
            if m.next_match_id is None and m.winner_id is not None:
                champion = m.winner_id
        return {
            "event": event,
            "participant_count": len(participants),
            "participants": participants,
            "match_count": len(matches),
            "completed_match_count": len(completed),
            "prize_pool_paise": event.prize_pool_paise,
            "entry_fee_paise": event.entry_fee_paise,
            "entry_fee_revenue_paise": len(participants) * event.entry_fee_paise,
            "champion_participant_id": champion,
            "is_complete": event.status == EventStatus.COMPLETED,
        }


def _next_power_of_two(n: int) -> int:
    p = 1
    while p < n:
        p *= 2
    return p


def _standard_seeding(p: int) -> list[int]:
    """0-indexed seeds in round-1 slot order with complementary pairings.

    Pair j is (order[2j], order[2j+1]) and order[2j] + order[2j+1] == p-1, so a
    bye seed (>= n, where n is the real participant count) is always paired
    with a real seed (never bye-vs-bye).
    """
    if p <= 1:
        return [0]
    if p == 2:
        return [0, 1]
    half = _standard_seeding(p // 2)
    second = [p - 1 - x for x in half]
    return [v for pair in zip(half, second, strict=True) for v in pair]


def _build_single_elim_spec(participant_ids: list[str]) -> list[dict[str, Any]]:
    n = len(participant_ids)
    p = _next_power_of_two(n)
    seeds = [participant_ids[i] if i < n else None for i in range(p)]
    order = _standard_seeding(p)
    k = p.bit_length() - 1
    matches: list[dict[str, Any]] = []
    wb_idx: dict[tuple[int, int], int] = {}
    for r in range(1, k + 1):
        count = p // (2**r)
        for i in range(count):
            a = seeds[order[2 * i]] if r == 1 else None
            b = seeds[order[2 * i + 1]] if r == 1 else None
            winner_to = (r + 1, i // 2) if r < k else None
            matches.append(
                {
                    "group": EventBracketGroup.WINNERS,
                    "round": r,
                    "slot_a": a,
                    "slot_b": b,
                    "winner_to": winner_to,
                    "loser_to": None,
                }
            )
            wb_idx[(r, i)] = len(matches) - 1
    for m in matches:
        wt = m["winner_to"]
        m["winner_to"] = wb_idx[wt] if wt is not None else None
    return matches


def _build_double_elim_spec(participant_ids: list[str]) -> list[dict[str, Any]]:
    n = len(participant_ids)
    if n & (n - 1) != 0:
        raise HTTPException(
            status_code=400,
            detail="Double elimination requires a power-of-2 number of participants",
        )
    p = n
    k = p.bit_length() - 1
    # Degenerate 2-player double elimination: one WB match feeding a GF.
    if p == 2:
        return [
            {
                "group": EventBracketGroup.WINNERS,
                "round": 1,
                "slot_a": participant_ids[0],
                "slot_b": participant_ids[1],
                "winner_to": 1,
                "loser_to": 1,
            },
            {
                "group": EventBracketGroup.GRAND_FINAL,
                "round": 1,
                "slot_a": None,
                "slot_b": None,
                "winner_to": None,
                "loser_to": None,
            },
        ]
    order = _standard_seeding(p)
    matches: list[dict[str, Any]] = []
    wb_idx: dict[tuple[int, int], int] = {}
    for r in range(1, k + 1):
        count = p // (2**r)
        for i in range(count):
            winner_to = (r + 1, i // 2) if r < k else None
            matches.append(
                {
                    "group": EventBracketGroup.WINNERS,
                    "round": r,
                    "slot_a": participant_ids[order[2 * i]] if r == 1 else None,
                    "slot_b": participant_ids[order[2 * i + 1]] if r == 1 else None,
                    "winner_to": winner_to,
                    "loser_to": None,
                }
            )
            wb_idx[(r, i)] = len(matches) - 1
    for r in range(1, k + 1):
        count = p // (2**r)
        for i in range(count):
            wt = matches[wb_idx[(r, i)]]["winner_to"]
            matches[wb_idx[(r, i)]]["winner_to"] = (
                wb_idx[wt] if wt is not None else None
            )
    r_lb = 2 * k - 2
    sizes: list[int] = []
    for t in range(1, r_lb + 1):
        if t <= 2:
            sizes.append(p // 4)
        else:
            sizes.append(p // (2 ** (2 + (t - 1) // 2)))
    lb_idx: dict[tuple[int, int], int] = {}
    for t in range(1, r_lb + 1):
        for i in range(sizes[t - 1]):
            winner_to = (t + 1, i) if t < r_lb else None
            matches.append(
                {
                    "group": EventBracketGroup.LOSERS,
                    "round": t,
                    "slot_a": None,
                    "slot_b": None,
                    "winner_to": winner_to,
                    "loser_to": None,
                }
            )
            lb_idx[(t, i)] = len(matches) - 1
    matches.append(
        {
            "group": EventBracketGroup.GRAND_FINAL,
            "round": 1,
            "slot_a": None,
            "slot_b": None,
            "winner_to": None,
            "loser_to": None,
        }
    )
    gf_index = len(matches) - 1
    # The WB final winner advances into the Grand Final.
    matches[wb_idx[(k, 0)]]["winner_to"] = gf_index
    for t in range(1, r_lb + 1):
        for i in range(sizes[t - 1]):
            m = matches[lb_idx[(t, i)]]
            wt = m["winner_to"]
            m["winner_to"] = lb_idx[wt] if wt is not None else gf_index
    for r in range(1, k + 1):
        count = p // (2**r)
        for i in range(count // 2 if r == 1 else count):
            if r == 1:
                matches[wb_idx[(1, 2 * i)]]["loser_to"] = lb_idx[(1, i)]
                matches[wb_idx[(1, 2 * i + 1)]]["loser_to"] = lb_idx[(1, i)]
            else:
                lb_t = 2 * r - 2
                if r == k:
                    loser_target = (
                        lb_idx[(lb_t, i)]
                        if (r_lb > 0 and (lb_t, i) in lb_idx)
                        else gf_index
                    )
                else:
                    loser_target = lb_idx[(lb_t, i)]
                matches[wb_idx[(r, i)]]["loser_to"] = loser_target
    return matches


async def _instantiate_bracket(
    db: AsyncSession, event: Event, participant_ids: list[str]
) -> None:
    if event.bracket_type == EventBracketType.SINGLE_ELIMINATION:
        spec = _build_single_elim_spec(participant_ids)
    else:
        spec = _build_double_elim_spec(participant_ids)
    created: list[EventMatch] = []
    for s in spec:
        m = EventMatch(
            event_id=event.id,
            bracket_group=s["group"],
            round=s["round"],
            slot_a_id=s["slot_a"],
            slot_b_id=s["slot_b"],
        )
        created.append(m)
    db.add_all(created)
    await db.flush()
    for m, s in zip(created, spec, strict=True):
        await db.refresh(m)
        m.next_match_id = (
            created[s["winner_to"]].id if s["winner_to"] is not None else None
        )
        m.next_loser_match_id = (
            created[s["loser_to"]].id if s["loser_to"] is not None else None
        )
    await db.flush()
    await _resolve_byes(db, created)


async def _resolve_byes(db: AsyncSession, matches: list[EventMatch]) -> None:
    """Advance the survivor out of single-slot (bye) matches.

    A bye is a free pass: the lone participant is dropped into the next slot.
    The match is intentionally left PENDING (not COMPLETED) so it does not trip
    the "registration closes once a match result exists" guard in
    :meth:`register_participant` when a transient odd-count bracket is built
    mid-registration.
    """
    for m in matches:
        if m.status.value == "PENDING" and (
            (m.slot_a_id is not None) ^ (m.slot_b_id is not None)
        ):
            survivor = m.slot_a_id or m.slot_b_id
            if survivor is None:
                continue
            m.winner_id = survivor
            await db.flush()
            await _advance(db, m, survivor, is_winner=True)


async def _advance(
    db: AsyncSession,
    from_match: EventMatch,
    participant_id: str,
    is_winner: bool,
) -> None:
    target_id = (
        from_match.next_match_id if is_winner else from_match.next_loser_match_id
    )
    if target_id is None:
        return
    target = await event_match_repo.get_match_by_id(db, target_id)
    if target is None:
        return
    if target.slot_a_id is None:
        target.slot_a_id = participant_id
    elif target.slot_b_id is None:
        target.slot_b_id = participant_id
    else:
        return  # already full (unexpected for a fresh bracket)
    await event_match_repo.update_match(db, target)


class MatchAlreadyRecordedError(HTTPException):
    def __init__(self, match_id: str) -> None:
        super().__init__(
            status_code=409, detail=f"Match {match_id} result already recorded"
        )

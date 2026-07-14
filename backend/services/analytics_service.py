"""Analytics Service -- read-only aggregates over local SQLite.

All queries run against the local SQLite database only (FR-ANALYTICS-002);
no external service is contacted. Each query is bounded by a date window so
the summary stays fast on a large (365-day) dataset (NFR-PERF-002).

Date grouping uses SQLite ``strftime`` for the heavy group-bys (busiest hour,
weekly revenue) -- SQLite accepts the ``+00:00`` offset that SQLAlchemy stores
on tz-aware columns, so ``strftime`` returns correct UTC buckets. Values that
come back as datetimes (sessions, reservations) are re-attached to UTC before
arithmetic.

Health alerts are the one exception to "DB only": health metrics live in the
in-memory WebSocketManager (they are never persisted), so we read them from
``manager``.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.ws_manager import (
    manager,  # noqa: F401  # used by health section (Tasks 6-7)
)
from backend.models import (
    GamingSession,
    Invoice,
    Member,
    MenuItem,
    Reservation,
    Seat,
    SessionPOSItem,
    Zone,
)
from backend.models._enums import ReservationStatus, SessionStatus
from backend.schemas.analytics import (
    AnalyticsSummary,
    BusiestHour,
    DailyRevenue,
    MemberStats,
    TopPosItem,
    TopSpender,
    UpcomingReservation,
    WolSuccessRate,
    ZoneUtilisation,
)

# --- Configurable thresholds (spec does not fix values) -----------------------
UTILISATION_WINDOW_DAYS = 7
BUSIEST_HOUR_WINDOW_DAYS = 30
TOP_ITEMS_WINDOW_DAYS = 30
TOP_SPENDERS_WINDOW_DAYS = 30


def _day_window(now: datetime) -> tuple[datetime, datetime]:
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    return start, start + timedelta(days=1)


async def _busiest_hour(db: AsyncSession, since: datetime) -> BusiestHour | None:
    """Peak hour-of-day over the window, via SQLite strftime grouping."""
    rows = (
        await db.execute(
            select(
                func.strftime("%H", GamingSession.started_at).label("hr"),
                func.count().label("c"),
            )
            .where(GamingSession.started_at >= since)
            .group_by("hr")
        )
    ).all()
    if not rows:
        return None
    top = max(rows, key=lambda r: r.c)
    return BusiestHour(hour=int(top.hr), session_count=int(top.c))


async def _weekly_revenue(
    db: AsyncSession, start: datetime, end: datetime
) -> list[DailyRevenue]:
    """Last 7 daily totals, via SQLite strftime grouping; fills gaps with 0."""
    rows = (
        await db.execute(
            select(
                func.strftime("%Y-%m-%d", Invoice.created_at).label("d"),
                func.coalesce(func.sum(Invoice.total_paise), 0).label("total"),
            )
            .where(Invoice.created_at >= start, Invoice.created_at < end)
            .group_by("d")
        )
    ).all()
    totals = {r.d: int(r.total) for r in rows}
    out: list[DailyRevenue] = []
    day = start
    while day < end:
        key = day.strftime("%Y-%m-%d")
        out.append(DailyRevenue(date=key, total_paise=totals.get(key, 0)))
        day += timedelta(days=1)
    return out


async def _top_pos_items(
    db: AsyncSession, since: datetime, limit: int = 10
) -> list[TopPosItem]:
    rows = (
        await db.execute(
            select(
                SessionPOSItem.menu_item_id.label("mi"),
                MenuItem.name.label("nm"),
                func.sum(SessionPOSItem.quantity).label("q"),
            )
            .join(GamingSession, GamingSession.id == SessionPOSItem.session_id)
            .join(MenuItem, MenuItem.id == SessionPOSItem.menu_item_id)
            .where(
                GamingSession.started_at >= since,
                GamingSession.status == SessionStatus.COMPLETED,
            )
            .group_by(SessionPOSItem.menu_item_id)
            .order_by(func.sum(SessionPOSItem.quantity).desc())
            .limit(limit)
        )
    ).all()
    return [TopPosItem(menu_item_id=r.mi, name=r.nm, quantity=int(r.q)) for r in rows]


async def _zone_utilisation(
    db: AsyncSession,
    seats: Sequence[Seat],
    zones: Sequence[Zone],
    start: datetime,
    now: datetime,
) -> list[ZoneUtilisation]:
    sessions = (
        await db.execute(
            select(
                GamingSession.seat_id,
                GamingSession.started_at,
                GamingSession.ended_at,
                GamingSession.total_paused_seconds,
            ).where(
                GamingSession.started_at >= start,
                GamingSession.status == SessionStatus.COMPLETED,
                GamingSession.ended_at.isnot(None),
            )
        )
    ).all()
    seat_zone = {s.id: s.zone_id for s in seats}
    zone_seat_count: dict[str, int] = {}
    for s in seats:
        zone_seat_count[s.zone_id] = zone_seat_count.get(s.zone_id, 0) + 1
    session_hours: dict[str, float] = {}
    window_hours = (now - start).total_seconds() / 3600.0
    for r in sessions:
        zid = seat_zone.get(r.seat_id)
        if zid is None:
            continue
        ended = r.ended_at
        if ended.tzinfo is None:
            ended = ended.replace(tzinfo=UTC)
        started = r.started_at
        if started.tzinfo is None:
            started = started.replace(tzinfo=UTC)
        dur = (ended - started).total_seconds() - (r.total_paused_seconds or 0)
        session_hours[zid] = session_hours.get(zid, 0.0) + dur / 3600.0
    out: list[ZoneUtilisation] = []
    for z in zones:
        avail = zone_seat_count.get(z.id, 0) * window_hours
        sh = session_hours.get(z.id, 0.0)
        pct = (sh / avail * 100.0) if avail > 0 else 0.0
        out.append(
            ZoneUtilisation(
                zone_id=z.id,
                zone_name=z.name,
                session_hours=round(sh, 2),
                available_hours=round(avail, 2),
                utilisation_pct=round(pct, 2),
            )
        )
    return out


async def _member_stats(
    db: AsyncSession, today_start: datetime, thirty_days_ago: datetime
) -> MemberStats:
    new_today = (
        await db.scalar(select(func.count()).where(Member.created_at >= today_start))
        or 0
    )
    active = (
        await db.scalar(
            select(func.count(func.distinct(GamingSession.member_id))).where(
                GamingSession.started_at >= thirty_days_ago,
                GamingSession.member_id.isnot(None),
            )
        )
        or 0
    )
    rows = (
        await db.execute(
            select(
                Invoice.member_id.label("mid"),
                Member.name.label("nm"),
                func.coalesce(func.sum(Invoice.total_paise), 0).label("spend"),
            )
            .join(Member, Member.id == Invoice.member_id)
            .where(Invoice.member_id.isnot(None), Invoice.created_at >= thirty_days_ago)
            .group_by(Invoice.member_id)
            .order_by(func.sum(Invoice.total_paise).desc())
            .limit(5)
        )
    ).all()
    top = [
        TopSpender(member_id=r.mid, name=r.nm, total_paise=int(r.spend)) for r in rows
    ]
    return MemberStats(
        new_today=int(new_today), active_last_30d=int(active), top_spenders=top
    )


async def _upcoming_reservations(
    db: AsyncSession, today_start: datetime, tomorrow_start: datetime, now: datetime
) -> list[UpcomingReservation]:
    rows = (
        await db.execute(
            select(Reservation, Seat)
            .join(Seat, Seat.id == Reservation.seat_id)
            .where(
                Reservation.reserved_from >= today_start,
                Reservation.reserved_from < tomorrow_start,
                Reservation.reserved_from >= now,
                Reservation.status.in_(
                    [ReservationStatus.PENDING.value, ReservationStatus.CONFIRMED.value]
                ),
            )
            .order_by(Reservation.reserved_from)
        )
    ).all()
    out: list[UpcomingReservation] = []
    for res, seat in rows:
        rf = res.reserved_from
        if rf.tzinfo is None:
            rf = rf.replace(tzinfo=UTC)
        out.append(
            UpcomingReservation(
                reservation_id=res.id,
                seat_id=res.seat_id,
                seat_name=seat.name,
                customer_name=res.customer_name,
                reserved_from=rf,
            )
        )
    return out


def _wol_success_rates(seats: Sequence[Seat]) -> list[WolSuccessRate]:
    out: list[WolSuccessRate] = []
    for s in seats:
        attempts = s.wol_attempts or 0
        if attempts <= 0:
            continue
        successes = s.wol_successes or 0
        rate = successes / attempts * 100.0
        out.append(
            WolSuccessRate(
                seat_id=s.id,
                seat_name=s.name,
                attempts=attempts,
                successes=successes,
                rate_pct=round(rate, 2),
            )
        )
    return out


async def get_summary(db: AsyncSession) -> AnalyticsSummary:
    now = datetime.now(UTC)
    today_start, tomorrow_start = _day_window(now)
    seven_days_ago = today_start - timedelta(days=6)
    thirty_days_ago = today_start - timedelta(days=30)

    revenue = await db.scalar(
        select(func.coalesce(func.sum(Invoice.total_paise), 0)).where(
            Invoice.created_at >= today_start,
            Invoice.created_at < tomorrow_start,
        )
    )
    session_count = (
        await db.scalar(
            select(func.count()).where(
                GamingSession.started_at >= today_start,
                GamingSession.started_at < tomorrow_start,
            )
        )
        or 0
    )
    completed_today = (
        await db.scalars(
            select(GamingSession).where(
                GamingSession.started_at >= today_start,
                GamingSession.started_at < tomorrow_start,
                GamingSession.status == SessionStatus.COMPLETED,
                GamingSession.ended_at.isnot(None),
            )
        )
    ).all()
    if completed_today:
        total = 0.0
        for s in completed_today:
            ended_at = s.ended_at
            if ended_at is None:
                continue
            total += (ended_at - s.started_at).total_seconds() - s.total_paused_seconds
        avg_duration = total / len(completed_today)
    else:
        avg_duration = 0.0
    busiest_hour = await _busiest_hour(db, thirty_days_ago)
    weekly_revenue = await _weekly_revenue(db, seven_days_ago, tomorrow_start)

    zones = (await db.scalars(select(Zone))).all()
    seats = (await db.scalars(select(Seat))).all()
    top_pos_items = await _top_pos_items(db, thirty_days_ago)
    zone_utilisation = await _zone_utilisation(
        db, seats, zones, today_start - timedelta(days=UTILISATION_WINDOW_DAYS), now
    )
    member_stats = await _member_stats(db, today_start, thirty_days_ago)
    upcoming_reservations = await _upcoming_reservations(
        db, today_start, tomorrow_start, now
    )
    wol_success_rates = _wol_success_rates(seats)

    # Health alerts + current shift filled in Task 7.
    return AnalyticsSummary(
        total_revenue_paise=int(revenue or 0),
        session_count=int(session_count),
        average_duration_seconds=avg_duration,
        busiest_hour=busiest_hour,
        weekly_revenue=weekly_revenue,
        top_pos_items=top_pos_items,
        zone_utilisation=zone_utilisation,
        member_stats=member_stats,
        health_alerts=[],
        upcoming_reservations=upcoming_reservations,
        wol_success_rates=wol_success_rates,
        current_shift_id=None,
        shift_opened_at=None,
    )

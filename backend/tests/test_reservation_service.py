"""Unit tests for ReservationService.create_reservation."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.core.database import Base
from backend.models import Reservation, ReservationStatus, SeatStatus
from backend.repositories import seat_repo
from backend.schemas.reservation import ReservationUpdate
from backend.services.reservation_service import (
    ReservationNotFoundError,
    SeatUnavailableError,
    cancel_reservation,
    confirm_reservation,
    create_reservation,
    delete_reservation,
    get_reservation,
    list_reservations,
    mark_due_reservations_reserved,
    update_reservation,
)


@pytest.fixture
async def db() -> AsyncGenerator[AsyncSession]:
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as session:
        yield session
    await engine.dispose()


@pytest.fixture
async def seat(db: AsyncSession) -> str:
    from backend.models import PricingModel, Zone

    zone = Zone(
        name="Main Floor",
        rate_per_minute_paise=5,
        rate_per_hour_paise=300,
        pricing_model=PricingModel.PER_MINUTE,
    )
    db.add(zone)
    await db.flush()
    created = await seat_repo.create(db, name="PC-01", zone_id=zone.id)
    return created.id


async def test_create_reservation_ok(db: AsyncSession, seat: str) -> None:
    r = await create_reservation(
        db,
        seat_id=seat,
        customer_name="Alice",
        reserved_from=datetime.now(UTC) + timedelta(minutes=10),
        reserved_until=datetime.now(UTC) + timedelta(minutes=30),
        notes="window seat",
        created_by_staff_id="staff-1",
    )
    assert r.customer_name == "Alice"
    assert r.notes == "window seat"
    assert r.status == ReservationStatus.PENDING


async def test_create_reservation_seat_not_found(db: AsyncSession) -> None:
    with pytest.raises(HTTPException) as exc:
        await create_reservation(
            db,
            seat_id="ghost",
            customer_name="Bob",
            reserved_from=datetime.now(UTC) + timedelta(minutes=10),
            reserved_until=datetime.now(UTC) + timedelta(minutes=30),
            notes=None,
            created_by_staff_id="staff-1",
        )
    assert exc.value.status_code == 404


async def test_create_reservation_conflict(db: AsyncSession, seat: str) -> None:
    base_from = datetime.now(UTC) + timedelta(minutes=10)
    await create_reservation(
        db,
        seat_id=seat,
        customer_name="First",
        reserved_from=base_from,
        reserved_until=base_from + timedelta(minutes=20),
        notes=None,
        created_by_staff_id="staff-1",
    )
    with pytest.raises(SeatUnavailableError):
        await create_reservation(
            db,
            seat_id=seat,
            customer_name="Second",
            reserved_from=base_from + timedelta(minutes=5),
            reserved_until=base_from + timedelta(minutes=25),
            notes=None,
            created_by_staff_id="staff-1",
        )


async def test_create_reservation_persists(db: AsyncSession, seat: str) -> None:
    from backend.repositories import reservation_repo

    r = await create_reservation(
        db,
        seat_id=seat,
        customer_name="Carol",
        reserved_from=datetime.now(UTC) + timedelta(minutes=10),
        reserved_until=datetime.now(UTC) + timedelta(minutes=30),
        notes=None,
        created_by_staff_id="staff-1",
    )
    reloaded = await reservation_repo.get_by_id(db, r.id)
    assert reloaded is not None
    assert reloaded.customer_name == "Carol"


async def test_confirm_reservation_success(db: AsyncSession, seat: str) -> None:
    r = await create_reservation(
        db,
        seat_id=seat,
        customer_name="Dave",
        reserved_from=datetime.now(UTC) + timedelta(minutes=10),
        reserved_until=datetime.now(UTC) + timedelta(minutes=30),
        notes=None,
        created_by_staff_id="staff-1",
    )
    confirmed = await confirm_reservation(db, reservation_id=r.id, staff_id="staff-1")
    assert confirmed.status == ReservationStatus.CONFIRMED


async def test_confirm_reservation_not_found(db: AsyncSession) -> None:
    with pytest.raises(HTTPException) as exc:
        await confirm_reservation(db, reservation_id="ghost-id", staff_id="staff-1")
    assert exc.value.status_code == 404


async def test_confirm_reservation_invalid_state(db: AsyncSession, seat: str) -> None:
    r = await create_reservation(
        db,
        seat_id=seat,
        customer_name="Eve",
        reserved_from=datetime.now(UTC) + timedelta(minutes=10),
        reserved_until=datetime.now(UTC) + timedelta(minutes=30),
        notes=None,
        created_by_staff_id="staff-1",
    )
    await confirm_reservation(db, reservation_id=r.id, staff_id="staff-1")
    with pytest.raises(HTTPException) as exc:
        await confirm_reservation(db, reservation_id=r.id, staff_id="staff-1")
    assert exc.value.status_code == 409
    assert "can only confirm a pending" in str(exc.value.detail).lower()


async def test_cancel_reservation_success(db: AsyncSession, seat: str) -> None:
    r = await create_reservation(
        db,
        seat_id=seat,
        customer_name="Frank",
        reserved_from=datetime.now(UTC) + timedelta(minutes=10),
        reserved_until=datetime.now(UTC) + timedelta(minutes=30),
        notes=None,
        created_by_staff_id="staff-1",
    )
    cancelled = await cancel_reservation(db, reservation_id=r.id, staff_id="staff-2")
    assert cancelled.status == ReservationStatus.CANCELLED


async def test_cancel_reservation_not_found(db: AsyncSession) -> None:
    with pytest.raises(HTTPException) as exc:
        await cancel_reservation(db, reservation_id="ghost-id", staff_id="staff-1")
    assert exc.value.status_code == 404


async def test_cancel_reservation_invalid_state(db: AsyncSession, seat: str) -> None:
    r = await create_reservation(
        db,
        seat_id=seat,
        customer_name="Grace",
        reserved_from=datetime.now(UTC) + timedelta(minutes=10),
        reserved_until=datetime.now(UTC) + timedelta(minutes=30),
        notes=None,
        created_by_staff_id="staff-1",
    )
    # Cancel once, then try to cancel again - should fail
    await cancel_reservation(db, reservation_id=r.id, staff_id="staff-2")
    with pytest.raises(HTTPException) as exc:
        await cancel_reservation(db, reservation_id=r.id, staff_id="staff-2")
    assert exc.value.status_code == 409
    assert "already cancelled" in str(exc.value.detail).lower()


async def _seed(db: AsyncSession, seat: str, *, offset: int = 10) -> Reservation:
    from backend.services.reservation_service import create_reservation

    base = datetime.now(UTC) + timedelta(minutes=offset)
    return await create_reservation(
        db,
        seat_id=seat,
        customer_name="Test",
        reserved_from=base,
        reserved_until=base + timedelta(minutes=20),
        notes=None,
        created_by_staff_id="staff-1",
    )


async def test_get_and_list(db: AsyncSession, seat: str) -> None:
    r = await _seed(db, seat)
    got = await get_reservation(db, reservation_id=r.id)
    assert got.id == r.id
    all_r = await list_reservations(db)
    assert len(all_r) == 1


async def test_get_not_found(db: AsyncSession) -> None:
    from backend.services.reservation_service import ReservationNotFoundError

    with pytest.raises(ReservationNotFoundError):
        await get_reservation(db, reservation_id="ghost")


async def test_update_notes(db: AsyncSession, seat: str) -> None:
    r = await _seed(db, seat)
    updated = await update_reservation(
        db,
        reservation_id=r.id,
        updates=ReservationUpdate(notes="updated note"),
        staff_id="staff-1",
    )
    assert updated.notes == "updated note"


async def test_update_window_conflict(db: AsyncSession, seat: str) -> None:
    first = await _seed(db, seat, offset=10)
    second = await _seed(db, seat, offset=60)
    with pytest.raises(SeatUnavailableError):
        await update_reservation(
            db,
            reservation_id=second.id,
            updates=ReservationUpdate(
                reserved_from=first.reserved_from, reserved_until=first.reserved_until
            ),
            staff_id="staff-1",
        )


async def test_delete_reservation(db: AsyncSession, seat: str) -> None:
    r = await _seed(db, seat)
    deleted = await delete_reservation(db, reservation_id=r.id)
    assert deleted is True
    with pytest.raises(ReservationNotFoundError):
        await get_reservation(db, reservation_id=r.id)


async def test_mark_due_flips_seat_reserved(db: AsyncSession, seat: str) -> None:
    from unittest.mock import AsyncMock, patch

    from backend.core.ws_manager import manager as ws_manager

    await _seed(db, seat, offset=1)  # starts in 1 minute -> within window
    with patch.object(ws_manager, "broadcast_to_dashboards", new=AsyncMock()):
        updated = await mark_due_reservations_reserved(db)
    assert seat in updated
    refreshed = await seat_repo.get_by_id(db, seat)
    assert refreshed.status == SeatStatus.RESERVED


async def test_cancel_reservation_restores_reserved_seat(
    db: AsyncSession, seat: str
) -> None:
    from unittest.mock import AsyncMock, patch

    from backend.core.ws_manager import manager as ws_manager
    from backend.models import SeatStatus

    # Create a PENDING reservation
    reservation = await _seed(db, seat, offset=10)
    # Simulate scheduler flipping seat to RESERVED
    seat_obj = await seat_repo.get_by_id(db, seat)
    seat_obj.status = SeatStatus.RESERVED
    await seat_repo.update(db, seat_obj)

    broadcast_mock = AsyncMock()
    with patch.object(ws_manager, "broadcast_to_dashboards", broadcast_mock):
        cancelled = await cancel_reservation(
            db, reservation_id=reservation.id, staff_id="staff-2"
        )

    assert cancelled.status == ReservationStatus.CANCELLED
    refreshed_seat = await seat_repo.get_by_id(db, seat)
    assert refreshed_seat.status == SeatStatus.AVAILABLE
    broadcast_mock.assert_awaited_once()
    args, _ = broadcast_mock.call_args
    assert args[0] == "seat_updated"
    assert args[1]["id"] == seat
    assert args[1]["status"] == "AVAILABLE"


async def test_cancel_from_confirmed_releases_seat(db: AsyncSession, seat: str) -> None:
    from unittest.mock import AsyncMock, patch

    from backend.core.ws_manager import manager as ws_manager
    from backend.models import SeatStatus

    # Create and confirm a reservation
    reservation = await _seed(db, seat, offset=10)
    await confirm_reservation(db, reservation_id=reservation.id, staff_id="staff-1")
    # Simulate scheduler flipping seat to RESERVED
    seat_obj = await seat_repo.get_by_id(db, seat)
    seat_obj.status = SeatStatus.RESERVED
    await seat_repo.update(db, seat_obj)

    broadcast_mock = AsyncMock()
    with patch.object(ws_manager, "broadcast_to_dashboards", broadcast_mock):
        cancelled = await cancel_reservation(
            db, reservation_id=reservation.id, staff_id="staff-2"
        )

    assert cancelled.status == ReservationStatus.CANCELLED
    refreshed_seat = await seat_repo.get_by_id(db, seat)
    assert refreshed_seat.status == SeatStatus.AVAILABLE
    broadcast_mock.assert_awaited_once()
    args, _ = broadcast_mock.call_args
    assert args[0] == "seat_updated"
    assert args[1]["id"] == seat
    assert args[1]["status"] == "AVAILABLE"


async def test_delete_reservation_releases_reserved_seat(
    db: AsyncSession, seat: str
) -> None:
    from unittest.mock import AsyncMock, patch

    from backend.core.ws_manager import manager as ws_manager
    from backend.models import SeatStatus

    # Create a reservation
    reservation = await _seed(db, seat, offset=10)
    # Simulate scheduler flipping seat to RESERVED
    seat_obj = await seat_repo.get_by_id(db, seat)
    seat_obj.status = SeatStatus.RESERVED
    await seat_repo.update(db, seat_obj)

    broadcast_mock = AsyncMock()
    with patch.object(ws_manager, "broadcast_to_dashboards", broadcast_mock):
        deleted = await delete_reservation(
            db, reservation_id=reservation.id, staff_id="staff-1"
        )

    assert deleted is True
    refreshed_seat = await seat_repo.get_by_id(db, seat)
    assert refreshed_seat.status == SeatStatus.AVAILABLE
    broadcast_mock.assert_awaited_once()
    args, _ = broadcast_mock.call_args
    assert args[0] == "seat_updated"
    assert args[1]["id"] == seat
    assert args[1]["status"] == "AVAILABLE"


async def test_update_window_blocked_when_confirmed(
    db: AsyncSession, seat: str
) -> None:
    r = await _seed(db, seat)
    await confirm_reservation(db, reservation_id=r.id, staff_id="staff-1")
    with pytest.raises(HTTPException) as exc:
        await update_reservation(
            db,
            reservation_id=r.id,
            updates=ReservationUpdate(
                reserved_from=r.reserved_from + timedelta(minutes=5)
            ),
            staff_id="staff-1",
        )
    assert exc.value.status_code == 409
    assert "time window" in str(exc.value.detail).lower()


async def test_update_notes_on_confirmed(db: AsyncSession, seat: str) -> None:
    r = await _seed(db, seat)
    await confirm_reservation(db, reservation_id=r.id, staff_id="staff-1")
    updated = await update_reservation(
        db,
        reservation_id=r.id,
        updates=ReservationUpdate(notes="vip arrival"),
        staff_id="staff-1",
    )
    assert updated.status == ReservationStatus.CONFIRMED
    assert updated.notes == "vip arrival"

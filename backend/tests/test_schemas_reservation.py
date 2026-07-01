from datetime import UTC, datetime

from backend.models._enums import ReservationStatus
from backend.schemas.reservation import ReservationCreate, ReservationResponse


class TestReservationCreate:
    def test_valid(self) -> None:
        now = datetime.now(UTC)
        r = ReservationCreate(
            seat_id="seat1",
            customer_name="John",
            reserved_from=now,
            created_by_staff_id="staff1",
        )
        assert r.status == ReservationStatus.PENDING


class TestReservationResponse:
    def test_from_orm(self) -> None:
        now = datetime.now(UTC)

        class FakeReservation:
            id = "res1"
            seat_id = "seat1"
            customer_name = "John"
            member_id = None
            reserved_from = now
            reserved_until = None
            group_reservation_id = None
            notes = None
            created_by_staff_id = "staff1"
            status = ReservationStatus.PENDING
            created_at = now
            updated_at = now

        r = ReservationResponse.model_validate(FakeReservation())
        assert r.id == "res1"

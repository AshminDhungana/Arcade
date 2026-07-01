from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from backend.models._enums import PricingModel, SeatStatus
from backend.schemas.seat import SeatCreate, SeatResponse, SeatUpdate
from backend.schemas.zone import ZoneCreate, ZoneResponse, ZoneUpdate


class TestZoneCreate:
    def test_valid(self) -> None:
        z = ZoneCreate(
            name="VIP Zone",
            rate_per_minute_paise=50,
            rate_per_hour_paise=3000,
            pricing_model=PricingModel.PER_MINUTE,
        )
        assert z.name == "VIP Zone"
        assert z.pricing_model == PricingModel.PER_MINUTE

    def test_negative_rate_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ZoneCreate(
                name="VIP",
                rate_per_minute_paise=-1,
                rate_per_hour_paise=100,
                pricing_model=PricingModel.PER_MINUTE,
            )

    def test_name_too_long_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ZoneCreate(
                name="x" * 300,
                rate_per_minute_paise=50,
                rate_per_hour_paise=3000,
                pricing_model=PricingModel.PER_MINUTE,
            )


class TestZoneUpdate:
    def test_partial_empty(self) -> None:
        u = ZoneUpdate()
        assert u.name is None

    def test_partial_name(self) -> None:
        u = ZoneUpdate(name="New Name")
        assert u.name == "New Name"


class TestZoneResponse:
    def test_has_id(self) -> None:
        class FakeZone:
            id = "abc123"
            name = "Main"
            rate_per_minute_paise = 50
            rate_per_hour_paise = 3000
            pricing_model = PricingModel.PER_MINUTE
            block_minutes = None

        r = ZoneResponse.model_validate(FakeZone())
        assert r.id == "abc123"
        assert r.name == "Main"


class TestSeatCreate:
    def test_defaults(self) -> None:
        s = SeatCreate(name="Seat 01", zone_id="zone1")
        assert s.zone_id == "zone1"
        assert s.status == SeatStatus.AVAILABLE
        assert s.is_console is False
        assert s.mac_address is None

    def test_with_all_fields(self) -> None:
        s = SeatCreate(
            name="Seat 2",
            zone_id="z1",
            mac_address="AA:BB:CC:DD:EE:FF",
            status=SeatStatus.MAINTENANCE,
            plug_id="plug1",
            is_console=True,
            notes="Test seat",
        )
        assert s.status == SeatStatus.MAINTENANCE


class TestSeatUpdate:
    def test_partial(self) -> None:
        u = SeatUpdate(status=SeatStatus.MAINTENANCE, notes="GPU dead")
        assert u.status == SeatStatus.MAINTENANCE
        assert u.notes == "GPU dead"
        assert u.name is None


class TestSeatResponse:
    def test_from_orm(self) -> None:
        now = datetime.now(UTC)

        class FakeSeat:
            id = "seat01"
            name = "Seat 1"
            zone_id = "z1"
            mac_address = "aa:bb:cc:dd:ee:ff"
            status = SeatStatus.AVAILABLE
            plug_id = None
            is_console = False
            notes = None
            created_at = now
            updated_at = now

        r = SeatResponse.model_validate(FakeSeat())
        assert r.id == "seat01"
        assert r.created_at == now

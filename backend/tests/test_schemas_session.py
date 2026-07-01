from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from backend.models._enums import PricingModel, SessionStatus
from backend.schemas.session import SessionCreate, SessionResponse, SessionUpdate


class TestSessionCreate:
    def test_valid(self) -> None:
        s = SessionCreate(
            seat_id="seat1",
            locked_rate_paise=50,
            locked_pricing_model=PricingModel.PER_MINUTE,
        )
        assert s.seat_id == "seat1"
        assert s.discount_paise == 0  # default

    def test_negative_rate_rejected(self) -> None:
        with pytest.raises(ValidationError):
            SessionCreate(
                seat_id="seat1",
                locked_rate_paise=-10,
                locked_pricing_model=PricingModel.PER_MINUTE,
            )

    def test_defaults(self) -> None:
        s = SessionCreate(
            seat_id="s1",
            locked_rate_paise=100,
            locked_pricing_model=PricingModel.PER_MINUTE,
        )
        assert s.member_id is None
        assert s.discount_paise == 0


class TestSessionUpdate:
    def test_empty(self) -> None:
        u = SessionUpdate()
        assert u.status is None
        assert u.discount_paise is None

    def test_partial_status(self) -> None:
        u = SessionUpdate(status=SessionStatus.PAUSED)
        assert u.status == SessionStatus.PAUSED


class TestSessionResponse:
    def test_from_orm(self) -> None:
        now = datetime.now(UTC)

        class FakeSession:
            id = "sess1"
            seat_id = "seat1"
            member_id = None
            shift_id = None
            status = SessionStatus.ACTIVE
            started_at = now
            ended_at = None
            paused_at = None
            total_paused_seconds = 0
            locked_rate_paise = 50
            locked_pricing_model = PricingModel.PER_MINUTE
            package_entitlement_id = None
            promotion_id = None
            discount_paise = 0
            payment_method = None
            created_at = now
            updated_at = now

        r = SessionResponse.model_validate(FakeSession())
        assert r.id == "sess1"
        assert r.status == SessionStatus.ACTIVE
        assert r.started_at == now

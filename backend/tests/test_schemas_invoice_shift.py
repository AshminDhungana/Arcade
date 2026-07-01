from datetime import UTC, datetime

from backend.models._enums import InvoiceLineItemType, PaymentMethod, ShiftStatus
from backend.schemas.invoice import (
    InvoiceCreate,
    InvoiceLineItemCreate,
    InvoiceResponse,
)
from backend.schemas.shift import ShiftCreate, ShiftResponse


class TestInvoiceLineItemCreate:
    def test_valid(self) -> None:
        li = InvoiceLineItemCreate(
            type=InvoiceLineItemType.TIME_CHARGE,
            description="1 hour gameplay",
            unit_price_paise=1500,
            total_paise=1500,
        )
        assert li.quantity == 1  # default
        assert li.unit_price_paise == 1500


class TestInvoiceCreate:
    def test_valid(self) -> None:
        inv = InvoiceCreate(
            session_id="session1",
            payment_method=PaymentMethod.CASH,
        )
        assert inv.total_paise == 0
        assert inv.line_items == []


class TestInvoiceResponse:
    def test_from_orm(self) -> None:
        now = datetime.now(UTC)

        class FakeInvoice:
            id = "inv1"
            session_id = "sess1"
            member_id = None
            shift_id = None
            time_charge_paise = 1000
            package_credit_used_paise = 0
            discount_paise = 100
            pos_total_paise = 0
            total_paise = 900
            payment_method = PaymentMethod.CASH
            created_at = now

        r = InvoiceResponse.model_validate(FakeInvoice())
        assert r.id == "inv1"
        assert r.total_paise == 900


class TestShiftCreate:
    def test_valid(self) -> None:
        s = ShiftCreate(opened_by_staff_id="staff1")
        assert s.opened_by_staff_id == "staff1"


class TestShiftResponse:
    def test_from_orm(self) -> None:
        now = datetime.now(UTC)

        class FakeShift:
            id = "shift1"
            opened_by_staff_id = "staff1"
            closed_by_staff_id = None
            opened_at = now
            closed_at = None
            float_paise = 5000
            counted_paise = None
            status = ShiftStatus.OPEN

        r = ShiftResponse.model_validate(FakeShift())
        assert r.id == "shift1"
        assert r.status == ShiftStatus.OPEN

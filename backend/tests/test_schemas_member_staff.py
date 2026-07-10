from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from backend.models._enums import StaffRole
from backend.schemas.member import MemberCreate, MemberUpdate
from backend.schemas.staff import StaffCreate, StaffResponse, StaffUpdate


class TestMemberCreate:
    def test_valid(self) -> None:
        m = MemberCreate(name="Alice", phone="9801234567")
        assert m.name == "Alice"
        assert m.phone == "9801234567"

    def test_name_required(self) -> None:
        with pytest.raises(ValidationError):
            MemberCreate(phone="980")  # type: ignore[call-arg]

    def test_birth_month_valid_range(self) -> None:
        m = MemberCreate(name="Bob", phone="123", birth_month=6)
        assert m.birth_month == 6

    def test_birth_month_invalid(self) -> None:
        with pytest.raises(ValidationError):
            MemberCreate(name="Bob", phone="123", birth_month=13)


class TestMemberUpdate:
    def test_partial(self) -> None:
        u = MemberUpdate(phone="999")
        assert u.phone == "999"
        assert u.name is None


class TestStaffCreate:
    def test_valid(self) -> None:
        s = StaffCreate(name="Staff1", role=StaffRole.ADMIN, pin="1234")
        assert s.name == "Staff1"
        assert s.role == StaffRole.ADMIN

    def test_pin_too_short(self) -> None:
        with pytest.raises(ValidationError):
            StaffCreate(name="Staff1", role=StaffRole.ADMIN, pin="12")


class TestStaffUpdate:
    def test_partial(self) -> None:
        u = StaffUpdate(role=StaffRole.CASHIER)
        assert u.role == StaffRole.CASHIER
        assert u.name is None


class TestStaffResponse:
    def test_no_pin_hash_exposed(self) -> None:
        now = datetime.now(UTC)

        class FakeStaff:
            id = "staff1"
            name = "Boss"
            role = StaffRole.ADMIN
            is_active = True
            updated_at = now

        r = StaffResponse.model_validate(FakeStaff())
        assert r.id == "staff1"
        assert r.name == "Boss"
        assert r.role == StaffRole.ADMIN
        assert not hasattr(r, "pin_hash")


class TestStaffAuditActions:
    def test_staff_audit_actions_defined(self) -> None:
        from backend.models._enums import AuditAction

        assert AuditAction.STAFF_CREATED.value == "STAFF_CREATED"
        assert AuditAction.STAFF_PIN_CHANGED.value == "STAFF_PIN_CHANGED"
        assert AuditAction.STAFF_DEACTIVATED.value == "STAFF_DEACTIVATED"

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError

from backend.models._enums import VoucherStatus
from backend.schemas.voucher import (
    VoucherBatchCreate,
    VoucherBatchResponse,
    VoucherCreate,
    VoucherRedeemRequest,
    VoucherResponse,
)


class TestVoucherCreate:
    def test_valid(self) -> None:
        v = VoucherCreate(code="ABCD123", batch_id="batch1")
        assert v.code == "ABCD123"
        assert v.value_paise is None


class TestVoucherResponse:
    def test_from_orm(self) -> None:
        now = datetime.now(UTC)

        class FakeVoucher:
            id = "vouch1"
            code = "ABCD123"
            value_paise = 1000
            value_minutes = None
            status = VoucherStatus.UNUSED
            redeemed_by_member_id = None
            redeemed_at = None
            expires_at = None
            batch_id = "b1"
            created_at = now

        r = VoucherResponse.model_validate(FakeVoucher())
        assert r.id == "vouch1"
        assert r.status == VoucherStatus.UNUSED


# NEW: Batch creation schemas
class TestVoucherBatchCreate:
    def test_valid(self):
        body = VoucherBatchCreate(
            count=50,
            value_paise=10000,
            expires_in_days=30,
        )
        assert body.count == 50
        assert body.value_paise == 10000
        assert body.expires_in_days == 30

    def test_valid_with_value_minutes(self):
        body = VoucherBatchCreate(
            count=10,
            value_minutes=60,
            expires_in_days=7,
        )
        assert body.value_minutes == 60
        assert body.value_paise is None

    def test_invalid_count_zero(self):
        with pytest.raises(ValidationError):
            VoucherBatchCreate(count=0, value_paise=1000)

    def test_invalid_count_negative(self):
        with pytest.raises(ValidationError):
            VoucherBatchCreate(count=-1, value_paise=1000)

    def test_invalid_no_value(self):
        with pytest.raises(ValidationError):
            VoucherBatchCreate(count=10)  # Neither value_paise nor value_minutes


class TestVoucherBatchResponse:
    def test_from_orm(self):
        from backend.schemas.voucher import VoucherResponse

        class FakeVoucher:
            id = "v1"
            code = "ABC123"
            value_paise = 1000
            value_minutes = None
            status = VoucherStatus.UNUSED
            redeemed_by_member_id = None
            redeemed_at = None
            expires_at = datetime.now(UTC) + timedelta(days=30)
            batch_id = "batch1"
            created_at = datetime.now(UTC)

        vouchers = [VoucherResponse.model_validate(FakeVoucher()) for _ in range(3)]
        resp = VoucherBatchResponse(batch_id="batch1", count=3, vouchers=vouchers)

        assert resp.batch_id == "batch1"
        assert resp.count == 3
        assert len(resp.vouchers) == 3


class TestVoucherRedeemRequest:
    def test_valid(self):
        body = VoucherRedeemRequest(code="ABCDEFGHIJKL", member_id="member123")
        assert body.code == "ABCDEFGHIJKL"
        assert body.member_id == "member123"

    def test_code_max_length(self):
        body = VoucherRedeemRequest(code="A" * 12, member_id="m1")
        assert len(body.code) == 12

    def test_code_too_long(self):
        with pytest.raises(ValidationError):
            VoucherRedeemRequest(code="A" * 13, member_id="m1")

    def test_member_id_required(self):
        with pytest.raises(ValidationError):
            VoucherRedeemRequest(code="ABCDEFGHIJKL")  # missing member_id

from datetime import UTC, datetime

from backend.models._enums import VoucherStatus
from backend.schemas.voucher import VoucherCreate, VoucherResponse


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

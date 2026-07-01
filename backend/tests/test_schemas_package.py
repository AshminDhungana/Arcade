import pytest
from pydantic import ValidationError

from backend.models._enums import PackageType
from backend.schemas.package import MemberPackageEntitlementCreate, PackageCreate


class TestPackageCreate:
    def test_valid(self) -> None:
        p = PackageCreate(
            name="2 Hour Bundle",
            type=PackageType.HOUR_BUNDLE,
            total_minutes=120,
            price_paise=300000,
        )
        assert p.name == "2 Hour Bundle"
        assert p.price_paise == 300000

    def test_total_minutes_validation(self) -> None:
        with pytest.raises(ValidationError):
            PackageCreate(
                name="Bad",
                type=PackageType.HOUR_BUNDLE,
                total_minutes=0,
                price_paise=100,
            )


class TestMemberPackageEntitlementCreate:
    def test_valid(self) -> None:
        e = MemberPackageEntitlementCreate(
            member_id="m1",
            package_id="p1",
            remaining_minutes=120,
        )
        assert e.remaining_minutes == 120

"""Unit tests for the require_self_or_admin dependency."""

from __future__ import annotations

from fastapi import HTTPException

from backend.api.deps import require_self_or_admin
from backend.models._enums import StaffRole


def _make_staff(id_: str, role: StaffRole):  # type: ignore[no-untyped-def]
    class _FakeStaff:
        is_active = True
        token_version = 0

    obj = _FakeStaff()
    obj.id = id_  # type: ignore[attr-defined]
    obj.role = role  # type: ignore[attr-defined]
    return obj


async def test_admin_allowed_for_any_target() -> None:
    admin = _make_staff("other-id", StaffRole.ADMIN)
    result = await require_self_or_admin("any-id", staff=admin)
    assert result is admin


async def test_self_allowed() -> None:
    self_staff = _make_staff("self-id", StaffRole.CASHIER)
    result = await require_self_or_admin("self-id", staff=self_staff)
    assert result is self_staff


async def test_other_cashier_forbidden() -> None:
    other = _make_staff("other-id", StaffRole.CASHIER)
    try:
        await require_self_or_admin("self-id", staff=other)
        raise AssertionError("expected HTTPException 403")
    except HTTPException as exc:
        assert exc.status_code == 403

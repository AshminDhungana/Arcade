"""StaffService — business logic for staff management.

Covers creating staff, updating PINs, deactivating, and listing staff.
All public functions are ``async def`` and accept ``db: AsyncSession`` first.
"""

from __future__ import annotations

from collections.abc import Sequence

from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.security import hash_pin
from backend.models._enums import AuditAction, StaffRole
from backend.models.staff import Staff
from backend.repositories import staff_repo
from backend.services import audit_service


class NotFoundError(HTTPException):
    """Raised when a staff member cannot be found — always returns 404."""

    def __init__(self, detail: str) -> None:
        super().__init__(status_code=404, detail=detail)


class StaffService:
    @staticmethod
    async def create(
        db: AsyncSession,
        *,
        name: str,
        role: StaffRole | str,
        pin: str,
        is_active: bool = True,
        staff: Staff | None = None,
    ) -> Staff:
        """Create a new staff member with an Argon2id-hashed PIN.

        ``token_version`` defaults to 0 (set by the model).
        """
        role_value = role.value if isinstance(role, StaffRole) else str(role)
        new_staff = await staff_repo.create(
            db,
            name=name,
            role=role_value,
            pin_hash=hash_pin(pin),
            is_active=is_active,
        )
        await audit_service.log(
            db,
            action=AuditAction.STAFF_CREATED,
            entity_type="staff",
            entity_id=new_staff.id,
            staff_id=staff.id if staff else None,
            detail=f"Created staff '{name}' (role={role_value})",
        )
        return new_staff

    @staticmethod
    async def list_staff(db: AsyncSession) -> Sequence[Staff]:
        """Return all staff members."""
        return await staff_repo.list(db)

    @staticmethod
    async def update_pin(
        db: AsyncSession,
        *,
        staff_id: str,
        new_pin: str,
        staff: Staff | None = None,
    ) -> Staff:
        """Update a staff member's PIN and invalidate existing tokens.

        Bumps ``token_version`` so any JWT issued before this change is
        rejected by the auth dependency on the next request.
        """
        target = await staff_repo.get_by_id(db, staff_id)
        if target is None:
            raise NotFoundError("Staff not found")
        target.pin_hash = hash_pin(new_pin)
        target.token_version += 1
        target = await staff_repo.update(db, target)
        await audit_service.log(
            db,
            action=AuditAction.STAFF_PIN_CHANGED,
            entity_type="staff",
            entity_id=target.id,
            staff_id=staff.id if staff else None,
            detail="PIN changed; token_version incremented",
        )
        return target

    @staticmethod
    async def deactivate(
        db: AsyncSession,
        *,
        staff_id: str,
        staff: Staff | None = None,
    ) -> Staff:
        """Deactivate a staff member and bump ``token_version``.

        Bumping ``token_version`` invalidates every existing JWT for this
        staff member on the next request.
        """
        target = await staff_repo.get_by_id(db, staff_id)
        if target is None:
            raise NotFoundError("Staff not found")
        target.is_active = False
        target.token_version += 1
        target = await staff_repo.update(db, target)
        await audit_service.log(
            db,
            action=AuditAction.STAFF_DEACTIVATED,
            entity_type="staff",
            entity_id=target.id,
            staff_id=staff.id if staff else None,
            detail="Staff deactivated; token_version incremented",
        )
        return target

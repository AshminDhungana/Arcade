"""Package & entitlement repository — CRUD + atomic drawdown."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import MemberPackageEntitlement, Package


async def create(
    db: AsyncSession,
    *,
    name: str,
    type: str,
    total_minutes: int,
    price_paise: int,
    valid_days: int | None = None,
    zone_restriction_id: str | None = None,
    is_active: bool = True,
) -> Package:
    package = Package(
        name=name,
        type=type,
        total_minutes=total_minutes,
        price_paise=price_paise,
        valid_days=valid_days,
        zone_restriction_id=zone_restriction_id,
        is_active=is_active,
    )
    db.add(package)
    await db.flush()
    await db.refresh(package)
    return package


async def get_by_id(db: AsyncSession, package_id: str) -> Package | None:
    result = await db.execute(select(Package).where(Package.id == package_id))
    return result.scalar_one_or_none()


async def list(db: AsyncSession) -> Sequence[Package]:
    result = await db.execute(select(Package))
    return result.scalars().all()


async def update(db: AsyncSession, package: Package) -> Package:
    db.add(package)
    await db.flush()
    await db.refresh(package)
    return package


async def delete_by_id(db: AsyncSession, package_id: str) -> bool:
    package = await get_by_id(db, package_id)
    if package is None:
        return False
    await db.delete(package)
    await db.flush()
    return True


async def drawdown_minutes(db: AsyncSession, entitlement_id: str, minutes: int) -> bool:
    """Atomically deduct minutes from an entitlement.

    Uses ``UPDATE ... WHERE remaining_minutes >= ?`` so SQLite does not need
    row-level locking.  Returns ``True`` if at least one row was updated.
    """
    result = await db.execute(
        text(
            "UPDATE member_package_entitlements "
            "SET remaining_minutes = remaining_minutes - :minutes "
            "WHERE id = :id AND remaining_minutes >= :minutes"
        ),
        {"minutes": minutes, "id": entitlement_id},
    )
    return int(result.rowcount) > 0  # type: ignore[attr-defined]


# -- entitlement helpers --


async def get_entitlement_by_id(
    db: AsyncSession, entitlement_id: str
) -> MemberPackageEntitlement | None:
    result = await db.execute(
        select(MemberPackageEntitlement).where(
            MemberPackageEntitlement.id == entitlement_id
        )
    )
    return result.scalar_one_or_none()

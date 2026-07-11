from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.device_type import DeviceType


async def create(
    db: AsyncSession, name: str, description: str | None = None
) -> DeviceType:
    """Create a new DeviceType."""
    obj = DeviceType(name=name, description=description)
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def get_by_id(db: AsyncSession, device_type_id: str) -> DeviceType | None:
    """Fetch a device type by primary key."""
    return (
        await db.execute(select(DeviceType).where(DeviceType.id == device_type_id))
    ).scalar_one_or_none()


async def list(db: AsyncSession) -> Sequence[DeviceType]:  # noqa: A001
    """Return all device types ordered by name."""
    return (
        (await db.execute(select(DeviceType).order_by(DeviceType.name))).scalars().all()
    )


async def update(db: AsyncSession, dt: DeviceType) -> DeviceType:
    """Update a device type."""
    db.add(dt)
    await db.flush()
    await db.refresh(dt)
    return dt


async def delete_by_id(db: AsyncSession, device_type_id: str) -> bool:
    """Delete a device type by ID.

    Returns True if deleted, False if not found.
    """
    dt = await get_by_id(db, device_type_id)
    if dt is None:
        return False
    await db.delete(dt)
    await db.flush()
    return True

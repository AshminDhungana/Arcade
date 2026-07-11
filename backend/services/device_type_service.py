from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.device_type import DeviceType
from backend.repositories import device_type_repo


class DeviceTypeService:
    @staticmethod
    async def create(
        db: AsyncSession, name: str, description: str | None = None
    ) -> DeviceType:
        return await device_type_repo.create(db, name=name, description=description)

    @staticmethod
    async def get_by_id(db: AsyncSession, dt_id: str) -> DeviceType | None:
        return await device_type_repo.get_by_id(db, dt_id)

    @staticmethod
    async def list(db: AsyncSession) -> Sequence[DeviceType]:
        return await device_type_repo.list(db)

    @staticmethod
    async def update(db: AsyncSession, dt: DeviceType) -> DeviceType:
        return await device_type_repo.update(db, dt)

    @staticmethod
    async def delete(db: AsyncSession, dt_id: str) -> bool:
        return await device_type_repo.delete_by_id(db, dt_id)

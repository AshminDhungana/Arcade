from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.peak_schedule import PeakSchedule
from backend.repositories import peak_schedule_repo


class PeakScheduleService:
    @staticmethod
    async def create(
        db: AsyncSession,
        name: str,
        is_peak: bool = True,
        day_of_week: int | None = None,
        start_time: str = "",
        end_time: str = "",
        surcharge_paise: int = 0,
    ) -> PeakSchedule:
        return await peak_schedule_repo.create(
            db,
            name=name,
            is_peak=is_peak,
            day_of_week=day_of_week,
            start_time=start_time,
            end_time=end_time,
            surcharge_paise=surcharge_paise,
        )

    @staticmethod
    async def get_by_id(db: AsyncSession, sc_id: str) -> PeakSchedule | None:
        return await peak_schedule_repo.get_by_id(db, sc_id)

    @staticmethod
    async def list(db: AsyncSession) -> Sequence[PeakSchedule]:
        return await peak_schedule_repo.list(db)

    @staticmethod
    async def update(db: AsyncSession, sc: PeakSchedule) -> PeakSchedule:
        return await peak_schedule_repo.update(db, sc)

    @staticmethod
    async def delete(db: AsyncSession, sc_id: str) -> bool:
        return await peak_schedule_repo.delete_by_id(db, sc_id)

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.peak_schedule import PeakSchedule


async def create(
    db: AsyncSession,
    name: str,
    is_peak: bool = True,
    day_of_week: int | None = None,
    start_time: str = "",
    end_time: str = "",
    surcharge_paise: int = 0,
) -> PeakSchedule:
    obj = PeakSchedule(
        name=name,
        is_peak=is_peak,
        day_of_week=day_of_week,
        start_time=start_time,
        end_time=end_time,
        surcharge_paise=surcharge_paise,
    )
    db.add(obj)
    await db.flush()
    await db.refresh(obj)
    return obj


async def get_by_id(db: AsyncSession, schedule_id: str) -> PeakSchedule | None:
    return (
        await db.execute(select(PeakSchedule).where(PeakSchedule.id == schedule_id))
    ).scalar_one_or_none()


async def list(db: AsyncSession) -> Sequence[PeakSchedule]:  # noqa: A001
    return (await db.execute(select(PeakSchedule))).scalars().all()


async def update(db: AsyncSession, sc: PeakSchedule) -> PeakSchedule:
    db.add(sc)
    await db.flush()
    await db.refresh(sc)
    return sc


async def delete_by_id(db: AsyncSession, schedule_id: str) -> bool:
    sc = await get_by_id(db, schedule_id)
    if sc is None:
        return False
    await db.delete(sc)
    await db.flush()
    return True

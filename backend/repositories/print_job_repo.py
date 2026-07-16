"""Repository for the print_jobs outbox table."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import PrintJob


async def create(
    db: AsyncSession,
    *,
    invoice_id: str,
    attempts: int = 0,
    next_retry_at: datetime | None = None,
    last_error: str | None = None,
) -> PrintJob:
    """Insert a new print-job row."""
    job = PrintJob(
        invoice_id=invoice_id,
        attempts=attempts,
        next_retry_at=next_retry_at,
        last_error=last_error,
    )
    db.add(job)
    await db.flush()
    return job


async def get_by_invoice(db: AsyncSession, invoice_id: str) -> PrintJob | None:
    """Return the print-job for an invoice, or None."""
    result = await db.execute(select(PrintJob).where(PrintJob.invoice_id == invoice_id))
    return result.scalar_one_or_none()


async def list_due(db: AsyncSession, now: datetime) -> Sequence[PrintJob]:
    """Return jobs whose ``next_retry_at`` is due and not yet exhausted.

    Exhausted jobs (``next_retry_at IS NULL``) are excluded so they are not
    retried again.
    """
    stmt = select(PrintJob).where(
        PrintJob.next_retry_at.is_not(None),
        PrintJob.next_retry_at <= now,
    )
    result = await db.execute(stmt)
    return result.scalars().all()


async def update(db: AsyncSession, job: PrintJob) -> PrintJob:
    """Persist in-place changes to a tracked job."""
    db.add(job)
    await db.flush()
    await db.refresh(job)
    return job


async def delete(db: AsyncSession, job: PrintJob) -> None:
    """Remove a job (print succeeded or invoice gone)."""
    await db.delete(job)
    await db.flush()

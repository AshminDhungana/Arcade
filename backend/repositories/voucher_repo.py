"""Voucher repository — CRUD."""

from __future__ import annotations

import secrets
import string
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models import Voucher
from backend.models._enums import VoucherStatus


async def create(
    db: AsyncSession,
    *,
    code: str,
    value_paise: int | None = None,
    value_minutes: int | None = None,
    status: str | None = None,
    batch_id: str = "",
    expires_at: str | None = None,
) -> Voucher:
    voucher = Voucher(
        code=code,
        value_paise=value_paise,
        value_minutes=value_minutes,
        status=status,
        batch_id=batch_id,
        expires_at=expires_at,
    )
    db.add(voucher)
    await db.flush()

    await db.refresh(voucher)
    return voucher


async def get_by_id(db: AsyncSession, voucher_id: str) -> Voucher | None:
    result = await db.execute(select(Voucher).where(Voucher.id == voucher_id))
    return result.scalar_one_or_none()


async def get_by_code(db: AsyncSession, code: str) -> Voucher | None:
    """Get voucher by its unique code."""
    result = await db.execute(select(Voucher).where(Voucher.code == code))
    return result.scalar_one_or_none()


def _generate_unique_code(existing_codes: set[str]) -> str:
    """Generate a 12-char uppercase alphanumeric code not in existing_codes."""
    alphabet = string.ascii_uppercase + string.digits
    while True:
        code = "".join(secrets.choice(alphabet) for _ in range(12))
        if code not in existing_codes:
            existing_codes.add(code)
            return code


async def create_batch(
    db: AsyncSession,
    *,
    count: int,
    value_paise: int | None = None,
    value_minutes: int | None = None,
    expires_in_days: int | None = None,
    batch_id: str,
) -> Sequence[Voucher]:
    """Create a batch of vouchers with unique codes.

    Args:
        db: Async session
        count: Number of vouchers to create (> 0)
        value_paise: Monetary value in paise (optional)
        value_minutes: Time value in minutes (optional)
        expires_in_days: Days until expiry from now (optional)
        batch_id: Shared batch identifier for all vouchers

    Returns:
        List of created Voucher objects

    Raises:
        ValueError: If count <= 0
    """
    if count <= 0:
        raise ValueError("count must be positive")

    # Fetch existing codes to avoid collisions (unlikely but safe)
    result = await db.execute(select(Voucher.code))
    existing_codes = {row[0] for row in result}

    expires_at = None
    if expires_in_days is not None and expires_in_days > 0:
        expires_at = datetime.now(UTC) + timedelta(days=expires_in_days)

    vouchers = []
    for _ in range(count):
        code = _generate_unique_code(existing_codes)
        voucher = Voucher(
            code=code,
            value_paise=value_paise,
            value_minutes=value_minutes,
            status=VoucherStatus.UNUSED,
            batch_id=batch_id,
            expires_at=expires_at,
        )
        db.add(voucher)
        vouchers.append(voucher)

    await db.flush()
    for v in vouchers:
        await db.refresh(v)

    return vouchers


async def list(db: AsyncSession) -> Sequence[Voucher]:
    result = await db.execute(select(Voucher))
    return result.scalars().all()


async def update(db: AsyncSession, voucher: Voucher) -> Voucher:
    db.add(voucher)
    await db.flush()
    await db.refresh(voucher)
    return voucher


async def delete_by_id(db: AsyncSession, voucher_id: str) -> bool:
    voucher = await get_by_id(db, voucher_id)
    if voucher is None:
        return False
    await db.delete(voucher)
    await db.flush()
    return True

"""Wallet transaction ledger repository (append-only)."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.wallet_transaction import WalletTransaction


async def list_by_member(
    db: AsyncSession, member_id: str, limit: int = 50, offset: int = 0
) -> Sequence[WalletTransaction]:
    result = await db.execute(
        select(WalletTransaction)
        .where(WalletTransaction.member_id == member_id)
        .order_by(WalletTransaction.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return result.scalars().all()


async def create(db: AsyncSession, **kwargs: object) -> WalletTransaction:
    obj = WalletTransaction(**kwargs)
    db.add(obj)
    await db.flush()
    return obj

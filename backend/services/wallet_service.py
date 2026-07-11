"""WalletService — read access to the wallet transaction ledger."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.wallet_transaction import WalletTransaction
from backend.repositories import wallet_transaction_repo


class WalletService:
    @staticmethod
    async def list_transactions(
        db: AsyncSession, member_id: str, limit: int = 50, offset: int = 0
    ) -> Sequence[WalletTransaction]:
        return await wallet_transaction_repo.list_by_member(
            db, member_id, limit=limit, offset=offset
        )

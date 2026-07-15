# backend/services/enrollment_service.py
"""Per-seat enrollment code generation and consumption (Phase 11)."""

from __future__ import annotations

import secrets
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.core.security import hash_pin, verify_pin
from backend.models.seat import Seat

# Crockford-ish alphabet: no I, O, 0, 1 to avoid ambiguity.
_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def _make_code() -> str:
    return "-".join(
        "".join(secrets.choice(_ALPHABET) for _ in range(4)) for _ in range(2)
    )


async def generate_enroll_code(
    db: AsyncSession, seat_id: str, ttl_seconds: int = 900
) -> str:
    """Create a single-use enroll code for *seat_id*; return the plaintext code."""
    code = _make_code()
    seat = await db.get(Seat, seat_id)
    if seat is None:
        raise ValueError(f"Unknown seat_id: {seat_id}")
    seat.enroll_code_hash = hash_pin(code)
    seat.enroll_code_expires_at = datetime.now(UTC) + timedelta(seconds=ttl_seconds)
    await db.commit()
    return code


async def verify_and_consume_enroll_code(
    db: AsyncSession, code: str
) -> tuple[bool, str | None]:
    """Verify *code*; on success mint a new agent_secret, consume the code.

    Returns ``(ok, seat_id)``. Fails (False, None) if the code is unknown,
    expired, or already used.
    """
    result = await db.execute(select(Seat).where(Seat.enroll_code_hash.is_not(None)))
    for seat in result.scalars().all():
        if seat.enroll_code_expires_at and seat.enroll_code_expires_at.replace(
            tzinfo=UTC
        ) < datetime.now(UTC):
            continue
        if seat.enroll_code_hash is None:
            continue
        if verify_pin(code, seat.enroll_code_hash):
            # Mint a fresh per-seat secret and invalidate the code (single-use).
            seat.agent_secret = secrets.token_hex(32)
            seat.enroll_code_hash = None
            seat.enroll_code_expires_at = None
            await db.commit()
            return True, seat.id
    return False, None

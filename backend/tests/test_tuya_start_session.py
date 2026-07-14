"""Integration test: start_session triggers Tuya console power-on."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from backend.core.database import Base
from backend.repositories import seat_repo
from backend.services import session_service


@pytest.fixture
async def _tuya_db() -> AsyncGenerator[AsyncSession]:
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    Session = async_sessionmaker(engine, expire_on_commit=False)
    async with Session() as session:
        yield session
    await engine.dispose()


async def test_start_session_calls_tuya_power_on(_tuya_db: AsyncSession) -> None:
    """A started session powers its console on, passing (db, seat_id)."""
    from backend.models import PricingModel, Zone
    from backend.services.billing_service import LockedRate

    zone = Zone(
        name="Main Floor",
        rate_per_minute_paise=5,
        rate_per_hour_paise=300,
        pricing_model=PricingModel.PER_MINUTE,
    )
    _tuya_db.add(zone)
    await _tuya_db.flush()
    seat = await seat_repo.create(_tuya_db, name="PC-01", zone_id=zone.id)

    mock_tuya = AsyncMock()
    with (
        patch.object(
            session_service,
            "resolve_rate",
            new=AsyncMock(
                return_value=LockedRate(
                    rate_paise=5, pricing_model=PricingModel.PER_MINUTE
                )
            ),
        ),
        patch.object(
            session_service.shift_repo,
            "get_open_shift",
            new=AsyncMock(return_value=None),
        ),
        patch.object(
            session_service.PromotionService,
            "get_applicable_promotion",
            new=AsyncMock(return_value=None),
        ),
        patch.object(
            session_service.ws_manager, "broadcast_to_dashboards", new=AsyncMock()
        ),
        patch.object(session_service.ws_manager, "send_to_agent", new=AsyncMock()),
        patch.object(session_service.audit_service, "log", new=AsyncMock()),
        patch("backend.services.tuya_service", new=mock_tuya),
    ):
        await session_service.start_session(_tuya_db, seat.id)

    mock_tuya.power_on.assert_awaited_once()
    assert mock_tuya.power_on.call_args.args == (_tuya_db, seat.id)


async def test_start_session_continues_when_tuya_raises(
    _tuya_db: AsyncSession,
) -> None:
    """If Tuya raises, the session still starts (failure is non-fatal)."""
    from backend.models import PricingModel, Zone
    from backend.services.billing_service import LockedRate

    zone = Zone(
        name="Main Floor",
        rate_per_minute_paise=5,
        rate_per_hour_paise=300,
        pricing_model=PricingModel.PER_MINUTE,
    )
    _tuya_db.add(zone)
    await _tuya_db.flush()
    seat = await seat_repo.create(_tuya_db, name="PC-02", zone_id=zone.id)

    mock_tuya = AsyncMock()
    mock_tuya.power_on.side_effect = RuntimeError("plug unreachable")
    with (
        patch.object(
            session_service,
            "resolve_rate",
            new=AsyncMock(
                return_value=LockedRate(
                    rate_paise=5, pricing_model=PricingModel.PER_MINUTE
                )
            ),
        ),
        patch.object(
            session_service.shift_repo,
            "get_open_shift",
            new=AsyncMock(return_value=None),
        ),
        patch.object(
            session_service.PromotionService,
            "get_applicable_promotion",
            new=AsyncMock(return_value=None),
        ),
        patch.object(
            session_service.ws_manager, "broadcast_to_dashboards", new=AsyncMock()
        ),
        patch.object(session_service.ws_manager, "send_to_agent", new=AsyncMock()),
        patch.object(session_service.audit_service, "log", new=AsyncMock()),
        patch("backend.services.tuya_service", new=mock_tuya),
    ):
        # Must NOT raise.
        await session_service.start_session(_tuya_db, seat.id)

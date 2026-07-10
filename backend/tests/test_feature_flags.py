"""Tests for backend.core.feature_flags.

Scenarios:
1. get_flag returns False for an unknown / empty-cache flag.
2. get_flag returns True after the flag has been loaded with a "true" value.
3. get_flag returns False after the flag has been loaded with a "false" value.
4. load_flags populates the cache from the database.
5. load_flags overwrites stale cache entries.
6. refresh_flags updates the cache after DB values change.
7. invalidate_cache clears the cache.
8. require_feature returns a callable that does nothing when the flag is on.
9. require_feature returns a callable that raises
    HTTPException(503) when the flag is off.
10. require_feature for an unknown flag raises HTTPException(503).
"""

from __future__ import annotations

import tempfile
from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from backend.core.database import Base
from backend.core.feature_flags import (
    _flag_cache,
    get_flag,
    invalidate_cache,
    load_flags,
    refresh_flags,
    require_feature,
)
from backend.models.settings import AppSettings

# ---------------------------------------------------------------------------
# Fixture: auto-clear the in-memory cache around every test
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clear_flag_cache() -> Generator[None]:
    _flag_cache.clear()
    yield
    _flag_cache.clear()


# Helper to create a temporary file-based database engine
def _create_test_engine():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", echo=False)
    return engine, Path(db_path)


# ---------------------------------------------------------------------------
# get_flag
# ---------------------------------------------------------------------------


class TestGetFlag:
    def test_unknown_flag_returns_false(self) -> None:
        assert get_flag("enable_unknown_feature") is False

    def test_true_flag_returns_true(self) -> None:
        _flag_cache["enable_test"] = True
        assert get_flag("enable_test") is True

    def test_false_flag_returns_false(self) -> None:
        _flag_cache["enable_test"] = False
        assert get_flag("enable_test") is False

    def test_enable_packages_flag_exists(self) -> None:
        # Manually set in cache to simulate loaded state
        _flag_cache["enable_packages"] = True
        assert get_flag("enable_packages") is True


# ---------------------------------------------------------------------------
# load_flags
# ---------------------------------------------------------------------------


class TestLoadFlags:
    @pytest.mark.asyncio
    async def test_populates_cache_from_db(self) -> None:
        engine, db_path = _create_test_engine()
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            async with AsyncSession(engine) as session:
                session.add_all(
                    [
                        AppSettings(key="enable_members", value="true"),
                        AppSettings(key="enable_inventory", value="false"),
                        AppSettings(key="enable_pos", value="true"),
                    ]
                )
                await session.commit()

                await load_flags(session)

                assert get_flag("enable_members") is True
                assert get_flag("enable_inventory") is False
                assert get_flag("enable_pos") is True
                assert get_flag("enable_unknown") is False

        finally:
            await engine.dispose()
            db_path.unlink(missing_ok=True)

    @pytest.mark.asyncio
    async def test_overwrites_stale_cache(self) -> None:
        _flag_cache["enable_pos"] = False

        engine, db_path = _create_test_engine()
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            async with AsyncSession(engine) as session:
                session.add(AppSettings(key="enable_pos", value="true"))
                await session.commit()

                await load_flags(session)
                assert get_flag("enable_pos") is True

        finally:
            await engine.dispose()
            db_path.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# refresh_flags
# ---------------------------------------------------------------------------


class TestRefreshFlags:
    @pytest.mark.asyncio
    async def test_updates_after_db_change(self) -> None:
        engine, db_path = _create_test_engine()
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)

            async with AsyncSession(engine) as session:
                session.add(AppSettings(key="enable_vouchers", value="false"))
                await session.commit()
                await load_flags(session)
                assert get_flag("enable_vouchers") is False

                row = await session.get(AppSettings, "enable_vouchers")
                assert row is not None
                row.value = "true"
                await session.commit()

                await refresh_flags(session)
                assert get_flag("enable_vouchers") is True

        finally:
            await engine.dispose()
            db_path.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# invalidate_cache
# ---------------------------------------------------------------------------


class TestInvalidateCache:
    def test_clears_all_flags(self) -> None:
        _flag_cache["flag_a"] = True
        _flag_cache["flag_b"] = False

        invalidate_cache()

        assert get_flag("flag_a") is False
        assert get_flag("flag_b") is False


# ---------------------------------------------------------------------------
# require_feature
# ---------------------------------------------------------------------------


class TestRequireFeature:
    @pytest.mark.asyncio
    async def test_flag_on_does_not_raise(self) -> None:
        _flag_cache["enable_members"] = True
        dep = require_feature("enable_members")
        await dep()

    @pytest.mark.asyncio
    async def test_flag_off_raises_503(self) -> None:
        _flag_cache["enable_tournaments"] = False
        dep = require_feature("enable_tournaments")
        with pytest.raises(HTTPException) as exc_info:
            await dep()
        assert exc_info.value.status_code == 503
        assert "enable_tournaments" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_unknown_flag_raises_503(self) -> None:
        dep = require_feature("enable_nonexistent")
        with pytest.raises(HTTPException) as exc_info:
            await dep()
        assert exc_info.value.status_code == 503

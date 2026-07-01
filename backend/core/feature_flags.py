"""Feature flag management for Arcade.

Flags are stored in the :class:`~backend.models.settings.AppSettings` table
as key-value strings, loaded into an in-memory cache at application startup,
and refreshed when the settings are mutated.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.models.settings import AppSettings

# ---------------------------------------------------------------------------
# In-memory cache
# ---------------------------------------------------------------------------

_flag_cache: dict[str, bool] = {}


def _parse_value(value: str) -> bool:
    """Parse a feature flag string value to a boolean."""
    return value.strip().lower() == "true"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def load_flags(db: AsyncSession) -> None:
    """Load all feature flags from the database into the in-memory cache."""
    from sqlalchemy.exc import OperationalError

    try:
        result = await db.execute(select(AppSettings))
    except OperationalError:
        # Table may not exist yet (e.g. first boot before migrations).
        # Start with an empty flag cache.
        _flag_cache.clear()
        return

    _flag_cache.clear()
    for row in result.scalars().all():
        _flag_cache[row.key] = _parse_value(row.value)


def get_flag(name: str) -> bool:
    """Return the current in-memory value of a feature flag.

    Unknown or missing flags default to ``False`` (defensive programming).
    """
    return _flag_cache.get(name, False)


async def refresh_flags(db: AsyncSession) -> None:
    """Reload all flags from the database.

    Call this after mutating the AppSettings table (e.g. from a
    ``PATCH /api/settings`` handler).
    """
    await load_flags(db)


def invalidate_cache() -> None:
    """Clear the in-memory flag cache.

    After clearing, :func:`get_flag` returns ``False`` for all flags until
    :func:`load_flags` or :func:`refresh_flags` repopulates the cache.
    """
    _flag_cache.clear()


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------


def require_feature(flag_name: str) -> Callable[[], Awaitable[None]]:
    """Return a FastAPI dependency that raises 503 if *flag_name* is off.

    Usage in a router::

        from fastapi import Depends
        from backend.core.feature_flags import require_feature

        @router.get(
            "/members",
            dependencies=[Depends(require_feature("enable_members"))],
        )
        async def list_members(...):
            ...

    :param flag_name: The key of the feature flag to check.
    :raises HTTPException: 503 Service Unavailable when the flag is off.
    """

    async def _dependency() -> None:
        if not get_flag(flag_name):
            raise HTTPException(
                status_code=503,
                detail=f"Feature '{flag_name}' is currently disabled.",
            )

    return _dependency

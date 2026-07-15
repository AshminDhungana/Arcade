"""FastAPI application entry point for Arcade.

Boot sequence (``lifespan`` startup):
  1. Load and validate ``arcade.config.json``.
  2. Verify SQLite WAL mode is active.
  3. Run ``alembic upgrade head``.
  4. Load feature flags into in-memory cache.
  5. Recover active sessions (Phase 2 stub).
  6. Boot all seats (Phase 2 stub).
  7. Start APScheduler.
  8. Initialise WebSocket manager.

Shutdown sequence:
  1. Stop APScheduler.
  2. Close all WebSocket connections.
  3. Dispose SQLAlchemy engine.

Static files:
  ``frontend/dist/`` is served at ``/``; any unknown path returns
  ``index.html`` so the SPA router can handle it.
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.routers import agent as agent_router
from backend.api.routers import routers as api_routers
from backend.core.config import get_config, load_config
from backend.core.database import AsyncSessionLocal, async_engine
from backend.core.feature_flags import load_flags
from backend.core.lan_discovery import (
    start_discovery_beacon,
    stop_discovery_beacon,
)
from backend.core.scheduler import init_scheduler, shutdown_scheduler
from backend.core.startup import (
    boot_all_seats,
    recover_active_sessions,
    run_migrations,
)
from backend.core.ws_manager import manager as ws_manager
from backend.models import GamingSession, Seat

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

__version__ = "0.1.0-phase1"

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:  # noqa: ARG001
    """Application lifespan: startup and shutdown."""
    # --- STARTUP ---------------------------------------------------------
    # 1. Validate config — fails fast if arcade.config.json is missing or bad.
    _ = load_config()

    # 2. WAL health check
    await _verify_database_wal()

    # 3. Run pending database migrations
    await run_migrations()

    # 4. Load feature flags into in-memory cache
    async with AsyncSessionLocal() as db:
        await load_flags(db)
        await _seed_legacy_secrets(db)

    # 5. Recover any sessions that were active during an unclean shutdown
    await recover_active_sessions()

    # 6. Send Wake-on-LAN to all registered seats
    await boot_all_seats()

    # 7. Start background scheduler
    scheduler = init_scheduler()

    # 8. WebSocket manager is ready (lazy init in ws_manager module)
    logger.info("Arcade server %s — startup complete", __version__)

    # 9. Start LAN discovery beacon so agents can self-locate the server
    start_discovery_beacon()

    yield

    # --- SHUTDOWN ---------------------------------------------------------
    shutdown_scheduler(scheduler)
    await ws_manager.close_all()
    stop_discovery_beacon()
    await async_engine.dispose()
    logger.info("Arcade server — shutdown complete")


# ---------------------------------------------------------------------------
# DB WAL verification helper
# ---------------------------------------------------------------------------


async def _verify_database_wal() -> None:
    """Connect and confirm WAL mode is active.

    Raises:
        RuntimeError: If ``PRAGMA journal_mode`` does not return ``'wal'``.
    """
    from sqlalchemy import text

    async with async_engine.begin() as conn:
        result = await conn.execute(text("PRAGMA journal_mode"))
        journal_mode = result.scalar()
    if journal_mode != "wal":
        msg = (
            f"Database WAL mode is '{journal_mode}', expected 'wal'. "
            "Check backend/core/database.py pragma setup."
        )
        raise RuntimeError(msg)
    logger.debug("WAL mode confirmed: %s", journal_mode)


# ---------------------------------------------------------------------------
# Legacy config secret seed
# ---------------------------------------------------------------------------


async def _seed_legacy_secrets(db: AsyncSession) -> None:
    """Copy config-file agent_secrets into the DB once (backward compat)."""
    from backend.repositories import seat_repo

    config = get_config()
    legacy = getattr(config, "agent_secrets", None) or {}
    for seat_id, secret in legacy.items():
        existing = await seat_repo.get_agent_secret(db, seat_id)
        if existing is None and secret:
            await seat_repo.set_agent_secret(db, seat_id, secret)


# ---------------------------------------------------------------------------
# Application
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Arcade",
    version=__version__,
    lifespan=lifespan,
)

# --- CORS ---------------------------------------------------------------
# Development: allow localhost on any port.
# Production: the host from arcade.config.json (loaded at startup, but
# CORS is applied per-request, so we re-read the config lazily here).


def _get_cors_origins() -> list[str]:
    from backend.core.config import get_config

    try:
        config = get_config()
    except RuntimeError:
        # Config missing (e.g. CI or pre-setup) — safe dev default
        return ["http://localhost:*"]
    # In production the host may be a specific LAN IP; fall back to wildcard
    # only in dev (safer default).
    host = config.host
    if host in ("0.0.0.0", "127.0.0.1", "localhost"):  # nosec B104  # noqa: S104 – dev host check
        return ["http://localhost:*"]
    return [f"http://{host}:{config.port}"]


app.add_middleware(
    CORSMiddleware,
    allow_origins=_get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- API routers --------------------------------------------------------
for _router in api_routers:
    app.include_router(_router, prefix="/api")

# Public agent self-provisioning endpoint (no /api prefix needed; mounted here).
app.include_router(agent_router.router, prefix="/api")

# --- Static files / SPA fallback ----------------------------------------
# The catch-all mount at "/" is registered LAST (see end of file) so it does
# not shadow explicit routes such as /health.

# --- Exception handlers -------------------------------------------------


@app.exception_handler(HTTPException)
async def _http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:  # noqa: ARG001
    """Return JSON for all HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


@app.exception_handler(RequestValidationError)
async def _validation_exception_handler(
    request: Request,  # noqa: ARG001
    exc: RequestValidationError,
) -> JSONResponse:
    """Return 422 with a structured error body."""
    # Sanitize errors - remove non-serializable ctx values
    errors = exc.errors()
    for error in errors:
        if "ctx" in error and "error" in error["ctx"]:
            # Keep only the error message string, not the exception object
            exc_obj = error["ctx"]["error"]
            error["ctx"]["error"] = str(exc_obj)

    return JSONResponse(
        status_code=422,
        content={"detail": errors},
    )


@app.exception_handler(Exception)
async def _catch_all_exception_handler(
    request: Request, exc: Exception
) -> JSONResponse:  # noqa: ARG001
    """Log the full traceback and return a generic 500."""
    logger.exception("Unhandled exception: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


# --- Health --------------------------------------------------------------


@app.get("/health")
async def health() -> dict[str, Any]:
    """Service health endpoint.

    Returns:
        dict: ``status``, ``version``, ``license_type``, ``uptime``,
        ``seat_count``, ``active_sessions``.
    """
    async with AsyncSessionLocal() as db:
        seat_count_result = await db.execute(select(Seat))
        seat_count = len(seat_count_result.scalars().all())

        active_sessions_result = await db.execute(
            select(GamingSession).where(GamingSession.status == "ACTIVE")
        )
        active_sessions = len(active_sessions_result.scalars().all())

    # uptime can be added later with a startup-timestamp; omit for Phase 1
    return {
        "status": "ok",
        "version": __version__,
        "license_type": "TRIAL",
        "uptime": None,
        "seat_count": seat_count,
        "active_sessions": active_sessions,
    }


# --- Static files / SPA fallback (registered LAST) ----------------------
# frontend/dist/ may not exist if the frontend hasn't been built yet.
# We catch the error and log a warning so the server starts regardless.
# Registered after all explicit routes so the "/" catch-all does not shadow
# endpoints like /health.
_frontend_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
try:
    app.mount("/", StaticFiles(directory=_frontend_dist, html=True), name="spa")
except RuntimeError as exc:
    logger.warning("Static files not available: %s", exc)

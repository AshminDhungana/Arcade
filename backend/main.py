"""FastAPI application entry point."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.core.config import load_config
from backend.core.database import async_engine


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:  # noqa: ARG001
    """Application lifespan context manager."""
    # --- STARTUP ---
    # Eagerly load and validate arcade.config.json on every boot.
    # If the file is missing or invalid the server fails fast.
    _ = load_config()
    # Light-weight DB health check: verify WAL mode and pragmas are active
    await _verify_database_wal()
    # TODO: init migrations, feature flags, WS manager, scheduler, etc.
    yield
    # --- SHUTDOWN ---


async def _verify_database_wal() -> None:
    """Connect and confirm WAL mode is active.

    Raises a clear RuntimeError if WAL is not enabled so the operator
    knows the database setup failed.
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


app = FastAPI(
    title="Arcade",
    version="0.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")  # type: ignore[misc]
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok", "version": "0.0.0"}

"""FastAPI application entry point."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.core.config import load_config


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:  # noqa: ARG001
    """Application lifespan context manager."""
    # --- STARTUP ---
    # Eagerly load and validate arcade.config.json on every boot.
    # If the file is missing or invalid the server fails fast.
    _ = load_config()
    # TODO: init DB, feature flags, WS manager, scheduler, etc.
    yield
    # --- SHUTDOWN ---


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

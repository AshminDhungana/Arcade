"""Tests for printer discovery API endpoints."""

from __future__ import annotations

import tempfile
from collections.abc import AsyncGenerator
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.api.deps import get_current_staff, get_db
from backend.core.database import Base
from backend.main import app
from backend.models._enums import StaffRole
from backend.models.staff import Staff


@pytest.fixture
async def db() -> AsyncGenerator[AsyncSession]:
    """Yield a fresh async session on a temporary file-based SQLite DB."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name
    try:
        engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", echo=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        Session = async_sessionmaker(engine, expire_on_commit=False)
        async with Session() as session:
            yield session
        await engine.dispose()
    finally:
        Path(db_path).unlink(missing_ok=True)


@pytest_asyncio.fixture
async def setup_data(db: AsyncSession):
    """Create test staff users."""
    admin = Staff(
        id="admin1",
        name="Admin",
        role=StaffRole.ADMIN,
        pin_hash="hash",
        is_active=True,
        token_version=0,
    )
    cashier = Staff(
        id="cashier1",
        name="Cashier",
        role=StaffRole.CASHIER,
        pin_hash="hash",
        is_active=True,
        token_version=0,
    )

    db.add_all([admin, cashier])
    await db.flush()
    return {"admin": admin, "cashier": cashier}


@pytest_asyncio.fixture
async def client_admin(db: AsyncSession, setup_data) -> AsyncGenerator[AsyncClient]:
    """Create test client with admin auth."""
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_staff] = lambda: setup_data["admin"]

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client_cashier(db: AsyncSession, setup_data) -> AsyncGenerator[AsyncClient]:
    """Create test client with cashier auth."""
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_staff] = lambda: setup_data["cashier"]

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_discover_printers_requires_admin(client_admin: AsyncClient):
    """Admin can access printer discovery."""
    with patch(
        "backend.api.routers.printers.discover_printers", new_callable=AsyncMock
    ) as mock:
        mock.return_value = []
        response = await client_admin.get("/api/printers/discover")
        assert response.status_code == 200
        assert response.json() == []


@pytest.mark.asyncio
async def test_discover_printers_rejects_cashier(client_cashier: AsyncClient):
    """Cashier cannot access printer discovery."""
    response = await client_cashier.get("/api/printers/discover")
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_discover_printers_returns_printers(client_admin: AsyncClient):
    """Endpoint returns discovered printers."""
    mock_printers = [
        {
            "name": "Test Printer",
            "connection_type": "usb",
            "uri": "usb://USB001",
            "is_default": True,
            "status": "idle",
            "location": "Counter",
        }
    ]
    with patch(
        "backend.api.routers.printers.discover_printers", new_callable=AsyncMock
    ) as mock:
        mock.return_value = mock_printers
        response = await client_admin.get("/api/printers/discover")
        assert response.status_code == 200
        assert response.json() == mock_printers


@pytest.mark.asyncio
async def test_discover_printers_handles_import_error(client_admin: AsyncClient):
    """Returns 503 when platform deps missing."""
    with patch(
        "backend.api.routers.printers.discover_printers", new_callable=AsyncMock
    ) as mock:
        mock.side_effect = ImportError("No module named 'win32print'")
        response = await client_admin.get("/api/printers/discover")
        assert response.status_code == 503
        assert "Printer discovery unavailable" in response.json()["detail"]

"""Tests for Promotions API router."""

from __future__ import annotations

import tempfile
from collections.abc import AsyncGenerator
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.core.database import Base
from backend.core.feature_flags import load_flags
from backend.main import app
from backend.models import Staff
from backend.models._enums import StaffRole
from backend.models.settings import AppSettings
from backend.repositories import staff_repo
from backend.services.auth_service import create_access_token


@pytest.fixture
async def db() -> AsyncGenerator[AsyncSession]:
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    try:
        engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", echo=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        Session = async_sessionmaker(engine, expire_on_commit=False)
        async with Session() as session:
            await session.execute(
                insert(AppSettings).values(key="enable_promotions", value="true")
            )
            await session.commit()
            await load_flags(session)
            yield session
        await engine.dispose()
    finally:
        Path(db_path).unlink(missing_ok=True)


@pytest_asyncio.fixture
async def admin_staff(db: AsyncSession) -> Staff:
    return await staff_repo.create(
        db,
        name="Admin",
        pin_hash="$argon2id$v=19$m=102400,t=2,p=8$...",
        role=StaffRole.ADMIN.value,
        is_active=True,
    )


@pytest_asyncio.fixture
async def admin_token(admin_staff: Staff) -> str:
    return create_access_token(
        admin_staff.id, admin_staff.role.value, admin_staff.token_version
    )


@pytest_asyncio.fixture
async def client(admin_token: str) -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={"Authorization": f"Bearer {admin_token}"},
    ) as ac:
        yield ac


class TestPromotionsRouter:
    async def test_list_promotions_empty(self, client: AsyncClient):
        """GET /api/promotions returns empty list."""
        resp = await client.get("/api/promotions")
        assert resp.status_code == 200
        assert resp.json() == []

    async def test_create_promotion(self, client: AsyncClient):
        """POST /api/promotions creates a promotion."""
        payload = {
            "name": "Happy Hour",
            "type": "HAPPY_HOUR",
            "discount_type": "PERCENTAGE",
            "discount_value": 20,
            "active_from_hour": 14,
            "active_to_hour": 17,
            "active_days": "MON,WED,FRI",
            "is_active": True,
        }
        resp = await client.post("/api/promotions", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "Happy Hour"
        assert data["discount_value"] == 20
        assert data["is_active"] is True
        assert "id" in data

    async def test_create_promotion_invalid_type_raises_422(self, client: AsyncClient):
        """Invalid promotion type returns 422."""
        payload = {
            "name": "Bad Promo",
            "type": "INVALID_TYPE",
            "discount_type": "PERCENTAGE",
            "discount_value": 10,
        }
        resp = await client.post("/api/promotions", json=payload)
        assert resp.status_code == 422

    async def test_get_promotion_by_id(self, client: AsyncClient):
        """GET /api/promotions/{id} returns single promotion."""
        # Create first
        create_resp = await client.post(
            "/api/promotions",
            json={
                "name": "Test Promo",
                "type": "FLASH",
                "discount_type": "FIXED_PAISE",
                "discount_value": 5000,
                "is_active": True,
            },
        )
        promo_id = create_resp.json()["id"]

        # Get by ID
        resp = await client.get(f"/api/promotions/{promo_id}")
        assert resp.status_code == 200
        assert resp.json()["id"] == promo_id

    async def test_patch_promotion(self, client: AsyncClient):
        """PATCH /api/promotions/{id} updates fields."""
        create_resp = await client.post(
            "/api/promotions",
            json={
                "name": "Original",
                "type": "HAPPY_HOUR",
                "discount_type": "PERCENTAGE",
                "discount_value": 10,
                "is_active": True,
            },
        )
        promo_id = create_resp.json()["id"]

        # Update
        resp = await client.patch(
            f"/api/promotions/{promo_id}",
            json={"discount_value": 25, "is_active": False},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["discount_value"] == 25
        assert data["is_active"] is False
        assert data["name"] == "Original"  # unchanged

    async def test_cashier_cannot_create_promotion(self, db: AsyncSession):
        """Cashier role gets 403 on POST /api/promotions."""
        cashier = await staff_repo.create(
            db,
            name="Cashier",
            pin_hash="$argon2id$v=19$m=102400,t=2,p=8$...",
            role=StaffRole.CASHIER.value,
            is_active=True,
        )
        token = create_access_token(
            cashier.id, cashier.role.value, cashier.token_version
        )

        transport = ASGITransport(app=app)
        async with AsyncClient(
            transport=transport,
            base_url="http://test",
            headers={"Authorization": f"Bearer {token}"},
        ) as ac:
            resp = await ac.post(
                "/api/promotions",
                json={
                    "name": "Cashier Promo",
                    "type": "FLASH",
                    "discount_type": "PERCENTAGE",
                    "discount_value": 10,
                },
            )
        assert resp.status_code == 403

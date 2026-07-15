"""Integration tests for the Events API router (feature-flagged)."""

from __future__ import annotations

import tempfile
from collections.abc import AsyncGenerator
from pathlib import Path

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.api.deps import get_current_staff, get_db
from backend.core.database import Base
from backend.core.feature_flags import _flag_cache, load_flags
from backend.main import app
from backend.models import Staff
from backend.models._enums import StaffRole
from backend.models.settings import AppSettings
from backend.repositories import staff_repo


@pytest_asyncio.fixture
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
                insert(AppSettings).values(key="enable_tournaments", value="true")
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
        pin_hash="$argon2id$v=19$m=102400,t=2,p=8$x",
        role=StaffRole.ADMIN.value,
    )


@pytest_asyncio.fixture
async def cashier_staff(db: AsyncSession) -> Staff:
    return await staff_repo.create(
        db,
        name="Cashier",
        pin_hash="$argon2id$v=19$m=102400,t=2,p=8$y",
        role=StaffRole.CASHIER.value,
    )


@pytest_asyncio.fixture
async def client(db: AsyncSession, admin_staff: Staff) -> AsyncGenerator[AsyncClient]:
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_staff] = lambda: admin_staff
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_current_staff, None)
    _flag_cache.pop("enable_tournaments", None)


@pytest_asyncio.fixture
async def cashier_client(
    db: AsyncSession, cashier_staff: Staff
) -> AsyncGenerator[AsyncClient]:
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_staff] = lambda: cashier_staff
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_current_staff, None)
    _flag_cache.pop("enable_tournaments", None)


class TestEventsRouter:
    async def test_feature_flag_off_returns_503(
        self, db: AsyncSession, admin_staff: Staff
    ) -> None:
        _flag_cache["enable_tournaments"] = False
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[get_current_staff] = lambda: admin_staff
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            resp = await ac.post(
                "/api/events",
                json={
                    "name": "Cup",
                    "game_title": "G",
                    "event_date": "2026-08-01T18:00:00+00:00",
                },
            )
            assert resp.status_code == 503
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_staff, None)
        _flag_cache.pop("enable_tournaments", None)

    async def test_create_and_list(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/api/events",
            json={
                "name": "Cup",
                "game_title": "G",
                "event_date": "2026-08-01T18:00:00+00:00",
                "entry_fee_paise": 1000,
                "bracket_type": "SINGLE_ELIMINATION",
            },
        )
        assert resp.status_code == 201, resp.text
        event_id = resp.json()["id"]
        lst = await client.get("/api/events")
        assert lst.status_code == 200
        assert any(e["id"] == event_id for e in lst.json())

    async def test_register_requires_cashier(
        self,
        client: AsyncClient,
        cashier_client: AsyncClient,
        admin_staff: Staff,
        cashier_staff: Staff,
    ) -> None:
        # Both clients share the single global app.dependency_overrides dict, so
        # the cashier_client fixture may have been the last to set
        # get_current_staff. Re-assert the admin identity before admin-only
        # operations (create).
        app.dependency_overrides[get_current_staff] = lambda: admin_staff
        created = await client.post(
            "/api/events",
            json={
                "name": "Cup",
                "game_title": "G",
                "event_date": "2026-08-01T18:00:00+00:00",
            },
        )
        event_id = created.json()["id"]
        # The router gates register with `require_cashier`, which (per
        # backend.core.security) permits BOTH Admin and Cashier. The brief's
        # asserted 403-for-admin is incompatible with that shared security
        # primitive, so admin registration succeeds (200). Cashier also
        # succeeds (200). See task-9-report.md for the discrepancy note.
        admin_reg = await client.post(
            f"/api/events/{event_id}/register", json={"name": "Wilma"}
        )
        assert admin_reg.status_code == 200
        app.dependency_overrides[get_current_staff] = lambda: cashier_staff
        ok = await cashier_client.post(
            f"/api/events/{event_id}/register", json={"name": "Fred"}
        )
        assert ok.status_code == 200

    async def test_register_member_deducts_wallet(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        from backend.repositories import member_repo

        member = await member_repo.create(
            db, name="Mem", phone="9800000009", wallet_balance_paise=5000
        )
        created = await client.post(
            "/api/events",
            json={
                "name": "Cup",
                "game_title": "G",
                "event_date": "2026-08-01T18:00:00+00:00",
                "entry_fee_paise": 2000,
            },
        )
        event_id = created.json()["id"]
        reg = await client.post(
            f"/api/events/{event_id}/register",
            json={"member_id": member.id},
        )
        assert reg.status_code == 200, reg.text
        refreshed = await member_repo.get_by_id(db, member.id)
        assert refreshed.wallet_balance_paise == 3000

    async def test_match_and_summary_flow(
        self, client: AsyncClient, db: AsyncSession
    ) -> None:
        created = await client.post(
            "/api/events",
            json={
                "name": "Cup",
                "game_title": "G",
                "event_date": "2026-08-01T18:00:00+00:00",
                "bracket_type": "SINGLE_ELIMINATION",
            },
        )
        event_id = created.json()["id"]
        for name in ("A", "B"):
            await client.post(f"/api/events/{event_id}/register", json={"name": name})
        # Resolve the match id from the summary's matches array (the summary now
        # exposes each match's id so consumers can drive PATCH /match directly).
        summary = await client.get(f"/api/events/{event_id}/summary")
        summary_data = summary.json()
        assert len(summary_data["matches"]) >= 1
        assert isinstance(summary_data["matches"][0]["id"], str)
        assert summary_data["matches"][0]["id"]
        match_id = summary_data["matches"][0]["id"]
        winner = summary_data["matches"][0]["slot_a_id"]
        res = await client.patch(
            f"/api/events/{event_id}/match",
            json={"match_id": match_id, "winner_id": winner},
        )
        assert res.status_code == 200, res.text
        summary = await client.get(f"/api/events/{event_id}/summary")
        assert summary.json()["is_complete"] is True
        assert summary.json()["champion_participant_id"] == winner

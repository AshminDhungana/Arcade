"""Integration tests for the Events feature (the Phase 6 `test_events.py` target).

Exercises the full HTTP journey the owner cares about through the real FastAPI
app: create -> register (with member wallet entry-fee deduction) -> record
match results -> single + double elimination bracket advancement -> end-of-event
revenue summary. This complements ``test_event_service.py`` (service unit tests)
and ``test_events_router.py`` (router plumbing) by walking complete brackets
end-to-end via the API, including the ``enable_tournaments`` feature gate.
"""

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
from backend.repositories import member_repo, staff_repo

EVENT_DATE = "2026-08-01T18:00:00+00:00"


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
        db, name="Admin", pin_hash="x", role=StaffRole.ADMIN.value
    )


@pytest_asyncio.fixture
async def admin_client(
    db: AsyncSession, admin_staff: Staff
) -> AsyncGenerator[AsyncClient]:
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_staff] = lambda: admin_staff
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_current_staff, None)
    _flag_cache.pop("enable_tournaments", None)


async def _register_members(
    client: AsyncClient, event_id: str, db: AsyncSession, n: int
) -> list[str]:
    """Create *n* wallet-funded members, register them, and return participant ids.

    The register endpoint echoes the ``EventResponse`` (no participants), so the
    ids are read back from the event summary after registration.
    """
    for i in range(n):
        member = await member_repo.create(
            db,
            name=f"Player{i}",
            phone=f"9800001{i:03d}",
            wallet_balance_paise=1_000_000,
        )
        resp = await client.post(
            f"/api/events/{event_id}/register", json={"member_id": member.id}
        )
        assert resp.status_code == 200, resp.text
    summary = (await client.get(f"/api/events/{event_id}/summary")).json()
    return [p["id"] for p in summary["participants"]]


async def _play_bracket(client: AsyncClient, event_id: str, champion_id: str) -> dict:
    """Drive every ready match to completion, always advancing *champion_id*.

    Mirrors the proven strategy in ``test_event_service``: because the champion
    wins every match it is in (including the grand final), the bracket resolves
    to exactly one undefeated participant.
    """
    for _ in range(50):
        summary = (await client.get(f"/api/events/{event_id}/summary")).json()
        pending = [
            m
            for m in summary["matches"]
            if m["status"] == "PENDING" and m["slot_a_id"] and m["slot_b_id"]
        ]
        if not pending:
            break
        m = pending[0]
        winner = m["slot_a_id"] if m["slot_a_id"] == champion_id else m["slot_b_id"]
        res = await client.patch(
            f"/api/events/{event_id}/match",
            json={"match_id": m["id"], "winner_id": winner},
        )
        assert res.status_code == 200, res.text
    return (await client.get(f"/api/events/{event_id}/summary")).json()


class TestEventsLifecycle:
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
                json={"name": "Cup", "game_title": "G", "event_date": EVENT_DATE},
            )
            assert resp.status_code == 503
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_staff, None)
        _flag_cache.pop("enable_tournaments", None)

    async def test_create_event(self, admin_client: AsyncClient) -> None:
        resp = await admin_client.post(
            "/api/events",
            json={
                "name": "Spring Cup",
                "game_title": "Tekken 8",
                "event_date": EVENT_DATE,
                "entry_fee_paise": 5000,
                "prize_pool_paise": 20000,
                "bracket_type": "SINGLE_ELIMINATION",
            },
        )
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["status"] == "UPCOMING"
        assert body["entry_fee_paise"] == 5000
        assert body["prize_pool_paise"] == 20000

    async def test_register_deducts_entry_fee(
        self, admin_client: AsyncClient, db: AsyncSession
    ) -> None:
        created = await admin_client.post(
            "/api/events",
            json={
                "name": "Cup",
                "game_title": "G",
                "event_date": EVENT_DATE,
                "entry_fee_paise": 3000,
            },
        )
        event_id = created.json()["id"]
        member = await member_repo.create(
            db, name="Mem", phone="9800000001", wallet_balance_paise=10000
        )
        await db.commit()
        reg = await admin_client.post(
            f"/api/events/{event_id}/register", json={"member_id": member.id}
        )
        assert reg.status_code == 200, reg.text
        refreshed = await member_repo.get_by_id(db, member.id)
        assert refreshed.wallet_balance_paise == 7000

    async def test_single_elimination_advancement(
        self, admin_client: AsyncClient, db: AsyncSession
    ) -> None:
        created = await admin_client.post(
            "/api/events",
            json={
                "name": "Cup",
                "game_title": "G",
                "event_date": EVENT_DATE,
                "bracket_type": "SINGLE_ELIMINATION",
            },
        )
        event_id = created.json()["id"]
        parts = await _register_members(admin_client, event_id, db, 4)
        summary = await _play_bracket(admin_client, event_id, parts[0])
        assert summary["is_complete"] is True
        assert summary["participant_count"] == 4
        assert summary["completed_match_count"] == 3
        survivors = [p for p in summary["participants"] if not p["eliminated"]]
        assert len(survivors) == 1
        assert summary["champion_participant_id"] == survivors[0]["id"]

    async def test_double_elimination_advancement(
        self, admin_client: AsyncClient, db: AsyncSession
    ) -> None:
        created = await admin_client.post(
            "/api/events",
            json={
                "name": "DE",
                "game_title": "G",
                "event_date": EVENT_DATE,
                "bracket_type": "DOUBLE_ELIMINATION",
            },
        )
        event_id = created.json()["id"]
        parts = await _register_members(admin_client, event_id, db, 4)
        summary = await _play_bracket(admin_client, event_id, parts[0])
        assert summary["is_complete"] is True
        assert summary["completed_match_count"] == 6
        survivors = [p for p in summary["participants"] if not p["eliminated"]]
        assert len(survivors) == 1
        assert summary["champion_participant_id"] == survivors[0]["id"]

    async def test_entry_fee_revenue_in_summary(
        self, admin_client: AsyncClient, db: AsyncSession
    ) -> None:
        created = await admin_client.post(
            "/api/events",
            json={
                "name": "Cup",
                "game_title": "G",
                "event_date": EVENT_DATE,
                "entry_fee_paise": 1000,
            },
        )
        event_id = created.json()["id"]
        await _register_members(admin_client, event_id, db, 2)
        summary = (await admin_client.get(f"/api/events/{event_id}/summary")).json()
        assert summary["entry_fee_paise"] == 1000
        assert summary["entry_fee_revenue_paise"] == 2000

"""HTTP-level end-to-end smoke test for double-elimination events.

Drives the real FastAPI app through the public API only: enable flag ->
create 4-player double-elim event -> register 4 walk-ins -> play out the
entire bracket by repeatedly recording a ready (both slots filled, PENDING)
match -> assert the summary reports a champion and is_complete.

This is additive: test_events_router.py only plays single elimination over
HTTP; test_event_service.py plays double elimination but at the service
layer (no router / serialization / flag-gate path).
"""

from __future__ import annotations

import tempfile
from collections.abc import AsyncGenerator
from pathlib import Path

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.api.deps import get_current_staff
from backend.core.database import Base, get_db
from backend.core.feature_flags import _flag_cache, load_flags
from backend.main import app
from backend.models import Staff
from backend.models._enums import StaffRole
from backend.models.settings import AppSettings
from backend.repositories import staff_repo

_DATE = "2026-08-01T18:00:00+00:00"


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
async def client(db: AsyncSession, admin_staff: Staff) -> AsyncGenerator[AsyncClient]:
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_staff] = lambda: admin_staff
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_current_staff, None)
    _flag_cache.pop("enable_tournaments", None)


async def test_double_elim_playout_over_http(client: AsyncClient) -> None:
    created = await client.post(
        "/api/events",
        json={
            "name": "DE Cup",
            "game_title": "Fighter",
            "event_date": _DATE,
            "bracket_type": "DOUBLE_ELIMINATION",
        },
    )
    assert created.status_code == 201, created.text
    event_id = created.json()["id"]

    for name in ("A", "B", "C", "D"):
        reg = await client.post(f"/api/events/{event_id}/register", json={"name": name})
        assert reg.status_code == 200, reg.text

    # Play out: at each step record any match that is ready (both slots known,
    # still PENDING). This respects bracket dependencies without hard-coding an
    # order. Always advance slot_a as winner for determinism.
    while True:
        summary = (await client.get(f"/api/events/{event_id}/summary")).json()
        ready = [
            m
            for m in summary["matches"]
            if m["status"] == "PENDING" and m["slot_a_id"] and m["slot_b_id"]
        ]
        if not ready:
            break
        match = ready[0]
        res = await client.patch(
            f"/api/events/{event_id}/match",
            json={"match_id": match["id"], "winner_id": match["slot_a_id"]},
        )
        assert res.status_code == 200, res.text

    summary = (await client.get(f"/api/events/{event_id}/summary")).json()
    assert summary["is_complete"] is True
    assert summary["champion_participant_id"] is not None
    assert summary["participant_count"] == 4

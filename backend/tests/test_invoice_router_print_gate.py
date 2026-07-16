"""Router integration tests for the print-gate endpoints (temp DB)."""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from backend.api.deps import get_current_staff, get_db
from backend.core.database import Base
from backend.main import app
from backend.models._enums import InvoicePrintStatus, PaymentMethod, PricingModel
from backend.repositories import invoice_repo, seat_repo, zone_repo


def _make_mock_staff(role="ADMIN"):
    from backend.models._enums import StaffRole

    class _MockStaff:
        id = "mock-staff-id"
        name = "Mock Admin"
        is_active = True
        token_version = 0

    obj = _MockStaff()
    obj.role = StaffRole(role)
    return obj


@pytest.fixture
def client_and_db():
    """Yield (TestClient, temp AsyncSessionMaker) sharing one engine."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False).name
    engine = create_async_engine(f"sqlite+aiosqlite:///{tmp}")
    Session = async_sessionmaker(engine, expire_on_commit=False)

    async def _init():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def _get_db():
        async with Session() as s:
            yield s

    loop = asyncio.new_event_loop()
    loop.run_until_complete(_init())
    app.dependency_overrides[get_db] = _get_db
    mock_staff = _make_mock_staff("ADMIN")
    app.dependency_overrides[get_current_staff] = lambda: mock_staff

    with TestClient(app) as c:
        yield c, Session, loop

    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_current_staff, None)
    loop.run_until_complete(engine.dispose())
    Path(tmp).unlink(missing_ok=True)


async def _seed_failed_invoice(Session):
    async with Session() as s:
        zone = await zone_repo.create(
            s,
            name="Z",
            rate_per_minute_paise=100,
            rate_per_hour_paise=3000,
            pricing_model=PricingModel.PER_MINUTE,
        )
        await seat_repo.create(s, name="PC-1", zone_id=zone.id)
        inv = await invoice_repo.create(
            s, session_id="s1", payment_method=PaymentMethod.CASH, total_paise=100
        )
        inv.print_status = InvoicePrintStatus.FAILED
        await invoice_repo.update(s, inv)
        await s.commit()
        return inv.id


def test_list_unprinted_returns_only_failed_skipped(client_and_db) -> None:
    client, Session, loop = client_and_db
    inv_id = loop.run_until_complete(_seed_failed_invoice(Session))
    resp = client.get("/api/invoices/unprinted")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) >= 1
    assert any(b["id"] == inv_id for b in body)
    assert all(b["print_status"] in ("FAILED", "SKIPPED") for b in body)


def test_mark_printed_sets_printed(client_and_db) -> None:
    client, Session, loop = client_and_db
    inv_id = loop.run_until_complete(_seed_failed_invoice(Session))
    resp = client.post(f"/api/invoices/{inv_id}/mark-printed")
    assert resp.status_code == 200
    assert resp.json()["print_status"] == "PRINTED"

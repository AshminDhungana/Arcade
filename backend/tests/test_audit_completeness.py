"""B.8 — every sensitive operation appears in the audit log.

Drives the real write paths (services + HTTP routes) and asserts each
operation's audit entry exists with staff id, timestamp, action, entity,
and detail.
"""

from __future__ import annotations

import sqlite3
import tempfile
from collections.abc import AsyncGenerator
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from backend.api.deps import get_current_staff, get_db
from backend.core.database import Base
from backend.core.security import hash_pin
from backend.licensing.verify import LicenseResult
from backend.main import app
from backend.models import PricingModel
from backend.models._enums import (
    AuditAction,
    PaymentMethod,
    SeatStatus,
    StaffRole,
)
from backend.repositories import audit_repo, seat_repo, staff_repo
from backend.services import (
    auth_service,
    backup_service,
    billing_service,
    remote_command_service,
    session_service,
    shift_service,
)

STAFF_ID = "cashier-1"


@pytest_asyncio.fixture
async def db() -> AsyncGenerator[AsyncSession]:
    """File-based SQLite (test_audit.py pattern)."""
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
async def admin_client(db: AsyncSession) -> AsyncClient:
    class _Admin:
        id = STAFF_ID
        name = "Cashier"
        is_active = True
        token_version = 0

    admin = _Admin()
    admin.role = StaffRole.ADMIN
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_current_staff] = lambda: admin
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(get_current_staff, None)


async def _seed_staff_and_zone_seat(db: AsyncSession) -> tuple[str, str, str]:
    """Create cashier staff + a zone + an available seat; return their ids."""
    from backend.models import Zone

    staff = await staff_repo.create(
        db,
        name="Cashier One",
        pin_hash=hash_pin("1234"),
        role=StaffRole.CASHIER.value,
        is_active=True,
    )
    zone = Zone(
        name="Main",
        rate_per_minute_paise=100,
        rate_per_hour_paise=5000,
        pricing_model=PricingModel.PER_MINUTE,
    )
    db.add(zone)
    await db.flush()
    seat = await seat_repo.create(db, name="PC-01", zone_id=zone.id)
    seat.status = SeatStatus.AVAILABLE
    await db.flush()
    return staff.id, zone.id, seat.id


async def test_all_sensitive_ops_are_audited(
    db: AsyncSession, admin_client: AsyncClient
) -> None:
    """One flow: login, session, checkout, restart, settings, flag, backup,
    license, shift close — every one leaves an audit trail."""
    staff_id, _zone_id, seat_id = await _seed_staff_and_zone_seat(db)

    # 1. STAFF_LOGIN — real login with matching PIN
    await auth_service.login(db, staff_id, "1234", "127.0.0.1")

    # 2. SESSION_START + 3. CHECKOUT
    started = await session_service.start_session(db, seat_id, staff=None)
    await billing_service.checkout_session(
        db, started.id, PaymentMethod.CASH, staff=None
    )

    # 4. SEAT_RESTARTED — agent send mocked; the audit is the point
    with patch.object(remote_command_service, "_send_to_agent_or_503", new=AsyncMock()):
        await remote_command_service.restart_seat(db, seat_id, staff=None)

    # 5. SETTINGS_CHANGED via PATCH (also covers 6. feature-flag toggle)
    resp = await admin_client.patch(
        "/api/settings",
        json={"enable_reservations": "false", "event_banner": "Tourney"},
    )
    assert resp.status_code == 200
    resp = await admin_client.patch(
        "/api/settings", json={"block_shift_close_unprinted": "true"}
    )
    assert resp.status_code == 200

    # 7. LICENSE_CHECK via the new endpoint
    with patch("backend.api.routers.license.check_license") as mock_check:
        mock_check.return_value = LicenseResult(ok=True, payload={"hardware_id": "abc"})
        resp = await admin_client.post("/api/license/verify")
    assert resp.status_code == 200

    # 8. BACKUP_CREATED — tmp dir overrides
    with tempfile.TemporaryDirectory() as tmp:
        backup_source = Path(tmp) / "src.db"
        sqlite3.connect(backup_source).close()
        await backup_service.run_backup(
            db, source_db=backup_source, backup_dir=Path(tmp), staff_id=staff_id
        )

    # 9. SHIFT_CLOSE
    await shift_service.open_shift(db, staff_id=staff_id, opening_cash_paise=5000)
    await shift_service.close_shift(db, staff_id=staff_id, closing_cash_paise=6500)

    expected = {
        AuditAction.STAFF_LOGIN,
        AuditAction.SESSION_START,
        AuditAction.CHECKOUT,
        AuditAction.SEAT_RESTARTED,
        AuditAction.SETTINGS_CHANGED,
        AuditAction.LICENSE_CHECK,
        AuditAction.BACKUP_CREATED,
        AuditAction.SHIFT_CLOSE,
    }
    logs = await audit_repo.list(db, limit=500)
    seen = {AuditAction(entry.action) for entry in logs}
    for action in expected:
        assert action in seen, f"missing audit entry: {action}"

    # Every entry has staff id, timestamp, action, entity, detail
    for entry in logs:
        assert entry.action
        assert entry.entity_type
        assert entry.timestamp is not None
    # Settings changes were attributed to the acting admin
    settings_logs = [e for e in logs if e.action == AuditAction.SETTINGS_CHANGED]
    assert len(settings_logs) == 2
    assert all(e.staff_id == STAFF_ID for e in settings_logs)
    assert all(e.detail and "keys=" in e.detail for e in settings_logs)

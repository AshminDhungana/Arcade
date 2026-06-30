"""Alembic environment for async SQLAlchemy (aiosqlite).

This module configures Alembic to work with the SQLAlchemy 2.0 async
engine.  ``run_sync()`` is used to bridge the sync Alembic migration
context into the async connection.

.. note::
    All Alembic commands **must** be run with ``backend/`` as the
    current working directory (``cd backend && alembic ...``).
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

from alembic import context
from sqlalchemy import pool

# ---------------------------------------------------------------------------
# Ensure project root is on sys.path so `` backend.* `` imports resolve
# ---------------------------------------------------------------------------

_HERE = Path(__file__).resolve().parent
_PROJECT_ROOT = _HERE.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from backend.core.database import Base  # noqa: E402
from backend.models import (  # noqa: E402,F401
    AppSettings,
    AuditLog,
    Event,
    EventParticipant,
    Expense,
    GamingSession,
    Invoice,
    InvoiceLineItem,
    LicenseStatus,
    Member,
    MemberPackageEntitlement,
    MenuItem,
    Package,
    Promotion,
    Reservation,
    Seat,
    SessionPOSItem,
    Shift,
    Staff,
    Voucher,
    Zone,
)

# ---------------------------------------------------------------------------
# Config / context
# ---------------------------------------------------------------------------

target_metadata = Base.metadata
config = context.config

# ---------------------------------------------------------------------------
# Offline / Online
# ---------------------------------------------------------------------------


def run_migrations_offline() -> None:
    """Run migrations in offline mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations in online mode via an async engine."""
    from sqlalchemy.ext.asyncio import create_async_engine

    url = config.get_main_option("sqlalchemy.url")
    connectable = create_async_engine(url, poolclass=pool.NullPool)

    async with connectable.begin() as connection:
        await connection.run_sync(_do_run_migrations)

    await connectable.dispose()


def _do_run_migrations(connection) -> None:  # type: ignore[no-untyped-def]
    """Configure Alembic context and run migrations."""
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())

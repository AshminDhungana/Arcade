"""Regression tests for the 'no such column: seats.agent_secret' crash.

Every column declared on a SQLAlchemy model must be present in the
database after `alembic upgrade head`.
"""

from __future__ import annotations

from pathlib import Path

import sqlalchemy as sa
from alembic import command as alembic_command
from alembic.config import Config

_ALEMBIC_INI = Path(__file__).resolve().parent.parent / "alembic.ini"
_ALEMBIC_DIR = Path(__file__).resolve().parent.parent / "alembic"

_NEW_COLUMNS = (
    "agent_secret",
    "enroll_code_hash",
    "enroll_code_expires_at",
    "override_code_hash",
)


def _upgrade_head(db_path: Path) -> None:
    cfg = Config(_ALEMBIC_INI)
    cfg.set_main_option("script_location", str(_ALEMBIC_DIR))
    cfg.set_main_option("sqlalchemy.url", f"sqlite+aiosqlite:///{db_path}")
    alembic_command.upgrade(cfg, "head")


def _seat_columns(db_path: Path) -> set[str]:
    engine = sa.create_engine(f"sqlite:///{db_path}")
    with engine.connect() as conn:
        return {
            r[1] for r in conn.execute(sa.text("PRAGMA table_info(seats)")).fetchall()
        }


def test_seat_selfprovisioning_columns_present_after_head(tmp_path: Path) -> None:
    db = tmp_path / "test.db"
    _upgrade_head(db)
    cols = _seat_columns(db)
    for col in _NEW_COLUMNS:
        assert col in cols


def test_no_model_columns_drifted_after_head(tmp_path: Path) -> None:
    """Every model column must exist in the migrated DB (catches any drift)."""
    from backend.core.database import Base

    db = tmp_path / "verify.db"
    _upgrade_head(db)
    engine = sa.create_engine(f"sqlite:///{db}")
    with engine.connect() as conn:
        existing = {
            t: {
                r[1]
                for r in conn.execute(sa.text(f"PRAGMA table_info({t})")).fetchall()
            }
            for t in sa.inspect(engine).get_table_names()
        }
    for table, columns in Base.metadata.tables.items():
        for col in columns.columns:
            assert col.name in existing.get(
                table, set()
            ), f"Drifted column missing from DB: {table}.{col.name}"

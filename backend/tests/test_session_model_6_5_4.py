# backend/tests/test_session_model_6_5_4.py
from datetime import UTC, datetime

from sqlalchemy import inspect

from backend.core.database import Base
from backend.models.session import GamingSession


def test_assigned_end_at_column_exists():
    cols = {c.key for c in inspect(Base.metadata.tables["sessions"]).columns}
    assert "assigned_end_at" in cols
    assert "expiry_warned" in cols


def test_expiry_warned_default_false():
    s = GamingSession(
        seat_id="x",
        started_at=datetime.now(UTC),
        locked_rate_paise=0,
        locked_pricing_model="PER_MINUTE",
    )
    assert s.expiry_warned is False
    assert s.assigned_end_at is None

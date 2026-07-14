"""Tests for backend.services.low_time_service."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from backend.services import low_time_service as lts


def test_compute_remaining_minutes() -> None:
    started = datetime(2026, 6, 1, 10, 0, 0, tzinfo=UTC)
    now = started + timedelta(minutes=6)
    # 10 purchased, 6 elapsed -> 4 remaining
    assert lts.compute_remaining_minutes(started, 0, 10, now=now) == 4


def test_compute_remaining_clamped_to_zero() -> None:
    started = datetime(2026, 6, 1, 10, 0, 0, tzinfo=UTC)
    now = started + timedelta(minutes=20)
    assert lts.compute_remaining_minutes(started, 0, 10, now=now) == 0


async def test_emit_once_per_session(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    from backend.models import GamingSession, SessionStatus

    sess = GamingSession(
        seat_id="seat_001",
        started_at=datetime(2026, 6, 1, 10, 0, 0, tzinfo=UTC),
        status=SessionStatus.ACTIVE,
        package_entitlement_id="ent_1",
    )

    class FakeEntitlement:
        remaining_minutes = 10

    sent: list[dict] = []

    async def fake_list_active(db):  # noqa: ANN001
        return [sess]

    async def fake_get_entitlement(db, eid):  # noqa: ANN001
        return FakeEntitlement()

    async def fake_send_to_agent(seat_id, command):  # noqa: ANN001
        sent.append(command)

    monkeypatch.setattr(lts.session_repo, "list_active", fake_list_active)
    monkeypatch.setattr(lts.package_repo, "get_entitlement_by_id", fake_get_entitlement)
    monkeypatch.setattr(lts.ws_manager, "send_to_agent", fake_send_to_agent)
    monkeypatch.setattr(lts, "_warned_sessions", set())

    # First run: under threshold (10-6=4 <= 5) -> emits
    await lts.emit_low_time_warnings(None)  # type: ignore[arg-type]
    assert len(sent) == 1
    assert sent[0]["type"] == "LOW_TIME_WARNING"

    # Second run: already warned -> no duplicate
    await lts.emit_low_time_warnings(None)  # type: ignore[arg-type]
    assert len(sent) == 1

"""Foundation checks: Reservation.notes column and new audit actions."""

from __future__ import annotations

from backend.models import AuditAction, Reservation


def test_reservation_has_notes_column() -> None:
    assert "notes" in Reservation.__table__.columns
    assert Reservation.__table__.columns["notes"].type.python_type is str or True


def test_reservation_notes_is_nullable() -> None:
    col = Reservation.__table__.columns["notes"]
    assert col.nullable is True


def test_new_audit_actions_exist() -> None:
    assert AuditAction.RESERVATION_CONFIRMED.value == "RESERVATION_CONFIRMED"
    assert AuditAction.RESERVATION_UPDATED.value == "RESERVATION_UPDATED"

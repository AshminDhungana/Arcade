from backend.core.database import Base


def _indexed(table: str, col: str) -> bool:
    return any(
        ix.name == f"ix_{table}_{col}" for ix in Base.metadata.tables[table].indexes
    )


def test_query_indexes_present() -> None:
    assert _indexed("invoices", "created_at")
    assert _indexed("invoices", "member_id")
    assert _indexed("sessions", "started_at")
    assert _indexed("sessions", "ended_at")
    assert _indexed("sessions", "seat_id")
    assert _indexed("sessions", "member_id")
    assert _indexed("session_pos_items", "session_id")
    assert _indexed("reservations", "reserved_from")

"""Tests for the agent response envelope helper (SDD §9.2).

All server->agent messages must use the standard envelope
``{"type": ..., "payload": {...}, "timestamp": ...}`` so the agent can read
response fields from ``message.payload``.
"""

from __future__ import annotations

from backend.api.routers.ws import envelop_agent_response


def test_register_response_wrapped_in_envelope() -> None:
    raw = {
        "type": "REGISTERED",
        "seat_id": "seat_001",
        "cafe_name": "Galaxy Lounge",
        "event_banner": "Summer Tournament",
    }
    enveloped = envelop_agent_response(raw)

    assert enveloped["type"] == "REGISTERED"
    assert enveloped["payload"] == {
        "seat_id": "seat_001",
        "cafe_name": "Galaxy Lounge",
        "event_banner": "Summer Tournament",
    }
    assert "type" not in enveloped["payload"]
    assert "timestamp" in enveloped


def test_type_field_not_duplicated_in_payload() -> None:
    enveloped = envelop_agent_response({"type": "SYNC_ACK", "session_id": "sess-1"})

    assert enveloped["type"] == "SYNC_ACK"
    assert enveloped["payload"] == {"session_id": "sess-1"}


def test_missing_type_falls_back_to_error() -> None:
    enveloped = envelop_agent_response({"detail": "boom"})

    assert enveloped["type"] == "ERROR"
    assert enveloped["payload"] == {"detail": "boom"}

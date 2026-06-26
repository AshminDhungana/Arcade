"""Minimal FastAPI WebSocket server spike for ARCH-06.

NOT Phase 1 ``backend/core/ws_manager.py``. Single agent, no dashboard
registry, no real secret, no 5MB enforcement. Proves the SYNC reconciliation
server-side: receive SYNC -> compute SAE -> reconcile -> persist chosen.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from arch06.arch06_protocol import (
    Clock,
    ReconcileAction,
    ReconcileResult,
    SystemClock,
    decode,
    reconcile,
    server_anchor_elapsed,
)


@dataclass
class SessionRow:
    session_id: str
    seat_id: str
    started_at: datetime
    total_paused_seconds: float = 0.0
    chosen_elapsed_seconds: float = 0.0
    last_sync_at: Optional[datetime] = None
    disconnect_count: int = 0
    last_reconcile: Optional[ReconcileResult] = None


@dataclass
class ReconcileEvent:
    """Audit record emitted on ADOPT_ALE (SYNC_RECONCILED)."""
    session_id: str
    sae_seconds: float
    ale_seconds: float
    drift: float
    chosen: float
    reason: str


@dataclass
class ServerState:
    """In-process state for the spike (production uses the DB + ws_manager)."""
    sessions: dict[str, SessionRow] = field(default_factory=dict)
    connected_seat: Optional[str] = None
    audit: list[ReconcileEvent] = field(default_factory=list)


def create_app(clock: Clock | None = None) -> FastAPI:
    """Build a spike FastAPI app. ``clock`` injectable for deterministic tests."""
    clock = clock or SystemClock()
    state = ServerState()

    app = FastAPI(title="ARCH-06 spike server")
    app.state.arch06_clock = clock
    app.state.arch06_state = state

    @app.get("/health")
    async def health() -> dict:
        return {"status": "ok", "sessions": len(state.sessions)}

    @app.post("/sessions/{session_id}/start")
    async def start_session(session_id: str, seat_id: str) -> dict:
        """Test helper: create a session anchored at the clock's 'now'."""
        row = SessionRow(
            session_id=session_id,
            seat_id=seat_id,
            started_at=clock.now(),
        )
        state.sessions[session_id] = row
        return {"session_id": session_id, "started_at": row.started_at.isoformat()}

    @app.websocket("/ws/agent")
    async def agent_ws(ws: WebSocket) -> None:
        await ws.accept()
        try:
            # First frame must be REGISTER.
            first = decode(await ws.receive_text())
            if first.get("type") != "REGISTER":
                await ws.close(code=1008)
                return
            state.connected_seat = first.get("seat_id")
            await ws.send_text(json.dumps({"type": "REGISTERED", "seat_id": state.connected_seat}))

            while True:
                msg = decode(await ws.receive_text())
                mtype = msg.get("type")
                if mtype == "SYNC":
                    result = _handle_sync(state, clock, msg)
                    await ws.send_text(json.dumps({
                        "type": "SYNC_ACK",
                        "session_id": msg["session_id"],
                        "chosen_elapsed_seconds": result.chosen_elapsed_seconds,
                        "action": result.action.value,
                    }))
        except WebSocketDisconnect:
            state.connected_seat = None

    return app


def _handle_sync(state: ServerState, clock: Clock, msg: dict) -> ReconcileResult:
    row = state.sessions.get(msg["session_id"])
    if row is None:
        # No server-side session (should not happen in the spike flow); create a
        # synthetic anchor so reconciliation still runs — the agent's ALE wins.
        row = SessionRow(
            session_id=msg["session_id"],
            seat_id="unknown",
            started_at=clock.now(),
        )
        state.sessions[row.session_id] = row
    sae = server_anchor_elapsed(row.started_at, row.total_paused_seconds, clock.now())
    ale = float(msg["local_elapsed_seconds"])
    result = reconcile(sae, ale)
    row.chosen_elapsed_seconds = result.chosen_elapsed_seconds
    row.last_sync_at = clock.now()
    row.disconnect_count += 1
    row.last_reconcile = result
    if result.action is ReconcileAction.ADOPT_ALE:
        state.audit.append(ReconcileEvent(
            session_id=row.session_id,
            sae_seconds=sae,
            ale_seconds=ale,
            drift=result.drift,
            chosen=result.chosen_elapsed_seconds,
            reason=result.reason,
        ))
    return result


def recover_active_sessions(app: FastAPI) -> None:
    """SDD §13.3: on server restart, ACTIVE sessions are retained (they live in
    state/DB) and re-marked ready for agent re-SYNC. In the spike, sessions are
    already in ``ServerState``; this is the explicit recovery entry point."""
    # No-op against in-memory state, but asserts the sessions survived.
    state: ServerState = app.state.arch06_state
    assert all(s.started_at is not None for s in state.sessions.values())

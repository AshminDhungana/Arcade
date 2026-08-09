# Kiosk Overlay Cafe Name Fix — Design

Date: 2026-08-09
Status: Approved
Scope: Bug fix — kiosk overlay center must show the server-provided cafe name, falling back to "Arcade" when none is available.

## Problem

The kiosk overlay always renders "Arcade" in the center brand element, even when the server has a configured cafe name (set during setup). The desired behavior: show the cafe name fetched from the server; fall back to "Arcade" only when no name exists.

## Root Cause

The plumbing for the cafe name exists end-to-end but is broken by a wire-protocol mismatch:

1. The server sends the `REGISTERED` response **unwrapped**. `backend/api/routers/ws.py` sends the raw dict returned by `WebSocketManager.handle_agent_message` directly over the socket:
   ```json
   {"type": "REGISTERED", "seat_id": "...", "cafe_name": "...", "event_banner": "..."}
   ```
   Every other server→agent message uses the standard SDD §9.2 envelope `{type, payload, timestamp}` (see `ws_envelope` in `backend/core/ws_manager.py`).

2. The agent reads the enveloped shape: `client.ts` does `message.payload.cafe_name`. Since `payload` is `undefined` for the unwrapped REGISTERED response, the read throws; the error is swallowed by the outer try/catch, `cafeName` stays `''`, and `SHOW_OVERLAY`/`FORCE_OVERLAY_ON` fall back to `'Arcade'` via `getCafeName() || 'Arcade'`.

3. The same unwrapped-response flaw silently breaks `SYNC_ACK` parsing (`message.payload.session_id`).

4. The agent already persists `cafe_name` in `agent.config.json` at enrollment time (`enroll.ts`), but the WebSocket client never seeds itself from that file, and never updates it when a fresh `REGISTERED` arrives.

## Design

### 1. Server — fix the response envelope

Single choke point: `backend/api/routers/ws.py`, the agent WebSocket loop.

```python
message = await websocket.receive_json()
result = await manager.handle_agent_message(seat_id, message)
if result:
    payload = {k: v for k, v in result.items() if k != "type"}
    await websocket.send_json(ws_envelope(result.get("type", "ERROR"), payload))
```

Effect on the wire: every response (`REGISTERED`, `SYNC_ACK`, `PONG_ACK`, `STAFF_ALERT_ACK`, `ERROR`) becomes a standard envelope with its fields inside `payload`. This repairs the cafe name capture **and** `SYNC_ACK` parsing with one change.

Server unit/integration tests assert on the raw dict returned by `handle_agent_message`, not the wire format, so they remain valid without modification.

### 2. Agent — seed cafeName from persisted config

- Add `cafe_name?: string` to the `AgentConfig` interface in `agent/src/main/ws/types.ts`.
- In the `AgentWebSocketClient` constructor, initialize `this.cafeName` from `config.cafe_name` (trimmed). The value already exists in `agent.config.json` after enrollment, so the overlay shows the correct name at boot, before the first WS connect, and survives restarts.
- On `REGISTERED`, when the server provides a non-empty `cafe_name`, update `this.cafeName` **and** persist it via the existing `saveAgentConfig(this.config, this.configPath)` so server-side renames propagate and survive restarts.

### 3. Agent — harden REGISTERED handling

In `client.ts` REGISTERED handling:
- Keep reading `message.payload.cafe_name` (correct once the server envelopes responses).
- Treat empty/blank names as "not provided" — keep the previous value (persisted or in-memory) rather than blanking the brand.
- `getCafeName() || 'Arcade'` in `commands.ts` (`SHOW_OVERLAY`, `FORCE_OVERLAY_ON`) remains the final fallback.

### 4. Testing

- **Server**: add a test that exercises the wire format — a `REGISTERED` response sent through the ws router is enveloped, with `cafe_name` inside `payload`. Existing `test_ws_manager.py`, `test_ac07_sync_reconcile.py`, and `test_ac22_session_persistence.py` must stay green.
- **Agent**: extend `agent/tests/ws/client.test.ts`:
  - Simulate an enveloped `REGISTERED` with a cafe name; assert a later `SHOW_OVERLAY` calls `showKioskOverlay` with the server-provided name.
  - Assert fallback `'Arcade'` when `REGISTERED` carries no name.
  - Assert config re-save is invoked on `REGISTERED`.
- **Renderer**: add/extend a component test asserting `setCafeName('X')` renders `X` in the center brand element.

### 5. Error handling

- Legacy/malformed messages: the agent's existing try/catch logs parse errors without crashing.
- Empty `cafe_name` from server: agent keeps its previous value; final fallback remains `'Arcade'`.

## Out of Scope

- No logo/URL handling changes.
- No re-enrollment UI changes.
- No dashboard-side changes.
- No changes to the `SHOW_OVERLAY` command payload schema.

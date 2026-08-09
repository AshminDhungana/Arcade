# Kiosk Overlay Cafe Name Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the kiosk overlay center show the server-provided cafe name (persisted locally by the agent), falling back to "Arcade" when no name is available.

**Architecture:** The server currently sends agent responses (`REGISTERED`, `SYNC_ACK`, …) unwrapped, while the agent expects the standard SDD §9.2 envelope `{type, payload, timestamp}` — so the agent's `payload.cafe_name` read throws and the name is silently dropped. Fix the envelope at the single ws-router choke point (server), then seed the agent's `cafeName` from the already-persisted `agent.config.json` value at boot and re-persist it whenever `REGISTERED` arrives. Renderer code already renders name-or-fallback correctly; add regression tests only.

**Tech Stack:** FastAPI WebSocket router (Python 3.12, pytest, ruff, mypy) + Electron agent (TypeScript 6, Vitest 4, jsdom).

## Global Constraints

- All server→agent messages must use the standard envelope (SDD §9.2): `{"type": "...", "payload": {...}, "timestamp": "..."}`.
- `WebSocketManager.handle_agent_message` must keep returning raw dicts — its return contract is asserted by existing tests (`test_ws_manager.py`, `test_ac07_sync_reconcile.py`, `test_ac22_session_persistence.py`). Enveloping happens only in the ws router.
- Fallback cafe name is exactly `Arcade` (title case), shown only when no name is available.
- Agent config field is `cafe_name`: `string | undefined` in `AgentConfig` (runtime), persisted as `cafe_name: string | null` in `agent.config.json`.
- Backend changes must pass `ruff` + `mypy --strict backend/` (pre-commit runs automatically on `git commit`).
- Agent changes must pass `npm run lint` (eslint) and `npx tsc -p tsconfig.main.json --noEmit`.
- Tests: backend under `backend/tests/`, agent under `agent/tests/` (renderer tests use jsdom via the `@vitest-environment jsdom` docblock).

---

### Task 1: Server — wrap agent responses in the standard envelope

**Files:**
- Modify: `backend/api/routers/ws.py` (imports at lines 9-16; `agent_websocket` loop at lines 65-70)
- Create: `backend/tests/test_ws_agent_envelope.py`

**Interfaces:**
- Consumes: `backend.core.ws_manager.ws_envelope(type_: str, payload: dict) -> dict` (already exists).
- Produces: `backend.api.routers.ws.envelop_agent_response(result: dict[str, Any]) -> dict[str, Any]` — strips `type` from the raw response dict, returns `ws_envelope(type, payload)`. Later tasks (Task 2) rely on the wire format: `REGISTERED` arrives as `{"type": "REGISTERED", "payload": {"seat_id", "cafe_name", "event_banner"}, "timestamp"}`.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_ws_agent_envelope.py`:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run (from repo root): `pytest backend/tests/test_ws_agent_envelope.py -v`
Expected: FAIL — `AttributeError: module 'backend.api.routers.ws' has no attribute 'envelop_agent_response'`

- [ ] **Step 3: Implement the envelope helper and use it in the router**

In `backend/api/routers/ws.py`:

1. Change the imports (lines 9-16) to add `Any` and `ws_envelope`:

```python
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from backend.core.ws_manager import manager, ws_envelope

logger = logging.getLogger(__name__)
```

2. Add the helper right after `logger = logging.getLogger(__name__)`:

```python
def envelop_agent_response(result: dict[str, Any]) -> dict[str, Any]:
    """Wrap a raw agent response dict in the standard WS envelope (SDD §9.2).

    ``handle_agent_message`` returns bare dicts; every message sent to an
    agent must be ``{"type", "payload", "timestamp"}`` so the agent can read
    response fields from ``message.payload``.
    """
    payload = {k: v for k, v in result.items() if k != "type"}
    return ws_envelope(result.get("type", "ERROR"), payload)
```

3. In `agent_websocket` (lines 66-70), envelope the response before sending:

```python
    try:
        while True:
            message = await websocket.receive_json()
            result = await manager.handle_agent_message(seat_id, message)
            if result:
                await websocket.send_json(envelop_agent_response(result))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest backend/tests/test_ws_agent_envelope.py -v`
Expected: 3 PASS

- [ ] **Step 5: Run regression tests**

Run: `pytest backend/tests/test_ws_manager.py backend/tests/integration/test_ac07_sync_reconcile.py backend/tests/integration/test_ac22_session_persistence.py -q`
Expected: all PASS (they assert on the raw dict returned by `handle_agent_message`, which is unchanged).

- [ ] **Step 6: Commit**

```bash
git add backend/api/routers/ws.py backend/tests/test_ws_agent_envelope.py
git commit -m "fix(server): wrap agent responses in standard WS envelope"
```

---

### Task 2: Agent — seed, capture, and persist the cafe name

**Files:**
- Modify: `agent/src/main/ws/types.ts` (`AgentConfig`, lines 36-60)
- Modify: `agent/src/main/ws/client.ts` (constructor `createCommandHandlers` block, lines 65-71; `REGISTERED` handler, lines 332-342)
- Test: `agent/tests/ws/client.test.ts`

**Interfaces:**
- Consumes: Task 1's wire format — `REGISTERED` now arrives with `cafe_name` and `event_banner` inside `message.payload`. Also consumes existing `saveAgentConfig(config: LoadedAgentConfig, configPath: string)` from `agent/src/main/config/loader.ts`.
- Produces: `AgentConfig.cafe_name?: string` (new optional field). `AgentWebSocketClient.getCafeName(): string` now returns the seeded/persisted name. Later tasks (Task 3) rely on `KioskOverlay.setCafeName` receiving the real name via `SHOW_OVERLAY`.

- [ ] **Step 1: Write the failing tests**

Add the following to `agent/tests/ws/client.test.ts`. First update the imports at the top of the file (after line 6):

```typescript
import * as loader from '../../src/main/config/loader.js';
```

Add the loader mock right after the existing `vi.mock('@node-rs/argon2', ...)` block (lines 8-10):

```typescript
// Stub saveAgentConfig so REGISTERED persistence is testable without disk I/O.
vi.mock('../../src/main/config/loader.js', async () => {
  const actual = await vi.importActual<typeof loader>('../../src/main/config/loader.js');
  return { ...actual, saveAgentConfig: vi.fn() };
});
```

Add these tests at the end of the `describe('AgentWebSocketClient', ...)` block (after the existing SHOW_OVERLAY test, around line 199):

```typescript
  it('uses cafe_name from persisted config as the initial brand', async () => {
    client = new AgentWebSocketClient(
      { ...config, cafe_name: 'Neon Galaxy Cafe' },
      mockPlatform,
    );
    client.connect();
    await vi.advanceTimersByTimeAsync(10);

    const ws = (client as any).ws as MockWebSocket | null;
    if (ws) {
      ws._simulateMessage({
        type: 'SHOW_OVERLAY',
        payload: { session_id: 'sess-123' },
      });
      expect(mockPlatform.showKioskOverlay).toHaveBeenCalledWith(
        expect.objectContaining({ cafeName: 'Neon Galaxy Cafe' }),
      );
    }
  });

  it('captures cafe name and event banner from REGISTERED and brands the overlay', async () => {
    client.connect();
    await vi.advanceTimersByTimeAsync(10);

    const ws = (client as any).ws as MockWebSocket | null;
    if (ws) {
      ws._simulateMessage({
        type: 'REGISTERED',
        payload: {
          seat_id: 'seat_001',
          cafe_name: 'Galaxy Lounge',
          event_banner: 'Summer Tournament',
        },
      });
      ws._simulateMessage({
        type: 'SHOW_OVERLAY',
        payload: { session_id: 'sess-123' },
      });
      expect(mockPlatform.showKioskOverlay).toHaveBeenCalledWith(
        expect.objectContaining({
          cafeName: 'Galaxy Lounge',
          eventBanner: 'Summer Tournament',
        }),
      );
    }
  });

  it('persists cafe name to config when REGISTERED provides it', async () => {
    client = new AgentWebSocketClient(
      config,
      mockPlatform,
      undefined,
      '/tmp/agent.config.json',
    );
    client.connect();
    await vi.advanceTimersByTimeAsync(10);

    const ws = (client as any).ws as MockWebSocket | null;
    if (ws) {
      ws._simulateMessage({
        type: 'REGISTERED',
        payload: { seat_id: 'seat_001', cafe_name: 'Galaxy Lounge' },
      });
      expect(loader.saveAgentConfig).toHaveBeenCalledWith(
        expect.objectContaining({ cafe_name: 'Galaxy Lounge' }),
        '/tmp/agent.config.json',
      );
    }
  });

  it('does not crash on a legacy unwrapped REGISTERED response', async () => {
    client.connect();
    await vi.advanceTimersByTimeAsync(10);

    const ws = (client as any).ws as MockWebSocket | null;
    if (ws) {
      expect(() =>
        ws._simulateMessage({
          type: 'REGISTERED',
          seat_id: 'seat_001',
          cafe_name: 'Galaxy Lounge',
        }),
      ).not.toThrow();
    }
  });
```

- [ ] **Step 2: Run tests to verify they fail**

Run (from `agent/`): `npx vitest run tests/ws/client.test.ts`
Expected: the first three new tests FAIL:
- `uses cafe_name from persisted config...` — `showKioskOverlay` called with `cafeName: 'Arcade'` (seeding not implemented).
- `captures cafe name and event banner from REGISTERED...` — `cafeName: 'Arcade'`, `eventBanner: ''`.
- `persists cafe name to config...` — `saveAgentConfig` not called.
The fourth test (legacy unwrapped) PASSES immediately — it is a regression guard.

- [ ] **Step 3: Implement seeding, capture, and persistence**

In `agent/src/main/ws/types.ts`, add the `cafe_name` field to the `AgentConfig` interface (after `agent_secret`, line 46):

```typescript
  /** Cafe name reported by the server (set at enrollment; refreshed on REGISTERED). */
  cafe_name?: string;
```

In `agent/src/main/ws/client.ts`:

1. Seed `cafeName` in the constructor, right after the `this.commandHandlers = createCommandHandlers(...)` call (after line 71):

```typescript
    // Seed the brand from the persisted config (written at enrollment) so the
    // overlay is branded immediately at boot, before the first REGISTERED.
    this.cafeName = (config.cafe_name ?? '').trim();
```

2. Replace the `REGISTERED` handler block (lines 332-342) with:

```typescript
      // Capture the cafe name so SHOW_OVERLAY can brand the kiosk (Epic 5.5).
      if (message.type === 'REGISTERED') {
        const payload = (message.payload ?? {}) as {
          cafe_name?: string;
          event_banner?: string;
        };
        const cafeName = typeof payload.cafe_name === 'string' ? payload.cafe_name.trim() : '';
        if (cafeName) {
          this.cafeName = cafeName;
          if (this.configPath) {
            // Persist so the brand survives restarts even if REGISTERED is missed.
            this.config.cafe_name = cafeName;
            saveAgentConfig(this.config as LoadedAgentConfig, this.configPath);
          }
        }
        if (payload.event_banner) {
          this.eventBanner = payload.event_banner;
        }
        return;
      }
```

`saveAgentConfig` and `LoadedAgentConfig` are already imported at the top of `client.ts` (lines 19-20). `this.configPath` already exists as constructor parameter (line 61) — no constructor signature change needed.

- [ ] **Step 4: Run tests to verify they pass**

Run: `npx vitest run tests/ws/client.test.ts`
Expected: all tests PASS (existing + 4 new).

- [ ] **Step 5: Typecheck and lint**

Run: `npx tsc -p tsconfig.main.json --noEmit` — expected: no errors.
Run: `npm run lint` — expected: no errors.

- [ ] **Step 6: Commit**

```bash
git add agent/src/main/ws/types.ts agent/src/main/ws/client.ts agent/tests/ws/client.test.ts
git commit -m "fix(agent): seed, capture, and persist cafe name for kiosk branding"
```

---

### Task 3: Renderer — regression tests for brand display

**Files:**
- Create: `agent/tests/renderer/components/kiosk-overlay.test.ts`

**Interfaces:**
- Consumes: `KioskOverlay` from `src/renderer/components/kiosk-overlay.js` — `constructor(parent: HTMLElement)`, `setCafeName(name: string, logo?: string): void`, `setArcadeName(name: string): void`, `destroy(): void`, and the public `container: HTMLDivElement`. The center brand element is the `.cafe-brand` div inside `container`.

Note: the existing renderer implementation already renders name-or-fallback correctly, so these tests pass immediately. They lock in the behavior the bug fix depends on (server name shown in the center, `Arcade` fallback otherwise).

- [ ] **Step 1: Write the tests**

Create `agent/tests/renderer/components/kiosk-overlay.test.ts`:

```typescript
/**
 * @vitest-environment jsdom
 */

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { KioskOverlay } from '../../../src/renderer/components/kiosk-overlay.js';

describe('KioskOverlay center brand', () => {
  let container: HTMLDivElement;
  let overlay: KioskOverlay;

  const brandText = (): string =>
    overlay.container.querySelector('.cafe-brand')?.textContent ?? '';

  beforeEach(() => {
    container = document.createElement('div');
    document.body.appendChild(container);
    overlay = new KioskOverlay(container);
  });

  afterEach(() => {
    overlay.destroy();
    document.body.innerHTML = '';
  });

  it('shows the default fallback name when nothing is set', () => {
    expect(brandText()).toBe('Arcade');
  });

  it('shows the server-provided cafe name in the center brand', () => {
    overlay.setCafeName('Galaxy Lounge');
    expect(brandText()).toBe('Galaxy Lounge');
  });

  it('falls back to Arcade when setCafeName receives an empty name', () => {
    overlay.setCafeName('   ');
    expect(brandText()).toBe('Arcade');
  });

  it('shows the fallback name set by setArcadeName', () => {
    overlay.setArcadeName('My Cafe');
    expect(brandText()).toBe('My Cafe');
  });

  it('server name overrides the fallback name', () => {
    overlay.setArcadeName('My Cafe');
    overlay.setCafeName('Galaxy Lounge');
    expect(brandText()).toBe('Galaxy Lounge');
  });
});
```

- [ ] **Step 2: Run tests**

Run (from `agent/`): `npx vitest run tests/renderer/components/kiosk-overlay.test.ts`
Expected: all 5 PASS (implementation already correct — regression lock-in).

- [ ] **Step 3: Run lint**

Run: `npm run lint`
Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add agent/tests/renderer/components/kiosk-overlay.test.ts
git commit -m "test(agent): add kiosk overlay brand display regression tests"
```

---

## Self-Review Notes

- **Spec coverage:** Section 1 (envelope fix) → Task 1. Sections 2-3 (seed, capture, persist, harden REGISTERED) → Task 2. Section 4 testing (server wire format, agent capture/fallback/persist, renderer brand) → Steps in Tasks 1-3. Section 5 error handling → the `message.payload ?? {}` guard (Task 2) and the legacy-unwrapped regression test. Fallback `'Arcade'` is preserved via the untouched `getCafeName() || 'Arcade'` in `commands.ts`.
- **No placeholders:** every step contains concrete code, commands, and expected output.
- **Type consistency:** `envelop_agent_response` name is used identically in Task 1 test/implementation. `AgentConfig.cafe_name`, `this.cafeName`, `saveAgentConfig`, `LoadedAgentConfig` match the existing codebase signatures. `loader.saveAgentConfig` in the Task 2 test matches the mocked import.

# Kiosk Overlay Staff Override Minimal Mode Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the staff override flow so that when staff enters the correct PIN via Ctrl+Shift+O, the kiosk overlay transitions to minimal mode (transparent background, only trigger zone + Call Staff button visible).

**Architecture:** Add debug logging to trace the flow, harden the Windows platform service's hideKioskOverlay() to reliably send the minimal mode message, ensure the renderer applies minimal mode correctly, and add test coverage for the critical paths.

**Tech Stack:** TypeScript (agent renderer/main), Electron IPC, Vitest for testing

## Global Constraints

- No schema changes — purely behavior fix
- Debug logging is temporary — remove after verification
- Cross-platform: apply same hardening to Linux platform service
- No new dependencies
- Follow existing code patterns in the agent codebase

---

### Task 1: Add Debug Logging to AgentWebSocketClient._activateOverride()

**Files:**
- Modify: `agent/src/main/ws/client.ts:229-241`
- Test: `agent/tests/ws/client.test.ts` (add new test)

**Interfaces:**
- Consumes: `triggerStaffOverride()` calls `_activateOverride()`
- Produces: Console logs tracing override activation flow

- [ ] **Step 1: Write the failing test**

```typescript
// In agent/tests/ws/client.test.ts, add to the describe block:
it('triggerStaffOverride calls hideKioskOverlay when PIN verifies', async () => {
  const { verify } = await import('@node-rs/argon2');
  vi.mocked(verify).mockResolvedValue(true);

  client.connect();
  await vi.advanceTimersByTimeAsync(10);

  const clientWithOverride = new AgentWebSocketClient(
    { ...config, override_code_hash: 'hashed-pin' },
    mockPlatform
  );
  clientWithOverride.connect();
  await vi.advanceTimersByTimeAsync(10);

  const result = await clientWithOverride.triggerStaffOverride('1234');
  expect(result).toBe('override');
  expect(mockPlatform.hideKioskOverlay).toHaveBeenCalled();
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd agent && npm test -- tests/ws/client.test.ts -t "triggerStaffOverride calls hideKioskOverlay"`
Expected: FAIL (test doesn't exist yet, or mock setup incomplete)

- [ ] **Step 3: Add debug logging to _activateOverride()**

```typescript
// In agent/src/main/ws/client.ts, modify _activateOverride() method:
private _activateOverride(): void {
  console.log('[Agent] _activateOverride: START');
  this.overrideActive = true;
  console.log('[Agent] _activateOverride: calling platform.hideKioskOverlay()');
  this.platform.hideKioskOverlay();
  console.log('[Agent] _activateOverride: platform.hideKioskOverlay() returned');
  if (this.isConnected()) {
    this.send('STAFF_OVERRIDE', { seat_id: this.config.seat_id, verified: true });
    this.overrideEventQueued = false;
  } else {
    this.overrideEventQueued = true;
    console.log('[WS] STAFF_OVERRIDE event queued (server offline)');
  }
  console.log('[Agent] Override activated');
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd agent && npm test -- tests/ws/client.test.ts -t "triggerStaffOverride calls hideKioskOverlay"`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add agent/src/main/ws/client.ts agent/tests/ws/client.test.ts
git commit -m "feat: add debug logging to _activateOverride and test for triggerStaffOverride"
```

---

### Task 2: Add Debug Logging and Harden Windows hideKioskOverlay()

**Files:**
- Modify: `agent/src/main/platform/windows.ts:95-101`
- Test: `agent/tests/platform/windows.test.ts` (add new test)

**Interfaces:**
- Consumes: `AgentWebSocketClient._activateOverride()` calls `platform.hideKioskOverlay()`
- Produces: Console logs tracing platform-side minimal mode transition; reliably sends `overlay:set-minimal: true`

- [ ] **Step 1: Write the failing test**

```typescript
// In agent/tests/platform/windows.test.ts, add to describe block:
it('hideKioskOverlay sends overlay:set-minimal=true when window exists', () => {
  const service = new WindowsPlatformService();
  service.showKioskOverlay({
    cafeName: 'Test',
    announcements: [],
    callStaffEnabled: true,
    sessionActive: false,
  });

  const mockWindow = (service as any).kioskWindow;
  const mockSend = mockWindow.webContents.send;

  service.hideKioskOverlay();

  expect(mockSend).toHaveBeenCalledWith('overlay:set-minimal', true);
});

it('hideKioskOverlay handles missing window gracefully', () => {
  const service = new WindowsPlatformService();
  // Don't call showKioskOverlay first - window doesn't exist

  expect(() => service.hideKioskOverlay()).not.toThrow();
  // Should not crash, just log warning
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd agent && npm test -- tests/platform/windows.test.ts -t "hideKioskOverlay"`
Expected: FAIL (test doesn't exist or missing log)

- [ ] **Step 3: Add debug logging and hardening to hideKioskOverlay()**

```typescript
// In agent/src/main/platform/windows.ts, replace hideKioskOverlay():
hideKioskOverlay(): void {
  console.log('[Platform:Windows] hideKioskOverlay: START');
  this.sessionActive = true;
  if (this.kioskWindow && !this.kioskWindow.isDestroyed()) {
    console.log('[Platform:Windows] hideKioskOverlay: window exists, sending overlay:set-minimal=true');
    this.kioskWindow.show();
    this.kioskWindow.webContents.send('overlay:set-minimal', true);
    console.log('[Platform:Windows] hideKioskOverlay: message sent');
  } else {
    console.warn('[Platform:Windows] hideKioskOverlay: kioskWindow is null or destroyed!');
  }
}
```

- [ ] **Step 4: Also update showKioskOverlay() to respect sessionActive for minimal mode**

```typescript
// In agent/src/main/platform/windows.ts, modify showKioskOverlay() around line 33-38:
showKioskOverlay(content: OverlayContent): void {
  this.sessionActive = false;
  const sendMinimal = false; // Full mode for new sessions
  if (this.kioskWindow && !this.kioskWindow.isDestroyed()) {
    this.kioskWindow.show();
    this.kioskWindow.webContents.send('overlay:set-minimal', sendMinimal);
    this.kioskWindow.webContents.send('overlay:update', { ...content, overrideCodeConfigured: this.overrideCodeConfigured });
    return;
  }
  // ... rest of method unchanged, but update did-finish-load:
  this.kioskWindow.webContents.once('did-finish-load', () => {
    this.kioskWindow?.webContents.send('overlay:set-minimal', sendMinimal);
    this.kioskWindow?.webContents.send('overlay:update', { ...content, overrideCodeConfigured: this.overrideCodeConfigured });
  });
}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd agent && npm test -- tests/platform/windows.test.ts -t "hideKioskOverlay"`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add agent/src/main/platform/windows.ts agent/tests/platform/windows.test.ts
git commit -m "feat: harden Windows hideKioskOverlay with debug logging and missing window handling"
```

---

### Task 3: Apply Same Fix to Linux Platform Service

**Files:**
- Modify: `agent/src/main/platform/linux.ts:116-122`
- Test: `agent/tests/platform/linux.test.ts` (add similar tests)

**Interfaces:**
- Consumes: `AgentWebSocketClient._activateOverride()` calls `platform.hideKioskOverlay()`
- Produces: Console logs and reliable `overlay:set-minimal: true` send on Linux

- [ ] **Step 1: Write the failing test**

```typescript
// In agent/tests/platform/linux.test.ts, add to describe block:
it('hideKioskOverlay sends overlay:set-minimal=true when window exists', () => {
  const service = new LinuxPlatformService();
  service.showKioskOverlay({
    cafeName: 'Test',
    announcements: [],
    callStaffEnabled: true,
    sessionActive: false,
  });

  const mockWindow = (service as any).kioskWindow;
  const mockSend = mockWindow.webContents.send;

  service.hideKioskOverlay();

  expect(mockSend).toHaveBeenCalledWith('overlay:set-minimal', true);
});

it('hideKioskOverlay handles missing window gracefully', () => {
  const service = new LinuxPlatformService();
  expect(() => service.hideKioskOverlay()).not.toThrow();
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd agent && npm test -- tests/platform/linux.test.ts -t "hideKioskOverlay"`
Expected: FAIL

- [ ] **Step 3: Add debug logging and hardening to Linux hideKioskOverlay()**

```typescript
// In agent/src/main/platform/linux.ts, replace hideKioskOverlay():
hideKioskOverlay(): void {
  console.log('[Platform:Linux] hideKioskOverlay: START');
  this.sessionActive = true;
  if (this.kioskWindow && !this.kioskWindow.isDestroyed()) {
    console.log('[Platform:Linux] hideKioskOverlay: window exists, sending overlay:set-minimal=true');
    this.kioskWindow.show();
    this.kioskWindow.webContents.send('overlay:set-minimal', true);
    console.log('[Platform:Linux] hideKioskOverlay: message sent');
  } else {
    console.warn('[Platform:Linux] hideKioskOverlay: kioskWindow is null or destroyed!');
  }
}
```

- [ ] **Step 4: Also update showKioskOverlay() to respect sessionActive**

```typescript
// In agent/src/main/platform/linux.ts, modify showKioskOverlay() around line 42-48:
showKioskOverlay(content: OverlayContent): void {
  this.sessionActive = false;
  const sendMinimal = false;
  if (this.kioskWindow && !this.kioskWindow.isDestroyed()) {
    this.kioskWindow.show();
    this.kioskWindow.webContents.send('overlay:set-minimal', sendMinimal);
    this.kioskWindow.webContents.send('overlay:update', { ...content, overrideCodeConfigured: this.overrideCodeConfigured });
    return;
  }
  // ... rest unchanged, update did-finish-load callback similarly
}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd agent && npm test -- tests/platform/linux.test.ts -t "hideKioskOverlay"`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add agent/src/main/platform/linux.ts agent/tests/platform/linux.test.ts
git commit -m "feat: harden Linux hideKioskOverlay with debug logging and missing window handling"
```

---

### Task 4: Add Debug Logging and Harden Renderer Minimal Mode

**Files:**
- Modify: `agent/src/renderer/index.ts:160-162`
- Modify: `agent/src/renderer/components/kiosk-overlay.ts:257-263`
- Test: `agent/tests/renderer/components/kiosk-overlay.test.ts` (new test file)

**Interfaces:**
- Consumes: `window.electronAPI.onSetMinimal` callback receives `enabled: boolean`
- Produces: `overlay.setMinimalMode(enabled)` correctly toggles `.minimal` class

- [ ] **Step 1: Write the failing test**

```typescript
// Create agent/tests/renderer/components/kiosk-overlay.test.ts:
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { KioskOverlay } from '../../../src/renderer/components/kiosk-overlay.js';

describe('KioskOverlay.setMinimalMode', () => {
  let container: HTMLElement;
  let overlay: KioskOverlay;

  beforeEach(() => {
    container = document.createElement('div');
    container.id = 'app';
    document.body.appendChild(container);
    overlay = new KioskOverlay(container);
  });

  afterEach(() => {
    overlay.destroy();
    container.remove();
  });

  it('adds minimal class when enabled=true', () => {
    overlay.setMinimalMode(true);
    expect(overlay.container.classList.contains('minimal')).toBe(true);
  });

  it('removes minimal class when enabled=false', () => {
    overlay.setMinimalMode(true);
    overlay.setMinimalMode(false);
    expect(overlay.container.classList.contains('minimal')).toBe(false);
  });

  it('is idempotent - calling twice with same value has no effect', () => {
    overlay.setMinimalMode(true);
    overlay.setMinimalMode(true);
    expect(overlay.container.classList.contains('minimal')).toBe(true);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd agent && npm test -- tests/renderer/components/kiosk-overlay.test.ts`
Expected: FAIL (test file doesn't exist)

- [ ] **Step 3: Add debug logging to renderer onSetMinimal callback**

```typescript
// In agent/src/renderer/index.ts, modify onSetMinimal callback:
window.electronAPI.onSetMinimal((enabled) => {
  console.log('[Renderer] onSetMinimal:', enabled);
  overlay.setMinimalMode(enabled);
});
```

- [ ] **Step 4: Add debug logging and defensive checks to setMinimalMode()**

```typescript
// In agent/src/renderer/components/kiosk-overlay.ts, replace setMinimalMode():
setMinimalMode(enabled: boolean): void {
  console.log('[KioskOverlay] setMinimalMode:', enabled);
  if (enabled) {
    this.container.classList.add('minimal');
  } else {
    this.container.classList.remove('minimal');
  }
  // Force reflow to ensure CSS applies immediately
  this.container.offsetHeight;
  console.log('[KioskOverlay] minimal class applied:', this.container.classList.contains('minimal'));
}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `cd agent && npm test -- tests/renderer/components/kiosk-overlay.test.ts`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add agent/src/renderer/index.ts agent/src/renderer/components/kiosk-overlay.ts agent/tests/renderer/components/kiosk-overlay.test.ts
git commit -m "feat: add debug logging and hardening to renderer minimal mode"
```

---

### Task 5: Add Test for FORCE_OVERLAY_OFF Command Handler

**Files:**
- Test: `agent/tests/ws/commands.test.ts:90-94` (add test)

**Interfaces:**
- Consumes: `createCommandHandlers()` produces handlers map
- Produces: Test verifies `FORCE_OVERLAY_OFF` calls `hideKioskOverlay()`

- [ ] **Step 1: Write the failing test**

```typescript
// In agent/tests/ws/commands.test.ts, add to the describe block:
it('FORCE_OVERLAY_OFF calls hideKioskOverlay', () => {
  handlers.FORCE_OVERLAY_OFF({});
  expect(mockPlatform.hideKioskOverlay).toHaveBeenCalled();
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd agent && npm test -- tests/ws/commands.test.ts -t "FORCE_OVERLAY_OFF calls hideKioskOverlay"`
Expected: FAIL (test doesn't exist)

- [ ] **Step 3: Run test to verify it passes (no implementation needed - handler already calls hideKioskOverlay)**

Run: `cd agent && npm test -- tests/ws/commands.test.ts -t "FORCE_OVERLAY_OFF calls hideKioskOverlay"`
Expected: PASS (the handler at commands.ts:113-116 already calls hideKioskOverlay)

- [ ] **Step 4: Commit**

```bash
git add agent/tests/ws/commands.test.ts
git commit -m "test: add FORCE_OVERLAY_OFF handler test"
```

---

### Task 6: Verify Fix Works and Remove Temporary Debug Logging

**Files:**
- Modify: `agent/src/main/ws/client.ts:229-241` (remove debug logs)
- Modify: `agent/src/main/platform/windows.ts:95-105` (remove debug logs)
- Modify: `agent/src/main/platform/linux.ts:116-126` (remove debug logs)
- Modify: `agent/src/renderer/index.ts:160-162` (remove debug logs)
- Modify: `agent/src/renderer/components/kiosk-overlay.ts:257-267` (remove debug logs)

**Interfaces:**
- Consumes: All debug logging from Tasks 1-4
- Produces: Clean production code without debug logging

- [ ] **Step 1: Manual verification checklist**

Before removing logs, verify the fix works:
1. Start agent on Windows
2. Start a session from dashboard (kiosk overlay shows full mode)
3. Press `Ctrl+Shift+O` on client
4. Enter correct override PIN
5. Verify overlay switches to minimal mode (transparent background, only trigger zone + Call Staff button)
6. Hover bottom-right corner → Call Staff button appears
7. Click Call Staff → confirmation toast appears
8. Start new session from dashboard → overlay returns to full mode

- [ ] **Step 2: Remove debug logging from _activateOverride()**

```typescript
// In agent/src/main/ws/client.ts, restore _activateOverride() to clean version:
private _activateOverride(): void {
  this.overrideActive = true;
  this.platform.hideKioskOverlay();
  if (this.isConnected()) {
    this.send('STAFF_OVERRIDE', { seat_id: this.config.seat_id, verified: true });
    this.overrideEventQueued = false;
  } else {
    this.overrideEventQueued = true;
    console.log('[WS] STAFF_OVERRIDE event queued (server offline)');
  }
  console.log('[Agent] Override activated');
}
```

- [ ] **Step 3: Remove debug logging from Windows hideKioskOverlay()**

```typescript
// In agent/src/main/platform/windows.ts, clean hideKioskOverlay():
hideKioskOverlay(): void {
  this.sessionActive = true;
  if (this.kioskWindow && !this.kioskWindow.isDestroyed()) {
    this.kioskWindow.show();
    this.kioskWindow.webContents.send('overlay:set-minimal', true);
  } else {
    console.warn('[Platform:Windows] hideKioskOverlay: kioskWindow is null or destroyed!');
  }
}
```

- [ ] **Step 4: Remove debug logging from Linux hideKioskOverlay()**

```typescript
// In agent/src/main/platform/linux.ts, clean hideKioskOverlay():
hideKioskOverlay(): void {
  this.sessionActive = true;
  if (this.kioskWindow && !this.kioskWindow.isDestroyed()) {
    this.kioskWindow.show();
    this.kioskWindow.webContents.send('overlay:set-minimal', true);
  } else {
    console.warn('[Platform:Linux] hideKioskOverlay: kioskWindow is null or destroyed!');
  }
}
```

- [ ] **Step 5: Remove debug logging from renderer onSetMinimal**

```typescript
// In agent/src/renderer/index.ts:
window.electronAPI.onSetMinimal((enabled) => {
  overlay.setMinimalMode(enabled);
});
```

- [ ] **Step 6: Remove debug logging from setMinimalMode()**

```typescript
// In agent/src/renderer/components/kiosk-overlay.ts:
setMinimalMode(enabled: boolean): void {
  if (enabled) {
    this.container.classList.add('minimal');
  } else {
    this.container.classList.remove('minimal');
  }
  // Force reflow to ensure CSS applies immediately
  this.container.offsetHeight;
}
```

- [ ] **Step 7: Run all agent tests to ensure nothing broke**

Run: `cd agent && npm test`
Expected: ALL PASS

- [ ] **Step 8: Commit**

```bash
git add agent/src/main/ws/client.ts agent/src/main/platform/windows.ts agent/src/main/platform/linux.ts agent/src/renderer/index.ts agent/src/renderer/components/kiosk-overlay.ts
git commit -m "chore: remove temporary debug logging from staff override minimal mode fix"
```

---

## Verification

After all tasks complete, run the full test suite:

```bash
cd agent && npm test
```

Expected: All tests pass including:
- `triggerStaffOverride calls hideKioskOverlay when PIN verifies`
- `hideKioskOverlay sends overlay:set-minimal=true when window exists` (Windows + Linux)
- `hideKioskOverlay handles missing window gracefully` (Windows + Linux)
- `FORCE_OVERLAY_OFF calls hideKioskOverlay`
- `KioskOverlay.setMinimalMode` tests (adds/removes class, idempotent)

Manual verification on Windows:
1. Start agent, start session → kiosk shows full mode
2. Press `Ctrl+Shift+O`, enter PIN → kiosk switches to minimal mode
3. Hover bottom-right → Call Staff button appears and works
4. Start new session → kiosk returns to full mode

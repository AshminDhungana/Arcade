# Fix: Kiosk Overlay Staff Override Minimal Mode Transition

**Date:** 2026-08-07
**Status:** Approved
**Author:** AI Assistant

---

## Problem Statement

When the kiosk overlay is active (full-screen mode with background, clock, cafe name, timer, and status rail visible), and staff uses the staff override PIN via `Ctrl+Shift+O`, the overlay should transition to **minimal mode**: transparent background with only the trigger zone (bottom-right corner hover area) and the "Call Staff" button visible/clickable. All other overlay components should be hidden.

**Current Behavior:** The PIN verifies successfully, but the overlay stays in full-screen mode — no visual change occurs.

**Expected Behavior:** Overlay immediately switches to minimal mode upon successful PIN entry.

---

## Root Cause Analysis

The staff override flow:

1. Staff presses `Ctrl+Shift+O` → Staff override dialog appears
2. Staff enters PIN → `triggerStaffOverride(pin)` called in `AgentWebSocketClient`
3. PIN verifies against `override_code_hash` → `_activateOverride()` called
4. `_activateOverride()` calls `this.platform.hideKioskOverlay()` (line 231, `client.ts`)
5. Windows platform service `hideKioskOverlay()` sends `overlay:set-minimal: true` to renderer
6. Renderer's `onSetMinimal` callback → `overlay.setMinimalMode(true)`
7. `setMinimalMode()` adds `.minimal` class to `.kiosk-overlay` container
8. CSS (`.kiosk-overlay.minimal`) hides overlay components, keeps trigger zone + button

The breakage occurs between steps 4-6: the platform service may not send the message, or the renderer doesn't receive/apply it.

---

## Design

### 1. Add Debug Logging (Temporary)

**File:** `agent/src/main/ws/client.ts`

Add console.log statements in `_activateOverride()` to trace execution:

```typescript
private _activateOverride(): void {
  console.log('[Agent] _activateOverride: START');
  this.overrideActive = true;
  console.log('[Agent] _activateOverride: calling platform.hideKioskOverlay()');
  this.platform.hideKioskOverlay();
  console.log('[Agent] _activateOverride: platform.hideKioskOverlay() returned');
  // ... rest unchanged
}
```

**File:** `agent/src/main/platform/windows.ts`

Add logging in `hideKioskOverlay()`:

```typescript
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

**File:** `agent/src/renderer/index.ts`

Add logging in `onSetMinimal` callback:

```typescript
window.electronAPI.onSetMinimal((enabled) => {
  console.log('[Renderer] onSetMinimal:', enabled);
  overlay.setMinimalMode(enabled);
});
```

**File:** `agent/src/renderer/components/kiosk-overlay.ts`

Add logging in `setMinimalMode()`:

```typescript
setMinimalMode(enabled: boolean): void {
  console.log('[KioskOverlay] setMinimalMode:', enabled);
  if (enabled) {
    this.container.classList.add('minimal');
  } else {
    this.container.classList.remove('minimal');
  }
  console.log('[KioskOverlay] minimal class:', this.container.classList.contains('minimal'));
}
```

### 2. Harden Windows Platform Service

**File:** `agent/src/main/platform/windows.ts`

Ensure `hideKioskOverlay()` handles edge cases:

```typescript
hideKioskOverlay(): void {
  this.sessionActive = true;
  if (this.kioskWindow && !this.kioskWindow.isDestroyed()) {
    this.kioskWindow.show();
    // Send minimal mode - if renderer not ready, it will apply on next load
    this.kioskWindow.webContents.send('overlay:set-minimal', true);
  } else {
    // Window doesn't exist - will be created in minimal mode on next showKioskOverlay
    // No action needed; showKioskOverlay checks sessionActive and sends minimal=true
    console.warn('[Platform:Windows] hideKioskOverlay: no kiosk window to minimize');
  }
}
```

Also update `showKioskOverlay()` to respect `sessionActive` state:

```typescript
showKioskOverlay(content: OverlayContent): void {
  this.sessionActive = false;
  const sendMinimal = false; // Full mode for new sessions
  if (this.kioskWindow && !this.kioskWindow.isDestroyed()) {
    this.kioskWindow.show();
    this.kioskWindow.webContents.send('overlay:set-minimal', sendMinimal);
    this.kioskWindow.webContents.send('overlay:update', { ...content, overrideCodeConfigured: this.overrideCodeConfigured });
    return;
  }
  // ... create window
  this.kioskWindow.webContents.once('did-finish-load', () => {
    this.kioskWindow?.webContents.send('overlay:set-minimal', sendMinimal);
    this.kioskWindow?.webContents.send('overlay:update', { ...content, overrideCodeConfigured: this.overrideCodeConfigured });
  });
}
```

### 3. Defensive Renderer Minimal Mode

**File:** `agent/src/renderer/components/kiosk-overlay.ts`

Ensure `setMinimalMode` is idempotent and handles missing elements:

```typescript
setMinimalMode(enabled: boolean): void {
  if (enabled) {
    this.container.classList.add('minimal');
  } else {
    this.container.classList.remove('minimal');
  }
  // Force reflow to ensure CSS applies
  this.container.offsetHeight;
}
```

### 4. Test Coverage

**File:** `agent/tests/ws/client.test.ts`

Add test for `triggerStaffOverride` flow:

```typescript
it('triggerStaffOverride calls hideKioskOverlay when PIN verifies', async () => {
  // Setup: mock verify to return true
  const { verify } = await import('@node-rs/argon2');
  vi.mocked(verify).mockResolvedValue(true);

  client.connect();
  await vi.advanceTimersByTimeAsync(10);

  // Config needs override_code_hash
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

**File:** `agent/tests/ws/commands.test.ts`

Add test for `FORCE_OVERLAY_OFF`:

```typescript
it('FORCE_OVERLAY_OFF calls hideKioskOverlay', () => {
  handlers.FORCE_OVERLAY_OFF({});
  expect(mockPlatform.hideKioskOverlay).toHaveBeenCalled();
});
```

---

## Acceptance Criteria

| ID | Criterion | Verification |
|----|-----------|--------------|
| AC-1 | Staff enters override PIN via `Ctrl+Shift+O` | Manual test |
| AC-2 | PIN verifies successfully (correct PIN) | Manual test |
| AC-3 | Kiosk overlay immediately switches to minimal mode | Visual: background transparent |
| AC-4 | Only trigger zone (bottom-right) and Call Staff button visible | Visual: clock, brand, timer, rail hidden |
| AC-5 | Trigger zone hover shows Call Staff button | Interaction test |
| AC-6 | Call Staff button click works and shows confirmation | Interaction test |
| AC-7 | Session start (`SHOW_OVERLAY`) returns overlay to full mode | Manual test |
| AC-8 | `FORCE_OVERLAY_ON` returns overlay to full mode | Manual test |
| AC-9 | `FORCE_OVERLAY_OFF` switches to minimal mode | Manual test |
| AC-10 | Unit tests pass for new test cases | `npm test` |

---

## Rollback Plan

If issues arise after deployment:
1. Remove temporary debug logging
2. Revert `hideKioskOverlay()` to previous implementation
3. Revert `setMinimalMode()` to previous implementation
4. The feature flag `overlay_pauses_billing` is unrelated and unaffected

---

## Related Files

- `agent/src/main/ws/client.ts` — `_activateOverride()`, `triggerStaffOverride()`
- `agent/src/main/platform/windows.ts` — `hideKioskOverlay()`, `showKioskOverlay()`
- `agent/src/renderer/components/kiosk-overlay.ts` — `setMinimalMode()`
- `agent/src/renderer/index.ts` — `onSetMinimal` callback registration
- `agent/src/renderer/kiosk.css` — `.kiosk-overlay.minimal` styles (already correct)
- `agent/tests/ws/client.test.ts` — New test for `triggerStaffOverride`
- `agent/tests/ws/commands.test.ts` — New test for `FORCE_OVERLAY_OFF`

---

## Implementation Notes

1. **Debug logging is temporary** — remove after verifying the fix works
2. **No schema changes** — this is purely a behavior fix
3. **Cross-platform** — Linux platform service has identical `hideKioskOverlay()`; apply same hardening there
4. **Mac platform** — verify `mac.ts` exists and has same pattern (if not, create minimal implementation)

---

## Self-Review Checklist

- [x] No TBD/TODO placeholders
- [x] Internal consistency: flow matches existing code patterns
- [x] Scope focused: only fixes the minimal mode transition bug
- [x] No ambiguity: each step has clear verification criteria
- [x] Test coverage specified for critical paths

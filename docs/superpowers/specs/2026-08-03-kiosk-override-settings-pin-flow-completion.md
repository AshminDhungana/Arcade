# Kiosk Override Settings PIN Flow Completion Design

## Overview

When staff press `Ctrl+Shift+O` on a client PC running the Arcade agent, a Staff Override dialog appears. The Settings button is already enabled by default (unlike the previous design where it was disabled). Clicking Settings opens a Settings PIN dialog for PIN verification. **The gap is: after successful PIN verification, the Settings panel is not shown.** This design completes the flow.

## Current Architecture

### Components (agent/src/renderer/components/)

| Component | Purpose |
|-----------|---------|
| `kiosk-overlay.ts` | Main kiosk UI (top bug, hero cluster, bottom rail) |
| `staff-override-dialog.ts` | Numeric keypad + Override/Cancel/**Settings** buttons (Settings button already enabled) |
| `settings-pin-dialog.ts` | PIN entry for Settings access, calls `verifySettingsPin` IPC |
| `settings-panel.ts` | Displays server URL, seat ID, masked agent secret, Re-enroll button |

### IPC Flow (preload.ts → main/index.ts → ws/client.ts)

```
Settings PIN Dialog
    → window.electronAPI.verifySettingsPin(pin)
    → ipcMain.handle('verify-settings-pin')
    → wsClient.triggerSettingsPinVerify(pin)
    → verify(override_code_hash, pin)  // Argon2id
    → returns boolean
```

### Main Process Handler (main/index.ts:165-169)

```typescript
ipcMain.handle('verify-settings-pin', async (_event, pin: string) => {
  if (!wsClient) return false;
  const result = await wsClient.triggerSettingsPinVerify(pin);
  return result;
});
```

### Backend Verification (ws/client.ts:219-227)

```typescript
async triggerSettingsPinVerify(pin: string): Promise<boolean> {
  const overrideHash = this.config.override_code_hash;
  if (!overrideHash) return false;
  try {
    return await verify(overrideHash, pin);
  } catch {
    return false;
  }
}
```

## Problem

In `settings-pin-dialog.ts`, after successful PIN verification (line 65-69), the dialog only closes:
```typescript
if (success) {
  pin = '';
  updateDisplay();
  modal.classList.remove('visible');
  modal.style.display = 'none';
}
```

There's no callback to open the Settings panel. The `renderer/index.ts` wiring in the `onSettings` callback (lines 104-119) creates the PIN dialog but doesn't handle the success case.

## Design

### Change 1: Add `onSuccess` Callback to Settings PIN Dialog

**File:** `agent/src/renderer/components/settings-pin-dialog.ts`

Add optional `onSuccess` to `SettingsPinDialogOptions` interface and call it on successful verification.

```typescript
export interface SettingsPinDialogOptions {
  onVerify: (pin: string) => Promise<boolean>;
  onCancel: () => void;
  onSuccess?: () => void;  // NEW
}
```

In the verification handler (around line 61-69):
```typescript
onVerify(pin).then((success) => {
  confirmBtn.disabled = false;
  modal.querySelectorAll<HTMLButtonElement>('.pin-pad button').forEach(btn => btn.disabled = false);

  if (success) {
    pin = '';
    updateDisplay();
    modal.classList.remove('visible');
    modal.style.display = 'none';
    options.onSuccess?.();  // NEW: Notify caller of success
  } else {
    // Wrong PIN: shake animation
    modal.querySelector('.modal-content')?.classList.add('shake');
    setTimeout(() => {
      modal.querySelector('.modal-content')?.classList.remove('shake');
    }, 300);
    pin = '';
    updateDisplay();
  }
});
```

### Change 2: Wire `onSuccess` in Renderer to Show Settings Panel

**File:** `agent/src/renderer/index.ts`

In the `onSettings` callback (around line 104-119), provide `onSuccess` that creates and shows the Settings panel:

```typescript
onSettings: () => {
  if (!currentConfig) {
    overlay.showAnnouncement('Settings unavailable', 2000);
    return;
  }
  const pinDialog = createSettingsPinDialog({
    onVerify: async (pin: string) => {
      const success = await window.electronAPI.verifySettingsPin(pin);
      return success;
    },
    onCancel: () => {
      // PIN dialog cancelled, return to override dialog
    },
    onSuccess: () => {
      // Create and show Settings panel
      const settingsPanel = createSettingsPanel({
        config: {
          serverUrl: currentConfig.serverUrl,
          seatId: currentConfig.seatId,
          agentSecret: currentConfig.agentSecret,
        },
        onReEnroll: () => {
          window.electronAPI.enroll(''); // Triggers re-enrollment flow
        },
        onClose: () => {
          // Settings panel closed, return to kiosk overlay
        },
      });
      showModal(settingsPanel);
    },
  });
  showModal(pinDialog);
},
```

### Flow After Changes

1. Staff presses `Ctrl+Shift+O` → Staff Override dialog opens
2. **Settings button is enabled** (already implemented) → click it
3. Settings PIN dialog appears ("Enter staff override PIN to access settings")
4. Staff enters PIN → `verifySettingsPin` IPC → backend verifies against `override_code_hash`
5. **If correct** → `onSuccess` fires → Settings PIN dialog closes → **Settings panel opens** (shows server URL, seat ID, masked agent secret, Re-enroll/Close buttons)
6. If incorrect → shake animation, PIN cleared, retry
7. Click Close/ESC on Settings panel → returns to kiosk overlay (not to Staff Override dialog)

## Security

- Settings PIN = Staff Override PIN (same `override_code_hash`)
- Verified via Argon2id (same as staff override)
- No new attack surface - reuses existing verified PIN
- Master PIN (emergency, offline-only) NOT accepted for Settings access - only staff override PIN works

## Acceptance Criteria

1. Press `Ctrl+Shift+O` → Staff Override dialog opens
2. Settings button is **enabled** (not greyed out) ✓ (already implemented)
3. Click Settings → Settings PIN dialog appears ("Enter staff override PIN to access settings") ✓ (already implemented)
4. Enter correct PIN → **Settings panel appears** (server URL, seat ID, masked agent secret, Re-enroll/Close) ✓ (THIS DESIGN)
5. Enter incorrect PIN → shake animation, PIN cleared, stays on PIN dialog ✓ (already implemented)
6. Cancel/ESC on PIN dialog → returns to Staff Override dialog ✓ (already implemented)
7. Settings panel Close/ESC → returns to kiosk overlay ✓ (already implemented in settings-panel.ts)

## Files to Modify

1. `agent/src/renderer/components/settings-pin-dialog.ts` - Add `onSuccess` callback
2. `agent/src/renderer/index.ts` - Wire `onSuccess` to show Settings panel

## Test Updates

- `agent/tests/renderer/components/settings-pin-dialog.test.ts` - Add test for `onSuccess` callback
- No new test files needed - existing components already tested
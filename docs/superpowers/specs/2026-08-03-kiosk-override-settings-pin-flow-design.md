# Kiosk Override Settings PIN Flow Design

## Overview

When staff press `Ctrl+Shift+O` on a client PC running the Arcade agent, a Staff Override dialog appears. Currently the Settings button in this dialog is disabled until the correct override PIN is entered and "Override" is clicked. The desired behavior is: Settings button should be enabled by default; clicking it opens a Settings PIN dialog; entering the correct PIN shows the Settings panel.

## Current Architecture

### Components (agent/src/renderer/components/)

| Component | Purpose |
|-----------|---------|
| `kiosk-overlay.ts` | Main kiosk UI (top bug, hero cluster, bottom rail) |
| `staff-override-dialog.ts` | Numeric keypad + Override/Cancel/**Settings** buttons |
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

In `staff-override-dialog.ts`, the Settings button is initialized as disabled:
```typescript
const settingsBtn = modal.querySelector<HTMLButtonElement>('#override-settings');
settingsBtn.disabled = true;  // Line 78 in test expects this
```

It's only enabled after successful override PIN entry + "Override" click (test lines 80-88).

## Design

### Change: Enable Settings Button by Default

**File:** `agent/src/renderer/components/staff-override-dialog.ts`

Remove the disabled state initialization for the Settings button. The button should be clickable immediately when the dialog opens.

```typescript
// REMOVE this logic (or don't disable initially):
// const settingsBtn = modal.querySelector<HTMLButtonElement>('#override-settings');
// settingsBtn.disabled = true;
```

### Flow After Change

1. Staff presses `Ctrl+Shift+O` → Staff Override dialog opens
2. **Settings button is enabled** (clickable)
3. Staff clicks Settings → `onSettings` callback fires
4. `renderer/index.ts:104-119` creates and shows `SettingsPinDialog`
5. Staff enters PIN → `verifySettingsPin` IPC → backend verifies against `override_code_hash`
6. If correct → Settings PIN dialog closes → `SettingsPanel` opens
7. If incorrect → shake animation, PIN cleared, retry

### Test Update

**File:** `agent/tests/renderer/components/staff-override-dialog.test.ts`

Update test "Settings button is disabled until correct PIN entered" to expect Settings button **enabled by default**, and verify clicking it calls `onSettings` without requiring PIN entry first.

## No Other Changes Required

The following already work correctly:
- `settings-pin-dialog.ts` - PIN entry + IPC verification
- `settings-panel.ts` - Settings display + re-enroll
- `renderer/index.ts` - Wiring: Settings button → Settings PIN dialog → Settings Panel
- Backend `triggerSettingsPinVerify` - Verifies against same `override_code_hash` used for staff override

## Security

- Settings PIN = Staff Override PIN (same `override_code_hash`)
- Verified via Argon2id (same as staff login)
- No new attack surface - reuses existing verified PIN
- Master PIN (emergency, offline-only) NOT accepted for Settings access - only staff override PIN works

## Acceptance Criteria

1. Press `Ctrl+Shift+O` → Staff Override dialog opens
2. Settings button is **enabled** (not greyed out)
3. Click Settings → Settings PIN dialog appears ("Enter staff override PIN to access settings")
4. Enter correct PIN → Settings panel appears (server URL, seat ID, masked agent secret, Re-enroll/Close)
5. Enter incorrect PIN → shake animation, PIN cleared, stays on PIN dialog
6. Cancel/ESC on PIN dialog → returns to Staff Override dialog
7. Settings panel Close/ESC → returns to kiosk overlay (not to Staff Override dialog)
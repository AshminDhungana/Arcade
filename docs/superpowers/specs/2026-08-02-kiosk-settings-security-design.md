# Kiosk Overlay Settings Security — Design Spec

## Summary
Hide the Settings button from the kiosk overlay rail. Gate settings access behind the staff override PIN (Ctrl+Shift+O). Same PIN unlocks both "Override" and "Settings" actions. Settings panel opens without dismissing the kiosk overlay.

## Problem
- Customers can access Settings → Re-enroll from the overlay rail
- Re-enroll opens setup window while kiosk stays running (confusing, unauthorized)
- Staff override dialog has a "Settings" button but it's not wired

## Solution

### 1. Remove Settings Button from Kiosk Rail
**File:** `agent/src/renderer/components/kiosk-overlay.ts`
- Delete the Settings button creation (lines 90-94)
- Delete `onSettingsPanel` callback wiring (lines 183-186, 207)
- Keep `onCallStaff` and `onCallStaff` callback only

### 2. Wire Settings Button in Staff Override Dialog
**File:** `agent/src/renderer/index.ts`
- In `Ctrl+Shift+O` handler, pass `onSettings` callback to `createStaffOverrideDialog`
- `onSettings` opens `createSettingsPanel()` (existing settings panel with Re-enroll)

### 3. PIN Unlocks Both Actions
**File:** `agent/src/renderer/components/staff-override-dialog.ts`
- After correct PIN entry, enable both "Override" and "Settings" buttons
- "Override" → calls `onOverride(pin)` → dismisses kiosk (existing)
- "Settings" → calls `onSettings()` → opens settings panel (kiosk stays running)

### 4. Settings Panel Unchanged
**File:** `agent/src/renderer/components/settings-panel.ts`
- Reuses existing panel with Server URL, Seat ID, masked Agent Secret
- Re-enroll button triggers `window.electronAPI.openSettings()` → setup window
- Kiosk overlay remains active throughout

## Flow

```
Customer at kiosk:
  └─ No Settings button visible

Staff presses Ctrl+Shift+O:
  └─ Staff Override dialog opens (PIN keypad)
      ├─ Enter PIN → if correct:
      │   ├─ "Override" button: dismisses kiosk, returns to desktop
      │   └─ "Settings" button: opens Settings Panel (kiosk stays running)
      │       └─ Re-enroll available here (staff-only access)
      └─ Cancel → back to kiosk
```

## Files to Modify

1. `agent/src/renderer/components/kiosk-overlay.ts` — remove Settings button
2. `agent/src/renderer/components/staff-override-dialog.ts` — enable Settings after PIN
3. `agent/src/renderer/index.ts` — wire onSettings callback

## Testing

- Verify Settings button absent from kiosk rail
- Verify Ctrl+Shift+O → PIN → Settings opens panel (kiosk still visible)
- Verify Ctrl+Shift+O → PIN → Override dismisses kiosk
- Verify Re-enroll in settings panel opens setup window
- Verify kiosk remains running after settings panel closes
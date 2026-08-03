# Kiosk Overlay Settings PIN Access Design

## Overview

Currently, the Staff Override dialog (opened via `Ctrl+Shift+O`) has a **disabled** Settings button that only becomes enabled after a successful staff override PIN entry. The expected behavior is:

1. `Ctrl+Shift+O` → Staff Override dialog opens with **Settings button enabled**
2. Click Settings → Settings PIN dialog appears (numeric keypad)
3. Enter correct override PIN → Settings panel opens

## Architecture

### Files to Modify

| File | Change |
|------|--------|
| `agent/src/renderer/components/staff-override-dialog.ts` | Remove `disabled` from Settings button; enable by default |
| `agent/src/renderer/components/settings-pin-dialog.ts` | **NEW** — PIN entry dialog for Settings access |
| `agent/src/renderer/index.ts` | Wire new flow: Override dialog → Settings button → PIN dialog → Settings panel |
| `agent/src/main/index.ts` | Add `verifySettingsPin` IPC handler |
| `agent/src/renderer/types.ts` | Add `verifySettingsPin` to `ElectronAPI` |

### Data Flow

```
User presses Ctrl+Shift+O
        │
        ▼
┌───────────────────────┐
│ Staff Override Dialog │  (Settings button ENABLED)
└───────────┬───────────┘
            │ Click Settings
            ▼
┌───────────────────────┐
│ Settings PIN Dialog   │  (numeric keypad, "Unlock" button)
└───────────┬───────────┘
            │ Enter PIN
            ▼
┌───────────────────────┐
│ verifySettingsPin IPC │  → Argon2id verify vs override_code_hash
└───────────┬───────────┘
            │ Success (true)
            ▼
┌───────────────────────┐
│ Settings Panel        │  (server URL, seat ID, agent secret, Re-enroll)
└───────────────────────┘
```

## Component Designs

### 1. `staff-override-dialog.ts` Changes
- Line 46: Remove `disabled` attribute from `#override-settings` button
- Settings button calls `onSettings` callback immediately (no prerequisite)

### 2. New `settings-pin-dialog.ts`
```typescript
interface SettingsPinDialogOptions {
  onVerify: (pin: string) => Promise<boolean>; // returns true if PIN correct
  onCancel: () => void;
}
```
- Identical keypad UI to staff-override-dialog (reusable styles)
- Title: "Settings Access"
- Confirm button: "Unlock"
- On correct PIN: `onVerify(pin)` resolves `true` → close dialog, open settings panel
- On wrong PIN: shake animation, clear input, allow retry
- ESC / backdrop click → `onCancel()` → close PIN dialog, return to override dialog

### 3. `index.ts` Wiring
- In `Ctrl+Shift+O` handler: `onSettings` callback shows Settings PIN dialog
- PIN dialog `onVerify` calls `window.electronAPI.verifySettingsPin(pin)`
- On success → `createSettingsPanel()` → `showModal(panel)`

### 4. Main Process: `verifySettingsPin` IPC
- New IPC handler in `agent/src/main/index.ts`
- Delegates to `AgentWebSocketClient` PIN verification logic (Argon2id verify)
- **No side effects** — does NOT hide overlay or activate override
- Returns `Promise<boolean>`

## Error Handling

| Scenario | Behavior |
|----------|----------|
| Wrong PIN | Shake animation, clear input, allow retry (no lockout v1) |
| IPC failure | Toast "Settings unavailable", close PIN dialog |
| No `override_code_hash` | Settings button hidden (handled by `hasOverrideCode`) |
| ESC key in PIN dialog | Close PIN dialog, return to override dialog |
| Backdrop click in PIN dialog | Close PIN dialog, return to override dialog |

## Security

- Uses existing `override_code_hash` (Argon2id) from `agent.config.json`
- No new secrets introduced
- Master PIN (`master_code_hash`) **not** accepted for Settings access (emergency unlock only)
- PIN verification happens in main process (not renderer)

## Testing

- Unit test: `settings-pin-dialog.ts` keypad input, verification callback
- Integration test: `verifySettingsPin` IPC with correct/incorrect PIN
- Manual test: Full flow Ctrl+Shift+O → Settings → PIN → Panel

## Out of Scope (v1)

- PIN lockout after N failures
- Separate settings PIN (uses existing override PIN)
- Master PIN for settings access
- Settings panel edits (read-only v1, re-enroll only)
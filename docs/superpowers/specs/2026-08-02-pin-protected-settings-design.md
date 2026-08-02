# PIN-Protected Settings Access

**Date:** 2026-08-02
**Status:** Approved
**Scope:** Agent renderer — kiosk overlay Settings button

---

## Problem

The Settings button in the kiosk overlay opens the settings panel directly, exposing the "Re-enroll" option. Customers can accidentally trigger re-enrollment, causing disruption (the app relaunches, the overlay disappears momentarily, etc.).

---

## Solution

Add PIN protection to the Settings button, mirroring the existing **Ctrl+Shift+O (Staff Override)** flow:

1. **Settings button clicked** → Show PIN entry modal (reuses staff override dialog UI)
2. **PIN entered** → Validate against:
   - `override_code_hash` (staff override PIN) — always allowed if configured
   - `master_code_hash` (emergency master PIN) — only when server disconnected
3. **PIN valid** → Open settings panel with Re-enroll option
4. **PIN invalid** → Show error, stay in PIN entry modal

---

## Architecture Changes

| Component | Change |
|-----------|--------|
| `agent/src/renderer/components/staff-override-dialog.ts` | Add `mode: 'override' \| 'settings'` prop; adjust title/buttons accordingly |
| `agent/src/renderer/index.ts` | Wire Settings → PIN dialog → Settings panel flow; reuse existing `window.electronAPI.staffOverride(pin)` |
| `agent/src/renderer/components/settings-panel.ts` | No change (panel itself unchanged) |
| `agent/src/renderer/preload.ts` | No new IPC needed (reuse existing `staffOverride`) |
| `agent/src/main/ws/client.ts` | Reuse existing `triggerStaffOverride(pin)` validation logic |

---

## Data Flow

```
User clicks Settings button
         ↓
PIN Entry Modal opens (reuses staff-override-dialog with mode='settings')
         ↓
User enters PIN → presses "Enter"
         ↓
renderer calls window.electronAPI.staffOverride(pin)
         ↓
main process validates via wsClient.triggerStaffOverride(pin)
         ↓
Returns 'override' | 'master' | false
         ↓
If valid → hide PIN modal, show settings panel
If invalid → show "Invalid PIN" error in modal, clear input
```

---

## UI Behavior

- **Kiosk overlay remains visible** in background (per requirements)
- **PIN modal appears above overlay** (same visual layer as Ctrl+Shift+O)
- **Settings panel opens on top of PIN modal** after valid PIN
- **Escape/backdrop click** cancels PIN entry and returns to overlay
- **Title:** "Staff Override" for Ctrl+Shift+O, "Settings Access" for Settings button
- **Action button label:** "Override" vs "Access Settings" (or "Enter")

---

## Validation Rules (from ws/client.ts:triggerStaffOverride)

```typescript
// Connected to server:
if (overrideHash && verify(overrideHash, pin)) → 'override'

// Disconnected from server (emergency):
if (!connected && masterHash && verify(masterHash, pin)) → 'master'

// Otherwise → false
```

---

## Error Handling

| Scenario | Behavior |
|----------|----------|
| No `override_code_hash` configured | Show "Settings access not configured" announcement, don't open PIN modal |
| PIN verification fails | Show "Invalid PIN" error in modal, clear input, allow retry |
| Network error during validation | Show "Unable to verify PIN" error, allow retry |

---

## Testing

- Unit test `staff-override-dialog` with both modes
- Integration test: Settings button → PIN entry → settings panel
- Verify `triggerStaffOverride` validation logic covered (existing tests)

---

## Out of Scope

- Changing the Re-enroll flow itself
- Adding server-side PIN for settings
- Audit logging for settings access (can be added later)
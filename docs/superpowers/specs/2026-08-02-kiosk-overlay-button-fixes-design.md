# Kiosk Overlay Button Fixes — Design Spec

**Date**: 2026-08-02
**Status**: Approved
**Author**: AI Assistant
**Related**: Arcade Agent (Electron kiosk overlay)

---

## Problem Statement

The kiosk overlay on client PCs has two issues with the bottom-rail buttons:

1. **Styling broken**: Buttons use `.kiosk-btn` class but CSS only defines `.call-staff-btn`. Settings button has no styles.
2. **Settings opens separate window**: Clicking Settings opens a new `BrowserWindow` (`openSetupWindow()`) which:
   - Appears behind the always-on-top kiosk overlay
   - Causes Windows Start menu to flash/appear
   - Is not modal/focused properly
3. **Call Staff lacks feedback**: No visual confirmation when staff is notified.

---

## Solution Overview

| Issue | Fix |
|-------|-----|
| Button styling | Shared `.kiosk-btn` base class + `.secondary` variant for Settings |
| Settings window | Replace with in-overlay modal panel (no new BrowserWindow) |
| Call Staff feedback | Toast confirmation using existing announcement system |

---

## Detailed Design

### 1. Button Styling (`agent/src/renderer/kiosk.css`)

**Current**: `.call-staff-btn` (only styles Call Staff)
**New**: `.kiosk-btn` base class with variants

```css
.kiosk-btn {
  font-family: var(--font-display);
  font-weight: 600;
  font-size: .9rem;
  letter-spacing: .12em;
  text-transform: uppercase;
  border-radius: 10px;
  padding: .7rem 1.6rem;
  cursor: pointer;
  box-shadow: var(--glow) rgba(34, 211, 238, .25);
  transition: background .2s, color .2s;
}

/* Primary — Call Staff */
.kiosk-btn.primary {
  color: var(--accent);
  background: transparent;
  border: 1.5px solid var(--accent);
}
.kiosk-btn.primary:hover {
  background: var(--accent);
  color: var(--bg-0);
}

/* Secondary — Settings */
.kiosk-btn.secondary {
  color: var(--text-2);
  background: transparent;
  border: 1.5px solid var(--border);
}
.kiosk-btn.secondary:hover {
  background: var(--bg-2);
  border-color: var(--accent);
  color: var(--accent);
}
```

**HTML (in `kiosk-overlay.ts`)**:
```typescript
const callStaffBtn = document.createElement('button');
callStaffBtn.className = 'kiosk-btn primary';
callStaffBtn.textContent = 'Call Staff';

const settingsBtn = document.createElement('button');
settingsBtn.className = 'kiosk-btn secondary';
settingsBtn.textContent = 'Settings';
```

---

### 2. In-Overlay Settings Panel (`agent/src/renderer/components/settings-panel.ts` — NEW FILE)

**Purpose**: Modal dialog inside the kiosk overlay (no new window)

**Reuses**: `.modal-overlay`, `.modal-content`, `.modal-btn` from `tokens.css`

**API**:
```typescript
export interface SettingsPanelOptions {
  config: {
    serverUrl: string;
    seatId: string;
    agentSecret: string; // displayed masked
  };
  onReEnroll: () => void;
  onClose: () => void;
}

export function createSettingsPanel(options: SettingsPanelOptions): HTMLDivElement
```

**UI Structure**:
```
┌─────────────────────────────────────┐
│  🎮  Settings                       │
├─────────────────────────────────────┤
│  Server URL:  http://192.168.1.50:8742
│  Seat ID:     seat_01
│  Agent Secret: ●●●●●●●●●●●●●●●●
│                                       │
│  [Re-enroll]    [Close]              │
└─────────────────────────────────────┘
```

**Behavior**:
- **Re-enroll** → calls `onReEnroll()` → triggers existing `agent:enroll` IPC → on success, app relaunches
- **Close** → calls `onClose()` → hides modal
- ESC key / backdrop click → closes modal

---

### 3. Call Staff Visual Confirmation

**Add to `KioskOverlay` class** (`kiosk-overlay.ts`):
```typescript
showCallStaffConfirmation(): void {
  this.showAnnouncement('✓ Staff notified', 3000);
}
```

Uses existing `.kiosk-toast` styling (bottom-center, auto-dismiss).

---

### 4. Integration Updates

#### `kiosk-overlay.ts`
- Update button classes to `.kiosk-btn.primary` / `.kiosk-btn.secondary`
- Add `showCallStaffConfirmation()` method
- Add `onSettingsPanel(cb)` callback for Settings button

#### `index.ts` (renderer entry)
```typescript
// Settings button → show in-overlay panel
overlay.onSettingsPanel(() => {
  const panel = createSettingsPanel({
    config: { serverUrl, seatId, agentSecret },
    onReEnroll: () => window.electronAPI.openSettings(), // triggers re-enroll flow
    onClose: () => hideModal(panel),
  });
  showModal(panel);
});

// Call Staff → send IPC + show confirmation
overlay.onCallStaff(() => {
  window.electronAPI.callStaff();
  overlay.showCallStaffConfirmation();
});
```

#### `preload.ts`
- No new IPC needed; `openSettings()` already triggers re-enroll flow
- Settings panel calls existing `agent:open-settings` which opens setup window for re-enrollment

#### `main/index.ts`
- `agent:open-settings` IPC handler unchanged (opens setup window for re-enroll)
- No new main-process code required

---

## File Changes Summary

| File | Change Type | Description |
|------|-------------|-------------|
| `kiosk.css` | Modify | Rename `.call-staff-btn` → `.kiosk-btn` base + variants |
| `kiosk-overlay.ts` | Modify | Update button classes, add `showCallStaffConfirmation()`, add `onSettingsPanel()` |
| `settings-panel.ts` | **Create** | New component for in-overlay settings modal |
| `index.ts` | Modify | Wire Settings → panel, Call Staff → confirmation |
| `tokens.css` | None | Reuses existing modal styles |

---

## Testing Checklist

- [ ] Call Staff button styled correctly (primary variant)
- [ ] Settings button styled correctly (secondary variant)
- [ ] Click Settings → modal panel appears over overlay
- [ ] Panel shows masked agent secret, server URL, seat ID
- [ ] Click Re-enroll → opens setup window (existing flow)
- [ ] Click Close / ESC / backdrop → panel closes
- [ ] Click Call Staff → sends `STAFF_ALERT` + shows "✓ Staff notified" toast
- [ ] No new BrowserWindow created for Settings
- [ ] Windows Start menu does not appear/flash

---

## Rollback Plan

If issues arise:
1. Revert `kiosk.css` to `.call-staff-btn`
2. Revert `kiosk-overlay.ts` button classes
3. Delete `settings-panel.ts`
4. Revert `index.ts` to call `window.electronAPI.openSettings()` directly

No database/migrations affected.

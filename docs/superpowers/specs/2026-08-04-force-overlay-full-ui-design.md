# Force Overlay Full UI Design

**Date:** 2026-08-04
**Status:** Draft
**Author:** Assistant

---

## Problem Statement

When an admin enables "Force Overlay" from the dashboard, the kiosk displays a transparent screen showing only the timer and "Call Staff" button (resembling the HUD), instead of the full kiosk overlay with background, cafe brand, clock, event banner, and bottom rail.

**Expected Behavior:** Force Overlay should display the complete kiosk overlay UI matching the normal idle overlay appearance.

---

## Root Cause

The `FORCE_OVERLAY_ON` command handler in `agent/src/main/ws/commands.ts:96-110` calls `platform.showKioskOverlay()` but passes an `OverlayContent` object that includes explicit `remainingTime: undefined` and `lowTimeWarning: false` fields, whereas `SHOW_OVERLAY` (normal idle overlay) at lines 50-64 passes a cleaner structure without these explicit undefined fields.

Both commands call the same `showKioskOverlay()` platform method, but the renderer's `KioskOverlay` component receives slightly different data structures, potentially causing inconsistent UI rendering.

---

## Solution

Modify the `FORCE_OVERLAY_ON` handler to send the exact same `OverlayContent` structure as `SHOW_OVERLAY`, ensuring the kiosk overlay renderer receives consistent data regardless of how the overlay was triggered.

### File Changes

**1. `agent/src/main/ws/commands.ts`** - Update `FORCE_OVERLAY_ON` handler (lines 96-110)

```typescript
FORCE_OVERLAY_ON(payload) {
  // Force-show the kiosk overlay regardless of session state
  // Match SHOW_OVERLAY structure exactly for consistent UI rendering
  platform.showKioskOverlay({
    cafeName: deps.getCafeName?.() || 'Arcade',
    announcements: [],
    callStaffEnabled: true,
    sessionActive: !!payload.session_id,
    eventBanner: deps.getEventBanner?.() || '',
    serverUrl: deps.serverUrl,
    seatId: deps.seatId,
    agentSecret: deps.agentSecret,
  });
},
```

**Removed fields:**
- `remainingTime: undefined` - not needed; renderer handles empty timer when sessionActive=false
- `lowTimeWarning: false` - not needed; default is false in OverlayContent interface

---

## Architecture

### Data Flow

```
Dashboard "Lock all idle seats" button
       ↓
POST /api/seats/bulk/overlay {show: true}
       ↓
Server broadcasts FORCE_OVERLAY_ON {session_id?: string}
       ↓
AgentWebSocketClient.handleMessage() 
       ↓
createCommandHandlers().FORCE_OVERLAY_ON()
       ↓
platform.showKioskOverlay(OverlayContent)
       ↓
WindowsPlatformService.showKioskOverlay()
       ↓
kioskWindow.webContents.send('overlay:update', content)
       ↓
Preload.onOverlayContent() → renderer callback
       ↓
KioskOverlay.setCafeName(), setEventBanner(), setSessionActive(), setTimer()
```

### Component Behavior

**`KioskOverlay` class** (`agent/src/renderer/components/kiosk-overlay.ts`) already handles both states correctly:

| State | UI Components Visible |
|-------|----------------------|
| `sessionActive: false` (idle/force overlay) | Background, cafe brand, clock, event banner, bottom rail with Call Staff button. Status pill: "OPEN". Timer: hidden/empty. Session indicator: hidden. |
| `sessionActive: true` (active session) | All above PLUS timer counting up, status pill: "LIVE", session indicator: "● Session in progress" |

---

## Acceptance Criteria

- [ ] Enabling Force Overlay from dashboard displays complete overlay UI (dark background, cafe brand, clock, event banner, bottom rail with Call Staff button)
- [ ] Status pill shows "OPEN" when no session, "LIVE" when session active
- [ ] Timer is hidden/empty when no session, counts up when session active
- [ ] Visually matches normal idle overlay (triggered by session end)
- [ ] Force Overlay OFF hides the overlay completely

---

## Testing

**Manual Test:**
1. Start agent with no active session
2. From dashboard, click "Lock all idle seats"
3. Verify kiosk shows full overlay (not transparent HUD-like)
4. Start a session on that seat
5. Verify overlay updates to show timer and "LIVE" status
6. End session → verify overlay returns to idle state
7. Click "Unlock all seats" → verify overlay hides

**Edge Cases:**
- Force Overlay ON when seat already has active session
- Force Overlay ON/OFF rapid toggle
- Server disconnect/reconnect during Force Overlay

---

## Out of Scope

- HUD behavior during active sessions (already working)
- Staff override (Ctrl+Shift+O) functionality
- Settings panel access from overlay
- Multi-seat coordination (handled by bulk API)

---

## Implementation Notes

The fix is a one-line structural change in `commands.ts`. No changes needed to:
- Platform service (`windows.ts`, `types.ts`)
- Renderer components (`kiosk-overlay.ts`, `index.ts`)
- Preload script (`preload.ts`)
- Frontend dashboard

This follows YAGNI - minimal change for maximum consistency.
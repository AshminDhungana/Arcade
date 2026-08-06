# Kiosk Overlay OFF State — Call Staff Button Behavior

## Overview
When the kiosk overlay is turned OFF (via `HIDE_OVERLAY` or `FORCE_OVERLAY_OFF`), hide all overlay UI elements **except** the Call Staff button. The button should appear only when the user moves the mouse to the bottom-right corner of the screen (existing trigger zone), using the already-implemented mouse-edge detection logic.

## Current Architecture
- **Overlay OFF triggers**: `HIDE_OVERLAY` (session start) + `FORCE_OVERLAY_OFF` (staff force-off)
- **Overlay ON triggers**: `SHOW_OVERLAY` (session end) + `FORCE_OVERLAY_ON` (staff force-on)
- **Minimal mode**: Adds `.minimal` class to `.kiosk-overlay`, hides `.kiosk-bug`, `.kiosk-center`, `.kiosk-rail`, `.kiosk-status` via CSS
- **Trigger zone**: 20×20px fixed box at bottom-right corner (`right: 0; bottom: 0`)
- **Call Staff button**: Currently child of `.kiosk-rail` → gets hidden in minimal mode
- **Button reveal logic**: Already implemented via `triggerZone` `mouseenter`/`mouseleave` events

## Design

### 1. Component Restructure (`kiosk-overlay.ts`)

Move `callStaffBtn` from `railEl` to be a direct child of `container` (sibling to `triggerZone`):

```typescript
// In constructor:
this.triggerZone = document.createElement('div');
this.triggerZone.className = 'kiosk-trigger-zone';
this.container.appendChild(this.triggerZone);

// ... bugEl, centerEl, railEl construction unchanged ...

// Call Staff button — appended to CONTAINER (not railEl)
const callStaffBtn = document.createElement('button');
callStaffBtn.className = 'kiosk-btn primary';
callStaffBtn.textContent = 'Call Staff';
callStaffBtn.addEventListener('click', () => {
  this.callStaffCb?.();
  this.showCallStaffConfirmation();
  this.hideButton();
});
this.callStaffBtn = callStaffBtn;
this.container.appendChild(callStaffBtn); // CHANGED: was this.railEl.appendChild(...)

// railEl no longer contains callStaffBtn
this.railEl.appendChild(railStatus);
// this.railEl.appendChild(callStaffBtn); // REMOVED

this.container.appendChild(this.railEl);

// Event listeners for hot-corner trigger (unchanged)
this.triggerZone.addEventListener('mouseenter', () => this.showButton());
this.triggerZone.addEventListener('mouseleave', () => this.scheduleHide());
this.callStaffBtn.addEventListener('mouseenter', () => {
  this.isMouseOverButton = true;
  this.clearHideTimer();
});
this.callStaffBtn.addEventListener('mouseleave', () => {
  this.isMouseOverButton = false;
  this.scheduleHide();
});
```

### 2. CSS Minimal Mode (`kiosk.css`)

No changes needed to minimal mode rules — they already correctly hide `.kiosk-rail` while leaving `.kiosk-trigger-zone` and `.kiosk-btn.primary` (fixed position, controlled by `.visible` class) unaffected:

```css
/* Minimal mode — hide full overlay content, keep trigger zone + call staff button */
.kiosk-overlay.minimal .kiosk-bug,
.kiosk-overlay.minimal .kiosk-center,
.kiosk-overlay.minimal .kiosk-rail,
.kiosk-overlay.minimal .kiosk-status {
  display: none;
}

/* Trigger zone and button remain visible in minimal mode — no extra rules needed */
/* .kiosk-trigger-zone already display: block (fixed position, not child of hidden elements) */
/* .kiosk-btn.primary visibility controlled by .visible class (opacity + pointer-events) */
```

### 3. Button Behavior (Unchanged)

- Hidden by default: `opacity: 0; pointer-events: none;`
- Shows on `triggerZone` `mouseenter`: adds `.visible` class → `opacity: 1; pointer-events: auto;`
- Hides after 3s delay on `mouseleave`: removes `.visible` class
- Click → calls `callStaffCb` → `window.electronAPI.callStaff()` → shows confirmation toast

### 4. State Transitions

| Event | Overlay State | Minimal Mode | Visible Elements |
|-------|---------------|--------------|------------------|
| `HIDE_OVERLAY` / `FORCE_OVERLAY_OFF` | OFF | `true` | Trigger zone + Call Staff button (on hover) |
| `SHOW_OVERLAY` / `FORCE_OVERLAY_ON` | ON | `false` | Bug + Center + Rail + Status + Trigger zone + Call Staff button (on hover) |

## Regression Checks

- [ ] Overlay OFF: only trigger zone + call staff button (on right-edge hover) visible
- [ ] Overlay ON: full UI restored (bug, center, rail, status, button)
- [ ] Call Staff button click works identically in both states
- [ ] No other overlay elements render/interact in minimal mode
- [ ] Mouse-edge reveal works during active gameplay (not just idle)
- [ ] Toggling overlay ON/OFF multiple times works consistently

## Implementation Plan

1. **Refactor `kiosk-overlay.ts`**: Move button to container level, remove from rail
2. **Verify CSS**: Confirm minimal mode rules don't hide button
3. **Add unit test**: Test `setMinimalMode` visibility behavior
4. **Manual verification**: Test overlay OFF/ON transitions

## Files to Modify

- `agent/src/renderer/components/kiosk-overlay.ts` — Move button creation/append
- `agent/src/renderer/kiosk.css` — Verify (no changes expected)
- `agent/tests/ws/commands.test.ts` — Add test for minimal mode button visibility (optional)

## Acceptance Criteria

1. When `platform.showKioskOverlay({...})` is called with `minimal: true` (or `setMinimalMode(true)`), the Call Staff button appears on right-edge hover
2. When `setMinimalMode(false)`, full overlay UI is restored
3. Call Staff button click triggers `callStaffCb` in both modes
4. No visual regressions in full overlay mode

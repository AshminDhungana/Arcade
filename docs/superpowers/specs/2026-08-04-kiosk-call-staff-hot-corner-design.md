# Kiosk Overlay: Call Staff Button — Hot Corner Trigger Design

**Date:** 2026-08-04  
**Status:** Approved  
**Author:** AI Assistant (via brainstorming skill)

---

## Problem

The Call Staff button in the kiosk overlay currently sits at `bottom: 4vh`, which overlaps with the Windows taskbar when the overlay is visible. Additionally, the button is always visible, which can be accidentally triggered during gameplay.

**Requirements:**
1. Move button higher (above taskbar) — ~10vh from bottom
2. Button hidden by default
3. Appears only when mouse enters a tiny (20×20px) hot corner at the exact bottom-right of the screen
4. Auto-hides after 3 seconds (matching existing toast behavior)
5. Stays visible while mouse hovers over button or trigger zone

---

## Architecture

### Component Changes

**File:** `agent/src/renderer/components/kiosk-overlay.ts`

- Add invisible trigger zone element (20×20px, fixed at bottom-right)
- Move Call Staff button from `.kiosk-rail` flex child to fixed-positioned element
- Add `buttonVisible` state + `hideTimer` for auto-hide logic
- Reuse existing `showAnnouncement()` for "Staff notified" toast

**File:** `agent/src/renderer/kiosk.css`

- Add `.kiosk-trigger-zone` (fixed, bottom:0, right:0, 20×20px)
- Raise `.kiosk-rail` to `bottom: 10vh`
- Style `.kiosk-btn.primary` as hidden by default (`opacity: 0; pointer-events: none;`)
- Add `.kiosk-btn.primary.visible` state (`opacity: 1; pointer-events: auto;`)

### Constants

```typescript
const TRIGGER_ZONE_SIZE = 20;        // px
const BUTTON_BOTTOM_OFFSET = '10vh'; // raised above taskbar
const AUTO_HIDE_DELAY = 3000;        // ms (matches toast)
```

---

## Interaction Logic

| Event | Action |
|-------|--------|
| Mouse enters trigger zone | Add `.visible` to button; start 3s hide timer |
| Mouse enters button | Clear hide timer (button stays) |
| Mouse leaves button & trigger zone | Restart 3s hide timer |
| Hide timer fires | Remove `.visible` from button |
| Button clicked | Fire `callStaffCb`; show toast; hide button immediately |
| `destroy()` called | Clear hide timer |

---

## CSS Specification

```css
/* Hot-corner trigger zone */
.kiosk-trigger-zone {
  position: fixed;
  bottom: 0; right: 0;
  width: 20px; height: 20px;
  z-index: 100;
  pointer-events: auto;
}

/* Raise rail above taskbar */
.kiosk-rail {
  bottom: 10vh; /* was 4vh */
}

/* Call Staff button — hidden by default, fixed position */
.kiosk-btn.primary {
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.2s ease;
  position: fixed;
  bottom: 10vh;
  right: 4vw;
  z-index: 101;
}

/* Visible state */
.kiosk-btn.primary.visible {
  opacity: 1;
  pointer-events: auto;
}
```

---

## Error Handling & Edge Cases

| Scenario | Handling |
|----------|----------|
| Rapid hover enter/leave | Timer cleared/restarted; no flicker |
| Click during auto-hide | Timer cleared; toast shown; button hidden |
| `destroy()` with running timer | Cleanup added to clear timer |
| `prefers-reduced-motion` | Transition disabled via existing media query |
| Multi-monitor / fullscreen | Fixed viewport coords; works on primary display |

---

## Testing Plan

**New unit tests:**
1. Trigger zone exists at correct position
2. Button hidden by default (no `.visible`)
3. Hover trigger zone → button gets `.visible`
4. Button auto-hides after 3s when mouse leaves
5. Hover button → cancels auto-hide
6. Click → fires callback, shows toast, hides button
7. `destroy()` clears hide timer

**Regression:** All existing tests pass (rail status, session indicator, clock, branding, etc.)

---

## Implementation Order

1. Add trigger zone element + CSS in `kiosk-overlay.ts` constructor
2. Move button to fixed position + add visibility toggle methods
3. Implement hover handlers + auto-hide timer logic
4. Update CSS per spec
5. Add unit tests
6. Run lint/typecheck
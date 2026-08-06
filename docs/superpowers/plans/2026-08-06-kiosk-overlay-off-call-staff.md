# Kiosk Overlay OFF State — Call Staff Button Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move the Call Staff button out of the rail so it remains visible in minimal mode (overlay OFF), appearing only on right-edge hover using existing trigger zone logic.

**Architecture:** Pure DOM restructure — move button from `.kiosk-rail` child to `.kiosk-overlay` container child. CSS minimal mode rules already correctly hide rail while preserving fixed-position button. No new logic needed.

**Tech Stack:** TypeScript (ES modules), Electron renderer process, plain CSS

## Global Constraints

- Button behavior identical in both overlay states (click → `callStaffCb` → `window.electronAPI.callStaff()`)
- Trigger zone: 20×20px fixed at bottom-right (unchanged)
- Minimal mode toggled via `overlay.setMinimalMode(true/false)` from main process
- No changes to preload, main process, or WebSocket command handlers
- YAGNI: no new features, no refactoring beyond required restructure

---

### Task 1: Restructure KioskOverlay Component

**Files:**
- Modify: `agent/src/renderer/components/kiosk-overlay.ts:103-114` (button creation/append)
- Test: `agent/tests/ws/commands.test.ts` (add minimal mode visibility test)

**Interfaces:**
- Consumes: `KioskOverlay` class, existing `triggerZone` mouse events
- Produces: `callStaffBtn` as direct child of `container`; `railEl` no longer contains button

- [ ] **Step 1: Write failing test for minimal mode button visibility**

```typescript
// agent/tests/ws/commands.test.ts
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { KioskOverlay } from '../../src/renderer/components/kiosk-overlay.js';

describe('KioskOverlay minimal mode', () => {
  let container: HTMLDivElement;
  let overlay: KioskOverlay;

  beforeEach(() => {
    container = document.createElement('div');
    document.body.appendChild(container);
    overlay = new KioskOverlay(container);
  });

  afterEach(() => {
    overlay.destroy();
    container.remove();
  });

  it('shows call staff button on trigger zone hover in minimal mode', () => {
    overlay.setMinimalMode(true);

    // Trigger zone should exist and be visible
    const triggerZone = container.querySelector('.kiosk-trigger-zone');
    expect(triggerZone).toBeInTheDocument();

    // Call staff button should exist in container (not in rail)
    const callStaffBtn = container.querySelector('.kiosk-btn.primary');
    expect(callStaffBtn).toBeInTheDocument();

    // Button should be hidden by default (no .visible class)
    expect(callStaffBtn).not.toHaveClass('visible');

    // Simulate mouseenter on trigger zone
    triggerZone?.dispatchEvent(new MouseEvent('mouseenter'));

    // Button should now be visible
    expect(callStaffBtn).toHaveClass('visible');
  });

  it('hides call staff button when leaving trigger zone in minimal mode', () => {
    overlay.setMinimalMode(true);
    const triggerZone = container.querySelector('.kiosk-trigger-zone');
    const callStaffBtn = container.querySelector('.kiosk-btn.primary');

    triggerZone?.dispatchEvent(new MouseEvent('mouseenter'));
    expect(callStaffBtn).toHaveClass('visible');

    triggerZone?.dispatchEvent(new MouseEvent('mouseleave'));

    // After 3s delay (or immediate if we test the timer), button should hide
    // For test, we can advance timers or check scheduleHide was called
    vi.useFakeTimers();
    vi.advanceTimersByTime(3100);
    expect(callStaffBtn).not.toHaveClass('visible');
    vi.useRealTimers();
  });

  it('call staff button click works in minimal mode', () => {
    overlay.setMinimalMode(true);
    const callStaffCb = vi.fn();
    overlay.onCallStaff(callStaffCb);

    const callStaffBtn = container.querySelector('.kiosk-btn.primary') as HTMLButtonElement;
    const triggerZone = container.querySelector('.kiosk-trigger-zone');

    triggerZone?.dispatchEvent(new MouseEvent('mouseenter'));
    callStaffBtn.click();

    expect(callStaffCb).toHaveBeenCalledTimes(1);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd agent && npm test -- tests/ws/commands.test.ts -v
```
Expected: FAIL — button is inside rail, hidden in minimal mode

- [ ] **Step 3: Move button to container level in kiosk-overlay.ts**

```typescript
// agent/src/renderer/components/kiosk-overlay.ts
// Lines 103-114: Replace railEl button append with container append

// REMOVE from railEl:
// const callStaffBtn = document.createElement('button');
// callStaffBtn.className = 'kiosk-btn primary';
// callStaffBtn.textContent = 'Call Staff';
// callStaffBtn.addEventListener('click', () => {
//   this.callStaffCb?.();
//   this.showCallStaffConfirmation();
//   this.hideButton();
// });
// this.callStaffBtn = callStaffBtn;
// this.railEl.appendChild(callStaffBtn);

// ADD after railEl creation, before container.appendChild(this.railEl):
const callStaffBtn = document.createElement('button');
callStaffBtn.className = 'kiosk-btn primary';
callStaffBtn.textContent = 'Call Staff';
callStaffBtn.addEventListener('click', () => {
  this.callStaffCb?.();
  this.showCallStaffConfirmation();
  this.hideButton();
});
this.callStaffBtn = callStaffBtn;
this.container.appendChild(callStaffBtn); // CHANGED: append to container

// railEl only gets railStatus
this.railEl.appendChild(railStatus);
// this.railEl.appendChild(callStaffBtn); // REMOVED

this.container.appendChild(this.railEl);
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd agent && npm test -- tests/ws/commands.test.ts -v
```
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add agent/src/renderer/components/kiosk-overlay.ts agent/tests/ws/commands.test.ts
git commit -m "feat: move call staff button to container level for minimal mode visibility"
```

---

### Task 2: Verify CSS Minimal Mode Rules

**Files:**
- Read: `agent/src/renderer/kiosk.css:171-181`
- No modifications expected

**Interfaces:**
- Consumes: `.kiosk-overlay.minimal` class, `.kiosk-btn.primary` fixed positioning
- Produces: Confirmation that rules correctly hide rail but not button

- [ ] **Step 1: Inspect current CSS minimal mode rules**

```bash
cat agent/src/renderer/kiosk.css | sed -n '171,181p'
```

Expected output:
```css
/* Minimal mode — hide full overlay content, keep trigger zone + call staff button */
.kiosk-overlay.minimal .kiosk-bug,
.kiosk-overlay.minimal .kiosk-center,
.kiosk-overlay.minimal .kiosk-rail,
.kiosk-overlay.minimal .kiosk-status {
  display: none;
}

/* Trigger zone and button remain visible in minimal mode — no extra rules needed */
/* .kiosk-trigger-zone already display: block */
/* .kiosk-btn.primary visibility controlled by .visible class */
```

- [ ] **Step 2: Confirm no changes needed**

If rules match above, no action needed. If `.kiosk-btn.primary` is incorrectly targeted, fix it.

- [ ] **Step 3: Commit (if any changes)**

```bash
git add agent/src/renderer/kiosk.css
git commit -m "style: confirm minimal mode CSS preserves call staff button"
```

---

### Task 3: Manual Verification & Integration Test

**Files:**
- No file changes

**Interfaces:**
- Consumes: Built agent, Electron app
- Produces: Verified behavior in both overlay states

- [ ] **Step 1: Build agent**

```bash
cd agent && npm run build
```

- [ ] **Step 2: Test overlay ON state (full UI)**

1. Launch agent
2. Verify full overlay visible: bug (ARCADE + status pill), center (brand, clock, timer), rail (status + call staff button)
3. Hover bottom-right → call staff button appears
4. Click call staff button → "Staff notified" toast

- [ ] **Step 3: Test overlay OFF state (minimal mode)**

1. Trigger `HIDE_OVERLAY` (start session) or `FORCE_OVERLAY_OFF` (staff force-off)
2. Verify: bug, center, rail, status HIDDEN
3. Verify: trigger zone (bottom-right 20×20) still present
4. Hover bottom-right → call staff button appears
5. Click call staff button → "Staff notified" toast
6. Move mouse away → button hides after 3s

- [ ] **Step 4: Test toggle ON/OFF cycles**

1. Toggle overlay OFF → ON → OFF → ON multiple times
2. Verify no visual glitches, button works consistently

- [ ] **Step 5: Commit verification**

```bash
git commit --allow-empty -m "test: manual verification of minimal mode call staff behavior"
```

---

## Summary

| Task | Description | Files Changed |
|------|-------------|---------------|
| 1 | Move button to container level | `kiosk-overlay.ts`, `commands.test.ts` |
| 2 | Verify CSS minimal mode rules | `kiosk.css` (verify only) |
| 3 | Manual integration test | None (verification) |

**Total estimated time:** 30-45 minutes

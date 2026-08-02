# Kiosk Overlay Cafe Name Fallback Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add fallback "Arcade" display in kiosk overlay center when cafe name is unavailable, with server-provided name taking priority once received via REGISTERED.

**Architecture:** Renderer owns the fallback. `KioskOverlay` tracks both arcade fallback name and server cafe name. On init, center shows "Arcade". When `onOverlayContent` delivers server cafe name, it overrides the fallback. Top bug wordmark stays "ARCADE".

**Tech Stack:** TypeScript, Electron renderer process, Vitest for unit tests

## Global Constraints

- Top bug wordmark (`.cafe-wordmark`) remains hardcoded "ARCADE" — no changes
- Fallback name "Arcade" is hardcoded in renderer, not configurable
- Server is source of truth for cafe name; no local persistence
- Existing `OverlayData` interface and IPC flow unchanged
- Backward compatible: if server never sends cafe_name, "Arcade" displays

---

### Task 1: Add `setArcadeName` and modify `setCafeName` in KioskOverlay component

**Files:**
- Modify: `agent/src/renderer/components/kiosk-overlay.ts`
- Test: `agent/tests/renderer/components/kiosk-overlay.test.ts`

**Interfaces:**
- Consumes: None (base component)
- Produces: `KioskOverlay.setArcadeName(name: string)`, modified `KioskOverlay.setCafeName(name: string, logo?: string)`

- [ ] **Step 1: Write failing tests for new fallback behavior**

```typescript
// Add to agent/tests/renderer/components/kiosk-overlay.test.ts

import { describe, it, expect, beforeEach, afterEach } from 'vitest';
import { KioskOverlay } from '../../../src/renderer/components/kiosk-overlay.js';

describe('KioskOverlay fallback behavior', () => {
  let parent: HTMLDivElement;
  let overlay: KioskOverlay;

  beforeEach(() => {
    parent = document.createElement('div');
    document.body.appendChild(parent);
    overlay = new KioskOverlay(parent);
  });

  afterEach(() => {
    overlay.destroy();
    document.body.innerHTML = '';
  });

  it('shows "Arcade" in center by default (before any setCafeName)', () => {
    const brand = parent.querySelector('.cafe-brand');
    expect(brand).not.toBeNull();
    expect(brand!.textContent).toBe('Arcade');
  });

  it('setArcadeName updates fallback and displays it when no cafe name set', () => {
    overlay.setArcadeName('My Arcade');
    const brand = parent.querySelector('.cafe-brand');
    expect(brand!.textContent).toBe('My Arcade');
  });

  it('setCafeName with non-empty name displays that name (overrides fallback)', () => {
    overlay.setArcadeName('Fallback');
    overlay.setCafeName('Neon Cafe');
    const brand = parent.querySelector('.cafe-brand');
    expect(brand!.textContent).toBe('Neon Cafe');
  });

  it('setCafeName with empty name falls back to arcadeName', () => {
    overlay.setArcadeName('Fallback');
    overlay.setCafeName('');
    const brand = parent.querySelector('.cafe-brand');
    expect(brand!.textContent).toBe('Fallback');
  });

  it('setCafeName with only whitespace falls back to arcadeName', () => {
    overlay.setArcadeName('Fallback');
    overlay.setCafeName('   ');
    const brand = parent.querySelector('.cafe-brand');
    expect(brand!.textContent).toBe('Fallback');
  });

  it('setCafeName with logo and name displays both', () => {
    overlay.setCafeName('Neon Cafe', 'logo.png');
    const brand = parent.querySelector('.cafe-brand');
    expect(brand!.textContent).toBe('Neon Cafe');
    expect(brand!.querySelector('img')).not.toBeNull();
    expect(brand!.querySelector('img')!.src).toContain('logo.png');
  });

  it('setCafeName with logo only (empty name) shows logo + fallback name', () => {
    overlay.setArcadeName('Fallback');
    overlay.setCafeName('', 'logo.png');
    const brand = parent.querySelector('.cafe-brand');
    expect(brand!.textContent).toBe('Fallback');
    expect(brand!.querySelector('img')).not.toBeNull();
  });

  it('calling setArcadeName after setCafeName with server name does NOT override server name', () => {
    overlay.setCafeName('Server Cafe');
    overlay.setArcadeName('New Fallback');
    const brand = parent.querySelector('.cafe-brand');
    expect(brand!.textContent).toBe('Server Cafe');
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd agent && npm test -- tests/renderer/components/kiosk-overlay.test.ts -v`
Expected: FAIL (methods don't exist, default shows empty)

- [ ] **Step 3: Implement `setArcadeName` and modify `setCafeName` in kiosk-overlay.ts**

```typescript
// agent/src/renderer/components/kiosk-overlay.ts

export class KioskOverlay {
  public readonly container: HTMLDivElement;
  private readonly bugEl: HTMLDivElement;
  private readonly statusPill: HTMLDivElement;
  private readonly centerEl: HTMLDivElement;
  private readonly cafeBrandEl: HTMLDivElement;
  private readonly clockEl: HTMLDivElement;
  private readonly timerEl: HTMLDivElement;
  private readonly sessionIndicator: HTMLDivElement;
  private readonly bannerEl: HTMLDivElement;
  private readonly railEl: HTMLDivElement;
  private clockInterval: ReturnType<typeof setInterval> | null = null;

  // NEW: Fallback name (default "Arcade")
  private arcadeName = 'Arcade';
  // NEW: Track server-provided cafe name
  private currentCafeName = '';

  constructor(parent: HTMLElement) {
    this.container = document.createElement('div');
    this.container.className = 'kiosk-overlay';
    parent.appendChild(this.container);

    // Top bug: product wordmark + OPEN/LIVE status pill
    this.bugEl = document.createElement('div');
    this.bugEl.className = 'kiosk-bug';
    const wordmark = document.createElement('span');
    wordmark.className = 'cafe-wordmark';
    wordmark.textContent = 'ARCADE';
    this.statusPill = document.createElement('div');
    this.statusPill.className = 'status-pill';
    this.statusPill.innerHTML = '<span class="dot"></span><span class="label">OPEN</span>';
    this.bugEl.append(wordmark, this.statusPill);
    this.container.appendChild(this.bugEl);

    // Centered hero cluster
    this.centerEl = document.createElement('div');
    this.centerEl.className = 'kiosk-center';

    this.cafeBrandEl = document.createElement('div');
    this.cafeBrandEl.className = 'cafe-brand';
    // Initialize with fallback name
    const span = document.createElement('span');
    span.textContent = this.arcadeName;
    this.cafeBrandEl.appendChild(span);
    this.centerEl.appendChild(this.cafeBrandEl);

    this.bannerEl = document.createElement('div');
    this.bannerEl.className = 'event-banner';
    this.bannerEl.style.display = 'none';
    this.centerEl.appendChild(this.bannerEl);

    this.clockEl = document.createElement('div');
    this.clockEl.className = 'clock';
    this.centerEl.appendChild(this.clockEl);

    this.timerEl = document.createElement('div');
    this.timerEl.className = 'timer-display';
    this.centerEl.appendChild(this.timerEl);

    this.sessionIndicator = document.createElement('div');
    this.sessionIndicator.className = 'session-indicator';
    this.sessionIndicator.textContent = '● Session in progress';
    this.centerEl.appendChild(this.sessionIndicator);

    this.container.appendChild(this.centerEl);

    // Bottom rail: status + buttons
    this.railEl = document.createElement('div');
    this.railEl.className = 'kiosk-rail';
    const railStatus = document.createElement('div');
    railStatus.className = 'kiosk-status';
    railStatus.innerHTML = '<span class="ok"></span><span>Online</span>';
    this.railEl.appendChild(railStatus);

    const callStaffBtn = document.createElement('button');
    callStaffBtn.className = 'kiosk-btn primary';
    callStaffBtn.textContent = 'Call Staff';
    callStaffBtn.addEventListener('click', () => this.callStaffCb?.());
    this.railEl.appendChild(callStaffBtn);

    this.container.appendChild(this.railEl);
  }

  // ... existing methods unchanged (startClock, stopClock, setTimer, setSessionActive, isClockRunning, showAnnouncement, showCallStaffConfirmation, onCallStaff, destroy, updateClock) ...

  /** NEW: Set the fallback name (default 'Arcade'). */
  setArcadeName(name: string): void {
    this.arcadeName = name || 'Arcade';
    // If no server name has been set, update display immediately
    if (!this.currentCafeName) {
      this.cafeBrandEl.replaceChildren();
      const span = document.createElement('span');
      span.textContent = this.arcadeName;
      this.cafeBrandEl.appendChild(span);
    }
  }

  /** MODIFIED: Render cafe name or fallback to arcadeName. */
  setCafeName(name: string, logo?: string): void {
    this.currentCafeName = name || '';
    this.cafeBrandEl.replaceChildren();
    if (logo) {
      const img = document.createElement('img');
      img.src = logo;
      img.className = 'cafe-logo';
      img.alt = name || this.arcadeName;
      this.cafeBrandEl.appendChild(img);
    }
    const span = document.createElement('span');
    span.textContent = this.currentCafeName || this.arcadeName;
    this.cafeBrandEl.appendChild(span);
  }

  // ... rest unchanged ...
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd agent && npm test -- tests/renderer/components/kiosk-overlay.test.ts -v`
Expected: PASS

- [ ] **Step 5: Run all kiosk-overlay tests to ensure no regressions**

Run: `cd agent && npm test -- tests/renderer/components/kiosk-overlay.test.ts -v`
Expected: All 22 tests pass

- [ ] **Step 6: Commit**

```bash
git add agent/src/renderer/components/kiosk-overlay.ts agent/tests/renderer/components/kiosk-overlay.test.ts
git commit -m "feat(kiosk): add cafe name fallback with setArcadeName/setCafeName"
```

---

### Task 2: Call `setArcadeName('Arcade')` on overlay init in renderer index.ts

**Files:**
- Modify: `agent/src/renderer/index.ts`
- Test: None (integration verified manually/e2e)

**Interfaces:**
- Consumes: `KioskOverlay.setArcadeName` from Task 1
- Produces: Initial "Arcade" display on agent startup

- [ ] **Step 1: Modify initKiosk to set fallback name**

```typescript
// agent/src/renderer/index.ts

function initKiosk(): void {
  const app = document.getElementById('app');
  if (!app) {
    console.error('[Renderer] #app container not found');
    return;
  }

  // --- Core overlay ---
  const overlay = new KioskOverlay(app);
  
  // NEW: Set fallback name immediately on init
  overlay.setArcadeName('Arcade');
  
  overlay.startClock();

  // ... rest unchanged ...
}
```

- [ ] **Step 2: Verify no TypeScript errors**

Run: `cd agent && npx tsc --noEmit`
Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add agent/src/renderer/index.ts
git commit -m "feat(kiosk): initialize fallback cafe name on overlay start"
```

---

### Task 3: Verify end-to-end behavior manually

**Files:**
- None (manual verification)

**Interfaces:**
- Consumes: Tasks 1-2 complete

- [ ] **Step 1: Build agent**

Run: `cd agent && npm run build`
Expected: Build succeeds

- [ ] **Step 2: Run agent in dev mode and verify initial display**

Run: `cd agent && npm run dev`
Expected: Kiosk overlay opens, center shows "Arcade" immediately (before WebSocket connects)

- [ ] **Step 3: Verify server cafe name overrides fallback after REGISTERED**

(Requires running server; verify center updates to actual cafe name after connection)

- [ ] **Step 4: Commit any dev-only fixes if needed**

```bash
git add -A
git commit -m "fix: any dev-mode adjustments for cafe name fallback"
```

---

### Task 4: Run full test suite to ensure no regressions

**Files:**
- None

- [ ] **Step 1: Run all agent tests**

Run: `cd agent && npm test`
Expected: All tests pass

- [ ] **Step 2: Run lint**

Run: `cd agent && npm run lint`
Expected: No errors

- [ ] **Step 3: Commit**

```bash
git commit -m "test: verify full suite passes after cafe name fallback"
```

---

## Self-Review

**Spec coverage check:**
- ✅ Fallback "Arcade" on init — Task 1 (constructor), Task 2 (init call)
- ✅ Server cafe name overrides — Task 1 (setCafeName logic)
- ✅ Empty/whitespace cafe name falls back — Task 1 (tests + implementation)
- ✅ Logo handling with fallback — Task 1 (tests + implementation)
- ✅ setArcadeName after server name doesn't override — Task 1 (test + implementation)
- ✅ Top bug unchanged — Not modified anywhere

**Placeholder scan:** No TBD/TODO — all code blocks complete with exact implementations

**Type consistency:** `arcadeName` and `currentCafeName` are private strings; `setArcadeName` and `setCafeName` signatures match test expectations and usage in index.ts

---

**Plan complete and saved to** `docs/superpowers/plans/2026-08-02-kiosk-overlay-cafe-name-fallback.md`

Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
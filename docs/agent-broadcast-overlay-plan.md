# Agent Broadcast Overlay Redesign — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the Arcade Agent's kiosk lock screen, in-session HUD, and modals into a tournament-ready broadcast look — distinct cyan/violet identity, shared design tokens, a transient HUD (timer appears briefly at session start, hidden during play, returns urgently at ~5 min), scarce Call Staff (30 s after unlock / 10 s on bottom-right corner hover), and a server-controlled optional event banner.

**Architecture:** Two vanilla-DOM renderer windows (kiosk + HUD) share one new `tokens.css` design system and a `motion.ts` Web Animations helper. A pure `hud-state.ts` reducer drives the HUD lifecycle so transitions are unit-testable. The event banner is an optional `eventBanner` field on `OverlayContent`, owned by the server and rendered only when present. No framework, no new runtime dependency, no WebSocket timer contract change.

**Tech Stack:** TypeScript (vanilla DOM, Electron renderer), CSS custom properties, Web Animations API, Vitest (jsdom). Agent tests run from repo root with `npx vitest run`.

## Global Constraints

- **No React / no `motion-dev` dependency.** Adapt `ui-ux-pro-max` and `motion-dev` *principles* into CSS + Web Animations API (spec §3).
- **No WebSocket contract change for the timer.** The HUD countdown is *local* from `minutes_remaining` (spec §3, §7).
- **Agent keeps its own identity** — electric cyan `#22d3ee` / violet `#a855f7` — diverging from the web dashboard's blue `#0090fa` and the launcher's indigo `#6366F1` (spec §3, §4).
- **Renderer stays vanilla DOM** — no framework migration (spec §3).
- **Clicks pass through during play** — HUD uses `setIgnoreMouseEvents(true,{forward:true})`; only the Call Staff button captures its own clicks (spec §3, §7).
- **WCAG AA contrast** for all text (≥ 4.5:1); large/non-text accent elements exempt (spec §1).
- **Event banner hidden by default, server-controlled** — agent is a passive renderer; never hard-code banner text (spec §7).
- **Reduced motion respected** via `@media (prefers-reduced-motion: reduce)` (spec §5).
- **Fonts bundled** (`renderer/public/*.woff2`) with a system fallback so a missing font never breaks layout (spec §6).

---

### Task 1: Shared design tokens (`tokens.css`) + link in both HTML files

**Files:**
- Create: `agent/src/renderer/tokens.css`
- Modify: `agent/src/renderer/index.html`, `agent/src/renderer/hud.html`

**Interfaces:**
- Consumes: nothing.
- Produces: the CSS custom properties (`--bg-0`, `--accent`, `--grad`, etc.) and shared `.modal-*` / reduced-motion rules used by every later task.

- [ ] **Step 1: Create `agent/src/renderer/tokens.css`**

```css
/* agent/src/renderer/tokens.css — shared broadcast design system */

:root {
  --bg-0: #050609;
  --bg-1: #0b0e15;
  --bg-2: #141926;
  --accent: #22d3ee;
  --accent-2: #a855f7;
  --live: #ef4444;
  --warn: #f59e0b;
  --text-1: #f8fafc;
  --text-2: #9aa6b8;
  --text-3: #5b6678;
  --border: rgba(255, 255, 255, .08);
  --glow: 0 0 24px;
  --radius: 14px;
  --grad: linear-gradient(135deg, #22d3ee, #a855f7);
  --font-display: 'Chakra Petch', 'Russo One', system-ui, sans-serif;
  --font-ui: 'Inter', system-ui, sans-serif;
}

/* ---- Fonts (bundled; system fallback) — files added in Task 9 ---- */
@font-face {
  font-family: 'Chakra Petch';
  src: url('./public/ChakraPetch-SemiBold.woff2') format('woff2');
  font-weight: 600; font-display: swap;
}
@font-face {
  font-family: 'Inter';
  src: url('./public/Inter-Regular.woff2') format('woff2');
  font-weight: 400; font-display: swap;
}
@font-face {
  font-family: 'Inter';
  src: url('./public/Inter-Medium.woff2') format('woff2');
  font-weight: 500; font-display: swap;
}

/* ---- Shared modal (used by kiosk + HUD) ---- */
.modal-overlay {
  position: fixed; inset: 0;
  background: rgba(0, 0, 0, .85);
  display: none; align-items: center; justify-content: center;
  z-index: 1000; opacity: 0;
  transition: opacity .3s ease;
  pointer-events: none;
}
.modal-overlay.visible { opacity: 1; }
.modal-content {
  pointer-events: auto;
  background: var(--bg-1);
  border: 1px solid var(--accent);
  border-radius: var(--radius);
  padding: 2.5rem;
  max-width: 520px; width: 90%;
  text-align: center;
  box-shadow: 0 0 50px rgba(34, 211, 238, .18);
}
.modal-title {
  font-family: var(--font-display); font-weight: 600;
  font-size: 1.4rem; margin-bottom: 1rem; color: var(--warn);
  display: flex; align-items: center; justify-content: center; gap: .5rem;
}
.modal-body { font-size: .95rem; color: var(--text-2); margin-bottom: 1.25rem; }
.modal-actions { display: flex; gap: 1rem; justify-content: center; margin-top: 1.25rem; }
.modal-btn {
  pointer-events: auto; padding: .75rem 2rem; font-size: 1rem;
  border-radius: 8px; cursor: pointer; text-transform: uppercase;
  font-family: var(--font-display); letter-spacing: .08em;
  transition: background .2s ease;
}
.modal-btn.primary { background: var(--accent); border: none; color: var(--bg-0); }
.modal-btn.primary:hover { background: #6fe3ff; }
.modal-btn.secondary { background: transparent; border: 1px solid var(--accent); color: var(--accent); }
.modal-btn.secondary:hover { background: var(--bg-2); }

/* ---- Reduced motion ---- */
@media (prefers-reduced-motion: reduce) {
  * { animation: none !important; transition: none !important; }
}
```

- [ ] **Step 2: Link `tokens.css` (and keep the surface CSS) in both HTML files**

In `agent/src/renderer/index.html`, change the `<head>` to:

```html
  <link rel="stylesheet" href="./tokens.css">
  <link rel="stylesheet" href="./kiosk.css">
```

In `agent/src/renderer/hud.html`:

```html
  <link rel="stylesheet" href="./tokens.css">
  <link rel="stylesheet" href="./hud.css">
```

- [ ] **Step 3: Verify no regressions**

Run: `npx vitest run agent/tests/renderer`
Expected: all existing renderer tests PASS (tokens.css is inert until later tasks use the variables).

- [ ] **Step 4: Commit**

```bash
git add agent/src/renderer/tokens.css agent/src/renderer/index.html agent/src/renderer/hud.html
git commit -m "feat(agent): add shared broadcast design tokens"
```

---

### Task 2: Web Animations helpers (`motion.ts`)

**Files:**
- Create: `agent/src/renderer/motion.ts`
- Test: `agent/tests/renderer/motion.test.ts`

**Interfaces:**
- Consumes: nothing.
- Produces: `reveal(el, delayMs?)`, `pulseTimer(el)`, `countdown(fromSeconds, onTick, onDone?, intervalMs?)` — used by `hud.ts` (Task 6) and (optionally) modals.

- [ ] **Step 1: Write the failing test**

```ts
// agent/tests/renderer/motion.test.ts
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { countdown } from '../../src/renderer/motion.js';

describe('countdown', () => {
  beforeEach(() => vi.useFakeTimers());
  afterEach(() => vi.useRealTimers());

  it('calls onTick immediately then each second, ending at 0', () => {
    const ticks: number[] = [];
    countdown(2, (r) => ticks.push(r));
    expect(ticks).toEqual([2]);
    vi.advanceTimersByTime(1000);
    expect(ticks).toEqual([2, 1]);
    vi.advanceTimersByTime(1000);
    expect(ticks).toEqual([2, 1, 0]);
  });

  it('calls onDone at zero', () => {
    const done = vi.fn();
    countdown(1, () => {}, done);
    vi.advanceTimersByTime(1000);
    expect(done).toHaveBeenCalledOnce();
  });

  it('returns a stop function that halts ticks', () => {
    const ticks: number[] = [];
    const stop = countdown(5, (r) => ticks.push(r));
    vi.advanceTimersByTime(1000);
    stop();
    vi.advanceTimersByTime(5000);
    expect(ticks).toEqual([5, 4]);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run agent/tests/renderer/motion.test.ts`
Expected: FAIL — `Cannot find module '../../src/renderer/motion.js'`.

- [ ] **Step 3: Write minimal implementation**

```ts
// agent/src/renderer/motion.ts

/** Entrance reveal: fade + rise. No-op if Web Animations API is unavailable. */
export function reveal(el: HTMLElement, delayMs = 0): void {
  if (typeof el.animate !== 'function') return;
  el.animate(
    [{ opacity: 0, transform: 'translateY(12px)' }, { opacity: 1, transform: 'translateY(0)' }],
    { duration: 320, delay: delayMs, easing: 'cubic-bezier(.2,.7,.3,1)', fill: 'both' },
  );
}

/** Subtle per-second pulse on the timer digit group. */
export function pulseTimer(el: HTMLElement): void {
  if (typeof el.animate !== 'function') return;
  el.animate(
    [{ transform: 'scale(1)' }, { transform: 'scale(1.04)' }, { transform: 'scale(1)' }],
    { duration: 180, easing: 'ease-out' },
  );
}

/** Local countdown. Calls onTick immediately and every intervalMs; onDone at 0.
 *  Returns a stop function. */
export function countdown(
  fromSeconds: number,
  onTick: (remaining: number) => void,
  onDone?: () => void,
  intervalMs = 1000,
): () => void {
  let remaining = fromSeconds;
  onTick(remaining);
  const id = setInterval(() => {
    remaining -= 1;
    if (remaining <= 0) {
      clearInterval(id);
      onTick(0);
      onDone?.();
      return;
    }
    onTick(remaining);
  }, intervalMs);
  return () => clearInterval(id);
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run agent/tests/renderer/motion.test.ts`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add agent/src/renderer/motion.ts agent/tests/renderer/motion.test.ts
git commit -m "feat(agent): add WAAPI motion helpers"
```

---

### Task 3: HUD state machine (`hud-state.ts`)

**Files:**
- Create: `agent/src/renderer/hud-state.ts`
- Test: `agent/tests/renderer/hud-state.test.ts`

**Interfaces:**
- Consumes: nothing.
- Produces: `type HudPhase`, `type HudEvent`, `nextHudPhase(phase, event)` — the pure reducer wired by `hud.ts` (Task 6).

- [ ] **Step 1: Write the failing test**

```ts
// agent/tests/renderer/hud-state.test.ts
import { describe, it, expect } from 'vitest';
import { nextHudPhase, type HudPhase } from '../../src/renderer/hud-state.js';

describe('nextHudPhase', () => {
  it('session-start moves to INTRO from ENDED', () => {
    expect(nextHudPhase('ENDED', 'session-start')).toBe('INTRO');
  });
  it('intro-timeout moves INTRO to AMBIENT', () => {
    expect(nextHudPhase('INTRO', 'intro-timeout')).toBe('AMBIENT');
  });
  it('intro-timeout is a no-op outside INTRO', () => {
    expect(nextHudPhase('AMBIENT', 'intro-timeout')).toBe('AMBIENT');
  });
  it('low-time moves AMBIENT to URGENT', () => {
    expect(nextHudPhase('AMBIENT', 'low-time')).toBe('URGENT');
  });
  it('low-time moves INTRO to URGENT', () => {
    expect(nextHudPhase('INTRO', 'low-time')).toBe('URGENT');
  });
  it('session-end moves any phase to ENDED', () => {
    const phases: HudPhase[] = ['INTRO', 'AMBIENT', 'URGENT', 'ENDED'];
    for (const p of phases) expect(nextHudPhase(p, 'session-end')).toBe('ENDED');
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run agent/tests/renderer/hud-state.test.ts`
Expected: FAIL — module not found.

- [ ] **Step 3: Write minimal implementation**

```ts
// agent/src/renderer/hud-state.ts

export type HudPhase = 'INTRO' | 'AMBIENT' | 'URGENT' | 'ENDED';
export type HudEvent = 'session-start' | 'intro-timeout' | 'low-time' | 'session-end';

/** Pure HUD lifecycle reducer. The renderer holds `phase` and calls this on each
 *  real event; see spec §3. */
export function nextHudPhase(phase: HudPhase, event: HudEvent): HudPhase {
  switch (event) {
    case 'session-start':
      return 'INTRO';
    case 'intro-timeout':
      return phase === 'INTRO' ? 'AMBIENT' : phase;
    case 'low-time':
      return 'URGENT';
    case 'session-end':
      return 'ENDED';
  }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run agent/tests/renderer/hud-state.test.ts`
Expected: PASS (6 tests).

- [ ] **Step 5: Commit**

```bash
git add agent/src/renderer/hud-state.ts agent/tests/renderer/hud-state.test.ts
git commit -m "feat(agent): add pure HUD state machine"
```

---

### Task 4: Kiosk overlay — broadcast layout + event banner (`kiosk-overlay.ts`)

**Files:**
- Modify: `agent/src/renderer/components/kiosk-overlay.ts`
- Test: `agent/tests/renderer/components/kiosk-overlay.test.ts`

**Interfaces:**
- Consumes: CSS classes defined in `kiosk.css` (Task 5): `kiosk-overlay`, `kiosk-bug`, `cafe-wordmark`, `status-pill`, `kiosk-center`, `cafe-brand`, `cafe-logo`, `event-banner`, `clock`, `timer-display`, `session-indicator`, `kiosk-rail`, `kiosk-status`.
- Produces: `setEventBanner(text?: string)` — shows the banner element when `text` is non-empty, hides it otherwise. Used by `index.ts` (Task 11). The Call Staff button stays appended by `index.ts` and is positioned by CSS (no `index.ts` change in this task).
- `setSessionActive(active)` now also drives the `.status-pill` label (OPEN ⇄ LIVE) and its `.live` class.

> **Scope note (plan gap closed):** The approved design's kiosk (spec §2 / mockup) shows a top "bug" (product wordmark + OPEN/LIVE pill) and a bottom status rail. The current component (`kiosk-overlay.ts`) builds only a centered column, so this task ADDS those elements (bug + center wrapper + rail). The existing `kiosk-overlay.test.ts` (queries `.clock` / `.session-indicator` / `.timer-display` / `.kiosk-overlay` / `.cafe-brand` via descendant selectors) stays fully compatible — all those elements still exist, now nested inside the layout.

- [ ] **Step 1: Write the failing test (append to the existing test file)**

```ts
// agent/tests/renderer/components/kiosk-overlay.test.ts (append)
import { describe, it, expect } from 'vitest';
import { KioskOverlay } from '../../../src/renderer/components/kiosk-overlay.js';

describe('KioskOverlay.setEventBanner', () => {
  it('shows the banner with text', () => {
    const root = document.createElement('div');
    const overlay = new KioskOverlay(root);
    overlay.setEventBanner('Weekend Tournament');
    const banner = root.querySelector('.event-banner') as HTMLElement;
    expect(banner).not.toBeNull();
    expect(banner.textContent).toBe('Weekend Tournament');
    expect(banner.style.display).not.toBe('none');
  });

  it('hides the banner when text is empty (default)', () => {
    const root = document.createElement('div');
    const overlay = new KioskOverlay(root);
    overlay.setEventBanner('');
    const banner = root.querySelector('.event-banner') as HTMLElement;
    expect(banner.style.display).toBe('none');
  });

  it('hides the banner when called with no argument', () => {
    const root = document.createElement('div');
    const overlay = new KioskOverlay(root);
    overlay.setEventBanner();
    const banner = root.querySelector('.event-banner') as HTMLElement;
    expect(banner.style.display).toBe('none');
  });

  it('builds the bug + center + rail layout', () => {
    const root = document.createElement('div');
    new KioskOverlay(root);
    expect(root.querySelector('.kiosk-bug')).not.toBeNull();
    expect(root.querySelector('.cafe-wordmark')).not.toBeNull();
    expect(root.querySelector('.status-pill')).not.toBeNull();
    expect(root.querySelector('.kiosk-center')).not.toBeNull();
    expect(root.querySelector('.kiosk-rail')).not.toBeNull();
    expect(root.querySelector('.kiosk-status')).not.toBeNull();
  });

  it('toggles the status pill between OPEN and LIVE', () => {
    const root = document.createElement('div');
    const overlay = new KioskOverlay(root);
    const label = () => (root.querySelector('.status-pill .label') as HTMLElement).textContent;
    expect(label()).toBe('OPEN');
    overlay.setSessionActive(true);
    expect(label()).toBe('LIVE');
    expect(root.querySelector('.status-pill')!.classList.contains('live')).toBe(true);
    overlay.setSessionActive(false);
    expect(label()).toBe('OPEN');
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run agent/tests/renderer/components/kiosk-overlay.test.ts`
Expected: FAIL — `banner` is null / `setEventBanner` not a function / layout elements missing.

- [ ] **Step 3: Replace `kiosk-overlay.ts` with the broadcast-layout version below**

```ts
/**
 * Kiosk overlay UI component — plain DOM, no external lib.
 * Built for the Arcade Agent electron renderer process.
 */

export interface KioskOverlayState {
  cafeName: string;
  sessionActive: boolean;
  remainingTime: string;
  callStaffEnabled: boolean;
}

/**
 * Encapsulates all kiosk overlay UI: top bug (wordmark + status pill),
 * hero cluster (brand, event banner, clock, timer, session indicator),
 * and bottom status rail.
 */
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

    // Bottom rail: status
    this.railEl = document.createElement('div');
    this.railEl.className = 'kiosk-rail';
    const railStatus = document.createElement('div');
    railStatus.className = 'kiosk-status';
    railStatus.innerHTML = '<span class="ok"></span><span>Online</span>';
    this.railEl.appendChild(railStatus);
    this.container.appendChild(this.railEl);
  }

  /** Start the live clock (updates every second). */
  startClock(): void {
    this.updateClock();
    this.clockInterval = setInterval(() => this.updateClock(), 1000);
  }

  /** Stop the live clock. */
  stopClock(): void {
    if (this.clockInterval !== null) {
      clearInterval(this.clockInterval);
      this.clockInterval = null;
    }
  }

  /** Update the visible timer string (e.g., "00:05:32"). */
  setTimer(timeString = ''): void {
    this.timerEl.textContent = timeString;
  }

  /** Show/hide the session indicator and drive the bug status pill. */
  setSessionActive(active: boolean): void {
    const label = this.statusPill.querySelector('.label');
    if (active) {
      this.sessionIndicator.classList.add('active');
      this.statusPill.classList.add('live');
      if (label) label.textContent = 'LIVE';
    } else {
      this.sessionIndicator.classList.remove('active');
      this.statusPill.classList.remove('live');
      if (label) label.textContent = 'OPEN';
      this.timerEl.textContent = '';
    }
  }

  /** Render the branded cafe name/logo header. */
  setCafeName(name: string, logo?: string): void {
    this.cafeBrandEl.replaceChildren();
    if (logo) {
      const img = document.createElement('img');
      img.src = logo;
      img.className = 'cafe-logo';
      img.alt = name;
      this.cafeBrandEl.appendChild(img);
    }
    const span = document.createElement('span');
    span.textContent = name;
    this.cafeBrandEl.appendChild(span);
  }

  /** Show the server-provided event banner, or hide it when empty/unset. */
  setEventBanner(text?: string): void {
    if (text && text.trim().length > 0) {
      this.bannerEl.textContent = text;
      this.bannerEl.style.display = '';
    } else {
      this.bannerEl.style.display = 'none';
    }
  }

  /** Return whether clock is running. */
  isClockRunning(): boolean {
    return this.clockInterval !== null;
  }

  /** Tear down the component. */
  destroy(): void {
    this.stopClock();
    if (this.container.parentNode) {
      this.container.parentNode.removeChild(this.container);
    }
  }

  private updateClock(): void {
    const now = new Date();
    this.clockEl.textContent = now.toLocaleTimeString('en-US', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
    });
  }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run agent/tests/renderer/components/kiosk-overlay.test.ts`
Expected: PASS (existing 9 tests + the 5 new tests).

- [ ] **Step 5: Commit**

```bash
git add agent/src/renderer/components/kiosk-overlay.ts agent/tests/renderer/components/kiosk-overlay.test.ts
git commit -m "feat(agent): kiosk broadcast layout + server-controlled event banner"
```

---

### Task 5: Kiosk CSS restyle (`kiosk.css`)

**Files:**
- Modify: `agent/src/renderer/kiosk.css`

**Interfaces:**
- Consumes: tokens from `tokens.css` (Task 1); `.modal-*` rules already in `tokens.css`.
- Produces: the full broadcast kiosk layout using token classes; the `.event-banner` style consumed by `setEventBanner` (Task 4).

- [ ] **Step 1: Replace `kiosk.css` entirely with the broadcast layout**

```css
/* agent/src/renderer/kiosk.css — broadcast kiosk lock screen */

* { margin: 0; padding: 0; box-sizing: border-box; }

body {
  font-family: var(--font-ui);
  background: var(--bg-0);
  color: var(--text-1);
  height: 100vh; width: 100vw;
  overflow: hidden;
  display: flex; align-items: center; justify-content: center;
}

#app {
  width: 100%; height: 100%;
  display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  text-align: center;
}

.kiosk-overlay {
  position: relative;
  width: 100%; height: 100%;
}

/* Centered hero cluster (brand, banner, clock, timer, session indicator) */
.kiosk-center {
  position: absolute; inset: 0;
  display: flex; flex-direction: column;
  align-items: center; justify-content: center;
  gap: 1.25rem; text-align: center;
}

/* Top bug: gradient wordmark + status pill */
.kiosk-bug {
  position: absolute; top: 4vh; left: 4vw; right: 4vw;
  display: flex; align-items: center; justify-content: space-between;
}
.cafe-wordmark {
  font-family: var(--font-display); font-weight: 700;
  font-size: clamp(20px, 2.4vw, 34px); letter-spacing: .06em;
  background: var(--grad); -webkit-background-clip: text; background-clip: text; color: transparent;
}
.status-pill {
  display: flex; align-items: center; gap: .5rem;
  font-family: var(--font-display); font-weight: 600; font-size: .8rem;
  letter-spacing: .16em; color: var(--live);
  padding: .35rem .8rem; border: 1px solid rgba(239, 68, 68, .5);
  border-radius: 40px; background: rgba(239, 68, 68, .1);
}
.status-pill .dot {
  width: 8px; height: 8px; border-radius: 50%; background: var(--live);
  box-shadow: var(--glow) var(--live); animation: pulse 1.6s ease-in-out infinite;
}
@keyframes pulse { 0%, 100% { opacity: 1; transform: scale(1); } 50% { opacity: .35; transform: scale(.7); } }

/* Hero */
.cafe-brand {
  font-family: var(--font-display); font-weight: 700;
  font-size: clamp(32px, 5vw, 64px); letter-spacing: .04em;
  color: var(--text-1); text-shadow: 0 0 30px rgba(34, 211, 238, .18);
}
.event-banner {
  margin-top: .5rem; font-size: clamp(11px, 1.2vw, 15px);
  letter-spacing: .14em; text-transform: uppercase; color: var(--accent);
}

.clock {
  font-family: var(--font-display); font-weight: 600;
  font-size: clamp(48px, 9vw, 110px); letter-spacing: .03em;
  color: var(--text-1); font-variant-numeric: tabular-nums;
  text-shadow: 0 0 40px rgba(34, 211, 238, .3);
}

/* Bottom rail */
.kiosk-rail {
  position: absolute; bottom: 4vh; left: 4vw; right: 4vw;
  display: flex; align-items: center; justify-content: space-between;
}
.kiosk-status {
  font-size: .75rem; letter-spacing: .12em; text-transform: uppercase; color: var(--text-2);
  display: flex; align-items: center; gap: .5rem;
}
.kiosk-status .ok { width: 8px; height: 8px; border-radius: 50%; background: var(--accent); box-shadow: var(--glow) var(--accent); }

.call-staff-btn {
  font-family: var(--font-display); font-weight: 600; font-size: .9rem;
  letter-spacing: .12em; text-transform: uppercase; color: var(--accent);
  background: transparent; border: 1.5px solid var(--accent);
  border-radius: 10px; padding: .7rem 1.6rem; cursor: pointer;
  box-shadow: var(--glow) rgba(34, 211, 238, .25); transition: background .2s, color .2s;
}
.call-staff-btn:hover { background: var(--accent); color: var(--bg-0); }

/* Announcement (reused by HUD) */
.announcement-banner {
  position: fixed; top: 0; left: 0; right: 0;
  padding: 1rem; background: rgba(245, 158, 11, .15);
  border-bottom: 1px solid rgba(245, 158, 11, .3);
  color: var(--warn); font-size: 1rem; text-align: center;
  opacity: 0; transition: opacity .5s ease; pointer-events: none;
}
.announcement-banner.visible { opacity: 1; }
```

- [ ] **Step 2: Verify no regressions + visual sanity**

Run: `npx vitest run agent/tests/renderer/components/kiosk-overlay.test.ts`
Expected: PASS (class names used by `KioskOverlay` — `cafe-brand`, `clock`, `session-indicator`, `timer-display` — are unchanged; only the new `.event-banner` + layout classes were added).

- [ ] **Step 3: Commit**

```bash
git add agent/src/renderer/kiosk.css
git commit -m "feat(agent): restyle kiosk to broadcast layout"
```

---

### Task 6: HUD wiring — transient timer + Call Staff visibility (`hud.ts`)

**Files:**
- Modify: `agent/src/renderer/hud.ts`
- Test: `agent/tests/renderer/hud.test.ts`

**Interfaces:**
- Consumes: `nextHudPhase` (Task 3), `reveal`/`pulseTimer`/`countdown` (Task 2), `createLowTimeModal`/`showModal`/`hideModal` (existing `low-time-warning.ts`), `window.electronAPI` (existing preload).
- Produces: the live HUD behavior — INTRO timer ~5 s + Call Staff 30 s, AMBIENT (nothing), URGENT (local countdown + modal), corner-hover Call Staff 10 s.

- [ ] **Step 1: Write the failing test (append to existing `hud.test.ts`)**

```ts
// agent/tests/renderer/hud.test.ts (append)
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

function mockElectronAPI() {
  const handlers: Record<string, (...a: any[]) => void> = {};
  (window as any).electronAPI = {
    onTimerUpdate: (cb: any) => { handlers['timer'] = cb; },
    onAnnouncement: (cb: any) => { handlers['announcement'] = cb; },
    onLowTimeWarning: (cb: any) => { handlers['lowtime'] = cb; },
    onOverlayContent: () => {},
    onSessionStatus: () => {},
    callStaff: vi.fn(),
  };
  return handlers;
}

describe('HUD transient behavior', () => {
  // The renderer auto-runs initHud on import, so we set up the DOM + fake
  // timers, then dynamically import after mocking electronAPI.
  beforeEach(() => { document.body.innerHTML = '<div id="app"></div>'; mockElectronAPI(); });
  afterEach(() => vi.useRealTimers());

  it('hides the timer after the INTRO window (~5s)', async () => {
    vi.useFakeTimers();
    await import('../../src/renderer/hud.js');
    const timer = document.querySelector('.hud-timer') as HTMLElement;
    expect(timer.style.display).not.toBe('none');
    vi.advanceTimersByTime(5000);
    expect(timer.style.display).toBe('none');
  });

  it('hides Call Staff after the INTRO window (30s)', async () => {
    vi.useFakeTimers();
    await import('../../src/renderer/hud.js');
    const btn = document.querySelector('.call-staff-btn') as HTMLElement;
    expect(btn.style.display).not.toBe('none');
    vi.advanceTimersByTime(30000);
    expect(btn.style.display).toBe('none');
  });

  it('shows Call Staff for 10s when the mouse enters the bottom-right corner', async () => {
    vi.useFakeTimers();
    await import('../../src/renderer/hud.js');
    const btn = document.querySelector('.call-staff-btn') as HTMLElement;
    vi.advanceTimersByTime(30000); // past INTRO
    expect(btn.style.display).toBe('none');
    const move = new MouseEvent('mousemove', { clientX: window.innerWidth - 5, clientY: window.innerHeight - 5 });
    document.dispatchEvent(move);
    expect(btn.style.display).not.toBe('none');
    vi.advanceTimersByTime(10000);
    expect(btn.style.display).toBe('none');
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run agent/tests/renderer/hud.test.ts`
Expected: FAIL — `.hud-timer` element missing / display assertions wrong (current `hud.ts` always shows a centered timer).

- [ ] **Step 3: Rewrite `hud.ts`**

```ts
/**
 * HUD renderer — transparent, click-through overlay shown over the live game
 * during a session. Timer + Call Staff are transient (see hud-state).
 */
import { createLowTimeModal, showModal, hideModal } from './components/low-time-warning.js';
import { nextHudPhase, type HudPhase, type HudEvent } from './hud-state.js';
import { reveal, pulseTimer, countdown } from './motion.js';

const TIMER_INTRO_MS = 5000;       // elapsed timer visible at session start
const CALLSTAFF_INTRO_MS = 30000;  // Call Staff visible after unlock
const CALLSTAFF_HOVER_MS = 10000;  // Call Staff visible on corner hover
const HOVER_ZONE = 0.12;           // bottom-right hotzone size (fraction of viewport)

function formatElapsed(totalSeconds: number): string {
  const s = Math.max(0, Math.floor(totalSeconds));
  const hh = Math.floor(s / 3600);
  const mm = Math.floor((s % 3600) / 60);
  const ss = s % 60;
  const pad = (n: number) => n.toString().padStart(2, '0');
  return `${pad(hh)}:${pad(mm)}:${pad(ss)}`;
}

function formatCountdown(totalSeconds: number): string {
  const safe = Math.max(0, Math.floor(totalSeconds));
  const mm = String(Math.floor(safe / 60)).padStart(2, '0');
  const ss = String(safe % 60).padStart(2, '0');
  return `${mm}:${ss}`;
}

export function initHud(): void {
  const app = document.getElementById('app');
  if (!app) return;

  let phase: HudPhase = 'INTRO';
  const dispatch = (event: HudEvent) => { phase = nextHudPhase(phase, event); };

  const timer = document.createElement('div');
  timer.className = 'hud-timer';
  timer.style.display = 'none';

  const callBtn = document.createElement('button');
  callBtn.className = 'call-staff-btn';
  callBtn.textContent = 'Call Staff';
  callBtn.style.display = 'none';
  callBtn.addEventListener('click', () => window.electronAPI.callStaff());

  const announcementEl = document.createElement('div');
  announcementEl.className = 'announcement-banner';

  app.append(timer, callBtn, announcementEl);

  // INTRO: timer (~5s) + Call Staff (30s)
  timer.style.display = '';
  timer.textContent = formatElapsed(0);
  reveal(timer);
  const introTimer = setTimeout(() => {
    timer.style.display = 'none';
    dispatch('intro-timeout');
  }, TIMER_INTRO_MS);

  callBtn.style.display = '';
  const introCall = setTimeout(() => { callBtn.style.display = 'none'; }, CALLSTAFF_INTRO_MS);

  // Corner hover: Call Staff 10s
  let hoverCall = 0;
  const onMouseMove = (e: MouseEvent) => {
    const w = window.innerWidth, h = window.innerHeight;
    const inZone = e.clientX > w * (1 - HOVER_ZONE) && e.clientY > h * (1 - HOVER_ZONE);
    if (inZone && callBtn.style.display === 'none') {
      callBtn.style.display = '';
      clearTimeout(hoverCall);
      hoverCall = window.setTimeout(() => { callBtn.style.display = 'none'; }, CALLSTAFF_HOVER_MS);
    }
  };
  document.addEventListener('mousemove', onMouseMove);

  // Timer updates (INTRO only; URGENT drives its own countdown)
  window.electronAPI.onTimerUpdate((tick) => {
    if (timer.style.display !== 'none' && phase !== 'URGENT') {
      const prev = timer.textContent;
      timer.textContent = formatElapsed(tick.elapsedSeconds);
      if (prev !== timer.textContent) pulseTimer(timer);
    }
  });

  // Announcements (lower-third)
  window.electronAPI.onAnnouncement((text, durationMs) => {
    announcementEl.textContent = text;
    announcementEl.classList.add('visible');
    setTimeout(() => announcementEl.classList.remove('visible'), durationMs);
  });

  // Low-time → URGENT
  let stopCountdown: (() => void) | null = null;
  window.electronAPI.onLowTimeWarning((minutes) => {
    dispatch('low-time');
    timer.style.display = '';
    timer.classList.add('urgent');
    callBtn.style.display = '';
    stopCountdown = countdown(minutes * 60, (remaining) => {
      timer.textContent = formatCountdown(remaining);
    });
    const lowTimeModal = createLowTimeModal({
      minutesRemaining: minutes,
      onDismiss: () => hideModal(lowTimeModal),
    });
    document.body.appendChild(lowTimeModal);
    showModal(lowTimeModal);
  });

  window.addEventListener('beforeunload', () => {
    clearTimeout(introTimer); clearTimeout(introCall); clearTimeout(hoverCall);
    stopCountdown?.();
  });
}

if (typeof document !== 'undefined') {
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initHud);
  } else {
    initHud();
  }
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run agent/tests/renderer/hud.test.ts`
Expected: PASS (existing + 3 new tests).

- [ ] **Step 5: Commit**

```bash
git add agent/src/renderer/hud.ts agent/tests/renderer/hud.test.ts
git commit -m "feat(agent): transient HUD timer + scarce Call Staff"
```

---

### Task 7: HUD CSS restyle (`hud.css`)

**Files:**
- Modify: `agent/src/renderer/hud.css`

**Interfaces:**
- Consumes: tokens from `tokens.css` (Task 1); `.announcement-banner` already defined in `kiosk.css` but the HUD needs its own copy (or rely on shared) — define here for the HUD; `.modal-*` already in `tokens.css`.
- Produces: transparent click-through HUD; `.hud-timer` (hidden by default, `.urgent` variant), `.call-staff-btn` (hidden by default), `.announcement-banner` lower-third.

- [ ] **Step 1: Replace `hud.css` entirely**

```css
/* agent/src/renderer/hud.css — transparent in-session HUD (click-through) */

* { margin: 0; padding: 0; box-sizing: border-box; }

body {
  background: transparent; overflow: hidden;
  font-family: var(--font-ui); color: var(--text-1);
  pointer-events: none; /* click-through to the game */
}

#app {
  width: 100vw; height: 100vh;
  display: flex; flex-direction: column;
  justify-content: center; align-items: center;
}

/* Timer — hidden by default; shown briefly at INTRO and persistently at URGENT */
.hud-timer {
  font-family: var(--font-display); font-weight: 600;
  font-size: clamp(40px, 7vw, 90px); letter-spacing: .03em;
  color: var(--text-1); font-variant-numeric: tabular-nums;
  text-shadow: 0 0 36px rgba(34, 211, 238, .3);
}
.hud-timer.urgent {
  color: var(--warn);
  text-shadow: 0 0 44px rgba(245, 158, 11, .45);
  animation: warnpulse 1.1s ease-in-out infinite;
}
@keyframes warnpulse { 0%, 100% { opacity: 1; } 50% { opacity: .72; } }

/* Call Staff — hidden by default; shown by hud.ts (INTRO / corner hover / URGENT) */
.call-staff-btn {
  position: absolute; right: 4vw; bottom: 4vh;
  pointer-events: auto;
  font-family: var(--font-display); font-weight: 600; font-size: .8rem;
  letter-spacing: .12em; text-transform: uppercase; color: var(--accent);
  background: rgba(5, 6, 9, .4); backdrop-filter: blur(4px);
  border: 1px solid rgba(34, 211, 238, .35); border-radius: 9px;
  padding: .6rem 1.1rem; cursor: pointer; transition: opacity .2s, background .2s;
}
.call-staff-btn:hover { background: var(--accent); color: var(--bg-0); }

/* Announcement lower-third */
.announcement-banner {
  position: fixed; left: 4vw; bottom: 12vh; max-width: 60%;
  background: rgba(11, 14, 21, .92); border-left: 3px solid var(--accent);
  border-radius: 0 10px 10px 0; padding: .75rem 1.1rem;
  font-size: .9rem; color: var(--text-1);
  box-shadow: 0 10px 30px rgba(0, 0, 0, .5);
  opacity: 0; transform: translateX(-30px);
  transition: opacity .5s ease, transform .5s ease; pointer-events: none;
}
.announcement-banner.visible { opacity: 1; transform: none; }
```

- [ ] **Step 2: Verify no regressions**

Run: `npx vitest run agent/tests/renderer`
Expected: PASS (DOM class names used by `hud.ts` — `.hud-timer`, `.call-staff-btn`, `.announcement-banner` — match the new CSS).

- [ ] **Step 3: Commit**

```bash
git add agent/src/renderer/hud.css
git commit -m "feat(agent): restyle HUD to minimal broadcast layout"
```

---

### Task 8: Modals broadcast restyle (reuse shared CSS)

**Files:**
- Modify: `agent/src/renderer/components/low-time-warning.ts` (no TS change needed — class names unchanged), `agent/src/renderer/components/staff-override-dialog.ts` (no TS change needed)
- Verify: `agent/tests/renderer/components/low-time-warning.test.ts`, `agent/tests/renderer/components/staff-override-dialog.test.ts`

**Interfaces:**
- Consumes: `.modal-*` shared rules from `tokens.css` (Task 1). The two component files use stable class names (`.modal-overlay`, `.modal-content`, `.modal-title`, `.modal-body`, `.modal-actions`, `.modal-btn`, `.low-time-countdown`, `.pin-pad`, `.pin-display`, `.modal-icon`). **No TS edit required** — they already reference these classes; the restyle lives in `tokens.css` (Task 1) + the surface CSS.
- Produces: broadcast-styled modals via the shared `.modal-*` rules; PIN-pad accents via the additions below.

- [ ] **Step 1: Confirm the TS class names are unchanged**

Run: `npx vitest run agent/tests/renderer/components/low-time-warning.test.ts agent/tests/renderer/components/staff-override-dialog.test.ts`
Expected: PASS — `formatCountdown`, modal creation, and PIN pad logic are unaffected.

- [ ] **Step 2: Add PIN-pad + countdown accents to `tokens.css` (append)**

Append to `agent/src/renderer/tokens.css`:

```css
/* ---- PIN pad (staff override) ---- */
.pin-display {
  font-family: var(--font-display); font-size: 2rem; letter-spacing: .4em;
  color: var(--accent); margin: 1rem 0; min-height: 2.5rem;
  font-variant-numeric: tabular-nums;
}
.pin-pad {
  display: grid; grid-template-columns: repeat(3, 1fr); gap: .5rem;
  margin: 1rem auto; max-width: 300px;
}
.pin-pad button {
  padding: 1rem; font-size: 1.4rem; font-family: var(--font-display);
  background: var(--bg-2); border: 1px solid var(--border); color: var(--text-1);
  border-radius: 8px; cursor: pointer; user-select: none;
  transition: background .15s, border-color .15s;
}
.pin-pad button:hover { background: #1c2436; border-color: var(--accent); }
.modal-icon { color: var(--accent); }

/* ---- Low-time countdown numeral ---- */
.low-time-countdown {
  font-family: var(--font-display); font-weight: 600; font-size: 2.2rem;
  color: var(--warn); font-variant-numeric: tabular-nums; margin-top: .5rem;
}
```

- [ ] **Step 3: Verify modals render with the new styles**

Run: `npx vitest run agent/tests/renderer/components`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add agent/src/renderer/tokens.css
git commit -m "feat(agent): broadcast-restyle modals via shared tokens"
```

---

### Task 9: Bundle display + UI fonts

**Files:**
- Create: `agent/src/renderer/public/ChakraPetch-SemiBold.woff2`, `agent/src/renderer/public/Inter-Regular.woff2`, `agent/src/renderer/public/Inter-Medium.woff2`

**Interfaces:**
- Consumes: `@font-face` blocks in `tokens.css` (Task 1) referencing `./public/*.woff2`.
- Produces: the bundled font files so the renderer needs no network and falls back to system fonts if missing.

- [ ] **Step 1: Obtain the woff2 files**

Download Chakra Petch (weight 600) and Inter (weights 400, 500) as `.woff2` and place them at the exact paths above. Reliable sources:
  - `npm view @fontsource/chakra-petch` / `@fontsource/inter` — install either package and copy the `files/*.woff2` from `node_modules/@fontsource/.../files/` into `agent/src/renderer/public/`.
  - Or fetch from the Google Fonts GitHub (`google/fonts`), saving the `latin` subset woff2.

  Filenames MUST match the `@font-face` `src` URLs in `tokens.css`: `ChakraPetch-SemiBold.woff2`, `Inter-Regular.woff2`, `Inter-Medium.woff2`.

- [ ] **Step 2: Verify the build references them**

Run: `npx tsc -p agent/src/renderer --noEmit` (or the agent's typecheck) — confirms no broken imports. Visually confirm in the running agent that headers/timer use Chakra Petch and fall back to system sans if a file is temporarily removed.

- [ ] **Step 3: Commit**

```bash
git add agent/src/renderer/public/ChakraPetch-SemiBold.woff2 agent/src/renderer/public/Inter-Regular.woff2 agent/src/renderer/public/Inter-Medium.woff2
git commit -m "feat(agent): bundle Chakra Petch + Inter woff2"
```

> If binary fonts cannot be committed in your environment, commit a `fonts.README` in `agent/src/renderer/public/` documenting the exact filenames + source, and keep the `@font-face` blocks (system fallback preserves layout).

---

### Task 10: Agent-side event banner field (`OverlayContent` → `OverlayData` → commands)

**Files:**
- Modify: `agent/src/main/platform/types.ts`, `agent/src/renderer/preload.ts`, `agent/src/main/ws/commands.ts`
- Test: `agent/tests/ws/commands.test.ts`

**Interfaces:**
- Consumes: `HandlerDeps.getCafeName` pattern (existing) — add a parallel `getEventBanner`.
- Produces: `OverlayContent.eventBanner?`, `OverlayData.eventBanner?`, and `SHOW_OVERLAY` / `FORCE_OVERLAY_ON` populating it — consumed by `index.ts` (Task 11) and the kiosk `setEventBanner` (Task 4).

- [ ] **Step 1: Write the failing test (append to `commands.test.ts`)**

```ts
// agent/tests/ws/commands.test.ts (append)
import { describe, it, expect, vi } from 'vitest';
import { createCommandHandlers } from '../../src/main/ws/commands.js';

function fakePlatform() {
  return {
    showKioskOverlay: vi.fn(), hideKioskOverlay: vi.fn(), showHud: vi.fn(),
    hideHud: vi.fn(), showLowTimeWarning: vi.fn(), sendAnnouncement: vi.fn(),
    isKioskVisible: () => false,
  } as any;
}

describe('event banner', () => {
  it('SHOW_OVERLAY passes eventBanner from getEventBanner', () => {
    const platform = fakePlatform();
    const handlers = createCommandHandlers(platform, {
      seatId: 'seat-1',
      getCafeName: () => 'Arcade',
      getEventBanner: () => 'Weekend Tournament',
    });
    handlers.SHOW_OVERLAY({ session_id: 's1', started_at: '2026-01-01T00:00:00Z' });
    const content = platform.showKioskOverlay.mock.calls[0][0];
    expect(content.eventBanner).toBe('Weekend Tournament');
  });

  it('omits banner when getEventBanner returns empty', () => {
    const platform = fakePlatform();
    const handlers = createCommandHandlers(platform, {
      seatId: 'seat-1', getCafeName: () => 'Arcade', getEventBanner: () => '',
    });
    handlers.SHOW_OVERLAY({ session_id: 's1', started_at: '2026-01-01T00:00:00Z' });
    const content = platform.showKioskOverlay.mock.calls[0][0];
    expect(content.eventBanner).toBe('');
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run agent/tests/ws/commands.test.ts`
Expected: FAIL — `getEventBanner` not a known `HandlerDeps` field / `eventBanner` undefined.

- [ ] **Step 3: Add the field to `OverlayContent` (`platform/types.ts`)**

In the `OverlayContent` interface, add:

```ts
  /** Optional event/tournament banner shown on the kiosk when set by the server. */
  eventBanner?: string;
```

- [ ] **Step 4: Add the field to `OverlayData` (`renderer/preload.ts`)**

In the `OverlayData` interface (the `onOverlayContent` callback payload), add:

```ts
  eventBanner?: string;
```

- [ ] **Step 5: Populate it in `commands.ts`**

In `HandlerDeps`, add:

```ts
  getEventBanner?: () => string;
```

In the `SHOW_OVERLAY` handler, change the `showKioskOverlay` call to:

```ts
      platform.showKioskOverlay({
        cafeName: deps.getCafeName?.() || 'Arcade',
        announcements: [],
        callStaffEnabled: true,
        sessionActive: false,
        eventBanner: deps.getEventBanner?.() || '',
      });
```

In the `FORCE_OVERLAY_ON` handler, change its `showKioskOverlay` call similarly (add `eventBanner: deps.getEventBanner?.() || ''`).

- [ ] **Step 6: Run test to verify it passes**

Run: `npx vitest run agent/tests/ws/commands.test.ts`
Expected: PASS (existing + 2 new tests).

- [ ] **Step 7: Commit**

```bash
git add agent/src/main/platform/types.ts agent/src/renderer/preload.ts agent/src/main/ws/commands.ts agent/tests/ws/commands.test.ts
git commit -m "feat(agent): wire server-controlled event banner through OverlayContent"
```

---

### Task 11: Kiosk renders the banner (`index.ts`)

**Files:**
- Modify: `agent/src/renderer/index.ts`
- Test: `agent/tests/renderer/components/kiosk-overlay.test.ts` (already covers `setEventBanner`)

**Interfaces:**
- Consumes: `setEventBanner(text?)` (Task 4), `OverlayData.eventBanner?` (Task 10).
- Produces: the kiosk now shows the server banner when present, hidden otherwise.

- [ ] **Step 1: Pass `eventBanner` from overlay content into the overlay**

In `agent/src/renderer/index.ts`, in `updateOverlay`, after the `setCafeName` call, add:

```ts
  if (data.eventBanner !== undefined) {
    overlay.setEventBanner(data.eventBanner);
  }
```

Also update the `initialData` object to include `eventBanner: ''` (so the banner starts hidden):

```ts
  const initialData: OverlayData = {
    cafeName: 'Arcade',
    sessionActive: false,
    callStaffEnabled: true,
    announcements: [],
    eventBanner: '',
  };
```

- [ ] **Step 2: Verify**

Run: `npx vitest run agent/tests/renderer`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add agent/src/renderer/index.ts
git commit -m "feat(agent): render server event banner on kiosk"
```

---

### Task 12: Backend event-banner setting

**Files:**
- Modify: backend settings model + settings GET serializer/endpoint (locate via `backend/models/` and the settings router the agent already calls for `cafeName`).

**Interfaces:**
- Consumes: the existing server settings store/endpoint the agent uses for `getCafeName` (trace `getCafeName` in `agent/src/main/ws/client.ts` → the settings fetch).
- Produces: a persistent `event_banner` string (default `''`) returned by that GET endpoint, read by the agent's `getEventBanner`.

- [ ] **Step 1: Locate the settings model + endpoint**

Grep: `grep -rn "cafe_name\|cafeName" backend/` to find where `cafeName` is sourced. The same model/endpoint gains `event_banner`.

- [ ] **Step 2: Add the field**

Add `event_banner: str = ""` (or the ORM equivalent, e.g. SQLAlchemy `Column(String, default="")`) to the settings model. If settings are stored as a single JSON blob, add the key there instead. No new migration if the store is JSON; otherwise add an Alembic revision.

- [ ] **Step 3: Expose it on the GET endpoint**

Ensure the settings GET response includes `event_banner`. The agent's `getCafeName` reads from this response — add `event_banner` alongside it.

- [ ] **Step 4: Test (pytest)**

Add/extend a backend test asserting `GET /settings` returns `event_banner` (default `''`) and that `PUT /settings` with `{"event_banner": "Weekend Tournament"}` persists and is returned.

Run: `pytest backend/tests/ -k "settings" -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/  # the settings model + endpoint + test
git commit -m "feat(backend): add event_banner setting"
```

---

### Task 13: Frontend dashboard event-banner field

**Files:**
- Modify: `frontend/src/components/settings/*` (the Settings tab that edits cafe/branding — find it via `grep -rn "cafeName\|cafe_name" frontend/src`), `frontend/src/types/settings.ts` if present.

**Interfaces:**
- Consumes: the backend `event_banner` setting (Task 12).
- Produces: a dashboard text field to set/clear the event banner, persisted via the existing settings PUT.

- [ ] **Step 1: Locate the settings form**

Grep: `grep -rn "cafeName\|cafe_name" frontend/src` to find the Settings field that edits the cafe name. Add the event-banner field next to it.

- [ ] **Step 2: Add the field**

Add a labeled text input bound to `event_banner`, with a clear/save button that calls the existing settings update mutation. Placeholder: "e.g. Weekend Tournament (shown on the kiosk when set)".

- [ ] **Step 3: Test (vitest)**

Add/extend a frontend test asserting the field renders, edits `event_banner`, and submits it via the settings mutation.

Run: `npx vitest run frontend/src/components/settings`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add frontend/  # the settings tab + types + test
git commit -m "feat(frontend): dashboard field to set the event banner"
```

---

### Task 14: Full manual smoke + reduced-motion check

**Files:** none (verification only).

- [ ] **Step 1: Build/run the agent on the target OS (Windows)**

Launch the agent; from the dashboard start a session on a seat.

- [ ] **Step 2: Verify HUD lifecycle**
  - Session start: HUD timer shows ~5 s then hides; Call Staff shows 30 s then hides.
  - Play: no timer, no Call Staff; clicks reach the game (whole screen usable).
  - Move mouse into bottom-right corner: Call Staff appears ~10 s then hides.
  - Server sends low-time at ~5 min: timer returns (amber→red, pulsing) + low-time modal; Call Staff visible.
  - Announcement (`SHOW_MESSAGE`): lower-third slides in and auto-dismisses.

- [ ] **Step 3: Verify kiosk + banner**
  - Kiosk (idle/ended): broadcast layout, no banner by default.
  - Set the dashboard event banner → kiosk shows it; clear it → hidden.
  - `Ctrl+Shift+O` staff override PIN pad works.

- [ ] **Step 4: Reduced motion**
  - Enable OS "reduce motion"; restart agent. Timers still update; no pulses/entrance animations.

- [ ] **Step 5: Final commit (if any polish landed)**

```bash
git add -A && git commit -m "chore(agent): broadcast overlay polish from smoke test"
```

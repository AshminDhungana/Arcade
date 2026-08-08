# PIN Dialog Keyboard Input Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let staff type PINs with a physical keyboard (digits, Backspace, Enter, Escape) in the agent's staff-override and settings-access dialogs, which today accept mouse clicks only.

**Architecture:** A shared helper (`pin-keyboard.ts`) binds a document-level `keydown` listener while a modal is visible and maps keys to callbacks; both PIN dialogs wire it into their existing `handleKey` flow. A one-line fix to `hideModal` makes the codebase's existing-but-dead `_cleanup` pattern actually run, eliminating listener leaks.

**Tech Stack:** TypeScript (ES2022, strict), Electron renderer (plain DOM, no framework), Vitest + jsdom.

## Global Constraints

- Follow the existing modal pattern: document-level `keydown` listener, `_cleanup` property typed as `(el as HTMLDivElement & { _cleanup?: () => void })._cleanup`.
- Ignore key events with `ctrlKey`, `altKey`, or `metaKey` (keeps `Ctrl+Shift+O` working in `index.ts`).
- Guard every dispatch on `modal.classList.contains('visible')` — hidden dialogs never consume keys.
- `preventDefault()` on Enter/NumpadEnter so a focused keypad button cannot double-submit.
- No CSS changes; dialog markup unchanged.
- Always require Enter to submit — no auto-submit at any PIN length.
- Backspace deletes the last digit; the on-screen `C` key keeps clearing all.
- Settings dialog: ignore all keyboard input while `onVerify` is pending.
- Tests use Vitest + jsdom with the `@vitest-environment jsdom` docblock, mirroring `agent/tests/renderer/components/low-time-warning.test.ts`.
- Pre-commit `end-of-file-fixer` may abort the first commit and fix the file itself; if so, re-run `git commit` unchanged.
- `docs/superpowers/` is gitignored — stage plan/spec commits with `git add -f`.

---

## File Structure

| File | Action | Responsibility |
|---|---|---|
| `agent/src/renderer/components/pin-keyboard.ts` | Create | Document keydown → PIN action mapping, cleanup fn |
| `agent/src/renderer/components/staff-override-dialog.ts` | Modify | Bind keyboard; Backspace action; Escape closes; cleanup on every close path |
| `agent/src/renderer/components/settings-pin-dialog.ts` | Modify | Replace inline ESC handler with helper; Backspace; input guard during verify |
| `agent/src/renderer/components/low-time-warning.ts` | Modify | `hideModal` invokes `_cleanup` (fixes dead pattern + leaks) |
| `agent/tests/renderer/components/pin-keyboard.test.ts` | Create | Helper behavior tests |
| `agent/tests/renderer/components/staff-override-dialog.test.ts` | Create | Dialog keyboard behavior tests |
| `agent/tests/renderer/components/settings-pin-dialog.test.ts` | Create | Dialog keyboard behavior tests |
| `agent/tests/renderer/components/low-time-warning.test.ts` | Modify | `hideModal` `_cleanup` test |

All test/verify commands run from the `agent/` directory: `cd agent`.

---

### Task 1: Shared keyboard helper `pin-keyboard.ts`

**Files:**
- Create: `agent/src/renderer/components/pin-keyboard.ts`
- Test: `agent/tests/renderer/components/pin-keyboard.test.ts`

**Interfaces:**
- Produces:
  ```ts
  export interface PinKeyboardCallbacks {
    onDigit: (digit: string) => void; // "0".."9"
    onBackspace: () => void;
    onSubmit: () => void;
    onCancel: () => void;
  }
  export function bindPinKeyboard(
    modal: HTMLElement,
    callbacks: PinKeyboardCallbacks
  ): () => void; // cleanup: removes the document keydown listener
  ```

- [ ] **Step 1: Write the failing test**

Create `agent/tests/renderer/components/pin-keyboard.test.ts`:

```ts
/**
 * @vitest-environment jsdom
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { bindPinKeyboard } from '../../../src/renderer/components/pin-keyboard.js';

function fireKey(key: string, init: KeyboardEventInit = {}): boolean {
  return document.dispatchEvent(new KeyboardEvent('keydown', { key, cancelable: true, ...init }));
}

function makeCallbacks() {
  return {
    onDigit: vi.fn(),
    onBackspace: vi.fn(),
    onSubmit: vi.fn(),
    onCancel: vi.fn(),
  };
}

describe('bindPinKeyboard', () => {
  let modal: HTMLElement;
  let cbs: ReturnType<typeof makeCallbacks>;

  beforeEach(() => {
    modal = document.createElement('div');
    modal.classList.add('visible');
    document.body.appendChild(modal);
    cbs = makeCallbacks();
  });

  afterEach(() => {
    document.body.innerHTML = '';
  });

  it('routes digit keys 0-9 to onDigit', () => {
    bindPinKeyboard(modal, cbs);
    for (const d of '0123456789') fireKey(d);
    expect(cbs.onDigit).toHaveBeenCalledTimes(10);
    expect(cbs.onDigit).toHaveBeenNthCalledWith(1, '0');
    expect(cbs.onDigit).toHaveBeenNthCalledWith(10, '9');
  });

  it('routes Backspace to onBackspace', () => {
    bindPinKeyboard(modal, cbs);
    fireKey('Backspace');
    expect(cbs.onBackspace).toHaveBeenCalledTimes(1);
  });

  it('routes Enter and NumpadEnter to onSubmit and prevents default', () => {
    bindPinKeyboard(modal, cbs);
    expect(fireKey('Enter')).toBe(false);
    expect(fireKey('NumpadEnter')).toBe(false);
    expect(cbs.onSubmit).toHaveBeenCalledTimes(2);
  });

  it('routes Escape to onCancel', () => {
    bindPinKeyboard(modal, cbs);
    fireKey('Escape');
    expect(cbs.onCancel).toHaveBeenCalledTimes(1);
  });

  it('ignores keys with ctrl/alt/meta modifiers', () => {
    bindPinKeyboard(modal, cbs);
    fireKey('5', { ctrlKey: true });
    fireKey('5', { altKey: true });
    fireKey('5', { metaKey: true });
    expect(cbs.onDigit).not.toHaveBeenCalled();
  });

  it('ignores keys when the modal is not visible', () => {
    modal.classList.remove('visible');
    bindPinKeyboard(modal, cbs);
    fireKey('5');
    expect(cbs.onDigit).not.toHaveBeenCalled();
  });

  it('ignores non-PIN keys (letters, function keys)', () => {
    bindPinKeyboard(modal, cbs);
    fireKey('a');
    fireKey('F5');
    fireKey('ArrowUp');
    expect(cbs.onDigit).not.toHaveBeenCalled();
    expect(cbs.onBackspace).not.toHaveBeenCalled();
    expect(cbs.onSubmit).not.toHaveBeenCalled();
    expect(cbs.onCancel).not.toHaveBeenCalled();
  });

  it('cleanup removes the listener', () => {
    const cleanup = bindPinKeyboard(modal, cbs);
    cleanup();
    fireKey('5');
    expect(cbs.onDigit).not.toHaveBeenCalled();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run tests/renderer/components/pin-keyboard.test.ts`
Expected: FAIL — `Error: No "bindPinKeyboard" export is defined on the "../../../src/renderer/components/pin-keyboard.js"` (module does not exist yet).

- [ ] **Step 3: Write the minimal implementation**

Create `agent/src/renderer/components/pin-keyboard.ts`:

```ts
/**
 * Physical-keyboard PIN entry helper — pure DOM helper.
 *
 * Listens for document-level keydown events while `modal` is visible and maps
 * digits/Backspace/Enter/Escape to PIN entry callbacks. Returns a cleanup
 * function that removes the listener.
 */

export interface PinKeyboardCallbacks {
  onDigit: (digit: string) => void;
  onBackspace: () => void;
  onSubmit: () => void;
  onCancel: () => void;
}

/** Bind keyboard PIN entry to a modal. Returns a cleanup function. */
export function bindPinKeyboard(
  modal: HTMLElement,
  callbacks: PinKeyboardCallbacks
): () => void {
  const handleKeyDown = (e: KeyboardEvent): void => {
    if (e.ctrlKey || e.altKey || e.metaKey) return;
    if (!modal.classList.contains('visible')) return;

    if (e.key >= '0' && e.key <= '9') {
      callbacks.onDigit(e.key);
    } else if (e.key === 'Backspace') {
      callbacks.onBackspace();
    } else if (e.key === 'Enter' || e.key === 'NumpadEnter') {
      e.preventDefault();
      callbacks.onSubmit();
    } else if (e.key === 'Escape') {
      callbacks.onCancel();
    }
  };

  document.addEventListener('keydown', handleKeyDown);
  return () => document.removeEventListener('keydown', handleKeyDown);
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run tests/renderer/components/pin-keyboard.test.ts`
Expected: PASS (8 tests).

- [ ] **Step 5: Commit**

```bash
git add agent/src/renderer/components/pin-keyboard.ts agent/tests/renderer/components/pin-keyboard.test.ts
git commit -m "feat: add shared keyboard PIN entry helper"
```

If the commit is aborted by `end-of-file-fixer`, re-run `git commit` unchanged. Verify with `git log --oneline -1`.

---

### Task 2: Keyboard input in the staff override dialog

**Files:**
- Modify: `agent/src/renderer/components/staff-override-dialog.ts`
- Test: `agent/tests/renderer/components/staff-override-dialog.test.ts`

**Interfaces:**
- Consumes: `bindPinKeyboard(modal, { onDigit, onBackspace, onSubmit, onCancel })` from `./pin-keyboard.js` (Task 1).
- Produces: `createStaffOverrideDialog(options)` unchanged signature. New behavior: digits/Backspace/Enter/Escape work while the modal is `visible`; Escape closes it; the keyboard listener is removed on every close path (cancel, escape, override submit).

- [ ] **Step 1: Write the failing test**

Create `agent/tests/renderer/components/staff-override-dialog.test.ts`:

```ts
/**
 * @vitest-environment jsdom
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { createStaffOverrideDialog } from '../../../src/renderer/components/staff-override-dialog.js';
import { showModal } from '../../../src/renderer/components/low-time-warning.js';

function fireKey(key: string, init: KeyboardEventInit = {}): void {
  document.dispatchEvent(new KeyboardEvent('keydown', { key, cancelable: true, ...init }));
}

describe('createStaffOverrideDialog keyboard input', () => {
  let onOverride: ReturnType<typeof vi.fn>;
  let onCancel: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    onOverride = vi.fn();
    onCancel = vi.fn();
  });

  afterEach(() => {
    document.body.innerHTML = '';
  });

  it('submits the typed PIN on Enter', () => {
    const modal = createStaffOverrideDialog({ onOverride, onCancel });
    showModal(modal);
    fireKey('1');
    fireKey('2');
    fireKey('3');
    fireKey('4');
    fireKey('Enter');
    expect(onOverride).toHaveBeenCalledWith('1234');
  });

  it('deletes the last digit on Backspace', () => {
    const modal = createStaffOverrideDialog({ onOverride, onCancel });
    showModal(modal);
    fireKey('1');
    fireKey('2');
    fireKey('3');
    fireKey('Backspace');
    fireKey('Enter');
    expect(onOverride).toHaveBeenCalledWith('12');
  });

  it('closes the dialog on Escape', () => {
    const modal = createStaffOverrideDialog({ onOverride, onCancel });
    showModal(modal);
    fireKey('1');
    fireKey('Escape');
    expect(onCancel).toHaveBeenCalled();
    expect(modal.classList.contains('visible')).toBe(false);
  });

  it('does not submit on Enter with an empty PIN', () => {
    const modal = createStaffOverrideDialog({ onOverride, onCancel });
    showModal(modal);
    fireKey('Enter');
    expect(onOverride).not.toHaveBeenCalled();
  });

  it('stops responding to keys after the dialog closes', () => {
    const modal = createStaffOverrideDialog({ onOverride, onCancel });
    showModal(modal);
    fireKey('Escape');
    fireKey('5');
    fireKey('Enter');
    expect(onOverride).not.toHaveBeenCalled();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run tests/renderer/components/staff-override-dialog.test.ts`
Expected: FAIL — typing digits then Enter never calls `onOverride` (no keyboard listener yet).

- [ ] **Step 3: Write the implementation**

Replace the entire contents of `agent/src/renderer/components/staff-override-dialog.ts` with:

```ts
/**
 * Staff override PIN dialog — pure DOM helper.
 *
 * Renders a numeric keypad for PIN entry.  On confirm, calls the
 * `onOverride` callback with the entered PIN.  Supports physical-keyboard
 * entry via `bindPinKeyboard` (digits, Backspace, Enter, Escape).
 */

import { ARCADE_ICON_SVG } from '../icon.js';
import { bindPinKeyboard } from './pin-keyboard.js';

export interface StaffOverrideOptions {
  onOverride: (pin: string) => void;
  onCancel?: () => void;
  onSettings?: () => void;
}

/** Build the staff-override modal element with a numeric keypad. */
export function createStaffOverrideDialog(options: StaffOverrideOptions): HTMLDivElement {
  const modal = document.createElement('div');
  modal.className = 'modal-overlay';
  modal.style.display = 'flex';

  modal.innerHTML = `
    <div class="modal-content">
      <div class="modal-title"><span class="modal-icon">${ARCADE_ICON_SVG}</span><span>Staff Override</span></div>
      <div class="modal-body">
        <p>Enter staff override PIN:</p>
        <div class="pin-display" id="pin-display"></div>
        <div class="pin-pad">
          <button data-key="1">1</button>
          <button data-key="2">2</button>
          <button data-key="3">3</button>
          <button data-key="4">4</button>
          <button data-key="5">5</button>
          <button data-key="6">6</button>
          <button data-key="7">7</button>
          <button data-key="8">8</button>
          <button data-key="9">9</button>
          <button data-key="C">Clear</button>
          <button data-key="0">0</button>
          <button data-key="✓">Enter</button>
        </div>
      </div>
      <div class="modal-actions">
        <button class="modal-btn secondary" id="override-cancel">Cancel</button>
        <button class="modal-btn primary" id="override-confirm">Override</button>
        <button class="modal-btn secondary" id="override-settings">Settings</button>
      </div>
    </div>
  `;

  let pin = '';
  const display = modal.querySelector<HTMLDivElement>('#pin-display')!;

  const updateDisplay = (): void => {
    display.textContent = pin.replace(/./g, '●');
  };

  // Physical-keyboard cleanup, assigned below; used by submit/closeModal.
  let keyboardCleanup: () => void = () => {};

  const submit = (): void => {
    if (pin.length === 0) return;
    options.onOverride(pin);
    pin = '';
    updateDisplay();
    keyboardCleanup();
  };

  const closeModal = (): void => {
    pin = '';
    updateDisplay();
    keyboardCleanup();
    options.onCancel?.();
    modal.classList.remove('visible');
    modal.style.display = 'none';
  };

  // Numeric keypad handler
  const handleKey = (key: string): void => {
    if (key === 'C') {
      pin = '';
    } else if (key === '✓') {
      submit();
      return;
    } else {
      pin += key;
    }
    updateDisplay();
  };

  // Physical-keyboard entry
  keyboardCleanup = bindPinKeyboard(modal, {
    onDigit: (digit) => handleKey(digit),
    onBackspace: () => {
      pin = pin.slice(0, -1);
      updateDisplay();
    },
    onSubmit: submit,
    onCancel: closeModal,
  });
  (modal as HTMLDivElement & { _cleanup?: () => void })._cleanup = keyboardCleanup;

  // Wire keypad buttons
  modal.querySelectorAll<HTMLButtonElement>('.pin-pad button').forEach((btn) => {
    btn.addEventListener('click', () => handleKey(btn.dataset.key || ''));
  });

  // Cancel button
  modal.querySelector<HTMLButtonElement>('#override-cancel')?.addEventListener('click', closeModal);

  // Confirm button
  modal.querySelector<HTMLButtonElement>('#override-confirm')?.addEventListener('click', submit);

  // Settings button
  modal.querySelector<HTMLButtonElement>('#override-settings')?.addEventListener('click', () => {
    options.onSettings?.();
  });

  return modal;
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run tests/renderer/components/staff-override-dialog.test.ts`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add agent/src/renderer/components/staff-override-dialog.ts agent/tests/renderer/components/staff-override-dialog.test.ts
git commit -m "feat: support keyboard input in staff override dialog"
```

Verify with `git log --oneline -1`.

---

### Task 3: Keyboard input in the settings PIN dialog

**Files:**
- Modify: `agent/src/renderer/components/settings-pin-dialog.ts`
- Test: `agent/tests/renderer/components/settings-pin-dialog.test.ts`

**Interfaces:**
- Consumes: `bindPinKeyboard(modal, { onDigit, onBackspace, onSubmit, onCancel })` from `./pin-keyboard.js` (Task 1).
- Produces: `createSettingsPinDialog(options)` unchanged signature. New behavior: digits/Backspace/Enter/Escape while visible; Enter runs the same verify path as the Unlock button (buttons disabled while pending, shake + clear on failure); Escape calls `onCancel` and closes; listener removed on every close path.

- [ ] **Step 1: Write the failing test**

Create `agent/tests/renderer/components/settings-pin-dialog.test.ts`:

```ts
/**
 * @vitest-environment jsdom
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { createSettingsPinDialog } from '../../../src/renderer/components/settings-pin-dialog.js';
import { showModal } from '../../../src/renderer/components/low-time-warning.js';

function fireKey(key: string, init: KeyboardEventInit = {}): void {
  document.dispatchEvent(new KeyboardEvent('keydown', { key, cancelable: true, ...init }));
}

describe('createSettingsPinDialog keyboard input', () => {
  let onCancel: ReturnType<typeof vi.fn>;
  let onSuccess: ReturnType<typeof vi.fn>;
  let onVerify: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    onCancel = vi.fn();
    onSuccess = vi.fn();
    onVerify = vi.fn().mockResolvedValue(true);
  });

  afterEach(() => {
    document.body.innerHTML = '';
  });

  it('verifies the typed PIN on Enter and hides on success', async () => {
    const modal = createSettingsPinDialog({ onVerify, onCancel, onSuccess });
    showModal(modal);
    fireKey('1');
    fireKey('2');
    fireKey('3');
    fireKey('4');
    fireKey('Enter');
    expect(onVerify).toHaveBeenCalledWith('1234');
    await onVerify.mock.results[0].value;
    expect(modal.classList.contains('visible')).toBe(false);
    expect(onSuccess).toHaveBeenCalled();
  });

  it('deletes the last digit on Backspace', async () => {
    const modal = createSettingsPinDialog({ onVerify, onCancel, onSuccess });
    showModal(modal);
    fireKey('1');
    fireKey('2');
    fireKey('3');
    fireKey('Backspace');
    fireKey('4');
    fireKey('Enter');
    expect(onVerify).toHaveBeenCalledWith('124');
    await onVerify.mock.results[0].value;
  });

  it('closes on Escape and calls onCancel', () => {
    const modal = createSettingsPinDialog({ onVerify, onCancel, onSuccess });
    showModal(modal);
    fireKey('1');
    fireKey('Escape');
    expect(onCancel).toHaveBeenCalled();
    expect(modal.classList.contains('visible')).toBe(false);
  });

  it('clears the PIN on a wrong PIN and keeps the dialog open', async () => {
    onVerify.mockResolvedValue(false);
    const modal = createSettingsPinDialog({ onVerify, onCancel, onSuccess });
    showModal(modal);
    fireKey('9');
    fireKey('Enter');
    await onVerify.mock.results[0].value;
    expect(modal.classList.contains('visible')).toBe(true);
    expect(onSuccess).not.toHaveBeenCalled();
    const display = modal.querySelector<HTMLDivElement>('#pin-display')!;
    expect(display.textContent).toBe('');
  });

  it('stops responding to keys after the dialog closes', () => {
    const modal = createSettingsPinDialog({ onVerify, onCancel, onSuccess });
    showModal(modal);
    fireKey('Escape');
    fireKey('5');
    fireKey('Enter');
    expect(onVerify).not.toHaveBeenCalled();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run tests/renderer/components/settings-pin-dialog.test.ts`
Expected: FAIL — Enter never verifies (no digit/Enter keyboard handling).

- [ ] **Step 3: Write the implementation**

Replace the entire contents of `agent/src/renderer/components/settings-pin-dialog.ts` with:

```ts
/**
 * Settings PIN dialog — pure DOM helper.
 * Reuses staff-override-dialog keypad style for Settings access PIN entry.
 * Supports physical-keyboard entry via `bindPinKeyboard`.
 */

import { ARCADE_ICON_SVG } from '../icon.js';
import { bindPinKeyboard } from './pin-keyboard.js';

export interface SettingsPinDialogOptions {
  onVerify: (pin: string) => Promise<boolean>;
  onCancel: () => void;
  onSuccess?: () => void;
}

export function createSettingsPinDialog(options: SettingsPinDialogOptions): HTMLDivElement {
  const { onVerify, onCancel, onSuccess } = options;

  const modal = document.createElement('div');
  modal.className = 'modal-overlay';
  modal.style.display = 'flex';

  modal.innerHTML = `
    <div class="modal-content">
      <div class="modal-title"><span class="modal-icon">${ARCADE_ICON_SVG}</span><span>Settings Access</span></div>
      <div class="modal-body">
        <p>Enter staff override PIN to access settings:</p>
        <div class="pin-display" id="pin-display"></div>
        <div class="pin-pad">
          <button data-key="1">1</button>
          <button data-key="2">2</button>
          <button data-key="3">3</button>
          <button data-key="4">4</button>
          <button data-key="5">5</button>
          <button data-key="6">6</button>
          <button data-key="7">7</button>
          <button data-key="8">8</button>
          <button data-key="9">9</button>
          <button data-key="C">Clear</button>
          <button data-key="0">0</button>
          <button data-key="✓" id="pin-confirm">Unlock</button>
        </div>
      </div>
    </div>
  `;

  let pin = '';
  const display = modal.querySelector<HTMLDivElement>('#pin-display')!;
  const confirmBtn = modal.querySelector<HTMLButtonElement>('#pin-confirm')!;

  const updateDisplay = (): void => {
    display.textContent = pin.replace(/./g, '●');
  };

  // Physical-keyboard cleanup, assigned below; used by closeModal.
  let keyboardCleanup: () => void = () => {};

  const closeModal = (): void => {
    pin = '';
    updateDisplay();
    keyboardCleanup();
    modal.classList.remove('visible');
    modal.style.display = 'none';
  };

  const handleKey = (key: string): void => {
    if (confirmBtn.disabled) return; // ignore input while verification is pending
    if (key === 'C') {
      pin = '';
    } else if (key === '✓') {
      if (pin.length === 0) return;
      // Disable buttons during verification
      confirmBtn.disabled = true;
      modal.querySelectorAll<HTMLButtonElement>('.pin-pad button').forEach(btn => btn.disabled = true);

      onVerify(pin).then((success) => {
        confirmBtn.disabled = false;
        modal.querySelectorAll<HTMLButtonElement>('.pin-pad button').forEach(btn => btn.disabled = false);

        if (success) {
          closeModal();
          onSuccess?.();
        } else {
          // Wrong PIN: shake animation
          modal.querySelector('.modal-content')?.classList.add('shake');
          setTimeout(() => {
            modal.querySelector('.modal-content')?.classList.remove('shake');
          }, 300);
          pin = '';
          updateDisplay();
        }
      });
      return;
    } else {
      pin += key;
    }
    updateDisplay();
  };

  // Physical-keyboard entry
  keyboardCleanup = bindPinKeyboard(modal, {
    onDigit: (digit) => handleKey(digit),
    onBackspace: () => {
      pin = pin.slice(0, -1);
      updateDisplay();
    },
    onSubmit: () => handleKey('✓'),
    onCancel: () => {
      onCancel();
      closeModal();
    },
  });
  (modal as HTMLDivElement & { _cleanup?: () => void })._cleanup = keyboardCleanup;

  // Wire keypad buttons
  modal.querySelectorAll<HTMLButtonElement>('.pin-pad button').forEach((btn) => {
    btn.addEventListener('click', () => handleKey(btn.dataset.key || ''));
  });

  // Cancel on backdrop click
  modal.addEventListener('click', (e) => {
    if (e.target === modal) {
      onCancel();
      closeModal();
    }
  });

  return modal;
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run tests/renderer/components/settings-pin-dialog.test.ts`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add agent/src/renderer/components/settings-pin-dialog.ts agent/tests/renderer/components/settings-pin-dialog.test.ts
git commit -m "feat: support keyboard input in settings pin dialog"
```

Verify with `git log --oneline -1`.

---

### Task 4: `hideModal` invokes `_cleanup`

**Files:**
- Modify: `agent/src/renderer/components/low-time-warning.ts:90-97`
- Test: `agent/tests/renderer/components/low-time-warning.test.ts`

**Interfaces:**
- Consumes: the existing `_cleanup?: () => void` property set by dialogs (already set by `settings-pin-dialog.ts` and `settings-panel.ts`).
- Produces: `hideModal(el)` also calls `(el as HTMLDivElement & { _cleanup?: () => void })._cleanup?.()` before hiding, so modal-owned document listeners (ESC/keyboard) are always removed.

- [ ] **Step 1: Write the failing test**

Append this test inside the existing `describe('showModal / hideModal')` block in `agent/tests/renderer/components/low-time-warning.test.ts`:

```ts
  it('calls _cleanup when present on hide', () => {
    const modal = document.createElement('div');
    modal.className = 'modal-overlay';
    const cleanup = vitest.fn();
    (modal as HTMLDivElement & { _cleanup?: () => void })._cleanup = cleanup;
    document.body.appendChild(modal);

    showModal(modal);
    hideModal(modal);

    expect(cleanup).toHaveBeenCalled();
    document.body.innerHTML = '';
  });
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run tests/renderer/components/low-time-warning.test.ts`
Expected: FAIL — `cleanup` is never called by the current `hideModal`.

- [ ] **Step 3: Write the implementation**

In `agent/src/renderer/components/low-time-warning.ts`, change `hideModal` to:

```ts
/** Hide a modal element with an opacity transition and remove from DOM. */
export function hideModal(el: HTMLDivElement): void {
  (el as HTMLDivElement & { _cleanup?: () => void })._cleanup?.();
  el.classList.remove('visible');
  setTimeout(() => {
    el.style.display = 'none';
    if (el.parentNode) {
      el.parentNode.removeChild(el);
    }
  }, 300);
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run tests/renderer/components/low-time-warning.test.ts`
Expected: PASS (4 tests, including the new one).

- [ ] **Step 5: Commit**

```bash
git add agent/src/renderer/components/low-time-warning.ts agent/tests/renderer/components/low-time-warning.test.ts
git commit -m "fix: hideModal invokes modal _cleanup to release key listeners"
```

Verify with `git log --oneline -1`.

---

### Task 5: Full verification

**Files:** none (verification only)

- [ ] **Step 1: Run the full renderer component test suite**

Run: `npx vitest run tests/renderer`
Expected: PASS — all tests including the new `pin-keyboard`, `staff-override-dialog`, and `settings-pin-dialog` suites and the extended `low-time-warning` suite.

- [ ] **Step 2: Typecheck the renderer**

Run: `npx tsc -p tsconfig.renderer.json --noEmit`
Expected: No errors.

- [ ] **Step 3: Lint**

Run: `npm run lint`
Expected: No errors or warnings (`eslint` covers `src/`, which includes all three modified/created source files).

- [ ] **Step 4: Manual smoke check (optional but recommended)**

Run: `npm start` in `agent/`, press `Ctrl+Shift+O`, and verify:
1. Typing `1234` with the physical keyboard fills the PIN dots.
2. `Backspace` deletes one digit; `C` still clears all.
3. `Enter` submits; `Escape` closes the dialog.
4. From the override dialog, open Settings → the PIN dialog accepts the same keyboard input; wrong PIN shakes and clears.

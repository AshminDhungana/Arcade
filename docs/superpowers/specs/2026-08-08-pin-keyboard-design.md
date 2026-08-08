# PIN Dialog Keyboard Input — Design

**Date:** 2026-08-08
**Status:** Approved
**Scope:** Support physical-keyboard PIN entry in the agent's staff-override and settings-access PIN dialogs (mouse-only today).

## Problem

The agent renderer shows two PIN entry dialogs, both with an on-screen numeric
keypad that only accepts mouse clicks:

- Staff override (`agent/src/renderer/components/staff-override-dialog.ts`,
  opened via `Ctrl+Shift+O`)
- Settings access (`agent/src/renderer/components/settings-pin-dialog.ts`,
  opened from the override dialog's "Settings" button)

Staff with a physical keyboard cannot type the PIN — they must click each digit.
Requirement: digits, Backspace (delete last digit), Enter (submit), and Escape
(close/cancel) must work via keyboard in both dialogs.

## Current behavior (verified in code)

Both dialogs share the same structure: `.pin-display` (bullet dots) + `.pin-pad`
grid of buttons with `data-key` (`0`–`9`, `C` = clear-all, `✓` = submit) and a
`handleKey(key)` function. Buttons are wired with `click` listeners only.

- `settings-pin-dialog.ts` already has a document-level `keydown` listener for
  Escape only. Its cleanup is buggy: the listener is removed only when Escape is
  pressed, not on success or backdrop-close (listener leak).
- `staff-override-dialog.ts` has no keyboard handling at all.
- Existing keyboard pattern: document-level `keydown` + `_cleanup` property on
  the modal element (used in `settings-pin-dialog.ts` and `settings-panel.ts`).

## Design (Approach A: shared keyboard helper)

### 1. New module: `agent/src/renderer/components/pin-keyboard.ts`

Exports:

```ts
export interface PinKeyboardCallbacks {
  onDigit: (digit: string) => void; // "0".."9"
  onBackspace: () => void;          // delete last digit
  onSubmit: () => void;             // Enter / NumpadEnter
  onCancel: () => void;             // Escape
}

export function bindPinKeyboard(
  modal: HTMLElement,
  callbacks: PinKeyboardCallbacks
): () => void; // returns cleanup
```

Behavior:

- Registers one document-level `keydown` listener.
- `e.key` of `0`–`9` (layout-aware; numpad digits report the digit as `e.key`)
  → `onDigit`.
- `Backspace` → `onBackspace`.
- `Enter` / `NumpadEnter` → `onSubmit`, with `preventDefault()` so a focused
  keypad button does not also fire `click` (double submit).
- `Escape` → `onCancel`.
- Events with `ctrlKey`, `altKey`, or `metaKey` set are ignored, so
  `Ctrl+Shift+O` (handled by a separate listener in `index.ts`) keeps working.
- Guards on `modal.classList.contains('visible')` — a hidden dialog never
  consumes keys.
- Returns a cleanup function that removes the listener; the dialog stores it on
  the modal as `_cleanup` and invokes it on every close path (see below).

Note: `_cleanup` is currently dead code in this codebase — set by
`settings-pin-dialog.ts` and `settings-panel.ts` but never invoked, because
`hideModal` (`low-time-warning.ts:90`) does not call it and the settings
dialog's inline cancel paths never call `hideModal`. The ESC listeners in those
components genuinely leak. This design fixes that.

### 2. `staff-override-dialog.ts`

- Call `bindPinKeyboard` on creation with `handleKey`-compatible callbacks:
  - `onDigit(d)` → `handleKey(d)`
  - `onBackspace()` → `pin = pin.slice(0, -1)` + update display (new internal
    action; the on-screen pad keeps `C` = clear-all)
  - `onSubmit()` → same submit path as the `✓` button (`onOverride(pin)` when
    `pin` is non-empty)
  - `onCancel()` → same path as the Cancel button (clears PIN, calls
    `options.onCancel()`, hides modal)
- This adds Escape-to-close, which the dialog does not have today.
- Every close path (Escape, Cancel button, Override submit) invokes the
  `bindPinKeyboard` cleanup.

### 3. `settings-pin-dialog.ts`

- Replace the inline `handleEsc` with `bindPinKeyboard`:
  - `onDigit` / `onBackspace` as above
  - `onSubmit()` → same path as the `✓` button: disables pad + confirm button,
    runs `onVerify(pin)`, re-enables on completion, shake + clear on failure,
    close + `onSuccess` on success
  - `onCancel()` → same path as backdrop-close / existing Escape (clear PIN,
    hide, call `onCancel()`)
- Fixes the pre-existing leak: the `bindPinKeyboard` cleanup runs on every
  close path (success, cancel, backdrop, Escape).

### 4. Targeted fix: `hideModal` invokes `_cleanup`

`hideModal` (`low-time-warning.ts:90`) gains one line: `(el as any)._cleanup?.()`.
The `_cleanup` property is already set by `settings-pin-dialog.ts` and
`settings-panel.ts`; today nothing invokes it, so their document-level ESC
listeners leak on every open/close cycle. This makes the existing pattern work
and keeps future modals safe.

### Edge cases

- Backspace on an empty PIN → no-op.
- Enter with an empty PIN → no-op (same as the `✓` button today).
- Key repeat while holding a key works naturally.
- While `onVerify` is pending, keyboard input is ignored (pad buttons are
  already disabled; the submit path re-checks the disabled state).
- Both dialogs unchanged in appearance; no CSS changes.

### Testing

Vitest + jsdom, following the pattern in
`agent/tests/renderer/components/low-time-warning.test.ts`:

- New `agent/tests/renderer/components/pin-keyboard.test.ts`:
  - Dispatch `keydown` with digits, numpad digits → `onDigit` with correct value
  - `Backspace`, `Enter`, `NumpadEnter`, `Escape` → correct callbacks
  - Ctrl/Alt/Meta-modified events ignored
  - Events while modal lacks `visible` class are ignored
  - Cleanup function removes the listener
- New/extended dialog tests:
  - `staff-override-dialog`: Enter submits (`onOverride` called with PIN),
    Backspace deletes last digit, Escape closes
  - `settings-pin-dialog`: Enter triggers verify path, Escape closes
- `low-time-warning.test.ts`: `hideModal` invokes `_cleanup` when present

## Out of scope

- Auto-submit at any PIN length (always requires Enter, matching mouse UX).
- Visual highlight of keypad buttons on keypress (PIN dots are sufficient).
- Keyboard support for other modals (low-time warning, settings panel).

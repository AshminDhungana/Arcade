# Kiosk Override Settings PIN Flow Completion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the Settings PIN flow by adding an `onSuccess` callback to the Settings PIN dialog that opens the Settings panel after successful PIN verification.

**Architecture:** Two targeted changes - add optional `onSuccess` callback to `SettingsPinDialogOptions` interface and call it on verification success; wire it in `renderer/index.ts` to create and show the `SettingsPanel` with current config.

**Tech Stack:** TypeScript, Vitest, Electron renderer process (plain DOM, no framework)

## Global Constraints

- No new dependencies
- Reuse existing `verifySettingsPin` IPC and backend `triggerSettingsPinVerify` (verifies against `override_code_hash` via Argon2id)
- Settings PIN = Staff Override PIN (same hash)
- Master PIN (emergency, offline-only) NOT accepted for Settings access
- Follow existing code style: plain DOM, ES modules, vitest with jsdom
- No new components - only wiring existing ones

---

### Task 1: Add `onSuccess` Callback to Settings PIN Dialog

**Files:**
- Modify: `agent/src/renderer/components/settings-pin-dialog.ts`
- Test: `agent/tests/renderer/components/settings-pin-dialog.test.ts`

**Interfaces:**
- Consumes: `SettingsPinDialogOptions.onSuccess?: () => void` (new optional callback)
- Produces: Call to `options.onSuccess?.()` after successful PIN verification (before modal close)

- [ ] **Step 1.1: Read current implementation**

```bash
cat agent/src/renderer/components/settings-pin-dialog.ts
```

- [ ] **Step 1.2: Write failing test for `onSuccess` callback**

```bash
cat > /tmp/test_onSuccess.ts << 'EOF'
import { describe, it, expect, vi } from 'vitest';
import { createSettingsPinDialog } from '../../../src/renderer/components/settings-pin-dialog.js';

describe('createSettingsPinDialog - onSuccess callback', () => {
  it('calls onSuccess when PIN verification succeeds', async () => {
    const onVerify = vi.fn().mockResolvedValue(true);
    const onCancel = vi.fn();
    const onSuccess = vi.fn();
    const modal = createSettingsPinDialog({ onVerify, onCancel, onSuccess });
    document.body.appendChild(modal);

    // Enter PIN: 1-2-3-4
    modal.querySelector<HTMLButtonElement>('[data-key="1"]')?.click();
    modal.querySelector<HTMLButtonElement>('[data-key="2"]')?.click();
    modal.querySelector<HTMLButtonElement>('[data-key="3"]')?.click();
    modal.querySelector<HTMLButtonElement>('[data-key="4"]')?.click();
    // Click Unlock
    modal.querySelector<HTMLButtonElement>('#pin-confirm')?.click();

    // Wait for async verification
    await new Promise(r => setTimeout(r, 10));

    expect(onSuccess).toHaveBeenCalled();
    document.body.innerHTML = '';
  });

  it('does NOT call onSuccess when PIN verification fails', async () => {
    const onVerify = vi.fn().mockResolvedValue(false);
    const onCancel = vi.fn();
    const onSuccess = vi.fn();
    const modal = createSettingsPinDialog({ onVerify, onCancel, onSuccess });
    document.body.appendChild(modal);

    modal.querySelector<HTMLButtonElement>('[data-key="1"]')?.click();
    modal.querySelector<HTMLButtonElement>('#pin-confirm')?.click();

    await new Promise(r => setTimeout(r, 10));

    expect(onSuccess).not.toHaveBeenCalled();
    document.body.innerHTML = '';
  });

  it('works when onSuccess is not provided', async () => {
    const onVerify = vi.fn().mockResolvedValue(true);
    const onCancel = vi.fn();
    const modal = createSettingsPinDialog({ onVerify, onCancel });
    document.body.appendChild(modal);

    modal.querySelector<HTMLButtonElement>('[data-key="1"]')?.click();
    modal.querySelector<HTMLButtonElement>('#pin-confirm')?.click();

    await new Promise(r => setTimeout(r, 10));

    // Should not throw
    document.body.innerHTML = '';
  });
});
EOF
```

Run test to verify it fails:
```bash
cd agent && npx vitest run tests/renderer/components/settings-pin-dialog.test.ts -t "onSuccess callback"
```
Expected: FAIL (onSuccess not yet implemented)

- [ ] **Step 1.3: Modify `settings-pin-dialog.ts` to add `onSuccess` to interface and call it**

```typescript
// agent/src/renderer/components/settings-pin-dialog.ts
// Line 8-11: Update interface
export interface SettingsPinDialogOptions {
  onVerify: (pin: string) => Promise<boolean>;
  onCancel: () => void;
  onSuccess?: () => void;  // ADD THIS LINE
}

// Line 13-14: Destructure onSuccess
const { onVerify, onCancel, onSuccess } = options;

// Lines 61-69: Call onSuccess after successful verification
onVerify(pin).then((success) => {
  confirmBtn.disabled = false;
  modal.querySelectorAll<HTMLButtonElement>('.pin-pad button').forEach(btn => btn.disabled = false);

  if (success) {
    pin = '';
    updateDisplay();
    modal.classList.remove('visible');
    modal.style.display = 'none';
    onSuccess?.();  // ADD THIS LINE
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
```

- [ ] **Step 1.4: Run test to verify it passes**

```bash
cd agent && npx vitest run tests/renderer/components/settings-pin-dialog.test.ts -t "onSuccess callback"
```
Expected: PASS

- [ ] **Step 1.5: Run full test suite for this component**

```bash
cd agent && npx vitest run tests/renderer/components/settings-pin-dialog.test.ts
```
Expected: All tests PASS

- [ ] **Step 1.6: Commit**

```bash
git add agent/src/renderer/components/settings-pin-dialog.ts agent/tests/renderer/components/settings-pin-dialog.test.ts
git commit -m "feat(kiosk): add onSuccess callback to Settings PIN dialog"
```

---

### Task 2: Wire `onSuccess` in Renderer to Show Settings Panel

**Files:**
- Modify: `agent/src/renderer/index.ts`

**Interfaces:**
- Consumes: `createSettingsPinDialog` with `onSuccess` callback, `createSettingsPanel` with `config`, `onReEnroll`, `onClose`
- Produces: Settings panel shown after successful PIN verification

- [ ] **Step 2.1: Read current `onSettings` callback in index.ts**

```bash
cat agent/src/renderer/index.ts
```

- [ ] **Step 2.2: Modify `onSettings` callback to provide `onSuccess` that shows Settings panel**

```typescript
// agent/src/renderer/index.ts
// Around lines 104-119, update the onSettings callback:
onSettings: () => {
  if (!currentConfig) {
    overlay.showAnnouncement('Settings unavailable', 2000);
    return;
  }
  const pinDialog = createSettingsPinDialog({
    onVerify: async (pin: string) => {
      const success = await window.electronAPI.verifySettingsPin(pin);
      return success;
    },
    onCancel: () => {
      // PIN dialog cancelled, return to override dialog
    },
    onSuccess: () => {
      // Create and show Settings panel
      const settingsPanel = createSettingsPanel({
        config: {
          serverUrl: currentConfig.serverUrl,
          seatId: currentConfig.seatId,
          agentSecret: currentConfig.agentSecret,
        },
        onReEnroll: () => {
          window.electronAPI.enroll(''); // Triggers re-enrollment flow
        },
        onClose: () => {
          // Settings panel closed, return to kiosk overlay
        },
      });
      showModal(settingsPanel);
    },
  });
  showModal(pinDialog);
},
```

- [ ] **Step 2.3: Verify TypeScript compiles**

```bash
cd agent && npx tsc --noEmit
```
Expected: No errors

- [ ] **Step 2.4: Run full test suite**

```bash
cd agent && npx vitest run
```
Expected: All tests PASS

- [ ] **Step 2.5: Build agent**

```bash
cd agent && npm run build
```
Expected: Build succeeds

- [ ] **Step 2.6: Commit**

```bash
git add agent/src/renderer/index.ts
git commit -m "feat(kiosk): wire Settings PIN success to show Settings panel"
```

---

### Task 3: Manual/Integration Verification

**Files:** None (verification only)

- [ ] **Step 3.1: Verify end-to-end flow manually**

Launch agent in dev mode (`npm run start` in agent directory), press `Ctrl+Shift+O`, click Settings, enter correct PIN, verify Settings panel opens with server URL, seat ID, masked agent secret, Re-enroll/Close buttons.

- [ ] **Step 3.2: Verify incorrect PIN behavior**

Enter incorrect PIN → shake animation, PIN cleared, stays on PIN dialog.

- [ ] **Step 3.3: Verify Close/ESC behavior**

Cancel/ESC on PIN dialog → returns to Staff Override dialog.
Settings panel Close/ESC → returns to kiosk overlay.

- [ ] **Step 3.4: Commit any additional fixes**

```bash
git add -A
git commit -m "chore: verify build and tests pass after Settings panel wiring"
```

---

## Acceptance Criteria Verification

After implementation, manually verify:

1. Press `Ctrl+Shift+O` → Staff Override dialog opens
2. Settings button is **enabled** (not greyed out) ✓
3. Click Settings → Settings PIN dialog appears ("Enter staff override PIN to access settings") ✓
4. Enter correct PIN → **Settings panel appears** (server URL, seat ID, masked agent secret, Re-enroll/Close) ✓
5. Enter incorrect PIN → shake animation, PIN cleared, stays on PIN dialog ✓
6. Cancel/ESC on PIN dialog → returns to Staff Override dialog ✓
7. Settings panel Close/ESC → returns to kiosk overlay ✓

---

## Summary

**Total changes:** 2 files modified
- `agent/src/renderer/components/settings-pin-dialog.ts` - Add `onSuccess` callback to interface and call it on success
- `agent/src/renderer/index.ts` - Wire `onSuccess` to create and show Settings panel

**Test updates:** 1 test file modified
- `agent/tests/renderer/components/settings-pin-dialog.test.ts` - Add tests for `onSuccess` callback

**No new components** - only wiring existing verified components.
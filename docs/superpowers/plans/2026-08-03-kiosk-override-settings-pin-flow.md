# Kiosk Override Settings PIN Flow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enable the Settings button in the Staff Override dialog by default, allowing staff to click Settings → enter PIN → access Settings panel without first entering the override PIN.

**Architecture:** Single-file change in the Staff Override dialog component to remove the disabled state on the Settings button. The existing Settings PIN dialog and Settings panel already handle PIN verification and display. Test updated to reflect new behavior.

**Tech Stack:** TypeScript, Vitest, Electron renderer process (plain DOM, no framework)

## Global Constraints

- No new dependencies
- Reuse existing `verifySettingsPin` IPC and backend `triggerSettingsPinVerify` (verifies against `override_code_hash` via Argon2id)
- Settings PIN = Staff Override PIN (same hash)
- Master PIN (emergency, offline-only) NOT accepted for Settings access
- Follow existing code style: plain DOM, ES modules, vitest with jsdom

---

### Task 1: Update Staff Override Dialog - Enable Settings Button

**Files:**
- Modify: `agent/src/renderer/components/staff-override-dialog.ts`
- Test: `agent/tests/renderer/components/staff-override-dialog.test.ts`

**Interfaces:**
- Consumes: `StaffOverrideOptions.onSettings` callback (already exists)
- Produces: Settings button clickable immediately on dialog open

- [ ] **Step 1.1: Read current implementation**

```bash
cat agent/src/renderer/components/staff-override-dialog.ts
```

- [ ] **Step 1.2: Write failing test for new behavior**

```bash
cat > /tmp/test_new_behavior.ts << 'EOF'
import { describe, it, expect, vi } from 'vitest';
import { createStaffOverrideDialog } from '../../../src/renderer/components/staff-override-dialog.js';

describe('createStaffOverrideDialog - new behavior', () => {
  it('Settings button is enabled by default (no PIN required)', () => {
    const onSettings = vi.fn();
    const modal = createStaffOverrideDialog({ onOverride: vi.fn(), onSettings });
    document.body.appendChild(modal);

    const settingsBtn = modal.querySelector<HTMLButtonElement>('#override-settings');
    expect(settingsBtn?.disabled).toBe(false);

    // Click Settings immediately - should call onSettings
    settingsBtn?.click();
    expect(onSettings).toHaveBeenCalled();

    document.body.innerHTML = '';
  });
});
EOF
```

Run test to verify it fails with current code:
```bash
cd agent && npx vitest run tests/renderer/components/staff-override-dialog.test.ts -t "Settings button is enabled by default"
```
Expected: FAIL (Settings button currently disabled)

- [ ] **Step 1.3: Modify staff-override-dialog.ts to enable Settings button**

```typescript
// agent/src/renderer/components/staff-override-dialog.ts
// Find the Settings button wiring (around line 99-101)
// REMOVE or COMMENT OUT any code that sets settingsBtn.disabled = true

// Current code to remove:
// const settingsBtn = modal.querySelector<HTMLButtonElement>('#override-settings');
// settingsBtn.disabled = true;

// The button should just work - no disabled state initialization needed
```

Specifically, remove lines that disable the Settings button. The button HTML already exists in the template (line 46), and the click handler (lines 99-101) already calls `options.onSettings?.()`.

- [ ] **Step 1.4: Run test to verify it passes**

```bash
cd agent && npx vitest run tests/renderer/components/staff-override-dialog.test.ts -t "Settings button is enabled by default"
```
Expected: PASS

- [ ] **Step 1.5: Run full test suite for this component**

```bash
cd agent && npx vitest run tests/renderer/components/staff-override-dialog.test.ts
```
Expected: All tests PASS (including updated existing test)

- [ ] **Step 1.6: Update existing test "Settings button is disabled until correct PIN entered"**

The existing test at lines 71-95 expects Settings button disabled initially. Update it to match new behavior:

```typescript
// agent/tests/renderer/components/staff-override-dialog.test.ts
// REPLACE the test "Settings button is disabled until correct PIN entered" (lines 71-95)
// WITH a test that verifies Settings button works immediately

it('Settings button is enabled by default and calls onSettings', () => {
  const onOverride = vi.fn();
  const onSettings = vi.fn();
  const modal = createStaffOverrideDialog({ onOverride, onSettings });
  document.body.appendChild(modal);

  const settingsBtn = modal.querySelector<HTMLButtonElement>('#override-settings');
  expect(settingsBtn?.disabled).toBe(false);

  // Click Settings immediately - should call onSettings without any PIN entry
  settingsBtn?.click();
  expect(onSettings).toHaveBeenCalled();

  document.body.innerHTML = '';
});
```

- [ ] **Step 1.7: Run all tests again to verify**

```bash
cd agent && npx vitest run tests/renderer/components/staff-override-dialog.test.ts
```
Expected: All tests PASS

- [ ] **Step 1.8: Commit**

```bash
git add agent/src/renderer/components/staff-override-dialog.ts agent/tests/renderer/components/staff-override-dialog.test.ts
git commit -m "feat(kiosk): enable Settings button by default in Staff Override dialog"
```

---

### Task 2: Verify End-to-End Flow (Manual/Integration)

**Files:** None (verification only)

- [ ] **Step 2.1: Build agent**

```bash
cd agent && npm run build
```
Expected: Build succeeds

- [ ] **Step 2.2: Verify no TypeScript errors**

```bash
cd agent && npx tsc --noEmit
```
Expected: No errors

- [ ] **Step 2.3: Run full test suite**

```bash
cd agent && npx vitest run
```
Expected: All tests PASS

- [ ] **Step 2.4: Commit any additional fixes**

```bash
git add -A
git commit -m "chore: verify build and tests pass after Settings button change"
```

---

## Acceptance Criteria Verification

After implementation, manually verify:

1. Press `Ctrl+Shift+O` → Staff Override dialog opens
2. Settings button is **enabled** (not greyed out) ✓
3. Click Settings → Settings PIN dialog appears ("Enter staff override PIN to access settings") ✓
4. Enter correct PIN → Settings panel appears (server URL, seat ID, masked agent secret, Re-enroll/Close) ✓
5. Enter incorrect PIN → shake animation, PIN cleared, stays on PIN dialog ✓
6. Cancel/ESC on PIN dialog → returns to Staff Override dialog ✓
7. Settings panel Close/ESC → returns to kiosk overlay ✓

Items 3-7 already work - they use existing `settings-pin-dialog.ts`, `settings-panel.ts`, and wiring in `renderer/index.ts`.

---

## Summary

**Total changes:** 2 files modified
- `agent/src/renderer/components/staff-override-dialog.ts` - Remove disabled state on Settings button
- `agent/tests/renderer/components/staff-override-dialog.test.ts` - Update test to expect enabled button

**No new code** - only removing the logic that disabled the button. All downstream components (Settings PIN dialog, Settings panel, IPC, backend verification) already exist and work correctly.
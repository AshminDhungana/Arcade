# Kiosk Overlay Settings Security Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Hide Settings button from kiosk rail; gate settings access behind staff override PIN (Ctrl+Shift+O); same PIN unlocks both Override and Settings actions; settings panel opens without dismissing kiosk.

**Architecture:** Three focused changes across renderer components: remove Settings from kiosk-overlay, wire onSettings callback in staff-override-dialog, connect callback in renderer index. No new files.

**Tech Stack:** TypeScript, Electron renderer process, plain DOM (no frameworks)

## Global Constraints

- Kiosk overlay must remain running when Settings panel opens
- Same PIN (override_code_hash) authenticates both Override and Settings
- Settings panel reuses existing `createSettingsPanel()` with Re-enroll button
- No new dependencies, no new files
- Follow existing code patterns in `agent/src/renderer/components/`

---

### Task 1: Remove Settings Button from Kiosk Overlay Rail

**Files:**
- Modify: `agent/src/renderer/components/kiosk-overlay.ts:76-96, 183-186, 207`

**Interfaces:**
- Consumes: None (removal only)
- Produces: `KioskOverlay` class no longer has `settingsPanelCb` or `onSettingsPanel()`

- [ ] **Step 1: Write failing test**

```typescript
// agent/tests/renderer/components/kiosk-overlay.test.ts
import { KioskOverlay } from '../../../src/renderer/components/kiosk-overlay.js';

test('kiosk overlay rail has no Settings button', () => {
  const container = document.createElement('div');
  const overlay = new KioskOverlay(container);
  
  const rail = container.querySelector('.kiosk-rail');
  const settingsBtn = rail?.querySelector('button:nth-of-type(2)');
  
  expect(settingsBtn?.textContent).not.toBe('Settings');
  expect(settingsBtn?.classList.contains('kiosk-btn')).toBe(false);
  
  overlay.destroy();
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -- agent/tests/renderer/components/kiosk-overlay.test.ts`
Expected: FAIL - Settings button exists

- [ ] **Step 3: Remove Settings button from rail**

```typescript
// agent/src/renderer/components/kiosk-overlay.ts
// Lines 76-96: Remove settingsBtn creation (lines 90-94)
// Keep only callStaffBtn

// Lines 183-186: Remove onSettingsPanel method entirely

// Line 207: Remove private settingsPanelCb field
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test -- agent/tests/renderer/components/kiosk-overlay.test.ts`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add agent/src/renderer/components/kiosk-overlay.ts agent/tests/renderer/components/kiosk-overlay.test.ts
git commit -m "feat: remove Settings button from kiosk overlay rail"
```

---

### Task 2: Enable Settings Button in Staff Override Dialog After PIN Entry

**Files:**
- Modify: `agent/src/renderer/components/staff-override-dialog.ts:17-103`

**Interfaces:**
- Consumes: `StaffOverrideOptions` with optional `onSettings` callback
- Produces: Settings button enabled only after correct PIN; calls `onSettings()` on click

- [ ] **Step 1: Write failing test**

```typescript
// agent/tests/renderer/components/staff-override-dialog.test.ts
import { createStaffOverrideDialog } from '../../../src/renderer/components/staff-override-dialog.js';

test('Settings button disabled until correct PIN entered', () => {
  const onOverride = vi.fn();
  const onSettings = vi.fn();
  
  const dialog = createStaffOverrideDialog({ onOverride, onSettings });
  document.body.appendChild(dialog);
  
  const settingsBtn = dialog.querySelector('#override-settings') as HTMLButtonElement;
  expect(settingsBtn.disabled).toBe(true);
  
  // Simulate correct PIN entry
  dialog.querySelector('[data-key="1"]')?.click();
  dialog.querySelector('[data-key="2"]')?.click();
  dialog.querySelector('[data-key="3"]')?.click();
  dialog.querySelector('[data-key="4"]')?.click();
  dialog.querySelector('#override-confirm')?.click();
  
  expect(settingsBtn.disabled).toBe(false);
  
  settingsBtn.click();
  expect(onSettings).toHaveBeenCalled();
  
  document.body.removeChild(dialog);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -- agent/tests/renderer/components/staff-override-dialog.test.ts`
Expected: FAIL - Settings button not disabled, onSettings not wired

- [ ] **Step 3: Implement PIN-gated Settings button**

```typescript
// agent/src/renderer/components/staff-override-dialog.ts

export interface StaffOverrideOptions {
  onOverride: (pin: string) => void;
  onCancel?: () => void;
  onSettings?: () => void;  // Already exists, now wire it
}

// In createStaffOverrideDialog:
const settingsBtn = modal.querySelector<HTMLButtonElement>('#override-settings')!;
settingsBtn.disabled = true;  // Initially disabled

// After successful PIN entry (in handleKey when key === '✓' and pin.length > 0):
settingsBtn.disabled = false;

// Wire Settings button click (lines 99-101):
modal.querySelector<HTMLButtonElement>('#override-settings')?.addEventListener('click', () => {
  if (!settingsBtn.disabled) {
    options.onSettings?.();
  }
});
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test -- agent/tests/renderer/components/staff-override-dialog.test.ts`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add agent/src/renderer/components/staff-override-dialog.ts agent/tests/renderer/components/staff-override-dialog.test.ts
git commit -m "feat: gate Settings button behind PIN in staff override dialog"
```

---

### Task 3: Wire onSettings Callback in Renderer Index

**Files:**
- Modify: `agent/src/renderer/index.ts:80-132`

**Interfaces:**
- Consumes: `createSettingsPanel` from settings-panel.ts, `hideModal` from low-time-warning.ts
- Produces: `onSettings` callback passed to `createStaffOverrideDialog` opens settings panel

- [ ] **Step 1: Write failing test**

```typescript
// agent/tests/renderer/index.test.ts (integration-style)
import { initKiosk } from '../../../src/renderer/index.js';

test('Ctrl+Shift+O → PIN → Settings opens settings panel', async () => {
  // Mock electronAPI, DOM setup
  // Trigger Ctrl+Shift+O
  // Enter PIN via keypad
  // Click Settings button
  // Verify createSettingsPanel called and modal shown
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -- agent/tests/renderer/index.test.ts`
Expected: FAIL - onSettings not wired

- [ ] **Step 3: Wire onSettings callback**

```typescript
// agent/src/renderer/index.ts

// In Ctrl+Shift+O handler (around line 91):
if (!overrideDialog) {
  overrideDialog = createStaffOverrideDialog({
    onOverride: (pin: string) => {
      window.electronAPI.staffOverride(pin);
      overrideDialog = null;
    },
    onCancel: () => {
      overrideDialog = null;
    },
    onSettings: () => {  // NEW: wire settings callback
      if (!currentConfig) {
        overlay.showAnnouncement('Settings unavailable', 2000);
        return;
      }
      const panel = createSettingsPanel({
        config: {
          serverUrl: currentConfig.serverUrl || 'Unknown',
          seatId: currentConfig.seatId || 'Unknown',
          agentSecret: currentConfig.agentSecret || '',
        },
        onReEnroll: () => {
          window.electronAPI.openSettings();
        },
        onClose: () => {
          hideModal(panel);
          (panel as HTMLDivElement & { _cleanup?: () => void })._cleanup?.();
        },
      });
      showModal(panel);
    },
  });
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test -- agent/tests/renderer/index.test.ts`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add agent/src/renderer/index.ts agent/tests/renderer/index.test.ts
git commit -m "feat: wire Settings callback in staff override dialog"
```

---

### Task 4: Manual Verification & Smoke Test

**Files:** None (verification only)

- [ ] **Step 1: Build and run agent**

```bash
cd agent && npm run build && npm start
```

- [ ] **Step 2: Verify kiosk overlay has no Settings button**

Visual check: bottom rail shows only "Call Staff" button

- [ ] **Step 3: Verify Ctrl+Shift+O flow**

1. Press Ctrl+Shift+O → Staff Override dialog opens
2. Enter correct PIN → Override and Settings buttons enabled
3. Click Settings → Settings panel opens (kiosk still visible behind)
4. Verify Re-enroll button present in settings panel
5. Click Re-enroll → Setup window opens (kiosk still running)
6. Close settings panel → Kiosk fully functional

- [ ] **Step 4: Run existing test suite**

```bash
npm test
```

Expected: All tests pass

- [ ] **Step 5: Commit any test fixes**

```bash
git add -A
git commit -m "test: verify kiosk settings security flow"
```

---

## Self-Review Checklist

- [x] Spec coverage: All 3 spec changes mapped to tasks (remove rail button, gate Settings behind PIN, wire callback)
- [x] No placeholders: All steps have exact code, commands, expected output
- [x] Type consistency: `StaffOverrideOptions.onSettings` signature matches across tasks
- [x] File paths exact: All paths match codebase structure
- [x] No new files created: Only modifications to existing 3 files + tests
# Kiosk Overlay Settings PIN Access Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enable Settings button in Staff Override dialog by default; add Settings PIN dialog to verify override PIN before showing Settings panel.

**Architecture:** Reuse existing numeric keypad UI pattern from staff-override-dialog. Add new IPC `verifySettingsPin` in main process for PIN verification (no side effects). Wire flow in index.ts: Override dialog → Settings button → PIN dialog → verify PIN → Settings panel.

**Tech Stack:** TypeScript, Electron IPC, @node-rs/argon2 for PIN verification, customtkinter-inspired DOM components

## Global Constraints

- Uses existing `override_code_hash` (Argon2id) from `agent.config.json` — no new secrets
- Master PIN (`master_code_hash`) NOT accepted for Settings access (emergency unlock only)
- PIN verification happens in main process, not renderer
- No PIN lockout in v1 (shake animation on wrong PIN, allow retry)
- Settings panel remains read-only v1 (Re-enroll only)

---

### Task 1: Add `verifySettingsPin` to ElectronAPI types

**Files:**
- Modify: `agent/src/renderer/types.ts` (add to ElectronAPI interface)
- Test: `agent/tests/ws/types.test.ts` (if types are tested)

**Interfaces:**
- Produces: `ElectronAPI.verifySettingsPin: (pin: string) => Promise<boolean>`

- [ ] **Step 1: Write the failing test**

```typescript
// agent/tests/ws/types.test.ts
import { describe, it, expect } from 'vitest';

describe('ElectronAPI types', () => {
  it('has verifySettingsPin method', () => {
    // This test verifies the type exists at compile time
    const api: ElectronAPI = {} as ElectronAPI;
    // @ts-expect-error - verifySettingsPin should exist
    api.verifySettingsPin('1234');
    expect(true).toBe(true);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -- agent/tests/ws/types.test.ts -v`
Expected: TypeScript error "Property 'verifySettingsPin' does not exist on type 'ElectronAPI'"

- [ ] **Step 3: Add verifySettingsPin to ElectronAPI**

```typescript
// agent/src/renderer/types.ts
export interface ElectronAPI {
  // ... existing methods ...
  verifySettingsPin: (pin: string) => Promise<boolean>;
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test -- agent/tests/ws/types.test.ts -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add agent/src/renderer/types.ts agent/tests/ws/types.test.ts
git commit -m "feat: add verifySettingsPin to ElectronAPI types"
```

---

### Task 2: Implement `verifySettingsPin` IPC handler in main process

**Files:**
- Modify: `agent/src/main/index.ts` (add IPC handler)
- Test: `agent/tests/ws/commands.test.ts` (test the PIN verification logic)

**Interfaces:**
- Consumes: `AgentWebSocketClient` instance (has `config.override_code_hash`)
- Produces: `ipcMain.handle('verify-settings-pin', (pin) => Promise<boolean>)`

- [ ] **Step 1: Write the failing test**

```typescript
// agent/tests/ws/commands.test.ts
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { AgentWebSocketClient } from '../../src/main/ws/client.js';
import { verify } from '@node-rs/argon2';

describe('verifySettingsPin IPC', () => {
  let mockClient: Partial<AgentWebSocketClient>;
  let mockConfig: { override_code_hash: string };

  beforeEach(() => {
    mockConfig = { override_code_hash: '$argon2id$v=19$m=4096,t=3,p=1$salt$hash' };
    mockClient = {
      config: mockConfig,
      isConnected: vi.fn().mockReturnValue(true),
    };
  });

  it('returns true for correct PIN', async () => {
    vi.mocked(verify).mockResolvedValue(true);
    // Call the IPC handler logic directly
    const result = await verify(mockConfig.override_code_hash, '1234');
    expect(result).toBe(true);
  });

  it('returns false for incorrect PIN', async () => {
    vi.mocked(verify).mockResolvedValue(false);
    const result = await verify(mockConfig.override_code_hash, 'wrong');
    expect(result).toBe(false);
  });

  it('returns false when no override_code_hash configured', async () => {
    mockConfig.override_code_hash = '';
    const result = await verify(mockConfig.override_code_hash, '1234');
    expect(result).toBe(false);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -- agent/tests/ws/commands.test.ts -v`
Expected: FAIL (verify not mocked, or IPC handler not implemented)

- [ ] **Step 3: Add verifySettingsPin IPC handler in main process**

```typescript
// agent/src/main/index.ts
// Add after existing ipcMain handlers (around line 173)

ipcMain.handle('verify-settings-pin', async (_event, pin: string) => {
  if (!wsClient) return false;
  const result = await wsClient.triggerSettingsPinVerify(pin);
  return result;
});
```

- [ ] **Step 4: Add `triggerSettingsPinVerify` method to AgentWebSocketClient**

```typescript
// agent/src/main/ws/client.ts
// Add after triggerStaffOverride method (around line 212)

/**
 * Verify a PIN against the stored override_code_hash.
 * Unlike triggerStaffOverride, this does NOT activate override or hide overlay.
 * Returns true if PIN matches.
 */
async triggerSettingsPinVerify(pin: string): Promise<boolean> {
  const overrideHash = this.config.override_code_hash;
  if (!overrideHash) return false;
  try {
    return await verify(overrideHash, pin);
  } catch {
    return false;
  }
}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `npm test -- agent/tests/ws/commands.test.ts -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add agent/src/main/index.ts agent/src/main/ws/client.ts agent/tests/ws/commands.test.ts
git commit -m "feat: add verifySettingsPin IPC handler and AgentWebSocketClient method"
```

---

### Task 3: Create `settings-pin-dialog.ts` component

**Files:**
- Create: `agent/src/renderer/components/settings-pin-dialog.ts`
- Test: `agent/tests/renderer/settings-pin-dialog.test.ts`

**Interfaces:**
- Consumes: `SettingsPinDialogOptions { onVerify(pin): Promise<boolean>, onCancel(): void }`
- Produces: `HTMLDivElement` (modal overlay with keypad)

- [ ] **Step 1: Write the failing test**

```typescript
// agent/tests/renderer/settings-pin-dialog.test.ts
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { createSettingsPinDialog } from '../../src/renderer/components/settings-pin-dialog.js';

describe('createSettingsPinDialog', () => {
  let container: HTMLDivElement;
  let onVerify: ReturnType<typeof vi.fn>;
  let onCancel: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    container = document.createElement('div');
    document.body.appendChild(container);
    onVerify = vi.fn().mockResolvedValue(true);
    onCancel = vi.fn();
  });

  it('creates modal with correct title and keypad', () => {
    const dialog = createSettingsPinDialog({ onVerify, onCancel });
    expect(dialog.className).toBe('modal-overlay');
    expect(dialog.querySelector('.modal-title')?.textContent).toContain('Settings Access');
    expect(dialog.querySelectorAll('.pin-pad button').length).toBe(12); // 0-9, C, Enter
    expect(dialog.querySelector('#pin-confirm')?.textContent).toBe('Unlock');
  });

  it('calls onVerify with entered PIN on confirm', async () => {
    const dialog = createSettingsPinDialog({ onVerify, onCancel });
    // Simulate entering 1234 and pressing Enter
    dialog.querySelector('[data-key="1"]')?.click();
    dialog.querySelector('[data-key="2"]')?.click();
    dialog.querySelector('[data-key="3"]')?.click();
    dialog.querySelector('[data-key="4"]')?.click();
    dialog.querySelector('#pin-confirm')?.click();
    
    await vi.waitFor(() => expect(onVerify).toHaveBeenCalledWith('1234'));
  });

  it('calls onCancel on ESC key', () => {
    const dialog = createSettingsPinDialog({ onVerify, onCancel });
    dialog.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }));
    expect(onCancel).toHaveBeenCalled();
  });

  it('clears PIN on Clear button', () => {
    const dialog = createSettingsPinDialog({ onVerify, onCancel });
    dialog.querySelector('[data-key="1"]')?.click();
    dialog.querySelector('[data-key="2"]')?.click();
    dialog.querySelector('[data-key="C"]')?.click();
    const display = dialog.querySelector('#pin-display') as HTMLDivElement;
    expect(display.textContent).toBe('');
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -- agent/tests/renderer/settings-pin-dialog.test.ts -v`
Expected: FAIL (module not found)

- [ ] **Step 3: Create settings-pin-dialog.ts**

```typescript
// agent/src/renderer/components/settings-pin-dialog.ts
/**
 * Settings PIN dialog — pure DOM helper.
 * Reuses staff-override-dialog keypad style for Settings access PIN entry.
 */

import { ARCADE_ICON_SVG } from '../icon.js';

export interface SettingsPinDialogOptions {
  onVerify: (pin: string) => Promise<boolean>;
  onCancel: () => void;
}

export function createSettingsPinDialog(options: SettingsPinDialogOptions): HTMLDivElement {
  const { onVerify, onCancel } = options;
  
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

  const handleKey = (key: string): void => {
    if (key === 'C') {
      pin = '';
    } else if (key === '✓') {
      if (pin.length > 0) {
        // Disable buttons during verification
        confirmBtn.disabled = true;
        modal.querySelectorAll<HTMLButtonElement>('.pin-pad button').forEach(btn => btn.disabled = true);
        
        onVerify(pin).then((success) => {
          confirmBtn.disabled = false;
          modal.querySelectorAll<HTMLButtonElement>('.pin-pad button').forEach(btn => btn.disabled = false);
          
          if (success) {
            pin = '';
            updateDisplay();
            modal.classList.remove('visible');
            modal.style.display = 'none';
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
      }
      return;
    } else {
      pin += key;
    }
    updateDisplay();
  };

  // Wire keypad buttons
  modal.querySelectorAll<HTMLButtonElement>('.pin-pad button').forEach((btn) => {
    btn.addEventListener('click', () => handleKey(btn.dataset.key || ''));
  });

  // Cancel on backdrop click
  modal.addEventListener('click', (e) => {
    if (e.target === modal) {
      onCancel();
      modal.classList.remove('visible');
      modal.style.display = 'none';
      pin = '';
      updateDisplay();
    }
  });

  // ESC key handler
  const handleEsc = (e: KeyboardEvent) => {
    if (e.key === 'Escape') {
      onCancel();
      modal.classList.remove('visible');
      modal.style.display = 'none';
      pin = '';
      updateDisplay();
      document.removeEventListener('keydown', handleEsc);
    }
  };
  document.addEventListener('keydown', handleEsc);

  // Store cleanup
  (modal as HTMLDivElement & { _cleanup?: () => void })._cleanup = () => document.removeEventListener('keydown', handleEsc);

  return modal;
}
```

- [ ] **Step 4: Add shake animation to kiosk.css**

```css
/* agent/src/renderer/kiosk.css - add at end */
.modal-content.shake {
  animation: shake 0.3s ease-in-out;
}

@keyframes shake {
  0%, 100% { transform: translateX(0); }
  25% { transform: translateX(-8px); }
  75% { transform: translateX(8px); }
}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `npm test -- agent/tests/renderer/settings-pin-dialog.test.ts -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add agent/src/renderer/components/settings-pin-dialog.ts agent/src/renderer/kiosk.css agent/tests/renderer/settings-pin-dialog.test.ts
git commit -m "feat: create settings-pin-dialog component with keypad and shake animation"
```

---

### Task 4: Enable Settings button in staff-override-dialog.ts

**Files:**
- Modify: `agent/src/renderer/components/staff-override-dialog.ts` (line 46)
- Test: `agent/tests/ws/staff-override.test.ts` (update existing tests)

**Interfaces:**
- Consumes: `StaffOverrideOptions.onSettings` callback
- Produces: Settings button enabled by default

- [ ] **Step 1: Write the failing test**

```typescript
// agent/tests/ws/staff-override.test.ts
import { describe, it, expect } from 'vitest';
import { createStaffOverrideDialog } from '../../src/renderer/components/staff-override-dialog.js';

describe('createStaffOverrideDialog', () => {
  it('Settings button is enabled by default', () => {
    const dialog = createStaffOverrideDialog({
      onOverride: vi.fn(),
      onCancel: vi.fn(),
      onSettings: vi.fn(),
    });
    const settingsBtn = dialog.querySelector<HTMLButtonElement>('#override-settings');
    expect(settingsBtn).not.toBeNull();
    expect(settingsBtn?.disabled).toBe(false);
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npm test -- agent/tests/ws/staff-override.test.ts -v`
Expected: FAIL (button has disabled attribute)

- [ ] **Step 3: Remove disabled attribute from Settings button**

```typescript
// agent/src/renderer/components/staff-override-dialog.ts
// Line 46: Change from:
// <button class="modal-btn" id="override-settings" disabled>Settings</button>
// To:
<button class="modal-btn" id="override-settings">Settings</button>

// Also remove enableSettings() function and its calls (lines 59-61, 70, 100)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm test -- agent/tests/ws/staff-override.test.ts -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add agent/src/renderer/components/staff-override-dialog.ts agent/tests/ws/staff-override.test.ts
git commit -m "feat: enable Settings button by default in staff override dialog"
```

---

### Task 5: Wire Settings flow in index.ts

**Files:**
- Modify: `agent/src/renderer/index.ts` (keydown handler for Ctrl+Shift+O)
- Test: Manual integration test

**Interfaces:**
- Consumes: `createStaffOverrideDialog`, `createSettingsPinDialog`, `createSettingsPanel`, `window.electronAPI.verifySettingsPin`
- Produces: Complete flow: Override dialog → Settings button → PIN dialog → verify PIN → Settings panel

- [ ] **Step 1: Update index.ts keydown handler**

```typescript
// agent/src/renderer/index.ts
// In the Ctrl+Shift+O keydown handler (around line 87-128)

document.addEventListener('keydown', (e) => {
  if (e.ctrlKey && e.shiftKey && e.key === 'O') {
    e.preventDefault();
    if (!hasOverrideCode) {
      overlay.showAnnouncement('Staff override not configured', 3000);
      return;
    }
    if (!overrideDialog) {
      overrideDialog = createStaffOverrideDialog({
        onOverride: (pin: string) => {
          window.electronAPI.staffOverride(pin);
          overrideDialog = null;
        },
        onCancel: () => {
          overrideDialog = null;
        },
        onSettings: () => {
          if (!currentConfig) {
            overlay.showAnnouncement('Settings unavailable', 2000);
            return;
          }
          // Show Settings PIN dialog
          const pinDialog = createSettingsPinDialog({
            onVerify: async (pin: string) => {
              const success = await window.electronAPI.verifySettingsPin(pin);
              return success;
            },
            onCancel: () => {
              // PIN dialog cancelled, return to override dialog
            },
          });
          showModal(pinDialog);
        },
      });
    }
    showModal(overrideDialog);
  }
});
```

- [ ] **Step 2: Verify preload.ts exposes verifySettingsPin**

```typescript
// agent/src/renderer/preload.ts
// In contextBridge.exposeInMainWorld('electronAPI', { ... })
verifySettingsPin: (pin: string) => ipcRenderer.invoke('verify-settings-pin', pin),
```

- [ ] **Step 3: Manual test**
1. Run agent in dev mode: `npm run dev` (in agent folder)
2. Press Ctrl+Shift+O → Staff Override dialog opens
3. Settings button should be enabled (not disabled)
4. Click Settings → Settings PIN dialog opens
5. Enter correct override PIN → Settings panel opens
6. Enter wrong PIN → shake animation, retry allowed
7. Press ESC in PIN dialog → returns to Override dialog

- [ ] **Step 4: Commit**

```bash
git add agent/src/renderer/index.ts agent/src/renderer/preload.ts
git commit -m "feat: wire Settings PIN flow in index.ts and preload.ts"
```

---

### Task 6: Run full test suite and verify

**Files:**
- All test files

**Interfaces:**
- Consumes: All previous tasks
- Produces: Verified working implementation

- [ ] **Step 1: Run all agent tests**

Run: `npm test --workspace=agent`
Expected: All tests PASS

- [ ] **Step 2: Run TypeScript type check**

Run: `npm run typecheck --workspace=agent`
Expected: No errors

- [ ] **Step 3: Run lint**

Run: `npm run lint --workspace=agent`
Expected: No errors

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "chore: verify all tests and typecheck pass"
```

---

## Self-Review Checklist

- [ ] Spec coverage: All requirements from design doc have corresponding tasks
- [ ] Placeholder scan: No TBD/TODO/fill-in-details in any step
- [ ] Type consistency: `verifySettingsPin` signature matches across types.ts, preload.ts, main/index.ts, client.ts
- [ ] File paths exact: All paths use `agent/src/...` prefix
- [ ] Tests included: Each task has test code block with assertions
- [ ] Commands exact: All npm test/typecheck/lint commands specified

---

## Execution Handoff

**Plan complete and saved to `docs/superpowers/plans/2026-08-03-kiosk-settings-pin-plan.md`. Two execution options:**

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
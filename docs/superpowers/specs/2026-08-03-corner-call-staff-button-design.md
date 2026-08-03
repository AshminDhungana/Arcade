# Corner-Triggered Call Staff Button in HUD

## Overview

Add a corner hot-zone trigger to show the Call Staff button in the in-session HUD when the kiosk overlay is hidden. The button appears for 5 seconds when the user moves their mouse to the bottom-right corner of the screen, with hover-extension behavior. Both the hot-zone trigger and button click show toast notifications.

## Current Behavior

- HUD (`hud.ts`) already has a `call-staff-btn` at bottom-right (glassmorphism style)
- Hot-zone: bottom-right 12% of viewport shows button for **10 seconds**
- Click calls `window.electronAPI.callStaff()` → IPC `call-staff` → Server `STAFF_ALERT`
- Server broadcasts to dashboards and returns `STAFF_ALERT_ACK`
- **No handler for `STAFF_ALERT_ACK`** → no confirmation toast in HUD
- Kiosk overlay has `showCallStaffConfirmation()` but HUD doesn't use it

## Design

### Hot-Zone Behavior

| Aspect | Specification |
|--------|---------------|
| **Trigger zone** | Bottom-right 12% × 12% of viewport (existing) |
| **Visibility duration** | 5 seconds (reduced from 10s) |
| **Hover extension** | Timer resets while mouse is over button; hides 5s after mouse leaves button |
| **Phase restriction** | Only when `phase !== 'ENDED'` (session active) |
| **Button style/position** | Identical to existing HUD button (bottom-right, glassmorphism) |

### Notifications

| Trigger | Toast Message | Duration |
|---------|---------------|----------|
| Hot-zone shows button | "✓ Call Staff available" | 3s |
| Button clicked + ACK received | "✓ Staff notified" | 3s |

### Message Flow

```
Hot-zone trigger
    → Button appears (5s)
    → Show toast "✓ Call Staff available"

User clicks button
    → IPC call-staff
    → Main: wsClient.send('STAFF_ALERT', ...)
    → Server: broadcasts ALERT to dashboards, returns STAFF_ALERT_ACK
    → Agent WS client receives STAFF_ALERT_ACK
    → IPC event to renderer: 'staff-alert-ack'
    → HUD: Show toast "✓ Staff notified"
```

## Implementation Plan

### Files to Modify

1. **`agent/src/main/ws/client.ts`**
   - Add `STAFF_ALERT_ACK` case in `handleMessage()`
   - Emit IPC event `staff-alert-ack` to renderer

2. **`agent/src/renderer/preload.ts`**
   - Add `onStaffAlertAck: (callback: () => void) => void` to `electronAPI`
   - Listen for `staff-alert-ack` IPC from main

3. **`agent/src/renderer/hud.ts`**
   - Update hot-zone handler (lines 166-177):
     - Change timeout from 10000ms → 5000ms
     - Add hover tracking on button (mouseenter/mouseleave)
     - Implement reset-timer-on-hover logic
   - Add `window.electronAPI.onStaffAlertAck(() => showToast('✓ Staff notified'))`
   - Add toast on hot-zone trigger: `showToast('✓ Call Staff available')`
   - Reuse `showToast` pattern from `showAnnouncement` (create toast element, auto-dismiss)

4. **`agent/src/main/index.ts`**
   - No changes needed if WS client emits IPC directly
   - Alternative: forward `STAFF_ALERT_ACK` via `ipcMain` if preferred

### Toast Implementation in HUD

```typescript
function showToast(message: string, durationMs = 3000): void {
  let toast = document.querySelector('.hud-toast') as HTMLDivElement;
  if (!toast) {
    toast = document.createElement('div');
    toast.className = 'hud-toast';
    document.body.appendChild(toast);
  }
  toast.textContent = message;
  toast.style.display = 'block';
  toast.style.opacity = '1';
  setTimeout(() => {
    toast.style.opacity = '0';
    setTimeout(() => { toast.style.display = 'none'; }, 300);
  }, durationMs);
}
```

Add CSS for `.hud-toast` in `hud.css`:
```css
.hud-toast {
  position: fixed; right: 4vw; bottom: 12vh;
  background: rgba(5, 6, 9, .9); border: 1px solid var(--accent);
  border-radius: 9px; padding: .6rem 1.1rem;
  font-family: var(--font-ui); font-size: .85rem; color: var(--text-1);
  box-shadow: 0 10px 30px rgba(0,0,0,.5); opacity: 0;
  transition: opacity .3s ease; pointer-events: none; z-index: 1000;
}
```

### Hover-Extension Logic

```typescript
let hoverTimer: ReturnType<typeof setTimeout> | null = null;
let isHoveringButton = false;

callBtn?.addEventListener('mouseenter', () => { isHoveringButton = true; });
callBtn?.addEventListener('mouseleave', () => { isHoveringButton = false; });

function scheduleHide() {
  if (hoverTimer) clearTimeout(hoverTimer);
  hoverTimer = setTimeout(checkAndHide, 5000);
}

function checkAndHide() {
  if (!isHoveringButton && callBtn) {
    callBtn.style.display = 'none';
  } else if (isHoveringButton) {
    hoverTimer = setTimeout(checkAndHide, 500); // Re-check while hovering
  }
}

window.addEventListener('mousemove', (e) => {
  if (e.clientX > innerWidth * (1 - HOVER_ZONE) && e.clientY > innerHeight * (1 - HOVER_ZONE)) {
    if (callBtn && callBtn.style.display === 'none' && phase !== 'ENDED') {
      callBtn.style.display = 'block';
      reveal(callBtn, 80);
      showToast('✓ Call Staff available');
      scheduleHide();
    }
  }
});
```

## Testing

- Verify hot-zone triggers at bottom-right 12% corner
- Verify button shows for 5s, extends on hover, hides 5s after hover ends
- Verify "✓ Call Staff available" toast on hot-zone trigger
- Verify "✓ Staff notified" toast on button click + ACK
- Verify button/style matches existing HUD Call Staff button
- Verify no regression in kiosk overlay Call Staff button
- Test with session active (INTRO/AMBIENT/URGENT phases) and ENDED phase

## Acceptance Criteria

1. Mouse to bottom-right 12% corner → Call Staff button appears (5s)
2. Hover over button → timer resets, button stays visible
3. Mouse leaves button → hides after 5s
4. Hot-zone trigger shows "✓ Call Staff available" toast (3s)
5. Button click sends call-staff, receives ACK, shows "✓ Staff notified" toast (3s)
6. Button uses existing glassmorphism style at bottom-right
7. Only works when session active (`phase !== 'ENDED'`)
8. No changes to kiosk overlay Call Staff behavior
# Kiosk Overlay Cafe Name Fallback Design

**Date:** 2026-08-02
**Status:** Approved
**Author:** Assistant

---

## Problem Statement

The kiosk overlay center (`.cafe-brand` element) displays the cafe name only after receiving `OverlayContent` from the main process. This occurs when the server sends `SHOW_OVERLAY` or `FORCE_OVERLAY_ON` commands.

Before that happens (on agent startup, before WebSocket connects, or before first `SHOW_OVERLAY`), the center is empty while the top-left bug shows the hardcoded product name "ARCADE".

**Requirement:** The center should show the cafe name from the server. If the cafe name is unavailable (not yet received, or server sends empty), fall back to displaying "Arcade".

---

## Solution: Approach A — Default in Renderer, Update on REGISTERED

### Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        RENDERER PROCESS                         │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    KioskOverlay                          │   │
│  │  - arcadeName: string = 'Arcade'  (fallback)            │   │
│  │  - cafeName: string | null = null   (server-provided)   │   │
│  │                                                         │   │
│  │  setArcadeName(name)     → updates fallback             │   │
│  │  setCafeName(name, logo) → displays name or fallback    │   │
│  └─────────────────────────────────────────────────────────┘   │
│                            ▲                                    │
│                    onOverlayContent                             │
└────────────────────────────┼────────────────────────────────────┘
                             │
                    IPC (OverlayContent)
                             │
┌────────────────────────────┼────────────────────────────────────┐
│                       MAIN PROCESS                              │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │              AgentWebSocketClient                        │   │
│  │  - cafeName: string = ''      (from REGISTERED)         │   │
│  │  - eventBanner: string = ''   (from REGISTERED)         │   │
│  │                                                         │   │
│  │  handleMessage(REGISTERED) → stores cafeName            │   │
│  └─────────────────────────────────────────────────────────┘   │
│                            ▲                                    │
│                    commandHandlers                              │
└────────────────────────────┼────────────────────────────────────┘
                             │
              SHOW_OVERLAY / FORCE_OVERLAY_ON
                             │
                             ▼
                    platform.showKioskOverlay(OverlayContent)
                             │
                    (cafeName from WS client)
```

### Data Flow

1. **Agent starts** → `initKiosk()` creates `KioskOverlay` → calls `overlay.setArcadeName('Arcade')` → center renders "Arcade"
2. **WebSocket connects** → `REGISTER` sent → `REGISTERED` received with `cafe_name`
3. **WS client** stores `cafeName` from `REGISTERED` payload
4. **Server sends** `SHOW_OVERLAY` or `FORCE_OVERLAY_ON`
5. **Command handler** builds `OverlayContent` using `deps.getCafeName()` → WS client's `cafeName`
6. **Main process** sends `OverlayContent` via IPC to renderer
7. **Renderer** receives `onOverlayContent` → calls `overlay.setCafeName(data.cafeName, data.cafeLogo)`
8. **KioskOverlay** displays server-provided cafe name (overriding fallback)

### Fallback Behavior

| Scenario | Center Display |
|----------|----------------|
| First run (before enrollment) | "Arcade" |
| After enrollment, before REGISTERED | "Arcade" |
| After REGISTERED with cafe_name | Actual cafe name |
| Server sends empty cafe_name | "Arcade" (fallback) |
| Network disconnect, then reconnect | Last known cafe name (persisted in WS client) |

---

## Changes

### 1. `agent/src/renderer/components/kiosk-overlay.ts`

```typescript
export class KioskOverlay {
  // ... existing fields ...
  private arcadeName = 'Arcade';      // NEW: fallback name
  private currentCafeName = '';       // NEW: track server-provided name

  constructor(parent: HTMLElement) {
    // ... existing code ...
    // Initialize cafeBrandEl with fallback
    this.cafeBrandEl = document.createElement('div');
    this.cafeBrandEl.className = 'cafe-brand';
    const span = document.createElement('span');
    span.textContent = this.arcadeName;
    this.cafeBrandEl.appendChild(span);
    this.centerEl.appendChild(this.cafeBrandEl);
    // ... rest unchanged ...
  }

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
}
```

### 2. `agent/src/renderer/index.ts`

```typescript
function initKiosk(): void {
  // ... existing code ...
  const overlay = new KioskOverlay(app);
  
  // NEW: Set fallback name immediately on init
  overlay.setArcadeName('Arcade');
  
  overlay.startClock();
  // ... rest unchanged ...
  
  window.electronAPI.onOverlayContent((data: OverlayData) => {
    currentConfig = data;
    // EXISTING: This now properly overrides fallback when server provides name
    overlay.setCafeName(data.cafeName, data.cafeLogo);
    // ... rest unchanged ...
  });
}
```

### 3. Top Bug Wordmark — **No Change**

The top-left bug (`.cafe-wordmark`) remains hardcoded "ARCADE" as the product name, per user decision.

---

## Testing

### Unit Tests (kiosk-overlay.test.ts)

- `setArcadeName` updates fallback and displays it when no cafe name set
- `setCafeName` with non-empty name displays that name
- `setCafeName` with empty name falls back to arcadeName
- `setCafeName` with logo + name displays both
- `setCafeName` with logo only (empty name) shows logo + fallback name
- Calling `setArcadeName` after `setCafeName` with server name does NOT override server name

### Integration Tests

- Agent startup → overlay center shows "Arcade" before any IPC
- After REGISTERED → `onOverlayContent` with cafeName → center shows cafe name
- Server sends empty cafeName → center falls back to "Arcade"

---

## Non-Goals

- Do not persist cafe name to local config (server is source of truth)
- Do not change top bug wordmark ("ARCADE")
- Do not modify enrollment flow or REGISTER/REGISTERED protocol
- Do not add UI for editing arcade fallback name

---

## Rollout

- No migration needed (fallback is client-side default)
- Backward compatible: if server never sends cafe_name, "Arcade" displays
- No config changes required
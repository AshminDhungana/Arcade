# Force Overlay Full UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix Force Overlay to display the full kiosk overlay UI (background, cafe brand, clock, event banner, bottom rail) instead of a transparent HUD-like screen.

**Architecture:** Single-file fix in the WebSocket command handler. The `FORCE_OVERLAY_ON` handler currently passes extra undefined fields to `showKioskOverlay()`. Removing these to match `SHOW_OVERLAY` structure ensures consistent renderer behavior.

**Tech Stack:** TypeScript, Electron, WebSocket

## Global Constraints

- Follow existing code patterns in `agent/src/main/ws/commands.ts`
- No changes to platform service, renderer, or preload scripts
- Minimal change - only modify the `FORCE_OVERLAY_ON` handler
- Preserve `sessionActive: !!payload.session_id` logic

---

### Task 1: Update FORCE_OVERLAY_ON handler in commands.ts

**Files:**
- Modify: `agent/src/main/ws/commands.ts:96-110`

**Interfaces:**
- Consumes: `HandlerDeps` (seatId, getCafeName, getEventBanner, serverUrl, agentSecret)
- Produces: `OverlayContent` passed to `platform.showKioskOverlay()`

- [ ] **Step 1: View current FORCE_OVERLAY_ON handler**

```bash
# View the current implementation
cat agent/src/main/ws/commands.ts | sed -n '96,110p'
```

Expected output shows current handler with `remainingTime: undefined` and `lowTimeWarning: false`

- [ ] **Step 2: Edit commands.ts to match SHOW_OVERLAY structure**

```typescript
// In agent/src/main/ws/commands.ts, replace lines 96-110:

FORCE_OVERLAY_ON(payload) {
  // Force-show the kiosk overlay regardless of session state
  // Match SHOW_OVERLAY structure exactly for consistent UI rendering
  platform.showKioskOverlay({
    cafeName: deps.getCafeName?.() || 'Arcade',
    announcements: [],
    callStaffEnabled: true,
    sessionActive: !!payload.session_id,
    eventBanner: deps.getEventBanner?.() || '',
    serverUrl: deps.serverUrl,
    seatId: deps.seatId,
    agentSecret: deps.agentSecret,
  });
},
```

- [ ] **Step 3: Verify the change compiles**

```bash
cd agent && npm run build
# or
cd agent && npx tsc --noEmit
```

Expected: No TypeScript errors

- [ ] **Step 4: Commit**

```bash
git add agent/src/main/ws/commands.ts
git commit -m "fix: Force Overlay now shows full kiosk UI by matching SHOW_OVERLAY content structure"
```

---

### Task 2: Manual verification test

**Files:**
- None (manual test)

**Interfaces:**
- Consumes: Built agent executable
- Produces: Visual confirmation

- [ ] **Step 1: Build the agent**

```bash
cd agent && npm run build
```

- [ ] **Step 2: Run agent locally**

```bash
cd agent && npm start
# or run the built executable
```

- [ ] **Step 3: Test Force Overlay from dashboard**

1. Ensure agent is running with no active session
2. Open dashboard in browser
3. Click "Lock all idle seats" button
4. Verify kiosk shows:
   - Dark background (not transparent)
   - Cafe brand/name at top center
   - Live clock
   - Event banner (if configured)
   - Bottom rail with "Call Staff" button
   - Status pill showing "OPEN"
   - NO timer displayed

- [ ] **Step 4: Test with active session**

1. Start a session on the seat (via POS or API)
2. Verify overlay updates to show:
   - Timer counting up
   - Status pill showing "LIVE"
   - Session indicator "● Session in progress"

- [ ] **Step 5: Test Force Overlay OFF**

1. Click "Unlock all seats" in dashboard
2. Verify overlay hides completely

- [ ] **Step 6: Commit any follow-up fixes if needed**

```bash
git add -A
git commit -m "fix: follow-up adjustments after manual verification"
```

---

## Self-Review Checklist

- [x] Spec coverage: The single spec requirement (Force Overlay shows full UI) is addressed by Task 1
- [x] No placeholders: All steps contain actual code/commands
- [x] Type consistency: Uses existing `HandlerDeps` and `OverlayContent` types
- [x] Minimal change: Only modifies the one handler function
- [x] Follows existing patterns: Matches `SHOW_OVERLAY` structure exactly
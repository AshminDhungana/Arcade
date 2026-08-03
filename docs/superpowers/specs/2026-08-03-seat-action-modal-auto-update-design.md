# SeatActionModal Auto-Update on Seat Status Change

## Problem

The `SeatActionModal` receives a `seat` prop that is a snapshot of the seat data at the time the modal opens. When a PC connects via enroll code, the backend sends a `seat_updated` WebSocket event, which invalidates the React Query caches. However, the modal continues displaying stale data because it uses the `seat` prop directly instead of refetching the updated seat data.

**Current behavior:**
1. User clicks an OFFLINE seat → modal opens showing "Status: OFFLINE"
2. User adds enroll code in server dashboard → PC connects → status becomes AVAILABLE
3. WebSocket fires `seat_updated` → queries invalidated → SeatGrid updates
4. Modal still shows "Status: OFFLINE" (stale prop)
5. User must close and reopen modal to see updated status

**Expected behavior:** Modal automatically updates to reflect the new seat status (AVAILABLE) without requiring close/reopen.

## Solution

Modify `SeatActionModal` to use the existing `useSeat` hook (from `@/api/seats`) for real-time seat data by ID. The `seat` prop serves as `initialData` for immediate rendering while the query loads.

## Architecture

```
SeatGrid (click seat)
    → sets selectedSeat state (full seat object)
    → opens SeatActionModal with seat prop

SeatActionModal
    → uses useSeat(seat.id, { initialData: seat })
    → on seat_updated WebSocket event:
         useWebSocket invalidates ['seat', seatId]
         useSeat refetches automatically
         modal re-renders with fresh data
```

## Changes Required

### 1. `frontend/src/components/SeatActionModal.tsx`

- Import `useSeat` from `@/api/seats`
- Replace direct `seat` prop usage with data from `useSeat(seat.id, { initialData: seat })`
- Handle loading/error states gracefully (fallback to `seat` prop data)
- Keep `onClose` and all action handlers (`handleStartSession`, `handleForceOverlayOn/Off`, etc.) unchanged — they already use `seat.id` which remains stable

### 2. `frontend/src/components/SeatGrid.tsx` (minimal)

- No functional changes required — already passes full `seat` object to modal
- The modal reads `seat.id` from the prop to call `useSeat`

## Data Flow Comparison

| Step | Current Behavior | New Behavior |
|------|------------------|--------------|
| Modal opens | Uses `seat` prop snapshot | Uses `seat` prop as `initialData` for `useSeat` |
| PC connects (enroll) | Modal shows stale status | `seat_updated` → invalidates `['seat', seatId]` → `useSeat` refetches → modal updates automatically |
| Modal closes | `setSelectedSeat(null)` | Unchanged |

## Error Handling

- If `useSeat` query fails: fallback to `seat` prop data (available via `initialData` in error state)
- Brief loading state on first fetch mitigated by `initialData` — renders immediately with prop data
- No flash since `initialData` is used for initial render

## Testing

1. **Primary test:** Open modal for OFFLINE seat → add enroll code in dashboard → verify modal status updates to AVAILABLE without closing
2. **Regression tests:**
   - All action buttons work with fresh data (Start Session, Enroll Code, Regenerate PIN, Force Overlay, etc.)
   - Modal closes properly via `onClose`
   - No issues when WebSocket disconnects/reconnects
   - Loading/error states handled gracefully
3. **Edge cases:**
   - Seat deleted while modal open (API returns 404) → modal should handle error gracefully
   - Rapid status changes (OFFLINE → BOOTING → AVAILABLE) → modal reflects latest state

## Scope

This change is isolated to `SeatActionModal.tsx`. No changes to:
- WebSocket handling (`useWebSocket.ts`)
- Query invalidation logic
- SeatGrid or other components
- Backend API

## Files Modified

- `frontend/src/components/SeatActionModal.tsx`

## Out of Scope

- Auto-closing modal on status change (user chose Option A: auto-update while open)
- Real-time updates for SessionDrawer (separate component, separate issue if needed)
- Bulk seat operations
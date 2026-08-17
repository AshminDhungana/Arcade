# Section J — Events & Tournaments Design

**Date:** 2026-08-17
**Status:** Ready for implementation
**Related:** TODO.md Section J (J.1–J.4)

---

## Overview

The **backend for Events & Tournaments is fully implemented and tested**. All core functionality exists:

- Event creation with entry fee, prize pool, bracket type (single/double elimination)
- Participant registration (members with wallet deduction, walk-ins)
- Bracket generation (lazy, on registration)
- Match recording with winner advancement (single & double elimination)
- Event summary with revenue, prize pool, champion
- Feature-flag gated (`enable_tournaments`)

**Frontend gaps** (this design addresses):

1. **RegisterParticipantModal** — only supports walk-in name; needs member selection + seat assignment
2. **Dashboard Events Widget** — J.4 requires an events summary widget on the main Dashboard page
3. **Frontend tests** — need coverage for new registration flows

---

## 1. Registration Modal Enhancement (J.2)

### Current State
`RegisterParticipantModal` accepts only a `name` for walk-in participants. Backend supports `member_id` (wallet auto-deduct) and `seat_id` but frontend doesn't expose them.

### New Design

#### UI Flow
```
┌─────────────────────────────────────┐
│ Register Participant                │
├─────────────────────────────────────┤
│  (○) Member      (○) Walk-in        │  ← Radio toggle
├─────────────────────────────────────┤
│  [Member Mode]                      │
│  Member: [Dropdown ▼]               │  ← Active members
│  Wallet: ₹XXX.XX (fee: ₹YY.YY)       │  ← Balance preview
│  Seat:   [Dropdown ▼]               │  ← AVAILABLE seats
│                                     │
│  [Walk-in Mode]                     │
│  Name:   [Input________]            │  ← Required
│  Seat:   [Dropdown ▼]               │  ← AVAILABLE seats (optional)
│                                     │
│  [Register]                         │
└─────────────────────────────────────┘
```

#### Member Mode
- **Member dropdown** — fetches via `GET /api/members` (active only), shows `name (phone)`
- **Wallet preview** — shows current balance, entry fee, projected balance after deduction
- **Seat dropdown** — fetches seats with status `AVAILABLE` or `ONLINE`, shows `Seat #{id} (Zone)`

#### Walk-in Mode
- **Name input** — required, max 255 chars
- **Seat dropdown** — same as member mode, but optional (can be assigned later)
- **No wallet interaction** — entry fee collected at counter

#### API Integration
- Reuses existing `POST /api/events/{id}/register` (implemented in `EventService.register_participant`)
- Body: `{ member_id?, name?, seat_id? }`
- Member validation & wallet deduction handled server-side (atomic)
- Audit log: `EVENT_PARTICIPANT_REGISTERED`

### Components to Modify

| File | Change |
|------|--------|
| `frontend/src/components/events/RegisterParticipantModal.tsx` | Full rewrite with mode toggle, member dropdown, seat dropdown, wallet preview |
| `frontend/src/api/members.ts` | Add `useMembers` hook (fetch active members) |
| `frontend/src/api/seats.ts` | Add `useAvailableSeats` hook (filter by status) |

### New Hooks

**`frontend/src/api/members.ts`**
```typescript
export function useMembers() {
  // GET /api/members → MemberResponse[]
  // filter: is_active = true
}
```

**`frontend/src/api/seats.ts`**
```typescript
export function useAvailableSeats() {
  // GET /api/seats → SeatResponse[]
  // filter: status in ['AVAILABLE', 'ONLINE']
}
```

---

## 2. Dashboard Events Widget (J.4)

### Current State
Dashboard (`Dashboard.tsx`) shows only `SeatGrid` + `UnprintedInvoices`. Events page exists at `/events` but not linked from Dashboard.

### New Design

#### Placement
Below header, above `SeatGrid` (full-width card), or in a right sidebar column if layout permits.

#### Content
```
┌────────────────────────────────────────────────────────────┐
│ Upcoming Events                                    [View All] │
├────────────────────────────────────────────────────────────┤
│ 🎮 FIFA Cup — FIFA 24                    2026-08-15 18:00 │
│    8/16 players  •  ₹500 entry  •  ₹20,000 prize  [UPCOMING] │
├────────────────────────────────────────────────────────────┤
│ 🎮 Tekken Tournament — Tekken 8          2026-08-20 19:00 │
│    4/8 players   •  ₹300 entry  •  ₹10,000 prize  [UPCOMING] │
├────────────────────────────────────────────────────────────┤
│ No upcoming events. Create one on the Events page.          │
└────────────────────────────────────────────────────────────┘
```

#### Data
- Reuse `useEvents` hook (already fetches all events)
- Client-side filter: `status === 'UPCOMING'` ordered by `event_date`
- Show: name, game_title, event_date (localized), participant_count, entry_fee_paise, prize_pool_paise, status badge

#### Navigation
- "View All" button/link → navigates to `/events` (full Events page)

### Components

| File | Change |
|------|--------|
| `frontend/src/components/events/EventsWidget.tsx` | New component |
| `frontend/src/pages/Dashboard.tsx` | Import & render `EventsWidget` above `SeatGrid` |

---

## 3. Brackets & Prize Pool (J.3) — No Frontend Changes

### Backend Status (Complete)
- **Single elimination** — bracket generated when ≥2 participants (pads to power of 2 with byes)
- **Double elimination** — bracket generated when participant count is power of 2; enforced at first match recording
- **Match recording** — `PATCH /api/events/{id}/match` advances winner, drops loser to losers bracket (double elim)
- **Prize pool** — manual entry at creation (`prize_pool_paise`); summary shows `prize_pool_paise` + `entry_fee_revenue_paise`
- **Champion detection** — match with no `next_match_id` and `winner_id` set

### Frontend Status (Complete)
- `BracketView.tsx` renders winners/losers/grand-final brackets
- `EventSummaryPanel.tsx` shows prize pool, revenue, champion
- `RecordResultModal.tsx` allows recording match results

**No changes needed.**

---

## 4. Event Billing Verification (J.4) — Already Working

### Backend (Verified)
- Member registration → wallet deduction (`EVENT_ENTRY` transaction) ✅
- Walk-in registration → no wallet deduction ✅
- Summary `entry_fee_revenue_paise = participant_count × entry_fee_paise` ✅
- Audit: `EVENT_PARTICIPANT_REGISTERED` + `WALLET_TOPUP` (negative) ✅

### Frontend (Verified)
- Events page summary shows revenue KPI ✅
- Create event modal converts ₹ → paise ✅

**No changes needed.**

---

## 5. Testing Updates

### Backend
All tests pass — **no changes needed**.
- `test_events.py` — 6 tests (E2E HTTP)
- `test_events_router.py` — 5 tests (router integration)
- `test_event_service.py` — 13 tests (service unit)
- `test_events_e2e_smoke.py` — 1 test (double elim over HTTP)

### Frontend — Add Coverage

**`frontend/src/pages/Events.test.tsx`** — extend with:
- Member registration flow (wallet balance preview, deduction)
- Walk-in registration flow (name required, seat optional)
- Seat assignment in both modes
- Error states: insufficient funds, no available seats

**`frontend/src/pages/Dashboard.test.tsx`** — add:
- EventsWidget renders upcoming events
- "View All" navigates to `/events`
- Empty state when no upcoming events

---

## 6. Implementation Order

1. **Hooks** — `useMembers`, `useAvailableSeats` in `frontend/src/api/`
2. **RegisterParticipantModal** — rewrite with mode toggle, dropdowns, wallet preview
3. **EventsWidget** — new component for Dashboard
4. **Dashboard integration** — import EventsWidget in Dashboard.tsx
5. **Tests** — extend Events.test.tsx, add Dashboard.test.tsx coverage
6. **Verify** — run frontend test suite (`npx vitest run`)

---

## 7. Acceptance Criteria (from TODO.md)

| Item | Status | Verification |
|------|--------|--------------|
| **J.1 Event creation** | ✅ Backend done | `python -m pytest backend/tests/test_events.py backend/tests/test_events_router.py backend/tests/test_event_service.py` |
| **J.2 Participant registration + seats** | 🔄 Frontend pending | `backend/tests/test_events_e2e_smoke.py` + new frontend tests |
| **J.3 Brackets** | ✅ Complete | Single & double elim advancement verified in service + router tests |
| **J.4 Event billing** | ✅ Backend done | `cd frontend && npx vitest run src/pages/Events.test.tsx` (extend for new flows) |

---

## 8. Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Member dropdown performance (many members) | Add search/filter to dropdown; paginate API if >100 |
| Seat assignment race condition | Backend already validates seat status on registration; frontend shows real-time status via WS |
| Wallet balance stale in preview | Fetch fresh balance on modal open; show "refresh" button |
| Double elimination power-of-2 requirement | Backend enforces at first match recording with clear 400 error; UI can warn at registration if count not power of 2 |

---

## 9. Out of Scope (YAGNI)

- Participant check-in / seat assignment at event start (separate flow)
- Live bracket updates via WebSocket (current: refetch on summary)
- Prize distribution / payout workflow (manual at counter)
- Event templates / recurring events
- Spectator mode / public bracket view

---

## 10. Spec Self-Review

- [x] No TBD/TODO placeholders
- [x] Internal consistency: backend capabilities match frontend design
- [x] Scope focused: only frontend gaps addressed; backend complete
- [x] No ambiguity: each component change specified with API contracts

---

**Next step:** Invoke `writing-plans` skill to create implementation plan.

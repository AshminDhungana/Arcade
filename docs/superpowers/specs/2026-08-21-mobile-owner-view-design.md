# Mobile Owner View — Design Spec

**Date:** 2026-08-21
**Status:** Approved
**Section:** K.4 (TODO.md)

---

## 1. Overview

Add a mobile-optimized `/mobile` route to the existing React frontend that mirrors the desktop dashboard metrics (today's revenue, active sessions, shift summary, top zones) with real-time WebSocket updates. Single codebase, responsive Tailwind CSS, reusable API/WebSocket hooks.

**Success criteria:** Owner can open `/mobile` on phone (cafe WiFi), see live data without refresh, perform core actions (pause session, close shift).

---

## 2. Architecture

- **Route:** `/mobile` added to `frontend/src/App.tsx`
- **Layout:** `MobileLayout` — minimal header (cafe name, logout), bottom tab bar (Dashboard, Sessions, Shifts, Settings), responsive container (`max-w-screen-md mx-auto`)
- **Shared infrastructure:** Reuse existing `useWebSocket`, `useAuth`, API service layer — **zero backend changes**
- **Styling:** Tailwind mobile-first breakpoints (`sm:` 640px), existing `lg:`/`xl:` for desktop preserved
- **PWA-ready:** Manifest + service worker can be added later (not in scope)

---

## 3. Components & Pages

| Page | Route | Reused Logic | New Mobile Components |
|------|-------|--------------|----------------------|
| Dashboard | `/mobile` | `useAnalytics`, `useWebSocket` | `MobileStatsGrid` (4 cards), `MobileTopZones`, `MobileActiveSessionsList` |
| Sessions | `/mobile/sessions` | `useSeats`, `useSessions` | `MobileSeatGrid` (stacked cards), `MobileSessionActions` (bottom sheet) |
| Shifts | `/mobile/shifts` | `useShifts`, `useShiftTotals` | `MobileShiftCard`, `MobileReconciliationSheet` |
| Settings | `/mobile/settings` | `useFeatureFlags`, `useStaff` | `MobileFlagToggles`, `MobileStaffList` |

- New components under `frontend/src/components/mobile/`
- Seat grid → vertical stack of cards; tap expands to bottom action sheet (pause/resume/checkout/call staff)
- Bottom sheet pattern for all session actions — native mobile UX

---

## 4. Data Flow & Real-time Updates

- **WebSocket:** Single connection per tab (same as desktop). Topics: `analytics`, `seats`, `sessions`, `shifts`, `alerts`
- **Optimistic updates:** Session actions update local state immediately, sync on server ack
- **Background sync:** On `visibilitychange` / `focus`, fetch fresh `/api/analytics/today`, `/api/seats`, `/api/shifts/current`
- **Offline queue:** Failed mutations queued in `localStorage`, replay on reconnect
- **Battery/network aware:** WS ping interval 30s on mobile (vs 10s desktop) via `navigator.connection?.effectiveType`

---

## 5. Error Handling

- **Error boundaries:** Each mobile page wrapped in `ErrorBoundary` → shows retry button, logs to Sentry
- **WS reconnection:** Exponential backoff (1s, 2s, 4s, max 30s); toast "Reconnecting..." after 3s disconnect
- **Auth expiry:** 401 on any API call → redirect to `/login?next=/mobile`, preserve scroll position
- **Graceful degradation:** If WS fails, fall back to 30s polling for critical endpoints

---

## 6. Testing Strategy

| Layer | Scope | Tool |
|-------|-------|------|
| Unit | `MobileStatsGrid`, `MobileSeatCard`, `MobileActionSheet` | Vitest + React Testing Library |
| Integration | WS reconnection flow, offline queue replay, auth redirect | Vitest + MSW |
| E2E | Critical paths: view dashboard → pause session → close shift | Playwright (mobile viewport 375×667) |
| Visual | Regression screenshots for each mobile page | Playwright + pixelmatch |

---

## 7. Non-Functional Requirements

- **Performance:** Initial load <2s on 3G (bundle split: mobile chunks lazy-loaded)
- **Accessibility:** WCAG 2.1 AA — touch targets ≥48×48dp, color contrast, screen reader labels
- **Responsive:** Works 320px–768px width; landscape mode stacks tabs horizontally
- **iOS Safari / Chrome Android:** Tested on both; `-webkit-overflow-scrolling: touch` for momentum scroll

---

## 8. Out of Scope (Deferred)

- PWA install prompt / service worker offline caching
- Push notifications (background session alerts)
- Native biometric login (FaceID/TouchID)
- Separate owner-only auth (uses existing staff JWT)

---

## 9. Implementation Order

1. Add `/mobile` route + `MobileLayout` + bottom tab navigation
2. Mobile Dashboard page (stats grid, top zones, active sessions list)
3. Mobile Sessions page (seat cards + bottom action sheet)
4. Mobile Shifts page (current shift card + reconciliation sheet)
5. Mobile Settings page (feature flags, staff list)
6. WS reconnection logic + offline queue + background sync
7. Unit + integration tests
8. Playwright E2E + visual regression
9. Manual QA on real device (cafe WiFi)

---

## 10. Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| WS connection drops on mobile sleep | Background sync on wake + offline queue |
| Touch targets too small on dense data | Bottom sheets for actions; 48dp minimum |
| Bundle size increase | Lazy-load mobile routes (`React.lazy` + `Suspense`) |
| Safari PWA limitations | Not a PWA yet; plain web app works fine |

---

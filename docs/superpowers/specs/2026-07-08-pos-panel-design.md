# POS Panel — Design Spec (Feature 3.2.1)

**Date:** 2026-07-08
**Status:** Approved
**Reference:** `docs/TODO.md` Feature 3.2.1 · `docs/Arcade_SRS.md` §4.8 · `docs/Arcade_SDD.md` §6.3

## Overview

Build the **POS Panel** — a frontend component that lets staff add food/drink menu items to an active gaming session. It is embedded inside a slide-out **SessionDrawer** that opens when clicking an `IN_USE` seat on the dashboard. The backend POS APIs (`POST /api/pos/items`, `GET /api/pos/items/{sessionId}`, `DELETE /api/pos/items/{id}`, `GET /api/menu`) are already complete from Feature 3.1.4.

This feature also bootstraps the **feature flag system** in the frontend, which no subsequent feature can use until this is done.

---

## Goals

- Staff can browse menu items, click to add them to a session, and adjust quantities
- Inventory-aware stock badges (green/yellow/red) gated by `enable_inventory` flag
- Out-of-stock and unavailable items are visually disabled and not clickable
- All monetary amounts displayed as "Rs. X.XX" (paise→rupees conversion at display layer only)
- Entire POS subtree gated by `enable_pos` feature flag
- Feature flag infrastructure reusable by all future gated features

## Non-Goals (deferred to Feature 3.2.2)

- Checkout / invoice preview (Checkout tab is a placeholder)
- Payment method selection and confirmation
- Receipt printing trigger
- Menu item CRUD management (admin Settings feature)

---

## Design Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Integration point | Slide-out drawer from right (45% width) | Ample space for menu grid + session tab; seat grid remains partially visible |
| Page vs panel | Embedded panel only (no `/pos` route) | Keeps workflow focused on seat grid; no navigation fragmentation |
| Tab layout | POS tab + Checkout tab + Commands placeholder | Clean separation; checkout built in next feature |
| Add-to-tab UX | Click = add 1; +/- in session tab | Fastest for high-volume counter work |
| Quantity grouping | Rows grouped by `menu_item_id` in UI | Backend creates one row per add; UI sums quantities for display |
| Feature flag source | Zustand store populated from `GET /api/settings` | Single source of truth; no prop drilling |
| Currency display | `formatPaise()` utility — the ONLY place paise→rupees conversion happens | Enforces NFR-DATA-002 |

---

## Component Architecture

```
components/
├── SessionDrawer.tsx          (NEW) Slide-out drawer for IN_USE seats — tab container
├── SeatActionModal.tsx        (KEEP) For non-IN_USE seat statuses
├── pos/
│   ├── POSPanel.tsx           (NEW) Orchestrator: feature-flag gate, wires mutations
│   ├── MenuGrid.tsx           (NEW) Responsive grid of MenuItemCard
│   ├── MenuItemCard.tsx       (NEW) Single menu item: name, price, stock badge, click
│   ├── SessionTab.tsx         (NEW) Running list of items added to this session
│   └── TabItemRow.tsx         (NEW) Single row: item name, qty stepper, line total, remove
api/
├── pos.ts                     (NEW) fetchMenu, addPosItem, removePosItem, fetchSessionItems + hooks
├── featureFlags.ts            (NEW) fetchFeatureFlags, useFeatureFlags hook
store/
├── featureFlagStore.ts        (NEW) Zustand store for cached feature flags
types/
├── pos.ts                     (NEW) MenuItem, SessionPOSItem interfaces
hooks/
├── useFormatPaise.ts          (NEW) formatPaise(paise: int) → "Rs. X.XX"
```

### Modified Files

| File | Change |
|---|---|
| `components/SeatGrid.tsx` | IN_USE click → open `SessionDrawer` instead of `SeatActionModal` |
| `App.tsx` | Initialize feature flags on mount (wrap in `QueryClientProvider` level) |

---

## Data Flow

### Feature Flag Bootstrap
```
App mounts → useFeatureFlags() → GET /api/settings
→ extract flags from response → populate featureFlagStore
→ all components read flags via useFeatureFlags()
```

### POS Item Lifecycle
```
SessionDrawer opens (seat IN_USE, sessionId known)
  │
  ├─ POSPanel mounts, checks flags.enable_pos
  ├─ useMenu() → GET /api/menu → caches 5 min
  ├─ useSessionItems(sessionId) → GET /api/pos/items/{sessionId}
  │
  ├─ Click MenuItemCard
  │   ├─ useAddPosItem().mutate({session_id, menu_item_id, quantity: 1})
  │   ├─ POST /api/pos/items → 201
  │   └─ onSuccess → invalidate ['sessionItems', sessionId]
  │
  ├─ Click [+] on TabItemRow
  │   └─ Same as above (adds one more row, UI groups by menu_item_id)
  │
  ├─ Click [-] on TabItemRow
  │   └─ removePosItem({pos_item_id: one row's id, session_id})
  │       → DELETE /api/pos/items/{id}?session_id={sessionId}
  │       → onSuccess → invalidate ['sessionItems', sessionId]
  │
  └─ Click [✕] on TabItemRow
      └─ If multiple rows for same item: remove all of them
         → Promise.all(removePosItem for each row)
```

---

## UI States

### MenuItemCard States

| State | Visual | Clickable? |
|---|---|---|
| Available, stock ≥ threshold | Green badge "In Stock" (if inventory ON) | Yes |
| Low stock (0 < stock ≤ threshold) | Yellow badge "Low Stock (N left)" | Yes |
| Out of stock (stock = 0) | Red badge "Out of Stock", 50% opacity | **No** |
| `is_available = false` | Greyed out entirely, strikethrough price | **No** |
| No inventory tracking (`enable_inventory` OFF) | No stock badge | Yes |
| Inventory tracking ON but `stock_quantity = null` | No badge (unlimited stock) | Yes |

### SessionTab States

| State | Visual |
|---|---|
| Empty | "No items added yet" placeholder with muted icon |
| Has items | Grouped rows with +/- steppers, subtotal at bottom |
| Fetch error | "Failed to load items" with retry button |
| Mutation loading | Row shows spinner overlay; +/- buttons disabled |

### SessionDrawer States

| State | Visual |
|---|---|
| Opening | Slide-in animation (~300ms, ease-out) |
| POS tab active | Menu grid (left) + Session tab (right) |
| Checkout tab | Placeholder "Checkout coming soon" (Feature 3.2.2) |
| Commands tab | Placeholder |
| Closing | Slide-out animation or instant on backdrop click |
| `enable_pos` OFF | POS tab hidden; Checkout tab shows (when built) |

---

## Error Handling

| Scenario | Handling |
|---|---|
| `GET /api/menu` fails | Error banner in menu grid area: "Failed to load menu" + Retry button. Session tab unaffected. |
| `POST /api/pos/items` fails (409 seat unavailable) | Inline toast: "Cannot add items — session is not active" |
| `POST /api/pos/items` fails (404 item) | Toast: "Item not found in menu" |
| `DELETE /api/pos/items/{id}` fails | Toast: "Failed to remove item. Please retry." |
| Network error (any) | Toast with error message. React Query retries 3 times with exponential backoff. |
| `enable_pos` flag OFF | POS tab not rendered in drawer. No API calls made. |
| `enable_inventory` flag OFF | Stock badges hidden. All available items clickable. `stock_quantity`/`low_stock_threshold` not displayed. |
| Drawer closed during mutation | AbortController cancels pending fetches. React Query keeps cache. |

---

## Types (`types/pos.ts`)

```typescript
export interface MenuItem {
  id: string;
  name: string;
  category: string | null;
  price_paise: number;
  stock_quantity: number | null;
  low_stock_threshold: number | null;
  is_available: boolean;
  created_at: string;
  updated_at: string;
}

export interface SessionPOSItem {
  id: string;
  session_id: string;
  menu_item_id: string;
  quantity: number;
  unit_price_paise: number;
  added_at: string;
}
```

## Feature Flag Types

```typescript
export interface FeatureFlags {
  enable_members: boolean;
  enable_packages: boolean;
  enable_pos: boolean;
  enable_inventory: boolean;
  enable_reservations: boolean;
  enable_vouchers: boolean;
  enable_tournaments: boolean;
  enable_expense_tracking: boolean;
  enable_health_monitoring: boolean;
  require_member_for_session: boolean;
}
```

---

## Testing Plan

| Test File | Coverage |
|---|---|
| `pos/MenuGrid.test.tsx` | Renders items; stock badge colors; greyed-out items not clickable; category grouping; empty menu; fetch error + retry |
| `pos/MenuItemCard.test.tsx` | Price in Rs.; click handler; disabled states (stock=0, is_available=false); badge visibility gated by inventory flag |
| `pos/SessionTab.test.tsx` | Empty state; grouped items display; subtotal calculation; +/- fires mutations; ✕ removes all grouped rows; loading spinner |
| `pos/TabItemRow.test.tsx` | Line total = unit_price × quantity; +/- click handlers; ✕ handler; disabled during mutation |
| `pos/POSPanel.test.tsx` | Gated by enable_pos flag; passes sessionId to children; menu grid + session tab rendered |
| `SessionDrawer.test.tsx` | Opens on IN_USE click; tab switching; close button/Escape; POS tab renders POSPanel; Checkout tab shows placeholder |
| `api/pos.test.ts` | fetchMenu typed response; addPosItem body; removePosItem query params; error paths |
| `api/featureFlags.test.ts` | fetchFeatureFlags parses settings; useFeatureFlags returns cached flags; defaults when fetch fails |
| `store/featureFlagStore.test.ts` | Initial state; setFlags; getFlag; clear |
| `useFormatPaise.test.ts` | 0 → "Rs. 0.00"; 100 → "Rs. 1.00"; 25050 → "Rs. 250.50"; throws on negative |

### Manual Verification

1. Start backend, seed dev data (`python backend/scripts/seed_dev.py`)
2. Start dashboard, log in as cashier/admin
3. Start a session on a seat
4. Click the IN_USE seat → verify drawer slides in
5. Click menu items → verify they appear in session tab
6. Use +/- and ✕ buttons → verify correct behavior
7. Toggle `enable_pos` OFF in settings → verify POS tab hidden
8. Toggle `enable_inventory` OFF → verify stock badges hidden

---

## SRS Traceability

| Requirement | Implementation |
|---|---|
| FR-POS-001: Add items to any open session tab | `POST /api/pos/items` via `useAddPosItem` mutation |
| FR-POS-002: Items associated with seat | `session_id` FK (backend enforced) |
| FR-POS-003: Invoice itemizes all POS items | `SessionTab` shows running total; checkout in Feature 3.2.2 |
| FR-POS-004: Menu items configurable in Settings | `GET /api/menu` fetches configured items |
| FR-INV-003: Low-stock badge on POS screen | Yellow badge when `stock_quantity ≤ low_stock_threshold` |
| FR-INV-004: Out-of-stock items greyed out | Red badge + opacity + not clickable when `stock_quantity = 0` |
| NFR-USE-005: Feature-flag gated | `POSPanel` reads `flags.enable_pos`; hidden when OFF |
| NFR-DATA-002: Paise→rupees at display layer only | `formatPaise()` utility — all components use it |

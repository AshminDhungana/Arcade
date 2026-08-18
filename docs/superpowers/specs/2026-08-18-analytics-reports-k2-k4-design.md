# Section K — Analytics & Reports: K.2 Expense Tracking & K.4 Mobile Owner View

**Date:** 2026-08-18
**Status:** Approved for implementation
**Scope:** Complete K.2 (Expense Tracking + P&L) and K.4 (Mobile Owner View) — K.1 and K.3 already done.

---

## K.2 Expense Tracking & P&L Reports

### 1. Backend API

#### Expense Router — `/api/expenses`
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/` | Admin | List all expenses (newest first) |
| POST | `/` | Admin | Create expense |
| DELETE | `/{expense_id}` | Admin | Delete expense |

**Request/Response Schemas:**
```python
# POST /api/expenses
class ExpenseCreate(BaseModel):
    date: date                    # ISO date string
    category: ExpenseCategory     # RENT, ELECTRICITY, INTERNET, RESTOCK, HARDWARE, MAINTENANCE, WAGES, OTHER
    amount_paise: int             # positive integer
    note: str | None = None       # optional, max 1000 chars

# Response
class ExpenseResponse(BaseModel):
    id: str
    date: date
    category: ExpenseCategory
    amount_paise: int
    note: str | None
    logged_by_staff_id: str
    created_at: datetime
```

#### P&L Service — `services/pl_service.py`
```python
class PLSummary(BaseModel):
    period_start: date
    period_end: date
    # Revenue
    session_revenue_paise: int
    pos_revenue_paise: int
    total_revenue_paise: int
    # Expenses (grouped by category)
    expenses_by_category: dict[ExpenseCategory, int]
    total_expenses_paise: int
    # Profit
    gross_profit_paise: int          # == total_revenue_paise (no COGS tracking yet)
    net_profit_paise: int            # gross - total_expenses
```

**Functions:**
- `get_pl_summary(db, start_date, end_date) -> PLSummary`
- `get_monthly_pl(db, year, month) -> PLSummary`

#### P&L Router — `/api/reports/pl`
| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/summary` | Admin | P&L for query range (`?start=YYYY-MM-DD&end=YYYY-MM-DD`, defaults to current month) |
| GET | `/monthly/{year}/{month}` | Admin | Monthly P&L statement |

---

### 2. Frontend

#### Settings → Expenses Tab
- **List view**: Table with columns Date, Category, Amount, Note, Actions (delete)
- **Add Expense Modal**: Date picker, Category select (enum), Amount (₹ input → paise), Note textarea
- **Validation**: Amount > 0, date not in future, category required
- **Toast** on success/error

#### Settings → P&L Tab
- **Period selector**: Month picker (default current) + custom range button
- **Summary cards**: Total Revenue, Total Expenses, Net Profit (green/red)
- **Category breakdown table**: Category | Amount | % of Expenses
- **Monthly statement**: Same view scoped to selected month

---

### 3. Data Model (Already Exists)
```python
class Expense(Base):
    id: str (PK)
    date: date
    category: ExpenseCategory (enum)
    amount_paise: int
    note: str | None
    logged_by_staff_id: str (FK → staff.id)
    created_at: datetime
```

---

## K.4 Mobile Owner View — `/mobile`

### 1. Route & Auth
- **Route**: `/mobile` (public, no sidebar/nav shell)
- **Auth**: Staff PIN login (reuse `useAuthStore.login()` flow)
  - Login page at `/mobile` if not authenticated
  - Redirect to `/mobile/dashboard` on success
  - Session persists via existing JWT in localStorage

### 2. Mobile Dashboard — `/mobile/dashboard`
**Layout**: Single-column card grid (CSS Grid, responsive)
```
┌─────────────────────┐
│   Today's Revenue   │  ← Large ₹ number, green
│     ₹ 12,345.00     │
├─────────────────────┤
│   Active Sessions   │  ← Count + live indicator
│        7            │
├─────────────────────┤
│    Shift Summary    │  ← Float, Revenue, Expected Cash, Variance
│  Float: ₹5,000      │
│  Revenue: ₹12,345   │
│  Expected: ₹17,345  │
│  Variance: +₹200   │
├─────────────────────┤
│      Top Zones      │  ← Top 3 by utilisation%
│  VIP: 85% ████████  │
│  Standard: 62% ████ │
│  Budget: 41% ████   │
└─────────────────────┘
```

**Data Sources** (already available):
- `GET /api/analytics/summary` → `total_revenue_paise`, `session_count`, `zone_utilisation`
- `GET /api/shifts/current` → `float_paise`, `total_revenue_paise`, `expected_cash_paise`, `variance_paise`

**Real-time Updates:**
- Subscribe to existing WebSocket (`useWebSocket`)
- On `session_*` / `shift_*` messages → refetch both endpoints
- Optimistic UI: show stale data with subtle "updating" shimmer

**Responsive Design:**
- Container: `max-w-md mx-auto px-4 py-6`
- Cards: `bg-card rounded-xl border p-4 shadow-sm`
- Tap targets: `min-h-[44px]` on all interactive elements
- Font: `text-3xl` for revenue, `text-xl` for counts
- Works at 375px (iPhone SE) up to tablet

---

## Implementation Order

1. **K.2 Backend**: Expense router + P&L service + P&L router + tests
2. **K.2 Frontend**: Settings tabs (Expenses + P&L)
3. **K.4 Backend**: None needed (reuse existing endpoints)
4. **K.4 Frontend**: `/mobile` route + login + dashboard cards + WS integration

---

## Testing

### K.2
- `test_expense_router.py` — CRUD + auth (admin only)
- `test_pl_service.py` — math correctness (revenue - expenses = net)
- `test_pl_router.py` — summary + monthly endpoints
- Frontend: `ExpensesTab.test.tsx`, `PLTab.test.tsx`

### K.4
- `test_mobile_auth.py` — PIN login flow
- `test_mobile_dashboard.py` — card data matches API
- E2E: `mobile.spec.ts` — login → dashboard → real-time update

---

## Acceptance Criteria (from TODO.md)

- [ ] **K.2** Expense tracking — log rent/electricity/restock/wages; verify gross vs net P&L estimate
- [ ] **K.4** Mobile owner view — open `/mobile` on phone on cafe WiFi; verify responsive cards: today's revenue, active sessions, shift summary, top zones; real-time updates without refresh

---

## Out of Scope (Deferred)
- COGS tracking per menu item (true gross profit)
- Expense recurring/scheduled entries
- P&L export (PDF/CSV)
- Mobile push notifications
- Offline-first mobile caching

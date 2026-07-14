# Arcade Operator Guide

Practical, day-to-day procedures for counter staff and owners. Each workflow lists the
operator actions and the underlying API call (see `api-reference.md` for full request/response
schemas). All calls require a `Bearer` JWT from `POST /api/auth/login`.

> Fields named `*_paise` are in paise (1 rupee = 100 paise). `5000` paise = Rs. 50.00.

---

## Shift Open / Close

Open a shift at the start of each working day (or each cashier's till session) and close it
when you hand over or cash out. Only one shift can be open at a time.

### Open a shift

1. From the dashboard, open **Shifts** and choose **Open Shift**.
2. Enter the **opening float** in **rupees** (cash already in the drawer).
   - API: `POST /api/shifts/open` with `{"float_paise": <paise>}` → `201` returns the open `ShiftResponse` (`status: "OPEN"`). Omit `float_paise` for `0`.
   - If a shift is already open you get `409` `SHIFT_ALREADY_OPEN` — close the existing shift first.
3. Keep the shift id; every session started now is tied to this shift automatically.

### Close a shift

1. From **Shifts**, choose **Close Shift**.
2. Count the cash in the drawer and enter the **counted total** in **rupees**.
   - API: `POST /api/shifts/close` with `{"counted_paise": <paise>}` → `200` returns the closed `ShiftResponse`.
   - If no shift is open you get `409` `NO_OPEN_SHIFT`.
3. Review the **reconciliation**: `variance = counted − expected`, where
   `expected = float + cash_collected`. A non-zero variance means the drawer differs from the
   system — investigate before sign-off. (`variance_paise` is `null` while the shift is still open.)

### View the shift report (Admin)

- API: `GET /api/shifts/{shift_id}/report` → `ShiftReportResponse` with `session_count`,
  `invoice_count`, `total_revenue_paise`, `pos_total_paise`, `cash_collected_paise`,
  `expected_cash_paise`, and `variance_paise`.
- The currently open shift: `GET /api/shifts/current` → `ShiftResponse | null`.

---

## Member Management

Create and look up members so they can be attached to sessions and accumulate loyalty points.

1. **Open the dashboard** and go to **Members**.
2. **Create a member:** fill in name + phone (phone must be unique) and optional birth month, then Save.
   - API: `POST /api/members` with `{"name", "phone", "birth_month?"}` → `201` returns the new `MemberResponse` (tier starts at `BRONZE`).
   - If the phone already exists you get `409`; choose a different number or search for the existing member.
3. **Find a member:** type into the search box (matches name or phone).
   - API: `GET /api/members?q=<term>` (empty `q` lists all; `limit`/`offset` for paging).
4. **Open a session for a member:** from the seat grid, start a session and pick the member in the
   session-start modal. The member's active package (if any) is auto-attached and drawn down at checkout.
5. **View history:** open a member to see session history (`GET /api/members/{id}/sessions`) and the
   wallet ledger (`GET /api/members/{id}/transactions`).

**Tiers & loyalty:** loyalty points accrue per minute played (default 1 pt/min, configurable). At 500
points the member becomes `SILVER`, at 1000 `GOLD`. These thresholds are set in `AppSettings`.

---

## Wallet Top-up

Add funds to a member's wallet so they can pay for sessions, packages, or POS items with `WALLET`.

1. **Open the member** in the Members page.
2. **Top up:** enter the amount in **rupees**, choose a payment method (`CASH` / `CARD` / `WALLET`),
   and confirm.
   - API: `POST /api/members/{member_id}/topup` with `{"amount_paise": <paise>, "payment_method": "CASH"}` → `200` returns the updated member.
   - `amount_paise` must be > 0 or you get `400`.
3. **Verify:** the wallet balance increases and a `TOPUP` row appears in the member's transaction history
   (`GET /api/members/{member_id}/transactions`), tagged with the staff ID and payment method.
4. **Audit:** every top-up writes a `WALLET_TOPUP` entry to the immutable audit log.

> Wallet balance is spent at checkout (session time + POS) and when buying a package with
> payment_method: WALLET. It is never auto-refunded.

---

## Package Selling

Sell a time package (e.g. 2-hour bundle, day pass) to a member. The package becomes an entitlement
with a remaining-minute balance that is drawn down automatically during sessions.

1. **List available packages** (Admin manages these in Settings).
   - API: `GET /api/packages` → array of active `PackageResponse` (`type`, `total_minutes`, `price_paise`).
2. **Open the member** and choose **Sell Package**.
3. **Select the package** and a payment method:
   - `WALLET` → deducted from the member's wallet balance (fails with `400` if insufficient).
   - `CASH` / `CARD` → recorded as a payment; wallet unchanged.
   - API: `POST /api/members/{member_id}/packages` with `{"package_id", "payment_method"}` → `201` returns a
     `MemberPackageEntitlementResponse` (`remaining_minutes`, `status: ACTIVE`, optional `expires_at`).
4. **At checkout:** if the member has an active entitlement, the session draws down `ceil(elapsed_minutes)`
   from `remaining_minutes`. Once it hits 0 the entitlement becomes `EXHAUSTED`; any overflow time is billed
   per-minute from the wallet/cash.
5. **Audit:** package sales write a `PACKAGE_SOLD` entry and a `PACKAGE_PURCHASE` wallet ledger row
   (negative amount when paid by wallet).

**Notes**
- Packages are feature-flagged by `enable_packages`; if disabled the API returns `503`.
- A member may hold multiple entitlements; checkout uses the oldest active, non-expired one (FIFO).

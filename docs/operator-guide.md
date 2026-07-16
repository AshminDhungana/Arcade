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

## Reservations

Book a seat for a customer ahead of time. Reservations are on by default
(`enable_reservations=true`); if the feature is off the API returns `503`.

1. **Open Reservations** on the dashboard and choose **New Reservation**.
2. **Pick a seat**, enter the **customer name** (required), and the **from** / **until** times.
   Optionally attach a **member** (for loyalty) and a **note**. Leave status as `PENDING`.
   - API: `POST /api/reservations` with `{seat_id, customer_name, reserved_from, reserved_until?, member_id?, notes?}` → `201` returns `ReservationResponse`.
   - If the seat is already booked in that window you get `409`; if the seat doesn't exist, `404`.
3. **Confirm** the booking when the customer confirms (e.g. pays a deposit): set status to `CONFIRMED`.
   - API: `PATCH /api/reservations/{id}` with `{"status": "CONFIRMED"}` → `200`. (Only valid from `PENDING`; otherwise `409`.)
4. **Auto-reserve:** about 2 minutes before `reserved_from`, the server automatically sets the
   seat to `RESERVED` (only if it is still `AVAILABLE`), so it shows as booked on the seat grid.
5. **At arrival:** start the session on that seat as normal (see Member Management step 4). The
   reservation becomes `COMPLETED` once a session consumes it.
6. **Cancel** if the customer doesn't show:
   - API: `PATCH /api/reservations/{id}` with `{"status": "CANCELLED"}` → `200`. The seat is
     released back to `AVAILABLE` (allowed from `PENDING`/`CONFIRMED`; not from `COMPLETED`).
7. **List/audit:** `GET /api/reservations` (filter by `seat_id`, `member_id`, `reservation_status`).

**Statuses:** `PENDING` → `CONFIRMED` → `COMPLETED`; or `CANCELLED` from `PENDING`/`CONFIRMED`.

## Handling a Frozen / Unresponsive PC

The **server is the source of truth for billing** — a frozen client PC does NOT stop the
session timer. Act fast so the customer isn't over-billed, and so the seat is freed.

1. **Check the seat status** on the dashboard seat grid:
   - `OFFLINE` / `UNREACHABLE` → the agent process is down or the PC lost power/network.
   - Still `IN_USE` but no response → the PC or agent is wedged.
2. **Try a restart via the dashboard** (Remote Commands → Restart, or `POST /api/seats/{id}/restart`, Admin).
   The agent gets `RESTART` with a ~10-second grace delay and audits `SEAT_RESTARTED`. If the
   agent is offline the call returns `503` — move to step 3.
3. **If the PC is off / agent offline:** use **Wake-on-LAN** (`POST /api/seats/{id}/wol`, Admin)
   to boot it, or — for console seats on a Tuya smart plug — **Tuya power-on**
   (`POST /api/seats/{id}/power-on`, Admin; see `docs/deployment.md`). The seat goes `BOOTING`;
   if no agent registers within 60 s it becomes `UNREACHABLE`.
4. **Shut down hard** if restart won't work (e.g. wedged OS): `POST /api/seats/{id}/shutdown`
   (Admin), or physically hold the power button / toggle the Tuya plug.
5. **Stop billing:** once the PC is back or you've taken it out of service, **pause or end the
   session** from the seat modal so the customer isn't charged for downtime
   (`PATCH /api/sessions/{id}/pause` then checkout, or checkout directly).
6. **Known limitation:** on Windows, `Ctrl+Alt+Del` is OS-protected and **cannot** be
   intercepted by the kiosk overlay — a determined user can reach the secure desktop. For a
   truly frozen machine, prefer the dashboard restart/shutdown or the physical/Tuya power
   toggle over hoping the overlay responds.

> If the screen is merely frozen but the game is still running, a **screenshot**
> (`GET /api/seats/{id}/screenshot`, Cashier+) can confirm what the customer sees — but a
> wedged agent returns `503` (offline) or `504` (no response within 3 s).

---

## Feature Flags (Settings → Feature Flags)

### Require Print Before Release
When ON, a checkout does not free the seat or show the agent overlay until the receipt prints. Recovery paths for a failed print:
- **Reprint** (thermal) — succeeds → seat released.
- **Print the PDF receipt and click "Mark printed"** — counts as printed.
- **Force close with your own PIN + a reason** — releases the seat, logs `CHECKOUT_FORCED_UNPRINTED`, leaves the invoice as `FAILED`.

Turn this OFF immediately if the printer dies and you need checkouts to proceed without printing.

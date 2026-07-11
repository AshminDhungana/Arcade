# Arcade API Reference

> **Base URL:** `http://<server-ip>:8000/api`
>
> **Auth:** All endpoints require a valid JWT in the `Authorization: Bearer <token>` header.
>   Rate-limited: 5 failed login attempts per IP -> 15-minute lockout.

---

## Seat Endpoints

### `GET /api/seats`

List all seats with their current status. Cashier role required.

**Auth:** Bearer token (Cashier or Admin)

**Request:**
```
GET /api/seats
Authorization: Bearer <jwt>
```

**Response (200 OK):**
```json
[
  {
    "id": "seat_001",
    "name": "PC 1",
    "zone_id": "zone_001",
    "mac_address": "aa:bb:cc:dd:ee:01",
    "status": "AVAILABLE",
    "plug_id": null,
    "is_console": false,
    "notes": null,
    "created_at": "2026-07-06T08:00:00+00:00",
    "updated_at": "2026-07-06T10:00:00+00:00",
    "wol_attempts": 3,
    "wol_successes": 2,
    "wol_failures": 1
  }
]
```

---

### `GET /api/seats/{id}`

Get details for a single seat. Returns 404 if the seat does not exist.

**Auth:** Bearer token (Cashier or Admin)

**Request:**
```
GET /api/seats/seat_001
Authorization: Bearer <jwt>
```

**Response (200 OK):**
```json
{
  "id": "seat_001",
  "name": "PC 1",
  "zone_id": "zone_001",
  "mac_address": "aa:bb:cc:dd:ee:01",
  "status": "AVAILABLE",
  "plug_id": null,
  "is_console": false,
  "notes": null,
  "created_at": "2026-07-06T08:00:00+00:00",
  "updated_at": "2026-07-06T10:00:00+00:00",
  "wol_attempts": 3,
  "wol_successes": 2,
  "wol_failures": 1
}
```

**Response (404 Not Found):**
```json
{
  "detail": "Seat not found"
}
```

---

### `PATCH /api/seats/{id}/maintenance`

Set a seat to `MAINTENANCE` status. Admin role required.

**Auth:** Bearer token (Admin only)

**Request:**
```
PATCH /api/seats/seat_001/maintenance
Authorization: Bearer <jwt>
Content-Type: application/json

{
  "note": "GPU fan replacement in progress"
}
```

**Response (200 OK):**
```json
{
  "id": "seat_001",
  "name": "PC 1",
  "zone_id": "zone_001",
  "mac_address": "aa:bb:cc:dd:ee:01",
  "status": "MAINTENANCE",
  "plug_id": null,
  "is_console": false,
  "notes": "GPU fan replacement in progress",
  "created_at": "2026-07-06T08:00:00+00:00",
  "updated_at": "2026-07-06T12:00:00+00:00",
  "wol_attempts": 3,
  "wol_successes": 2,
  "wol_failures": 1
}
```

---

### `DELETE /api/seats/{id}/maintenance`

Clear `MAINTENANCE` status and set seat to `AVAILABLE`. Admin role required.

**Auth:** Bearer token (Admin only)

**Request:**
```
DELETE /api/seats/seat_001/maintenance
Authorization: Bearer <jwt>
```

**Response (200 OK):** Seat with `status` changed to `AVAILABLE`.

---

### `POST /api/seats/{id}/wol`

Send a Wake-on-LAN magic packet. Admin role required.

**Auth:** Bearer token (Admin only)

**Request:**
```
POST /api/seats/seat_001/wol
Authorization: Bearer <jwt>
```

**Response (200 OK):**
```json
{
  "id": "seat_001",
  "name": "PC 1",
  "zone_id": "zone_001",
  "mac_address": "aa:bb:cc:dd:ee:01",
  "status": "AVAILABLE",
  "plug_id": null,
  "is_console": false,
  "notes": null,
  "created_at": "2026-07-06T08:00:00+00:00",
  "updated_at": "2026-07-06T10:00:00+00:00",
  "wol_attempts": 4,
  "wol_successes": 2,
  "wol_failures": 1
}
```

---

### `POST /api/seats/{id}/wol/override`

Manually mark a seat as online. Admin role required.

**Auth:** Bearer token (Admin only)

**Request:**
```
POST /api/seats/seat_001/wol/override
Authorization: Bearer <jwt>
```

**Response (200 OK):** Seat with `status` changed to `AVAILABLE`.

---

### Seat Status Reference

| Value        | Meaning                                       |
|--------------|-----------------------------------------------|
| `AVAILABLE`  | Empty and ready for a session                 |
| `IN_USE`     | Active session running                        |
| `PAUSED`     | Session paused, timer not running             |
| `RESERVED`   | Reserved for a future booking                 |
| `MAINTENANCE`| Out of service                                |
| `OFFLINE`    | Agent disconnected                            |
| `BOOTING`    | Wake-on-LAN sent, waiting for agent         |
| `UNREACHABLE`| Agent did not register within 60 seconds    |

---

## Session Endpoints

### `POST /api/sessions`

Start a new session on an available seat.

**Auth:** Bearer token (Cashier or Admin)

**Request:**
```
POST /api/sessions
Authorization: Bearer <jwt>
Content-Type: application/json

{
  "seat_id": "seat_001",
  "member_id": "member_001"
}
```

**Response (201 Created):**
```json
{
  "seat_id": "seat_001",
  "member_id": "member_001",
  "shift_id": null,
  "locked_rate_paise": 50,
  "locked_pricing_model": "PER_MINUTE",
  "package_entitlement_id": null,
  "promotion_id": null,
  "discount_paise": 0,
  "payment_method": null,
  "id": "session_123",
  "status": "ACTIVE",
  "started_at": "2026-07-06T10:00:00+00:00",
  "ended_at": null,
  "paused_at": null,
  "total_paused_seconds": 0,
  "created_at": "2026-07-06T10:00:00+00:00",
  "updated_at": "2026-07-06T10:00:00+00:00"
}
```

---

### `PATCH /api/sessions/{id}/pause`

Pause an active session. The timer stops and the kiosk overlay is re-shown.

**Auth:** Bearer token (Cashier or Admin)

**Request:**
```
PATCH /api/sessions/session_123/pause
Authorization: Bearer <jwt>
```

---

### `PATCH /api/sessions/{id}/resume`

Resume a paused session. The timer restarts and the kiosk overlay is hidden.

**Auth:** Bearer token (Cashier or Admin)

**Request:**
```
PATCH /api/sessions/session_123/resume
Authorization: Bearer <jwt>
```

---

### `GET /api/sessions/active`

List all active or paused sessions.

**Auth:** Bearer token (Cashier or Admin)

**Request:**
```
GET /api/sessions/active
Authorization: Bearer <jwt>
```

---

### `GET /api/sessions/{id}`

Get a single session by ID.

**Auth:** Bearer token (Cashier or Admin)

**Request:**
```
GET /api/sessions/session_123
Authorization: Bearer <jwt>
```

---

### Session Status Reference

| Value       | Meaning                        | Billing Active |
|-------------|--------------------------------|----------------|
| `ACTIVE`    | Timer running                  | Yes            |
| `PAUSED`    | Timer frozen                   | No             |
| `COMPLETED` | Session ended normally         | -              |
| `ABANDONED` | Ended without checkout         | -              |

---

## Authentication Endpoints

### `POST /api/auth/login`

Authenticate a staff member and receive a JWT access token.

**Auth:** None (public, rate-limited)

**Rate Limiting:** 5 failed attempts per IP within 15 minutes -> HTTP 429 with Retry-After header.

**Request:**
```
POST /api/auth/login
Content-Type: application/json

{
  "staff_id": "admin001",
  "pin": "0000"
}
```

**Response (201 Created):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 28800,
  "staff": {
    "id": "admin001",
    "name": "Admin User",
    "role": "ADMIN",
    "is_active": true,
    "updated_at": "2026-07-06T08:00:00+00:00"
  }
}
```

**Response (401 Unauthorized):**
```json
{
  "detail": "Invalid PIN"
}
```

**Response (429 Too Many Requests):**
```json
{
  "detail": "Too many failed attempts. Retry after <timestamp>."
}
```

---

### `POST /api/auth/refresh`

Extend the expiry of a valid JWT. The token_version is checked against the database.

**Auth:** Bearer token

**Request:**
```
POST /api/auth/refresh
Authorization: Bearer <jwt>
```

**Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer",
  "expires_in": 28800,
  "staff": {
    "id": "admin001",
    "name": "Admin User",
    "role": "ADMIN",
    "is_active": true,
    "updated_at": "2026-07-06T08:00:00+00:00"
  }
}
```

**Response (401 Unauthorized - stale token):**
```json
{
  "detail": "Token version mismatch"
}
```

---

### `POST /api/auth/logout`

Client-side token discard (stateless).

**Auth:** Bearer token

**Request:**
```
POST /api/auth/logout
Authorization: Bearer <jwt>
```

**Response (200 OK):**
```json
{
  "detail": "Logged out successfully"
}
```

---

### Staff Role and Common Errors

| Role      | Permissions                                         |
|-----------|-----------------------------------------------------|
| `ADMIN`   | Full access - seat management, staff, settings     |
| `CASHIER` | Manage sessions, POS checkout, view analytics      |

**Common HTTP Errors:**

| Status | Reason                                    |
|--------|-------------------------------------------|
| 401    | Missing or invalid JWT                    |
| 403    | Valid JWT but role lacks permission       |
| 422    | Request body validation failure           |
| 429    | Rate limited (login only)                |
| 500    | Unexpected server error                   |

---

## Invoice Endpoints

### `GET /api/invoices/{id}`

Get details for a single invoice. Cashier role required.

**Auth:** Bearer token (Cashier or Admin)

**Response (200 OK):**
```json
{
  "id": "inv_123",
  "session_id": "session_123",
  "member_id": "member_001",
  "shift_id": "shift_001",
  "time_charge_paise": 30000,
  "package_credit_used_paise": 15000,
  "discount_paise": 3000,
  "pos_total_paise": 25000,
  "total_paise": 37000,
  "payment_method": "CASH",
  "created_at": "2026-07-06T12:00:00+00:00",
  "line_items": [
    {
      "id": "li_1",
      "invoice_id": "inv_123",
      "type": "TIME_CHARGE",
      "description": "Time charge (PER_MINUTE)",
      "quantity": 1,
      "unit_price_paise": 30000,
      "total_paise": 30000
    }
  ]
}
```

---

### `GET /api/invoices/{id}/pdf`

Get print-friendly HTML receipt. Cashier role required.

**Auth:** Bearer token (Cashier or Admin)

**Response (200 OK):**
HTML content that automatically triggers `window.print()` on load.

---

## Checkout Endpoint

### `POST /api/sessions/{session_id}/checkout`

Checkout and complete a gaming session, generating the finalized invoice. Cashier role required.

**Auth:** Bearer token (Cashier or Admin)

**Request:**
```json
{
  "payment_method": "CASH"
}
```

**Response (201 Created):**
Invoice response object (same as `GET /api/invoices/{id}`).

---

## POS Endpoints

These endpoints are feature-flagged and only available when `enable_pos` is set to `true`.

### `GET /api/pos/menu`

List all menu items for POS counter display. Cashier role required.

**Auth:** Bearer token (Cashier or Admin)

**Response (200 OK):**
```json
[
  {
    "id": "item_123",
    "name": "Cold Coke",
    "category": "Drinks",
    "price_paise": 150,
    "stock_quantity": 10,
    "low_stock_threshold": 3,
    "is_available": true
  }
]
```

---

### `POST /api/pos/items`

Add a POS item order to an active session. Cashier role required.

**Auth:** Bearer token (Cashier or Admin)

**Request:**
```json
{
  "session_id": "session_123",
  "menu_item_id": "item_123",
  "quantity": 2
}
```

**Response (201 Created):**
```json
{
  "id": "pos_item_123",
  "session_id": "session_123",
  "menu_item_id": "item_123",
  "quantity": 2,
  "unit_price_paise": 150,
  "added_at": "2026-07-06T11:00:00+00:00"
}
```

---

### `DELETE /api/pos/items/{pos_item_id}`

Remove a POS item from a session. Cashier role required.

**Auth:** Bearer token (Cashier or Admin)

**Request Parameters:**
- `session_id`: Query parameter (string, required)

**Response (200 OK):**
```json
{
  "deleted": true,
  "pos_item_id": "pos_item_123"
}
```

---

### `GET /api/pos/items/{session_id}`

List all POS items currently ordered for a given session. Cashier role required.

**Auth:** Bearer token (Cashier or Admin)

**Response (200 OK):**
Array of SessionPOSItem response objects.

---

## Inventory Endpoints

These endpoints are feature-flagged and only available when `enable_inventory` is set to `true`.

### `POST /api/inventory/restock`

Restock a menu item, resetting its stock quantity and marking it available if it was out of stock. Admin role required.

**Auth:** Bearer token (Admin only)

**Request:**
```json
{
  "menu_item_id": "item_123",
  "quantity": 50,
  "note": "Restocking drinks shipment"
}
```

**Response (200 OK):**
MenuItem response object (same as `GET /api/pos/menu` items).

---

### `GET /api/inventory/low-stock`

List all menu items that are at or below their low-stock threshold. Cashier role required.

**Auth:** Bearer token (Cashier or Admin)

**Response (200 OK):**
Array of MenuItem response objects.

---

## WebSocket Endpoints

Arcade uses two distinct WebSocket channels: one for dashboard clients (React app) and one for agent clients (Electron kiosk overlay).

All messages use the standard JSON envelope:

```json
{
  "type": "EVENT_TYPE",
  "payload": { ... },
  "timestamp": "2026-07-06T10:00:00+00:00"
}
```

### `GET /ws/dashboard`

Dashboard clients connect here to receive real-time events. Primarily a listener channel.

**Connection:**
```
wss://<server-ip>:8000/ws/dashboard
```

| Event Type     | Payload                          | Description                |
|----------------|-----------------------------------|----------------------------|
| `seat_updated` | `seat_id`, `status`, seat data   | Seat status changed        |
| `health_update`| `seat_id`, `cpu_percent`, ...    | Agent health metrics       |
| `announcement` | `text`, `type`                   | System-wide announcement   |
| `alert`        | `type`, `seat_id`, `message`     | Staff override, low time   |

---

### `GET /ws/agent/{seat_id}?secret=<agent_secret>`

Each gaming PC connects here. The `secret` is validated against `agent_secrets` in the server config.

**Connection:**
```
wss://<server-ip>:8000/ws/agent/seat_001?secret=<agent_secret>
```

**Agent -> Server messages:**

| Type   | Payload                                      | When Sent              |
|--------|----------------------------------------------|------------------------|
| `REGISTER` | `seat_id`, `mac_address`, `hostname`, ... | On connection          |
| `SYNC`     | `session_id`, `local_elapsed_seconds`       | After reconnection     |
| `HEALTH`   | `cpu_percent`, `ram_percent`, ...          | Every 60 seconds       |
| `STAFF_OVERRIDE` | `seat_id`, `verified`               | Override PIN accepted  |
| `PONG`     | `{}`                                         | Heartbeat response     |

**Server -> Agent commands:**

| Command         | Payload Fields               | Trigger                          |
|-----------------|------------------------------|----------------------------------|
| `HIDE_OVERLAY`  | `session_id`, `started_at`   | Session starts                   |
| `SHOW_OVERLAY`  | `session_id`                   | Session ends or pauses          |
| `SHOW_MESSAGE`  | `text`, `duration_seconds`   | Announcement sent                |
| `RESTART`       | `delay_seconds?`             | Admin triggers restart           |
| `SHUTDOWN`      | `delay_seconds?`             | Admin triggers shutdown          |
| `TAKE_SCREENSHOT` | `{}`                        | Screenshot request               |
| `LOW_TIME_WARNING` | `minutes_remaining`         | Package time <= 5 min            |
| `RESET_OVERRIDE` | `{}`                         | Clear staff override             |

---

### Heartbeat and Reconnection

- Server sends `PING` every 30 seconds.
- Agent must reply with `PONG` within 10 seconds.
- Missing `PONG` -> server closes connection (code 1001).
- Agent reconnects automatically with exponential backoff (1s -> 2s -> 4s ... capped at 30s + jitter).

---

## Package Endpoints

These endpoints are feature-flagged and only available when `enable_packages` is set to `true`.

### `GET /api/packages`

List all active packages available for sale. Cashier role required.

**Auth:** Bearer token (Cashier or Admin)

**Request:**
```
GET /api/packages
Authorization: Bearer <jwt>
```

**Response (200 OK):**
```json
[
  {
    "id": "pkg_abc123",
    "name": "2 Hour Bundle",
    "type": "HOUR_BUNDLE",
    "total_minutes": 120,
    "price_paise": 20000,
    "valid_days": 30,
    "zone_restriction_id": null,
    "is_active": true,
    "created_at": "2026-01-15T10:30:00Z"
  }
]
```

**Response (503 Service Unavailable):**
Feature `enable_packages` is disabled.
```json
{
  "detail": "Feature 'enable_packages' is currently disabled."
}
```

---

### `POST /api/members/{member_id}/packages`

Sell a package to a member. Cashier role required.

**Auth:** Bearer token (Cashier or Admin)

**Path Parameters:**
- `member_id` (string): Member UUID

**Request Body:**
```json
{
  "package_id": "pkg_abc123",
  "payment_method": "WALLET"
}
```

**Response (201 Created):**
```json
{
  "id": "ent_xyz789",
  "member_id": "mem_123",
  "package_id": "pkg_abc123",
  "remaining_minutes": 120,
  "expires_at": "2026-02-14T10:30:00Z",
  "status": "ACTIVE",
  "purchased_at": "2026-01-15T10:30:00Z",
  "updated_at": "2026-01-15T10:30:00Z"
}
```

**Errors:**
- `400`: Insufficient wallet balance, inactive package, invalid payment method
- `404`: Member not found, package not found
- `401`: Unauthorized
- `503`: Feature `enable_packages` disabled

---
## Member Endpoints

All Member endpoints are feature-flagged (`enable_members`) and require a Cashier+ JWT.
When the flag is off, every route returns `503` with
`{"detail": "Feature 'enable_members' is currently disabled."}`.

### `GET /api/members`

Search members by name or phone, or list all when `q` is empty. Cashier+ required.

**Query Parameters:**
- `q` (string, optional): search term (name/phone); empty lists all
- `limit` (int, 1–200, default 50): page size
- `offset` (int, ≥0, default 0): page offset

**Response (200 OK):**
```json
[
  {
    "id": "mem_123",
    "name": "Aarav Sharma",
    "phone": "9800000001",
    "birth_month": 5,
    "wallet_balance_paise": 5000,
    "loyalty_points": 120,
    "tier": "BRONZE",
    "total_visits": 3,
    "total_seconds_played": 7200,
    "created_at": "2026-07-06T08:00:00+00:00",
    "updated_at": "2026-07-06T10:00:00+00:00"
  }
]
```

---

### `POST /api/members`

Create a new member. Tier defaults to `BRONZE`. Phone must be unique. Cashier+ required.

**Request Body:**
```json
{
  "name": "Aarav Sharma",
  "phone": "9800000001",
  "birth_month": 5
}
```

**Response (201 Created):**
```json
{
  "id": "mem_123",
  "name": "Aarav Sharma",
  "phone": "9800000001",
  "birth_month": 5,
  "wallet_balance_paise": 0,
  "loyalty_points": 0,
  "tier": "BRONZE",
  "total_visits": 0,
  "total_seconds_played": 0,
  "created_at": "2026-07-06T08:00:00+00:00",
  "updated_at": "2026-07-06T08:00:00+00:00"
}
```

**Errors:**
- `409`: Phone already registered (`{"detail": "Phone number <phone> already registered"}`)
- `422`: Missing/over-length field

---

### `GET /api/members/{member_id}`

Get a single member by ID. Cashier+ required.

**Response (200 OK):** Member object (same shape as `GET /api/members` items).

**Response (404 Not Found):** `{"detail": "Member <member_id> not found"}`

---

### `POST /api/members/{member_id}/topup`

Add funds to a member's wallet and write a `WALLET_TOPUP` audit entry + ledger row. Cashier+ required.

**Request Body:**
```json
{
  "amount_paise": 5000,
  "payment_method": "CASH"
}
```

**Response (200 OK):** Updated Member object (wallet_balance_paise increased).

**Errors:**
- `400`: `amount_paise` ≤ 0
- `404`: Member not found
- `503`: `enable_members` disabled

---

### `GET /api/members/{member_id}/sessions`

Member session history (most recent first). Cashier+ required.

**Response (200 OK):** Array of `SessionResponse` objects (see Session Endpoints for shape). `404` if member not found.

---

### `GET /api/members/{member_id}/transactions`

Wallet ledger history, newest first. Cashier+ required.

**Query Parameters:** `limit` (1–200, default 50), `offset` (≥0, default 0).

**Response (200 OK):**
```json
[
  {
    "member_id": "mem_123",
    "type": "TOPUP",
    "amount_paise": 5000,
    "balance_after_paise": 5000,
    "payment_method": "CASH",
    "staff_id": "admin001",
    "reference_id": null,
    "created_at": "2026-07-06T09:30:00+00:00"
  },
  {
    "member_id": "mem_123",
    "type": "PACKAGE_PURCHASE",
    "amount_paise": -20000,
    "balance_after_paise": 5000,
    "payment_method": "WALLET",
    "staff_id": "admin001",
    "reference_id": "ent_xyz789",
    "created_at": "2026-07-06T09:35:00+00:00"
  }
]
```

**Errors:** `404` if member not found.

---

## Promotion Endpoints

Promotions are Admin-only (all routes) and feature-flagged (`enable_promotions`).
Note: promotion *evaluation* is automatic and internal — `PromotionService.get_applicable_promotion()`
runs at session start and locks a match onto the session's `promotion_id`. These endpoints only
manage the promotion catalogue.

### `GET /api/promotions`

List all promotions (active and inactive). Admin only.

**Response (200 OK):**
```json
[
  {
    "id": "promo_001",
    "name": "Evening Happy Hour",
    "type": "HAPPY_HOUR",
    "discount_type": "PERCENTAGE",
    "discount_value": 20,
    "active_days": "MON,TUE,WED,THU,FRI",
    "active_from_hour": 18,
    "active_to_hour": 22,
    "min_group_size": null,
    "zone_restriction_id": null,
    "is_active": true,
    "valid_from": null,
    "valid_until": null
  }
]
```

---

### `POST /api/promotions`

Create a promotion. Admin only.

**Request Body:**
```json
{
  "name": "Evening Happy Hour",
  "type": "HAPPY_HOUR",
  "discount_type": "PERCENTAGE",
  "discount_value": 20,
  "active_days": "MON,TUE,WED,THU,FRI",
  "active_from_hour": 18,
  "active_to_hour": 22,
  "is_active": true
}
```

**Response (201 Created):** The created Promotion object (same shape as list items, with `id`).

**Errors:** `403` non-admin; `422` validation (e.g. `discount_value` < 0, invalid enum).

---

### `GET /api/promotions/{promotion_id}`

Get a single promotion by ID. Admin only.

**Response (200 OK):** Promotion object.
**Response (404 Not Found):** `{"detail": "Promotion not found"}`

---

### `PATCH /api/promotions/{promotion_id}`

Update promotion fields (partial). Admin only.

**Request Body (all fields optional):**
```json
{
  "is_active": false,
  "discount_value": 25
}
```

**Response (200 OK):** Updated Promotion object.
**Response (404 Not Found):** `{"detail": "Promotion not found"}`

**Field notes:**
- `active_days`: comma-separated `MON,TUE,...,SUN` (uppercase, 3-letter).
- `active_from_hour` / `active_to_hour`: hour-of-day window (0–23).
- `valid_from` / `valid_until`: absolute date range (UTC) or `null`.
- `type` ∈ `HAPPY_HOUR | FLASH | FIRST_VISIT | GROUP | BIRTHDAY`.
- `discount_type` ∈ `PERCENTAGE | FIXED_PAISE | BONUS_MINUTES`.

## Voucher Endpoints

Vouchers are feature-flagged (`enable_vouchers`). Batch generation is Admin-only;
redemption requires Cashier+.

A voucher is **monetary** (`value_paise` set) or **time** (`value_minutes` set) — never both.
Monetary vouchers credit the member wallet on redemption. Time vouchers are **not** wallet-credited;
they are consumed via package drawdown at session checkout.

### `POST /api/vouchers/batch`

Generate a batch of vouchers with unique 12-char codes. Admin only.

**Request Body:**
```json
{
  "count": 50,
  "value_paise": 10000,
  "expires_in_days": 30
}
```
(For time vouchers, set `value_minutes` instead of `value_paise`. Exactly one of the two must be set.)

**Response (201 Created):**
```json
{
  "batch_id": "a1b2c3d4e5f6...",
  "count": 50,
  "vouchers": [
    {
      "id": "vouch_001",
      "code": "AB12CD34EF56",
      "value_paise": 10000,
      "value_minutes": null,
      "expires_at": "2026-08-05T10:00:00+00:00",
      "batch_id": "a1b2c3d4e5f6...",
      "status": "UNUSED",
      "redeemed_by_member_id": null,
      "redeemed_at": null,
      "created_at": "2026-07-06T10:00:00+00:00"
    }
  ]
}
```

**Errors:**
- `400`: `count` out of 1–10000; both/neither `value_paise`/`value_minutes` set; non-positive value
- `503`: `enable_vouchers` disabled

---

### `POST /api/vouchers/redeem`

Redeem a voucher for a member. Cashier or Admin required.

**Request Body:**
```json
{
  "code": "AB12CD34EF56",
  "member_id": "mem_123"
}
```

**Response (200 OK):** Updated `MemberResponse` object (wallet credited if `value_paise` set).

**Errors:**
- `404`: Voucher not found, or member not found
- `400`: Voucher already redeemed (`{"detail": "Voucher already redeemed"}`) or expired
- `503`: `enable_vouchers` disabled

## Staff Endpoints

Staff management. Most routes are Admin-only. `PATCH /api/staff/{staff_id}/pin` additionally allows
the account owner (self) to change their own PIN. PIN changes, deactivation, and reactivation all
increment `token_version`, immediately invalidating every existing JWT for that staff member.

`StaffResponse` never includes `pin_hash` or `token_version`.

### `POST /api/staff`

Create a staff member. Admin only. PIN is hashed with Argon2id; new staff start at `token_version=0`.

**Request Body:**
```json
{
  "name": "Bob Cashier",
  "role": "CASHIER",
  "is_active": true,
  "pin": "1234"
}
```

**Response (201 Created):**
```json
{
  "id": "cashier001",
  "name": "Bob Cashier",
  "role": "CASHIER",
  "is_active": true,
  "updated_at": "2026-07-06T08:00:00+00:00"
}
```

**Errors:** `403` non-admin; `422` invalid PIN (must be 4–20 chars) or role.

---

### `PATCH /api/staff/{staff_id}/pin`

Update a staff member's PIN. Admin or the staff member themselves. Increments `token_version`.

**Request Body:**
```json
{ "pin": "5678" }
```

**Response (200 OK):** Updated `StaffResponse`.

**Errors:** `403` if caller is neither Admin nor the target; `422` invalid PIN.

---

### `PATCH /api/staff/{staff_id}/deactivate`

Deactivate a staff member. Admin only. Sets `is_active=false` and increments `token_version`.

**Response (200 OK):** Updated `StaffResponse` with `"is_active": false`.

---

### `PATCH /api/staff/{staff_id}/reactivate`

Reactivate a previously deactivated staff member. Admin only. Sets `is_active=true` and increments `token_version`.

**Response (200 OK):** Updated `StaffResponse` with `"is_active": true`.

---

### `GET /api/staff`

List all staff members. Admin only.

**Response (200 OK):** Array of `StaffResponse` objects.

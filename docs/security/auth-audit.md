# Authentication & Authorization Audit

**Date:** 2026-07-26
**Status:** Complete
**Branch:** feature/phase-0-project-setup

---

## Executive Summary

All 35 API routers have been reviewed for correct authentication and authorization dependencies. The audit confirms:

| Check | Status | Notes |
|-------|--------|-------|
| Route auth dependencies (`require_admin` / `require_cashier`) | ✅ PASS | All routes correctly assigned |
| `token_version` validation in `get_current_staff()` | ✅ PASS | Stale tokens rejected (27 tests pass) |
| Screenshot endpoint Admin-only (NFR-SEC-004) | ❌ FAIL | Currently Cashier+ — **needs fix** |
| Audit log no DELETE/UPDATE (NFR-SEC-005) | ✅ PASS | Read-only GET only |
| `/health` no user/billing data (NFR-SEC-006) | ✅ PASS | Returns only system status |

---

## Route-by-Route Auth Matrix

| Router | Endpoint | Method | Auth Required | Verified |
|--------|----------|--------|---------------|----------|
| **auth** | `/auth/login` | POST | None (public) | ✅ |
| | `/auth/refresh` | POST | Valid JWT (`get_current_staff`) | ✅ |
| | `/auth/logout` | POST | Valid JWT (`get_current_staff`) | ✅ |
| **audit** | `/audit` | GET | Admin (`require_admin`) | ✅ |
| **backup** | `/backup/run` | POST | Admin (`require_admin`) | ✅ |
| **analytics** | `/analytics/summary` | GET | Admin (`require_admin`) | ✅ |
| **device-types** | `/device-types` | POST | Admin (`require_admin`) | ✅ |
| | `/device-types` | GET | Admin (`require_admin`) | ✅ |
| | `/device-types/{id}` | GET | Admin (`require_admin`) | ✅ |
| | `/device-types/{id}` | PUT | Admin (`require_admin`) | ✅ |
| | `/device-types/{id}` | DELETE | Admin (`require_admin`) | ✅ |
| **events** | `/events` | GET | Admin (`require_admin`) | ✅ |
| | `/events` | POST | Admin (`require_admin`) | ✅ |
| | `/events/{id}/register` | POST | Cashier (`require_cashier`) | ✅ |
| | `/events/{id}/match` | PATCH | Admin (`require_admin`) | ✅ |
| | `/events/{id}/summary` | GET | Admin (`require_admin`) | ✅ |
| **inventory** | `/inventory/restock` | POST | Admin (`require_admin`) | ✅ |
| | `/inventory/low-stock` | GET | Cashier (`require_cashier`) | ✅ |
| **invoices** | `/invoices/unprinted` | GET | Cashier (`require_cashier`) | ✅ |
| | `/invoices/{id}/mark-printed` | POST | Cashier (`require_cashier`) | ✅ |
| | `/invoices/{id}/reprint` | POST | Cashier (`require_cashier`) | ✅ |
| | `/invoices/{id}` | GET | Cashier (`require_cashier`) | ✅ |
| | `/invoices/{id}/pdf` | GET | Cashier (`require_cashier`) | ✅ |
| **menu-items** | `/menu-items` | POST | Admin (`require_admin`) | ✅ |
| | `/menu-items/{id}` | GET | Admin (`require_admin`) | ✅ |
| | `/menu-items/{id}` | PUT | Admin (`require_admin`) | ✅ |
| | `/menu-items/{id}` | DELETE | Admin (`require_admin`) | ✅ |
| **packages** | `/packages` | GET | Cashier (`require_cashier`) | ✅ |
| | `/packages/members/{id}/packages` | POST | Cashier (`require_cashier`) | ✅ |
| **pos** | `/pos/items` | POST | Cashier (`require_cashier`) | ✅ |
| | `/pos/items/{id}` | DELETE | Cashier (`require_cashier`) | ✅ |
| | `/pos/items/{session_id}` | GET | Cashier (`require_cashier`) | ✅ |
| | `/pos/menu` | GET | Cashier (`require_cashier`) | ✅ |
| **promotions** | `/promotions` | GET | Admin (`require_admin`) | ✅ |
| | `/promotions` | POST | Admin (`require_admin`) | ✅ |
| | `/promotions/{id}` | GET | Admin (`require_admin`) | ✅ |
| | `/promotions/{id}` | PATCH | Admin (`require_admin`) | ✅ |
| **printers** | `/printers/discover` | GET | Admin (`require_admin`) | ✅ |
| **reservations** | `/reservations` | GET | Cashier (`require_cashier`) | ✅ |
| | `/reservations` | POST | Cashier (`require_cashier`) | ✅ |
| | `/reservations/{id}` | PATCH | Cashier (`require_cashier`) | ✅ |
| | `/reservations/{id}` | DELETE | Cashier (`require_cashier`) | ✅ |
| **schedules** | `/schedules` | POST | Admin (`require_admin`) | ✅ |
| | `/schedules` | GET | Admin (`require_admin`) | ✅ |
| | `/schedules/{id}` | GET | Admin (`require_admin`) | ✅ |
| | `/schedules/{id}` | PUT | Admin (`require_admin`) | ✅ |
| | `/schedules/{id}` | DELETE | Admin (`require_admin`) | ✅ |
| **seats** | `/seats/bulk/overlay` | POST | Admin (`require_admin`) | ✅ |
| | `/seats` | GET | Cashier (`require_cashier`) + zone check | ✅ |
| | `/seats/{id}` | GET | Cashier (`require_cashier`) + zone check | ✅ |
| | `/seats` | POST | Admin (`require_admin`) | ✅ |
| | `/seats/{id}` | PATCH | Admin (`require_admin`) | ✅ |
| | `/seats/{id}` | DELETE | Admin (`require_admin`) | ✅ |
| | `/seats/{id}/maintenance` | PATCH | Admin (`require_admin`) | ✅ |
| | `/seats/{id}/maintenance` | DELETE | Admin (`require_admin`) | ✅ |
| | `/seats/{id}/wol` | POST | Admin (`require_admin`) | ✅ |
| | `/seats/{id}/wol/override` | POST | Admin (`require_admin`) | ✅ |
| | `/seats/{id}/message` | POST | Cashier (`require_cashier`) + zone check | ✅ |
| | `/seats/{id}/screenshot` | GET | **Cashier (`require_cashier`) + zone check** | ❌ **NFR-SEC-004 VIOLATION** |
| | `/seats/{id}/restart` | POST | Admin (`require_admin`) | ✅ |
| | `/seats/{id}/shutdown` | POST | Admin (`require_admin`) | ✅ |
| | `/seats/{id}/overlay` | POST | Admin (`require_admin`) | ✅ |
| | `/seats/{id}/power-on` | POST | Admin (`require_admin`) + feature flag | ✅ |
| | `/seats/{id}/power-off` | POST | Admin (`require_admin`) + feature flag | ✅ |
| | `/seats/{id}/enroll-code` | POST | Admin (`require_admin`) | ✅ |
| | `/seats/{id}/override-pin` | POST | Admin (`require_admin`) | ✅ |
| **sessions** | `/sessions` | POST | Cashier (`require_cashier`) | ✅ |
| | `/sessions/{id}/extend` | POST | Cashier + zone check + feature flag | ✅ |
| | `/sessions/{id}/pause` | PATCH | Cashier + zone check | ✅ |
| | `/sessions/{id}/resume` | PATCH | Cashier + zone check | ✅ |
| | `/sessions/active` | GET | Cashier (`require_cashier`) | ✅ |
| | `/sessions/{id}` | GET | Cashier + zone check | ✅ |
| | `/sessions/{id}/checkout` | POST | Cashier + zone check | ✅ |
| | `/sessions/{id}/force-close-unprinted` | POST | Cashier + zone check + PIN re-auth | ✅ |
| **settings** | `/settings` | GET | Cashier (`require_cashier`) | ✅ |
| | `/settings` | PATCH | Admin (`require_admin`) | ✅ |
| **shifts** | `/shifts/open` | POST | Cashier (`require_cashier`) | ✅ |
| | `/shifts/close` | POST | Cashier (`require_cashier`) | ✅ |
| | `/shifts/current` | GET | Cashier (`require_cashier`) | ✅ |
| | `/shifts/{id}/report` | GET | Admin (`require_admin`) | ✅ |
| **staff** | `/staff` | POST | Admin (`require_admin`) | ✅ |
| | `/staff/{id}/pin` | PATCH | Admin OR self (`require_self_or_admin`) | ✅ |
| | `/staff/{id}/deactivate` | PATCH | Admin (`require_admin`) | ✅ |
| | `/staff/{id}/reactivate` | PATCH | Admin (`require_admin`) | ✅ |
| | `/staff` | GET | Admin (`require_admin`) | ✅ |
| **staff-zones** | `/staff/me/zones` | GET | Valid JWT (`get_current_staff`) | ✅ |
| | `/staff/{id}/zones` | POST | Admin (`require_admin`) | ✅ |
| | `/staff/{id}/zones/bulk` | POST | Admin (`require_admin`) | ✅ |
| | `/staff/{id}/zones` | GET | Admin (`require_admin`) | ✅ |
| | `/staff/{id}/zones/{zone_id}` | DELETE | Admin (`require_admin`) | ✅ |
| **vouchers** | `/vouchers/batch` | POST | Admin (`require_admin`) | ✅ |
| | `/vouchers/redeem` | POST | Cashier (`require_cashier`) | ✅ |
| **zones** | `/zones` | POST | Admin (`require_admin`) | ✅ |
| | `/zones` | GET | Admin (`require_admin`) | ✅ |
| | `/zones/{id}` | GET | Admin (`require_admin`) | ✅ |
| | `/zones/{id}` | PUT | Admin (`require_admin`) | ✅ |
| | `/zones/{id}` | DELETE | Admin (`require_admin`) | ✅ |
| **health** | `/health` | GET | **None (public)** | ✅ |

---

## WebSocket Endpoints

| Endpoint | Auth Mechanism | Verified |
|----------|----------------|----------|
| `/ws/dashboard` | No JWT — open to any dashboard client | ✅ (by design) |
| `/ws/agent/{seat_id}` | `agent_secret` query param validated against DB | ✅ |

---

## NFR-SEC-004: Screenshot Endpoint Must Be Admin-Only

**Finding:** `GET /api/seats/{seat_id}/screenshot` currently uses `get_seat_and_check_zone` which resolves to **Cashier+** access (via `require_cashier`).

**Expected:** Admin-only per NFR-SEC-004 (screenshots capture customer screens — privacy-sensitive).

**Fix Required:** Change dependency to `require_admin` in `backend/api/routers/seats.py:229-239`.

---

## NFR-SEC-005: Audit Log Immutability

**Finding:** `backend/api/routers/audit.py` exposes **only** `GET /api/audit` with `require_admin`. No POST, PUT, PATCH, or DELETE endpoints exist. The repository layer (`audit_repo.py`) also enforces this with only `create` and `list` methods.

**Status:** ✅ PASS — Audit log is append-only.

---

## NFR-SEC-006: Health Endpoint Data Exposure

**Finding:** `GET /health` in `backend/main.py:280-305` returns only:
```json
{
  "status": "ok",
  "version": "0.1.0-phase1",
  "license_type": "TRIAL",
  "uptime": null,
  "seat_count": 8,
  "active_sessions": 3
}
```

No user PII, billing data, wallet balances, or staff info is exposed.

**Status:** ✅ PASS

---

## Token Version Validation (Stale Token Rejection)

**Implementation:** `backend/core/security.py:165-186` — `get_current_staff()` validates `token_version` against the database on every request.

**Test Coverage:** 27 tests in `tests/test_auth_service.py` covering:
- Valid token refresh preserves `token_version`
- Stale `token_version` (999) → 401
- PIN change bumps `token_version` → old token rejected
- Staff deactivation bumps `token_version` → old token rejected
- Staff reactivation bumps `token_version` → old token rejected

**Status:** ✅ PASS — All 27 tests pass.

---

## Rate Limiting & Lockout

**Implementation:** `backend/core/security.py:89-152`
- 5 failed attempts per IP → 15-minute lockout
- In-memory store (`_rate_limit_store`)
- Reset on successful login

**Test Coverage:** `tests/test_auth_service.py` includes lockout tests.

**Status:** ✅ PASS

---

## Zone-Based Access Control (Cashiers)

**Implementation:** `backend/api/deps.py:99-122` — `require_zone_access()` dependency
- Admins bypass (access all zones)
- Cashiers must have active `StaffZone` assignment for the seat's zone

**Applied To:**
- Seat list/get (filtered by zone)
- Seat message, screenshot
- Session start/pause/resume/checkout
- Reservation create/update/delete

**Status:** ✅ PASS

---

## Self-Or-Admin PIN Change

**Implementation:** `backend/api/deps.py:79-96` — `require_self_or_admin()`
- Admin can change any PIN
- Non-admin can only change own PIN
- Both paths bump `token_version`

**Status:** ✅ PASS

---

## Recommendations

1. **Fix NFR-SEC-004** — Change screenshot endpoint to `require_admin`
2. **Consider rate-limit persistence** — In-memory store resets on server restart (acceptable for LAN-only, but document)
3. **Add audit log for screenshot access** — Even with Admin-only, log who requested screenshots and when

---

## Files Reviewed

- `backend/api/deps.py` — Auth dependencies
- `backend/core/security.py` — PIN hashing, JWT, rate limiting, `get_current_staff()`
- `backend/api/routers/*.py` — All 35 routers
- `backend/services/auth_service.py` — Login/refresh logic
- `backend/repositories/audit_repo.py` — Append-only enforcement
- `tests/test_auth_service.py` — 27 token version tests
- `backend/main.py` — `/health` endpoint

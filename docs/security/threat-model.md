# Arcade Security — Threat Model

> Based on auth-audit.md findings (2026-07-26) and architecture per docs/architecture.md
> STRIDE methodology: Spoofing, Tampering, Repudiation, Information Disclosure, Denial of Service, Elevation of Privilege

---

## Threat Actors

| Actor | Description | Access Level |
|-------|-------------|--------------|
| **Local Network Attacker** | On same LAN (customer, compromised device); can sniff/inject traffic | Passive/Active network |
| **Malicious Staff** | Authenticated cashier or admin with dashboard access; insider threat | Valid JWT (Cashier/Admin) |
| **Compromised Client PC** | Malware on gaming machine; agent process or OS compromised | Local agent execution |
| **Physical Access** | Unattended counter PC or client machine; USB, keyboard access | Physical console |

---

## Attack Surface

| Surface | Components | Entry Points |
|---------|------------|--------------|
| **REST API** | 35 routers under `/api/*` | HTTP requests with Bearer JWT |
| **WebSocket — Dashboard** | `/ws/dashboard` | WS upgrade, no auth (by design) |
| **WebSocket — Agent** | `/ws/agent/{seat_id}?secret=` | WS upgrade + `agent_secret` query param |
| **Agent Enrollment** | Enroll code flow (UDP beacon + HTTP) | One-time code, 15-min expiry |
| **License Verification** | `license.key` file + Hardware ID | File read, `py-machineid` |
| **Config Files** | `arcade.config.json`, `agent.config.json` | File read (chmod 600) |
| **Database** | `arcade.db`, WAL files, backups | SQLite file access |
| **Backup Files** | `backups/arcade_*.db` | File read |

---

## STRIDE Analysis per Finding (from auth-audit.md)

### NFR-SEC-004: Screenshot Endpoint Cashier+ → Information Disclosure

| Aspect | Detail |
|--------|--------|
| **Threat** | Cashier captures customer screen without admin oversight |
| **STRIDE** | Information Disclosure |
| **Impact** | Privacy violation; potential credential capture |
| **Current State** | ❌ FAIL — endpoint used `require_cashier` |
| **Mitigation** | Changed to `require_admin`; add audit log entry `SCREENSHOT_TAKEN` with requester staff_id |
| **Residual Risk** | Admin can still capture screens — documented as operational capability |

### Rate Limiting In-Memory (Resets on Restart) → Denial of Service

| Aspect | Detail |
|--------|--------|
| **Threat** | Attacker triggers server restart to reset login lockout counter |
| **STRIDE** | Denial of Service |
| **Impact** | Brute-force PIN attempts bypass 15-min lockout |
| **Current State** | Documented limitation — in-memory `_rate_limit_store` |
| **Mitigation** | Acceptable for LAN-only deployment (attacker needs LAN access + server restart capability); document in threat model; consider Redis persistence in v2 |
| **Residual Risk** | Low — requires physical/admin access to restart server |

### Audit Log Immutability → Tampering / Repudiation

| Aspect | Detail |
|--------|--------|
| **Threat** | Attacker modifies/deletes audit entries to hide activity |
| **STRIDE** | Tampering, Repudiation |
| **Impact** | Loss of accountability for billing disputes, staff actions |
| **Current State** | ✅ PASS — Router only exposes `GET /api/audit`; Repository only `create` + `list`; no UPDATE/DELETE |
| **Mitigation** | Already enforced at router + repository layer; SQLite WAL prevents partial writes |

### Health Endpoint No PII → Information Disclosure

| Aspect | Detail |
|--------|--------|
| **Threat** | Unauthenticated `/health` exposes sensitive data |
| **STRIDE** | Information Disclosure |
| **Impact** | User PII, billing data, wallet balances leaked |
| **Current State** | ✅ PASS — Returns only `{status, version, license_type, uptime, seat_count, active_sessions}` |
| **Mitigation** | No changes needed; endpoint remains public for load balancer checks |

### Token Version Revocation → Elevation of Privilege

| Aspect | Detail |
|--------|--------|
| **Threat** | Stale JWT used after PIN change or staff deactivation |
| **STRIDE** | Elevation of Privilege |
| **Impact** | Deactivated staff retains access; PIN change doesn't lock out attacker |
| **Current State** | ✅ PASS — `get_current_staff()` validates `token_version` against DB on every request; 27 tests pass |
| **Mitigation** | Already implemented; immediate invalidation on PIN change, deactivation, reactivation |

### Zone-Based Cashier Access → Elevation of Privilege

| Aspect | Detail |
|--------|--------|
| **Threat** | Cashier accesses seats outside assigned zones |
| **STRIDE** | Elevation of Privilege |
| **Impact** | Unauthorized session management, billing manipulation |
| **Current State** | ✅ PASS — `require_zone_access()` dependency filters seat list, enforces zone on session start/pause/resume/checkout |
| **Mitigation** | Admins bypass (all zones); cashiers restricted to active `StaffZone` assignments |

### Self-or-Admin PIN Change → Tampering

| Aspect | Detail |
|--------|--------|
| **Threat** | Staff changes another staff's PIN without admin rights |
| **STRIDE** | Tampering |
| **Impact** | Unauthorized credential modification |
| **Current State** | ✅ PASS — `require_self_or_admin()` allows Admin any PIN, non-Admin only own PIN; both paths bump `token_version` |
| **Mitigation** | Already enforced at router dependency layer |

---

## Known Limitations (Accepted Risks)

| Limitation | STRIDE Category | Severity | Tracking | Mitigation |
|------------|-----------------|----------|----------|------------|
| **Ctrl+Alt+Del (Windows)** | Spoofing / Elevation | Critical | OS-protected | Group Policy disable Task Manager; physical security |
| **Win+D / Taskbar (Windows)** | Spoofing | High | electron#38020 | Replace shell (`explorer.exe`) for true kiosk; accept gap |
| **Wayland Kiosk Escapes** | Spoofing / Elevation | Critical | electron#50403 | Run under Cage/gnome-kiosk/ubuntu-frame compositor; recommend X11 for v1 |
| **macOS Cmd+Opt+Esc** | Spoofing | Critical | OS-protected | None — requires notarization + hardened runtime (v2) |
| **macOS Unsigned App** | Tampering | Medium | Gatekeeper re-prompts per rebuild | Notarization v2; document re-grant permissions |
| **Agent Offline Session Start** | Elevation | Medium | By design (FR-SES-010) | Prohibited — server is source of truth; simplifies reconciliation |
| **License Hardware Change** | Spoofing | Low | Manual process | Contact seller with new Hardware ID for reissue |

---

## Security Controls Summary

| Control | Implementation | Verification |
|---------|----------------|--------------|
| **Authentication — Staff** | Staff ID + PIN (Argon2id OWASP params) + JWT with `token_version` | 27 tests in `test_auth_service.py` |
| **Authentication — Agent** | Per-seat `agent_secret` (64-char hex, `secrets.token_hex(32)`) validated on every WS connect | `test_ac21_ws_secret.py` |
| **Authorization — Role** | `require_admin` / `require_cashier` dependencies on all routers | Auth audit: 35 routers verified |
| **Authorization — Zone** | `require_zone_access()` for cashiers; admins bypass | Applied to seats, sessions, reservations |
| **Authorization — Self-or-Admin** | `require_self_or_admin()` for PIN change | Tested in auth service |
| **Rate Limiting** | 5 failed logins/IP → 15-min lockout (in-memory) | Tested; documented limitation |
| **Audit Logging** | Immutable append-only; all sensitive ops logged | Router + repo enforce; `test_ac09_audit_immutability.py` |
| **Config Protection** | `chmod 600` on `arcade.config.json`, `agent.config.json`, `license.key` | Deployment guide enforces |
| **License Verification** | Offline Ed25519 signature + Hardware ID bind; no network call | ARCH-05 validated; `test_ac12_license_verification.py` |
| **Session Integrity** | Server source of truth; agent local cache + SYNC reconciliation (±5s) | ARCH-06 validated; `test_ac07_sync_reconcile.py` |
| **Kiosk Hardening** | Electron `kiosk:true`, `closable:false`, shortcut interception | ARCH-02 documented; per-OS gaps listed |

---

## Recommended Enhancements (v2)

1. **Persistent Rate Limiting** — Redis-backed store survives restarts
2. **Screenshot Audit Log** — Log every `SCREENSHOT_TAKEN` with staff_id, seat_id, timestamp
3. **TLS for LAN** — Optional mTLS for API/WS (currently plaintext on LAN)
4. **Notarized macOS Builds** — Stable code identity, no permission re-prompts
5. **Wayland Secure Compositor** — Document Cage/gnome-kiosk deployment path
6. **Hardware Security Module** — For license signing key custody
7. **Automated Secret Rotation** — Periodic `agent_secret` / `jwt_secret` rotation with zero-downtime

---

## References

- `docs/security/auth-audit.md` — Route-by-route auth verification (2026-07-26)
- `docs/architecture.md` — System architecture and component diagram
- `docs/PRODUCT_BRIEF.md` — Product overview and security decisions
- `docs/references/ARCH-02-kiosk-mode-validation.md` — Kiosk hardening verification
- `docs/references/ARCH-05-offline-license-validation.md` — License flow validation
- `docs/references/ARCH-06-websocket-reconnect-validation.md` — SYNC/reconciliation validation

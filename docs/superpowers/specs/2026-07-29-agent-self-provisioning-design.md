# Agent Self-Provisioning Design

**Date:** 2026-07-29
**Status:** Approved for Implementation
**Related:** `docs/agent-setup.md`, `docs/superpowers/plans/2026-07-15-agent-self-provisioning.md` (original plan)

---

## Overview

The Arcade Agent self-provisions on first launch — no hand-copied `agent.config.json` required. The agent discovers the server on LAN, enrolls using a one-time code from the dashboard, writes its own config, and relaunches into the kiosk overlay.

This document covers the **remaining three implementation items** needed to complete the feature (all other components are already implemented and working).

---

## Already Implemented (Reference)

| Component | Location | Status |
|-----------|----------|--------|
| UDP beacon server | `backend/core/lan_discovery.py` | ✅ Done |
| HTTP `/api/discovery` fallback endpoint | `backend/api/routers/agent.py:89` | ✅ Done |
| Enroll code generation (admin) | `backend/api/routers/seats.py:348` | ✅ Done |
| Agent enrollment endpoint | `backend/api/routers/agent.py:44` | ✅ Done |
| Enrollment service (generate/verify/consume) | `backend/services/enrollment_service.py` | ✅ Done |
| Agent discovery client (UDP) | `agent/src/main/discovery.ts` | ✅ Done |
| Agent enrollment flow | `agent/src/main/enroll.ts` | ✅ Done |
| First-run setup window | `agent/src/renderer/setup.html`, `setup.ts` | ✅ Done |
| Config persistence & relaunch | `agent/src/main/index.ts:71-89` | ✅ Done |
| Staff override dialog + Settings button | `agent/src/renderer/components/staff-override-dialog.ts` | ✅ Done |
| Ctrl+Shift+O shortcut | `agent/src/renderer/index.ts:99-121` | ✅ Done |

---

## Remaining Work (3 Items)

### 1. Build-Time Master PIN Injection

#### Current State
`agent/src/main/master-pin.ts` reads `ARCADE_MASTER_PIN` from `.env` or uses hardcoded `'1928'`, then hashes at runtime with Argon2id.

#### Design
- Add a build-time script that generates `src/main/master-pin.ts` with a **pre-computed Argon2id hash**
- The plaintext PIN is provided at build time (CI/CD secret or build arg) — never committed
- The generated file exports a constant hash; runtime hashing is removed
- At enrollment, `enroll.ts` writes this pre-computed hash directly to `agent.config.json` as `master_code_hash`

#### Generated File Structure
```typescript
// agent/src/main/master-pin.ts (GENERATED — DO NOT EDIT)
// Emergency master PIN hash, injected at build time.
// Plaintext PIN is provided via build secret; only the Argon2id hash is embedded.

export const MASTER_PIN_HASH = "$argon2id$v=19$m=4096,t=3,p=1$<salt>$<hash>";

/** Returns the pre-computed Argon2id hash of the emergency master PIN. */
export function resolveMasterPinHash(): string {
  return MASTER_PIN_HASH;
}
```

#### Build Script
```javascript
// agent/scripts/inject-master-pin.js
// Usage: node inject-master-pin.js --pin="1234" --out=src/main/master-pin.ts
// PIN is read from process.env.MASTER_PIN or --pin arg (CI secret).
```

#### Why
- Emergency master PIN must survive agent reinstall/reboot — baked into binary
- Plaintext PIN never in source, on disk, or in `.env` (which can be lost)
- Hash params match staff override PIN hashing (`m=4096, t=3, p=1`) for compatibility

---

### 2. HTTP `/api/discovery` Fallback in Agent

#### Current State
`discovery.ts` listens for UDP beacon on port 48123 for 4 seconds. On timeout, returns `null` with a `// TODO` comment for HTTP fallback.

#### Design
After UDP timeout, probe common LAN gateway IPs via HTTP `GET /api/discovery`:

```typescript
const COMMON_GATEWAYS = [
  '192.168.1.1', '192.168.0.1', '192.168.1.254', '192.168.0.254',
  '10.0.0.1', '10.0.1.1', '10.1.1.1',
  '172.16.0.1', '172.16.1.1',
];
```

- Probe up to 3 gateways in parallel (500ms timeout each)
- Return first successful `ws://host:port` from JSON response: `{ host: string, port: number, cafe_name?: string }`
- If all fail, return `null` → setup window shows "Server not found" error

#### Implementation Location
`agent/src/main/discovery.ts` — extend `discoverServer()` function

---

### 3. Master PIN Verification (Already Works)

The WebSocket client's `triggerStaffOverride()` in `agent/src/main/ws/client.ts:179` already implements the correct logic:

```typescript
async triggerStaffOverride(pin: string): Promise<'override' | 'master' | false> {
  const connected = this.isConnected();
  const overrideHash = this.config.override_code_hash;
  const masterHash = this.config.master_code_hash ?? null;

  // Staff override PIN works when connected
  if (overrideHash && (await verify(overrideHash, pin))) {
    this._activateOverride();
    return 'override';
  }
  // Master PIN ONLY when disconnected (emergency)
  if (!connected && masterHash && (await verify(masterHash, pin))) {
    this._activateOverride();
    return 'master';
  }
  return false;
}
```

**Only change needed:** `enroll.ts` must use the build-time injected `MASTER_PIN_HASH` instead of runtime `resolveMasterPin()`.

---

## Acceptance Criteria

| # | Criterion | Verification |
|---|-----------|--------------|
| 1 | Fresh agent install on LAN discovers server via UDP beacon ≤4s | Manual test on clean VM |
| 2 | If UDP blocked (firewall), discovers via HTTP `/api/discovery` on common gateways | Block UDP port 48123, test discovery |
| 3 | Setup window appears, user enters enroll code → agent enrolls, writes `agent.config.json`, relaunches into kiosk | End-to-end manual test |
| 4 | Enroll code is single-use, 15-min TTL, admin-only generation | Unit tests in `backend/tests/test_enroll_routers.py` |
| 5 | Emergency master PIN hash baked into binary at build time (no `.env`) | Inspect built `master-pin.js`, verify no `.env` read |
| 6 | Master PIN only works when server unreachable; staff override PIN works when connected | Test offline unlock vs online override |
| 7 | `Ctrl+Shift+O` opens staff override dialog; Settings button re-opens setup window | Manual test |

---

## File Changes Summary

| File | Change Type | Description |
|------|-------------|-------------|
| `agent/scripts/inject-master-pin.js` | **New** | Build script to generate master-pin.ts with Argon2id hash |
| `agent/src/main/master-pin.ts` | **Replace** | Generated file exporting pre-computed `MASTER_PIN_HASH` |
| `agent/src/main/enroll.ts` | **Modify** | Use `resolveMasterPinHash()` instead of `resolveMasterPin()` |
| `agent/src/main/discovery.ts` | **Modify** | Add HTTP fallback probing common gateways |
| `agent/package.json` | **Modify** | Add `inject-master-pin` script to build pipeline |

---

## Build Pipeline Integration

```json
// agent/package.json scripts
{
  "scripts": {
    "inject-master-pin": "node scripts/inject-master-pin.js --pin=$MASTER_PIN --out=src/main/master-pin.ts",
    "build": "npm run inject-master-pin && tsc -p tsconfig.main.json && tsc -p tsconfig.renderer.json && node scripts/copy-renderer-assets.mjs && electron-builder"
  }
}
```

- `MASTER_PIN` provided via CI/CD secret (GitHub Actions `secrets.MASTER_PIN`)
- Local dev: `MASTER_PIN=1234 npm run inject-master-pin` (uses default if not set)

---

## Security Notes

1. **Plaintext master PIN never written to disk** — only Argon2id hash in `agent.config.json`
2. **Master PIN hash baked into binary** — survives agent reinstall, no `.env` dependency
3. **Master PIN only accepted offline** — `triggerStaffOverride()` checks `isConnected()` first
4. **Enroll code single-use** — server clears `enroll_code_hash` after successful verification
5. **Enroll code 15-min TTL** — expires automatically, prevents stale code reuse

---

## Testing Strategy

| Test | Location | Type |
|------|----------|------|
| UDP discovery finds server | `agent/tests/enroll.test.ts` | Integration |
| HTTP fallback probes gateways | `agent/tests/discovery.test.ts` | Unit (mock fetch) |
| Enrollment writes config + relaunches | `agent/tests/enroll.test.ts` | Integration |
| Master PIN unlocks offline only | `agent/tests/master-pin.test.ts` | Unit |
| Build script generates valid hash | `agent/tests/inject-master-pin.test.ts` | Unit |
| Enroll code single-use + TTL | `backend/tests/test_enroll_routers.py` | Backend (existing) |

---

## Rollout Plan

1. Implement build script + master-pin.ts generation
2. Update enroll.ts to use injected hash
3. Implement HTTP discovery fallback
4. Run all tests (backend + agent)
5. Manual end-to-end test on clean Windows/Linux/macOS VMs
6. Update `docs/agent-setup.md` if any user-facing changes

---

## Out of Scope (v2 Enhancements)

- In-agent Settings: edit server URL, reconnect/health intervals (currently re-enroll only)
- Custom gateway list for HTTP discovery (hardcoded common gateways for v1)
- mDNS/Bonjour discovery as alternative to UDP + HTTP
- Automatic agent update from server

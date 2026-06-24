# Arcade — Folder Structure

---

## Project Structure

```
arcade/
├── docs/                           # Documentation
│
├── backend/                        # FastAPI server (cross‑platform)
│   ├── api/
│   │   ├── routers/                # Route handlers per domain
│   │   │   ├── seats.py
│   │   │   ├── sessions.py
│   │   │   ├── billing.py
│   │   │   ├── pos.py
│   │   │   ├── inventory.py
│   │   │   ├── members.py
│   │   │   ├── packages.py
│   │   │   ├── promotions.py
│   │   │   ├── vouchers.py
│   │   │   ├── reservations.py
│   │   │   ├── staff.py
│   │   │   ├── shifts.py
│   │   │   ├── expenses.py
│   │   │   ├── events.py
│   │   │   ├── analytics.py
│   │   │   ├── settings.py
│   │   │   ├── audit.py
│   │   │   └── ws.py               # WebSocket endpoint
│   │   └── deps.py                 # Dependencies: auth, DB session (AsyncSession), feature flags
│   │
│   ├── services/                   # Business logic (async)
│   │   ├── session_service.py
│   │   ├── billing_service.py
│   │   ├── pos_service.py
│   │   ├── member_service.py
│   │   ├── package_service.py
│   │   ├── promotion_service.py
│   │   ├── voucher_service.py
│   │   ├── reservation_service.py
│   │   ├── shift_service.py
│   │   ├── expense_service.py
│   │   ├── event_service.py
│   │   ├── analytics_service.py
│   │   ├── wol_service.py
│   │   ├── tuya_service.py
│   │   ├── print_service.py
│   │   ├── audit_service.py
│   │   └── backup_service.py       # Uses APScheduler AsyncIOScheduler
│   │
│   ├── repositories/               # All database queries (async, no business logic)
│   │   ├── seat_repo.py
│   │   ├── session_repo.py
│   │   ├── invoice_repo.py
│   │   ├── member_repo.py
│   │   ├── package_repo.py
│   │   ├── promotion_repo.py
│   │   ├── voucher_repo.py
│   │   ├── pos_repo.py
│   │   ├── inventory_repo.py
│   │   ├── reservation_repo.py
│   │   ├── shift_repo.py
│   │   ├── expense_repo.py
│   │   ├── event_repo.py
│   │   ├── staff_repo.py
│   │   └── audit_repo.py
│   │
│   ├── models/                     # SQLAlchemy ORM models (async-compatible)
│   │   ├── __init__.py
│   │   ├── seat.py
│   │   ├── session.py
│   │   ├── invoice.py
│   │   ├── member.py
│   │   ├── package.py
│   │   ├── promotion.py
│   │   ├── voucher.py
│   │   ├── menu_item.py
│   │   ├── reservation.py
│   │   ├── staff.py                # includes token_version INTEGER DEFAULT 0
│   │   ├── shift.py
│   │   ├── expense.py
│   │   ├── event.py
│   │   ├── audit_log.py
│   │   ├── settings.py
│   │   └── license_status.py       # Read-only cache for display
│   │
│   ├── schemas/                    # Pydantic request/response schemas
│   │   ├── seat.py
│   │   ├── session.py
│   │   ├── invoice.py
│   │   ├── member.py
│   │   ├── package.py
│   │   ├── promotion.py
│   │   ├── voucher.py
│   │   ├── pos.py
│   │   ├── reservation.py
│   │   ├── staff.py
│   │   ├── shift.py
│   │   ├── expense.py
│   │   ├── event.py
│   │   ├── analytics.py
│   │   ├── settings.py
│   │   └── audit.py
│   │
│   ├── licensing/                  # Offline license verification subsystem
│   │   ├── verify.py               # Ed25519 signature verification
│   │   ├── fingerprint.py          # Uses py-machineid (primary) + OS fallbacks
│   │   └── public_key.py           # Embedded Ed25519 public key (hardcoded)
│   │
│   ├── core/                       # Core infrastructure
│   │   ├── config.py               # arcade.config.json loader
│   │   ├── database.py             # SQLAlchemy AsyncEngine, WAL pragmas with busy_timeout=5000,
│   │   │                            # AsyncSessionLocal, get_db() dependency
│   │   ├── feature_flags.py        # Feature flag loader and checker (DB-backed)
│   │   ├── security.py             # Argon2id hashing (argon2-cffi), JWT with token_version,
│   │   │                            # rate limiting, lockout
│   │   └── ws_manager.py           # WebSocket connection manager (heartbeat, agent_secret validation)
│   │
│   ├── main.py                     # FastAPI app with lifespan context manager
│   ├── requirements.txt            # Python dependencies
│   └── alembic.ini                 # Alembic configuration (moved from root)
│
├── frontend/                       # React dashboard (Vite + TailwindCSS)
│   ├── src/
│   │   ├── pages/                  # Route pages
│   │   │   ├── Dashboard.tsx
│   │   │   ├── Session.tsx
│   │   │   ├── Checkout.tsx
│   │   │   ├── POS.tsx
│   │   │   ├── Members.tsx
│   │   │   ├── Packages.tsx
│   │   │   ├── Reservations.tsx
│   │   │   ├── Shifts.tsx
│   │   │   ├── Events.tsx
│   │   │   ├── Analytics.tsx
│   │   │   ├── Settings.tsx
│   │   │   └── Login.tsx
│   │   ├── components/             # Reusable UI components
│   │   │   ├── SeatCard.tsx
│   │   │   ├── SeatGrid.tsx
│   │   │   ├── SessionTimer.tsx
│   │   │   ├── InvoicePanel.tsx
│   │   │   ├── POSPanel.tsx
│   │   │   ├── MemberSearch.tsx
│   │   │   ├── HealthBadge.tsx
│   │   │   └── ...
│   │   ├── hooks/                  # Custom hooks
│   │   │   ├── useWebSocket.ts
│   │   │   ├── useSeats.ts
│   │   │   ├── useSession.ts
│   │   │   └── ...
│   │   ├── api/                    # React Query API client functions
│   │   ├── store/                  # Zustand/Context stores (auth, feature flags)
│   │   └── utils/
│   │       ├── currency.ts         # Paise → display conversion
│   │       └── time.ts
│   ├── index.html
│   ├── package.json
│   └── vite.config.ts
│
├── agent/                          # Electron client agent (cross‑platform)
│   ├── src/
│   │   ├── main/                   # Electron main process entry
│   │   │   ├── index.ts
│   │   │   ├── platform/           # Platform abstraction layer
│   │   │   │   ├── index.ts        # Exports unified PlatformService interface
│   │   │   │   │                    # (showKioskOverlay, hideKioskOverlay, updateTimer,
│   │   │   │   │                    #  restartPC, shutdownPC, captureScreenshot,
│   │   │   │   │                    #  sendAnnouncement, enableAutoStart, disableAutoStart)
│   │   │   │   ├── windows.ts
│   │   │   │   ├── macos.ts
│   │   │   │   └── linux.ts
│   │   │   ├── storage/            # Local SQLite for session persistence (better-sqlite3)
│   │   │   │   └── session_store.ts
│   │   │   ├── ipc/                # IPC handlers (kiosk overlay, screenshot, restart, shutdown)
│   │   │   │   └── handlers.ts
│   │   │   ├── ws/                 # WebSocket client to server (exponential backoff)
│   │   │   │   └── client.ts
│   │   │   ├── health/             # systeminformation collector (60s interval)
│   │   │   │   └── collector.ts
│   │   │   └── tray/               # System tray integration
│   │   │       └── tray.ts
│   │   ├── preload.ts              # Context bridge for IPC
│   │   └── renderer/               # React UI (kiosk overlay UI, splash, countdown, announcements)
│   │       ├── KioskOverlay.tsx    # Full‑screen kiosk overlay (branded, Call Staff button)
│   │       ├── SplashScreen.tsx    # 5‑second splash on session start
│   │       ├── CountdownOverlay.tsx # Low‑time warning popup
│   │       ├── Announcement.tsx    # Staff‑pushed announcements
│   │       └── App.tsx
│   ├── package.json
│   ├── electron-builder.yml        # Build config for all platforms
│   └── agent.config.json           # Per‑machine config (server_url, agent_secret) — chmod 600 on Linux/macOS
│
├── alembic/                        # Database migration scripts
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       ├── 001_initial.py
│       └── ...
│
├── tools/                          # INTERNAL — NOT SHIPPED TO CUSTOMERS
│   └── keygen/                     # Offline license key generation tool
│       ├── generate_license.py     # CLI tool — holds the private signing key
│       └── private_key.pem         # Ed25519 private key — NEVER committed to VCS
│
├── launcher.py                     # Tkinter GUI launcher (cross‑platform)
│                                   # - License Activation screen (py-machineid hardware ID)
│                                   # - Setup wizard (creates arcade.config.json with agent_secrets)
│                                   # - Server process management (starts FastAPI subprocess)
│                                   # - Live server logs display
│
├── arcade.config.json              # Runtime config (created by setup wizard — per server)
│                                   # Contains: cafe_name, host, port, db_path, backup settings,
│                                   # admin/cashier PIN hashes (Argon2id), jwt_secret,
│                                   # agent_secrets: {seat_id: agent_secret}
│
├── license.key                     # License file (placed by owner after activation — not in repo)
│
├── README.md
└── LICENSE                         # Apache 2.0
```

---

## Key Additions / Changes

| Directory / File                              | Purpose / Notes                                                                                                                                                                                                                                                                            |
| --------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **`backend/core/database.py`**                | **Async SQLAlchemy** with `AsyncSession` + `aiosqlite`. Configured with `busy_timeout=5000`, `synchronous=NORMAL`, `foreign_keys=ON`, `wal_autocheckpoint=1000`. `updated_at` fields are set explicitly in service code (`entity.updated_at = datetime.utcnow()`) — no `onupdate` trigger. |
| **`backend/core/security.py`**                | **Argon2id** hashing (via `argon2-cffi`) — OWASP-recommended. JWT with **60-minute expiry** and **`token_version`** claim for immediate revocation on PIN change/deactivation. Rate limiting (5 attempts/min/IP) and 60‑second lockout after 5 failed attempts.                            |
| **`backend/core/ws_manager.py`**              | Validates **agent_secret** on every REGISTER and reconnection. Rejects invalid/ missing secrets. Manages two connection registries: dashboards + agents. Heartbeat PING/PONG (30s interval). Rate-limits screenshots (at most one in‑flight per seat). Max message size: 5 MB.             |
| **`backend/models/seat.py`**                  | `status` enum includes: `AVAILABLE`, `IN_USE`, `RESERVED`, `PAUSED`, `MAINTENANCE`, `OFFLINE`, **`BOOTING`**, **`UNREACHABLE`**. `BOOTING` is set when a WoL packet is sent; `UNREACHABLE` is set if no agent heartbeat is received within 60 seconds.                                     |
| **`backend/services/wol_service.py`**         | Sends WoL magic packets on startup and on demand. After sending, sets seat status to `BOOTING` and starts a 60-second watchdog; sets status to `UNREACHABLE` if no agent REGISTER arrives within the window. Tracks per-seat WoL success/failure for the analytics dashboard.              |
| **`backend/licensing/fingerprint.py`**        | Uses **`py-machineid`** as primary source (no admin privileges). Fallbacks: `wmic`, `system_profiler`, `dmidecode`, `hdparm` only if `py-machineid` returns empty. Hashes result with SHA256 to produce consistent Hardware ID.                                                            |
| **`backend/services/backup_service.py`**      | Uses **APScheduler `AsyncIOScheduler`** (not `python-schedule`). Runs nightly at 3:00 AM. Retains configurable number of backups (default: 30 days). Integrated with FastAPI `lifespan` context manager.                                                                                   |
| **`backend/main.py`**                         | Uses **`lifespan` context manager** (FastAPI 0.93+). Startup: DB init, migrations, feature flags, WS manager, APScheduler. Shutdown: WS closure, scheduler shutdown, DB pool disposal. **No `@app.on_event`** (deprecated).                                                                |
| **`agent/src/main/platform/`**                | **Kiosk overlay model** — no `lockScreen()`/`unlockScreen()`. Interface: `showKioskOverlay()`, `hideKioskOverlay()`, `updateTimer()`, `restartPC()`, `shutdownPC()`, `captureScreenshot()`, `sendAnnouncement()`, `enableAutoStart()`, `disableAutoStart()`.                               |
| **`agent/src/main/platform/index.ts`**        | Unified `PlatformService` interface with **kiosk overlay** methods only — explicitly excludes OS lock/unlock.                                                                                                                                                                              |
| **`agent/src/main/ipc/handlers.ts`**          | Screenshot: JPEG at 80% quality, scaled to max **1280×720**, base64-encoded. Returns error if capture fails.                                                                                                                                                                               |
| **`agent/src/renderer/KioskOverlay.tsx`**     | Full‑screen Electron `BrowserWindow` with **hardened kiosk config**: `kiosk: true`, `alwaysOnTop: true`, `closable: false`, `devTools: false`, `sandbox: true`, `nodeIntegration: false`. Intercepts Alt+F4, Cmd+Q, F12, Alt+Shift+I, Ctrl+P. **No overlay bypass**.                       |
| **`agent/src/main/storage/session_store.ts`** | Local SQLite persistence for session state (start time, last sync, local elapsed seconds). Written every 10 seconds, on reconnect, and on every pause/resume/end. **Ensures no data loss on LAN drop or agent crash**.                                                                     |
| **`agent/src/main/ws/client.ts`**             | Sends `agent_secret` on REGISTER and every reconnection. Exponential backoff: 2s → 4s → … → 60s (cap) + jitter. SYNC message on reconnect: `{session_id, local_elapsed_seconds, disconnect_at, reconnect_at}`.                                                                             |
| **`launcher.py`**                             | License check (§16.6) gating setup wizard. Uses `py-machineid` for hardware fingerprint. Generates random `agent_secret` per seat during setup. **No admin privileges required** for hardware ID generation.                                                                               |
| **`arcade.config.json`**                      | Now includes `agent_secrets: {seat_id: agent_secret}` mapping. Generated at setup time using `secrets.token_hex(32)`. `agent_secret` is unique per seat, not hardcoded.                                                                                                                    |
| **`backend/models/staff.py`**                 | Added `token_version` INTEGER DEFAULT 0. Incremented on PIN change and deactivation. Validated on every protected endpoint against JWT `token_version` claim.                                                                                                                              |
| **`tools/keygen/`**                           | **Internal only** — never shipped. Holds Ed25519 private key. `generate_license.py` creates signed `license.key` files per customer. Private key never in VCS or customer builds.                                                                                                          |
| **`requirements.txt`**                        | Added: `aiosqlite`, `argon2-cffi`, `apscheduler`, `py-machineid`. Removed: `bcrypt`, `schedule`.                                                                                                                                                                                           |
| **`agent/package.json`**                      | Added: `better-sqlite3`, `jpeg-js` (or `sharp` for image resizing).                                                                                                                                                                                                                        |
| **`agent/agent.config.json`**                 | Treated as **secret file** — `chmod 600` on Linux/macOS. Contains `server_url` and `agent_secret`. Not world‑readable.                                                                                                                                                                     |

---

## Build Outputs (not in source control)

When built, the following **generated folders** appear:

```
frontend/dist/          # Built dashboard static files (served by FastAPI)
agent/dist/             # Platform‑specific distributables:
                        #   - Windows: .exe (NSIS installer)
                        #   - macOS: .dmg and .app bundle
                        #   - Linux: AppImage, .deb, or .rpm
```

These are **not** checked into the repository; they are produced by `npm run build` commands.

---

## Architecture Decisions Reflected in Structure

| Decision                                    | Where It's Enforced                                                                                    |
| ------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| **Kiosk overlay (not OS lock/unlock)**      | `agent/src/main/platform/` interface — no `lockScreen()`/`unlockScreen()` methods                      |
| **Async SQLAlchemy (`aiosqlite`)**          | `backend/core/database.py` — uses `AsyncSession`, `async_sessionmaker`, `create_async_engine`          |
| **Argon2id (not bcrypt)**                   | `backend/core/security.py` — imports `argon2-cffi`, no bcrypt fallback                                 |
| **`py-machineid` (no admin)**               | `backend/licensing/fingerprint.py` — primary source; OS fallbacks only if empty                        |
| **JWT `token_version` revocation**          | `backend/models/staff.py` — `token_version` column; validated in `api/deps.py`                         |
| **Agent `agent_secret` auth**               | `arcade.config.json` (generated at setup) → validated in `core/ws_manager.py`                          |
| **SQLite WAL + pragmas**                    | `backend/core/database.py` — `busy_timeout=5000`, `synchronous=NORMAL`, `wal_autocheckpoint=1000`      |
| **APScheduler (not `schedule`)**            | `backend/services/backup_service.py` — uses `AsyncIOScheduler`                                         |
| **`lifespan` (not `@app.on_event`)**        | `backend/main.py` — `@asynccontextmanager` lifespan function                                           |
| **Screenshot: JPEG, 1280×720 max**          | `agent/src/main/ipc/handlers.ts` — resizes, compresses to JPEG 80%, base64-encodes                     |
| **WoL seat statuses (BOOTING/UNREACHABLE)** | `backend/models/seat.py` — status enum; `backend/services/wol_service.py` — watchdog logic             |
| **Kiosk hardening**                         | `agent/src/renderer/KioskOverlay.tsx` — `kiosk: true`, `closable: false`, global shortcuts intercepted |
| **Explicit `updated_at`**                   | Service code (`entity.updated_at = datetime.utcnow()`) — not relying on SQLAlchemy `onupdate` trigger  |

---

## Project Structure

```
arcade-cafe/
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
│   │   │   └── ws.py              # WebSocket endpoint
│   │   └── deps.py                # Dependencies (auth, DB session, feature flags)
│   ├── services/                   # Business logic (billing, sessions, etc.)
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
│   │   └── backup_service.py
│   ├── repositories/               # All database queries (no business logic)
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
│   ├── models/                     # SQLAlchemy ORM models
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
│   │   ├── staff.py
│   │   ├── shift.py
│   │   ├── expense.py
│   │   ├── event.py
│   │   ├── audit_log.py
│   │   ├── settings.py
│   │   └── license_status.py
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
│   ├── licensing/                  # Offline license verification subsystem
│   │   ├── verify.py               # Ed25519 signature verification
│   │   ├── fingerprint.py          # Cross‑platform Hardware ID generation
│   │   └── public_key.py           # Embedded Ed25519 public key (hardcoded)
│   └── core/                       # Core infrastructure
│       ├── config.py               # arcade.config.json loader
│       ├── database.py             # SQLAlchemy engine, WAL, session factory
│       ├── feature_flags.py        # Feature flag loader and checker
│       ├── security.py             # PIN hashing, JWT, lockout
│       └── ws_manager.py           # WebSocket connection manager
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
│   │   ├── components/            # Reusable UI components
│   │   │   ├── SeatCard.tsx
│   │   │   ├── SeatGrid.tsx
│   │   │   ├── SessionTimer.tsx
│   │   │   ├── InvoicePanel.tsx
│   │   │   ├── POSPanel.tsx
│   │   │   ├── MemberSearch.tsx
│   │   │   ├── HealthBadge.tsx
│   │   │   └── ...
│   │   ├── hooks/                 # Custom hooks (useWebSocket, useSeats, etc.)
│   │   ├── api/                   # React Query API client functions
│   │   ├── store/                 # Zustand/Context stores (auth, feature flags)
│   │   └── utils/
│   │       ├── currency.ts        # Paise ↔ display conversion
│   │       └── time.ts
│   ├── index.html
│   ├── package.json
│   └── vite.config.ts
│
├── agent/                          # Electron client agent (cross‑platform)
│   ├── src/
│   │   ├── main.ts                 # Electron main process entry
│   │   ├── preload.ts              # Context bridge for IPC
│   │   ├── ipc/                    # IPC handlers (lock, unlock, screenshot, etc.)
│   │   ├── ws/                     # WebSocket client to server
│   │   ├── health/                 # systeminformation collector
│   │   ├── platform/               # Platform abstraction layer
│   │   │   ├── index.ts            # Exports unified PlatformService interface
│   │   │   ├── windows.ts          # Windows implementation
│   │   │   ├── macos.ts            # macOS implementation
│   │   │   └── linux.ts            # Linux implementation
│   │   └── renderer/               # React UI (splash, tray, countdown)
│   │       ├── SplashScreen.tsx
│   │       ├── CountdownOverlay.tsx
│   │       ├── Announcement.tsx
│   │       └── TrayIcon.tsx
│   ├── package.json
│   ├── electron-builder.yml        # Build config for all platforms
│   └── agent.config.json           # Per‑machine config (server URL, etc.) – filled at deploy
│
├── alembic/                        # Database migration scripts
│   ├── env.py
│   ├── alembic.ini
│   └── versions/                   # Individual migration files
│       ├── 001_initial.py
│       └── ...
│
├── tools/                          # INTERNAL – NOT SHIPPED TO CUSTOMERS
│   └── keygen/                     # Offline license key generation tool
│       ├── generate_license.py     # CLI tool – holds the private signing key
│       └── private_key.pem         # Ed25519 private key – NEVER committed to VCS
│
├── launcher.py                     # Tkinter GUI launcher (cross‑platform)
│                                   # - License Activation screen
│                                   # - Setup wizard
│                                   # - Server process management
│
├── arcade.config.json              # Runtime config (created by setup wizard – per server)
├── license.key                     # License file (placed by owner after activation – not in repo)
├── requirements.txt                # Python dependencies
├── README.md
└── LICENSE                         # Apache 2.0
```

---

## Key Additions / Changes

| Directory / File                                 | Purpose / Notes                                                                                                                                                                            |
| ------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `backend/licensing/`                             | Self‑contained offline license verification subsystem – signature check, hardware fingerprinting (cross‑platform), and public key embedding.                                               |
| `backend/core/feature_flags.py`                  | Centralised feature‑flag loader (database‑backed) with in‑memory cache.                                                                                                                    |
| `backend/core/ws_manager.py`                     | Manages all WebSocket connections – dashboards and agents – including heartbeat and reconnection logic.                                                                                    |
| `agent/src/platform/`                            | Platform abstraction layer – isolates OS‑specific operations (lock, restart, shutdown, auto‑start). Each module implements the same interface (`windows.ts`, `macos.ts`, `linux.ts`).      |
| `agent/src/renderer/`                            | React UI components for splash screen, countdown, announcements – identical across all OSes.                                                                                               |
| `tools/keygen/`                                  | **Internal only** – never included in any customer build. Holds the Ed25519 private key and the CLI tool used by Neurotech Biratnagar to generate signed `license.key` files per customer. |
| `launcher.py`                                    | Now cross‑platform; uses `os.path` and platform‑detection for file paths and subprocess management. Includes the License Activation screen before anything else.                           |
| `arcade.config.json` and `license.key`           | Both at the root. `license.key` is placed by the owner after activation; `arcade.config.json` is created by the setup wizard (only after license check passes).                            |
| `frontend/` and `agent/` both use `package.json` | Frontend is a standard Vite+React app; agent is an Electron app. Each has its own dependencies.                                                                                            |

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

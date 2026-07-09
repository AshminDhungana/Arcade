# Arcade — Folder Structure

---

## Project Structure

```
arcade/
├── .claude/                      # Claude Code configuration
├── .github/
│   └── workflows/                # GitHub Actions CI/CD
│       └── ci.yml
├── .gitignore
├── .pre-commit-config.yaml       # Pre-commit hooks config
├── .prettierrc                   # Prettier config
├── arcade.config.json            # Runtime server config (generated at setup)
├── CLAUDE.md                     # Project instructions for Claude Code
├── launcher.py                   # Tkinter launcher: license activation, setup wizard, server management
├── LICENSE
├── Makefile                      # Common dev shortcuts
├── pyproject.toml                # Python project config (ruff, mypy, black, pytest)
├── README.md
├── tools/                        # Internal tooling (not shipped)
│   └── keygen/                   # Ed25519 key generation (license signing keys — NEVER ship)
│
├── docs/                         # Documentation
│   ├── agent-setup.md
│   ├── api-reference.md
│   ├── Arcade_SDD.md             # Software Design Document
│   ├── Arcade_SRS.md             # Software Requirements Specification
│   ├── architecture.md
│   ├── CONTRIBUTING.md
│   ├── deployment.md
│   ├── developer-guide.md
│   ├── Folder_Structure.md       # This file
│   ├── operator-guide.md
│   ├── PRODUCT_BRIEF.md
│   ├── TODO.md
│   ├── references/
│   ├── security/
│   ├── superpowers/
│   └── testing/
│
├── backend/                      # FastAPI server (cross-platform)
│   ├── alembic/                  # Alembic migrations
│   │   ├── env.py
│   │   ├── README.md
│   │   ├── script.py.mako
│   │   └── versions/
│   │       ├── a1bb8b056ad6_add_wol_counters_to_seat.py
│   │       └── b45fd59d442e_001_initial.py
│   │
│   ├── api/
│   │   ├── routers/              # Route handlers per domain
│   │   │   ├── audit.py
│   │   │   ├── auth.py
│   │   │   ├── inventory.py
│   │   │   ├── invoices.py
│   │   │   ├── pos.py
│   │   │   ├── seats.py
│   │   │   ├── sessions.py
│   │   │   ├── settings.py
│   │   │   └── ws.py             # WebSocket endpoint
│   │   ├── deps.py               # Dependencies: auth, DB session (AsyncSession), feature flags
│   │   └── __init__.py
│   │
│   ├── core/                     # Core infrastructure
│   │   ├── config.py             # arcade.config.json loader
│   │   ├── database.py           # SQLAlchemy AsyncEngine, WAL pragmas (busy_timeout=5000),
│   │   │                          # AsyncSessionLocal, get_db() dependency
│   │   ├── feature_flags.py      # Feature flag loader and checker (DB-backed)
│   │   ├── scheduler.py          # APScheduler AsyncIOScheduler setup
│   │   ├── security.py           # Argon2id hashing (argon2-cffi), JWT with token_version,
│   │   │                          # rate limiting, lockout
│   │   ├── startup.py            # Startup/shutdown lifecycle (DB init, migrations, scheduler, WS manager)
│   │   └── ws_manager.py         # WebSocket connection manager (heartbeat, agent_secret validation)
│   │
│   ├── licensing/                # Offline license verification subsystem
│   │   ├── verify.py             # Ed25519 signature verification
│   │   ├── fingerprint.py        # Uses py-machineid (primary) + OS fallbacks
│   │   └── public_key.py         # Embedded Ed25519 public key (hardcoded)
│   │
│   ├── models/                   # SQLAlchemy ORM models (async-compatible)
│   │   ├── __init__.py
│   │   ├── _enums.py             # Shared enums
│   │   ├── _types.py             # Custom SQLAlchemy types
│   │   ├── audit_log.py
│   │   ├── event.py
│   │   ├── event_participant.py
│   │   ├── expense.py
│   │   ├── invoice.py
│   │   ├── invoice_line_item.py
│   │   ├── license_status.py     # Read-only cache for display
│   │   ├── member.py
│   │   ├── menu_item.py
│   │   ├── package.py
│   │   ├── package_entitlement.py
│   │   ├── promotion.py
│   │   ├── reservation.py
│   │   ├── restock_log.py
│   │   ├── seat.py
│   │   ├── session.py
│   │   ├── session_pos_item.py
│   │   ├── settings.py
│   │   ├── shift.py
│   │   ├── staff.py              # includes token_version INTEGER DEFAULT 0
│   │   ├── voucher.py
│   │   └── zone.py
│   │
│   ├── repositories/             # All database queries (async, no business logic)
│   │   ├── __init__.py
│   │   ├── audit_repo.py
│   │   ├── event_repo.py
│   │   ├── expense_repo.py
│   │   ├── inventory_repo.py
│   │   ├── invoice_repo.py
│   │   ├── member_repo.py
│   │   ├── package_repo.py
│   │   ├── pos_repo.py
│   │   ├── promotion_repo.py
│   │   ├── reservation_repo.py
│   │   ├── restock_repo.py
│   │   ├── seat_repo.py
│   │   ├── session_repo.py
│   │   ├── shift_repo.py
│   │   ├── staff_repo.py
│   │   ├── voucher_repo.py
│   │   └── zone_repo.py
│   │
│   ├── schemas/                  # Pydantic request/response schemas
│   │   ├── __init__.py
│   │   ├── analytics.py
│   │   ├── audit.py
│   │   ├── base.py
│   │   ├── event.py
│   │   ├── health.py
│   │   ├── invoice.py
│   │   ├── member.py
│   │   ├── package.py
│   │   ├── pos.py
│   │   ├── promotion.py
│   │   ├── reservation.py
│   │   ├── seat.py
│   │   ├── session.py
│   │   ├── settings.py
│   │   ├── shift.py
│   │   ├── staff.py
│   │   ├── voucher.py
│   │   └── zone.py
│   │
│   ├── services/                 # Business logic (async)
│   │   ├── __init__.py
│   │   ├── audit_service.py
│   │   ├── auth_service.py
│   │   ├── billing_service.py
│   │   ├── inventory_service.py
│   │   ├── pos_service.py
│   │   ├── print_service.py
│   │   ├── seat_service.py
│   │   ├── session_service.py
│   │   └── wol_service.py
│   │
│   ├── scripts/                  # Utility scripts
│   │   ├── __init__.py
│   │   └── seed_dev.py           # Dev database seeding
│   │
│   ├── tests/                    # Pytest test suite
│   │   ├── conftest.py
│   │   ├── test_*.py             # Unit/integration tests
│   │   └── validation_tasks/     # Architecture validation tasks
│   │       ├── arch01_app.py
│   │       ├── arch01_stress_test.py
│   │       ├── arch03/
│   │       ├── arch05/
│   │       └── arch06/
│   │
│   ├── __init__.py
│   ├── alembic.ini               # Alembic configuration
│   ├── main.py                   # FastAPI app with lifespan context manager
│   ├── requirements.txt          # Python dependencies
│   └── requirements-dev.txt      # Dev dependencies
│
├── frontend/                     # React dashboard (Vite + TailwindCSS v4)
│   ├── src/
│   │   ├── api/                  # API client layer
│   │   │   ├── auth.ts
│   │   │   ├── auth.test.ts
│   │   │   ├── featureFlags.ts
│   │   │   ├── invoices.ts
│   │   │   ├── invoices.test.ts
│   │   │   ├── pos.ts
│   │   │   ├── seats.ts
│   │   │   ├── seats.test.ts
│   │   │   ├── sessions.ts
│   │   │   └── sessions.test.ts
│   │   │
│   │   ├── components/           # Reusable UI components
│   │   │   ├── ElapsedTimer.tsx
│   │   │   ├── ElapsedTimer.test.tsx
│   │   │   ├── ProtectedRoute.tsx
│   │   │   ├── ProtectedRoute.test.tsx
│   │   │   ├── SeatActionModal.tsx
│   │   │   ├── SeatActionModal.test.tsx
│   │   │   ├── SeatCard.tsx
│   │   │   ├── SeatCard.test.tsx
│   │   │   ├── SeatGrid.tsx
│   │   │   ├── SeatGrid.test.tsx
│   │   │   ├── SeatStatusBadge.tsx
│   │   │   ├── SeatStatusBadge.test.tsx
│   │   │   └── SessionDrawer.tsx
│   │   │
│   │   ├── components/invoice/   # Checkout/Invoice components
│   │   │   ├── CheckoutPanel.tsx
│   │   │   ├── CheckoutPanel.test.tsx
│   │   │   ├── InvoiceLineItem.tsx
│   │   │   ├── InvoiceLineItem.test.tsx
│   │   │   ├── InvoicePanel.tsx
│   │   │   └── InvoicePanel.test.tsx
│   │   │
│   │   ├── components/pos/       # POS components
│   │   │   ├── MenuGrid.tsx
│   │   │   ├── MenuItemCard.tsx
│   │   │   ├── POSPanel.tsx
│   │   │   ├── SessionTab.tsx
│   │   │   └── TabItemRow.tsx
│   │   │
│   │   ├── hooks/                # Custom React hooks
│   │   │   ├── useFormatPaise.ts
│   │   │   ├── useWebSocket.ts
│   │   │   └── useWebSocket.test.tsx
│   │   │
│   │   ├── pages/                # Route pages
│   │   │   ├── Dashboard.tsx
│   │   │   ├── Login.tsx
│   │   │   └── Login.test.tsx
│   │   │
│   │   ├── store/                # Zustand stores
│   │   │   ├── authStore.ts
│   │   │   ├── authStore.test.ts
│   │   │   ├── featureFlagStore.ts
│   │   │   ├── healthStore.ts
│   │   │   └── healthStore.test.ts
│   │   │
│   │   ├── types/                # TypeScript types
│   │   │   ├── invoice.ts
│   │   │   ├── invoice.test.ts
│   │   │   ├── pos.ts
│   │   │   ├── seat.ts
│   │   │   ├── session.ts
│   │   │   └── ws.ts
│   │   │
│   │   ├── utils/                # Utility functions
│   │   │   ├── formatDuration.ts
│   │   │   └── formatDuration.test.ts
│   │   │
│   │   ├── __tests__/            # Smoke/integration tests
│   │   │   └── smoke.test.tsx
│   │   │
│   │   ├── App.tsx
│   │   ├── App.test.tsx
│   │   ├── main.tsx
│   │   ├── index.css
│   │   └── test-setup.ts
│   │
│   ├── eslint.config.js
│   ├── index.html
│   ├── package.json
│   ├── package-lock.json
│   ├── tsconfig.json
│   ├── tsconfig.app.json
│   ├── tsconfig.node.json
│   └── vite.config.ts
│
├── agent/                        # Electron agent (runs on each gaming PC)
│   ├── src/
│   │   ├── main/                 # Main process (Node.js)
│   │   │   ├── config/           # Configuration management
│   │   │   │   ├── index.ts
│   │   │   │   ├── loader.ts
│   │   │   │   ├── types.ts
│   │   │   │   └── validator.ts
│   │   │   ├── health/           # Health monitoring (placeholder)
│   │   │   ├── ipc/              # IPC handlers (placeholder)
│   │   │   ├── platform/         # Platform abstraction layer
│   │   │   │   ├── index.ts
│   │   │   │   ├── types.ts
│   │   │   │   └── windows.ts    # Windows implementation
│   │   │   ├── storage/          # Local SQLite persistence (better-sqlite3)
│   │   │   │   ├── session_store.ts
│   │   │   │   └── types.ts
│   │   │   ├── tray/             # System tray (placeholder)
 │   │   │   ├── ws/              # WebSocket client
│   │   │   │   ├── client.ts
│   │   │   │   ├── commands.ts
│   │   │   │   └── types.ts
│   │   │   └── index.ts          # Main process entry point
│   │   │
│   │   ├── renderer/             # Renderer process (React)
│   │   │   ├── components/       # Kiosk overlay components
│   │   │   │   ├── kiosk-overlay.ts
│   │   │   │   ├── low-time-warning.ts
│   │   │   │   └── staff-override-dialog.ts
│   │   │   ├── index.html
│   │   │   ├── index.ts
│   │   │   ├── kiosk.css
│   │   │   └── preload.ts        # Preload script (contextBridge)
│   │   │
│   │   └── tests/                # Vitest tests
│   │       ├── config/
│   │       ├── platform/
│   │       ├── renderer/components/
│   │       ├── storage/
│   │       └── ws/
│   │
│   ├── config.example.json       # Example agent config
│   ├── electron-builder.yml      # Electron Builder config
│   ├── eslint.config.js
│   ├── package.json
│   ├── package-lock.json
│   ├── tsconfig.json
│   ├── tsconfig.main.json
│   ├── tsconfig.renderer.json
│   └── vitest.config.ts
│
└── launcher.py                   # (Also at root for direct execution)
    # Also copied into backend/ for packaging
```

---

## Key Conventions

### Backend Layering (strict)
```
api/routers/  →  services/  →  repositories/  →  models/
```
- **Routers**: HTTP handling, validation, serialization only
- **Services**: Business logic, transactions, cross-repo coordination
- **Repositories**: Pure SQLAlchemy queries, no business logic
- **Models**: SQLAlchemy ORM definitions only

### Money Handling
- Stored as **integers in paise** (1/100 rupee) everywhere
- Only the display layer (frontend/agent renderer) converts to rupees

### Naming Conventions
| Layer | Pattern |
|-------|---------|
| Files | `snake_case.py` / `kebab-case.ts` / `PascalCase.tsx` (components) |
| Python | `snake_case` functions/variables, `PascalCase` classes |
| TypeScript | `camelCase` functions/variables, `PascalCase` types/components |
| Database | `snake_case` tables/columns |
| SQLAlchemy | `snake_case` columns, `PascalCase` model classes |

### Cross-Platform Notes
- **Backend**: Pure Python + `aiosqlite` — runs on Windows/macOS/Linux
- **Frontend**: Vite + React — runs anywhere Node.js runs
- **Agent**: Electron + platform abstraction layer (`src/main/platform/`) — Windows/macOS/Linux
- **Launcher**: Tkinter — runs on Windows/macOS/Linux (stdlib)

### Config Files (Never Committed)
| File | Location | Purpose |
|------|----------|---------|
| `arcade.config.json` | `backend/` (or root) | Server runtime config: DB path, secrets, agent_secrets per seat |
| `agent.config.json` | `agent/` (per client PC) | Client config: server URL, seat_id, agent_secret |
| License file | User-chosen path | Offline license (Ed25519-signed) |

### Key Generated Files (gitignored)
- `backend/arcade.db` — SQLite database (WAL mode)
- `backend/arcade.db-shm` / `-wal` — WAL files
- `backend/venv/` — Python virtual environment
- `frontend/node_modules/`, `agent/node_modules/`
- `frontend/dist/`, `agent/dist/` — Production builds
- `backend/__pycache__/`, `.mypy_cache/`, `.pytest_cache/`, `.ruff_cache/`

# Arcade Architecture

> Last updated: 2026-07-02 (Phase 1, in progress)
> See also: `docs/PRODUCT_BRIEF.md`, `docs/Folder_Structure.md`

## System Overview

Arcade is a four-component, LAN-only gaming cafe management system designed to run entirely without cloud infrastructure. The server runs on the counter PC; the agent runs on every gaming PC. There is no cloud dependency during normal operation.

The four components are:
1. **Backend** (`backend/`) — FastAPI server with async SQLAlchemy, SQLite WAL, offline Ed25519 license verification, and WebSocket hub
2. **Frontend** (`frontend/`) — React dashboard (Vite, TypeScript, TailwindCSS) for staff and owner interfaces
3. **Agent** (`agent/`) — Electron kiosk overlay application, local SQLite persistence, health metrics
4. **Launcher** (`launcher.py`) — Tkinter GUI for license activation, setup wizard, and server process management

## Component Diagram

```text
[Power strip]
    |
    +---> Main Counter PC (Windows/macOS/Linux)
    |      |
    |      +-> launcher.py (Tkinter)
    |      |    |- License check (offline Ed25519 + py-machineid HWID)
    |      |    |- Activation screen (missing/invalid license)
    |      |    |- Setup wizard (first run)
    |      |    `- Main screen (start/stop server, logs, open dashboard)
    |      |
    |      +-> FastAPI backend (uvicorn)
    |      |    |- SQLite database (WAL + pragmas)
    |      |    |- APScheduler (nightly backup)
    |      |    |- WebSocket hub (/ws/dashboard, /ws/agent/{seat_id})
    |      |    `- REST API (/api/*)
    |      |
    |      +-> React dashboard (Vite dev / dist/)
    |
    +---> Client PCs (Windows/macOS/Linux)
    |      `- Electron agent
    |           |- Kiosk overlay (hardened: kiosk=true, closable=false)
    |           |- Local SQLite (session state persistence across LAN drops)
    |           |- WebSocket client (exponential backoff reconnection)
    |           |- Health metrics collector (CPU%, RAM%, 60s interval)
    |           `- Screenshot capture (JPEG 80%, max 1280x720, base64)
    |
    +---> Tuya smart plugs (local LAN)
    |      `- Console power control (TinyTuya; no cloud after pairing)
    |
    `--> Owner phone (browser on same WiFi)
           `- Mobile-responsive dashboard view
```

## Component Descriptions

### 1. Backend (`backend/`)

**Entry point:** `backend/main.py`
- Uses `FastAPI` with `@asynccontextmanager lifespan` for startup/shutdown orchestration
- Startup sequence (8 steps): load config -> WAL check -> run migrations -> load feature flags -> recover active sessions -> boot seats -> start scheduler -> init WebSocket manager
- Serves `frontend/dist/` with SPA fallback; CORS allows `localhost:*` in dev
- `GET /health` returns `{ status, version, license_type, uptime, seat_count, active_sessions }`
- All API routers under `/api/` prefix; WebSocket under `/ws/`

**Database (`backend/core/database.py`):**
- Async engine: `sqlite+aiosqlite` at `./arcade.db`
- WAL enabled with 7 pragmas (see Technology Rationale below)
- `AsyncSessionLocal` with `expire_on_commit=False`
- `get_db()` dependency for router injection

**Repository pattern:**
- `api/routers/` — FastAPI route handlers (only business logic: auth, validation, calling services)
- `services/` — Business logic (planned for Phase 2; currently empty stubs)
- `repositories/` — Pure data access, no business logic; all methods are `async def`
- `models/` — SQLAlchemy ORM; all monetary fields are `Integer` (paise); all timestamps have `timezone=True`

**Core modules (`backend/core/`):**
- `config.py` — Pydantic `Settings` model; `get_config()` singleton
- `database.py` — Async engine + WAL pragmas
- `security.py` — Argon2id PIN hashing, JWT with `token_version` for revocation, brute-force lockout (5 attempts -> 15 min)
- `ws_manager.py` — Singleton manager; two registries (dashboards, agents); heartbeat PING every 30s; agent secret validation on every connection
- `feature_flags.py` — In-memory cache of `AppSettings` table; `require_feature()` dependency returns 503 if flag off
- `scheduler.py` — APScheduler for nightly backups
- `startup.py` — Migration runner + session recovery + WoL boot

### 2. Frontend (`frontend/`)

- Vite dev server with proxy: `/api` -> `localhost:8000`, `/ws` -> `ws://localhost:8000`
- TailwindCSS v4 for styling
- React Query for server state, Zustand for client state, Recharts for charts
- Vitest + jsdom + React Testing Library for tests
- Currently: scaffolding only (main.tsx, App.tsx, smoke test). Pages, components, hooks are `.gitkeep` placeholders.

### 3. Agent (`agent/`)

- Electron with `kiosk: true`, `closable: false`, `devTools: false`
- Full-screen overlay blocks desktop access when no session is active
- All platform-specific logic in `src/main/platform/` — kiosk overlay, restart, shutdown, screenshot
- Local SQLite via `better-sqlite3` caches session state (written every 10s + on pause/resume/end)
- WebSocket client: exponential backoff (2s -> 4s -> ... -> 60s cap + jitter); sends `agent:secret` on every connect
- Intercepted shortcuts: Alt+F4, Cmd+Q, F12, Alt+Shift+I, Ctrl+P
- Known gaps (documented, not bugs): Ctrl+Alt+Del on Windows; Wayland compositor variations on Linux

### 4. Launcher (`launcher.py`)

- Tkinter GUI; shown before any server starts
- License check first: call `check_license()` from `backend/licensing/verify.py`
- Activation screen (missing/invalid/mismatched license): shows copyable Hardware ID; browse for `license.key`
- Setup wizard (first run with valid license, no `arcade.config.json`): collects cafe name, host, port, staff credentials, generates `agent_secret` per seat
- Main screen (subsequent runs): start/stop server as subprocess, tail logs, open dashboard in browser
- Defaults on `make backend-dev` bypass the launcher for development

## Communication Model

**REST API:** Most read/write operations. Used by the React dashboard and mobile view.

**WebSockets (real-time):**
- `/ws/dashboard` — Server pushes seat status, session timers, health metrics, announcements
- `/ws/agent/{seat_id}` — Bi-directional for agent commands
- Authentication: `agent_secret` passed as query param on every connection
- Heartbeat: PING every 30s, disconnect if no PONG within 10s
- Max message size: 5 MB
- SYNC payload on reconnect: `{ session_id, local_elapsed_seconds, disconnect_at, reconnect_at }`

**Wake-on-LAN:** Server sends magic packets to boot client PCs. Seat status set to `BOOTING`; watchdog sets `UNREACHABLE` after 60s if no agent REGISTER.

**Console control:** TinyTuya over local LAN (no cloud after initial pairing). `device.turn_on()` / `device.turn_off()`.

## Technology Rationale

### Why SQLite (not PostgreSQL) for V1

- **LAN-only deployment:** No need for a separate database server; single-file database is zero-config for operators
- **Performance:** WAL + `busy_timeout=5000` + `synchronous=NORMAL` handles 50+ concurrent operations with zero `database is locked` errors (validated via ARCH-01)
- **Backup simplicity:** `cp arcade.db backups/` is atomically safe under WAL
- **V2 path:** Models are already abstracted behind repositories. PostgreSQL is a v2 concern for multi-location or >100-seat deployments

### Why Electron kiosk (not OS lock/unlock)

- **Cross-platform consistency:** `kiosk: true` behaves the same on Windows, macOS, and Linux. OS lock/unlock differs per-OS and usually requires elevated privileges
- **No privilege escalation:** The agent does not need admin/root access to function
- **Known gaps documented:** Ctrl+Alt+Del (Windows), Cmd+Tab (macOS) are documented limitations, not bugs. Wayland is flagged as high-risk

### Why FastAPI (not Flask/Django)

- Native async/await support matches our `async` SQLAlchemy + `aiosqlite` stack
- Automatic request/response validation via Pydantic (all schemas already defined in `backend/schemas/`)
- `lifespan` context manager (not deprecated `@app.on_event`) for clean startup/shutdown

### Why React + Vite + Tailwind (not Angular/Vue)

- Vite provides fast HMR and optimized production builds out of the box
- TailwindCSS v4 (utility-first) keeps component code colocated and reduces style consistency issues in a small team
- React Query + Zustand combination provides both server and client state management without overarchitecting

### Why integer paise (not float/double)

- Eliminates floating-point rounding errors entirely (critical for billing)
- All ORM model monetary fields are `Integer`. Pydantic schemas enforce `amount_paise: int`
- Display layer only: `Rs. {amount_paise / 100}` with `{:.2f}` formatting
- Currency conversion logic lives in one utility: `frontend/src/utils/currency.md`

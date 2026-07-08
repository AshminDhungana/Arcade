# Arcade — Engineering Execution Plan v2.1

**Project:** Arcade — Gaming Cafe Management System
**Version:** 2.0
**Prepared by:** Ashmin Dhungana
**Status:** Phase 0–2 Complete · Phase 3 In Progress (Features 3.1.5–3.1.6 done)
**Reference Documents:** `PRODUCT_BRIEF.md`, `Arcade_SRS.md`, `Arcade_SDD.md`, `Folder_Structure.md`

---

## Legend

| Symbol               | Meaning                                                        |
| -------------------- | -------------------------------------------------------------- |
| `[ ]`                | Not started                                                    |
| `[x]`                | Complete                                                       |
| `[~]`                | In progress                                                    |
| **ENG-A**            | Backend / Infra engineer                                       |
| **ENG-B**            | Frontend / Agent engineer                                      |
| **⚡ CHECKPOINT**    | Hard sync point — both engineers must verify before proceeding |
| **⚠ RISK**           | Identified risk requiring active mitigation                    |
| **FR-XXX / NFR-XXX** | Requirement reference from SRS v2.0                            |
| **AC-XX**            | Acceptance criterion reference from SRS §11                    |

---

## Project Overview

Arcade is a self-hosted, offline-first gaming cafe management system. It runs on a local area network with:

- **FastAPI backend** (Python) — business logic, REST API, WebSocket hub, scheduled tasks
- **React dashboard** (TypeScript + Vite) — staff interface and owner mobile view
- **Electron agent** (TypeScript) — per-client-PC kiosk overlay, hardware metrics, remote commands
- **Tkinter Launcher** (Python) — license activation, setup wizard, server process management

**No cloud infrastructure. No subscriptions. One-time perpetual license, activated offline.**

---

## Assumptions

1. The development team consists of two engineers (ENG-A, ENG-B) working in parallel.
2. Python 3.12.x and Node.js 20 LTS are the target runtimes.
3. The primary deployment target for v1.0 is Windows 10/11 for both server and client.
4. macOS and Linux are fully supported but tested second.
5. The private Ed25519 keygen key (`tools/keygen/private_key.pem`) is stored out-of-band — never in the repository.
6. SQLite is the production database for v1.0. PostgreSQL migration is a v2 concern.
7. PyInstaller `--onedir` mode is used for packaging (faster startup than `--onefile`, easier crash debugging). An NSIS installer wraps the directory into a single installer `.exe`.
8. All monetary values are integers in paise throughout the system. The display layer (UI and print) is the only place that converts to rupees. This is non-negotiable.
9. The license keygen private key must have a defined custody policy before any license is issued.
10. CI runs on GitHub Actions. No self-hosted runners needed for v1.0.

---

## Architecture Validation Tasks

> These tasks must be completed before any feature development begins. They de-risk the entire architecture.

- [x] **ARCH-01: Validate SQLite WAL + async SQLAlchemy (aiosqlite) under concurrent writes**
  - Spin up a minimal FastAPI app with WAL mode enabled
  - Run 10 concurrent write requests; confirm no `database is locked` errors
  - Confirm pragmas: `PRAGMA journal_mode = WAL`, `PRAGMA busy_timeout = 5000`, `PRAGMA synchronous = NORMAL`, `PRAGMA foreign_keys = ON`, `PRAGMA mmap_size = 134217728`
  - Add `PRAGMA wal_autocheckpoint = 1000` (checkpoint after 1000 pages, ~4 MB)
  - **Pass criteria:** Zero locking errors; WAL confirmed via `sqlite3 test.db "PRAGMA journal_mode;"` → `wal`
  - **Reference:** Industry benchmarks confirm WAL + NORMAL sync reduces P99 write latency 30–60% vs default rollback journal

- [x] **ARCH-02: Validate Electron `kiosk: true` behavior on each target OS**
  - Windows 10/11: TEST (don't assume) whether Alt+F4, F12, Ctrl+P, Win+D are blocked — current evidence says they are NOT blocked by default; plan for globalShortcut overrides, devTools:false, beforeunload/close interception, and print-shortcut suppression
  - macOS 11+: confirm Cmd+Space is blocked by default; confirm Cmd+Tab and Cmd+Q are NOT blocked by default (known long-standing gaps) — plan for blur-handler kiosk re-assertion and/or native NSApplicationPresentationOptions flags
  - Linux (X11): confirm desktop compositor shortcuts blocked — test per-DE (GNOME, KDE, XFCE); expect inconsistent results across WMs
  - Linux (Wayland): `setAlwaysOnTop(true, 'screen-saver')` is currently non-functional on Wayland (Electron not-supported / open upstream bug) — do NOT treat this as a working fallback; research compositor-specific lock/kiosk protocols instead
  - **Document all known gaps**, including: Ctrl+Alt+Del (OS-protected, cannot be intercepted — confirmed), Cmd+Tab (macOS, confirmed long-standing gap), Win+D/taskbar exposure (Windows, confirmed open bug)
  - **⚠ RISK (upgraded):** Wayland kiosk mode is not just "compositor-dependent" — the documented fallback API doesn't work at all on Wayland today. Treat Wayland as unsupported/high-risk until a working mitigation is identified, not as a "test early" item.

Reference document for ARCH-02 is at ./references/ARCH-02-kiosk-mode-validation.md

- [x] **ARCH-03: Validate PyInstaller `--onedir` with FastAPI + Alembic + aiosqlite + Tkinter**
  - Build a minimal proof-of-concept bundle on Windows
  - Confirm `alembic upgrade head` runs from within the bundle without Python installed
  - Confirm `aiosqlite` dynamic library loads correctly (it has C extensions)
  - Confirm Tkinter is bundled and renders correctly (on Linux: `sudo apt install python3-tk` prerequisite)
  - **Note:** PyInstaller cannot cross-compile. Build Windows `.exe` on Windows, macOS `.app` on macOS, Linux binary on Linux. Plan build machines accordingly.
  - **Pass criteria:** The bundled launcher shows the License Activation screen on a fresh machine with no Python installed

Reference document for ARCH-03 is at ./references/ARCH-03-pyinstaller-onedir-validation.md

- [ ] **ARCH-04: Validate TinyTuya local LAN control**
  - Test `tinytuya.BulbDevice` or `tinytuya.Device` with a real smart plug on the LAN
  - Confirm `device.turn_on()` and `device.turn_off()` work without internet (TinyTuya uses local LAN API)
  - Confirm device pairing (one-time, requires internet — document this)
  - **⚠ RISK:** TinyTuya requires the Tuya local key, which must be extracted once during pairing. Document the extraction process.

- [x] **ARCH-05: Validate Ed25519 offline license flow end-to-end** ✅ _(validated Windows only — macOS/Linux deferred; see `references/ARCH-05-offline-license-validation.md`)_
  - Generate a keypair; sign a test license payload; verify on a different machine
  - Confirm `py-machineid` produces a stable hardware ID on Windows and Linux (reboot-stable, not session-specific)
  - Confirm `py-machineid` requires no admin privileges on all three OSes
  - **Pass criteria:** Hardware ID is identical across reboots; license verification passes; hardware mismatch is correctly detected

- [x] **ARCH-06: Validate WebSocket reconnection and SYNC flow** ✅ _(validated Windows host, loopback only; protocol/reconciliation logic OS-agnostic — re-run live Layer 2 suite on macOS/Linux before Phase 2 agent ships; see `references/ARCH-06-websocket-reconnect-validation.md`)_
  - Implement minimal agent WS client with exponential backoff
  - Simulate a LAN drop: disconnect, wait 10 seconds, reconnect
  - Confirm SYNC payload is sent correctly after reconnect and session time is reconciled
  - **Pass criteria:** Session billing is accurate after a 30-second LAN outage (within ±5 seconds)

---

## Development Phases Overview

| Phase | Name                             | ENG-A                                         | ENG-B                                          | Duration (est.) |
| ----- | -------------------------------- | --------------------------------------------- | ---------------------------------------------- | --------------- |
| 0     | Project Setup & Tooling          | Python env, CI skeleton                       | Node.js env, scaffolding                       | 1–2 days        |
| 1     | Architecture Foundation          | FastAPI skeleton, DB, models, licensing       | Launcher, keygen                               | 1 week          |
| 2     | Seat & Session Core              | Session/Seat services, WoL, Auth API          | Agent kiosk + WS, Dashboard seat grid          | 2 weeks         |
| 3     | Billing, POS & Receipts          | Billing engine, POS, print, audit             | Checkout UI, POS UI, invoice panel             | 2 weeks         |
| 4     | Members, Packages, Promotions    | Member/package/promo/voucher/staff services   | Member UI, settings page                       | 1.5 weeks       |
| 5     | Operations & Experience          | Shift mgmt, reservations, health, backup      | Shift UI, reservation UI, health dashboard     | 1.5 weeks       |
| 6     | Analytics & Events               | Analytics service, event/tournament service   | Analytics page, events page                    | 1 week          |
| 7     | Cross-Platform Agent Polish      | macOS agent impl, cross-platform testing      | Linux agent impl, kiosk hardening verification | 1 week          |
| 8     | Testing & QA                     | Backend integration + perf tests, CI pipeline | Frontend E2E, cross-browser                    | 1 week          |
| 9     | Security Hardening               | Auth audit, key audit, Bandit/pip-audit       | Dependency audit, input validation audit       | 3–4 days        |
| 10    | Performance Optimisation         | DB indexes, query plans, seeded data test     | Bundle splitting, lazy loading                 | 3–4 days        |
| 11    | Deployment & Packaging           | PyInstaller spec, build pipeline              | electron-builder, agent distributables         | 3–4 days        |
| 12    | Documentation Finalisation       | API reference, architecture, operator guide   | Agent setup, deployment guide                  | 3–4 days        |
| 13    | Production Release               | Final AC verification, release artifacts      | Release packaging, customer deployment         | 2–3 days        |
| 14    | Post-Launch Support & V2 Scoping | Bug SLA process, V2 scope doc                 | —                                              | Ongoing         |

**Total estimated duration:** 14–16 weeks for two engineers working concurrently.

---

## Risk Register

| ID   | Risk                                                      | Impact                                  | Probability | Mitigation                                                                                               |
| ---- | --------------------------------------------------------- | --------------------------------------- | ----------- | -------------------------------------------------------------------------------------------------------- |
| R-01 | SQLite write contention under concurrent sessions         | Data corruption or locked errors        | Low         | WAL mode + `busy_timeout=5000`; validate in ARCH-01                                                      |
| R-02 | Electron kiosk bypass on Wayland                          | Customers bypass kiosk overlay          | Medium      | Early validation (ARCH-02); document known gaps; recommend X11 for client PCs                            |
| R-03 | TinyTuya local key extraction fails                       | Console power control unavailable       | Medium      | Test with real hardware early (ARCH-04); document manual fallback                                        |
| R-04 | PyInstaller bundle fails to include all hidden imports    | Launcher crashes at customer site       | Medium      | ARCH-03 validation; use `--onedir` not `--onefile` for easier debugging                                  |
| R-05 | Private key leaked into repository                        | License system compromised              | Critical    | `.gitignore` + CI check for `.pem` files; never commit keygen directory                                  |
| R-06 | Paise arithmetic error leads to billing discrepancy       | Customer billing disputes               | High        | All monetary fields typed as `int`; Pydantic schema validation; dedicated billing unit tests             |
| R-07 | Agent SYNC reconciliation bug after LAN drop              | Session billing lost during outage      | High        | ARCH-06 validation; integration tests for disconnect/reconnect scenario                                  |
| R-08 | `py-machineid` returns different ID after hardware change | License invalidated unexpectedly        | Medium      | Document hardware change process; include fallback fingerprint (hostname + MAC); test on target hardware |
| R-09 | Argon2id parameters too weak for brute-force              | PIN compromise                          | Low         | Use OWASP recommended params; validate with timed hash in CI                                             |
| R-10 | Cross-compilation not supported by PyInstaller            | Cannot build Windows `.exe` on macOS    | Medium      | Plan a Windows build machine (or GitHub Actions Windows runner) from Phase 0                             |
| R-11 | Alembic migration fails on customer DB after upgrade      | Data inaccessible after software update | High        | Test migration on a copy of production DB before release; include rollback script                        |
| R-12 | ESC/POS thermal printer model incompatibility             | Receipt printing fails                  | Medium      | Abstract `PrintService` to allow printer model config; test with target hardware; maintain PDF fallback  |

---

## Parallel Work Streams Summary

```
Timeline →
ENG-A: [Phase 0 Backend] → [Phase 1 FastAPI+DB+Models] → [Phase 2 Services+API] → [Phase 3 Billing+POS] → [Phase 4 Members+Staff] → [Phase 5 Shifts+Reservations] → [Phase 6 Analytics] → [Phase 7 macOS] → [Phase 8 Tests+CI] → [Phase 9 Security] → [Phase 10 Perf] → [Phase 11 Packaging] → ...

ENG-B: [Phase 0 Frontend] → [Phase 1 Launcher+Keygen] → [Phase 2 Agent+Dashboard] → [Phase 3 Checkout UI] → [Phase 4 Member UI] → [Phase 5 Ops UI] → [Phase 6 Analytics UI] → [Phase 7 Linux] → [Phase 8 E2E Tests] → [Phase 9 Dep Audit] → [Phase 10 Bundle] → [Phase 11 Agent Pkg] → ...

⚡ CHECKPOINTS: 0-END, 1-A, 1-B, 2-A, 3-A, 4-A, 5-A, 6-A, 8-END, 13-END
```

---

## Phase 0: Project Setup & Tooling

### Objectives

Establish a fully operational repository, development environment, code quality toolchain, branching strategy, and CI skeleton before any feature code is written. Every engineer joining must be able to clone the repo and have a running dev environment within 30 minutes.

### Deliverables

- Initialised monorepo matching `Folder_Structure.md` exactly
- Working pre-commit hooks and linters for Python (Ruff + Black + Mypy) and TypeScript (ESLint + Prettier)
- GitHub repository with branch protection rules and PR template
- Root `Makefile` for common development commands
- `.gitignore`, `LICENSE` (Apache 2.0), and base `README.md` committed
- GitHub Actions CI skeleton (runs on every PR, even if there are zero tests yet)

### Dependencies

None — this is the starting phase.

### Parallel Work

ENG-A: Python toolchain, backend scaffolding, Makefile, CI skeleton
ENG-B: Node.js/TypeScript toolchain, Vite frontend scaffold, Electron agent scaffold

### ⚡ CHECKPOINT 0-END

Before proceeding to Phase 1:

- [~] `make install` succeeds from a clean clone on all three OSes
- [~] `pre-commit run --all-files` passes with zero errors
- [~] `npm run lint` passes in both `frontend/` and `agent/`
- [x] `python -m pytest backend/` runs and reports zero tests, zero failures
- [x] All directories from `Folder_Structure.md` are present
- [x] Direct push to `main` is rejected; PR template appears on new PRs

---

### Epic 0.1: Repository Initialisation

#### Feature 0.1.1: Git Repository and Folder Structure

- [x] **Task: Initialise git repository and create folder structure**
  - [x] Run `git init` in `arcade/` root
  - [x] Create all subdirectories from `Folder_Structure.md` with `.gitkeep` files
  - [x] Create `LICENSE` (Apache 2.0)
  - [x] Create base `README.md` with project name, tech stack, and "Getting Started" stub
  - [x] Push to GitHub under `neurotech-biratnagar/arcade` (private repository)
  - [x] **Definition of done:** `git log` shows clean initial commit; all directories present

- [x] **Task: Configure `.gitignore`**
  - [x] Python: `__pycache__/`, `*.pyc`, `venv/`, `.env`, `arcade.config.json`, `license.key`, `arcade.db`, `arcade.db-shm`, `arcade.db-wal`, `backups/`, `dist/`
  - [x] Security-critical: `tools/keygen/private_key.pem`, `*.pem`, `*.key` (private key patterns)
  - [x] Node.js: `node_modules/`, `dist/`, `.cache/`, `agent/dist/`, `frontend/dist/`
  - [x] OS: `.DS_Store`, `Thumbs.db`, `.idea/`, `.vscode/`, `*.swp`
  - [x] Build artifacts: `build/`, `*.spec` outputs, `_MEI*/`
  - [~] **Definition of done:** `git status` after `pip install` and `npm install` shows no unintended tracked files

- [x] **Task: Branch protection and PR template**
  - [x] Protect `main` branch: require PR review, require CI status checks (lint + test), no force-push, no delete
  - [x] Create `develop` branch as integration branch
  - [x] Create `.github/pull_request_template.md`: description, testing steps, checklist (tests passing, docs updated, no secrets committed)
  - [x] Document branching strategy in `docs/CONTRIBUTING.md`: `feature/*`, `fix/*`, `chore/*`, `release/*` naming
  - [x] **Definition of done:** Direct push to `main` is rejected; PR template appears on new PRs

#### Feature 0.1.2: Python Development Environment (ENG-A)

- [x] **Task: Configure Python virtual environment and dependencies**
  - [x] Create `backend/requirements.txt` with pinned versions:
    ```
    fastapi==0.138.1
    sqlalchemy[asyncio]==2.0.51
    aiosqlite==0.22.1
    uvicorn[standard]==0.49.0
    httpx==0.28.1
    PyNaCl==1.6.2
    py-machineid==1.0.0
    pytest==9.1.1
    pytest-asyncio==1.4.0
    pydantic==2.10.4
    alembic==1.14.0
    argon2-cffi==23.1.0
    python-jose[cryptography]==3.4.0
    apscheduler==3.11.0
    cryptography==44.0.0
    pyinstaller==6.12.0
    tinytuya==1.17.0
    python-escpos==3.1.0
    ```
  - [x] Create `backend/requirements-dev.txt`:
    ```
    pytest==9.1.1
    pytest-asyncio==1.4.0
    pytest-cov==6.0.0
    httpx==0.28.1
    ruff==0.8.0
    mypy==1.13.0
    black==24.10.0
    pre-commit==4.0.1
    bandit==1.9.4
    pip-audit==2.7.3
    locust==2.32.0
    faker==33.0.0
    ```
  - [~] Create and activate `backend/.venv/`; confirm `pip install -r requirements.txt -r requirements-dev.txt` succeeds
  - [~] **Definition of done:** `python -c "import fastapi, sqlalchemy, aiosqlite, nacl"` succeeds in venv

- [x] **Task: Configure Python linters, formatters, and type checker**
  - [x] Create `pyproject.toml` at repo root with Ruff rules: `E`, `F`, `I`, `UP`, `B`, `S` (Bandit-equivalent)
  - [x] Configure `black` for 88-char line length in `pyproject.toml`
  - [x] Configure `mypy` with `strict = true` in `pyproject.toml`
  - [x] Create `.pre-commit-config.yaml`: `ruff`, `black`, `mypy`, `bandit` hooks
  - [~] Run `pre-commit install`; verify hooks fire on `git commit`
  - [~] **Definition of done:** `pre-commit run --all-files` passes with zero errors on empty skeleton

#### Feature 0.1.3: Node.js / TypeScript Development Environment (ENG-B)

- [x] **Task: Initialise frontend (React + Vite + TypeScript + TailwindCSS)**
  - [x] Run `npm create vite@latest frontend -- --template react-ts` in `arcade/`
  - [x] Install TailwindCSS: `npm install -D tailwindcss postcss autoprefixer && npx tailwindcss init -p`
  - [x] Install runtime deps: `@tanstack/react-query react-router-dom zustand recharts lucide-react`
  - [x] Install test deps: `vitest @testing-library/react @testing-library/user-event jsdom`
  - [x] Configure `tsconfig.json`: strict mode, path alias `@/` → `src/`
  - [x] Configure `vite.config.ts`: proxy `'/api'` → `http://localhost:8000`, `'/ws'` → `ws://localhost:8000`
  - [~] **Definition of done:** `npm run dev` starts; `npm run build` produces `dist/`; `npm test` runs (zero tests, zero failures)

- [x] **Task: Initialise Electron agent project**
  - [x] `npm init` in `agent/`; configure `package.json` with `"main": "dist/main/index.js"`
  - [x] Install dev deps: `electron electron-builder typescript ts-node`
  - [x] Install runtime deps: `better-sqlite3 systeminformation sharp`
  - [x] Create `electron-builder.yml`: targets Windows (nsis), macOS (dmg), Linux (AppImage, deb)
  - [x] Configure `tsconfig.json` for main (CommonJS) and renderer (ESM) processes
  - [x] Create stub `agent/src/main/index.ts` that opens a window
  - [~] **Definition of done:** `npm run start` opens an Electron window; `npm run build` produces a distributable

- [x] **Task: Configure TypeScript linting for frontend and agent**
  - [x] Install ESLint + plugins: `eslint @typescript-eslint/eslint-plugin @typescript-eslint/parser eslint-plugin-react-hooks prettier eslint-config-prettier`
  - [x] Create `frontend/eslint.config.js` (flat config) and `agent/.eslintrc.js` with TypeScript strict rules
  - [x] Create `.prettierrc`: 2-space indent, single quotes, trailing commas
  - [~] Add ESLint hook to `.pre-commit-config.yaml` (optional — not yet wired)
  - [~] **Definition of done:** `npm run lint` and `npm run format:check` pass on empty scaffolding

#### Feature 0.1.4: Shared Infrastructure

- [x] **Task: Create root Makefile**
  - [x] Targets: `install`, `backend-dev`, `frontend-dev`, `agent-dev`, `test`, `lint`, `lint-python`, `lint-frontend`, `lint-agent`, `build-frontend`, `build-agent`, `clean`
  - [x] Each target documented with a comment
  - [~] **Definition of done:** `make install` installs all deps; `make backend-dev` starts FastAPI dev server

- [x] **Task: Establish CI skeleton (GitHub Actions)**
  - [x] Create `.github/workflows/ci.yml` with jobs: `lint-python`, `test-backend`, `lint-frontend`, `test-frontend`, `lint-agent`
  - [x] Run on: push to `develop`, all PRs to `main`
  - [~] Use `actions/cache` for pip and npm dependency caching
  - [~] Add CI status badge to `README.md`
  - [~] **Definition of done:** CI runs and passes (zero tests, zero failures) on the empty skeleton

- [x] **Task: Establish docs directory**
  - [x] Create placeholder files: `docs/architecture.md`, `docs/api-reference.md`, `docs/deployment.md`, `docs/agent-setup.md`, `docs/developer-guide.md`, `docs/CONTRIBUTING.md`, `docs/operator-guide.md`, `docs/security/auth-audit.md`, `docs/security/key-management.md`, `docs/security/threat-model.md`
  - [x] Each file has a heading and "TODO: Document during corresponding phase" note

### Documentation Requirements (Phase 0)

- [x] `docs/CONTRIBUTING.md`: branching strategy, commit message format (`type(scope): message`), PR process, local setup steps
- [x] `README.md`: Getting Started section with `make install`, `make backend-dev`, `make frontend-dev`

---

## Phase 1: Architecture Foundation & Core Infrastructure

### Objectives

Build the foundational infrastructure that every other feature depends on: FastAPI skeleton, async SQLAlchemy with WAL, Alembic migrations, all ORM models, all Pydantic schemas, WebSocket manager, core configuration, licensing subsystem, and Tkinter Launcher.

**This phase produces the skeleton that all Phase 2–6 features plug into. Do not skip tasks here.**

### Deliverables

- FastAPI app with working `lifespan`, router registration, `/health` endpoint
- SQLAlchemy async engine with WAL pragmas (validated by ARCH-01)
- Alembic initialised; all ORM models defined; migration `001_initial.py` applied
- `backend/core/` fully implemented: `config.py`, `database.py`, `security.py`, `ws_manager.py`, `feature_flags.py`, `deps.py`
- Offline licensing subsystem: `fingerprint.py`, `verify.py`, `public_key.py`
- Internal keygen tool: `tools/keygen/generate_license.py`
- Tkinter Launcher: License Activation screen, Setup Wizard, Main Screen
- WebSocket endpoints: `/ws/dashboard` and `/ws/agent/{seat_id}` with agent secret auth
- All Pydantic schemas defined

### Dependencies

- Phase 0 complete (⚡ CHECKPOINT 0-END passed)
- ARCH-01, ARCH-05 validated

### Parallel Work

**ENG-A:** FastAPI skeleton, core infrastructure, ORM models, Alembic, WebSocket manager, feature flags, Pydantic schemas, repository stubs
**ENG-B:** Tkinter Launcher, licensing subsystem (`fingerprint.py`, `verify.py`), keygen tool

### ⚡ CHECKPOINT 1-A (Mid-Phase Sync)

After ENG-A completes `core/config.py` and `database.py`:

- [ ] ENG-B reviews `Settings` model field names — Launcher setup wizard must generate exactly these fields in `arcade.config.json`
- [ ] Both engineers agree on the exact structure of `arcade.config.json` (reference Appendix B)

### ⚡ CHECKPOINT 1-B (End of Phase)

- [ ] `uvicorn backend.main:app` starts cleanly, no deprecation warnings (AC-19)
- [ ] `GET /health` returns HTTP 200 with correct JSON body
- [ ] `alembic upgrade head` applies all migrations to a fresh database
- [ ] WAL mode confirmed: `sqlite3 arcade.db "PRAGMA journal_mode;"` → `wal`
- [ ] Agent WebSocket connection with invalid secret is rejected
- [ ] Launcher shows Activation screen when `license.key` is missing
- [ ] Launcher shows setup wizard after valid `license.key` is placed (AC-12)
- [ ] All licensing unit tests pass (5 outcomes covered)

---

### Epic 1.1: FastAPI Application Skeleton (ENG-A)

#### Feature 1.1.1: Core Configuration (`backend/core/config.py`)

- [x] **Task: Implement `arcade.config.json` loader**
  - [x] Create `backend/core/config.py` with a `Settings` Pydantic model containing all fields from Appendix B
  - [x] `load_config(path: str = "arcade.config.json") -> Settings`: reads and validates JSON
  - [x] `get_config()`: cached singleton (module-level, loaded once at startup)
  - [x] Handle `FileNotFoundError` → `RuntimeError("arcade.config.json not found. Run the setup wizard.")`
  - [x] **Security note:** Document in `docs/deployment.md` that `arcade.config.json` must have `chmod 600` permissions on Linux/macOS
  - [x] **Definition of done:** `from backend.core.config import get_config; c = get_config()` works with a valid config file

#### Feature 1.1.2: Async Database Layer (`backend/core/database.py`) ✅ _Complete_

- [x] **Task: Configure SQLAlchemy async engine with SQLite WAL pragmas**
  - [x] Create `backend/core/database.py`
  - [x] `async_engine = create_async_engine("sqlite+aiosqlite:///./arcade.db", echo=False)`
  - [x] Use `@event.listens_for(async_engine.sync_engine, "connect")` to set pragmas on every new connection:
    ```python
    PRAGMA journal_mode = WAL;
    PRAGMA busy_timeout = 5000;
    PRAGMA synchronous = NORMAL;
    PRAGMA foreign_keys = ON;
    PRAGMA mmap_size = 134217728;
    PRAGMA cache_size = -32000;
    PRAGMA wal_autocheckpoint = 1000;
    ```
  - [x] `AsyncSessionLocal = async_sessionmaker(async_engine, expire_on_commit=False)`
  - [x] `async def get_db()` dependency yielding `AsyncSession`
  - [x] **⚠ RISK (R-01):** Validated with ARCH-01 — concurrent write test in `test_database.py` passes (50 concurrent UPDATEs, no `database is locked` errors)
  - [x] Added DB readiness check (`_verify_database_wal()`) to `main.py` lifespan startup
  - [x] Tests: `backend/tests/test_database.py` — WAL mode, `busy_timeout`, `foreign_keys` pragmas; `get_db()` yields `AsyncSession`; ARCH-01 regression (concurrent writes)

#### Feature 1.1.3: All SQLAlchemy ORM Models (`backend/models/`)

- [x] **Task: Define all ORM models** (ENG-A)
  - [x] Create one file per entity. All models inherit from `Base`. All monetary fields are `Integer` (paise). All timestamps are `DateTime` with `timezone=True`.
  - [x] `models/seat.py`: `Seat` — id, name, zone_id, device_type, status (enum), mac_address, wol_attempts, wol_successes, current_session_id, notes, created_at
  - [x] `models/session.py`: `Session` — id, seat_id, member_id, staff_id, started_at, ended_at, paused_at, total_paused_seconds, status (enum: ACTIVE, PAUSED, COMPLETED), locked_rate_paise, locked_pricing_model, rate_block_minutes, package_entitlement_id, promotion_id, shift_id
  - [x] `models/invoice.py`: `Invoice`, `InvoiceLineItem` — invoice: id, session_id, member_id, total_paise, payment_method, created_at; line_item: id, invoice_id, description, amount_paise, line_type
  - [x] `models/member.py`: `Member` — id, name, phone (unique), wallet_paise, loyalty_points, tier (enum: BRONZE, SILVER, GOLD), created_at
  - [x] `models/staff.py`: `Staff` — id (staff_id string), name, pin_hash, role (enum: ADMIN, CASHIER), is_active, token_version, created_at
  - [x] `models/shift.py`: `Shift` — id, opened_by, closed_by, opened_at, closed_at, opening_cash, closing_cash, expected_cash, is_open
  - [x] `models/menu_item.py`: `MenuItem` — id, name, category, price_paise, is_available, stock_quantity (nullable), low_stock_threshold (nullable)
  - [x] `models/session_pos_item.py`: `SessionPOSItem` — id, session_id, menu_item_id, quantity, unit_price_paise
  - [x] `models/package.py`: `Package` — id, name, minutes (nullable), is_day_pass, valid_hours_start, valid_hours_end, price_paise, is_active
  - [x] `models/package_entitlement.py`: `MemberPackageEntitlement` — id, member_id, package_id, total_minutes, remaining_minutes, status (ACTIVE, EXHAUSTED, EXPIRED), purchased_at, expires_at
  - [x] `models/promotion.py`: `Promotion` — id, name, discount_pct, applies_from (time), applies_to (time), days_of_week (JSON), is_active
  - [x] `models/voucher.py`: `Voucher` — id, code (unique), value_paise, expires_at, redeemed_at, redeemed_by_member_id
  - [x] `models/reservation.py`: `Reservation` — id, seat_id, member_id, customer_name, reserved_from, reserved_to, notes, status (PENDING, CONFIRMED, CANCELLED, COMPLETED)
  - [x] `models/zone.py`: `Zone` — id, name, rate_paise_per_minute, pricing_model (enum), rate_block_minutes
  - [x] `models/audit_log.py`: `AuditLog` — id, staff_id (nullable), action, entity_type, entity_id, detail, created_at — **no update/delete columns**
  - [x] `models/license_status.py`: `LicenseStatus` — id, cafe_name, hardware_id, license_type, verified_at, trial_expires_at
  - [x] `models/settings.py`: `AppSettings` — key (unique), value (JSON string) — key-value store for feature flags and all mutable config
  - [x] `models/expense.py`: `Expense` — id, category, amount_paise, description, recorded_by, created_at (feature-flagged)
  - [x] `models/event.py`: `Event`, `EventParticipant`, `EventMatch` (feature-flagged)
  - [x] Create `models/__init__.py` exporting all models — **must be kept in sync with Alembic `env.py`**
  - [x] **Definition of done:** `mypy backend/models/` passes with zero errors

#### Feature 1.1.4: Alembic Migrations

- [x] **Task: Initialise Alembic and create initial migration**
  - [x] Run `alembic init alembic` in `backend/`
  - [x] Update `alembic/env.py`: import all models from `backend.models`; use `async_engine`; set `target_metadata = Base.metadata`
  - [x] Generate migration: `alembic revision --autogenerate -m "001_initial"`
  - [x] Review generated migration — confirm all tables, columns, and constraints are correct
  - [x] Apply: `alembic upgrade head`
  - [x] Seed data: create `backend/scripts/seed_dev.py` that populates: 2 zones, 8 seats, 2 staff (admin + cashier), 5 menu items, 3 members, feature flags with defaults
  - [x] **Definition of done:** Fresh database has all tables; `alembic current` shows `head`; seed script runs without errors

#### Feature 1.1.5: Core Security (`backend/core/security.py`)

- [x] **Task: Implement PIN hashing, JWT, rate limiting, and lockout**
  - [x] Argon2id PIN hashing using `argon2-cffi` `PasswordHasher(time_cost=2, memory_cost=102400, parallelism=8)` — matches OWASP recommendations
  - [x] JWT create/decode using `python-jose` with `algorithm="HS256"` and `jwt_secret` from config
  - [x] JWT payload: `{sub: staff_id, role, token_version, exp}` — **always validate `token_version`** against DB on every request
  - [x] In-memory brute-force protection: 5 failed login attempts → 15-minute lockout by IP (use `dict` with timestamp; or `cachetools.TTLCache`)
  - [x] `async def get_current_staff(token, db)` dependency — validates JWT and `token_version`
  - [x] `async def require_admin(staff)` and `async def require_cashier(staff)` role dependencies
  - [x] **Security note:** `token_version` invalidation means stale JWTs are rejected immediately after PIN change or deactivation — critical for staff termination scenarios

#### Feature 1.1.6: WebSocket Manager (`backend/core/ws_manager.py`)

- [x] **Task: Implement `WebSocketManager`**
  - [x] Dashboard connections: `connect_dashboard(ws)`, `disconnect_dashboard(ws)`, `broadcast_to_dashboards(event, data)`
  - [x] Agent connections: `connect_agent(seat_id, ws, secret)` — validates `agent_secret` from config on connection; rejects if missing or wrong
  - [x] `send_to_agent(seat_id, command_dict)` — raises `AgentOfflineError` if not connected (caller handles gracefully)
  - [x] `disconnect_agent(seat_id)`
  - [x] Heartbeat: PING agents every 30 s; disconnect if no PONG within 10 s grace period
  - [x] Max WebSocket message size: 5 MB (enforced at `uvicorn` level via `--ws-max-size 5242880`)
  - [x] Agent REGISTER handler: validates secret, broadcasts seat status to dashboards
  - [x] Agent SYNC handler: reconciles session time after reconnect via `reconcile()` / `server_anchor_elapsed()` (FR-SES-009)
  - [x] Agent HEALTH handler: stores latest health metrics; broadcasts `health_update` to dashboards
  - [x] Agent STAFF_OVERRIDE handler: broadcasts alert to dashboards
  - [x] FastAPI endpoints: `/ws/dashboard` and `/ws/agent/{seat_id}` (with `?secret=` query param)
  - [x] Module-level singleton `manager`; lifespan shutdown calls `close_all()`
  - [x] 27 tests; all 89 backend tests pass with zero regressions

#### Feature 1.1.7: Feature Flags (`backend/core/feature_flags.py`)

- [x] **Task: Implement feature flag loading and enforcement**
  - [x] Load all flags from `AppSettings` table at startup; cache in memory
  - [x] `get_flag(name: str) -> bool` — reads from cache (refreshed when settings are updated)
  - [x] `def require_feature(flag_name: str)` — FastAPI dependency that returns HTTP 503 if flag is off
  - [x] Default flag values: see Appendix D (applied by seed script on first run)
  - [x] Invalidate cache when `PATCH /api/settings` is called

#### Feature 1.1.8: All Pydantic Schemas (`backend/schemas/`)

- [x] **Task: Define all Pydantic request/response schemas**
  - [x] One file per domain: `schemas/seat.py`, `schemas/session.py`, `schemas/invoice.py`, `schemas/member.py`, `schemas/staff.py`, `schemas/shift.py`, `schemas/pos.py`, `schemas/package.py`, `schemas/promotion.py`, `schemas/voucher.py`, `schemas/reservation.py`, `schemas/analytics.py`, `schemas/audit.py`, `schemas/settings.py`, `schemas/health.py`
  - [x] All monetary fields: `amount_paise: int` — **never `float`** (R-06 mitigation)
  - [x] All string fields: include `max_length` constraints to prevent oversized inputs
  - [x] All timestamps: `datetime` with `timezone=True`; UTC enforced
  - [x] Response schemas separate from request schemas (avoid leaking internal fields like `pin_hash`)
  - [x] **Definition of done:** `mypy backend/schemas/` passes; all schemas import cleanly

#### Feature 1.1.9: Repository Layer Stubs (`backend/repositories/`)

- [x] **Task: Create all repository files with method stubs**
  - [x] One repository file per entity (standard CRUD: `create`, `get_by_id`, `list`, `update`, `delete_by_id`)
  - [x] All methods are `async def` accepting `db: AsyncSession` as first parameter
  - [x] Return ORM model instances (not dicts)
  - [x] Special methods:
    - `seat_repo.py`: `list_with_mac()`, `update_status()`
    - `session_repo.py`: `get_active_by_seat()`, `list_active()`, `list_by_shift()`
    - `invoice_repo.py`: `get_by_session()`
    - `member_repo.py`: `get_by_phone()`, `search(query)`
    - `package_repo.py`: atomic `drawdown_minutes(entitlement_id, minutes) -> bool` using `UPDATE ... WHERE remaining_minutes >= ?` (atomicity without locking — R-06 mitigation)
    - `audit_repo.py`: **only `create` and `list`** — no update or delete (immutability enforced at repo layer)
  - [x] Stubs may `raise NotImplementedError` — they will be implemented in feature phases
  - [x] **Definition of done:** All repo files import cleanly; `mypy` passes on the stubs

#### Feature 1.1.10: FastAPI Application Entry Point (`backend/main.py`)

- [x] **Task: Create FastAPI app with `lifespan` context manager**
  - [x] Use `@asynccontextmanager` for `lifespan` — **not `@app.on_event`** (deprecated, AC-19)
  - [x] Startup: `alembic upgrade head`, WAL pragma validation, `recover_active_sessions()`, `boot_all_seats()`, APScheduler start, WebSocket manager init
  - [x] Shutdown: APScheduler shutdown, WebSocket connection cleanup, SQLAlchemy engine dispose
  - [x] Register all routers under `/api/` prefix
  - [x] Serve `frontend/dist/` as static files at `/`; `index.html` fallback for SPA routing
  - [x] `GET /health` endpoint: returns `{status, version, license_type, uptime, seat_count, active_sessions}`
  - [x] WebSocket routes: `GET /ws/dashboard`, `GET /ws/agent/{seat_id}`
  - [x] Exception handlers: `HTTPException`, `RequestValidationError`, generic `Exception` (log + return 500)
  - [x] CORS: allow `http://localhost:*` in development; in production, `arcade.config.json` host

---

### Epic 1.2: Licensing Subsystem (ENG-B)

#### Feature 1.2.1: Hardware Fingerprinting (`backend/licensing/fingerprint.py`)

- [ ] **Task: Implement `get_hardware_id()`**
  - [ ] Primary: `machineid.id()` from `py-machineid` — works without admin privileges on all three OSes
  - [ ] Fallback chain if `py-machineid` fails: `hostname + first_mac_address` (sorted, lowercased, SHA-256 hex)
  - [ ] Return a stable, consistent string — same value across reboots on the same hardware
  - [ ] **⚠ RISK (R-08):** Document that hardware changes (motherboard replacement) will invalidate the license

#### Feature 1.2.2: Public Key Embedding (`backend/licensing/public_key.py`)

- [x] **Task: Generate Ed25519 keypair and embed public key**
  - [x] Generate keypair: `python -c "from nacl.signing import SigningKey; k = SigningKey.generate(); print(k.encode().hex(), k.verify_key.encode().hex())"`
  - [x] Store **private key only** in `tools/keygen/private_key.pem` (plaintext hex, gitignored, never committed)
  - [x] Embed **only the public key hex** in `backend/licensing/public_key.py`:
    ```python
    # NEVER add the private key to this file or the repository.
    ARCADE_PUBLIC_KEY_HEX = "c9a1...4f3e"  # 64-char hex
    ```
  - [x] Add CI check: fail build if any `*.pem` file or `private_key*` is detected in git history
  - [x] **⚠ RISK (R-05):** Verify `tools/keygen/private_key.pem` is in `.gitignore` before first commit of this feature

#### Feature 1.2.3: License Verification (`backend/licensing/verify.py`) ✅

- [x] **Task: Implement `check_license()`**
  - [x] `LicenseError` enum: `MISSING`, `INVALID_SIGNATURE`, `HARDWARE_MISMATCH`, `TRIAL_EXPIRED`
  - [x] `LicenseResult` dataclass: `ok: bool`, `error: LicenseError | None`, `payload: dict | None`
  - [x] `check_license(license_path: str = "license.key") -> LicenseResult`:
    1. Check file exists → `MISSING` if not
    2. Base64-decode and JSON-parse the file content
    3. Verify Ed25519 signature using `nacl.signing.VerifyKey` and `ARCADE_PUBLIC_KEY_HEX` → `INVALID_SIGNATURE` on failure
    4. Compare `payload["hardware_id"]` to `get_hardware_id()` → `HARDWARE_MISMATCH` if different
    5. If `license_type == "TRIAL"` and `date.today() > trial_expires_at` → `TRIAL_EXPIRED`
    6. Return `LicenseResult(ok=True, payload=payload)`
  - [x] **Definition of done:** Unit tests covering all 5 outcomes (valid, missing, bad signature, hardware mismatch, trial expired) all pass (FR-LIC-007, FR-LIC-008)

#### Feature 1.2.4: Internal Keygen Tool (`tools/keygen/generate_license.py`) ✅

- [x] **Task: Build the offline license key generation CLI**
  - [x] CLI args: `--hardware-id`, `--cafe-name`, `--license-type` (PERPETUAL | TRIAL), `--trial-days` (optional, default 30)
  - [x] Read private key from `tools/keygen/private_key.pem`
  - [x] Build JSON payload: `{cafe_name, hardware_id, license_type, issue_date, trial_expires_at (if TRIAL)}`
  - [x] Sign canonical JSON (sorted keys, no whitespace) with `SigningKey.sign()`
  - [x] Output: `license.key` containing Base64-encoded `{"payload": ..., "signature": ...}`
  - [x] Print confirmation with cafe name, license type, and hardware ID
  - [x] **Definition of done:** Running the tool produces a `license.key` that passes `check_license()` when hardware ID matches

#### Feature 1.2.5: Tkinter Launcher (`launcher.py`)

- [x] **Task: Implement the Tkinter Launcher GUI**
  - [x] **License check at every launch (FR-SYS-008):** call `check_license()` before showing any UI; route based on result
  - [x] **Activation Screen** (when license missing, invalid, or mismatched):
    - Display Hardware ID in a copyable read-only `Entry` widget
    - Instructions label: "Send this Hardware ID to Seller to receive your license.key"
    - "Browse for license.key" button: opens file dialog, copies file to app root, re-runs `check_license()`
    - Display specific error message per `LicenseError` variant (per SDD §16.7 table)
    - Retry button to re-check without browsing
  - [x] **Setup Wizard** (first launch with valid license, no `arcade.config.json`):
    - Step 1: Cafe name, server host, server port
    - Step 2: Admin Staff ID + PIN; Cashier Staff ID + PIN; Staff Override Code (optional — leave blank to disable)
    - Step 3: Number of seats → generates one `agent_secret` per seat using `secrets.token_hex(32)`
    - On finish: write `arcade.config.json` with Argon2id-hashed PINs; hash override code if provided; `jwt_secret = secrets.token_hex(32)`; all `agent_secrets`
    - Also write `license_status` record to DB
  - [x] **Main Screen** (license valid and config exists):
    - Start/Stop Server button: spawns/terminates `uvicorn backend.main:app` as subprocess
    - Live log display: `ScrolledText` tailing `stdout`/`stderr`
    - Server status indicator (green/red dot using canvas)
    - Open Dashboard button: opens `http://localhost:{port}` in default browser
  - [x] **Close confirmation (FR-SYS-010):** if server running, `messagebox.askyesno("Confirm Exit", "The Arcade server is still running. Closing will stop it. Continue?")`. Terminate server on confirm.
  - [x] **Definition of done:** AC-12, AC-15, AC-23 all satisfied; Launcher runs on Windows, macOS, Linux without modification

### Testing Requirements (Phase 1)

- [x] `pytest backend/tests/test_licensing.py` — all 5 `check_license()` outcomes (FR-LIC-007, FR-LIC-008)
- [x] `pytest backend/tests/test_security.py` — PIN hashing, JWT create/decode, rate limiting, lockout, `token_version` validation, stale token rejection
- [x] `pytest backend/tests/test_database.py` — WAL mode, `busy_timeout`, `foreign_keys` pragmas are set; concurrent write test (ARCH-01 coverage)
- [x] `pytest backend/tests/test_ws_manager.py` — agent secret validation, broadcast, heartbeat, REGISTER, SYNC handlers
- [x] `pytest backend/tests/test_feature_flags.py` — all 10 flags load correctly; disable/enable round-trips; cache invalidation

### Documentation Requirements (Phase 1)

- [ ] `docs/architecture.md`: system diagram, component descriptions, technology choices with rationale (why SQLite not Postgres, why Electron not web kiosk, etc.)
- [ ] `docs/developer-guide.md`: local setup, run tests, linting commands, migration commands, seed script usage
- [ ] `docs/security/key-management.md`: keygen process, private key custody policy, license file lifecycle
- [ ] Update `README.md` Getting Started section with working commands

---

## Phase 2: Seat Management & Session Lifecycle

### Objectives

End-to-end session workflow: staff starts a session on a seat → kiosk overlay hides on client PC → timer runs → staff ends session. This is the minimum viable product (MVP).

### Deliverables

- `SeatService`, `SessionService` with start/pause/resume/stop
- Wake-on-LAN service with BOOTING/UNREACHABLE watchdog
- Staff authentication API (login endpoint)
- All seat and session REST API routes
- React Dashboard: seat grid (`SeatGrid`, `SeatCard`) with real-time WebSocket updates
- Electron agent (Windows-first): hardened kiosk overlay, WebSocket client with reconnect, session store SQLite, HIDE_OVERLAY / SHOW_OVERLAY commands working end-to-end
- Agent REGISTER, HEALTH, SYNC, STAFF_OVERRIDE WebSocket message handling

### Dependencies

- Phase 1 complete (⚡ CHECKPOINT 1-B passed)
- ARCH-02 validated (Electron kiosk on Windows)
- ARCH-06 validated (WebSocket reconnect + SYNC)

### Parallel Work

**ENG-A:** `SeatService`, `SessionService`, WoL service, Auth API, seat/session routers
**ENG-B:** Electron agent kiosk + WebSocket client + session store; React dashboard seat grid

### ⚡ CHECKPOINT 2-A (End of Phase)

Both engineers test together on real hardware:

- [ ] Agent connects to server; dashboard shows seat status changing in real time
- [ ] Session started on `seat_001` → overlay hides on client PC (`HIDE_OVERLAY` received)
- [ ] Agent disconnects for 30 seconds, reconnects → SYNC payload sent → session time reconciled (AC-07)
- [ ] Staff logs in, gets JWT; wrong PIN returns 401; 5th wrong PIN triggers lockout

---

### Epic 2.1: Seat and Session Services (ENG-A)

#### Feature 2.1.1: Seat Service

- [x] **Task: Implement `SeatService` (`backend/services/seat_service.py`)**
  - [x] `list_seats(db)` — returns all seats with current status
  - [x] `get_seat(seat_id, db)` — raises 404 if not found
  - [x] `set_maintenance(seat_id, note, db, staff)` — sets `MAINTENANCE`, writes note, logs audit `SEAT_MAINTENANCE_ON` (FR-SEAT-006)
  - [x] `clear_maintenance(seat_id, db, staff)` — sets `AVAILABLE`, logs audit `SEAT_MAINTENANCE_OFF`
  - [x] `update_mac_address(seat_id, mac, db)` — called from WebSocket REGISTER handler
- [x] After any status change: `ws_manager.broadcast_to_dashboards("seat_updated", seat_data)` (FR-SEAT-005)
  - [x] **Definition of done:** Status change triggers WebSocket broadcast to all connected dashboards

- [x] **Task: Implement Seat API Router (`backend/api/routers/seats.py`)**
  - [x] `GET /api/seats` — list all seats (Cashier auth)
  - [x] `GET /api/seats/{id}` — get seat details (Cashier auth)
  - [x] `PATCH /api/seats/{id}/maintenance` — set maintenance (Admin auth)
  - [x] `DELETE /api/seats/{id}/maintenance` — clear maintenance (Admin auth)
  - [x] `POST /api/seats/{id}/wol` — send WoL (Admin auth)
  - [x] All routes: correct auth dependencies, correct HTTP status codes, documented errors

#### Feature 2.1.2: Session Service ✅ _Complete_

- [x] **Task: Implement `SessionService` — start, pause, resume (`backend/services/session_service.py`)**
  - [x] `start_session(seat_id, member_id, db, staff)`:
    1. Load seat; validate status `AVAILABLE` or `RESERVED` → 409 `SEAT_UNAVAILABLE` otherwise
    2. Check `require_member_for_session` flag; 400 if ON and no `member_id`
    3. Validate no existing ACTIVE session for this seat
    4. Resolve pricing rate via `billing_service.resolve_rate()` (stubs resolve_rate returning zero for now — billing added Phase 3)
    5. Create `Session` record with `status=ACTIVE`, `started_at=utcnow()`
    6. Update seat status to `IN_USE`
    7. Broadcast `seat_updated` to dashboards
    8. Send `HIDE_OVERLAY` to agent (log warning if agent offline — do not block)
    9. Write audit: `SESSION_START`
    10. Return `SessionResponse`
  - [x] `pause_session(session_id, db, staff)`: validate ACTIVE → `PAUSED`; `paused_at=utcnow()`; seat `PAUSED`; send `SHOW_OVERLAY`; broadcast; audit `SESSION_PAUSE`
  - [x] `resume_session(session_id, db, staff)`: validate PAUSED; accumulate `total_paused_seconds`; `ACTIVE`; seat `IN_USE`; send `HIDE_OVERLAY`; broadcast; audit `SESSION_RESUME`
  - [x] `recover_active_sessions(db)`: called at server startup; loads all ACTIVE sessions; broadcasts current seat states; agents can re-sync (FR-SES-009, AC-22)
  - [x] **Definition of done:** Full lifecycle (start → pause → resume) works via REST; WebSocket broadcasts verified

- [x] **Task: Implement Session API Router (`backend/api/routers/sessions.py`)**
  - [x] `POST /api/sessions` — start session (Cashier)
  - [x] `PATCH /api/sessions/{id}/pause` (Cashier)
  - [x] `PATCH /api/sessions/{id}/resume` (Cashier)
  - [x] `GET /api/sessions/{id}` (Cashier)
  - [x] `GET /api/sessions/active` (Cashier)

#### Feature 2.1.3: Wake-on-LAN Service ✅

- [x] **Task: Implement `WolService` (`backend/services/wol_service.py`)**
  - [x] `send_magic_packet(mac_address, broadcast="255.255.255.255", port=9)`: constructs UDP magic packet (6×0xFF + 16×MAC bytes)
  - [x] `boot_all_seats(db)`: called at startup; sends WoL to all seats with MAC; sets status to `BOOTING`; starts 60-second watchdog per seat (FR-WOL-001, FR-WOL-005)
  - [x] Watchdog: after 60s, if seat still `BOOTING` → set `UNREACHABLE`, broadcast (FR-WOL-005, FR-WOL-006)
  - [x] `send_wol_to_seat(seat_id, db)`: single-seat WoL from dashboard (FR-WOL-003)
  - [x] Track `wol_attempts` and `wol_successes` per seat (FR-WOL-004)
  - [x] `override_seat_online(seat_id, db)`: manual override for manually-started machines (FR-WOL-007)
  - [x] **⚠ RISK (R-04):** WoL requires MAC address registered; seats without MAC skip WoL gracefully

#### Feature 2.1.4: Staff Authentication API

- [x] **Task: Implement `POST /api/auth/login` and auth dependencies**
  - [x] `POST /api/auth/login`: accepts `{staff_id, pin}`; validates PIN with Argon2id; checks `is_active`; returns JWT with 8-hour expiry; logs audit `STAFF_LOGIN`
  - [x] Rate limiting: 5 failed attempts per IP → 15-minute lockout; return 429 with `retry_after` header
  - [x] `POST /api/auth/refresh`: refreshes JWT (extends expiry) if current token is valid
  - [x] `POST /api/auth/logout`: client-side token discard (stateless — `token_version` increment is handled by PIN change/deactivation)

---

### Epic 2.2: Electron Agent (ENG-B)

#### Feature 2.2.1: Agent Platform Abstraction Layer ✅ _Complete_

- [x] **Task: Create `PlatformService` interface and Windows implementation**
  - [x] Define `IPlatformService` interface in `agent/src/main/platform/types.ts`: `showKioskOverlay()`, `hideKioskOverlay()`, `updateTimer()`, `sendAnnouncement()`, `restartPC()`, `shutdownPC()`, `captureScreenshot()`, `enableAutoStart()`, `disableAutoStart()`, `getSystemInfo()`
  - [x] Implement `agent/src/main/platform/windows.ts`:
    - `showKioskOverlay()` / `hideKioskOverlay()`: `BrowserWindow` with `kiosk: true`, `alwaysOnTop: true`, `frame: false`, `closable: false`, `devTools: false`
    - `restartPC()`: `execAsync('shutdown /r /t 0')`
    - `shutdownPC()`: `execAsync('shutdown /s /t 0')`
    - `captureScreenshot()`: `desktopCapturer.getSources({types: ['screen']})` → `sharp` resize to 1280×720 max → JPEG at 80% quality; fallback to raw PNG on sharp failure
    - `enableAutoStart()` / `disableAutoStart()`: registry `HKCU\Software\Microsoft\Windows\CurrentVersion\Run` via `reg.exe`
    - Block keyboard shortcuts: `Alt+F4`, `Ctrl+P`, `F12`, `Ctrl+Shift+I`, `Alt+Shift+I` intercepted in `webContents.on('before-input-event')`
    - Edge-case hardening: `isDestroyed` guard before `hide()`/`destroy()`; screenshot no-sources error; sharp processing fallback
  - [x] Factory: `getPlatformService(): IPlatformService` — detects OS via `process.platform`; throws on unsupported platform
  - [x] **Wired into `agent/src/main/index.ts`**: `bootstrap()` calls `getPlatformService()` on app ready
  - [x] **Tests**: `tests/platform/types.test.ts` (2 passing); `tests/platform/factory.test.ts` (2 passing — OS detection, unsupported platform); `tests/platform/windows.test.ts` (7 passing — method existence, restart/shutdown, screenshot, autostart register/unregister, system info)

#### Feature 2.2.2: Agent WebSocket Client

- [x] **Task: Implement `agent/src/main/ws/client.ts`**
  - [x] On connect: send `REGISTER {seat_id, mac_address, agent_secret, hostname, os}` — server validates secret and accepts or closes connection
  - [x] Exponential backoff reconnection: 1s → 2s → 4s → 8s → 16s → 30s cap; jitter ±10%
  - [x] Heartbeat: send `PING` every 30s; if no `PONG` within 10s, reconnect
  - [x] On reconnect (if session was active): send `SYNC {session_id, local_elapsed_seconds, disconnect_at, reconnect_at}` (FR-SES-009, R-07 mitigation)
  - [x] Message handlers: `HIDE_OVERLAY` → platform.hideKioskOverlay(); `SHOW_OVERLAY` → platform.showKioskOverlay(); `TAKE_SCREENSHOT` → capture + send response; `SHOW_MESSAGE` → display overlay dialog; `RESTART` → platform.restartPC(); `SHUTDOWN` → platform.shutdownPC(); `LOW_TIME_WARNING` → show timer warning; `RESET_OVERRIDE` → clear override flag
  - [x] `STAFF_OVERRIDE` trigger: show numeric PIN dialog; on correct Argon2 verification → `hideKioskOverlay()` locally; send `STAFF_OVERRIDE` event to server; suppress subsequent `SHOW_OVERLAY` commands while override is active

#### Feature 2.2.3: Agent Local SQLite Session Store ✅ _Complete_

- [x] **Task: Implement `agent/src/main/storage/session_store.ts`**
  - [x] Use `better-sqlite3` (synchronous, appropriate for Electron main process)
  - [x] Schema: `sessions(session_id, seat_id, started_at, local_elapsed_seconds, disconnect_at, is_synced, status, updated_at)`
  - [x] `persistSession(sessionId, seatId, startedAt)`: saves session state on `HIDE_OVERLAY` (session start); `ON CONFLICT(session_id) DO UPDATE` for idempotency
  - [x] `updateElapsed(sessionId, elapsedSeconds)`: called every 10 seconds during active session via `startElapsedTimer()` in `ws/client.ts`
  - [x] `markDisconnect(sessionId, disconnectAt)`: called on WS disconnect to persist disconnect timestamp for crash recovery
  - [x] `getUnsyncedSession()`: returns session data for SYNC payload on reconnect (queries `is_synced = 0`)
  - [x] `markSynced(sessionId)`: called after successful SYNC acknowledgment from server
  - [x] `clearSession(sessionId)`: deletes session row on `SHOW_OVERLAY` (session end)
  - [x] `close()`: clean database connection close
  - [x] Wired into `agent/src/main/index.ts`: creates `~/.arcade-agent/sessions.db` and passes store to `AgentWebSocketClient`
  - [x] Wired into `agent/src/main/ws/commands.ts`: `HIDE_OVERLAY` persists session, `SHOW_OVERLAY` clears session
  - [x] **Tests**: `agent/tests/storage/session_store.test.ts` — 6 tests (persist/retrieve, updateElapsed, markDisconnect, markSynced, clearSession, re-persist idempotency) all passing
  - [x] **Definition of done:** Agent crash and restart recovers session state from SQLite; SYNC is sent correctly (AC-7)

#### Feature 2.2.4: Agent Kiosk Overlay UI ✅ _Complete_

- [x] **Task: Build kiosk overlay renderer process**
  - [x] Full-screen BrowserWindow: `kiosk: true`, `alwaysOnTop: true`, no menu bar, no title bar
  - [x] Overlay content: cafe branding, clock, "Session in progress" indicator
  - [x] Low-time warning dialog: shown when `LOW_TIME_WARNING` received — "5 minutes remaining"
  - [x] Staff override PIN dialog: shown when configured key combination pressed (`Ctrl+Shift+O`) — only if `override_code_hash` is set in `agent.config.json`
  - [x] HEALTH metrics: send every 60 seconds — `{seat_id, cpu_pct, ram_pct, cpu_temp, disk_used_gb, disk_total_gb}` via `systeminformation`
  - [x] **Implementation**: `src/renderer/preload.ts` (secure IPC bridge), `src/renderer/index.ts` (renderer entry), `src/renderer/kiosk.css` (styling), `src/renderer/components/kiosk-overlay.ts`, `low-time-warning.ts`, `staff-override-dialog.ts`
  - [x] **WindowsPlatformService** updated: loads renderer from file via `loadFile()`, preload script path, blocks `F11`/`Escape`, adds `isKioskVisible()`
  - [x] **IPC wired**: `call-staff` and `staff-override` channels in main process; `overlay:update`, `overlay:timer`, `overlay:announcement`, `overlay:low-time` channels in preload
  - [x] **staff-override**: timing-safe PIN comparison (placeholder for Argon2id verify), sends `STAFF_OVERRIDE` to server on success
  - [x] **Build**: `tsconfig.renderer.json` for renderer build; `electron-builder.yml` includes `dist/renderer/**/*`
  - [x] **Tests**: `agent/tests/renderer/preload.test.ts` (3 tests), `kiosk-overlay.test.ts` (7 tests), `low-time-warning.test.ts` (4 tests), `staff-override-dialog.test.ts` (4 tests) — all passing
  - [x] **Definition of done:** Full test suite: 56 tests across 12 test files; all passing

#### Feature 2.2.5: Agent Configuration Loading ✅ _Complete_

- [x] **Task: Load and validate `agent.config.json`**
  - [x] Read `agent.config.json` from the same directory as the agent executable; fall back to cwd in dev
  - [x] Fields: `server_url`, `seat_id`, `agent_secret`, `override_code_hash` (nullable)
  - [x] Validate all required fields present; exit with clear error via `ConfigError` dialog if missing
  - [x] `agent.config.json` must be `chmod 600` on Linux/macOS — documented in `docs/agent-setup.md`
  - [x] `agent.config.json` is in `.gitignore`
  - [x] **Tests**: `agent/tests/config/validator.test.ts` (10 tests), `agent/tests/config/loader.test.ts` (5 tests) — all passing
  - [x] **Definition of done:** 71 tests across 14 test files; all passing

---

### Epic 2.3: React Dashboard — Seat Grid (ENG-B)

#### Feature 2.3.1: Dashboard WebSocket Hook ✅

- [x] **Task: Implement `useWebSocket` hook (`frontend/src/hooks/useWebSocket.ts`)**
  - [x] Connect to `ws://server/ws/dashboard`
  - [x] Exponential backoff reconnection (mirrors agent behavior)
  - [x] On `seat_updated` event: invalidate React Query cache for seats
  - [x] On `health_update` event: update health metrics store (Zustand)
  - [x] On disconnect: show "Connection lost" indicator; attempt reconnect

#### Feature 2.3.2: Seat Grid Components

- [x] **Task: Implement `SeatGrid` and `SeatCard` components**
  - [x] `SeatGrid`: queries `GET /api/seats`; displays all seats in a responsive grid; subscribes to WebSocket updates
  - [x] `SeatCard`: displays seat name, status (colour-coded: AVAILABLE=green, IN_USE=orange, PAUSED=yellow, RESERVED=blue, MAINTENANCE=grey, BOOTING=blue-pulse, UNREACHABLE=red), elapsed time (live ticking for IN_USE)
  - [x] Click on seat → modal with actions: Start Session, Pause/Resume, Checkout, Set Maintenance, WoL, View Health
  - [x] `SeatStatusBadge`, `ElapsedTimer` subcomponents
  - [x] **Definition of done:** Dashboard shows all seats; status updates arrive < 1 second after server change (AC-01, NFR-PERF-001)

#### Feature 2.3.3: Login Page ✅ _Complete_

- [x] **Task: Implement `Login.tsx` page**
  - [x] Staff ID field + PIN field (masked)
  - [x] `POST /api/auth/login` on submit; store JWT in memory (`zustand` auth store) — **not localStorage** (in-memory only, reset on page refresh requires re-login)
  - [x] Wrong PIN: show error message, increment failure counter
  - [x] 5th failure: show lockout message with remaining time
  - [x] Success: redirect to Dashboard
  - [x] **Definition of done:** Login flow works; locked-out account shows correct message; valid JWT stored in app state

### Testing Requirements (Phase 2)

- [x] `pytest backend/tests/test_seat_service.py` — list, status change, maintenance, WoL triggers, BOOTING → UNREACHABLE watchdog
- [x] `pytest backend/tests/test_session_service.py` — start (valid/invalid seat status), pause, resume, `recover_active_sessions()`, concurrent start rejection
- [x] `pytest backend/tests/test_auth.py` — login success, wrong PIN, lockout after 5 failures, `token_version` invalidation
- [x] `pytest backend/tests/test_wol_service.py` — magic packet construction (6×0xFF + 16×MAC verified), watchdog timeout, boot-all-seats, override, success callback
- [x] Agent: `npm test` — 56 tests across 12 test files all passing: `session_store.ts` (6), `ws/client.ts` (9), `ws/commands.ts` (8), `platform/windows.ts` (7), `renderer/preload.test.ts` (3), `renderer/kiosk-overlay.test.ts` (7), `renderer/low-time-warning.test.ts` (4), `renderer/staff-override-dialog.test.ts` (4) / remaining: `ipc/handlers.ts` (screenshot resize)
- [x] Frontend: `npm test` — unit tests for `useWebSocket` (reconnect, cache invalidation) ✅ — `SeatCard` (status colours, elapsed timer) ✅ — `Login` (error/lockout states)
- [x] **End-to-end (manual):** Start server + agent on Windows + dashboard; start session; disconnect network cable 30s; reconnect; verify SYNC sends; verify session billing not lost (AC-07)

### Documentation Requirements (Phase 2)


- [x] `docs/agent-setup.md`: complete Windows installation, `agent.config.json` setup, auto-start configuration
- [x] `docs/api-reference.md`: all seat, session, and auth endpoints with request/response examples
- [x] `docs/developer-guide.md`: WebSocket event format reference, `agent.config.json` schema

---

## Phase 3: Billing Engine, POS, Inventory & Receipts

### Objectives

Complete checkout workflow: billing engine (all pricing models, package drawdown, promotions), POS with inventory, invoice generation, thermal receipt printing, PDF fallback, and audit log.

### Deliverables

- `BillingService`: all pricing models, package drawdown, promotion discount, loyalty discount
- `POSService` and `InventoryService`
- `PrintService`: thermal ESC/POS + PDF fallback
- `AuditService` and audit API
- `POST /api/sessions/{id}/checkout` working end-to-end
- Frontend: `Checkout.tsx`, `InvoicePanel.tsx`, `POSPanel.tsx`

### Dependencies

- Phase 2 complete (⚡ CHECKPOINT 2-A passed)

### Parallel Work

**ENG-A:** `BillingService`, `POSService`, `InventoryService`, `PrintService`, `AuditService`, checkout API
**ENG-B:** Checkout UI, POS UI, invoice panel components

### ⚡ CHECKPOINT 3-A

- [ ] ENG-A completes checkout API and provides `InvoiceResponse` JSON example
- [ ] ENG-B verifies the schema matches what the UI needs before building the invoice panel
- [ ] End-to-end test: start session → add POS item → checkout → correct invoice → receipt printed (AC-03)

---

### Epic 3.1: Billing Engine (ENG-A)

#### Feature 3.1.1: Rate Resolution and Time Charge Calculation ✅ _Complete_

- [x] **Task: Implement `BillingService` core (`backend/services/billing_service.py`)**
  - [x] `resolve_rate(seat, member, now, db) -> LockedRate`:
    - Get zone pricing from seat's zone
    - Check peak/off-peak schedule from `AppSettings`
    - Check device-type override if present
    - Return `{rate_paise, pricing_model, rate_block_minutes}` — locked at session start (FR-BILL-003)
  - [x] `calculate_time_charge(session, elapsed_seconds, locked_rate) -> int` (returns paise):
    - `PER_MINUTE`: `math.ceil(elapsed_seconds / 60) * rate_per_minute_paise`
    - `FLAT_HOURLY`: `math.ceil(elapsed_seconds / 3600) * rate_per_hour_paise`
    - `TIME_BLOCK`: `math.ceil(elapsed_seconds / (block_minutes * 60)) * rate_per_block_paise`
    - **All arithmetic is integer — never float** (NFR-DATA-002, FR-BILL-001, R-06 mitigation)
    - Partial blocks always charged in full via `math.ceil()`
  - [x] **Definition of done:** All three pricing models produce correct paise amounts for tested scenarios

#### Feature 3.1.2: Checkout Flow ✅ _Complete_

- [x] **Task: Implement full checkout in `BillingService`**
  - [x] `checkout_session(session_id, payment_method, db, staff) -> Invoice` (FR-SES-008):
    1. ~~Load session (must be ACTIVE or PAUSED); 409 if already COMPLETED~~ ✅
    2. ~~Calculate elapsed: `(now - started_at) - total_paused_seconds`~~ ✅
    3. Load all POS items for session — _deferred to Feature 3.1.4_
    4. ~~Calculate time charge via `calculate_time_charge()`~~ ✅
    5. ~~Apply package drawdown (Feature 3.1.3)~~ ✅
    6. Apply promotion discount (locked `promotion_id` from session) — _deferred to Feature 4.1_
    7. Apply member loyalty discount (if member attached, based on `tier`) — _deferred to Feature 4.1_
    8. Sum POS item totals — _deferred to Feature 3.1.4_
    9. `total_paise = time_charge - package_credit - discount + pos_total` (never negative — floor at 0) — _POS items deferred_
    10. Create `Invoice` record ✅
    11. If `payment_method == WALLET`: validate sufficient wallet balance; deduct — _deferred to Feature 4.2_
    12. If member attached: add loyalty points; check tier thresholds; upgrade if met — _deferred to Feature 4.1_
    13. ~~Update session `status=COMPLETED`, `ended_at=now`~~ ✅
    14. ~~Update seat status → `AVAILABLE`~~ ✅
    15. ~~Send `SHOW_OVERLAY` to agent (log warning if offline)~~ ✅
    16. ~~Broadcast `seat_updated` to dashboards~~ ✅
    17. ~~Write audit: `CHECKOUT`~~ ✅
    18. ~~Trigger print **asynchronously** (do not block response on printer)~~ ✅
    19. ~~Return `Invoice`~~ ✅
  - [x] `POST /api/sessions/{id}/checkout` route (Cashier auth)
  - [x] **Definition of done:** AC-03 satisfied; checkout response < 2s even if printer is slow

#### Feature 3.1.3: Package Drawdown ✅ _Complete_

- [x] **Task: Integrate package entitlement into session start and checkout**
  - [x] In `session_service.start_session()`: if member attached, call `package_repo.get_active_entitlement(member_id)` and store `package_entitlement_id` in session (FR-BILL-004)
  - [x] In `billing_service.checkout()`: if `package_entitlement_id` set:
    - Calculate minutes used: `math.ceil(elapsed_seconds / 60)`
    - Call `package_repo.drawdown_minutes(entitlement_id, minutes_used)` — uses `UPDATE ... WHERE remaining_minutes >= ?` for atomicity (FR-BILL-010, R-06 mitigation)
    - If drawdown fails (insufficient minutes): calculate overflow (remaining package minutes + per-minute for rest)
    - Set `package_credit_used_paise` on invoice; create `PACKAGE_CREDIT` and `TIME_CHARGE` line items
  - [x] Exhaustion handling: when `remaining_minutes == 0`, set `EntitlementStatus.EXHAUSTED`
  - [ ] Send `LOW_TIME_WARNING` when package ≤ 5 minutes remaining (FR-SES-007) — _deferred to agent/WS implementation_
  - [x] **Definition of done:** AC-11 — member with 2-hour package checks out after 2.5 hours; first 2 hours from package, last 30 minutes billed per-minute

#### Feature 3.1.4: POS and Inventory Services ✅ _Complete_

- [x] **Task: Implement `POSService` and `InventoryService`**
  - [x] `POSService`: `add_item(session_id, menu_item_id, quantity, db)` — validate ACTIVE session; lock `unit_price_paise` at current price; decrement stock if `enable_inventory`; set low-stock alert if at threshold; set `is_available=False` if stock hits 0
  - [x] `POSService`: `remove_item(pos_item_id, session_id, db)` (Admin only); `list_session_items(session_id, db)`
  - [x] `InventoryService` (feature-flagged): `restock(menu_item_id, quantity, note, db, staff)` — increment stock; re-enable `is_available`; audit log `INVENTORY_RESTOCK`
  - [x] `InventoryService`: `get_low_stock_items(db)` — items with `stock_quantity <= low_stock_threshold`
  - [x] Routers: `backend/api/routers/pos.py`, `backend/api/routers/inventory.py`

#### Feature 3.1.5: Print Service ✅ _Complete_

- [x] **Task: Implement `PrintService` (`backend/services/print_service.py`)**
  - [x] `async def print_receipt(invoice, config)`: async (non-blocking); log WARNING on failure; never block checkout response
  - [x] ESC/POS receipt via `python-escpos`: header (cafe name, bold 2×), separator, seat, date, duration, POS items, separator, time charge, discount (with reason), TOTAL (bold), payment method, footer, cut command
  - [x] All amounts formatted as "Rs. X.XX" — **only place paise→rupees conversion happens** (NFR-DATA-002)
  - [x] `GET /api/invoices/{id}/pdf`: returns print-friendly HTML invoice; triggers `window.print()` in browser (PDF fallback)
  - [x] `GET /api/invoices/{id}`: invoice detail endpoint
  - [x] **⚠ RISK (R-12):** Abstract printer model config (`printer_type`: `usb` | `network`); test with target printer hardware early

#### Feature 3.1.6: Audit Log Service ✅ _Complete_

- [x] **Task: Implement `AuditService` (`backend/services/audit_service.py`)**
  - [x] `async def log(action, entity_type, entity_id, detail, staff_id, db)` — creates `AuditLog` record; immutable (repo only exposes `create` and `list`)
  - [x] Call from: login, session start/stop, checkout, wallet top-up, voucher actions, settings changes, screenshot requests, staff management, inventory restock, override trigger (FR-AUDIT-003)
  - [x] `GET /api/audit` (Admin, paginated, filterable by date range, action type, staff)

---

### Epic 3.2: Frontend — Checkout, POS, Invoice (ENG-B)

#### Feature 3.2.1: POS Panel ✅ _Complete_

- [x] **Task: Implement `POSPanel.tsx` and `POS.tsx`**
  - [x] Menu item grid: name, price, category, stock badge (green ≥ threshold, yellow ≤ threshold, red = 0), greyed-out when `is_available=false`
  - [x] Click item → `POST /api/pos/items` → refresh session tab
  - [x] Session tab: running list of items with subtotal
  - [x] Feature-flagged: only rendered when `enable_pos=true` (NFR-USE-005)

#### Feature 3.2.2: Checkout and Invoice Panel

- [ ] **Task: Implement `InvoicePanel.tsx` and `Checkout.tsx`**
  - [ ] Invoice breakdown: duration, time charge, package credit (if used), discount (with reason and percentage), POS items, total, payment method selector (CASH, WALLET, CARD)
  - [ ] All amounts in Rs. using `formatPaise(paise) => "Rs. X.XX"` utility (conversion at display layer only)
  - [ ] "Confirm Payment" → `POST /api/sessions/{id}/checkout`
  - [ ] "Print Receipt" → thermal (backend handles) or PDF (opens print dialog in browser)

### Testing Requirements (Phase 3)

- [x] `pytest backend/tests/test_billing_service.py` — per-minute, flat-hourly, time-block pricing; `resolve_rate`; integer arithmetic (NFR-DATA-002)
- [x] `pytest backend/tests/test_package_drawdown.py` — full drawdown, overflow billing, partial exhaust, exhaustion status; all amounts integer arithmetic; total never negative
- [ ] `pytest backend/tests/test_promotion.py` — promotion discount, loyalty discount — _deferred to Feature 4.1_
- [x] `pytest backend/tests/test_pos_service.py`, `test_inventory_service.py`, `test_pos_router.py`, `test_inventory_router.py` — add item, stock decrement, low-stock alert, zero-stock lockout, remove item, restock, POS count 19 tests passing
- [ ] `pytest backend/tests/test_checkout.py` — full end-to-end checkout, invoice line items, audit log entry, wallet deduction, loyalty points addition, PDF endpoint returns HTML
- [ ] `pytest backend/tests/test_print.py` — mock printer; correct ESC/POS format; async non-blocking (checkout returns within 100ms with printer mock that sleeps 2s)
- [x] `pytest backend/tests/test_audit.py` — append-only log; correct timestamps, staff identity, action names; no update/delete exposed (5 tests passing)

### Documentation Requirements (Phase 3)

- [ ] `docs/api-reference.md`: billing, POS, inventory, checkout, print, and invoice endpoints
- [ ] `docs/developer-guide.md`: billing engine logic, paise convention rationale, audit log immutability

---

## Phase 4: Members, Packages, Promotions, Vouchers & Staff Auth

### Objectives

Complete member system (wallet, loyalty, tiers), time packages, promotions engine, vouchers, full staff management, peak/off-peak scheduling, and per-zone pricing.

### Deliverables

- `MemberService`: wallet, loyalty points, tier management, voucher redemption
- `PackageService`: sell entitlements, track drawdown
- `PromotionService`: evaluate applicable promotion at session start
- `VoucherService`: batch generation, redemption, expiry
- Staff management API: create, PIN change, deactivate (with `token_version` increment)
- Frontend: `Members.tsx`, `Packages.tsx`, `Settings.tsx` (feature flags, pricing, zones, schedules)

### Dependencies

- Phase 2 complete, Phase 3 complete (⚡ CHECKPOINT 3-A passed)

### Parallel Work

**ENG-A:** `MemberService`, `PackageService`, `PromotionService`, `VoucherService`, staff management API
**ENG-B:** Member search component, `Members.tsx`, `Settings.tsx`, member integration into session start flow

### ⚡ CHECKPOINT 4-A

- [ ] Member lookup integrated into session start flow
- [ ] Member with active package checks out correctly (package drawdown + overflow tested)
- [ ] Feature flag toggling in Settings UI reflects in backend (page hides; API returns 503)

---

### Epic 4.1: Member System (ENG-A)

- [ ] **Task: Implement `MemberService` (`backend/services/member_service.py`)**
  - [ ] `create_member(name, phone, db)` — phone uniqueness check; initial tier BRONZE
  - [ ] `get_member(member_id, db)` — 404 if not found
  - [ ] `search_members(query, db)` — search by name or phone (ILIKE pattern)
  - [ ] `topup_wallet(member_id, amount_paise, payment_method, db, staff)` — audit `WALLET_TOPUP`
  - [ ] `redeem_voucher_to_wallet(member_id, code, db)` — validate voucher; add value; mark redeemed; audit `VOUCHER_REDEEMED`
  - [ ] `add_loyalty_points(member_id, session_duration_seconds, db)` — calc points per configured rule; update total; check tier thresholds; upgrade if met; broadcast `member_updated`
  - [ ] Member API router: `GET /api/members?q=`, `POST /api/members`, `GET /api/members/{id}`, `POST /api/members/{id}/topup`, `GET /api/members/{id}/sessions` (history)

- [ ] **Task: Implement `PackageService` (`backend/services/package_service.py`)**
  - [ ] `sell_package(member_id, package_id, payment_method, db, staff)` — create `MemberPackageEntitlement`; deduct from wallet or record cash payment; audit `PACKAGE_SOLD`
  - [ ] `get_active_entitlement(member_id, db)` — returns active entitlement (ACTIVE status, not expired, has remaining minutes)
  - [ ] `list_packages(db)` — all available packages (Admin manages via settings API)
  - [ ] Package API: `GET /api/packages`, `POST /api/members/{id}/packages` (sell)

- [ ] **Task: Implement `PromotionService` (`backend/services/promotion_service.py`)**
  - [ ] `get_applicable_promotion(seat_id, member_id, time_now, db) -> Promotion | None`
  - [ ] Check active promotions; match time window and day of week; return first match
  - [ ] `store_promotion_id_on_session(session_id, promotion_id, db)` — locked at session start
  - [ ] Promotion API: `GET /api/promotions`, `POST /api/promotions` (Admin), `PATCH /api/promotions/{id}` (Admin)

- [ ] **Task: Implement `VoucherService` (`backend/services/voucher_service.py`)** (feature-flagged `enable_vouchers`)
  - [ ] `generate_batch(count, value_paise, expires_in_days, db, staff)` — creates `count` vouchers with unique random codes; returns batch
  - [ ] `redeem(code, member_id, db)` — validates not expired, not redeemed; credits member wallet; marks redeemed
  - [ ] Voucher API: `POST /api/vouchers/batch` (Admin), `POST /api/vouchers/redeem`

- [ ] **Task: Staff Management API**
  - [ ] `POST /api/staff` (Admin): create staff member; hash PIN with Argon2id; initial `token_version=0`
  - [ ] `PATCH /api/staff/{id}/pin` (Admin or self): update PIN; **increment `token_version`** to invalidate all existing JWTs
  - [ ] `PATCH /api/staff/{id}/deactivate` (Admin): set `is_active=False`; **increment `token_version`**
  - [ ] `GET /api/staff` (Admin): list all staff

### Epic 4.2: Frontend — Members and Settings (ENG-B)

- [ ] **Task: Implement `MemberSearch` component** — debounced search input → `GET /api/members?q=`; selects member for session start modal
- [ ] **Task: Implement `Members.tsx` page** — member list, search, create form, wallet top-up, package purchase, transaction history
- [ ] **Task: Implement `Settings.tsx` page** — feature flags toggles; pricing (zones, rates, device types); peak/off-peak schedules; staff management; menu item management; printer config
  - [ ] All feature flag toggles call `PATCH /api/settings` and invalidate cache
  - [ ] **Definition of done:** Toggle flag OFF → corresponding nav item disappears; API endpoint returns 503

### Testing Requirements (Phase 4)

- [ ] `pytest backend/tests/test_member_service.py` — create, search, wallet topup (correct paise), loyalty points calculation, tier upgrades, voucher redemption
- [ ] `pytest backend/tests/test_package_service.py` — sell package, entitlement creation, active entitlement retrieval, drawdown edge cases
- [ ] `pytest backend/tests/test_promotion_service.py` — time window matching, day-of-week matching, no promotion when inactive
- [ ] `pytest backend/tests/test_voucher_service.py` — generation, redemption, expired voucher rejection, already-redeemed rejection
- [ ] `pytest backend/tests/test_staff_auth.py` — `token_version` increment on PIN change; stale JWT rejected; deactivated account JWT rejected

### Documentation Requirements (Phase 4)

- [ ] `docs/api-reference.md`: members, packages, promotions, vouchers, staff endpoints
- [ ] `docs/operator-guide.md` stub: member management, wallet topup, package selling

---

## Phase 5: Operations & Experience

### Objectives

Shift management (open/close, cash reconciliation), seat reservations, branded agent overlay, PC health monitoring, remote commands (screenshot, message, restart, shutdown), Tuya console control, announcement broadcasts, nightly backup scheduler, and log rotation.

### Deliverables

- `ShiftService`: open, close, cash reconciliation
- `ReservationService`: create, confirm, cancel, auto-session trigger
- `HealthService`: aggregate health metrics from agent HEALTH messages
- `RemoteCommandService`: screenshot (rate-limited), message, restart, shutdown, Tuya plug
- `BackupService`: APScheduler nightly SQLite backup with retention
- Branded agent overlay with menu and "Call Staff" button
- Frontend: `Shifts.tsx`, `Reservations.tsx`, `PCHealth.tsx`, `RemoteCommands.tsx`

### Dependencies

- Phase 2, 3, 4 complete

### Parallel Work

**ENG-A:** `ShiftService`, `ReservationService`, `HealthService`, `RemoteCommandService`, `BackupService`, Tuya integration
**ENG-B:** Shift UI, Reservation UI, PC health dashboard, remote command panel, agent overlay enhancements

### ⚡ CHECKPOINT 5-A

- [ ] Shift open → sessions run → shift close; reconciliation figures correct (AC-10)
- [ ] Reservation created → appears on dashboard with customer name and time slot
- [ ] Screenshot requested → arrives in dashboard within 3 seconds (AC-18)
- [ ] Nightly backup creates correctly named file; old files are pruned

---

### Epic 5.1: Shift Management (ENG-A)

- [ ] **Task: Implement `ShiftService`**
  - [ ] `open_shift(staff_id, opening_cash, db)`: validate no shift already open; create `Shift` record; audit `SHIFT_OPEN`
  - [ ] `close_shift(staff_id, closing_cash, db)`: validate open shift exists; calculate `expected_cash = opening_cash + cash_collected_this_shift`; set `closed_at`; audit `SHIFT_CLOSE`
  - [ ] `get_current_shift(db)`: returns open shift or None
  - [ ] `get_shift_report(shift_id, db)`: sessions during shift, revenue, POS totals, cash reconciliation
  - [ ] All sessions created during a shift have `shift_id` set (set in `session_service.start_session()`)
  - [ ] Shift API: `POST /api/shifts/open`, `POST /api/shifts/close`, `GET /api/shifts/current`, `GET /api/shifts/{id}/report`
  - [ ] **Definition of done:** AC-10 satisfied — shift closed with correct reconciliation figures

### Epic 5.2: Reservations (ENG-A)

- [ ] **Task: Implement `ReservationService`** (feature-flagged `enable_reservations`)
  - [ ] `create_reservation(seat_id, member_id, customer_name, from, to, notes, db, staff)`: validate seat not already reserved in time window; create record; audit `RESERVATION_CREATED`
  - [ ] `confirm_reservation(reservation_id, db, staff)`: set `status=CONFIRMED`
  - [ ] `cancel_reservation(reservation_id, db, staff)`: set `status=CANCELLED`; audit `RESERVATION_CANCELLED`
  - [ ] Scheduled check (APScheduler, every 1 minute): find reservations starting in the next 0–2 minutes; set seat `status=RESERVED`; broadcast seat update
  - [ ] Reservation API: `GET /api/reservations`, `POST /api/reservations`, `PATCH /api/reservations/{id}`, `DELETE /api/reservations/{id}`

### Epic 5.3: Remote Commands and PC Health (ENG-A)

- [ ] **Task: Implement `RemoteCommandService`**
  - [ ] `send_message(seat_id, message, db, staff)`: send `SHOW_MESSAGE` to agent; audit `MESSAGE_SENT`
  - [ ] `request_screenshot(seat_id, db, staff)`: check no in-flight screenshot for this seat (rate limit: 1 in-flight per seat); generate `request_id`; send `TAKE_SCREENSHOT`; await `SCREENSHOT_RESPONSE`; return JPEG bytes (AC-18)
  - [ ] `restart_seat(seat_id, db, staff)`: send `RESTART`; audit `SEAT_RESTARTED` (AC-06)
  - [ ] `shutdown_seat(seat_id, db, staff)`: send `SHUTDOWN`; audit `SEAT_SHUTDOWN`
  - [ ] Remote commands API: `POST /api/seats/{id}/message`, `GET /api/seats/{id}/screenshot`, `POST /api/seats/{id}/restart`, `POST /api/seats/{id}/shutdown`
  - [ ] **⚠ RISK:** Screenshot rate-limiting must be enforced at service level, not just route level — in-memory lock per seat_id

- [ ] **Task: Implement Tuya console control** (feature-gated, config-driven)
  - [ ] `TuyaService`: `power_on(seat_id, db)`, `power_off(seat_id, db)` using `tinytuya.Device` with LAN API (no internet at runtime)
  - [ ] Called from `session_service.start_session()` (if seat has tuya_device) and `billing_service.checkout()` (power off after checkout)
  - [ ] Test with mock: if `tuya_devices` list empty, skip silently
  - [ ] API: `POST /api/seats/{id}/power-on`, `POST /api/seats/{id}/power-off` (Admin)

### Epic 5.4: Nightly Backup (ENG-A)

- [ ] **Task: Implement `BackupService` with APScheduler**
  - [ ] `BackupService.run_backup()`: copy `arcade.db` to `{backup_dir}/arcade_{YYYYMMDD_HHMM}.db`; verify copy integrity (file size comparison)
  - [ ] `BackupService.prune_old_backups()`: delete files older than `backup_retain_days` (default 30)
  - [ ] Schedule via `AsyncIOScheduler`: `cron` trigger at `backup_time` from config (default 03:00)
  - [ ] Scheduler started in FastAPI `lifespan` startup; shut down in `lifespan` shutdown
  - [ ] `POST /api/backup/run` (Admin): trigger manual backup
  - [ ] Backup log in audit table: `BACKUP_CREATED`, `BACKUP_PRUNED`
  - [ ] **Definition of done:** AC-20 — backup runs at configured time; old files are pruned; manual trigger works

### Epic 5.5: Agent Overlay Enhancements (ENG-B)

- [ ] **Task: Enhance agent kiosk overlay with branded content**
  - [ ] Read cafe name from `agent.config.json` (add `cafe_name` field — or fetch from server on REGISTER)
  - [ ] Overlay: cafe name/logo, current time (large), "Session in progress" ticker, "Call Staff" button (sends `STAFF_ALERT` to server)
  - [ ] Low-time warning: modal overlay with countdown "5 minutes remaining — please see staff"
  - [ ] Staff message popup: display `SHOW_MESSAGE` content for 30 seconds, then auto-dismiss

### Testing Requirements (Phase 5)

- [ ] `pytest backend/tests/test_shift_service.py` — open/close, reconciliation calculations, duplicate open rejection
- [ ] `pytest backend/tests/test_reservation_service.py` — create, time conflict detection, scheduled seat status change, cancel
- [ ] `pytest backend/tests/test_remote_commands.py` — screenshot rate limiting, screenshot response payload validation, restart/shutdown audit log, Tuya mock
- [ ] `pytest backend/tests/test_backup.py` — backup file created with correct name, integrity check, pruning of old files, manual trigger

### Documentation Requirements (Phase 5)

- [ ] `docs/api-reference.md`: shifts, reservations, remote commands, Tuya, backup endpoints
- [ ] `docs/operator-guide.md`: shift open/close procedure, how to handle frozen PC, reservations workflow
- [ ] `docs/deployment.md`: Tuya smart plug pairing (one-time internet required), printer setup

---

## Phase 6: Analytics & Events

### Objectives

Owner-facing analytics dashboard with Recharts visualizations, tournament/event mode with bracket management, maintenance mode downtime tracking, feature flag finalisation, and mobile responsiveness.

### Deliverables

- `AnalyticsService`: all summary queries (< 2 seconds on 1-year dataset)
- `EventService`: create, register participants, record match results, bracket advancement
- Frontend: `Analytics.tsx` (Recharts charts), `Events.tsx` (bracket view)
- Mobile responsiveness on all pages (375px tested)
- All 10 feature flags verified end-to-end

### Dependencies

- Phases 2–5 complete

### ⚡ CHECKPOINT 6-A

- [ ] Analytics summary query completes in < 2 seconds on seeded 1-year dataset
- [ ] All 10 feature flags tested: toggle OFF → nav disappears, page 404s, API returns 503 (AC-08)
- [ ] Dashboard usable at 375px (iPhone SE width) — owner can check revenue from phone (AC-05)

---

### Epic 6.1: Analytics Service (ENG-A)

- [ ] **Task: Implement `AnalyticsService` (`backend/services/analytics_service.py`)**
  - [ ] All queries run against local SQLite only (FR-ANALYTICS-002) — no external service:
    - Today's revenue: `SUM(invoices.total_paise) WHERE DATE(created_at) = today`
    - Session count and average duration today
    - Busiest hour (group by hour, find peak)
    - Weekly revenue trend (last 7 days daily totals)
    - Top POS items by quantity sold
    - Seat utilisation by zone (session hours / available hours)
    - Member stats: new today, active last 30 days, top 5 by spend
    - Active health alerts: seats with CPU temp in red zone or no health report in > 5 minutes
    - Upcoming reservations today
    - WoL success rate per seat
  - [ ] `GET /api/analytics/summary` (Admin)
  - [ ] **Pass criteria:** All queries complete in < 2 seconds on 365-day seeded dataset (NFR-PERF-002)

### Epic 6.2: Events / Tournament Service (ENG-A)

- [ ] **Task: Implement `EventService`** (feature-flagged `enable_tournaments`)
  - [ ] `create_event(name, game, date, entry_fee_paise, prize_pool_paise, bracket_type, db, staff)`
  - [ ] `register_participant(event_id, member_id, seat_id, db, staff)`: deduct entry fee; create `EventParticipant`
  - [ ] `record_match_result(match_id, winner_id, db, staff)`: advance winner in bracket; move loser to losers' bracket (double elimination) or eliminate (single elimination)
  - [ ] `get_event_summary(event_id, db)`: participants, results, prize pool, entry fee revenue
  - [ ] Event API: `GET /api/events`, `POST /api/events`, `POST /api/events/{id}/register`, `PATCH /api/events/{id}/match`, `GET /api/events/{id}/summary`

### Epic 6.3: Frontend — Analytics and Events (ENG-B)

- [ ] **Task: Implement `Analytics.tsx` with Recharts**
  - [ ] KPI cards row: today's revenue, session count, avg duration, busiest hour
  - [ ] Weekly revenue: `BarChart`
  - [ ] Seat utilisation: grouped `BarChart` or `RadarChart`
  - [ ] Top POS items: horizontal `BarChart`
  - [ ] Member registration trend: `LineChart`
  - [ ] Health alerts: warning cards for overheating/offline seats
  - [ ] Mobile-responsive: all charts stack vertically at 375px (FR-MOB-001, FR-MOB-002, AC-05)

- [ ] **Task: Implement `Events.tsx`**
  - [ ] Event list and create form (feature-flagged)
  - [ ] Bracket view: single/double elimination; winners highlighted; match result entry
  - [ ] Event summary panel (revenue, prize pool)

- [ ] **Task: Feature flag UI finalisation** — audit all pages for flag compliance; test all 10 flags (AC-08)
- [ ] **Task: Mobile responsiveness pass** — test at 375px, 390px, 412px, 768px; fix any overflow or tap target issues (AC-05)

### Testing Requirements (Phase 6)

- [ ] `pytest backend/tests/test_analytics.py` — all summary fields correct with seeded 30-day dataset; performance < 2 seconds
- [ ] `pytest backend/tests/test_events.py` — create, register, match results, single/double elimination advancement, entry fee deduction
- [ ] Frontend: feature flag snapshot tests (all ON, all OFF, each individually toggled)
- [ ] **Manual mobile test:** Open dashboard on Android/iOS at 375px — verify revenue visible, session status visible, no horizontal overflow

### Documentation Requirements (Phase 6)

- [ ] `docs/api-reference.md`: analytics and events endpoints
- [ ] `docs/deployment.md`: feature flag reference table (flag, default, scope, recommended setting)

---

## Phase 7: Cross-Platform Agent Polish (macOS & Linux)

### Objectives

Complete the platform abstraction for macOS and Linux. Package the agent for all three OSes. Verify kiosk hardening on all platforms. Handle platform-specific permissions.

### Deliverables

- `macos.ts` and `linux.ts` fully implemented
- Agent builds: Windows `.exe`, macOS `.dmg`, Linux AppImage + `.deb`
- Auto-start: Windows startup folder, macOS LaunchAgent, Linux systemd / `.desktop`
- Kiosk hardening verified on all 3 platforms
- Launcher cross-platform testing complete

### Dependencies

- Phase 2: Windows agent implementation complete and tested

### Parallel Work

**ENG-A:** macOS platform implementation and `.dmg` packaging, Launcher cross-platform testing
**ENG-B:** Linux platform implementation and AppImage/`.deb` packaging

---

### Epic 7.1: macOS Platform Implementation (ENG-A)

- [ ] **Task: Implement `macos.ts`**
  - [ ] `showKioskOverlay()` / `hideKioskOverlay()`: `win.setKiosk(true/false)` (kiosk mode works on macOS)
  - [ ] `restartPC()`: `exec('osascript -e \'tell application "Finder" to restart\'')` or `exec('sudo shutdown -r now')` — document sudo requirement
  - [ ] `shutdownPC()`: `exec('sudo shutdown -h now')`
  - [ ] `captureScreenshot()`: `desktopCapturer.getSources({types: ['screen']})` — **requires Screen Recording permission**; handle `undefined` source gracefully; log warning if permission not granted
  - [ ] `enableAutoStart()` / `disableAutoStart()`: write/delete LaunchAgent plist at `~/Library/LaunchAgents/com.arcade.agent.plist`
  - [ ] Intercept macOS-specific shortcuts: `Cmd+Q`, `Cmd+W`, `Cmd+H`, `Cmd+M` → no-op in kiosk mode

- [ ] **Task: Create macOS build configuration**
  - [ ] `electron-builder.yml`: `mac.target = ["dmg", "zip"]`; set `appId`, `bundleId`
  - [ ] Document unsigned distribution workaround (Gatekeeper bypass for unsigned `.dmg`)
  - [ ] Test build on macOS: `npm run build -- --mac`

### Epic 7.2: Linux Platform Implementation (ENG-B)

- [ ] **Task: Implement `linux.ts`**
  - [ ] `showKioskOverlay()` / `hideKioskOverlay()`: `win.setKiosk(true/false)`; on Wayland, add fallback: maximise + `setAlwaysOnTop(true, 'screen-saver')` (FR-AGENT-002b)
  - [ ] `restartPC()`: `exec('systemctl reboot')`
  - [ ] `shutdownPC()`: `exec('systemctl poweroff')`
  - [ ] `captureScreenshot()`: `desktopCapturer` (X11 works natively; Wayland requires workaround — handle gracefully if unavailable)
  - [ ] `enableAutoStart()`: write `~/.config/autostart/arcade-agent.desktop`
  - [ ] `disableAutoStart()`: delete the `.desktop` file

- [ ] **Task: Create Linux build configuration**
  - [ ] `electron-builder.yml`: `linux.target = ["AppImage", "deb"]`; `linux.category = "Utility"`
  - [ ] Test build: `npm run build -- --linux`
  - [ ] Create `docs/autostart/arcade-agent.service` (systemd) and `arcade-agent.desktop` (autostart)

### Epic 7.3: Cross-Platform Kiosk Hardening Verification

- [ ] **Windows kiosk hardening verification** (ENG-A or ENG-B):
  - [ ] Alt+F4 → no action ✓
  - [ ] Ctrl+P → no print dialog ✓
  - [ ] F12 → no DevTools ✓
  - [ ] Ctrl+Shift+I → no DevTools ✓
  - [ ] Alt+Shift+I → no DevTools ✓ (Electron-specific)
  - [ ] Task Manager (Ctrl+Shift+Esc) → **cannot block at app level** — document this limitation
  - [ ] Ctrl+Alt+Del → **cannot block** — document this limitation
  - [ ] **Document all known gaps in `docs/agent-setup.md`**

- [ ] **macOS kiosk hardening verification** (ENG-A): Cmd+Q, Cmd+Tab, Cmd+Space blocked; Force Quit (Cmd+Opt+Esc) — document if not blockable
- [ ] **Linux kiosk hardening verification** (ENG-B): X11 all shortcuts blocked; Wayland fallback verified; known gaps documented

### Epic 7.4: Launcher Cross-Platform Testing (ENG-A)

- [ ] Test `launcher.py` on macOS: document `brew install python-tk@3.11` prerequisite
- [ ] Test on Ubuntu 22.04: document `sudo apt-get install python3-tk` prerequisite
- [ ] Verify subprocess spawning of uvicorn works on all 3 OSes
- [ ] **Definition of done:** AC-15 — Launcher runs without errors on all three OSes

### Acceptance Criteria (Phase 7)

- [ ] Agent kiosk overlay works on Windows, macOS, Linux (AC-13)
- [ ] Remote restart and shutdown work on all three platforms (AC-14)
- [ ] Agent distributables build on all three OSes (NFR-PORT-002)
- [ ] Launcher runs on all three OSes (AC-15)
- [ ] Kiosk bypass attempts (Alt+F4, Cmd+Q, F12, Ctrl+P) blocked on all platforms (AC-17)
- [ ] Known limitations (Ctrl+Alt+Del on Windows, Wayland compositor) documented

### Testing Requirements (Phase 7)

- [ ] Manual testing checklist executed on at least one machine of each OS
- [ ] Screenshot capture tested on all 3 OSes (macOS Screen Recording permission flow documented)
- [ ] Restart/shutdown tested on all 3 OSes (use VM to avoid disrupting dev machines)
- [ ] Auto-start verified on all 3 OSes

### Documentation Requirements (Phase 7)

- [ ] `docs/agent-setup.md`: complete per-OS installation (Windows, macOS, Linux), file permissions, auto-start, known limitations table
- [ ] `docs/deployment.md`: Launcher setup on macOS and Linux including Tkinter prerequisite

---

## Phase 8: Testing & Quality Assurance

### Objectives

Comprehensive automated test coverage, end-to-end testing of all 23 SRS acceptance criteria, load testing with 50 concurrent WebSocket connections, and a production-ready CI pipeline.

### Deliverables

- Backend unit test coverage ≥ 80% on all service and repository files
- Integration test suite covering all 23 SRS acceptance criteria
- Performance test: 50 concurrent WebSocket connections without degradation
- CI pipeline: lint → test → coverage report → dependency audit — runs on every PR

### Dependencies

- Phases 2–7 complete (or concurrent with Phase 7 for final validation)

### Parallel Work

**ENG-A:** Backend integration and performance tests, CI pipeline
**ENG-B:** Frontend component tests, cross-browser testing

### ⚡ CHECKPOINT 8-END (Production Readiness Gate)

- [ ] All 23 SRS acceptance criteria have an automated test or documented manual test result
- [ ] Backend test coverage ≥ 80%
- [ ] CI pipeline passes on all PRs
- [ ] 50-concurrent-WebSocket performance test passes (NFR-PERF-003)
- [ ] No P0 or P1 bugs outstanding
- [ ] `pip-audit` and `npm audit` report no HIGH or CRITICAL CVEs

---

### Epic 8.1: Backend Testing (ENG-A)

#### Feature 8.1.1: Integration Test Suite — All 23 Acceptance Criteria

- [ ] **Task: Write integration tests for all SRS acceptance criteria** (`backend/tests/test_acceptance.py`)
  - [ ] AC-01: WebSocket seat status update delivered < 1 second after service call
  - [ ] AC-02: Session start API responds < 2 seconds; checkout API responds < 10 seconds
  - [ ] AC-03: Checkout with time charge, package usage, POS items, receipt fields all correct
  - [ ] AC-04: WoL packets sent on startup (mock socket; verify packet structure)
  - [ ] AC-05: Analytics endpoint returns revenue summary (validate all fields present)
  - [ ] AC-06: Remote restart command delivered to agent via WebSocket mock
  - [ ] AC-07: Session data preserved through simulated agent disconnect (30s) + reconnect + SYNC
  - [ ] AC-08: All 10 feature flags gate their endpoints (503 when off) and UI sections
  - [ ] AC-09: Audit log records all events with correct fields, immutable (no delete endpoint)
  - [ ] AC-10: Shift open/close with correct reconciliation figures
  - [ ] AC-11: Package drawdown + per-minute overflow billing (2hr package, 2.5hr session)
  - [ ] AC-12: License verification blocks setup when license invalid or missing
  - [ ] AC-13: Agent kiosk overlay shows and hides correctly (manual on each OS)
  - [ ] AC-14: Remote restart/shutdown commands work (manual on each OS)
  - [ ] AC-15: Launcher runs on all three OSes (manual)
  - [ ] AC-16: TinyTuya local command sent on console session start/end (mock TinyTuya device)
  - [ ] AC-17: Kiosk hardening — bypass attempts blocked (manual checklist per OS)
  - [ ] AC-18: Screenshot payload ≤ 5 MB, rate-limited to 1 in-flight per seat
  - [ ] AC-19: Lifespan context manager — no `@app.on_event` deprecation warnings in server logs
  - [ ] AC-20: Backup scheduler runs at configured time; files older than retention period pruned
  - [ ] AC-21: Agent with wrong secret rejected by WebSocket server (connection closed immediately)
  - [ ] AC-22: Active sessions preserved through server restart (verify via DB state, not just API)
  - [ ] AC-23: Launcher confirmation dialog shown when closing with server running (manual)
  - [ ] **Test infrastructure:** Use `pytest-asyncio` + `httpx.AsyncClient` + in-memory SQLite for all backend integration tests; never use production DB in CI

#### Feature 8.1.2: Load and Performance Tests

- [ ] **Task: 50 concurrent WebSocket connections performance test**
  - [ ] Use `locust` with `websockets` library or `pytest-benchmark`
  - [ ] Simulate 50 agents: each connects, sends HEALTH messages every 60 seconds
  - [ ] Simulate 3 dashboard clients receiving seat broadcasts
  - [ ] Measure CPU usage, message delivery latency, memory usage
  - [ ] **Pass criteria:** No messages dropped; broadcast latency < 1 second; server CPU < 80% (NFR-PERF-001, NFR-PERF-003)
  - [ ] Add seeded dataset test: `backend/scripts/seed_year_data.py` — seeds 365 days × 100 sessions/day; run analytics queries; verify all complete < 2 seconds

#### Feature 8.1.3: CI Pipeline (GitHub Actions)

- [ ] **Task: Finalise GitHub Actions CI workflow** (`.github/workflows/ci.yml`)
  - [ ] Job: `lint-python` — `ruff check backend/`, `black --check backend/`, `mypy backend/`
  - [ ] Job: `security-scan` — `bandit -r backend/`, `pip-audit -r backend/requirements.txt`
  - [ ] Job: `test-backend` — `pytest --cov=backend --cov-report=xml --cov-fail-under=80`
  - [ ] Job: `lint-frontend` — `npm run lint` in `frontend/`
  - [ ] Job: `test-frontend` — `npm test` in `frontend/`
  - [ ] Job: `lint-agent` — `npm run lint` in `agent/`
  - [ ] Job: `dep-audit-frontend` — `npm audit --audit-level=high` in `frontend/` and `agent/`
  - [ ] Job: `check-secrets` — `git-secrets` or grep for `private_key`, `*.pem` in staged files
  - [ ] All jobs must pass before PR can merge to `main`
  - [ ] Coverage report uploaded to Codecov or published as GitHub Actions artifact
  - [ ] Pip cache and npm cache configured for speed
  - [ ] **Note:** Add Windows runner for native Windows tests: `runs-on: windows-latest` for the agent job

---

### Epic 8.2: Frontend and E2E Testing (ENG-B)

- [ ] **Task: Write component tests** (Vitest + React Testing Library) (`frontend/src/tests/`)
  - [ ] `SeatGrid.test.tsx` — renders correct count; status colour-coding
  - [ ] `SeatCard.test.tsx` — status badge, elapsed timer ticking, click triggers modal
  - [ ] `InvoicePanel.test.tsx` — paise→rupees display; all line items present
  - [ ] `POSPanel.test.tsx` — greyed-out when `is_available=false`; click calls API
  - [ ] `MemberSearch.test.tsx` — debounced search; member card renders
  - [ ] `Login.test.tsx` — wrong PIN shows error; 5th failure shows lockout; success stores token
  - [x] `useWebSocket.test.tsx` — reconnect behaviour; `seat_updated` invalidates cache — **9 tests in 4 test files passing**

- [ ] **Task: Cross-browser compatibility testing** (manual)
  - [ ] Chrome (latest), Firefox (latest), Safari (macOS/iOS) — all pages render
  - [ ] Mobile Chrome + Safari at 375px — AC-05 satisfied
  - [ ] Document any browser-specific workarounds

### Documentation Requirements (Phase 8)

- [ ] `docs/developer-guide.md`: how to run tests, performance tests, acceptance criteria checklist

---

## Phase 9: Security Hardening

### Objectives

Systematic security review of all attack surfaces. Ensure all NFR-SEC requirements are satisfied. Implement Staff Override feature. Threat model documentation.

### Deliverables

- Security review checklist completed for all NFR-SEC-001 through NFR-SEC-008
- `docs/security/auth-audit.md` — endpoint auth audit table (all 40+ routes verified)
- `docs/security/threat-model.md` — threats, mitigations, accepted risks
- Staff Override feature complete (optional feature, agent-side local bypass)
- No HIGH or CRITICAL CVEs in Python or Node.js dependencies

---

### Epic 9.1: Security Review (ENG-A)

- [ ] **Authentication and authorisation audit:**
  - [ ] Review every route: correct `require_admin` or `require_cashier` dependency?
  - [ ] `token_version` validation in `get_current_staff()` — test stale token rejection
  - [ ] Screenshot endpoint Admin-only (NFR-SEC-004)
  - [ ] Audit log has no DELETE or UPDATE endpoints (NFR-SEC-005)
  - [ ] No user or billing data in `/health` or any public endpoint (NFR-SEC-006)
  - [ ] **Output:** `docs/security/auth-audit.md` — table of all routes with auth level and verified checkbox

- [ ] **Argon2id implementation audit:**
  - [ ] `grep -r "bcrypt" backend/` → must return nothing
  - [ ] No plaintext PINs in any logging calls
  - [ ] `arcade.config.json` stores only hashed PINs
  - [ ] Argon2id params: `time_cost=2, memory_cost=102400, parallelism=8` — OWASP compliant

- [ ] **Agent and WebSocket security audit:**
  - [ ] `agent_secret` not hardcoded in source: `grep -r "agent_secret" agent/src/ backend/` — only appears as config read
  - [ ] `agent.config.json` in `.gitignore`; never committed
  - [ ] Max WebSocket message size 5 MB enforced; test with > 5 MB payload → connection closed
  - [ ] Screenshot payloads are JPEG-only (not PNG)

- [ ] **Input validation audit:**
  - [ ] All string fields have `max_length` in Pydantic schemas
  - [ ] All monetary fields are `int` (no `float` anywhere in schemas)
  - [ ] All queries go through SQLAlchemy ORM — no raw SQL with user input (SQL injection prevention)
  - [ ] `audit_repo.py` exposes only `create` and `list` — no `update` or `delete`

- [ ] **Sensitive file and key security:**
  - [ ] Confirm `tools/keygen/private_key.pem` never committed: `git log --all --full-history -- tools/keygen/private_key.pem` → empty
  - [ ] CI check added: fail build if any `*.pem` or `private_key*` file detected in repo
  - [ ] `arcade.config.json` and `license.key` in `.gitignore`
  - [ ] Document key custody policy in `docs/security/key-management.md`

### Epic 9.2: Dependency Vulnerability Audit (ENG-B)

- [ ] Python: `pip-audit -r backend/requirements.txt` — fix any HIGH or CRITICAL
- [ ] Node.js: `npm audit --audit-level=high` in `frontend/` and `agent/` — fix any HIGH or CRITICAL
- [ ] Add both to CI pipeline (already in Feature 8.1.3 — verify these pass)
- [ ] **⚠ RISK (R-09):** Review Chromium/Electron CVEs specifically — Electron bundles a specific Chromium version; update if necessary

### Epic 9.3: Staff Override Feature

- [ ] **Task: Add `override_code_hash` to `agent.config.json` schema** (ENG-A)
  - [ ] Nullable Argon2id PHC hash; absent/null = feature disabled (no trigger, no dialog)
  - [ ] Extend Launcher setup wizard with Step 5b — Override Code field (blank = disabled)
  - [ ] Hash with same Argon2id parameters as PINs

- [ ] **Task: Agent-side override flow** (ENG-B)
  - [ ] Configured key combination (e.g., `Ctrl+Shift+O`) shows PIN entry dialog — only if `override_code_hash` set
  - [ ] On correct code: `hideKioskOverlay()` locally; set `override_active=true`; send `STAFF_OVERRIDE` event to server
  - [ ] While `override_active`: suppress `SHOW_OVERLAY` commands from server; log `SHOW_OVERLAY_SUPPRESSED_BY_OVERRIDE`
  - [ ] Queue `STAFF_OVERRIDE` event if server offline; flush on reconnect
  - [ ] Handle optional `RESET_OVERRIDE` command from server to clear flag remotely

- [ ] **Task: Backend audit trail for override** (ENG-A)
  - [ ] `STAFF_OVERRIDE` case in `ws_manager.py` → `audit_service.log()` with `staff_id=None`
  - [ ] Optional: `POST /api/seats/{id}/reset-override` (Admin) sends `RESET_OVERRIDE` to agent

### Acceptance Criteria (Phase 9)

- [ ] All NFR-SEC-001 through NFR-SEC-008 verified and checked off
- [ ] No HIGH/CRITICAL CVEs in Python or Node.js dependencies
- [ ] Private key never in git history
- [ ] Rate limiting verified under simulated brute-force (5 attempts → lockout)
- [ ] All endpoints have correct auth per audit table
- [ ] Override: inert when `override_code_hash` absent; correct code hides overlay; wrong code no-op; audit event logged

---

## Phase 10: Performance Optimisation

### Objectives

Resolve performance bottlenecks found during Phase 8 load testing. Add database indexes. Optimise frontend bundle. Confirm all NFR-PERF requirements met.

### Deliverables

- Alembic migration `002_add_indexes.py` with all critical indexes
- Analytics queries verified < 500ms on 365-day dataset
- Frontend initial load < 3 seconds on local network (NFR-PERF-005)
- All NFR-PERF-001 through NFR-PERF-005 verified

---

### Epic 10.1: Database Performance (ENG-A)

- [ ] **Task: Add indexes** (`alembic/versions/002_add_indexes.py`):
  - `sessions`: `(seat_id, status)`, `(status, started_at)`, `(shift_id)`, `(created_at)`
  - `members`: `(phone)` unique
  - `session_pos_items`: `(session_id)`
  - `audit_log`: `(created_at, action)`
  - `vouchers`: `(code)` unique
  - `member_package_entitlements`: `(member_id, status)`
  - `reservations`: `(seat_id, reserved_from)`
  - `invoices`: `(created_at)`
  - `staff`: `(staff_id)` unique (if not primary key)

- [ ] **Task: Query plan analysis** — `EXPLAIN QUERY PLAN` on each analytics query; fix any full-table scans; `backend/tests/test_query_performance.py` asserts each query < 500ms on seeded 1-year dataset

- [ ] **Task: Seed 1-year data** — `backend/scripts/seed_year_data.py` — 365 days, ~100 sessions/day, 5 POS items/session, 200 members, varied pricing

### Epic 10.2: Frontend Performance (ENG-B)

- [ ] **Task: Code splitting and lazy loading**
  - [ ] `React.lazy()` + `Suspense` for all pages except `Dashboard` and `Login`
  - [ ] Vite `rollupOptions.manualChunks`: separate chunks for recharts, react-query, zustand
  - [ ] Target: initial bundle < 500KB gzipped
  - [ ] Use `vite-bundle-analyzer` to inspect chunk sizes

### Acceptance Criteria (Phase 10)

- [ ] NFR-PERF-001: Seat status changes < 1 second
- [ ] NFR-PERF-002: Session start and checkout < 10 seconds user interaction
- [ ] NFR-PERF-003: 50 concurrent WebSocket connections without degradation
- [ ] NFR-PERF-004: Health metrics collection < 2% CPU overhead on client PC
- [ ] NFR-PERF-005: Dashboard initial load < 3 seconds on local network

---

## Phase 11: Deployment & Packaging

### Objectives

Package the system for customer distribution. Server as standalone executable (no Python required). Agent as platform-specific distributables. Complete first-run deployment checklist.

### Deliverables

- `arcade.spec` PyInstaller spec; bundled executable for all three OSes
- Agent distributables: Windows `.exe` (NSIS), macOS `.dmg`, Linux AppImage + `.deb`
- Deployment documentation complete and customer-ready
- GitHub Release `v1.0.0` with all artifacts

---

### Epic 11.1: Server Packaging (ENG-A)

- [ ] **Task: Create PyInstaller spec file (`arcade.spec`)**
  - [ ] Entry point: `launcher.py`
  - [ ] Include: `backend/` module, `frontend/dist/` (pre-built), `alembic/` scripts, `backend/alembic.ini`
  - [ ] Hidden imports: `aiosqlite`, `sqlalchemy.dialects.sqlite`, `alembic`, `nacl`
  - [ ] Data files: `frontend/dist/*` → `frontend/dist/`
  - [ ] Exclude: `tools/`, `*.pem`, `*.key`, `venv/`, `backend/tests/`, `*.spec` output
  - [ ] Use `--onedir` mode (not `--onefile`) for faster startup and easier crash debugging
  - [ ] Wrap `onedir` output in an NSIS installer for Windows (single installer `.exe` for end user)
  - [ ] **⚠ RISK (R-04):** Test on a fresh Windows VM with no Python installed — must reach License Activation screen (NFR-PORT-003, AC per ARCH-03)

- [ ] **Task: Build pipeline for all OSes**
  - [ ] Windows: build on `windows-latest` GitHub Actions runner or dedicated Windows machine
  - [ ] macOS: build on `macos-latest` GitHub Actions runner or dedicated Mac
  - [ ] Linux: build on `ubuntu-latest` GitHub Actions runner — verify GLIBC version matches deployment target (Ubuntu 20.04 min)
  - [ ] All builds: verify `alembic upgrade head` runs in bundled context; Tkinter renders; license screen appears

- [ ] **Task: Build frontend static files for embedding**
  - [ ] `npm run build` in `frontend/` → `frontend/dist/`
  - [ ] FastAPI serves `frontend/dist/index.html` at `/` in packaged build
  - [ ] Verify all API calls from bundled React app reach FastAPI backend

### Epic 11.2: Agent Packaging (ENG-B)

- [ ] **Task: Finalise `electron-builder.yml`**
  - [ ] Windows: NSIS installer, target `x64`; `nsis.oneClick: false` (allow user to choose install path)
  - [ ] macOS: `dmg` + `zip`; `mac.category = "public.app-category.utilities"`
  - [ ] Linux: `AppImage`, `deb`; `linux.category = "Utility"`
  - [ ] `productName: "Arcade Agent"`, `copyright: "Neurotech Biratnagar"`
  - [ ] Create `agent/assets/icon.png` (256×256 placeholder; replace with cafe branding before release)
  - [ ] Verify installer sets `chmod 600 agent.config.json` on Linux/macOS post-install

### Acceptance Criteria (Phase 11)

- [ ] Customer can run `arcade-windows.exe` on fresh Windows machine without Python (NFR-PORT-003)
- [ ] Agent installs on Windows, macOS, Linux from distributables (NFR-PORT-002)
- [ ] First-run checklist in `docs/deployment.md` covers all SDD §15.4 items
- [ ] License activation flow works from packaged binary

---

## Phase 12: Documentation Finalisation

### Objectives

All documentation complete, accurate, and customer-ready. Every `TODO` placeholder replaced with real content. OpenAPI spec exported.

### Deliverables

- `README.md` fully updated
- `docs/api-reference.md` complete with all 40+ endpoints and examples
- `docs/architecture.md` final system diagram
- `docs/developer-guide.md` complete
- `docs/deployment.md` customer-ready (server + agent, all 3 OSes)
- `docs/agent-setup.md` per-OS quick-start guide
- `docs/operator-guide.md` for counter staff and cafe owner
- `docs/security/` complete
- OpenAPI spec exported: `docs/openapi.json`

---

### Epic 12.1: Documentation Tasks

- [ ] **Export OpenAPI spec** (ENG-A): `curl http://localhost:8000/openapi.json > docs/openapi.json`; verify all endpoints documented with correct auth, schemas, and error responses

- [ ] **Finalise all docs/** (ENG-A + ENG-B split):
  - [ ] Replace every `TODO` placeholder in `docs/*.md`
  - [ ] Cross-check `docs/api-reference.md` vs actual implemented routes
  - [ ] Verify `docs/deployment.md` works on a fresh machine (follow it step by step)
  - [ ] Update `README.md` Build Phases table to reflect actual implementation status

- [ ] **Write `docs/operator-guide.md`** (ENG-B — non-technical language, no assumptions):
  - [ ] How to open and close a shift
  - [ ] How to start and end sessions (step by step with screenshots)
  - [ ] How to add food/drink items
  - [ ] How to handle a member checkout
  - [ ] How to restart a frozen PC from the dashboard
  - [ ] What to do if the LAN goes down
  - [ ] How to run the nightly backup manually
  - [ ] How to add a new staff member
  - [ ] Troubleshooting common issues

### Acceptance Criteria (Phase 12)

- [ ] No `TODO` placeholders remain in any `.md` file
- [ ] OpenAPI spec is accurate and exported from running server
- [ ] New developer can follow `docs/developer-guide.md` and have working environment in 30 minutes
- [ ] Cafe owner can follow `docs/operator-guide.md` without technical support

---

## Phase 13: Production Release

### Objectives

Final pre-release validation, production build, license delivery process, and monitored first-customer deployment.

### Deliverables

- All 23 SRS acceptance criteria verified in a real deployment
- Production build artifacts attached to GitHub Release `v1.0.0`
- License delivered to first customer
- First deployment monitored 48 hours
- Post-launch bug process established

---

### Epic 13.1: Pre-Release Checklist

- [ ] **Final acceptance criteria verification** (ENG-A): go through all 23 AC one by one; mark each as VERIFIED or DEFERRED (with justification); **all must be VERIFIED before release**; output: `docs/release/v1.0-acceptance-results.md`

- [ ] **Version number consistency**: set identical version in `frontend/package.json`, `agent/package.json`, `launcher.py`, `backend/main.py` → `1.0.0`

- [ ] **Build all production artifacts** (ENG-A + ENG-B): clean build on each OS; no dev dependencies bundled; verify version is correct

- [ ] **Create GitHub Release `v1.0.0`**: attach artifacts (`arcade-windows.exe`, `arcade-macos.dmg`, `arcade-linux.AppImage`, `agent-windows.exe`, `agent-macos.dmg`, `agent-linux.AppImage`, `agent-linux.deb`); write release notes

- [ ] **First-customer license generation** (ENG-A):
  - [ ] Customer sends Hardware ID from Activation screen
  - [ ] Run keygen: `python tools/keygen/generate_license.py --hardware-id {id} --cafe-name "{name}" --license-type PERPETUAL`
  - [ ] Deliver `license.key` out-of-band (secure email or USB)
  - [ ] Record delivery in internal license registry

- [ ] **Monitored first deployment**:
  - [ ] Install on customer hardware with engineer present or remotely available
  - [ ] Follow `docs/deployment.md` first-run checklist (all SDD §15.4 items)
  - [ ] Verify all 23 AC against real environment
  - [ ] Monitor for 48 hours post-launch
  - [ ] Log all issues with severity classification

### ⚡ CHECKPOINT 13-END (Go/No-Go Gate)

- [ ] All 23 SRS acceptance criteria VERIFIED in real deployment
- [ ] No P0 bugs (system-down, data loss, billing error) outstanding
- [ ] License verified by customer (they can activate and use the system)
- [ ] Nightly backup running and confirmed
- [ ] Customer can operate the system without engineer assistance (operator guide sufficient)

---

## Phase 14: Post-Launch Support & V2 Scoping

### Objectives

Establish support process, bug fix cadence, and begin scoping V2 features.

### Deliverables

- Bug severity and SLA definitions documented
- Patch release process defined (semantic versioning: `v1.0.x` for patches)
- V2 feature scope document started

---

### Epic 14.1: Support Infrastructure

- [ ] **Bug severity and SLA** (document in `docs/CONTRIBUTING.md`):
  - P0: billing data loss, server crash loop, license verification failure → fix within 24 hours
  - P1: checkout error, kiosk overlay bypass → fix within 72 hours
  - P2: UI bugs, non-critical performance issues → next scheduled patch

- [ ] **Patch release process**: bump version; run all tests; build artifacts; deliver to customer; document customer upgrade process (Alembic handles schema migrations automatically)

- [ ] **Version tracking**: record which version each customer is running; document upgrade procedure

### Epic 14.2: V2 Scoping

- [ ] **Create `docs/roadmap/v2-scope.md`** — assess effort and technical dependencies for each V2 feature:
  - [ ] Online booking portal — assess frontend + backend effort
  - [ ] WhatsApp/SMS notifications (Sparrow SMS API) — assess Nepal connectivity, API costs
  - [ ] Optional WAN remote access (phone-home pattern) — assess security design (read-only stats endpoint, no inbound port)
  - [ ] Multi-location support — assess DB schema changes (multi-tenant); cross-location member accounts
  - [ ] PostgreSQL migration path — assess Alembic migration complexity; connection pooling changes (asyncpg)

- [ ] **V1 architectural decisions review**: which decisions facilitate V2 (settings table as key-value for multi-location); which need revision (SQLite → Postgres; single server → multi-server)

---

## Production Readiness Checklist

To be completed at the end of Phase 13, before any customer delivery.

### Code & Architecture

- [ ] All 23 SRS acceptance criteria verified (CHECKPOINT 13-END)
- [ ] No `@app.on_event` deprecation warnings in server logs (AC-19)
- [ ] All monetary fields are `int` (paise) — no `float` anywhere in codebase
- [ ] All ORM queries via SQLAlchemy — no raw SQL with user input
- [ ] All sensitive fields excluded from API responses (no `pin_hash` in any response schema)
- [ ] `token_version` invalidation working (stale JWT rejected within one request)

### Security

- [ ] `tools/keygen/private_key.pem` never in git history
- [ ] `arcade.config.json` and `agent.config.json` in `.gitignore`
- [ ] No HIGH or CRITICAL CVEs in Python or Node.js dependencies
- [ ] Argon2id params meet OWASP recommendations
- [ ] Agent secrets unique per seat, randomly generated, not hardcoded
- [ ] Auth audit table complete — all 40+ endpoints verified
- [ ] Rate limiting: 5 failed logins → 15-minute lockout
- [ ] Threat model documented

### Testing

- [ ] Backend unit test coverage ≥ 80%
- [ ] All 23 SRS acceptance criteria have passing tests or documented manual results
- [ ] 50-concurrent-WebSocket load test passes
- [ ] Analytics queries < 2 seconds on 1-year seeded dataset
- [ ] Cross-browser testing complete (Chrome, Firefox, Safari, mobile)
- [ ] Per-OS manual test checklist complete (Windows, macOS, Linux — server + agent + Launcher)

### Deployment

- [ ] PyInstaller build confirmed on a fresh Windows VM without Python installed
- [ ] Agent distributables install on all three OSes
- [ ] Nightly backup scheduled and tested (manual trigger works)
- [ ] Backup retention pruning works
- [ ] `docs/deployment.md` first-run checklist complete and followed successfully
- [ ] File permissions documented (`chmod 600` for `arcade.config.json`, `agent.config.json`, `license.key`)

### Documentation

- [ ] No `TODO` placeholders in any `.md` file
- [ ] OpenAPI spec exported and accurate
- [ ] `docs/operator-guide.md` reviewed by a non-technical person
- [ ] `docs/deployment.md` followed successfully on a fresh machine
- [ ] Known platform limitations table in `docs/agent-setup.md`

### Operations

- [ ] First customer license generated and delivered via secure channel
- [ ] License delivery recorded in internal registry
- [ ] Customer can activate, configure, and operate the system independently
- [ ] On-call engineer available for 48 hours post-launch
- [ ] Bug reporting process communicated to customer

---

## Appendix A: Integration Points Reference

| Integration Point         | Source    | Target        | Protocol              | Schema                                                                               |
| ------------------------- | --------- | ------------- | --------------------- | ------------------------------------------------------------------------------------ |
| Session start             | Dashboard | FastAPI       | REST POST             | `SessionStartRequest`                                                                |
| `HIDE_OVERLAY`            | FastAPI   | Agent         | WebSocket JSON        | `{type: "HIDE_OVERLAY", session_id}`                                                 |
| `SHOW_OVERLAY`            | FastAPI   | Agent         | WebSocket JSON        | `{type: "SHOW_OVERLAY"}`                                                             |
| `TAKE_SCREENSHOT`         | FastAPI   | Agent         | WebSocket JSON        | `{type: "TAKE_SCREENSHOT", request_id}`                                              |
| `SCREENSHOT_RESPONSE`     | Agent     | FastAPI       | WebSocket JSON        | `{type: "SCREENSHOT_RESPONSE", request_id, data: "base64jpeg"}`                      |
| `SHOW_MESSAGE`            | FastAPI   | Agent         | WebSocket JSON        | `{type: "SHOW_MESSAGE", message}`                                                    |
| `RESTART` / `SHUTDOWN`    | FastAPI   | Agent         | WebSocket JSON        | `{type: "RESTART"}` / `{type: "SHUTDOWN"}`                                           |
| `REGISTER`                | Agent     | FastAPI       | WebSocket JSON        | `{type: "REGISTER", seat_id, mac_address, agent_secret, hostname, os}`               |
| `SYNC`                    | Agent     | FastAPI       | WebSocket JSON        | `{type: "SYNC", session_id, local_elapsed_seconds, disconnect_at, reconnect_at}`     |
| `HEALTH`                  | Agent     | FastAPI       | WebSocket JSON        | `{type: "HEALTH", seat_id, cpu_pct, ram_pct, cpu_temp, disk_used_gb, disk_total_gb}` |
| `STAFF_OVERRIDE`          | Agent     | FastAPI       | WebSocket JSON        | `{type: "STAFF_OVERRIDE", payload: {seat_id, timestamp}}`                            |
| `RESET_OVERRIDE`          | FastAPI   | Agent         | WebSocket JSON        | `{type: "RESET_OVERRIDE", payload: {}}`                                              |
| `LOW_TIME_WARNING`        | FastAPI   | Agent         | WebSocket JSON        | `{type: "LOW_TIME_WARNING", minutes_remaining}`                                      |
| `seat_updated` broadcast  | FastAPI   | Dashboard     | WebSocket JSON        | `{event: "seat_updated", data: SeatResponse}`                                        |
| `health_update` broadcast | FastAPI   | Dashboard     | WebSocket JSON        | `{event: "health_update", data: {seat_id, metrics}}`                                 |
| WoL magic packet          | FastAPI   | Client PC NIC | UDP                   | 6×0xFF + 16×MAC address bytes                                                        |
| Tuya plug control         | FastAPI   | Smart Plug    | Local LAN (TinyTuya)  | `device.turn_on()` / `device.turn_off()`                                             |
| Thermal receipt           | FastAPI   | Printer       | USB/Network (ESC/POS) | `python-escpos` commands                                                             |

---

## Appendix B: `arcade.config.json` Schema Reference

All engineers must use the exact field names below. ENG-B (Launcher) writes this file; ENG-A (FastAPI) reads it.

```json
{
  "cafe_name": "string",
  "host": "string (IP)",
  "port": "integer",
  "db_path": "string",
  "backup_dir": "string",
  "backup_retain_days": "integer (default: 30)",
  "backup_time": "string HH:MM (default: '03:00')",
  "admin_staff_id": "string (e.g., 'S001')",
  "admin_pin_hash": "string (Argon2id PHC hash)",
  "cashier_staff_id": "string",
  "cashier_pin_hash": "string (Argon2id PHC hash)",
  "jwt_secret": "string (64-char hex from secrets.token_hex(32))",
  "agent_secrets": { "seat_id": "string (64-char hex)" },
  "tuya_devices": [
    {
      "seat_id": "string",
      "device_id": "string",
      "local_key": "string",
      "ip_address": "string",
      "protocol_version": "string"
    }
  ],
  "printer_type": "string ('usb' or 'network')",
  "printer_usb_vendor": "string (hex, e.g., '0x04b8')",
  "printer_usb_product": "string (hex)"
}
```

`agent.config.json` (per client machine):

```json
{
  "server_url": "string (e.g., 'ws://192.168.1.100:8000')",
  "cafe_name": "string",
  "seat_id": "string (e.g., 'seat_001')",
  "agent_secret": "string (64-char hex — unique per seat)",
  "override_code_hash": "string (Argon2id PHC hash, null or absent to disable Staff Override)"
}
```

---

## Appendix C: Environment Variables (Development Only)

For local development only. **Never used in production** — production reads `arcade.config.json`.

```bash
ARCADE_DB_PATH=./arcade_dev.db
ARCADE_PORT=8001
ARCADE_LOG_LEVEL=DEBUG
```

---

## Appendix D: Feature Flag Defaults Reference

| Flag                         | Default | Description                      | Gate (API returns 503 if OFF) |
| ---------------------------- | ------- | -------------------------------- | ----------------------------- |
| `enable_members`             | `true`  | Member accounts, wallet, loyalty | Member endpoints              |
| `enable_packages`            | `true`  | Time bundles and day passes      | Package endpoints             |
| `enable_pos`                 | `true`  | Food & drink ordering            | POS endpoints                 |
| `enable_inventory`           | `false` | Stock tracking for POS items     | Inventory endpoints           |
| `enable_reservations`        | `true`  | Advance seat reservations        | Reservation endpoints         |
| `enable_vouchers`            | `false` | Prepaid voucher codes            | Voucher endpoints             |
| `enable_tournaments`         | `false` | Event and tournament mode        | Event endpoints               |
| `enable_expense_tracking`    | `false` | Expense log and P&L              | Expense endpoints             |
| `enable_health_monitoring`   | `true`  | PC hardware metrics from agent   | Health endpoints              |
| `require_member_for_session` | `false` | Require member login to unlock   | Applied at session start      |

---

## Appendix E: SQLite Performance Tuning Reference

The following pragmas are set on every new database connection. Do not change without benchmarking and team review.

```sql
PRAGMA journal_mode = WAL;         -- Write-Ahead Logging; 30-60% better P99 write latency
PRAGMA busy_timeout = 5000;        -- Wait 5s before "database is locked" error
PRAGMA synchronous = NORMAL;       -- Safe with WAL; slight durability trade-off for performance
PRAGMA foreign_keys = ON;          -- Enforce referential integrity
PRAGMA mmap_size = 134217728;      -- 128 MB memory-mapped I/O; reduces syscall overhead
PRAGMA cache_size = -32000;        -- 32 MB page cache (negative = KB)
PRAGMA wal_autocheckpoint = 1000;  -- Checkpoint after 1000 WAL pages (~4 MB)
PRAGMA temp_store = MEMORY;        -- Keep temp tables in RAM
```

**Risk note:** `synchronous = NORMAL` with WAL means the most recent few milliseconds of commits may be lost on a power failure (OS kernel panic). This is acceptable for a cafe management system where the server has uninterruptible power or regular autosave. The database file will never be corrupted.

---

_This roadmap is the authoritative implementation plan for Arcade v1.0. It supersedes the v2.0 TODO.md. Changes to requirements must be reflected here before implementation begins._

_Last updated: June 2026_

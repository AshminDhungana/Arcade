# Software Design Document

## Arcade — Gaming Cafe Management System

**Document Version:** 2.0
**Project Version:** 2.0
**Date:** June 2026
**Prepared by:** Ashmin Dhungana
**Status:** Pre‑Development · Design Complete
**Classification:** Internal / Private
**Reference SRS:** Arcade_SRS v2.0

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [System Overview](#2-system-overview)
3. [Architecture Design](#3-architecture-design)
4. [Backend Design](#4-backend-design)
5. [Database Design](#5-database-design)
6. [Frontend Design](#6-frontend-design)
7. [Electron Agent Design](#7-electron-agent-design)
8. [Launcher Design](#8-launcher-design)
9. [Real-time Communication Design](#9-real-time-communication-design)
10. [Billing Engine Design](#10-billing-engine-design)
11. [Security Design](#11-security-design)
12. [Integration Design](#12-integration-design)
13. [Error Handling and Resilience](#13-error-handling-and-resilience)
14. [Configuration Design](#14-configuration-design)
15. [Deployment Design](#15-deployment-design)
16. [Licensing and Activation Design](#16-licensing-and-activation-design)
17. [Design Decisions and Trade-offs](#17-design-decisions-and-trade-offs)

---

## 1. Introduction

### 1.1 Purpose

This Software Design Document (SDD) describes the architectural and detailed design of Arcade, a self-hosted gaming cafe management system. It translates the requirements defined in the SRS into concrete design decisions, component structures, data models, interface contracts, and implementation guidance for the development team at Neurotech Biratnagar.

### 1.2 Scope

This document covers the design of all four primary Arcade components:

- **Arcade Server** — FastAPI backend, SQLite database, business logic (cross‑platform)
- **Arcade Dashboard** — React staff interface and owner mobile view (cross‑platform by nature)
- **Arcade Agent** — Electron client application on each gaming PC (cross‑platform with platform abstraction)
- **Arcade Launcher** — Tkinter GUI for server management, including license activation (cross‑platform)

It also covers cross-cutting concerns: real-time communication, billing logic, security, license activation and verification, external integrations (Tuya, thermal printing), resilience, cross‑platform support, and deployment on Windows, macOS, and Linux.

### 1.3 Intended Audience

- Backend and frontend developers implementing the system
- QA engineers designing test plans
- Future maintainers of the codebase

### 1.4 Relationship to SRS

This document maps directly to the requirements in `Arcade_SRS v2.0`. Where a design decision satisfies a specific requirement, the relevant `FR-XXX` or `NFR-XXX` identifier is referenced.

### 1.5 Document Conventions

- **Module paths** use dot notation: `backend.services.billing`
- **API routes** use HTTP method + path: `POST /api/sessions`
- **WebSocket events** use the prefix `ws:`
- Code samples are illustrative and not necessarily final implementation

---

## 2. System Overview

Arcade is a four-component client-server system operating entirely on a local area network. All components are designed to run on **Windows, macOS, and Linux** – the server (FastAPI + SQLite + Launcher) runs on any of these OSes, and the Electron agent runs on all three as well.

```
┌─────────────────────────────────────────────────────────────────┐
│                        COUNTER PC (Server)                      │
│                                                                 │
│  ┌──────────────┐     ┌─────────────────────────────────────┐  │
│  │   Launcher   │────▶│         FastAPI Server              │  │
│  │  (Tkinter)   │     │  ┌──────────┐  ┌────────────────┐  │  │
│  │  ┌────────┐  │     │  │  Routers │  │    Services    │  │  │
│  │  │License │  │     │  └──────────┘  └────────────────┘  │  │
│  │  │ Check  │  │     │  ┌──────────┐  ┌────────────────┐  │  │
│  │  └────────┘  │     │  │  Schemas │  │ Repositories   │  │  │
│  └──────────────┘     │  └──────────┘  └────────────────┘  │  │
│                        │         ▼               ▼           │  │
│  ┌──────────────┐      │  ┌─────────────────────────────┐   │  │
│  │   React      │◀────▶│  │     SQLite (WAL mode)        │   │  │
│  │  Dashboard   │      │  └─────────────────────────────┘   │  │
│  └──────────────┘      └─────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
         │  WebSocket + REST (LAN)         │  WoL (UDP)
         ▼                                 ▼
┌─────────────────┐              ┌──────────────────────────────┐
│  Owner's Phone  │              │   Client PCs (Windows/Mac/Linux)
│  (Mobile View)  │              │ ┌──────────────────────────┐ │
└─────────────────┘              │ │    Electron Agent         │ │
                                 │ │ ┌──────────────────────┐ │ │
                                 │ │ │ Platform Abstraction  │ │ │
                                 │ │ │  ┌─────────┬───────┐ │ │ │
                                 │ │ │  │ Windows │ macOS │ │ │ │
                                 │ │ │  ├─────────┴───────┤ │ │ │
                                 │ │ │  │     Linux       │ │ │ │
                                 │ │ │  └─────────────────┘ │ │ │
                                 │ │ └──────────────────────┘ │ │
                                 │ └──────────────────────────┘ │
                                 └──────────────────────────────┘
         │  Tuya Cloud API (internet)  │  (Local LAN after pairing)
         ▼                             ▼
┌─────────────────┐              ┌─────────────────┐
│  Smart Plugs    │              │    Smart Plugs  │
│  (PS5 / Xbox)   │              │  (PS5 / Xbox)   │
└─────────────────┘              └─────────────────┘
```

The Launcher's License Check runs once at every startup, entirely offline against the locally stored `license.key`. It gates the Tkinter setup wizard and the FastAPI server subprocess — neither runs unless the check passes. It never blocks on, or talks to, any network.

### 2.1 Communication Summary

| Direction                | Protocol              | Purpose                                              |
| ------------------------ | --------------------- | ---------------------------------------------------- |
| Dashboard ↔ Server       | REST (HTTP/JSON)      | CRUD operations, checkout, settings                  |
| Dashboard ↔ Server       | WebSocket             | Real-time seat status, health metrics, announcements |
| Agent ↔ Server           | WebSocket             | Overlay commands, health metrics, remote commands    |
| Server → Client PCs      | UDP (WoL)             | Wake-on-LAN magic packets (cross‑platform)           |
| Server → Tuya Cloud      | HTTPS (initial only)  | Smart plug on/off (local after pairing)              |
| Server → Thermal Printer | USB/Network (ESC/POS) | Receipt printing                                     |

---

## 3. Architecture Design

### 3.1 Layered Backend Architecture

The backend follows a strict four-layer architecture. Each layer communicates only with the layer directly below it.

```
┌─────────────────────────────────────────┐
│           HTTP / WebSocket Layer        │  ← FastAPI routers, request validation,
│         backend/api/routers/            │    response serialisation (Pydantic schemas)
├─────────────────────────────────────────┤
│              Service Layer              │  ← Business logic, billing engine,
│           backend/services/             │    orchestration, feature flag checks
├─────────────────────────────────────────┤
│            Repository Layer             │  ← All SQL queries, no business logic,
│         backend/repositories/           │    returns ORM models or typed dicts
├─────────────────────────────────────────┤
│           Database / ORM Layer          │  ← SQLAlchemy models, Alembic migrations,
│     backend/models/ + backend/core/     │    SQLite connection and WAL config
└─────────────────────────────────────────┘
```

**Rules enforced:**

- Routers MUST NOT contain SQL queries or business logic
- Services MUST NOT import SQLAlchemy models directly — they call repositories
- Repositories MUST NOT import services
- Services contain all feature flag checks before delegating to repositories

### 3.2 Full Directory Structure

```
arcade/
├── backend/
│   ├── api/
│   │   ├── routers/
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
│   │   │   └── ws.py               # WebSocket endpoints
│   │   └── deps.py                 # Shared FastAPI dependencies (AsyncSession, auth)
│   ├── services/
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
│   ├── repositories/
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
│   ├── models/
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
│   ├── licensing/
│   │   ├── verify.py               # Ed25519 signature verification
│   │   ├── fingerprint.py          # Uses py-machineid (primary) + OS fallbacks
│   │   └── public_key.py           # Embedded Ed25519 public key (hardcoded)
│   ├── core/
│   │   ├── config.py               # arcade.config.json loader
│   │   ├── database.py             # SQLAlchemy AsyncEngine, WAL pragmas with busy_timeout=5000,
│   │   │                            # AsyncSessionLocal, get_db() dependency
│   │   ├── feature_flags.py        # Feature flag loader and checker (DB-backed)
│   │   ├── security.py             # Argon2id hashing (argon2-cffi), JWT with token_version,
│   │   │                            # rate limiting, lockout
│   │   └── ws_manager.py           # WebSocket connection manager (heartbeat, agent_secret validation)
│   ├── main.py                     # FastAPI app with lifespan context manager
│   ├── requirements.txt            # Python dependencies
│   └── alembic.ini                 # Alembic configuration
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
├── alembic/                        # Database migration scripts
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│       ├── 001_initial.py
│       └── ...
├── tools/                          # INTERNAL — NOT SHIPPED TO CUSTOMERS
│   └── keygen/                     # Offline license key generation tool
│       ├── generate_license.py     # CLI tool — holds the private signing key
│       └── private_key.pem         # Ed25519 private key — NEVER committed to VCS
├── launcher.py                     # Tkinter GUI launcher (cross‑platform)
│                                   # - License Activation screen (py-machineid hardware ID)
│                                   # - Setup wizard (creates arcade.config.json with agent_secrets)
│                                   # - Server process management (starts FastAPI subprocess)
│                                   # - Live server logs display
├── arcade.config.json              # Runtime config (created by setup wizard — per server)
│                                   # Contains: cafe_name, host, port, db_path, backup settings,
│                                   # admin/cashier PIN hashes (Argon2id), jwt_secret,
│                                   # agent_secrets: {seat_id: agent_secret}
├── license.key                     # License file (placed by owner after activation — not in repo)
├── README.md
└── LICENSE                         # Apache 2.0
```

---

## 4. Backend Design

### 4.1 Application Entry Point

The FastAPI application is instantiated in `backend/main.py` using the **`lifespan` context manager pattern** (FastAPI 0.93+). The Launcher only spawns this process after a successful license check (see §16) — `main.py` itself does not re-verify the license, since FastAPI startup assumes the Launcher has already gated entry.

```python
# backend/main.py
from contextlib import asynccontextmanager
from fastapi import FastAPI
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- STARTUP ---
    # 1. Load arcade.config.json via core.config
    # 2. Run alembic upgrade head
    # 3. Load feature flags from DB settings table
    # 4. Initialise WebSocket manager
    # 5. Register all routers with prefix /api
    # 6. Register WebSocket router at /ws
    # 7. Send Wake-on-LAN packets to all registered seats
    # 8. Schedule nightly backup task via APScheduler
    yield
    # --- SHUTDOWN ---
    # 1. Stop accepting new WebSocket connections
    # 2. Notify all connected agents: server shutting down
    # 3. Close all WebSocket connections cleanly
    # 4. Flush any pending audit log writes
    # 5. Shutdown APScheduler
    # 6. Close SQLAlchemy connection pool

app = FastAPI(lifespan=lifespan)
```

### 4.2 Router Design

Each router is a `FastAPI.APIRouter` registered with a prefix and tags. Routers handle only:

- Request parsing (via Pydantic schemas)
- Auth dependency injection (via `deps.py`)
- Calling the appropriate service method
- Returning the response schema

**Example — Session Router (`routers/sessions.py`):**

```
POST   /api/sessions                → session_service.start_session()
PATCH  /api/sessions/{id}/pause     → session_service.pause_session()
PATCH  /api/sessions/{id}/resume    → session_service.resume_session()
POST   /api/sessions/{id}/checkout  → billing_service.checkout()
GET    /api/sessions/{id}           → session_service.get_session()
GET    /api/sessions/active         → session_service.list_active()
```

**Standard router dependencies:**

- `db: AsyncSession = Depends(get_db)` — async SQLAlchemy session per request
- `staff: StaffSchema = Depends(get_current_staff)` — authenticated staff from token
- `flags: FeatureFlags = Depends(get_feature_flags)` — current feature flag state

### 4.3 Service Layer Design

Services are plain Python classes (or modules) with no HTTP concern. They implement all business logic and call repositories for data access. All service methods are `async def` and use `AsyncSession` from repositories.

#### 4.3.1 Session Service (`services/session_service.py`)

```
async def start_session(seat_id, member_id?, db: AsyncSession) → Session
  1. Validate seat is Available or Reserved
  2. If require_member_for_session flag ON and no member_id → raise error
  3. Call billing_service.resolve_rate(seat, member, time_now) → locked_rate
  4. Call package_service.get_active_package(member_id) → active_package?
  5. Call promotion_service.get_applicable(seat, member, time_now) → promotion?
  6. Create Session record (rate locked, promo locked, package linked)
  7. Update seat status → IN_USE
  8. Send ws:seat_updated broadcast
  9. Call ws_manager.send_to_agent(seat_id, command=HIDE_OVERLAY)
  10. If console seat → call tuya_service.power_on(plug_id)
  11. Write audit log entry
  12. Return session

async def checkout(session_id, payment_method, db: AsyncSession) → Invoice
  1. Load session, validate IN_USE or PAUSED
  2. Compute elapsed seconds
  3. Call billing_service.calculate_invoice(session, elapsed) → InvoiceLineItems
  4. Create Invoice record
  5. If member → deduct wallet / update loyalty points
  6. Update seat status → AVAILABLE
  7. Send ws:seat_updated broadcast
  8. Call ws_manager.send_to_agent(seat_id, command=SHOW_OVERLAY)
  9. If console → call tuya_service.power_off(plug_id)
  10. Write audit log entry
  11. Trigger print_service.print_receipt(invoice) async
  12. Return invoice
```

#### 4.3.2 Billing Service (`services/billing_service.py`)

See Section 10 for detailed billing engine design.

#### 4.3.3 WebSocket Manager (`core/ws_manager.py`)

```python
class WebSocketManager:
    # Two connection registries:
    dashboard_connections: list[WebSocket]       # All dashboard clients
    agent_connections: dict[str, WebSocket]      # seat_id → agent WebSocket

    async def broadcast_to_dashboards(event: str, payload: dict)
    async def send_to_agent(seat_id: str, command: AgentCommand)
    async def register_agent(seat_id: str, ws: WebSocket)
    async def unregister_agent(seat_id: str)
    async def heartbeat_loop()                   # Pings all connections every 30s
    async def close_all()                        # Graceful shutdown
```

### 4.4 Repository Layer Design

Repositories contain all SQLAlchemy queries. They accept a `db: AsyncSession` parameter and return ORM model instances or typed dicts. No business logic lives in repositories. All repository methods are `async def`.

**Example — Session Repository (`repositories/session_repo.py`):**

```python
async def create(db: AsyncSession, seat_id, member_id, rate_paise, promo_id, package_id, ...) → SessionModel
async def get_by_id(db: AsyncSession, session_id) → SessionModel | None
async def get_active_by_seat(db: AsyncSession, seat_id) → SessionModel | None
async def list_active(db: AsyncSession) → list[SessionModel]
async def update_status(db: AsyncSession, session_id, status) → SessionModel
async def list_by_shift(db: AsyncSession, shift_id) → list[SessionModel]
async def list_active_sessions(db: AsyncSession) → list[SessionModel]  # For server recovery
```

### 4.5 Schema Design (Pydantic)

All request bodies and response payloads are typed Pydantic models. Monetary fields are always integers (paise) in API schemas; display conversion happens in the frontend.

**Example schemas:**

```python
class SessionStartRequest(BaseModel):
    seat_id: str
    member_id: str | None = None

class SessionResponse(BaseModel):
    id: str
    seat_id: str
    member_id: str | None
    started_at: datetime
    status: SessionStatus
    locked_rate_paise: int
    package_id: str | None
    promotion_id: str | None

class InvoiceResponse(BaseModel):
    id: str
    session_id: str
    time_charge_paise: int
    package_credit_used_paise: int
    discount_paise: int
    pos_items: list[InvoiceLineItem]
    total_paise: int
    payment_method: PaymentMethod
```

### 4.6 API Route Reference (Complete)

| Method    | Path                        | Auth    | Description                                                            |
| --------- | --------------------------- | ------- | ---------------------------------------------------------------------- |
| GET       | /health                     | None    | Server health check (includes license status summary)                  |
| GET       | /api/settings/license       | Admin   | View license status (cafe name, type, activation date, hardware match) |
| POST      | /api/auth/login             | None    | Staff PIN login → token                                                |
| GET       | /api/seats                  | Cashier | List all seats with status                                             |
| PATCH     | /api/seats/{id}/maintenance | Admin   | Toggle maintenance mode                                                |
| POST      | /api/sessions               | Cashier | Start session                                                          |
| PATCH     | /api/sessions/{id}/pause    | Cashier | Pause session                                                          |
| PATCH     | /api/sessions/{id}/resume   | Cashier | Resume session                                                         |
| POST      | /api/sessions/{id}/checkout | Cashier | Checkout and generate invoice                                          |
| GET       | /api/sessions/{id}          | Cashier | Session detail                                                         |
| GET       | /api/sessions/active        | Cashier | All active sessions                                                    |
| GET       | /api/invoices/{id}          | Cashier | Invoice detail                                                         |
| POST      | /api/pos/items              | Cashier | Add POS item to session tab                                            |
| DELETE    | /api/pos/items/{id}         | Cashier | Remove POS item from tab                                               |
| GET       | /api/menu                   | Cashier | List menu items                                                        |
| POST      | /api/menu                   | Admin   | Create menu item                                                       |
| PATCH     | /api/menu/{id}              | Admin   | Update menu item                                                       |
| POST      | /api/inventory/restock      | Admin   | Record restock event                                                   |
| GET       | /api/members                | Cashier | Search/list members                                                    |
| POST      | /api/members                | Cashier | Create member                                                          |
| GET       | /api/members/{id}           | Cashier | Member detail + active packages                                        |
| POST      | /api/members/{id}/topup     | Cashier | Wallet top-up                                                          |
| GET       | /api/packages               | Admin   | List package types                                                     |
| POST      | /api/packages               | Admin   | Create package type                                                    |
| POST      | /api/members/{id}/packages  | Cashier | Sell package to member                                                 |
| GET       | /api/promotions             | Admin   | List promotions                                                        |
| POST      | /api/promotions             | Admin   | Create promotion                                                       |
| PATCH     | /api/promotions/{id}        | Admin   | Update/toggle promotion                                                |
| POST      | /api/vouchers/generate      | Admin   | Generate voucher batch                                                 |
| POST      | /api/vouchers/redeem        | Cashier | Redeem voucher                                                         |
| GET       | /api/reservations           | Cashier | List reservations                                                      |
| POST      | /api/reservations           | Cashier | Create reservation                                                     |
| PATCH     | /api/reservations/{id}      | Cashier | Confirm / cancel / edit reservation                                   |
| DELETE    | /api/reservations/{id}      | Cashier | Hard-delete reservation record                                         |
| GET       | /api/staff                  | Admin   | List staff                                                             |
| POST      | /api/staff                  | Admin   | Create staff member                                                    |
| POST      | /api/staff/{id}/change-pin  | Admin   | Change staff PIN (increments token_version)                            |
| POST      | /api/staff/{id}/deactivate  | Admin   | Deactivate staff (increments token_version)                            |
| POST      | /api/shifts/open            | Cashier | Open shift                                                             |
| POST      | /api/shifts/close           | Cashier | Close shift                                                            |
| GET       | /api/shifts/{id}/report     | Admin   | Shift report                                                           |
| POST      | /api/expenses               | Admin   | Log expense                                                            |
| GET       | /api/expenses               | Admin   | List expenses                                                          |
| GET       | /api/analytics/summary      | Admin   | Analytics dashboard data                                               |
| GET       | /api/events                 | Admin   | List events                                                            |
| POST      | /api/events                 | Admin   | Create event                                                           |
| POST      | /api/events/{id}/register   | Cashier | Register participant                                                   |
| PATCH     | /api/events/{id}/match      | Admin   | Record match result                                                    |
| GET       | /api/settings               | Admin   | Get all settings + feature flags                                       |
| PATCH     | /api/settings               | Admin   | Update settings/feature flags                                          |
| POST      | /api/commands/{seat_id}     | Admin   | Send remote command to agent                                           |
| GET       | /api/audit                  | Admin   | Paginated audit log                                                    |
| WebSocket | /ws/dashboard               | Cashier | Dashboard real-time feed                                               |
| WebSocket | /ws/agent/{seat_id}         | Agent   | Agent command channel                                                  |

---

## 5. Database Design

### 5.1 ORM Models

All models use SQLAlchemy declarative base. All IDs are UUIDs (stored as strings). All timestamps are UTC. All monetary amounts are integers (paise).

#### seats

| Column      | Type        | Notes                                                     |
| ----------- | ----------- | --------------------------------------------------------- |
| id          | String PK   | UUID                                                      |
| name        | String      | Display name (e.g., "PC-01")                              |
| zone_id     | String FK   | → zones.id                                                |
| mac_address | String      | Registered by agent on first connect                      |
| status      | Enum        | AVAILABLE, IN_USE, RESERVED, PAUSED, MAINTENANCE, OFFLINE |
| plug_id     | String NULL | Tuya plug ID for console seats                            |
| is_console  | Boolean     | True for PS5/Xbox seats                                   |
| notes       | String NULL | Maintenance note                                          |
| created_at  | DateTime    |                                                           |
| updated_at  | DateTime    | Set explicitly in service code (not via onupdate trigger) |

#### zones

| Column                | Type         | Notes                                      |
| --------------------- | ------------ | ------------------------------------------ |
| id                    | String PK    | UUID                                       |
| name                  | String       | Standard PC, VIP PC, Console Corner, Other |
| rate_per_minute_paise | Integer      | Base per-minute rate                       |
| rate_per_hour_paise   | Integer      | Flat hourly rate                           |
| pricing_model         | Enum         | PER_MINUTE, FLAT_HOURLY, TIME_BLOCK        |
| block_minutes         | Integer NULL | Block size (e.g., 30) for TIME_BLOCK       |

#### sessions

| Column                 | Type              | Notes                                |
| ---------------------- | ----------------- | ------------------------------------ |
| id                     | String PK         | UUID                                 |
| seat_id                | String FK         | → seats.id                           |
| member_id              | String FK NULL    | → members.id                         |
| shift_id               | String FK NULL    | → shifts.id                          |
| status                 | Enum              | ACTIVE, PAUSED, COMPLETED, ABANDONED |
| started_at             | DateTime UTC      |                                      |
| ended_at               | DateTime UTC NULL |                                      |
| paused_at              | DateTime UTC NULL |                                      |
| total_paused_seconds   | Integer           | Accumulates across multiple pauses   |
| locked_rate_paise      | Integer           | Rate per minute locked at start      |
| locked_pricing_model   | Enum              | Locked at start                      |
| package_entitlement_id | String FK NULL    | → member_package_entitlements.id     |
| promotion_id           | String FK NULL    | → promotions.id                      |
| discount_paise         | Integer           | 0 if no discount                     |
| created_at             | DateTime UTC      |                                      |
| updated_at             | DateTime UTC      | Set explicitly in service code       |

#### invoices

| Column                    | Type           | Notes                       |
| ------------------------- | -------------- | --------------------------- |
| id                        | String PK      | UUID                        |
| session_id                | String FK      | → sessions.id               |
| member_id                 | String FK NULL |                             |
| shift_id                  | String FK NULL |                             |
| time_charge_paise         | Integer        |                             |
| package_credit_used_paise | Integer        |                             |
| discount_paise            | Integer        |                             |
| pos_total_paise           | Integer        |                             |
| total_paise               | Integer        |                             |
| payment_method            | Enum           | CASH, CARD, WALLET, PACKAGE |
| created_at                | DateTime UTC   |                             |

#### invoice_line_items

| Column           | Type      | Notes                                           |
| ---------------- | --------- | ----------------------------------------------- |
| id               | String PK | UUID                                            |
| invoice_id       | String FK | → invoices.id                                   |
| type             | Enum      | TIME_CHARGE, POS_ITEM, DISCOUNT, PACKAGE_CREDIT |
| description      | String    | Human-readable label                            |
| quantity         | Integer   |                                                 |
| unit_price_paise | Integer   |                                                 |
| total_paise      | Integer   |                                                 |

#### members

| Column               | Type          | Notes                          |
| -------------------- | ------------- | ------------------------------ |
| id                   | String PK     | UUID                           |
| name                 | String        |                                |
| phone                | String UNIQUE |                                |
| wallet_balance_paise | Integer       | Default 0                      |
| loyalty_points       | Integer       | Default 0                      |
| tier                 | Enum          | BRONZE, SILVER, GOLD           |
| birth_month          | Integer NULL  | 1–12, for birthday promotions  |
| total_visits         | Integer       | Default 0                      |
| total_seconds_played | Integer       | Default 0                      |
| created_at           | DateTime UTC  |                                |
| updated_at           | DateTime UTC  | Set explicitly in service code |

#### packages (types/products)

| Column              | Type         | Notes                                      |
| ------------------- | ------------ | ------------------------------------------ |
| id                  | String PK    | UUID                                       |
| name                | String       | e.g., "10-Hour Bundle"                     |
| type                | Enum         | HOUR_BUNDLE, DAY_PASS, NIGHT_PASS, MONTHLY |
| total_minutes       | Integer      |                                            |
| price_paise         | Integer      |                                            |
| valid_days          | Integer NULL | e.g., 30 for monthly                       |
| zone_restriction_id | String NULL  | NULL = all zones                           |
| is_active           | Boolean      |                                            |

#### member_package_entitlements

| Column            | Type          | Notes                          |
| ----------------- | ------------- | ------------------------------ |
| id                | String PK     | UUID                           |
| member_id         | String FK     | → members.id                   |
| package_id        | String FK     | → packages.id                  |
| remaining_minutes | Integer       |                                |
| expires_at        | DateTime NULL |                                |
| purchased_at      | DateTime UTC  |                                |
| status            | Enum          | ACTIVE, EXHAUSTED, EXPIRED     |
| updated_at        | DateTime UTC  | Set explicitly in service code |

#### promotions

| Column              | Type          | Notes                                           |
| ------------------- | ------------- | ----------------------------------------------- |
| id                  | String PK     | UUID                                            |
| name                | String        |                                                 |
| type                | Enum          | HAPPY_HOUR, FLASH, FIRST_VISIT, GROUP, BIRTHDAY |
| discount_type       | Enum          | PERCENTAGE, FIXED_PAISE, BONUS_MINUTES          |
| discount_value      | Integer       | Percentage (0–100) or paise or minutes          |
| active_days         | String NULL   | JSON: ["MON","TUE"] — NULL = all days           |
| active_from_hour    | Integer NULL  | 0–23                                            |
| active_to_hour      | Integer NULL  | 0–23                                            |
| min_group_size      | Integer NULL  | For GROUP type                                  |
| zone_restriction_id | String NULL   |                                                 |
| is_active           | Boolean       |                                                 |
| valid_from          | DateTime NULL |                                                 |
| valid_until         | DateTime NULL |                                                 |

#### vouchers

| Column                | Type          | Notes                                |
| --------------------- | ------------- | ------------------------------------ |
| id                    | String PK     | UUID                                 |
| code                  | String UNIQUE | Alphanumeric, 8–12 chars             |
| value_paise           | Integer NULL  | Credit value                         |
| value_minutes         | Integer NULL  | Time value                           |
| status                | Enum          | UNUSED, REDEEMED, EXPIRED            |
| redeemed_by_member_id | String NULL   |                                      |
| redeemed_at           | DateTime NULL |                                      |
| expires_at            | DateTime NULL |                                      |
| batch_id              | String        | Groups codes from one generation run |
| created_at            | DateTime UTC  |                                      |

#### menu_items

| Column              | Type         | Notes                            |
| ------------------- | ------------ | -------------------------------- |
| id                  | String PK    | UUID                             |
| name                | String       |                                  |
| category            | String NULL  | e.g., Drinks, Snacks             |
| price_paise         | Integer      |                                  |
| stock_quantity      | Integer NULL | NULL = not tracked               |
| low_stock_threshold | Integer NULL |                                  |
| is_available        | Boolean      | Auto-set to false when stock = 0 |
| updated_at          | DateTime UTC | Set explicitly in service code   |

#### session_pos_items

| Column           | Type         | Notes                   |
| ---------------- | ------------ | ----------------------- |
| id               | String PK    | UUID                    |
| session_id       | String FK    | → sessions.id           |
| menu_item_id     | String FK    | → menu_items.id         |
| quantity         | Integer      |                         |
| unit_price_paise | Integer      | Locked at time of order |
| added_at         | DateTime UTC |                         |

#### reservations

| Column               | Type          | Notes                                 |
| -------------------- | ------------- | ------------------------------------- |
| id                   | String PK     | UUID                                  |
| seat_id              | String FK     | → seats.id                            |
| customer_name        | String        |                                       |
| member_id            | String NULL   |                                       |
| reserved_from        | DateTime UTC  |                                       |
| reserved_until       | DateTime NULL |                                       |
| group_reservation_id | String NULL   | Groups linked reservations            |
| status               | Enum          | PENDING, CONFIRMED, COMPLETED, CANCELLED |
| created_by_staff_id  | String FK     | Server-assigned (authenticated staff); not client-supplied |
| created_at           | DateTime UTC  |                                       |
| updated_at           | DateTime UTC  | Set explicitly in service code        |

#### staff

| Column          | Type          | Notes                                             |
| --------------- | ------------- | ------------------------------------------------- |
| id              | String PK     | UUID                                              |
| name            | String        |                                                   |
| role            | Enum          | ADMIN, CASHIER                                    |
| pin_hash        | String        | Argon2id hash                                     |
| token_version   | Integer       | Default 0. Incremented on PIN change/deactivation |
| failed_attempts | Integer       | Default 0                                         |
| lockout_until   | DateTime NULL |                                                   |
| is_active       | Boolean       |                                                   |
| updated_at      | DateTime UTC  | Set explicitly in service code                    |

#### shifts

| Column             | Type          | Notes                 |
| ------------------ | ------------- | --------------------- |
| id                 | String PK     | UUID                  |
| opened_by_staff_id | String FK     |                       |
| closed_by_staff_id | String NULL   |                       |
| opened_at          | DateTime UTC  |                       |
| closed_at          | DateTime NULL |                       |
| float_paise        | Integer       | Cash float at open    |
| counted_paise      | Integer NULL  | Cash counted at close |
| status             | Enum          | OPEN, CLOSED          |

#### expenses

| Column             | Type         | Notes                                                                     |
| ------------------ | ------------ | ------------------------------------------------------------------------- |
| id                 | String PK    | UUID                                                                      |
| date               | Date         |                                                                           |
| category           | Enum         | RENT, ELECTRICITY, INTERNET, RESTOCK, HARDWARE, MAINTENANCE, WAGES, OTHER |
| amount_paise       | Integer      |                                                                           |
| note               | String NULL  |                                                                           |
| logged_by_staff_id | String FK    |                                                                           |
| created_at         | DateTime UTC |                                                                           |

#### events

| Column           | Type         | Notes                                  |
| ---------------- | ------------ | -------------------------------------- |
| id               | String PK    | UUID                                   |
| name             | String       |                                        |
| game_title       | String       |                                        |
| event_date       | DateTime UTC |                                        |
| entry_fee_paise  | Integer      |                                        |
| prize_pool_paise | Integer      |                                        |
| bracket_type     | Enum         | SINGLE_ELIMINATION, DOUBLE_ELIMINATION |
| status           | Enum         | UPCOMING, ACTIVE, COMPLETED            |

#### event_participants

| Column           | Type         | Notes                    |
| ---------------- | ------------ | ------------------------ |
| id               | String PK    | UUID                     |
| event_id         | String FK    |                          |
| member_id        | String NULL  |                          |
| name             | String       | For walk-in participants |
| seat_id          | String NULL  |                          |
| bracket_position | Integer NULL |                          |
| eliminated       | Boolean      |                          |

#### audit_log

| Column      | Type         | Notes                                                                                                                           |
| ----------- | ------------ | ------------------------------------------------------------------------------------------------------------------------------- |
| id          | String PK    | UUID                                                                                                                            |
| timestamp   | DateTime UTC |                                                                                                                                 |
| staff_id    | String FK    |                                                                                                                                 |
| action      | Enum         | SESSION_START, SESSION_END, PAYMENT, WALLET_TOPUP, VOUCHER_GENERATED, VOUCHER_REDEEMED, SETTINGS_CHANGED, SCREENSHOT_TAKEN, ... |
| entity_type | String       | "session", "member", "invoice", etc.                                                                                            |
| entity_id   | String       |                                                                                                                                 |
| detail      | String       | JSON blob of relevant fields                                                                                                    |

#### settings

| Column     | Type         | Notes                          |
| ---------- | ------------ | ------------------------------ |
| key        | String PK    | e.g., "enable_members"         |
| value      | String       | JSON-encoded value             |
| updated_at | DateTime UTC | Set explicitly in service code |

#### restock_log

| Column             | Type         | Notes |
| ------------------ | ------------ | ----- |
| id                 | String PK    | UUID  |
| menu_item_id       | String FK    |       |
| quantity_added     | Integer      |       |
| logged_by_staff_id | String FK    |       |
| created_at         | DateTime UTC |       |

#### license_status

| Column           | Type         | Notes                                                  |
| ---------------- | ------------ | ------------------------------------------------------ |
| id               | String PK    | Always a fixed singleton value, e.g. `"current"`       |
| cafe_name        | String       | From the verified license payload                      |
| hardware_id      | String       | Hardware ID this license is bound to                   |
| license_type     | Enum         | PERPETUAL, TRIAL                                       |
| issue_date       | Date         |                                                        |
| trial_expires_at | Date NULL    | Only set for TRIAL licenses                            |
| last_verified_at | DateTime UTC | Updated each time the Launcher re-verifies the license |

This table is a **read-only cache for display purposes** (FR-LIC-014), populated by the Launcher after a successful license check and surfaced at `GET /api/settings/license`. It is never the source of truth — that is always the signed `license.key` file plus the embedded public key, verified by the Launcher before the database or server process even start. A row existing here implies the corresponding `license.key` passed verification at last launch; it does not independently grant access.

### 5.2 Indexes

```sql
-- Performance-critical indexes
CREATE INDEX idx_sessions_seat_status ON sessions(seat_id, status);
CREATE INDEX idx_sessions_shift ON sessions(shift_id);
CREATE INDEX idx_sessions_member ON sessions(member_id);
CREATE INDEX idx_invoices_session ON invoices(session_id);
CREATE INDEX idx_audit_timestamp ON audit_log(timestamp);
CREATE INDEX idx_audit_staff ON audit_log(staff_id);
CREATE INDEX idx_members_phone ON members(phone);
CREATE INDEX idx_reservations_seat_time ON reservations(seat_id, reserved_from);
CREATE INDEX idx_entitlements_member_status ON member_package_entitlements(member_id, status);
CREATE INDEX idx_vouchers_code ON vouchers(code);
CREATE UNIQUE INDEX idx_vouchers_code_unique ON vouchers(code);
```

### 5.3 Database Configuration

```python
# backend/core/database.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import event

# Async SQLAlchemy with aiosqlite
DATABASE_URL = "sqlite+aiosqlite:///./arcade.db"
engine = create_async_engine(DATABASE_URL, echo=False)

# Enable WAL mode and performance pragmas on every connection
@event.listens_for(engine.sync_engine, "connect")
def set_sqlite_pragma(dbapi_conn, _):
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA synchronous=NORMAL")      # Safe with WAL; much faster than FULL
    cursor.execute("PRAGMA busy_timeout=5000")       # Wait up to 5s before SQLITE_BUSY
    cursor.execute("PRAGMA foreign_keys=ON")         # Enforce FK constraints
    cursor.execute("PRAGMA wal_autocheckpoint=1000") # Checkpoint every ~4MB
    cursor.execute("PRAGMA cache_size=-64000")       # 64MB cache
    cursor.close()

AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
```

**Important notes on this configuration:**

- `busy_timeout=5000` is **mandatory** — without it, any concurrent write results in an immediate `SQLITE_BUSY` error
- `synchronous=NORMAL` is safe with WAL mode and significantly faster than `FULL`
- `updated_at` fields are set explicitly in service code (`entity.updated_at = datetime.utcnow()`) rather than using SQLAlchemy's `onupdate` trigger, to ensure reliable updates with async operations

### 5.4 Migration Strategy

All schema changes go through Alembic. No direct schema edits. `alembic.ini` lives in `backend/` — run all Alembic commands from that directory.

```bash
# Developer workflow for schema change:
# 1. Edit the SQLAlchemy model in backend/models/
cd backend
# 2. Generate a migration:
alembic revision --autogenerate -m "describe the change"
# 3. Review the generated migration file in alembic/versions/
# 4. Apply:
alembic upgrade head
# 5. Rollback if needed:
alembic downgrade -1
```

Migrations run automatically on server startup via `alembic upgrade head` before the FastAPI app begins serving requests.

---

## 6. Frontend Design

### 6.1 Technology Stack

| Concern      | Tool                                                   |
| ------------ | ------------------------------------------------------ |
| Framework    | React 18 + TypeScript                                  |
| Build        | Vite                                                   |
| Styling      | TailwindCSS                                            |
| Server state | React Query (TanStack Query)                           |
| WebSocket    | Custom hook (`useWebSocket`) wrapping native WebSocket |
| Charts       | Recharts                                               |
| Routing      | React Router v6                                        |

### 6.2 Application Structure

```
frontend/src/
├── pages/            # One file per route
├── components/       # Reusable UI components
├── hooks/            # Custom React hooks
├── api/              # React Query query/mutation functions
├── store/            # Zustand or Context stores (auth, feature flags)
└── utils/
    ├── currency.ts   # paise → "Rs. X.XX" formatting
    └── time.ts       # seconds → "HH:MM:SS" formatting
```

### 6.3 Key Pages and Components

#### Dashboard Page (`pages/Dashboard.tsx`)

- Renders `<SeatGrid>` — full grid of `<SeatCard>` components
- Subscribes to `ws:seat_updated` events to update seat state
- Seat card colour coding:

| Status      | Colour |
| ----------- | ------ |
| AVAILABLE   | Green  |
| IN_USE      | Blue   |
| RESERVED    | Yellow |
| PAUSED      | Orange |
| MAINTENANCE | Red    |
| OFFLINE     | Grey   |

#### SeatCard Component (`components/SeatCard.tsx`)

- Displays: seat name, zone badge, status indicator, elapsed time (live), health badge (if `enable_health_monitoring` ON)
- Click actions vary by status:
  - AVAILABLE → Start Session modal
  - IN_USE → Session Detail panel (POS, Checkout, Commands)
  - RESERVED → Start Session or Cancel Reservation
  - MAINTENANCE → Clear Maintenance modal (Admin only)

#### Checkout Panel (`components/CheckoutPanel.tsx`)

- Displays invoice preview with live-computed time charge
- POS item list with quantities
- Package credit deduction (if applicable)
- Promotion discount line
- Total line
- Payment method selector
- Confirm Checkout button → `POST /api/sessions/{id}/checkout`

### 6.4 State Management

**React Query** manages all server state (seats, sessions, members, packages). It handles caching, background refetching, and optimistic updates.

**WebSocket events** trigger React Query cache invalidations:

```typescript
// hooks/useWebSocket.ts
ws.on("seat_updated", (payload) => {
  queryClient.setQueryData(["seats", payload.seat_id], payload);
});
ws.on("health_update", (payload) => {
  queryClient.setQueryData(["health", payload.seat_id], payload);
});
ws.on("announcement", (payload) => {
  showAnnouncementBanner(payload.message);
});
```

**Auth store** (Zustand or Context): holds the staff token, role, and current shift ID. Token is stored in memory only (not localStorage) and lost on page refresh — re-login required.

**Feature flags** are fetched once at login and stored in context. Components conditionally render based on flag state:

```typescript
const { flags } = useFeatureFlags()
{flags.enable_pos && <POSPanel sessionId={session.id} />}
```

### 6.5 Currency Display

All API responses carry paise integers. Display conversion occurs only in the UI:

```typescript
// utils/currency.ts
export const formatCurrency = (paise: number): string => {
  const rupees = paise / 100;
  return `Rs. ${rupees.toFixed(2)}`;
};
```

### 6.6 Mobile Responsive Layout

The dashboard uses TailwindCSS responsive utilities. On mobile (`sm:` breakpoint and below):

- The seat grid collapses to a single-column scrollable list
- The analytics sidebar is hidden behind a tab
- All interactive controls are touch-friendly (min 44px tap targets)

The owner mobile view is the same React app — no separate codebase. Feature flags suppress admin-only controls automatically.

---

## 7. Electron Agent Design

### 7.1 Process Architecture

The Electron agent uses standard main/renderer process separation. The **platform abstraction layer** isolates all OS-specific operations in the `platform/` module.

```
┌─────────────────────────────────────┐
│          Main Process (Node.js)     │
│  ├── ws/client.ts  (WS to server)   │
│  ├── health/collector.ts            │
│  ├── ipc/handlers.ts                │
│  ├── tray.ts                        │
│  └── platform/                      │ ← OS abstraction
│      ├── index.ts                   │   (exports unified PlatformService)
│      ├── windows.ts                 │
│      ├── macos.ts                   │
│      └── linux.ts                   │
│           ↕ IPC (contextBridge)     │
│  ┌──────────────────────────────┐   │
│  │     Renderer Process (React) │   │
│  │  ├── KioskOverlay.tsx        │   │
│  │  ├── SplashScreen.tsx        │   │
│  │  ├── CountdownOverlay.tsx    │   │
│  │  └── Announcement.tsx        │   │
│  └──────────────────────────────┘   │
└─────────────────────────────────────┘
```

### 7.2 Platform Abstraction Layer Interface

**Updated to reflect kiosk overlay approach** — no OS lock/unlock methods.

```typescript
// agent/src/platform/index.ts
export interface PlatformService {
  // Kiosk overlay management (primary access control)
  showKioskOverlay(content: OverlayContent): void;
  hideKioskOverlay(): void;
  updateTimer(timeString: string): void;

  // System operations
  restartPC(): Promise<void>;
  shutdownPC(): Promise<void>;
  captureScreenshot(): Promise<Buffer>; // Returns JPEG compressed, max 1280x720

  // Announcements
  sendAnnouncement(text: string, durationMs: number): void;

  // Auto-start
  enableAutoStart(): Promise<void>;
  disableAutoStart(): Promise<void>;
}

export interface OverlayContent {
  cafeLogo?: string; // base64 or file path
  cafeName: string;
  announcements: string[];
  callStaffEnabled: boolean;
  sessionActive: boolean;
  remainingTime?: string; // "HH:MM:SS" or "Unlimited"
  lowTimeWarning?: boolean;
}
```

Each OS module implements this interface using OS-specific APIs:

- **Windows:** Overlay uses Electron `BrowserWindow` with `kiosk: true`, `closable: false`; restart/shutdown via `shutdown`; screenshot via `desktopCapturer`; auto-start via registry.
- **macOS:** Overlay uses `kiosk: true`; restart/shutdown via `sudo shutdown`; screenshot via `desktopCapturer` (requires Screen Recording permission); auto-start via LaunchAgent plist.
- **Linux:** Overlay uses `kiosk: true`; restart/shutdown via `systemctl`/`shutdown`; screenshot via `desktopCapturer` (Wayland may require additional permissions); auto-start via `.desktop` file.

The correct module is selected at runtime via `process.platform`.

### 7.3 Kiosk Overlay Hardening

**FR-AGENT-002a and FR-AGENT-002b:** The agent's `BrowserWindow` SHALL be configured to prevent bypass:

```typescript
// agent/src/main/index.ts
import { app, BrowserWindow, globalShortcut } from "electron";

function createOverlayWindow(): BrowserWindow {
  const win = new BrowserWindow({
    fullscreen: true,
    kiosk: true, // Electron's native kiosk mode — blocks Cmd+Tab, Cmd+Space on macOS
    alwaysOnTop: true,
    frame: false,
    closable: false, // Prevents Alt+F4/Cmd+Q
    webPreferences: {
      devTools: false, // Disable F12 DevTools
      contextIsolation: true,
      sandbox: true,
      nodeIntegration: false,
    },
  });
  return win;
}

// Register global shortcuts to intercept before the OS handles them
app.on("browser-window-focus", () => {
  globalShortcut.registerAll(
    [
      "Alt+F4", // Windows/Linux close
      "CommandOrControl+W", // macOS/Windows close tab
      "CommandOrControl+Q", // macOS/Windows quit
      "F12", // DevTools
      "Alt+Shift+I", // DevTools (Chrome)
      "CommandOrControl+Shift+I", // DevTools (macOS/Windows)
      "CommandOrControl+P", // Print dialog (potential shell access on Windows)
    ],
    () => {}, // consume and discard
  );
});
```

**Known platform gaps (documented):**

- `Ctrl+Alt+Del` on Windows cannot be intercepted without a dedicated SAS filter driver or Windows Kiosk Mode assignment
- Wayland compositors on Linux may require additional configuration for `alwaysOnTop` to work reliably across all DEs — the agent SHALL gracefully degrade with a fallback to a maximised window

### 7.4 Startup Sequence

```
1. Agent process starts (via OS-specific auto-start)
2. Read server config from agent.config.json (SERVER_URL + AGENT_SECRET + SEAT_ID)
3. Connect WebSocket to ws://{SERVER_URL}/ws/agent/{seat_id}?secret={AGENT_SECRET}
4. On connection:
   a. Send REGISTER message: { seat_id, mac_address, hostname, hardware_specs, os_version, agent_version }
   b. Server validates agent_secret; responds with { seat_id, status, session_state? }
5. Begin health metric collection loop (every 60s)
6. Show system tray icon (grey = no session)
7. Listen for commands from server
```

### 7.5 Session Start Sequence (Agent Side)

Server sends: `{ command: "HIDE_OVERLAY", session: { id, duration_minutes?, started_at } }`

```
Agent:
1. Receive HIDE_OVERLAY command
2. Cache session locally in SQLite: { session_id, started_at, duration_minutes, last_sync_at }
3. Hide kiosk overlay using platform.hideOverlay()
4. Show SplashScreen (5 seconds) as a temporary overlay window:
   - Cafe logo and branding
   - Session info (seat name, duration, package info)
   - Menu items (from server)
   - "Call Staff" button
5. After 5s: close splash, show tray icon (green, shows elapsed time)
6. Start local countdown timer
7. At 5 minutes remaining: show CountdownOverlay with warning
```

### 7.6 Session End Sequence (Agent Side)

Server sends: `{ command: "SHOW_OVERLAY", session: { id } }`

```
Agent:
1. Receive SHOW_OVERLAY command
2. Show kiosk overlay using platform.showKioskOverlay()
3. Display "Session ended. Thank you!" message on overlay
4. Clear local session cache (set status to COMPLETED in SQLite)
5. Tray icon returns to grey
```

### 7.7 LAN Resilience

If the WebSocket connection to the server drops mid-session:

```typescript
// ws/client.ts
onDisconnect():
  1. Log disconnect time to SQLite
  2. Continue local timer from cached started_at
  3. Begin reconnection loop with exponential backoff:
     Attempt 1: wait 2s, Attempt 2: wait 4s, ... cap at 60s + random jitter
  4. On reconnect: send SYNC message:
     { session_id, local_elapsed_seconds, disconnect_at, reconnect_at }
  5. Server reconciles and corrects its record if needed

// session_store.ts (SQLite persistence)
interface LocalSessionCache {
  session_id: string;
  started_at: string;      // ISO timestamp
  last_sync_at: string;    // ISO timestamp
  local_elapsed_seconds: number;
  disconnect_count: number;
  status: 'ACTIVE' | 'PAUSED' | 'COMPLETED';
  updated_at: string;      // ISO timestamp
}
```

The agent writes to SQLite:

- Every 10 seconds during an active session
- On every pause/resume
- On every reconnect
- On session end

### 7.8 Health Metrics Collection

```typescript
// health/collector.ts  (using systeminformation library, cross‑platform)
setInterval(async () => {
  const cpu = await si.currentLoad();
  const mem = await si.mem();
  const temp = await si.cpuTemperature();
  const disk = await si.fsSize();

  ws.send({
    type: "HEALTH_METRICS",
    seat_id: registeredSeatId,
    cpu_percent: cpu.currentLoad,
    ram_percent: (mem.used / mem.total) * 100,
    cpu_temp_celsius: temp.main,
    disk_free_gb: disk[0].available / 1e9,
    collected_at: new Date().toISOString(),
  });
}, 60_000);
```

### 7.9 Remote Commands

| Command           | Agent Action                                                                                                                       |
| ----------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| `HIDE_OVERLAY`    | Hide kiosk overlay using `platform.hideKioskOverlay()` — allows desktop access                                                     |
| `SHOW_OVERLAY`    | Show kiosk overlay using `platform.showKioskOverlay()` — blocks desktop access                                                     |
| `SHOW_MESSAGE`    | Show `<Announcement>` overlay on renderer with message text and duration (common UI)                                               |
| `RESTART`         | Execute `platform.restartPC()` — `shutdown /r /t 10` on Windows, `sudo shutdown -r now` on macOS, `sudo systemctl reboot` on Linux |
| `SHUTDOWN`        | Execute `platform.shutdownPC()` — similarly                                                                                        |
| `TAKE_SCREENSHOT` | Capture screen via `desktopCapturer`, compress to JPEG 80% quality, scale to max 1280×720, return base64                           |

### 7.10 Screenshot Constraints (FR-AGENT-006a)

The `TAKE_SCREENSHOT` command SHALL:

1. Capture screen via `desktopCapturer`
2. Compress to **JPEG at 80% quality** (not PNG)
3. **Scale down to a maximum of 1280×720** before encoding
4. Return base64-encoded image
5. Maximum WebSocket message size: **5 MB** per frame

```typescript
// ipc/handlers.ts
async function handleScreenshot(): Promise<string> {
  const sources = await desktopCapturer.getSources({ types: ["screen"] });
  const image = sources[0].thumbnail;
  const resized = image.resize({ width: 1280, height: 720 });
  return resized.toJPEG(80).toString("base64");
}
```

### 7.11 Agent Configuration File

```json
{
  "server_url": "ws://192.168.1.100:8000",
  "seat_id": "seat_001",
  "agent_secret": "c9a1b2c3d4e5f6...",
  "reconnect_max_seconds": 60,
  "health_interval_seconds": 60
}
```

`agent_secret` is generated by the setup wizard using `secrets.token_hex(32)` and stored in both `arcade.config.json` (server) and the agent's `agent.config.json` during deployment. The agent uses this secret to authenticate with the server on the REGISTER message and on every reconnection.

`agent.config.json` SHALL be treated as a secret file — file permissions SHALL be set to owner-read-only on Linux and macOS (`chmod 600`).

---

## 8. Launcher Design

### 8.1 Responsibilities

The Launcher (`launcher.py`) is the only entry point for starting the Arcade server on the counter PC. It is a Tkinter GUI that:

1. On every start, runs the license check (see §16) before anything else
2. If the license check fails: shows the License Activation screen and stops here
3. If the license check passes and `arcade.config.json` does not exist: runs the setup wizard
4. If the license check passes and `arcade.config.json` exists: starts the FastAPI server as a subprocess
5. Displays live server logs in a scrollable text area
6. Shows a status indicator (Activation Required / Starting / Running / Stopped / Error)
7. Provides Start/Stop buttons (enabled only once licensed)
8. Prompts for confirmation if the user attempts to close the window while the server is running

**Cross‑platform note:** Tkinter is included with Python on all OSes. The Launcher uses `os.path.join` and `subprocess` appropriately. Hardware fingerprinting (see §16) uses `py-machineid` as the primary source (no admin privileges required).

### 8.2 Launcher Startup Flow

```
Launcher starts
  │
  ▼
licensing.verify.check_license()   ← see §16.6 (uses py-machineid, no admin)
  │
  ├── FAIL (no license.key / bad signature / hardware mismatch / expired trial)
  │     │
  │     ▼
  │   Show License Activation screen (§16.7)
  │   Block setup wizard and server start until license check passes
  │
  └── PASS
        │
        ▼
      arcade.config.json exists?
        │
        ├── NO  → Run setup wizard (§8.3)
        └── YES → Start FastAPI server subprocess (§8.4)
```

This ordering means the license check is a precondition for _every_ launch, not just the first — re-running the Launcher with a removed or corrupted `license.key` always re-enters the Activation screen rather than starting the server (FR-SYS-008, FR-LIC-013).

### 8.3 Setup Wizard Flow

```
Step 1: Welcome screen
Step 2: Enter cafe name
Step 3: Enter server IP (auto-detects local IP as default) + port (default: 8000)
Step 4: Set Admin PIN (4–6 digits, enter twice)
Step 5: Set Cashier PIN (4–6 digits, enter twice)
Step 6: Generate agent secrets for each seat:
        - For each seat (e.g., "PC-01" to "PC-N"): generate unique agent_secret with secrets.token_hex(32)
        - Write agent.config.json for each seat (to be deployed)
Step 7: Confirm and save → writes arcade.config.json
Step 8: Offer to start the server immediately
```

The setup wizard is only reachable after §8.2's license check passes (FR-SYS-001).

### 8.4 Server Process Management

```python
# launcher.py (simplified)
proc = subprocess.Popen(
    ["uvicorn", "backend.main:app", "--host", host, "--port", str(port)],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True
)

# Stream output to Tkinter text widget in a background thread
threading.Thread(target=stream_logs, args=(proc, log_widget), daemon=True).start()
```

On Stop: sends `SIGTERM` to the subprocess, waits up to 10 seconds for graceful shutdown, then `SIGKILL` if needed.

On Window Close: if the server is running, show a confirmation dialog: "The Arcade server is still running. Closing the Launcher will stop the server. Are you sure?" If confirmed, terminate the server gracefully and exit. If cancelled, keep the Launcher open.

---

## 9. Real-time Communication Design

### 9.1 WebSocket Endpoints

| Endpoint              | Clients          | Direction       | Events                                                         |
| --------------------- | ---------------- | --------------- | -------------------------------------------------------------- |
| `/ws/dashboard`       | React dashboards | Server → Client | `seat_updated`, `health_update`, `announcement`, `alert`       |
| `/ws/agent/{seat_id}` | Electron agents  | Bidirectional   | Server → Agent: commands. Agent → Server: health metrics, sync |

**Agent authentication:** The agent must include its `agent_secret` as a query parameter: `ws://{server}/ws/agent/{seat_id}?secret={AGENT_SECRET}`. The server validates the secret on every REGISTER message and rejects connections with invalid or missing secrets.

### 9.2 Message Envelope

All WebSocket messages use a standard JSON envelope:

```json
{
  "type": "EVENT_TYPE",
  "payload": { ... },
  "timestamp": "2026-06-01T10:00:00Z"
}
```

### 9.3 Event Catalogue

**Server → Dashboard:**

| Event           | Payload                             | Trigger                              |
| --------------- | ----------------------------------- | ------------------------------------ |
| `seat_updated`  | Full seat object                    | Any seat status change               |
| `health_update` | `{ seat_id, cpu, ram, temp, disk }` | Agent health report received         |
| `announcement`  | `{ message, duration_seconds }`     | Staff sends announcement             |
| `alert`         | `{ type, seat_id, message }`        | Health threshold exceeded, low stock |

**Server → Agent:**

| Event             | Payload                                         |
| ----------------- | ----------------------------------------------- |
| `HIDE_OVERLAY`    | `{ session_id, started_at, duration_minutes? }` |
| `SHOW_OVERLAY`    | `{ session_id }`                                |
| `SHOW_MESSAGE`    | `{ text, duration_seconds }`                    |
| `RESTART`         | `{ delay_seconds: 10 }`                         |
| `SHUTDOWN`        | `{ delay_seconds: 10 }`                         |
| `TAKE_SCREENSHOT` | `{}`                                            |

**Agent → Server:**

| Event               | Payload                                                                            |
| ------------------- | ---------------------------------------------------------------------------------- |
| `REGISTER`          | `{ seat_id, mac_address, hostname, cpu_model, ram_gb, os_version, agent_version }` |
| `HEALTH_METRICS`    | `{ cpu_percent, ram_percent, cpu_temp_celsius, disk_free_gb, collected_at }`       |
| `SYNC`              | `{ session_id, local_elapsed_seconds, disconnect_at, reconnect_at }`               |
| `SCREENSHOT_RESULT` | `{ seat_id, image_base64, captured_at }`                                           |

### 9.4 Connection Lifecycle

```
Agent connects to /ws/agent/{seat_id}?secret={AGENT_SECRET}
  └── Server validates secret; rejects if invalid
  └── Server registers in agent_connections[seat_id]
  └── Server marks seat as ONLINE (if was OFFLINE)
  └── Server broadcasts seat_updated to dashboards
  └── If session was active: server re-sends current HIDE_OVERLAY state

Agent disconnects
  └── Server detects via missed heartbeat (30s timeout)
  └── Server marks seat as OFFLINE
  └── Server broadcasts seat_updated to dashboards
  └── Server removes from agent_connections

Agent reconnects
  └── Resume from step 1 (with secret validation)
  └── If session was active: server re-sends current HIDE_OVERLAY state
```

### 9.5 Heartbeat Design

```python
# core/ws_manager.py
HEARTBEAT_INTERVAL = 30  # seconds
HEARTBEAT_TIMEOUT = 10   # seconds to wait for pong

async def heartbeat_loop():
    while True:
        await asyncio.sleep(HEARTBEAT_INTERVAL)
        for seat_id, ws in list(agent_connections.items()):
            try:
                await ws.send_json({"type": "PING"})
                # Expect PONG within 10s (enforced by receive timeout)
            except Exception:
                await unregister_agent(seat_id)
```

---

## 10. Billing Engine Design

### 10.1 Overview

The billing engine is implemented entirely in `backend/services/billing_service.py`. It performs two operations:

1. **`resolve_rate(seat, member, now)`** — called at session start to determine and lock the applicable rate
2. **`calculate_invoice(session, pos_items)`** — called at checkout to compute the final invoice

All arithmetic is integer arithmetic in paise throughout.

### 10.2 Rate Resolution (`resolve_rate`)

```
resolve_rate(seat, member, now) → LockedRate

1. Load zone for seat → base rate (per_minute_paise or per_hour_paise)
2. Check peak/off-peak schedule for current time and day:
   - If peak schedule matches → use peak_rate
   - Else → use standard rate
3. Check device-type override:
   - Console seat → use console_rate if configured
4. Result so far: effective_rate_paise (per minute)

5. Check active promotions (ordered by priority):
   - HAPPY_HOUR: active_from_hour ≤ now.hour < active_to_hour and today in active_days
   - FLASH: valid_from ≤ now ≤ valid_until and matches zone
   - FIRST_VISIT: member.total_visits == 0
   - BIRTHDAY: member.birth_month == now.month
   - GROUP: session is part of group start with ≥ min_group_size seats
   → Select highest-value applicable promotion (one only)

6. Return LockedRate:
   {
     rate_paise: int,              # per-minute rate after peak/device adjustment
     pricing_model: Enum,          # PER_MINUTE | FLAT_HOURLY | TIME_BLOCK
     block_minutes: int | None,    # for TIME_BLOCK
     promotion_id: str | None,
     discount_type: Enum | None,   # PERCENTAGE | FIXED_PAISE | BONUS_MINUTES
     discount_value: int | None,
   }
```

### 10.3 Invoice Calculation (`calculate_invoice`)

```
calculate_invoice(session, pos_items) → InvoiceLineItems

1. Compute billable_seconds:
   elapsed = (now - session.started_at).total_seconds()
   billable_seconds = elapsed - session.total_paused_seconds

2. Compute raw_time_charge based on pricing_model:
   PER_MINUTE:
     minutes = ceil(billable_seconds / 60)
     raw_time_charge = minutes × session.locked_rate_paise

   FLAT_HOURLY:
     hours = ceil(billable_seconds / 3600)
     raw_time_charge = hours × session.locked_rate_paise × 60

   TIME_BLOCK:
     blocks = ceil(billable_seconds / (session.block_minutes × 60))
     raw_time_charge = blocks × session.locked_rate_paise × session.block_minutes

3. Apply package entitlement (if linked):
   package = load active entitlement
   package_minutes_available = min(package.remaining_minutes, ceil(billable_seconds/60))
   package_credit_paise = package_minutes_available × session.locked_rate_paise
   overflow_minutes = ceil(billable_seconds/60) - package_minutes_available
   time_charge_after_package = overflow_minutes × session.locked_rate_paise
   # Deduct from package atomically:
   UPDATE member_package_entitlements
   SET remaining_minutes = remaining_minutes - package_minutes_available
   WHERE id = package_id AND remaining_minutes >= package_minutes_available

4. Apply promotion discount (if linked):
   if discount_type == PERCENTAGE:
     discount_paise = (time_charge_after_package × discount_value) // 100
   elif discount_type == FIXED_PAISE:
     discount_paise = min(discount_value, time_charge_after_package)
   elif discount_type == BONUS_MINUTES:
     bonus_credit = discount_value × session.locked_rate_paise
     discount_paise = min(bonus_credit, time_charge_after_package)
   time_charge_final = time_charge_after_package - discount_paise

5. Apply member tier discount (if member):
   tier_discount_pct = { BRONZE: 0, SILVER: 5, GOLD: 10 }[member.tier]
   member_discount = (time_charge_final × tier_discount_pct) // 100
   time_charge_final -= member_discount

6. Compute POS total:
   pos_total_paise = sum(item.unit_price_paise × item.quantity for item in pos_items)

7. Return InvoiceLineItems:
   {
     time_charge_paise: time_charge_final,
     package_credit_used_paise: package_credit_paise,
     discount_paise: discount_paise + member_discount,
     pos_items: [...],
     pos_total_paise: pos_total_paise,
     total_paise: time_charge_final + pos_total_paise
   }
```

### 10.4 Billing Precision Rules

- All intermediate values remain integers in paise
- `ceil()` (not `floor()` or `round()`) is used for minutes and blocks — the customer is billed for any started unit
- Division that would produce a fraction is deferred until the final step using integer `//`
- The total is always: `time_charge_final + pos_total_paise` — never recomputed from parts after storage
- Package updates use atomic `UPDATE ... WHERE remaining_minutes >= amount` to prevent race conditions

---

## 11. Security Design

### 11.1 Authentication Flow

```
Staff enters PIN on dashboard login screen
  │
  ▼
POST /api/auth/login { pin: "1234" }
  │
  ├── Load all active staff records
  ├── For each: argon2id.verify(staff.pin_hash, pin)  (Argon2id, not bcrypt)
  ├── If match found:
  │   ├── Reset failed_attempts to 0
  │   ├── Generate JWT: { staff_id, role, shift_id, token_version, exp: now+60m }
  │   └── Return { token, role, staff_name }
  └── If no match:
      ├── Increment failed_attempts for the specific Staff ID
      ├── If failed_attempts >= 5:
      │   └── Set lockout_until = now + 60 seconds
      └── Return 401
```

### 11.2 Token Validation with Revocation

Every protected endpoint uses a FastAPI dependency that validates both the JWT signature **and** the `token_version` claim against the database:

```python
# api/deps.py
async def get_current_staff(
    token: str = Header(...),
    db: AsyncSession = Depends(get_db)
) -> StaffSchema:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    except jwt.InvalidTokenError:
        raise HTTPException(401, "Invalid token")

    staff = await staff_repo.get_by_id(db, payload["staff_id"])
    if not staff or not staff.is_active:
        raise HTTPException(401, "Staff not found or inactive")

    # Token revocation check
    if payload.get("token_version", 0) != staff.token_version:
        raise HTTPException(401, "Token invalidated — PIN changed or account deactivated")

    return staff

async def require_admin(staff = Depends(get_current_staff)):
    if staff.role != Role.ADMIN:
        raise HTTPException(403, "Admin role required")
    return staff
```

**Token revocation triggers:**

- `POST /api/staff/{id}/change-pin` — increments `token_version`
- `POST /api/staff/{id}/deactivate` — increments `token_version` (in addition to setting `is_active=False`)

### 11.3 PIN Storage (Argon2id)

```python
# core/security.py
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError

ph = PasswordHasher(
    time_cost=2,        # Number of iterations
    memory_cost=102400, # 100 MB
    parallelism=8,
    hash_len=32,
    salt_len=16,
)

def hash_pin(pin: str) -> str:
    return ph.hash(pin)

def verify_pin(pin: str, hashed: str) -> bool:
    try:
        ph.verify(hashed, pin)
        return True
    except VerificationError:
        return False
```

PINs are never logged, never returned in API responses, and stored only as Argon2id hashes. **No bcrypt fallback shall be implemented** — Argon2id is the OWASP-recommended algorithm for new systems.

### 11.4 Agent Authentication

Agent WebSocket connections are authenticated by **agent_secret** — a randomly generated token created during the setup wizard and embedded in `agent.config.json`.

```python
# core/ws_manager.py
AGENT_SECRETS: dict[str, str]  # seat_id → agent_secret (loaded from arcade.config.json)

async def handle_agent_connection(seat_id: str, secret: str, ws: WebSocket):
    expected = AGENT_SECRETS.get(seat_id)
    if not expected or secret != expected:
        await ws.close(code=4001, reason="Invalid agent secret")
        return
    # Continue with registration...
```

The agent_secret is:

- Generated using `secrets.token_hex(32)` during setup
- Stored in `arcade.config.json` on the server
- Embedded in each agent's `agent.config.json` during deployment
- Validated on every REGISTER message and on every reconnection
- Never hardcoded in the source repository

`agent.config.json` SHALL be treated as a secret file — file permissions SHALL be set to owner-read-only on Linux and macOS (`chmod 600`).

### 11.5 Screenshot Security

- Screenshot command is `ADMIN` role only (enforced at API layer)
- Screenshot images are transmitted over the local WebSocket connection only
- Images are NOT persisted to disk — returned in-memory to the requesting dashboard session only
- Each screenshot request is logged in the audit log with: staff ID, seat ID, timestamp
- **Screenshot payload constraints:** JPEG at 80% quality, max 1280×720, max message size 5 MB
- **Rate limiting:** At most one in-flight screenshot per seat

### 11.6 Audit Log Immutability

The audit log table has no `UPDATE` or `DELETE` grants at the application level. The repository layer exposes only `create` and `list` methods — no `update` or `delete`. This is enforced in code, not at the SQLite level (SQLite does not support column-level grants). Direct database access is not protected by the application.

---

## 12. Integration Design

### 12.1 Wake-on-LAN

```python
# services/wol_service.py
import socket
import struct

def send_magic_packet(mac_address: str, broadcast: str = "255.255.255.255", port: int = 9):
    mac_bytes = bytes.fromhex(mac_address.replace(":", "").replace("-", ""))
    magic_packet = b'\xff' * 6 + mac_bytes * 16
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.sendto(magic_packet, (broadcast, port))

def boot_all_seats(db):
    seats = seat_repo.list_with_mac(db)
    for seat in seats:
        if seat.mac_address:
            send_magic_packet(seat.mac_address)
```

Called on server startup and available as an individual action from the dashboard. WoL works identically on all OSes.

### 12.2 Tuya Smart Plug Integration

```python
# services/tuya_service.py
# Uses TinyTuya library for local LAN communication

class TuyaService:
    def __init__(self):
        # Uses local_key, device_id, ip_address from settings
        # No cloud credentials needed after initial pairing
        pass

    def power_on(self, device_id: str):
        # Send local command via TinyTuya
        pass

    def power_off(self, device_id: str):
        # Send local command via TinyTuya
        pass
```

Tuya calls are made asynchronously and do not block session operations. Failures are logged but do not prevent the session from proceeding. Tuya credentials (device_id, local_key, ip_address, protocol_version) are stored in Settings.

### 12.3 Thermal Printing

```python
# services/print_service.py
from escpos.printer import Usb, Network

def print_receipt(invoice: InvoiceResponse, printer_config: dict):
    p = get_printer(printer_config)   # USB or Network based on config

    p.set(align="center", text_type="B", width=2, height=2)
    p.text(f"{cafe_name}\n")
    p.set(align="left", text_type="NORMAL", width=1, height=1)
    p.text(f"Seat: {invoice.seat_name}\n")
    p.text(f"Date: {invoice.created_at}\n")
    p.text(f"Duration: {format_duration(invoice.duration_seconds)}\n")
    p.text("-" * 32 + "\n")

    for item in invoice.pos_items:
        p.text(f"{item.name} x{item.quantity}  {format_currency(item.total_paise)}\n")

    p.text("-" * 32 + "\n")
    p.text(f"Time charge:  {format_currency(invoice.time_charge_paise)}\n")
    if invoice.discount_paise > 0:
        p.text(f"Discount:    -{format_currency(invoice.discount_paise)}\n")
    p.set(text_type="B")
    p.text(f"TOTAL:        {format_currency(invoice.total_paise)}\n")
    p.set(text_type="NORMAL")
    p.text(f"Paid by: {invoice.payment_method}\n")
    p.cut()
```

PDF fallback: the dashboard exposes a `/api/invoices/{id}/pdf` endpoint that returns a browser-printable HTML receipt. Staff trigger `window.print()` for PDF or paper output.

### 12.4 Nightly Backup (APScheduler)

**Updated to use APScheduler's `AsyncIOScheduler`** instead of the blocking `python-schedule` library.

```python
# services/backup_service.py
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import shutil, os
from datetime import datetime, timedelta

scheduler = AsyncIOScheduler()

async def run_backup(db_path: str, backup_dir: str, retain_days: int = 30):
    os.makedirs(backup_dir, exist_ok=True)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    dest = os.path.join(backup_dir, f"arcade_{timestamp}.db")
    shutil.copy2(db_path, dest)

    # Prune old backups
    backups = sorted(Path(backup_dir).glob("arcade_*.db"))
    for old in backups[:-retain_days]:
        old.unlink()

# Scheduled at server startup (within lifespan)
scheduler.add_job(
    run_backup,
    "cron",
    hour=3,
    minute=0,
    args=[db_path, backup_dir, retain_days],
)
scheduler.start()

# On shutdown (within lifespan): scheduler.shutdown()
```

**Why APScheduler over python-schedule:**

- `python-schedule` is single-threaded and blocking by design, requiring a separate daemon thread
- `AsyncIOScheduler` integrates natively with FastAPI's event loop
- Handles exceptions gracefully without silently dying
- Supports persistence across restarts (optional, not required for V1)

---

## 13. Error Handling and Resilience

### 13.1 HTTP Error Responses

All errors return a standard JSON envelope:

```json
{
  "error": "SESSION_CONFLICT",
  "message": "Seat PC-04 already has an active session.",
  "detail": { "seat_id": "abc123", "session_id": "xyz789" }
}
```

Standard error codes used across routers:

| Code                   | HTTP | Meaning                                           |
| ---------------------- | ---- | ------------------------------------------------- |
| `SEAT_UNAVAILABLE`     | 409  | Seat is not in AVAILABLE status                   |
| `SESSION_NOT_FOUND`    | 404  | Session ID does not exist                         |
| `MEMBER_NOT_FOUND`     | 404  | Member ID does not exist                          |
| `FEATURE_DISABLED`     | 503  | Feature flag is OFF                               |
| `INSUFFICIENT_BALANCE` | 402  | Wallet has insufficient funds                     |
| `VOUCHER_INVALID`      | 400  | Code not found, already used, or expired          |
| `AUTH_FAILED`          | 401  | Wrong PIN                                         |
| `AUTH_LOCKED`          | 423  | Too many failed attempts                          |
| `AUTH_TOKEN_REVOKED`   | 401  | Token invalidated (PIN change or deactivation)    |
| `FORBIDDEN`            | 403  | Role does not have permission                     |
| `AGENT_OFFLINE`        | 503  | Agent not connected — command cannot be delivered |

### 13.2 LAN Interruption Handling

| Scenario                    | Server Behaviour                                                                                            | Agent Behaviour                                                  |
| --------------------------- | ----------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------- |
| Agent drops mid-session     | Marks seat OFFLINE after heartbeat timeout. Session stays ACTIVE in DB.                                     | Keeps local timer in SQLite. Begins reconnect loop with backoff. |
| Agent reconnects            | Receives SYNC message. Reconciles elapsed time. Sends current session state to agent.                       | Sends SYNC with local elapsed time. Resumes normal operation.    |
| Server restarts mid-session | On restart, loads all ACTIVE sessions from DB. When agents reconnect, reconciles via SYNC.                  | Agent reconnects, sends SYNC.                                    |
| Tuya API unavailable        | Console session starts/ends normally. Tuya failure logged as WARNING. Staff manually power-cycles the plug. | N/A                                                              |

### 13.3 Server Session Recovery

```python
# services/session_service.py
async def recover_active_sessions(db: AsyncSession):
    """Called during server startup to prepare for agent reconnection."""
    active_sessions = await session_repo.list_active(db)
    for session in active_sessions:
        # Mark seat as IN_USE (agents will re-sync)
        await seat_repo.update_status(db, session.seat_id, SeatStatus.IN_USE)
        # Broadcast seat status to dashboard
        ws_manager.broadcast_to_dashboards("seat_updated", seat)
```

### 13.4 Feature Flag Middleware

```python
# services base pattern
def ensure_feature_enabled(flag_name: str, flags: FeatureFlags):
    if not getattr(flags, flag_name):
        raise HTTPException(
            status_code=503,
            detail={"error": "FEATURE_DISABLED", "flag": flag_name}
        )
```

All service methods that handle optional features call this check first. Existing data is preserved — the flag gates the UI and API, not the stored records.

### 13.5 Graceful Shutdown

**Updated to use `lifespan` context manager** (FastAPI 0.93+), replacing the deprecated `@app.on_event` decorator.

```python
# backend/main.py
from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- STARTUP ---
    await init_db()
    scheduler.start()
    # ... other startup tasks
    yield
    # --- SHUTDOWN ---
    await ws_manager.close_all()
    scheduler.shutdown()
    await engine.dispose()

app = FastAPI(lifespan=lifespan)
```

The Launcher sends `SIGTERM` and waits up to 10 seconds for the process to exit before forcing termination.

---

## 14. Configuration Design

### 14.1 File-based Config (`arcade.config.json`)

Created by the setup wizard. Read-only at runtime — changes require re-running the wizard or manual edit followed by server restart.

Note: `license.key` is a separate file from `arcade.config.json`, checked earlier in the boot sequence and owned by the licensing subsystem (§16), not by `core.config`. It exists before the wizard ever runs and is never written to or parsed by the FastAPI application itself — only by the Launcher.

```json
{
  "cafe_name": "Arcade",
  "host": "192.168.1.100",
  "port": 8000,
  "db_path": "arcade.db",
  "backup_dir": "backups/",
  "backup_retain_days": 30,
  "backup_time": "03:00",
  "admin_pin_hash": "<argon2id_hash>",
  "cashier_pin_hash": "<argon2id_hash>",
  "jwt_secret": "<random_256bit_hex>",
  "agent_secrets": {
    "seat_001": "c9a1b2c3d4e5f6...",
    "seat_002": "a1b2c3d4e5f6..."
  },
  "tuya_devices": [
    {
      "seat_id": "console_01",
      "device_id": "abc123",
      "local_key": "key456",
      "ip_address": "192.168.1.50",
      "protocol_version": "3.3"
    }
  ],
  "printer_type": "usb",
  "printer_usb_vendor": "0x04b8",
  "printer_usb_product": "0x0202"
}
```

`agent_secrets` is a mapping of `seat_id` → `agent_secret` (hex string, 32 bytes). Generated during setup wizard; used to authenticate agent WebSocket connections.

### 14.2 Database-stored Settings

All operational settings (pricing, feature flags, menu, zones, promotions) are stored in the `settings` table and editable from the dashboard Settings page without a server restart.

```
Key                          → Value (JSON)
---------------------------------------------------------------------------
enable_members               → true
enable_packages              → true
enable_pos                   → true
enable_inventory             → false
enable_reservations          → true
enable_vouchers              → false
enable_tournaments           → false
enable_expense_tracking      → false
enable_health_monitoring     → true
require_member_for_session   → false
loyalty_silver_threshold_pts → 500
loyalty_gold_threshold_pts   → 2000
loyalty_silver_discount_pct  → 5
loyalty_gold_discount_pct    → 10
low_time_warning_minutes     → 5
backup_time                  → "03:00"
```

### 14.3 Feature Flag Loading

Feature flags are loaded from the database at startup and cached in memory. The `GET /api/settings` endpoint returns the current flag state. The `PATCH /api/settings` endpoint updates flags and reloads the in-memory cache.

---

## 15. Deployment Design

### 15.1 Server Deployment (Counter PC)

**Cross‑platform prerequisites:** Python 3.11+, Node.js 20+, Git (or packaged build).

#### Windows

```
1. git clone https://github.com/neurotech/arcade.git
2. pip install -r requirements.txt
3. cd frontend && npm install && npm run build && cd ..
4. python launcher.py     # Shows License Activation screen on first launch
5. Add launcher.py shortcut to Windows Startup folder
   (or register via Task Scheduler for pre-login startup)
```

#### macOS / Linux

```
1. Same steps 1-3
2. python launcher.py
3. Auto-start:
   - macOS: create a LaunchAgent plist in ~/Library/LaunchAgents/
   - Linux: create a systemd user service or add .desktop to ~/.config/autostart/
```

The frontend is built to `frontend/dist/` and served as static files by the FastAPI app at `/`. No separate web server is needed.

### 15.2 Client Agent Deployment

```
On development machine (any OS):
1. cd agent && npm install && npm run build
   → Produces platform-specific distributables in agent/dist/:
     - Windows: .exe (NSIS installer)
     - macOS: .dmg and .app bundle
     - Linux: AppImage, .deb, or .rpm (configurable)

Per client PC:
1. Copy the appropriate distributable to the client machine
2. Install or extract it
3. Edit agent.config.json:
   - Set server_url to the counter PC's IP:port
   - Set seat_id to the seat identifier (e.g., "seat_001")
   - Set agent_secret to the value generated by setup wizard (unique per seat)
4. Enable auto-start:
   - Windows: copy shortcut to Startup folder
   - macOS: drag app to Applications, add Login Item via System Preferences
   - Linux: create .desktop in ~/.config/autostart/
5. Set file permissions on agent.config.json (Linux/macOS): chmod 600
```

### 15.3 Network Requirements

| Requirement     | Detail                                                                                                                                                                      |
| --------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Server PC       | Static local IP (e.g., 192.168.1.100) — set via router DHCP reservation                                                                                                     |
| Client PCs      | Wired ethernet, Wake-on-LAN enabled in BIOS (works on all OSes)                                                                                                             |
| Firewall        | Open TCP port 8000 on server PC for inbound LAN connections                                                                                                                 |
| UDP broadcast   | Port 9 open for Wake-on-LAN magic packets                                                                                                                                   |
| Internet access | Required for Tuya API only during initial pairing. License activation and ongoing verification are fully offline (see §16) — no internet needed for licensing at any point. |

### 15.4 First-run Checklist

- [ ] Hardware ID generated and sent to Neurotech Biratnagar; `license.key` received and placed in the app folder
- [ ] License Activation screen confirms a valid, matching license
- [ ] Setup wizard completed — `arcade.config.json` created with `agent_secrets`
- [ ] Frontend built — `frontend/dist/` populated
- [ ] Server starts and `/health` returns 200
- [ ] At least one zone configured in Settings
- [ ] At least one seat registered (agent connects with valid `agent_secret`)
- [ ] Thermal printer connected and tested (or PDF fallback confirmed)
- [ ] Tuya credentials entered (if consoles present)
- [ ] Feature flags configured for this cafe's needs
- [ ] Admin PIN and Cashier PIN tested
- [ ] Launcher auto-start configured per OS
- [ ] Agent auto-start configured on all client PCs

---

## 16. Licensing and Activation Design

This section details the design referenced from §8 (Launcher) and satisfies FR-LIC-001 through FR-LIC-014 in the SRS. It is a self-contained subsystem: the rest of the application (backend, frontend, agent) has no awareness of licensing beyond reading the cached `license_status` row for display (§5.1) and exposing it at `GET /api/settings/license`.

### 16.1 Design Goals

- **Zero ongoing network dependency.** Verification must work forever with no internet, no server, no phone-home call — consistent with Arcade's core "owns the box" positioning.
- **Hard to forge, easy to verify.** Asymmetric cryptography means anyone can verify a license (they have the public key, embedded in the binary) but only Neurotech Biratnagar can issue one (they alone hold the private key).
- **Hard to casually copy.** Binding to a Hardware ID means a `license.key` copied to a different PC fails verification, without requiring a server-side seat-tracking system.
- **Fails safe, not silent.** An invalid, missing, or mismatched license blocks the setup wizard and server start cleanly — it never partially starts the system or corrupts existing data.

### 16.2 Cryptographic Scheme

Arcade uses **Ed25519** (RFC 8032) for license signing and verification:

- One Ed25519 keypair exists for the entire product line, generated once and stored only on Seller internal keygen machine.
- The **private key** (`tools/keygen/private_key.pem`) signs every issued license. It is never committed to the `arcade` repository, never bundled into any build artifact, and never present on a customer's machine.
- The **public key** is a hardcoded constant in `backend/licensing/public_key.py`, compiled into every distributed copy of Arcade. It can verify signatures but cannot create them.

```python
# backend/licensing/public_key.py
# Public key only. Never add a private key to this file or this repository.
ARCADE_PUBLIC_KEY_HEX = "c9a1...<32-byte Ed25519 public key, hex-encoded>...4f3e"
```

### 16.3 Hardware Fingerprinting

**Updated to use `py-machineid` as the primary source** (no admin privileges required on any OS), with fallbacks only if `py-machineid` returns an empty result.

```python
# backend/licensing/fingerprint.py
import hashlib
import machineid  # py-machineid
import uuid

def get_hardware_id() -> str:
    # Primary: py-machineid (no admin, cross-platform)
    machine_id = machineid.hardware_id()
    if machine_id:
        raw = f"py-machineid:{machine_id}"
    else:
        # Fallback: combine available OS-specific identifiers
        fallback_parts = []
        if platform.system() == "Windows":
            fallback_parts.append(_wmic("baseboard", "serialnumber"))
            fallback_parts.append(_wmic("diskdrive", "serialnumber", index=0))
        elif platform.system() == "Darwin":
            fallback_parts.append(_osx_system_profiler("SPHardwareDataType", "Serial Number"))
            fallback_parts.append(_osx_disk_serial())
        else:  # Linux
            fallback_parts.append(_linux_dmidecode("baseboard", "Serial Number"))
            fallback_parts.append(_linux_disk_serial())
            fallback_parts.append(_linux_machine_id())
        raw = "|".join(p for p in fallback_parts if p)

    return hashlib.sha256(raw.encode()).hexdigest()[:32]  # Displayed as the Hardware ID
```

**Key points:**

- `py-machineid` is the primary source — it works on all three OSes without admin privileges
- Fallback OS-specific commands are only used if `py-machineid` returns empty
- Missing individual identifiers do not fail activation — the system uses whatever is available
- The result is hashed to produce a consistent 32-character Hardware ID

### 16.4 License File Format

`license.key` is a base64-encoded JSON payload plus signature, generated entirely offline:

```json
{
  "payload": {
    "cafe_name": "Galaxy Gaming Lounge",
    "hardware_id": "a1b2c3d4e5f6...",
    "license_type": "PERPETUAL",
    "issue_date": "2026-07-01",
    "trial_expires_at": null
  },
  "signature": "base64-encoded Ed25519 signature over canonical JSON of `payload`"
}
```

- Signing covers the canonical (sorted-key, no-whitespace) JSON encoding of `payload` to avoid signature mismatches from formatting differences.
- The file is _signed, not encrypted_ (FR-LIC-005) — there's nothing secret inside it worth hiding, only something that must not be tampered with. Anyone can read a `license.key`; nobody but Seller can produce one that verifies.

### 16.5 Keygen Tool (Internal Only)

```python
# tools/keygen/generate_license.py  (NEVER shipped to customers)
import json, base64
from nacl.signing import SigningKey

def generate_license(hardware_id: str, cafe_name: str, license_type: str = "PERPETUAL", trial_days: int | None = None) -> str:
    signing_key = SigningKey(open("private_key.pem", "rb").read())
    payload = {
        "cafe_name": cafe_name,
        "hardware_id": hardware_id,
        "license_type": license_type,
        "issue_date": date.today().isoformat(),
        "trial_expires_at": (date.today() + timedelta(days=trial_days)).isoformat() if trial_days else None,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    signature = signing_key.sign(canonical).signature
    return base64.b64encode(json.dumps({
        "payload": payload,
        "signature": base64.b64encode(signature).decode(),
    }).encode()).decode()
```

Run manually, per sale, by Seller staff: paste in the customer's Hardware ID and cafe name, get back a `license.key` file to send to the customer. This tool — and the `private_key.pem` it depends on — lives in a separate, private repository from `arcade`, never in the same VCS history as the shipped product (FR-LIC-001).

### 16.6 Verification Flow

```python
# backend/licensing/verify.py
from nacl.signing import VerifyKey
from nacl.exceptions import BadSignatureError

class LicenseError(Enum):
    MISSING = "no license.key found"
    INVALID_SIGNATURE = "signature verification failed"
    HARDWARE_MISMATCH = "license is bound to a different machine"
    TRIAL_EXPIRED = "trial period has ended"

def check_license(license_path: str) -> LicenseResult:
    if not os.path.exists(license_path):
        return LicenseResult(ok=False, error=LicenseError.MISSING)

    raw = base64.b64decode(open(license_path, "rb").read())
    parsed = json.loads(raw)
    payload, signature = parsed["payload"], base64.b64decode(parsed["signature"])
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()

    try:
        VerifyKey(bytes.fromhex(ARCADE_PUBLIC_KEY_HEX)).verify(canonical, signature)
    except BadSignatureError:
        return LicenseResult(ok=False, error=LicenseError.INVALID_SIGNATURE)

    if payload["hardware_id"] != get_hardware_id():
        return LicenseResult(ok=False, error=LicenseError.HARDWARE_MISMATCH)

    if payload["license_type"] == "TRIAL" and date.today() > date.fromisoformat(payload["trial_expires_at"]):
        return LicenseResult(ok=False, error=LicenseError.TRIAL_EXPIRED)

    return LicenseResult(ok=True, payload=payload)
```

This function is called by the Launcher (§8.2) before the setup wizard or server subprocess can run, and on every subsequent Launcher start (FR-SYS-008). On success, the Launcher writes/refreshes the `license_status` cache row (§5.1) so the running dashboard can display it without re-reading the key file.

### 16.7 Activation Screen (Launcher UI)

| State                                    | What's shown                                                                                                                                             | What's allowed                                            |
| ---------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------- |
| No `license.key` present                 | Hardware ID (copyable), instructions to send it to Seller, a "Browse for license.key" file picker                                                        | Nothing else — setup wizard and server start are disabled |
| `license.key` present, invalid signature | Error: "This license file isn't valid. Please confirm you received it correctly, or contact support."                                                    | Re-try / browse for a different file                      |
| `license.key` present, hardware mismatch | Error: "This license is registered to a different machine. Contact Seller with your Hardware ID below to get this license reissued." + Hardware ID shown | Re-try / browse for a different file                      |
| `license.key` present, trial expired     | Error: "Your trial period has ended. Contact Seller to purchase a full license."                                                                         | Re-try / browse for a different file                      |
| Valid license                            | Brief confirmation (cafe name, license type), then proceeds automatically to setup wizard or server start                                                | Continues normally                                        |

This mirrors FR-LIC-008's requirement to distinguish "invalid file" from "wrong machine" rather than showing one generic failure.

### 16.8 Hardware-Change Re-activation (FR-LIC-010)

There is no self-service transfer flow in V1. If a cafe's hardware changes (e.g. motherboard replacement) and the Hardware ID no longer matches:

1. Owner reaches the "hardware mismatch" Activation screen state and reads off the new Hardware ID
2. Owner contacts Seller with proof of original purchase and the new Hardware ID
3. Seller re-runs the keygen tool with the new Hardware ID, same cafe name and license type
4. Owner replaces `license.key` with the reissued file

This is intentionally a manual, support-mediated process rather than an automated transfer API — there is no license server to host such an API against, and the volume of hardware-replacement events for a single-location product is expected to be low.

### 16.9 Trial / Demo Mode (FR-LIC-011)

The same `license_type` field supports a `"TRIAL"` value with a `trial_expires_at` date, generated by the same keygen tool with a `--trial-days N` flag. No separate code path, license format, or verification logic is needed — `check_license()` simply adds the expiry check shown in §16.6 when `license_type == "TRIAL"`. This lets Seller hand a prospective cafe a 14- or 30-day evaluation license using the exact mechanism that powers paid licenses.

### 16.10 What This Design Deliberately Does Not Do

- **No phone-home, ever, post-activation.** There is no license server, so there is nothing to call. This is a deliberate trade-off against piracy-resistance: a sufficiently motivated user could patch the public key check out of the binary. The design accepts this risk in exchange for the zero-infrastructure, zero-recurring-cost positioning that is core to the product. Tying licensing to a model that requires Seller to run a server would directly contradict the product's main selling point.
- **No automated hardware-transfer or seat-reassignment system.** Handled manually per §16.8, by design, given expected volume.
- **No encryption of the license payload.** Signing, not secrecy, is the integrity mechanism (§16.4) — there is no confidential data in a license file worth protecting from the customer who already legitimately holds it.

---

## 17. Design Decisions and Trade-offs

| Decision                 | Choice                                                | Alternative Considered                                      | Rationale                                                                                                                                                                                                                                                                     |
| ------------------------ | ----------------------------------------------------- | ----------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Database**             | SQLite + WAL                                          | PostgreSQL                                                  | No installation or service management required. WAL mode handles concurrent reads. Single-location scope means SQLite performance is more than sufficient. PostgreSQL is the documented V2 upgrade path.                                                                      |
| **ORM**                  | SQLAlchemy (async)                                    | Raw SQL, Tortoise ORM                                       | Industry standard, excellent Alembic integration, strong typing support, wide community. Async support via `AsyncSession` prevents blocking the event loop.                                                                                                                   |
| **Database driver**      | aiosqlite (async)                                     | sqlite3 (sync)                                              | FastAPI is async-native; sync SQLAlchemy blocks the event loop on every DB operation. `aiosqlite` allows async DB calls without threadpool overhead.                                                                                                                          |
| **Migrations**           | Alembic                                               | Manual SQL scripts                                          | Versioned, reversible, auto-detects model diffs. Essential as the project evolves across phases.                                                                                                                                                                              |
| **Backend framework**    | FastAPI                                               | Flask, Django                                               | Async-native, automatic API docs, Pydantic integration, excellent WebSocket support, fastest Python web framework.                                                                                                                                                            |
| **Real-time**            | WebSockets                                            | Polling, SSE                                                | Sub-second updates are a core UX requirement. WebSocket is the only approach that satisfies this without hammering the server with polling.                                                                                                                                   |
| **Client agent**         | Electron with platform abstraction                    | Native per-OS apps, Python script                           | Single codebase for UI, cross-platform via abstraction, full OS APIs via Node.js, hardware metrics via `systeminformation`, modern UI for splash/countdown.                                                                                                                   |
| **Auth**                 | PIN + JWT + token_version revocation                  | Password + session cookie                                   | PINs are appropriate for the counter context — fast entry, shared terminal. JWT with `token_version` allows revocation without a blacklist.                                                                                                                                   |
| **Billing precision**    | Integer (paise)                                       | Float/Decimal                                               | Float rounding errors accumulate across hundreds of daily transactions. Integer arithmetic is exact. Decimal would also work but adds library dependency.                                                                                                                     |
| **Console control**      | Tuya smart plugs                                      | HDMI-CEC, custom hardware                                   | No agent possible on consoles. Smart plugs are inexpensive, widely available in Nepal, and the Tuya API is well-documented.                                                                                                                                                   |
| **Printing**             | python-escpos + PDF                                   | Receipt service, cloud printing                             | Local-first principle. python-escpos supports all common thermal printers. PDF fallback covers any regular printer with zero additional setup.                                                                                                                                |
| **Feature flags**        | DB-stored, runtime                                    | Code-level flags, env vars                                  | DB storage allows the cafe owner to toggle features from the dashboard UI without any technical knowledge or server restart.                                                                                                                                                  |
| **Modularity**           | Feature flags                                         | Separate product editions                                   | One codebase serves all cafe sizes. Flags suppress UI and gate APIs cleanly. Simpler to maintain and test than multiple editions.                                                                                                                                             |
| **Frontend state**       | React Query + WebSocket                               | Redux, SWR                                                  | React Query handles server state (caching, refetch, mutations) cleanly. WebSocket events trigger targeted cache invalidations. No global Redux boilerplate needed.                                                                                                            |
| **Auth token storage**   | In-memory (JS variable)                               | localStorage                                                | localStorage is not supported in sandboxed environments and is a XSS risk. In-memory token is lost on refresh (re-login required), which is acceptable and correct for a shared counter terminal.                                                                             |
| **Licensing**            | Offline Ed25519 signature + hardware fingerprint      | Online license server, time-bombed trial only, no licensing | A license server would require Seller to run permanent infrastructure, directly contradicting the product's zero-cloud-dependency pitch. Offline asymmetric signing makes licenses unforgeable without the private key while needing no network call, ever, after activation. |
| **PIN hashing**          | Argon2id (`argon2-cffi`)                              | bcrypt                                                      | Argon2id is the OWASP-recommended algorithm for new systems. It provides configurable memory hardness that bcrypt lacks. No fallback is implemented.                                                                                                                          |
| **Hardware fingerprint** | py-machineid (primary) + OS fallbacks                 | OS-specific commands only                                   | `py-machineid` works on all three OSes without admin privileges. OS-specific fallbacks only used if `py-machineid` returns empty.                                                                                                                                             |
| **Cross‑platform**       | Platform abstraction in agent; cross‑platform backend | Separate codebases per OS                                   | Single codebase for UI, but OS-specific modules for system calls. This minimises duplication while supporting all three OSes.                                                                                                                                                 |
| **Shutdown lifecycle**   | `lifespan` context manager                            | `@app.on_event("shutdown")`                                 | `@app.on_event` is deprecated in FastAPI 0.93+. `lifespan` consolidates startup and shutdown in one place and is the modern pattern.                                                                                                                                          |
| **Task scheduling**      | APScheduler `AsyncIOScheduler`                        | `python-schedule`                                           | `python-schedule` is blocking and single-threaded; `AsyncIOScheduler` integrates natively with FastAPI's event loop and handles exceptions gracefully.                                                                                                                        |
| **Screenshot payload**   | JPEG 80% quality, max 1280×720, 5MB limit             | PNG full resolution                                         | PNG screenshots are 3–8 MB, encoding to 4–11 MB base64. JPEG at 80% quality provides 5–10× compression with acceptable quality for monitoring.                                                                                                                                |
| **Server recovery**      | Load active sessions from DB on startup               | No recovery, lost sessions                                  | Preserves billing data and allows agents to re-sync. Critical for reliability.                                                                                                                                                                                                |
| **Agent offline start**  | Prohibited — sessions only from server                | Allow local session start offline                           | Simplifies billing reconciliation and prevents fraud. Agent is a client, not a peer.                                                                                                                                                                                          |

---

_This document is the authoritative design specification for Arcade v2.0._
_It must be updated whenever a significant design decision changes during implementation._

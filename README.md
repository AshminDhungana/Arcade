<div align="center">

# 🕹️ Arcade — Gaming Cafe Management Software

**The self‑hosted operating system for gaming cafes.**

Sessions, billing, POS, members, PC control, and analytics — one system, zero subscriptions, zero internet dependency.

[![Status](https://img.shields.io/badge/status-active--development-brightgreen)](https://github.com/AshminDhungana/Agentium)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue)](https://www.apache.org/licenses/LICENSE-2.0)
[![Python](https://img.shields.io/badge/backend-Python%203.11%2B-3776AB?logo=python&logoColor=white)](#tech-stack)
[![FastAPI](https://img.shields.io/badge/API-FastAPI-009688?logo=fastapi&logoColor=white)](#tech-stack)
[![React](https://img.shields.io/badge/frontend-React%20%2B%20Vite-61DAFB?logo=react&logoColor=white)](#tech-stack)
[![Electron](https://img.shields.io/badge/client-Electron-47848F?logo=electron&logoColor=white)](#tech-stack)
[![SQLite](<https://img.shields.io/badge/database-SQLite%20(WAL)-003B57?logo=sqlite&logoColor=white>)](#tech-stack)
[![Cross‑Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)](#getting-started)

</div>

---

Most gaming cafes run on a patchwork of a generic timer app, a separate POS, a notebook for expenses, and a lot of manual math at checkout. **Arcade replaces all of it with one system that runs entirely on your local network** — a FastAPI backend on the counter PC, a React dashboard for staff, and a lightweight agent on every client machine.

**Arcade is fully cross‑platform** — the server runs on Windows, macOS, or Linux, and the client agent works on all three OSes. You are not locked into a single ecosystem.

No internet required during operation. No subscription fees. No per-seat licensing. You own the box it runs on.

> **Project status:** Arcade is in the design-complete phase, ready for development. The architecture and feature set below reflect the plan for v1 — see [Build Phases](#build-phases) for what's planned.

---

## Table of Contents

- [Why Arcade](#why-arcade)
- [Features](#features)
- [Licensing](#licensing)
- [Tech Stack](#tech-stack)
- [Architecture](#architecture)
- [Getting Started](#getting-started)
- [Configuration](#configuration)
- [Feature Flags](#feature-flags)
- [Project Structure](#project-structure)
- [Seat Zones](#seat-zones)
- [Pricing Models](#pricing-models)
- [Customer Flows](#customer-flows)
- [Console Control](#console-control)
- [Database Migrations](#database-migrations)
- [Build Phases](#build-phases)
- [V2 Roadmap](#v2-roadmap)
- [License](#license)

---

## Why Arcade

- **Built for the LAN, not the cloud.** Everything runs on hardware you already own. No outage ever costs you a sale.
- **Billing you can trust.** All money is stored as integer paise — no floating-point rounding errors, ever.
- **Modular by design.** Feature flags let a 6-seat shop run a bare-bones timer, while a full esports venue turns on members, packages, tournaments, and inventory.
- **Hardware-aware.** Wake-on-LAN boot, Tuya-controlled consoles, and a branded lock screen mean staff manage the whole floor from one dashboard — not six.
- **Runs everywhere.** The server can be a Windows, macOS, or Linux machine; client agents run on all three platforms, giving you the freedom to choose your hardware.
- **Hardened kiosk overlay.** The agent uses Electron's `kiosk: true` mode, not OS lock/unlock, for consistent access control across all platforms. Alt+F4, Cmd+Q, F12, and Ctrl+P are intercepted and discarded.
- **Resilient by design.** Agent persists session state locally in SQLite. Server restarts preserve active sessions. No billing data is lost during LAN interruptions or agent crashes.
- **Secure by default.** Agent authentication uses per-seat random secrets. Staff PINs are hashed with Argon2id. JWT tokens include `token_version` for immediate revocation.

---

## Features

### Core Operations

- **Live seat dashboard** — colour-coded grid of all seats with real-time status (Available, In Use, Reserved, Paused, Maintenance, Offline, Booting, Unreachable), zone grouping, and health badges
- **Session management** — start, stop, pause, and resume timed sessions per seat
- **Seat reservations** — staff can reserve seats in advance for groups, parties, or call-ahead bookings
- **Maintenance mode** — mark any seat as out of order with a note; track downtime per machine over time
- **Auto-boot** — Wake-on-LAN magic packets boot all client PCs on server startup; seats show **Booting** status while waiting for agent heartbeat, and **Unreachable** if no connection arrives within 60 seconds; Tuya powers consoles locally via TinyTuya
- **Session recovery** — active sessions are preserved when the server restarts; agents re-sync on reconnect

### Billing

- **Flexible pricing** — per-minute, flat hourly, time-block, peak/off-peak, and device-type rates
- **Time packages & day passes** — sell bundled hour packs, day passes, night passes, and monthly passes
- **Promotions engine** — happy hours, flash discounts, first-visit offers, group discounts, birthday bonuses
- **Prepaid vouchers** — generate and print one-time codes redeemable at the counter or client screen
- **Billing precision** — all amounts stored as integers (paise) to eliminate rounding errors
- **Atomic package updates** — prevents race conditions when multiple sessions draw from the same package

### POS & Inventory

- **Food & drink POS** — add items to any open session tab from the counter
- **Inventory tracking** — stock levels per menu item, low-stock alerts, auto-disable when sold out
- **Restock log** — record incoming deliveries with timestamp and quantity

### Members & Loyalty

- **Member accounts** — prepaid wallet, loyalty points, tier-based discounts, visit history
- **Package entitlements** — active packages draw down before per-minute billing kicks in
- **Walk-in support** — no account needed; pay at checkout as usual

### PC & Console Control

- **Client agent (kiosk overlay model)** — full‑screen always‑on‑top overlay blocks desktop access when no session is active. `HIDE_OVERLAY` removes it during a session; `SHOW_OVERLAY` re‑enables it on session end. **Consistent across Windows, macOS, and Linux** — no OS lock/unlock.
- **Kiosk hardening** — `kiosk: true`, `closable: false`, DevTools disabled, global shortcuts intercepted (Alt+F4, Cmd+Q, F12, Ctrl+P). Known gaps documented (`Ctrl+Alt+Del` on Windows, Wayland compositor variations on Linux).
- **Remote commands** — restart, shutdown, send message, or screenshot any client from the dashboard
- **PC health monitoring** — CPU%, RAM%, temperature, and disk space reported from every agent every 60 seconds
- **Console control** — power PS5/Xbox on and off via **local LAN** (TinyTuya), no cloud dependency after initial pairing
- **Branded lock screen** — cafe logo, session time, food menu, and "Call Staff" button on every client screen
- **Announcements** — push a message from the dashboard that appears on all client screens instantly
- **Agent authentication** — each agent uses a random `agent_secret` generated at setup time, validated on every connection. Not hardcoded in source.
- **Agent offline behavior** — sessions cannot be started offline; agents continue tracking active sessions and sync on reconnect

### Staff & Shifts

- **Staff roles** — Admin (full access) and Cashier (billing + POS only); **Staff ID + PIN** authentication; **Argon2id** PIN hashing (OWASP-recommended); lockout after 5 failed attempts
- **JWT with token_version** — changing a PIN or deactivating a staff member immediately invalidates all previously issued tokens; JWT payload includes `staff_id`, `role`, and `token_version`
- **Shift management** — open and close shifts with cash float; per-shift revenue reporting
- **Audit log** — write-only log of all sensitive operations for billing disputes and accountability

### Reporting & Finance

- **Analytics dashboard** — today's revenue, busiest hours, seat utilisation by zone, top POS items, member activity
- **Expense tracking** — log rent, electricity, restocking, wages; see gross vs. net P&L estimate
- **Shift reports** — revenue, sessions, avg. duration, payment method breakdown per shift
- **Owner mobile view** — mobile-responsive dashboard accessible from the owner's phone on the cafe WiFi

### Receipts & Printing

- **Thermal printing** — via `python-escpos`
- **PDF fallback** — browser print or PDF for any regular printer
- **Receipt contents** — seat, customer, times, duration, time charge, itemised food/drink, total, payment method

### Tournaments & Events

- **Event mode** — create events with entry fees, register participants, assign seats, track brackets
- **Single/double elimination** — advance winners, record results, calculate prize pools
- **Event billing** — entry fees charged to member wallets or as standalone transactions

---

## Licensing

Arcade is sold as a **one-time, perpetual license per cafe location**, hardware-locked to the counter PC running the server. There are no subscriptions and no recurring per-seat fees.

- **Fully offline.** Activation does not require a license server. A `license.key` file, signed with an Ed25519 key by Seller, is verified locally against the embedded public key — no network call needed, ever, consistent with Arcade's zero-cloud-dependency design.
- **How it works:** On first launch, the Launcher computes a Hardware ID from this PC using `py-machineid` (**no admin privileges required**) and shows it on the Activation screen. Send that ID to Seller with proof of purchase; you'll receive a `license.key` file back. Drop it in the app folder (`arcade/license.key`) and the setup wizard unlocks.
- **Trial licenses:** Time-limited trial licenses are supported using the same signature mechanism, with an expiry date encoded in the license payload.
- **Hardware changes:** If you replace major hardware (e.g. the motherboard) and the Hardware ID changes, contact Seller with the new ID for a reissued license. This is a manual process in V1.
- **What's checked, and when:** The license is verified once at activation and again locally on every subsequent Launcher start. Tampering with or removing `license.key` simply returns the app to the Activation screen — it never touches or corrupts your session/billing data.
- **Cross‑platform note:** `py-machineid` works on all three OSes without admin/root privileges. OS-specific fallbacks (using `wmic`, `system_profiler`, `dmidecode`) are only used if `py-machineid` returns empty.

---

## Tech Stack

| Layer              | Technology                                                                                                  |
| ------------------ | ----------------------------------------------------------------------------------------------------------- |
| Backend API        | Python · FastAPI · Uvicorn                                                                                  |
| Database           | SQLite (WAL mode, `busy_timeout=5000`, `synchronous=NORMAL`) · **Async** SQLAlchemy · `aiosqlite` · Alembic |
| Frontend           | React · Vite · TypeScript · TailwindCSS · React Query                                                       |
| Server launcher    | Python · Tkinter                                                                                            |
| Client agent       | Electron · React · `systeminformation` · `better-sqlite3`                                                   |
| Console control    | **Local LAN** Tuya (TinyTuya) — no cloud dependency                                                         |
| Printing           | `python-escpos` · PDF fallback                                                                              |
| Real-time comms    | WebSockets (exponential backoff reconnection + heartbeat)                                                   |
| Charts             | Recharts                                                                                                    |
| Task queue         | **APScheduler** `AsyncIOScheduler` (nightly backup)                                                         |
| Shutdown lifecycle | FastAPI **`lifespan` context manager** — replaces deprecated `@app.on_event`                                |
| PIN hashing        | **Argon2id** via `argon2-cffi` (OWASP-recommended)                                                          |
| Hardware ID        | `py-machineid` (primary) + OS fallbacks — no admin required                                                 |
| Cross‑platform     | Electron (agent) + Python (backend) run on Windows, macOS, Linux                                            |

---

## Architecture

```
[Power strip ON]
       │
       ▼
Main Counter PC  ──  launcher.py (Tkinter GUI)
       │                    │
       │              License check (offline, Ed25519 signature + Hardware ID via py-machineid)
       │                    │ pass                          │ fail
       │                    ▼                                ▼
       │           Setup wizard / server start      License Activation screen
       │                    │
       │              FastAPI backend (async SQLAlchemy)  ◄──  React dashboard (staff UI)
       │              SQLite database (WAL + pragmas)       └── Mobile view (owner phone)
       │              APScheduler (nightly backup)
       │
       ├── Wake-on-LAN (magic packet) ──────► Client machines (Windows/macOS/Linux)
       │                                       └── Electron agent (kiosk overlay model)
       │                                           ├── Kiosk overlay (hardened: kiosk: true, closable: false)
       │                                           ├── Local SQLite session persistence
       │                                           ├── Platform abstraction (restart, shutdown, screenshot)
       │                                           ├── Countdown + low-time warning
       │                                           ├── Branded splash screen
       │                                           ├── Health metrics (CPU, RAM, temp)
       │                                           ├── Remote commands (HIDE_OVERLAY, SHOW_OVERLAY, message, restart, screenshot)
       │                                           └── Agent_secret authentication (generated at setup)
       │
       └── Local TinyTuya ─────────────────► Smart plugs (no cloud after pairing)
                                              └── PS5 / Xbox (boot on power restore)
```

The server PC is the only machine that needs to be on wired ethernet. All communication is local — no cloud dependency.
The agent uses a **platform abstraction layer** inside Electron – the same UI code works on Windows, macOS, and Linux, with OS‑specific modules for **kiosk overlay control**, shutdown, restart, screenshot capture, and auto‑start. **OS lock/unlock is not used** — the kiosk overlay model is consistent across all platforms.

On server startup, active sessions are loaded from the database and agents are notified to re-sync, ensuring no billing data is lost.

---

## Getting Started

### Prerequisites

- Python 3.11+ (macOS, Windows, or Linux)
- Node.js 20 LTS or newer

### Quick Start

```bash
# Clone the repository
git clone https://github.com/AshminDhungana/Arcade.git
cd Arcade

# Install all dependencies (Python + frontend + agent)
make install

# Start the backend dev server (FastAPI with hot reload)
make backend-dev

# In a separate terminal, start the frontend dev server
make frontend-dev
```

### Environment-specific Setup

If `make` is not available, use the equivalent commands directly:

```bash
# Install backend dependencies
cd backend && pip install -r requirements.txt

# Install frontend dependencies
cd frontend && npm install

# Start backend dev server
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# Start frontend dev server
cd frontend && npm run dev
```

### Server First Launch

On first launch, the Launcher (`python launcher.py`) will show a **License Activation** screen. Follow the instructions to activate your license. See `docs/security/key-management.md` for details on the licensing system.

### Running Tests

```bash
# Run all backend and frontend tests
make test
```


## Configuration


All runtime config lives in `arcade.config.json` (created by the setup wizard):

```json
{
  "cafe_name": "Arcade",
  "host": "192.168.1.100",
  "port": 8000,
  "db_path": "arcade.db",
  "backup_dir": "backups/",
  "backup_retain_days": 30,
  "backup_time": "03:00",
  "admin_staff_id": "S001",
  "admin_pin_hash": "<argon2id_hash>",
  "cashier_staff_id": "S002",
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
  "printer_type": "usb"
}
```

Per-zone pricing, peak/off-peak schedules, menu items, packages, promotions, and feature flags are all configured in the dashboard under **Settings**.

---

## Feature Flags

Arcade is modular. Features can be toggled on or off from the Settings screen to suit any cafe size or style:

| Flag                         | What it controls                 | Default |
| ---------------------------- | -------------------------------- | ------- |
| `enable_members`             | Member accounts, wallet, loyalty | ON      |
| `enable_packages`            | Time bundles and day passes      | ON      |
| `enable_pos`                 | Food & drink ordering            | ON      |
| `enable_inventory`           | Stock tracking for POS items     | OFF     |
| `enable_reservations`        | Advance seat reservations        | ON      |
| `enable_vouchers`            | Prepaid voucher codes            | OFF     |
| `enable_tournaments`         | Event and tournament mode        | OFF     |
| `enable_expense_tracking`    | Expense log and P&L              | OFF     |
| `enable_health_monitoring`   | PC hardware metrics from agent   | ON      |
| `require_member_for_session` | Require member login to unlock   | OFF     |

A cafe that just wants a simple timer and receipt can turn off most of these. A full esports venue turns them all on.

---

## Project Structure

The key architectural directories:

```
arcade/
├── backend/
│   ├── api/routers/          # FastAPI route handlers (async)
│   ├── services/             # Business logic (async) — billing, sessions, etc.
│   ├── repositories/         # All database queries (async, no business logic)
│   ├── models/               # SQLAlchemy ORM models
│   ├── schemas/              # Pydantic request/response schemas
│   ├── licensing/            # Offline license verification (py-machineid, Ed25519)
│   ├── core/
│   │   ├── database.py       # Async SQLAlchemy + WAL + busy_timeout=5000
│   │   ├── security.py       # Argon2id hashing + JWT with token_version
│   │   └── ws_manager.py     # WebSocket manager (agent_secret validation)
│   ├── main.py               # FastAPI app — lifespan context manager (startup/shutdown)
│   └── alembic.ini           # Alembic configuration
├── frontend/                 # React dashboard (Vite + TailwindCSS)
├── agent/
│   └── src/
│       ├── main/
│       │   ├── platform/     # OS abstraction: kiosk overlay, restart, screenshot
│       │   ├── storage/      # Local SQLite session persistence
│       │   ├── ipc/          # IPC handlers (overlay, screenshot, restart, shutdown)
│       │   └── ws/           # WebSocket client (agent_secret auth, exponential backoff)
│       └── renderer/         # Kiosk overlay UI (hardened: kiosk: true, closable: false)
├── alembic/                  # Database migration scripts
├── tools/keygen/             # INTERNAL — private signing key, NOT shipped
├── launcher.py               # Tkinter GUI (License Activation, setup wizard, server mgmt)
├── arcade.config.json        # Runtime config (created by setup wizard)
└── license.key               # License file (placed by owner at arcade/license.key)
```

---

## Seat Zones

Seats are grouped into zones for pricing and dashboard layout:

| Zone           | Examples                                  |
| -------------- | ----------------------------------------- |
| Standard PC    | Regular gaming rigs                       |
| VIP PC         | High-spec machines (144Hz+, top-tier GPU) |
| Console Corner | PS5, Xbox Series X                        |
| Other          | VR stations, projector rooms              |

Each zone has its own hourly rate set in Settings. Packages and promotions can be restricted to specific zones.

---

## Pricing Models

The billing engine supports:

- **Per-minute** — e.g. Rs. 2/min
- **Flat hourly** — e.g. Rs. 100/hr
- **Time-block** — billed per 30-min block
- **Peak / off-peak** — different rates by time of day or day of week
- **Device-type pricing** — PC rate ≠ PS5 rate ≠ VR rate
- **Member discount** — loyalty tier applies a percentage discount
- **Package entitlement** — time bundle or day pass draws down before per-minute billing
- **Promotions** — happy hour, group discount, birthday bonus, flash discount

Rates are locked at session start. A mid-day rate change never affects an in-progress session.

---

## Customer Flows

**Walk-in:**

1. Customer arrives → staff selects an available seat
2. Session starts → agent receives `HIDE_OVERLAY`, kiosk overlay removed, desktop accessible, branded splash shows for 5 seconds
3. Timer begins — server authoritative, agent caches locally in SQLite for LAN‑drop resilience
4. At 5-minute warning → countdown popup on client screen
5. Customer finishes → staff clicks Checkout → invoice generated
6. Payment marked → agent receives `SHOW_OVERLAY`, kiosk overlay re‑enabled → receipt printed

**Member with package:**

1. Member arrives → staff selects seat and looks up member account
2. Active package detected → session draws from package minutes, not per-minute rate
3. If package runs out mid-session → billing switches to per-minute automatically
4. Checkout reflects package usage + any overflow at per-minute rate

**Group reservation:**

1. Group calls ahead → staff reserves 6 seats for 3 PM
2. Dashboard shows those seats as "Reserved" until the group arrives
3. At 3 PM → staff starts sessions for all 6 seats simultaneously

---

## Console Control

PS5 and Xbox cannot run a custom agent. Each console is connected to a **Tuya-compatible smart plug**. Arcade controls them via **local LAN** using the TinyTuya library — **no internet dependency during normal operation**. An initial one‑time pairing (requiring internet) is performed via the Tuya app to retrieve the `local_key`, `device_id`, and `ip_address`, after which all control is local.

Enable "boot on power restore" in the console's settings once — after that, power-cycling the plug is enough to boot it.

---

## Database Migrations

Arcade uses **Alembic** for schema migrations. Never edit the schema manually. `alembic.ini` lives in `backend/` — run all Alembic commands from that directory.

```bash
cd backend

# Apply all pending migrations (run automatically on server startup)
alembic upgrade head

# Generate a new migration after changing a model
alembic revision --autogenerate -m "add packages table"

# Roll back one step
alembic downgrade -1
```

---

## Build Phases

| Phase                                  | Scope                                                                                                                                                                                                                                                                                                                     | Status     |
| -------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- |
| **1 — Core**                           | License activation (Ed25519 + `py-machineid`), Launcher, FastAPI scaffold with `lifespan`, Alembic, Async SQLAlchemy + WAL pragmas (`busy_timeout=5000`), WoL boot, session API, seat dashboard, Electron agent with hardened kiosk overlay (Windows first), WebSocket with `agent_secret` auth, local SQLite persistence | 🔲 Planned |
| **2 — Billing, POS & Printing**        | Time billing, food/drink POS, inventory tracking, receipt printing, audit log, integer paise precision                                                                                                                                                                                                                    | 🔲 Planned |
| **3 — Members, Packages & Promotions** | Member profiles, wallet, loyalty, time packages, day passes, voucher codes, promotions engine, per-zone pricing, staff roles (Argon2id PIN hashing, JWT with `token_version`)                                                                                                                                             | 🔲 Planned |
| **4 — Operations & Experience**        | Remote PC commands, PC health monitoring, shift management, expense tracking, seat reservations, branded kiosk overlay, announcements, APScheduler nightly backup, server session recovery                                                                                                                                | 🔲 Planned |
| **5 — Events & Analytics**             | Tournament/event mode, analytics dashboard, maintenance mode, configurable feature flags, screenshot rate-limiting (JPEG 80%, 1280×720)                                                                                                                                                                                   | 🔲 Planned |
| **6 — Cross‑Platform Polish**          | Complete agent platform abstraction (macOS/Linux), packaging for all OSes, auto‑start scripts, kiosk hardening verification on all platforms                                                                                                                                                                              | 🔲 Planned |
| **7 — Growth (V2)**                    | Online booking portal, WhatsApp/SMS notifications, optional WAN remote access, multi-location                                                                                                                                                                                                                             | 🔲 Future  |

**Legend:** 🔲 Planned · 🟡 In progress · ✅ Done

---

## V2 Roadmap

These are out of scope for the initial release but architecturally planned for:

- **Online seat booking portal** — public link showing live availability; customers reserve before walking in
- **WhatsApp / SMS notifications** — low-balance alerts, booking confirmations, event broadcasts via Sparrow SMS or WhatsApp Business API
- **Optional WAN access** — read-only owner dashboard accessible from outside the LAN
- **Multi-location support** — one owner account, multiple cafe locations, cross-location reporting
- **Game library management** — track which titles are installed on which machines
- **PostgreSQL migration path** — for larger deployments or multi-location

---

## Known Limitations (V1)

- **Ctrl+Alt+Del** on Windows cannot be intercepted by the agent without a dedicated SAS filter driver or Windows Kiosk Mode assignment
- **Wayland compositors** on Linux may require additional configuration for `alwaysOnTop` to work reliably across all desktop environments
- **macOS Screen Recording** permission must be granted for screenshot capture to work
- **Agent offline session start** is not supported — all sessions must be initiated from the dashboard
- **No self-service license transfer** — hardware changes require manual support contact

---

## License

Arcade is licensed under the **Apache License, Version 2.0**. See [LICENSE](LICENSE) for details.

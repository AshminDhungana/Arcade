<div align="center">

# 🕹️ Arcade - Gaming Cafe Management Software

**The self‑hosted operating system for gaming cafes.**

Sessions, billing, POS, members, PC control, and analytics — one system, zero subscriptions, zero internet dependency.

[![Status](https://img.shields.io/badge/status-in%20development-orange)](#build-phases)
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

> **Project status:** Arcade is in active early development. The architecture and feature set below reflect the plan for v1 — see [Build Phases](#build-phases) for what's actually built versus what's designed but not yet implemented.

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

---

## Features

### Core Operations

- **Live seat dashboard** — colour-coded grid of all seats with real-time status, zone grouping, and health badges
- **Session management** — start, stop, pause, and resume timed sessions per seat
- **Seat reservations** — staff can reserve seats in advance for groups, parties, or call-ahead bookings
- **Maintenance mode** — mark any seat as out of order with a note; track downtime per machine over time
- **Auto-boot** — Wake-on-LAN magic packets boot all client PCs on server startup; Tuya powers consoles

### Billing

- **Flexible pricing** — per-minute, flat hourly, time-block, peak/off-peak, and device-type rates
- **Time packages & day passes** — sell bundled hour packs, day passes, night passes, and monthly passes
- **Promotions engine** — happy hours, flash discounts, first-visit offers, group discounts, birthday bonuses
- **Prepaid vouchers** — generate and print one-time codes redeemable at the counter or client screen
- **Billing precision** — all amounts stored as integers (paise) to eliminate rounding errors

### POS & Inventory

- **Food & drink POS** — add items to any open session tab from the counter
- **Inventory tracking** — stock levels per menu item, low-stock alerts, auto-disable when sold out
- **Restock log** — record incoming deliveries with timestamp and quantity

### Members & Loyalty

- **Member accounts** — prepaid wallet, loyalty points, tier-based discounts, visit history
- **Package entitlements** — active packages draw down before per-minute billing kicks in
- **Walk-in support** — no account needed; pay at checkout as usual

### PC & Console Control

- **Client agent** — locks/unlocks Windows/macOS/Linux screens, shows countdown timer and low-time warnings
- **Remote commands** — restart, shutdown, send message, or screenshot any client from the dashboard
- **PC health monitoring** — CPU%, RAM%, temperature, and disk space reported from every agent every 60 seconds
- **Console control** — power PS5/Xbox on and off via Tuya-compatible smart plugs
- **Branded lock screen** — cafe logo, session time, food menu, and "Call Staff" button on every client screen
- **Announcements** — push a message from the dashboard that appears on all client screens instantly

### Staff & Shifts

- **Staff roles** — Admin (full access) and Cashier (billing + POS only); PIN lockout after 5 failed attempts
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
- **How it works:** On first launch, the Launcher computes a Hardware ID from this PC and shows it on the Activation screen. Send that ID to Seller with proof of purchase; you'll receive a `license.key` file back. Drop it in the app folder and the setup wizard unlocks.
- **Hardware changes:** If you replace major hardware (e.g. the motherboard) and the Hardware ID changes, contact Seller with the new ID for a reissued license. This is a manual process in V1.
- **What's checked, and when:** The license is verified once at activation and again locally on every subsequent Launcher start. Tampering with or removing `license.key` simply returns the app to the Activation screen — it never touches or corrupts your session/billing data.
- **Cross‑platform note:** Hardware ID generation uses a combination of system UUID, MAC address, and disk serial – works reliably on all three OSes.

---

## Tech Stack

| Layer           | Technology                                                       |
| --------------- | ---------------------------------------------------------------- |
| Backend API     | Python · FastAPI · Uvicorn                                       |
| Database        | SQLite (WAL mode) · SQLAlchemy · Alembic                         |
| Frontend        | React · Vite · TypeScript · TailwindCSS · React Query            |
| Server launcher | Python · Tkinter                                                 |
| Client agent    | Electron · React · `systeminformation`                           |
| Console control | Tuya smart plug API                                              |
| Printing        | `python-escpos` · PDF fallback                                   |
| Real-time comms | WebSockets (exponential backoff reconnection + heartbeat)        |
| Charts          | Recharts                                                         |
| Task queue      | Python `schedule` (nightly backup)                               |
| Cross‑platform  | Electron (agent) + Python (backend) run on Windows, macOS, Linux |

---

## Architecture

```
[Power strip ON]
       │
       ▼
Main Counter PC  ──  launcher.py (Tkinter GUI)
       │                    │
       │              License check (offline, signature + Hardware ID)
       │                    │ pass                          │ fail
       │                    ▼                                ▼
       │           Setup wizard / server start      License Activation screen
       │                    │
       │              FastAPI backend  ◄──  React dashboard (staff UI)
       │              SQLite database        └── Mobile view (owner phone)
       │
       ├── Wake-on-LAN (magic packet) ──────► Client machines
       │                                       └── Electron agent (cross‑platform)
       │                                           ├── Screen lock / unlock (OS‑specific)
       │                                           ├── Countdown + low-time warning
       │                                           ├── Branded splash screen
       │                                           ├── Health metrics (CPU, RAM, temp)
       │                                           └── Remote commands (restart, message)
       │
       └── Tuya API ───────────────────────► Smart plugs
                                              └── PS5 / Xbox (boot on power restore)
```

The server PC is the only machine that needs to be on wired ethernet. All communication is local — no cloud dependency.  
The agent uses a **platform abstraction layer** inside Electron – the same UI code works on Windows, macOS, and Linux, with OS‑specific modules for lock screen, shutdown, and auto‑start.

---

## Getting Started

### Prerequisites

- Python 3.11+ (any OS)
- Node.js 20+
- Client machines can run Windows, macOS, or Linux (the agent is packaged for each)
- Wake-on-LAN enabled in BIOS for client PCs (if using Ethernet)

### Server setup

```bash
# Clone the repo
git clone https://github.com/AshminDhungana/arcade.git
cd arcade

# Create a virtual environment (recommended)
python -m venv venv
source venv/bin/activate   # or `venv\Scripts\activate` on Windows

# Install Python dependencies
pip install -r requirements.txt

# Install frontend dependencies
cd frontend && npm install && cd ..

# First run — launcher handles license activation, DB init, and the setup wizard
python launcher.py
```

On first launch, the Launcher shows a **License Activation** screen before anything else. It displays a Hardware ID generated from this PC. Send that Hardware ID to Seller to receive a `license.key` file, place it in the app folder (or import it via the Activation screen), and the Launcher will verify it and unlock the setup wizard.

The setup wizard then asks for:

- Cafe name
- Server host and port
- Admin PIN and Cashier PIN

These are saved to `arcade.config.json`. Subsequent launches re-verify the license locally (no internet needed) and skip straight to starting the server.

### Client agent setup

```bash
cd agent
npm install
npm run build        # Produces a distributable in agent/dist/
```

The build step creates platform‑specific packages:

- **Windows**: `.exe` installer (NSIS)
- **macOS**: `.dmg` and `.app` bundle
- **Linux**: AppImage, `.deb`, or `.rpm` (depending on configuration)

Copy the built agent to each client machine and install it. On first run, it will ask for the server address (or you can pre‑configure it). The agent connects back to the server automatically on boot, registers its hardware info, and begins sending health metrics.

### Auto‑start on server boot

- **Windows**: Place a shortcut to `launcher.py` (or the built `.exe`) in the Startup folder, or register it via Task Scheduler.
- **macOS**: Use `launchd` – a sample plist is provided in the repository.
- **Linux**: Use `systemd` or autostart `.desktop` file – sample units are included.

Detailed instructions are available in the `/docs` folder.

---

## Configuration

All runtime config lives in `arcade.config.json` (created by the setup wizard):

```json
{
  "cafe_name": "Arcade",
  "host": "192.168.1.100",
  "port": 8000,
  "db_path": "arcade.db",
  "admin_pin": "****",
  "cashier_pin": "****"
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
2. Session starts → PC unlocks, branded splash shows, timer begins
3. At 5-minute warning → countdown popup on client screen
4. Customer finishes → staff clicks Checkout → invoice generated
5. Payment marked → PC locks → receipt printed

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

PS5 and Xbox cannot run a custom agent. Each console is connected to a **Tuya-compatible smart plug**. The server calls the Tuya API to power plugs on/off when a console session starts or ends. Enable "boot on power restore" in the console's settings once — after that, power-cycling the plug is enough to boot it.

---

## Database Migrations

Arcade uses **Alembic** for schema migrations. Never edit the schema manually.

```bash
# Apply all pending migrations (run automatically on server start)
alembic upgrade head

# Generate a new migration after changing a model
alembic revision --autogenerate -m "add packages table"

# Roll back one step
alembic downgrade -1
```

---

## Build Phases

| Phase                                  | Scope                                                                                                                                                       | Status     |
| -------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- |
| **1 — Core**                           | License activation (offline signature + Hardware ID), Launcher, FastAPI scaffold, Alembic, WoL boot, session API, seat dashboard, Electron agent, WebSocket | 🔲 Planned |
| **2 — Billing, POS & Printing**        | Time billing, food/drink POS, inventory tracking, receipt printing, audit log                                                                               | 🔲 Planned |
| **3 — Members, Packages & Promotions** | Member profiles, wallet, loyalty, time packages, day passes, voucher codes, promotions engine, per-zone pricing, staff roles                                | 🔲 Planned |
| **4 — Operations & Experience**        | Remote PC commands, PC health monitoring, shift management, expense tracking, seat reservations, lock screen upgrade, announcements                         | 🔲 Planned |
| **5 — Events & Analytics**             | Tournament/event mode, analytics dashboard, maintenance mode, configurable feature flags                                                                    | 🔲 Planned |
| **6 — Cross‑Platform Polish**          | Full testing and packaging for Windows, macOS, Linux; auto‑start scripts for all OSes; platform-specific documentation                                      | 🔲 Planned |
| **7 — Growth (V2)**                    | Online booking portal, WhatsApp/SMS notifications, optional WAN remote access, multi-location                                                               | 🔲 Future  |

**Legend:** 🔲 Planned · 🟡 In progress · ✅ Done

---

## V2 Roadmap

These are out of scope for the initial release but architecturally planned for:

- **Online seat booking portal** — public link showing live availability; customers reserve before walking in
- **WhatsApp / SMS notifications** — low-balance alerts, booking confirmations, event broadcasts via Sparrow SMS or WhatsApp Business API
- **Optional WAN access** — read-only owner dashboard accessible from outside the LAN
- **Multi-location support** — one owner account, multiple cafe locations, cross-location reporting
- **Game library management** — track which titles are installed on which machines

---

## License

Arcade is licensed under the **Apache License, Version 2.0**. See [LICENSE](LICENSE) for details.

# Software Requirements Specification

## Arcade — Gaming Cafe Management System

**Document Version:** 2.0  
**Project Version:** 2.0  
**Date:** June 2026  
**Prepared by:** Ashmin Dhungana  
**Status:** Pre‑Development · Design Complete  
**Classification:** Internal / Private

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Overall Description](#2-overall-description)
3. [System Architecture](#3-system-architecture)
4. [Functional Requirements](#4-functional-requirements)
   - 4.1 [System Initialisation](#41-system-initialisation)
   - 4.1a [Licensing and Activation](#41a-licensing-and-activation)
   - 4.2 [Seat Management](#42-seat-management)
   - 4.3 [Session Management](#43-session-management)
   - 4.4 [Billing Engine](#44-billing-engine)
   - 4.5 [Time Packages and Day Passes](#45-time-packages-and-day-passes)
   - 4.6 [Promotions Engine](#46-promotions-engine)
   - 4.7 [Prepaid Vouchers](#47-prepaid-vouchers)
   - 4.8 [Food and Drink POS](#48-food-and-drink-pos)
   - 4.9 [Inventory Tracking](#49-inventory-tracking)
   - 4.10 [Member System](#410-member-system)
   - 4.11 [Seat Reservations](#411-seat-reservations)
   - 4.12 [PC and Console Control](#412-pc-and-console-control)
   - 4.13 [Staff Roles and Authentication](#413-staff-roles-and-authentication)
   - 4.14 [Shift Management](#414-shift-management)
   - 4.15 [Audit Log](#415-audit-log)
   - 4.16 [Expense Tracking](#416-expense-tracking)
   - 4.17 [Analytics Dashboard](#417-analytics-dashboard)
   - 4.18 [Owner Mobile View](#418-owner-mobile-view)
   - 4.19 [Receipts and Printing](#419-receipts-and-printing)
   - 4.20 [Tournament and Event Mode](#420-tournament-and-event-mode)
   - 4.21 [Wake-on-LAN](#421-wake-on-lan)
   - 4.22 [Nightly Backup](#422-nightly-backup)
5. [Non-Functional Requirements](#5-non-functional-requirements)
6. [Feature Flags & Modularity](#6-feature-flags--modularity)
7. [Data Requirements](#7-data-requirements)
8. [External Interface Requirements](#8-external-interface-requirements)
9. [Build Phases](#9-build-phases)
10. [Constraints & Assumptions](#10-constraints--assumptions)
11. [Acceptance Criteria](#11-acceptance-criteria)
12. [Glossary](#12-glossary)

---

## 1. Introduction

### 1.1 Purpose

This Software Requirements Specification (SRS) defines the complete functional and non-functional requirements for **Arcade**, a self-hosted gaming cafe management system. It serves as the authoritative reference for system design, development, testing, and delivery, and is intended for developers, QA engineers, and project stakeholders at Neurotech Biratnagar.

### 1.2 Scope

Arcade is a local-network management platform for independent gaming cafes. It replaces manual timers, paper-based billing, and fragmented tooling with a unified system covering:

- Real-time seat and session management
- Automated billing across multiple pricing models
- Food and drink POS with inventory tracking
- Member accounts, loyalty programs, and time packages
- PC and console remote control via a kiosk overlay on client machines
- Staff shift management and audit logging
- Owner-facing analytics and mobile access
- Tournament and event management

The system runs entirely on the cafe's local network. No internet connection is required during daily operation (except for initial Tuya device pairing, if consoles are used). No cloud infrastructure, subscription fees, or per-seat licensing applies.

**Cross‑platform:** The server (FastAPI + Launcher) runs on Windows, macOS, and Linux. The client agent (Electron) runs on all three operating systems, using a platform abstraction layer for OS‑specific operations, and controls workstations via a **full‑screen kiosk overlay** rather than attempting to lock/unlock the system desktop. This ensures consistent, reliable control across all platforms.

### 1.3 Intended Audience

| Audience              | Use                                               |
| --------------------- | ------------------------------------------------- |
| Software Developers   | Design, implementation, and integration reference |
| QA Engineers          | Test case derivation and acceptance criteria      |
| Project Manager       | Scope definition and milestone planning           |
| Cafe Owner / Operator | Understanding of deliverable capabilities         |

### 1.4 Document Conventions

- **SHALL** — mandatory requirement
- **SHOULD** — recommended but not mandatory
- **MAY** — optional capability
- **FR-XXX** — Functional Requirement identifier
- **NFR-XXX** — Non-Functional Requirement identifier

### 1.5 References

- `README.md` — Arcade system overview and technical stack
- `PRODUCT_BRIEF.md` — Product context, user stories, and build plan
- `Arcade_SDD.md` — Software Design Document (v2.0)
- Alembic documentation — database migration reference
- TinyTuya documentation — local Tuya smart plug control
- RFC 8032 (Ed25519) — digital signature scheme used for offline license verification
- `py-machineid` — cross‑platform machine fingerprinting **without admin privileges** (primary hardware ID source)
- `argon2-cffi` — Python Argon2id implementation (OWASP-recommended PIN/password hashing)
- APScheduler documentation — async-compatible job scheduling for nightly backup
- Electron kiosk mode hardening — OWASP WebSocket Security Cheat Sheet for agent authentication

---

## 2. Overall Description

### 2.1 Product Perspective

Arcade is a greenfield self-hosted application. It does not integrate with or depend on any cloud service during operation (with the exception of an optional, one‑time internet connection for initial Tuya device pairing). The system is designed as a replacement for manual cafe operations and is positioned against cloud-based competitors that charge recurring per-seat fees and require internet connectivity.

### 2.2 Product Functions (Summary)

- Live seat grid with real-time status updates
- Timed session lifecycle management (start, stop, pause, resume)
- Multi-model billing engine with integer-precision arithmetic
- Food and drink POS with optional inventory tracking
- Member account management with wallet, loyalty, and packages
- Remote workstation control via a full‑screen kiosk overlay (instead of OS lock/unlock)
- Console power control via local Tuya LAN API (TinyTuya)
- Staff role management with Staff ID + PIN authentication and shift tracking
- Owner analytics dashboard and mobile-responsive view
- Tournament and event management with bracket tracking
- Thermal and PDF receipt printing
- Configurable feature flags for per-cafe customisation
- Offline, hardware-locked license activation gating first-run setup

### 2.3 User Classes

| User Class     | Description                                                 | Access Level |
| -------------- | ----------------------------------------------------------- | ------------ |
| Admin          | Cafe owner or manager — full system access                  | Full         |
| Cashier        | Counter staff — billing, POS, checkout                      | Restricted   |
| Owner (Mobile) | Read-only view of live status and revenue from phone        | Read-only    |
| Customer       | Indirect — interacts with branded client screen and receipt | None         |

### 2.4 Operating Environment

- **Server OS:** Windows 10/11, macOS 11+, or Linux (Ubuntu 20.04+ / Debian 11+ recommended)
- **Client OS:** Windows 10/11, macOS 11+, or Linux (any modern distribution with Electron support)
- **Network:** Local area network (wired ethernet on server; WiFi acceptable for owner mobile view)
- **Internet:** Not required during daily operation. A temporary internet connection may be needed for initial Tuya device provisioning (if using consoles), but all normal console control is local.
- **Hardware:** Counter PC (server), individual gaming PCs or Macs (clients), PS5/Xbox via Tuya smart plugs
- **Printing:** ESC/POS thermal printer or any regular printer (PDF fallback)

### 2.5 Design Constraints

- All inter-component communication MUST occur exclusively on the local network
- No user or session data shall be transmitted to external servers
- The billing engine MUST store all monetary values as integers in the lowest denomination (paise) to prevent floating-point rounding errors
- The system MUST remain operable if the LAN connection between server and one or more client agents is temporarily interrupted
- The server MUST be the single source of truth for all session timers, but the agent SHALL persist session state locally to recover from disconnections
- The license verification mechanism MUST NOT require an active internet connection or any phone-home call during normal day-to-day operation, once activated
- The client agent SHALL use a **kiosk overlay** to control workstation access, not OS lock/unlock, which is unreliable and inconsistent across platforms
- Agent SHALL store session and configuration data in a local SQLite database for crash recovery

### 2.6 Assumptions and Dependencies

- Client machines run one of the supported OSes (Windows, macOS, Linux) and are capable of running Electron
- Client machines support Wake-on-LAN (if using wired Ethernet)
- Client machines are connected via wired ethernet for reliable WoL and low‑latency communication; WiFi is supported but not recommended for production
- Consoles (PS5, Xbox) have "boot on power restore" enabled in their system settings
- Tuya-compatible smart plugs are used for all consoles; they are paired with the local network using the Tuya app (internet required during pairing only)
- Python 3.11+ and Node.js 20+ are available on the server PC (or the packaged build includes them)
- A thermal printer compatible with `python-escpos` is available (or PDF fallback is acceptable)
- For screenshot capture on macOS, the user may need to grant Screen Recording permission; on Linux, Wayland may require additional D-Bus permissions – these are best-effort and handled gracefully

---

## 3. System Architecture

### 3.1 Component Overview

Arcade is composed of four primary components communicating over LAN:

```
[Power strip ON]
       │
       ▼
Main Counter PC  ──  Arcade Launcher (Tkinter GUI, cross‑platform)
       │                    │
       │              License check (offline, Ed25519 signature + Hardware ID)
       │                    │ pass                          │ fail
       │                    ▼                                ▼
       │           Setup wizard / Server start      License Activation screen
       │                    │
       │              FastAPI Backend  ◄──  React Dashboard (staff UI)
       │              SQLite Database        └── Mobile View (owner phone)
       │
       ├── Wake-on-LAN (magic packet) ──────► Client machines (Windows/macOS/Linux)
       │                                       └── Electron Agent
       │                                           ├── Kiosk overlay (full‑screen, always‑on‑top, hardened)
       │                                           ├── Local SQLite storage (session persistence)
       │                                           ├── Platform abstraction (restart, shutdown, screenshot, overlay)
       │                                           ├── Countdown + low-time warning
       │                                           ├── Branded splash screen
       │                                           ├── Health metrics (CPU, RAM, temp)
       │                                           └── Remote commands (show/hide overlay, message, restart, screenshot)
       │
       └── Local Tuya LAN (TinyTuya) ────────► Smart Plugs
                                              └── PS5 / Xbox (boot on power restore)
```

### 3.2 Component Descriptions

| Component            | Technology                                                       | Responsibility                                                                                                                   |
| -------------------- | ---------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| **Arcade Server**    | Python · FastAPI · Uvicorn · SQLite                              | Authoritative business logic, session timing, database, REST API, WebSocket hub (cross‑platform)                                 |
| **Arcade Dashboard** | React · Vite · TypeScript · TailwindCSS · React Query · Recharts | Staff UI, seat grid, billing, POS, analytics, settings (browser‑based, OS‑agnostic)                                              |
| **Arcade Launcher**  | Python · Tkinter                                                 | GUI wrapper to start/stop the server; setup wizard on first run; displays live logs (cross‑platform)                             |
| **Arcade Agent**     | Electron · React · `systeminformation` · `better-sqlite3`        | Per‑client process; controls kiosk overlay, health metrics, remote command execution, local session persistence (cross‑platform) |

The **agent** uses a platform abstraction layer inside Electron: the same UI code runs on all OSes, while OS‑specific modules handle overlay display, shutdown/restart, screenshot capture, and auto‑start registration. The desktop is never locked/unlocked programmatically; instead, a full‑screen always‑on‑top kiosk overlay blocks user access when a session is not active.

### 3.3 Tech Stack

| Layer           | Technology                                                | Cross‑Platform                |
| --------------- | --------------------------------------------------------- | ----------------------------- |
| Backend API     | Python · FastAPI · Uvicorn                                | ✅                            |
| Database        | SQLite (WAL mode) · SQLAlchemy (async) · Alembic          | ✅                            |
| Frontend        | React · Vite · TypeScript · TailwindCSS · React Query     | ✅                            |
| Server Launcher | Python · Tkinter                                          | ✅                            |
| Client Agent    | Electron · React · `systeminformation` · `better-sqlite3` | ✅                            |
| Console Control | TinyTuya (local LAN)                                      | ✅                            |
| Printing        | `python-escpos` · Browser PDF fallback                    | ✅ (printer driver dependent) |
| Real‑time Comms | WebSockets (exponential backoff reconnection + heartbeat) | ✅                            |
| Charts          | Recharts                                                  | ✅                            |
| Task Queue      | **APScheduler** `AsyncIOScheduler` (nightly backup)       | ✅                            |

### 3.4 Project Structure

```
arcade/
├── backend/
│   ├── api/
│   │   └── routers/          # FastAPI route handlers (async)
│   ├── services/             # Business logic (billing, sessions, members, packages) — async services
│   ├── repositories/         # All database queries (async SQLAlchemy)
│   ├── models/               # SQLAlchemy ORM models
│   ├── schemas/              # Pydantic request/response schemas
│   ├── licensing/            # License file parsing + Ed25519 signature verification, hardware fingerprinting (no admin)
│   └── core/
│       ├── config.py         # Settings loader
│       ├── database.py       # Engine with WAL pragmas, AsyncSession factory
│       ├── security.py       # Argon2id hashing, JWT (60min expiry + token_version), rate limiting, lockout
│       └── ws_manager.py     # WebSocket connection manager (heartbeat, offline queue)
├── frontend/                 # React dashboard (Vite + TailwindCSS)
├── agent/
│   ├── src/
│   │   ├── main/             # Electron main process
│   │   │   ├── index.ts      # entry point
│   │   │   ├── platform/     # OS‑specific modules (overlay, restart, shutdown, screenshot)
│   │   │   │   ├── index.ts  # unified PlatformService interface
│   │   │   │   ├── windows.ts
│   │   │   │   ├── macos.ts
│   │   │   │   └── linux.ts
│   │   │   ├── storage/      # Local SQLite for session persistence
│   │   │   ├── ipc/          # IPC handlers (overlay, screenshot, restart, shutdown)
│   │   │   │   └── handlers.ts
│   │   │   ├── ws/           # WebSocket client (exponential backoff, agent_secret auth)
│   │   │   │   └── client.ts
│   │   │   ├── health/       # systeminformation collector (60s interval)
│   │   │   │   └── collector.ts
│   │   │   └── tray/         # System tray integration
│   │   │       └── tray.ts
│   │   └── renderer/         # React UI (kiosk overlay, splash, countdown, announcements)
│   ├── package.json
│   └── agent.config.json
├── alembic/                  # Database migration scripts
├── launcher.py               # Tkinter GUI launcher (includes Activation screen)
├── arcade.config.json        # Runtime config (created on first run)
└── README.md

tools/                        # NOT shipped to customers — internal only
└── keygen/                   # Offline license generation tool (holds the private signing key)
```

### 3.5 Real-time Communication

- The server SHALL expose WebSocket endpoints for seat status, health metrics, remote commands, and announcements
- WebSocket reconnection SHALL use exponential backoff with jitter
- The server SHALL emit heartbeat pings to detect dead connections (interval: 30 seconds)
- The agent SHALL persist session state locally (SQLite) and synchronise with the server upon reconnection to ensure no billing data is lost
- **Screenshot messages over WebSocket:** The agent SHALL compress screenshots to JPEG at 80% quality and scale down to a maximum of 1280×720 before encoding to base64. The server's `ws_manager.py` SHALL enforce a maximum message size of 5 MB per WebSocket frame and SHALL rate-limit screenshot requests to at most one in-flight per seat.

---

## 4. Functional Requirements

### 4.1 System Initialisation

**FR-SYS-001:** On first launch, the Launcher SHALL check for a valid, activated license before the setup wizard is permitted to run. If no valid license is present, the Launcher SHALL present the License Activation screen (see §4.1a) instead of the setup wizard, and the setup wizard SHALL NOT be reachable until activation succeeds.

**FR-SYS-002:** Once a valid license is confirmed, the Launcher SHALL run a setup wizard prompting for: cafe name, server host (IP), server port, admin Staff ID + PIN, and cashier Staff ID + PIN.

**FR-SYS-003:** The setup wizard output SHALL be saved to `arcade.config.json`. Subsequent launches SHALL skip both license activation (if already valid) and the wizard, and start the server directly.

**FR-SYS-004:** On server startup, Alembic migrations SHALL be applied automatically (`alembic upgrade head`).

**FR-SYS-005:** On server startup, the system SHALL send Wake-on-LAN magic packets to all registered client PC MAC addresses to boot them.

**FR-SYS-006:** The Launcher SHALL display live server logs and a health indicator in its GUI.

**FR-SYS-007:** The system SHALL expose a health check endpoint at `/health` returning server status, uptime, database connectivity, and license status.

**FR-SYS-008:** On every Launcher start (not just first run), the Launcher SHALL re-verify the locally stored license file's signature and hardware-fingerprint match before starting the server. If verification fails, the server SHALL NOT start and the License Activation screen SHALL be shown instead.

**FR-SYS-009:** The server SHALL be started using the `lifespan` context manager pattern (FastAPI 0.93+). Startup logic (database connection, scheduler start) and shutdown logic (WebSocket closure, scheduler shutdown, database pool disposal) SHALL be contained within a single `@asynccontextmanager` lifespan function, replacing the deprecated `@app.on_event("shutdown")` decorator.

**FR-SYS-010:** If the Launcher window is closed while the server is running, the Launcher SHALL prompt the user with a confirmation dialog: "The Arcade server is still running. Closing the Launcher will stop the server. Are you sure?" If confirmed, the server SHALL be terminated gracefully.

---

### 4.1a Licensing and Activation

This subsection defines the offline, hardware-locked, perpetual licensing mechanism that gates first-run setup. It exists to support commercial distribution of Arcade as a one-time-purchase product across independently owned cafes, while preserving the system's zero-cloud, zero-recurring-dependency design.

**Licensing model summary:**

| Aspect          | Decision                                                                                                                                                        |
| --------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| License type    | Perpetual (one-time purchase, no expiry, no recurring fee)                                                                                                      |
| Binding         | Hardware-locked to the counter PC running the server                                                                                                            |
| Activation mode | Fully offline — no license server, no internet call required at runtime                                                                                         |
| Verification    | Asymmetric cryptographic signature (Ed25519); private key held only by Neurotech Biratnagar                                                                     |
| Distribution    | Each license is a small signed file (`license.key`), generated per-sale using an internal keygen tool, delivered to the customer out-of-band (email, USB, etc.) |

**FR-LIC-001:** The application binary SHALL embed only the Ed25519 **public** key used to verify license signatures. The corresponding private signing key SHALL NEVER be present in the distributed application, its source repository, or any client-accessible file.

**FR-LIC-002:** On first launch with no `license.key` present, the Launcher SHALL compute a Hardware ID using **`py-machineid`** as the primary source (no admin privileges required). If `py-machineid` returns an empty result, the system SHALL fall back to combining available OS-specific identifiers (MAC address, motherboard serial, disk serial) and hash the result with SHA256. The Hardware ID SHALL be deterministic across reboots on the same machine and **SHALL NOT require administrator or root privileges** to generate. Missing individual identifiers SHALL NOT fail activation — the system uses whatever is available.

**FR-LIC-003:** The Launcher SHALL display the computed Hardware ID in the License Activation screen in a clearly copyable format, along with instructions for the cafe owner to send it to Neurotech Biratnagar to receive their `license.key`.

**FR-LIC-004:** A license SHALL be generated using an internal, offline keygen tool (distributed separately from the product, never shipped to customers) that accepts: the customer's Hardware ID, cafe name, license type, and issue date, and produces a `license.key` file signed with the private key.

**FR-LIC-005:** The `license.key` file SHALL be a structured payload (e.g. JSON) containing: cafe name, Hardware ID, license type, issue date, and an Ed25519 signature over the payload. The file MAY be base64-encoded for ease of transport but SHALL NOT be encrypted (signature, not secrecy, is the integrity mechanism).

**FR-LIC-006:** On activation, the cafe owner SHALL place the received `license.key` file in the application's root directory (`arcade/license.key`) or import it via a file picker in the Activation screen.

**FR-LIC-007:** The Launcher SHALL verify a presented `license.key` by: (a) verifying the Ed25519 signature against the embedded public key, and (b) confirming the Hardware ID inside the license payload matches the Hardware ID computed for the current machine. Both checks SHALL pass for activation to succeed.

**FR-LIC-008:** If signature verification fails, or the Hardware ID does not match, the Launcher SHALL reject the license, SHALL NOT proceed to setup or server start, and SHALL display a clear error distinguishing "invalid license file" from "license does not match this machine."

**FR-LIC-009:** Once activated, license verification SHALL be performed locally on every Launcher start (FR-SYS-008). No network call SHALL be required for this check.

**FR-LIC-010:** If the cafe's counter PC hardware changes such that the Hardware ID no longer matches, the system SHALL support re-activation by the owner contacting Neurotech Biratnagar with the new Hardware ID to receive a reissued `license.key`. This is a manual, support-driven process in V1; no self-service transfer flow is in scope.

**FR-LIC-011:** The system SHALL support a time-limited evaluation/demo mode (e.g. a license payload field marking it as a trial with an expiry date) for prospective customers, gated by the same signature mechanism.

**FR-LIC-012:** License status (cafe name, activation date, license type, hardware-match status) SHALL be viewable by Admin users from within Settings once the system is running.

**FR-LIC-013:** Tampering with or deleting `license.key` after activation SHALL cause the next Launcher start to fall back to the License Activation screen (per FR-SYS-008); it SHALL NOT crash the application or corrupt existing session/billing data.

**FR-LIC-014:** The system SHALL maintain a `license_status` table in the database as a read-only cache for display purposes. The Launcher SHALL populate this table after a successful license check. The table SHALL NOT be used for enforcement — the source of truth is always the signed `license.key` file.

---

### 4.2 Seat Management

**FR-SEAT-001:** The dashboard SHALL display all seats in a colour-coded grid reflecting real-time status.

**FR-SEAT-002:** Seat statuses SHALL include at minimum: Available, In Use, Reserved, Paused, Maintenance, Offline, Booting, Unreachable (see FR-WOL-006).

**FR-SEAT-003:** Seats SHALL be grouped into configurable zones. Supported zone types include: Standard PC, VIP PC, Console Corner, and Other.

**FR-SEAT-004:** Each seat tile SHALL display: seat name/number, zone, current status, current customer (if any), and elapsed session time.

**FR-SEAT-005:** The dashboard SHALL update seat statuses in real time via WebSocket without requiring a page refresh.

**FR-SEAT-006:** Staff SHALL be able to mark any seat as "Maintenance" with an optional note. The system SHALL track per-machine downtime duration.

**FR-SEAT-007:** The system SHALL record each seat's MAC address during agent registration and associate it permanently with that seat.

---

### 4.3 Session Management

**FR-SES-001:** Staff SHALL be able to start a session on any available seat by selecting the seat and optionally selecting a member account or entering a walk-in identifier.

**FR-SES-002:** Sessions SHALL be started, stopped, paused, and resumed from the dashboard.

**FR-SES-003:** The server SHALL be the authoritative holder of all session timers.

**FR-SES-004:** The agent SHALL cache the session start time locally in a persistent SQLite database. If the LAN connection drops, the agent SHALL continue tracking elapsed time locally. On reconnection, the agent SHALL send a SYNC message with local elapsed time, and the server SHALL reconcile and correct if needed.

**FR-SES-005:** No billing data SHALL be lost due to a temporary LAN interruption between the server and an agent, or due to an agent crash/reboot.

**FR-SES-006:** When a session is started, the system SHALL check and lock in: the applicable pricing rate, any active package entitlement, and any active promotion. These SHALL NOT change mid-session.

**FR-SES-007:** At 5 minutes remaining in a timed package, the agent SHALL display a low-time warning popup on the client screen.

**FR-SES-008:** When a session ends, the server SHALL trigger the agent to show the kiosk overlay (blocking desktop access) and SHALL generate an invoice.

**FR-SES-009:** If the server crashes or restarts while sessions are active, the system SHALL reconcile active sessions when agents reconnect. The server SHALL preserve all session records in the database and SHALL NOT lose committed data.

---

### 4.4 Billing Engine

**FR-BILL-001:** All monetary values SHALL be stored as integers in paise (lowest denomination) to eliminate floating-point rounding errors.

**FR-BILL-002:** The billing engine SHALL support the following pricing models simultaneously:

- Per-minute rate
- Flat hourly rate
- Time-block rate (e.g., billed per 30-minute block)
- Peak and off-peak rates configurable by time of day and day of week
- Device-type-specific pricing (PC ≠ PS5 ≠ VR)

**FR-BILL-003:** The applicable rate SHALL be determined and locked at session start. Mid-day rate changes SHALL NOT affect in-progress sessions.

**FR-BILL-004:** If a customer has an active time package, the billing engine SHALL draw from the package first before applying per-minute billing.

**FR-BILL-005:** When a package runs out mid-session, the billing engine SHALL automatically switch to per-minute billing for the remaining time.

**FR-BILL-006:** If an applicable promotion is active at session start, the billing engine SHALL apply the discount and record the promotion type and amount in the session record.

**FR-BILL-007:** Member loyalty tier discounts SHALL be applied as a percentage reduction on the time charge.

**FR-BILL-008:** The checkout invoice SHALL itemise: time charge, package usage (if applicable), discount applied and reason (if applicable), all food and drink items, and the final total.

**FR-BILL-009:** Staff SHALL be able to mark payment as cash, card, wallet, or package. Payment method SHALL be recorded and printed on the receipt.

**FR-BILL-010:** Package balance updates SHALL be performed atomically using `UPDATE ... WHERE remaining_minutes >= amount` to prevent race conditions when multiple sessions attempt to draw from the same package simultaneously.

---

### 4.5 Time Packages and Day Passes

**FR-PKG-001:** The system SHALL support the following package types: hour bundle (e.g., 10 hours purchased and used across visits), day pass (unlimited play for a calendar day), night pass (time-windowed), and monthly pass.

**FR-PKG-002:** Packages SHALL be purchasable and associated with a member account.

**FR-PKG-003:** The system SHALL track remaining package time per member and display it at session start.

**FR-PKG-004:** Package entitlement SHALL draw down in real time as the session progresses.

**FR-PKG-005:** Packages and promotions MAY be restricted to specific seat zones as configured in Settings.

---

### 4.6 Promotions Engine

**FR-PROMO-001:** The system SHALL support the following promotion types:

- Happy hour (specific time windows)
- Flash discount (e.g., 20% off Tuesday evenings)
- First-visit discount for new member accounts
- Group discount when multiple seats are booked simultaneously
- Birthday month bonus time or percentage discount

**FR-PROMO-002:** Promotions SHALL be configured in Settings with a name, type, value, and validity schedule.

**FR-PROMO-003:** The billing engine SHALL evaluate and apply at most one promotion at session start (highest-value or first-matching, as configured).

**FR-PROMO-004:** The applied promotion name and discount amount SHALL be stored in the session record and printed on the receipt.

---

### 4.7 Prepaid Vouchers

**FR-VCH-001:** Admin users SHALL be able to generate batches of one-time-use voucher codes.

**FR-VCH-002:** Voucher codes SHALL be printable as QR codes or alphanumeric slips.

**FR-VCH-003:** Voucher codes SHALL be redeemable at the counter (by staff) or at the client screen (by the customer).

**FR-VCH-004:** Once a voucher code is redeemed, the system SHALL mark it as used. It SHALL NOT be redeemable again.

**FR-VCH-005:** Voucher codes SHALL support an optional expiry date. Expired codes SHALL be rejected on redemption.

---

### 4.8 Food and Drink POS

**FR-POS-001:** Staff SHALL be able to add menu items to any open session tab from the dashboard at any point during the session.

**FR-POS-002:** POS items SHALL be associated with the seat (not the customer).

**FR-POS-003:** The final invoice SHALL itemise all POS items alongside the time charge.

**FR-POS-004:** Menu items SHALL be configurable in Settings with a name, price, and optional category.

---

### 4.9 Inventory Tracking

**FR-INV-001:** Each menu item MAY optionally have a current stock level tracked.

**FR-INV-002:** When a POS item is added to a session, its stock level SHALL decrement by the quantity ordered.

**FR-INV-003:** When a menu item's stock reaches the configured low-stock threshold, a visual badge SHALL appear on the POS screen.

**FR-INV-004:** When a menu item's stock reaches zero, it SHALL be visually greyed out in the POS and SHALL NOT be addable to any bill.

**FR-INV-005:** Admin users SHALL be able to record restock events with a quantity and timestamp via the admin panel. Each restock event SHALL be logged permanently.

---

### 4.10 Member System

**FR-MEM-001:** The system SHALL support member accounts with the following attributes: name, phone number, prepaid credit wallet balance, loyalty points, tier, visit history, and total hours played.

**FR-MEM-002:** Members SHALL be looked up at session start by phone number or member ID.

**FR-MEM-003:** Walk-in customers WITHOUT a member account SHALL be fully supported — sessions start and end normally, billed at standard rate with no loyalty features.

**FR-MEM-004:** The member wallet SHALL support top-ups by cash, card, or voucher.

**FR-MEM-005:** Loyalty points SHALL accrue per session based on configurable rules and SHALL be redeemable for discounts or session time.

**FR-MEM-006:** Membership tiers (e.g., Bronze, Silver, Gold) SHALL apply percentage discounts configurable in Settings.

**FR-MEM-007:** The system SHALL display a member's active packages, wallet balance, and loyalty tier at session start.

---

### 4.11 Seat Reservations

**FR-RES-001:** Staff SHALL be able to reserve one or more seats in advance, specifying customer name, number of seats, and time slot.

**FR-RES-002:** Reserved seats SHALL appear on the dashboard grid with the customer name and scheduled start time.

**FR-RES-003:** Staff SHALL be able to start sessions for all seats in a group reservation simultaneously.

**FR-RES-004:** Walk-in customers viewing reserved seats SHALL be able to see which seats become available and when.

---

### 4.12 PC and Console Control

#### 4.12.1 Client Agent (Cross‑Platform) — Kiosk Overlay

**FR-AGENT-001:** The Electron agent SHALL automatically connect to the server on boot, register its hardware info (MAC address, hostname, OS version, hardware specs), and begin sending health metrics. The agent SHALL obtain its `seat_id` from the `agent.config.json` file, which SHALL be created during setup.

**FR-AGENT-002:** The agent SHALL run a full‑screen, always‑on‑top kiosk overlay when no active session is present. This overlay SHALL block access to the desktop and display:

- Cafe logo and branding
- Announcements and promotions
- "Call Staff" button (which sends a notification to the dashboard)
- (When session active) remaining time and low‑time warnings

**FR-AGENT-002a (Kiosk Hardening):** The agent's `BrowserWindow` SHALL be configured with:

- `kiosk: true` — enables Electron's native kiosk mode (blocks Cmd+Tab, Cmd+Space on macOS)
- `fullscreen: true`, `alwaysOnTop: true`, `frame: false`, `closable: false` — prevents Alt+F4/Cmd+Q closing
- `webPreferences.devTools: false`, `sandbox: true`, `contextIsolation: true`, `nodeIntegration: false` — disables DevTools and prevents renderer process privilege escalation

**FR-AGENT-002b (Global Shortcut Interception):** The agent SHALL register and consume the following global keyboard shortcuts to prevent bypass:

- `Alt+F4` (Windows/Linux) and `CommandOrControl+W`, `CommandOrControl+Q` (macOS/Windows) — prevent application closure
- `F12`, `Alt+Shift+I`, `CommandOrControl+Shift+I` — prevent DevTools opening
- `CommandOrControl+P` — prevent print dialog (which can provide OS shell access on Windows)

These shortcuts SHALL be registered in the main process and discarded (no-op handlers). Known limitations: `Ctrl+Alt+Del` on Windows cannot be intercepted without a dedicated SAS filter driver or Windows Kiosk Mode assignment; this is documented as a known platform gap. On Linux, Wayland compositors may require additional configuration for `alwaysOnTop` to work reliably across all DEs; the agent SHALL gracefully degrade with a fallback to a maximised window if the compositor does not support always‑on‑top.

**FR-AGENT-003:** When a session starts, the server SHALL send a `HIDE_OVERLAY` command to the agent, removing the overlay and giving the user full access to the desktop. A branded splash screen (5 seconds) SHALL be shown transiently after the overlay is hidden, displaying session info and the menu. The splash screen SHALL be implemented as a temporary overlay window that auto-closes after 5 seconds.

**FR-AGENT-004:** When a session ends or is paused, the server SHALL send a `SHOW_OVERLAY` command, re‑enabling the overlay to block access.

**FR-AGENT-005:** The agent SHALL send health metrics to the server every 60 seconds including: CPU usage (%), RAM usage (%), CPU temperature, and disk space.

**FR-AGENT-006:** The agent SHALL receive and execute remote commands from the server:

- `SHOW_OVERLAY` — show the overlay (block desktop)
- `HIDE_OVERLAY` — hide the overlay (allow access)
- `SHOW_MESSAGE` — display an announcement overlay
- `RESTART` — restart the PC (OS‑specific)
- `SHUTDOWN` — shutdown the PC (OS‑specific)
- `TAKE_SCREENSHOT` — capture screen and return image (best‑effort)

**FR-AGENT-006a (Screenshot Constraints):** The `TAKE_SCREENSHOT` command SHALL return a screenshot compressed as JPEG at 80% quality, scaled to a maximum of 1280×720, and encoded as base64. The agent SHALL NOT return full‑resolution PNG screenshots. The maximum WebSocket message size SHALL be limited to 5 MB per frame, enforced on both the agent and server sides.

**FR-AGENT-007:** The agent SHALL implement a platform abstraction layer that exposes a unified interface for overlay management, restart, shutdown, screenshot, and auto‑start. OS‑specific implementations SHALL be selected at runtime based on `process.platform`:

- **Windows:** overlay using `setAlwaysOnTop` and `kiosk` mode; restart/shutdown via `shutdown`; screenshot via `desktopCapturer`; auto‑start via registry.
- **macOS:** overlay using `setAlwaysOnTop` and `kiosk`; restart/shutdown via `sudo shutdown`; screenshot via `desktopCapturer` (requires Screen Recording permission); auto‑start via LaunchAgent plist.
- **Linux:** overlay using `setAlwaysOnTop` and `kiosk`; restart/shutdown via `systemctl`/`shutdown`; screenshot via `desktopCapturer` (Wayland may require additional permissions); auto‑start via `.desktop` file.

**FR-AGENT-008:** The agent SHALL persist session state locally in a SQLite database, including session ID, start time, last sync time, local elapsed seconds, and disconnect count. This state SHALL be written every 10 seconds, on every reconnect, and on every pause/resume/end.

**FR-AGENT-009:** If the WebSocket connection drops, the agent SHALL continue tracking elapsed time locally and queue any non‑critical commands (messages, announcements, overlay changes) for later delivery. Upon reconnection, it SHALL send a SYNC message containing the local session data. Commands like `RESTART` and `SHUTDOWN` SHALL NOT be queued; they are ignored if the agent is offline.

**FR-AGENT-010:** The agent SHALL reconnect using exponential backoff with jitter, starting at 2 seconds and capping at 60 seconds. Heartbeat pings SHALL be sent every 30 seconds to detect disconnections.

**FR-AGENT-011 (Agent Authentication):** Each agent SHALL authenticate to the server using a **randomly generated agent secret** (`agent_secret`) created during the setup wizard and stored in `arcade.config.json`. The server SHALL generate a unique secret for each seat using `secrets.token_hex(32)` and embed it in the agent's `agent.config.json` during deployment. The server SHALL validate the agent secret on every REGISTER message and on every reconnection. `agent.config.json` SHALL be treated as a secret file; its file permissions SHALL be set to owner‑read‑only on Linux and macOS (chmod 600).

**FR-AGENT-012 (Agent Offline Session Start):** The agent SHALL NOT allow starting a new session when the server is offline. All sessions MUST be initiated by the server via the dashboard. If a user attempts to start a session while the agent is offline, the agent SHALL display a message: "Server unreachable. Please contact staff."

#### 4.12.2 Remote Commands (Dashboard)

**FR-CMD-001:** Staff SHALL be able to trigger a remote restart of any client PC from the dashboard.

**FR-CMD-002:** Staff SHALL be able to trigger a remote shutdown of any or all client PCs from the dashboard.

**FR-CMD-003:** Staff SHALL be able to send an announcement message that displays as an overlay on one or all client screens.

**FR-CMD-004:** Admin users SHALL be able to request a screenshot of any client PC screen from the dashboard. If screenshot capture is not supported on the client platform, the dashboard SHALL display an informative message and not fail silently.

**FR-CMD-005:** Screenshot requests SHALL be rate-limited to at most one in-flight screenshot per seat. The dashboard SHALL disable the screenshot button for a seat until the response is received or times out after 10 seconds.

#### 4.12.3 Console Control (Local Tuya LAN)

**FR-CON-001:** The system SHALL control console power state (on/off) via **local LAN communication** using the TinyTuya library, eliminating the need for cloud API calls during normal operation.

**FR-CON-002:** When a console session starts, the system SHALL send a power-on command to the corresponding Tuya smart plug via the local network using the device's `local_key` and `ip_address`.

**FR-CON-003:** When a console session ends, the system SHALL send a power-off command via the same local method.

**FR-CON-004:** Console smart plugs SHALL be configured in Settings with the following fields per device: `device_id`, `local_key`, `ip_address`, and `protocol_version`. An initial one‑time pairing (requiring internet) is performed via the Tuya app to retrieve these values, after which no internet is needed.

---

### 4.13 Staff Roles and Authentication

**FR-AUTH-001:** The system SHALL support two staff roles: Admin and Cashier.

**FR-AUTH-002:** Admin users SHALL have full access to all features including settings, reports, expense tracking, and screenshot commands.

**FR-AUTH-003:** Cashier users SHALL have access to billing, POS, session management, and checkout only. They SHALL NOT access settings, reports, or admin commands.

**FR-AUTH-004:** Authentication SHALL use a **Staff ID + PIN** combination. Each staff member has a unique ID (e.g., "S001") and a secret PIN.

**FR-AUTH-005:** PINs SHALL be stored hashed using **Argon2id** (via `argon2-cffi`). The system SHALL never store plaintext PINs. Argon2id is the OWASP-recommended algorithm for new systems; no bcrypt fallback shall be implemented.

**FR-AUTH-006:** After 5 consecutive failed PIN attempts for a given Staff ID, the system SHALL enforce a 60-second lockout before allowing further attempts for that account.

**FR-AUTH-007:** Successful authentication SHALL issue a JWT token with a default expiry of 60 minutes. The JWT payload SHALL include a `token_version` claim matching the staff record's `token_version` field. Changing a staff member's PIN or forcibly deactivating an account SHALL increment `token_version`, immediately invalidating all previously issued tokens for that account without requiring a token blacklist.

**FR-AUTH-007a:** The staff table SHALL include a `token_version` integer column (default 0). `POST /api/staff/{id}/deactivate` and `POST /api/staff/{id}/change-pin` SHALL increment this value atomically. Every protected endpoint SHALL validate the `token_version` claim against the current DB value and return HTTP 401 if they do not match.

**FR-AUTH-008:** All sensitive operations SHALL be tagged with the authenticated staff member's identity in the audit log.

**FR-AUTH-009:** Authentication endpoint (`/api/auth/login`) SHALL be rate-limited to 5 attempts per minute per client IP to prevent brute-force attacks.

**FR-AUTH-010:** The JWT signing secret SHALL be generated during the setup wizard using `secrets.token_hex(32)` and stored in `arcade.config.json`.

---

### 4.14 Shift Management

**FR-SHIFT-001:** Staff SHALL open a shift by entering the cash float amount at the start of a working period.

**FR-SHIFT-002:** Staff SHALL close a shift by entering the counted cash amount. The system SHALL calculate the expected cash, the actual cash, and the discrepancy.

**FR-SHIFT-003:** All sessions and transactions during a shift SHALL be tagged to the active shift.

**FR-SHIFT-004:** The shift report SHALL include: total revenue, session count, average session duration, payment method breakdown, cash expected, cash counted, and discrepancy.

**FR-SHIFT-005:** Admin users SHALL be able to view any past shift report at any time.

---

### 4.15 Audit Log

**FR-AUDIT-001:** The system SHALL maintain a write-only audit log of all sensitive operations. Logged events SHALL include at minimum: staff login/logout, session start/stop/override, payment recorded, member wallet top-up, voucher generation and redemption, price/settings changes, and screenshot commands.

**FR-AUDIT-002:** Each audit log entry SHALL include: timestamp, staff identity, action type, and affected entity (seat ID, member ID, session ID, etc.).

**FR-AUDIT-003:** Audit log entries SHALL NOT be editable or deletable by any user role. They are append‑only. This is enforced at the application level; direct database access is not protected by the application.

**FR-AUDIT-004:** Audit logs SHALL be backed up nightly together with the main database.

---

### 4.16 Expense Tracking

**FR-EXP-001:** Admin users SHALL be able to log expense entries in the following categories: rent, electricity, internet, restocking, hardware, maintenance, wages, and other.

**FR-EXP-002:** Each expense entry SHALL include: date, category, amount, and optional note.

**FR-EXP-003:** The analytics dashboard SHALL display gross revenue minus logged expenses as an approximate P&L estimate for any configurable date range.

---

### 4.17 Analytics Dashboard

**FR-ANALYTICS-001:** The analytics dashboard SHALL display the following real-time and historical data:

- Today's total revenue, session count, and average session length
- Busiest hour of the current day
- Weekly revenue trend (bar chart)
- Top-selling POS items by quantity and revenue
- Seat utilisation percentage by zone and time of day
- Member registrations, active vs lapsed members, and top spenders
- Active health alerts (overheating machines, low-stock items)
- Upcoming reservations for the day
- Wake‑on‑LAN success rate and offline machine count

**FR-ANALYTICS-002:** All analytics data SHALL be derived exclusively from the local SQLite database. No external analytics service SHALL be required.

**FR-ANALYTICS-003:** Charts SHALL be implemented using Recharts.

---

### 4.18 Owner Mobile View

**FR-MOB-001:** The React dashboard SHALL be fully mobile-responsive and accessible from any device on the cafe WiFi via a web browser.

**FR-MOB-002:** The mobile view SHALL display at minimum: live seat status grid, today's revenue summary, and any active health alerts.

---

### 4.19 Receipts and Printing

**FR-PRINT-001:** The system SHALL print receipts to a thermal printer via `python-escpos`.

**FR-PRINT-002:** The system SHALL support PDF receipt generation as a fallback for any regular printer (via browser print).

**FR-PRINT-003:** Every receipt SHALL include: seat number, customer name (if member), session start and end time, duration, time charge, package used (if applicable), discount applied (if applicable), itemised food/drink items, total amount, and payment method.

---

### 4.20 Tournament and Event Mode

**FR-EVT-001:** Admin users SHALL be able to create events with: name, game title, date/time, entry fee, and prize pool.

**FR-EVT-002:** Staff SHALL be able to register participants (members or walk-ins) and assign them to specific seats.

**FR-EVT-003:** The system SHALL support single-elimination and double-elimination bracket formats.

**FR-EVT-004:** Staff SHALL be able to record match results and advance brackets from the dashboard.

**FR-EVT-005:** Entry fees SHALL be charged to member wallets or as standalone transactions.

**FR-EVT-006:** The event summary SHALL display all results, bracket progression, prize pool amount, and total revenue generated by the event.

---

### 4.21 Wake-on-LAN

**FR-WOL-001:** The system SHALL send Wake-on-LAN magic packets to all registered client PC MAC addresses on server startup.

**FR-WOL-002:** Client PC MAC addresses SHALL be registered automatically when the Electron agent first connects to the server.

**FR-WOL-003:** Staff SHALL be able to trigger a Wake-on-LAN packet to any individual seat from the dashboard.

**FR-WOL-004:** The system SHALL track the success rate of Wake-on-LAN attempts per seat and display a reliability metric.

**FR-WOL-005:** After sending a WoL packet, the server SHALL wait up to 60 seconds for the agent to connect and send a heartbeat. If no connection is received within that time, the seat SHALL be marked as **UNREACHABLE** on the dashboard.

**FR-WOL-006:** Dashboard seat statuses SHALL include: ONLINE, BOOTING, OFFLINE, UNREACHABLE to reflect WoL outcomes.

**FR-WOL-007:** Staff SHALL be able to manually mark a seat as "powered on" (override) if WoL fails but the machine was started manually.

---

### 4.22 Nightly Backup

**FR-BACKUP-001:** The system SHALL automatically create a backup of the SQLite database each night at a configurable time (default: 3:00 AM) using **APScheduler's `AsyncIOScheduler`** integrated with FastAPI's lifespan.

**FR-BACKUP-002:** Backups SHALL be stored in a configurable local directory.

**FR-BACKUP-003:** The system SHALL retain a configurable number of recent backups (default: 30 days) and delete older ones automatically.

**FR-BACKUP-004:** The backup scheduler SHALL be started within the FastAPI `lifespan` startup phase and shut down cleanly during the `lifespan` shutdown phase (FR-SYS-009).

**FR-BACKUP-005:** The backup schedule time SHALL be configurable via the Settings UI.

---

## 5. Non-Functional Requirements

### 5.1 Performance

**NFR-PERF-001:** The seat dashboard SHALL reflect seat status changes within 1 second of the triggering event under normal LAN conditions.

**NFR-PERF-002:** Session start and checkout operations SHALL complete within 10 seconds of staff interaction under normal conditions.

**NFR-PERF-003:** The API SHALL handle at least 50 concurrent WebSocket connections without performance degradation (supporting cafes with up to 50 seats).

**NFR-PERF-004:** Health metrics collection from each agent (every 60 seconds) SHALL NOT measurably impact client PC gaming performance.

**NFR-PERF-005:** Dashboard initial load time SHALL be under 3 seconds on a local network.

### 5.2 Reliability and Availability

**NFR-REL-001:** The system SHALL remain operational if one or more client agents lose LAN connectivity temporarily.

**NFR-REL-002:** No billing or session data SHALL be lost due to a LAN interruption between the server and any agent, or due to an agent crash, because the agent persists session state locally.

**NFR-REL-003:** WebSocket connections SHALL reconnect automatically using exponential backoff with jitter after any disconnection.

**NFR-REL-004:** The server SHALL detect dead WebSocket connections via heartbeat pings (interval: 30 seconds) and mark the affected seat as "Offline" on the dashboard.

**NFR-REL-005:** The system SHALL recover from a server restart without losing any committed session or billing data. Active sessions SHALL be reconciled when agents reconnect.

**NFR-REL-006:** Agents SHALL queue non‑critical commands (messages, announcements, overlay changes) while offline and deliver them upon reconnection.

### 5.3 Security

**NFR-SEC-001:** All staff PINs SHALL be stored hashed using **Argon2id** (`argon2-cffi`). PINs SHALL NOT be stored in plaintext. No bcrypt fallback shall be implemented.

**NFR-SEC-002:** Staff authentication SHALL use Staff ID + PIN and issue a JWT token with a **60-minute expiry** and a `token_version` claim. The `token_version` claim SHALL be validated on every protected request; a mismatch SHALL return HTTP 401 and force re-login.

**NFR-SEC-003:** Authentication endpoints SHALL be rate-limited to 5 attempts per minute per IP.

**NFR-SEC-004:** The screenshot command SHALL be restricted to Admin role only.

**NFR-SEC-005:** The audit log SHALL be append-only. No user role SHALL be able to modify or delete audit log entries through the application interface.

**NFR-SEC-006:** The system SHALL NOT transmit any customer or billing data to external servers.

**NFR-SEC-007:** All network communication SHALL remain confined to the local network during normal operation.

**NFR-SEC-008:** The Electron agent SHALL authenticate to the server using a **randomly generated agent secret** (`agent_secret`) created during the setup wizard and stored in `arcade.config.json` and in each agent's `agent.config.json`. The secret SHALL be generated using a cryptographically secure random generator (`secrets.token_hex(32)`) and SHALL NOT be hardcoded in the source repository or any distributable installer. `agent.config.json` SHALL be treated as a secret file (not world-readable; file permissions SHALL be set to owner-read-only on Linux and macOS).

### 5.4 Usability

**NFR-USE-001:** The counter dashboard SHALL be operable by a staff member with no technical background after a brief orientation.

**NFR-USE-002:** A session start-to-checkout workflow SHALL require no more than 5 mouse clicks under normal conditions.

**NFR-USE-003:** The Launcher SHALL require only a double-click to start the server. No command line interaction SHALL be required for daily operation.

**NFR-USE-004:** The setup wizard SHALL complete in under 5 minutes for a first-time installation.

**NFR-USE-005:** The dashboard SHALL display only UI elements for features that are currently enabled via feature flags.

### 5.5 Maintainability

**NFR-MAINT-001:** All database schema changes SHALL be managed exclusively through Alembic migration scripts. Direct schema edits SHALL NOT be performed.

**NFR-MAINT-002:** The backend SHALL follow a layered architecture: routers (HTTP), services (business logic), repositories (data access), and models (ORM). All database operations SHALL be asynchronous (`async def`) using SQLAlchemy's `AsyncSession` to prevent blocking the FastAPI event loop.

**NFR-MAINT-003:** Feature flags SHALL be toggleable from the Settings UI without requiring code changes or server restarts.

**NFR-MAINT-004:** The server SHALL support graceful shutdown: completing in-progress requests and flushing any pending state before exit, implemented via the `lifespan` context manager.

**NFR-MAINT-005:** Application logs SHALL be rotated to prevent unbounded disk growth.

### 5.6 Portability and Installation

**NFR-PORT-001:** The server setup SHALL be completable via the commands specified in the README without additional system configuration on Windows, macOS, and Linux.

**NFR-PORT-002:** The Electron agent SHALL produce platform-specific distributables:

- Windows: `.exe` installer (NSIS)
- macOS: `.dmg` and `.app` bundle
- Linux: AppImage, `.deb`, or `.rpm` (configurable)

**NFR-PORT-003:** The server SHALL be packageable as a standalone executable via PyInstaller (or equivalent) for each OS, so that end-users do not need Python installed.

**NFR-PORT-004:** The Launcher SHALL detect the operating system and adjust file paths accordingly (using `os.path.join` or `pathlib`) and use OS‑appropriate system calls for startup and shutdown.

### 5.7 Data Integrity

**NFR-DATA-001:** SQLite SHALL operate in WAL (Write-Ahead Logging) mode to eliminate read/write blocking under concurrent access.

**NFR-DATA-001a:** The SQLite connection SHALL configure the following pragmas on every connection open:

- `PRAGMA busy_timeout=5000` — wait up to 5 seconds before raising `SQLITE_BUSY` instead of failing immediately. This is mandatory to prevent lock errors under normal cafe concurrency.
- `PRAGMA synchronous=NORMAL` — safe with WAL; significantly faster than FULL without data-loss risk on crash.
- `PRAGMA foreign_keys=ON` — enforce referential integrity.
- `PRAGMA wal_autocheckpoint=1000` — checkpoint every ~4MB to limit WAL file growth.

**NFR-DATA-001b:** All `updated_at` fields SHALL be set explicitly in service code (`entity.updated_at = datetime.utcnow()`) rather than relying on SQLAlchemy's `onupdate` trigger or database‑level DEFAULT to ensure reliable updates with async operations.

**NFR-DATA-002:** All monetary calculations SHALL use integer arithmetic in paise throughout. Conversion to display format (rupees) SHALL occur only at the presentation layer.

**NFR-DATA-003:** Rates, discounts, and package balances SHALL be recorded in the session record at the time of the session to ensure historical accuracy regardless of future settings changes.

---

## 6. Feature Flags and Modularity

All optional features SHALL be togglable via the Settings screen. The dashboard SHALL hide all UI elements associated with a disabled feature.

| Flag                         | Feature                                                | Default |
| ---------------------------- | ------------------------------------------------------ | ------- |
| `enable_members`             | Member accounts, wallet, loyalty points, tiers         | ON      |
| `enable_packages`            | Time bundles, day passes, night passes, monthly passes | ON      |
| `enable_pos`                 | Food and drink ordering                                | ON      |
| `enable_inventory`           | Stock tracking for POS items                           | OFF     |
| `enable_reservations`        | Advance seat reservations                              | ON      |
| `enable_vouchers`            | Prepaid voucher code generation and redemption         | OFF     |
| `enable_tournaments`         | Tournament and event mode                              | OFF     |
| `enable_expense_tracking`    | Expense log and P&L estimate                           | OFF     |
| `enable_health_monitoring`   | PC hardware metrics from agent                         | ON      |
| `require_member_for_session` | Require member login before unlocking a seat           | OFF     |

Disabling a feature SHALL gracefully degrade: related menu items are hidden, related API endpoints return a 503 with a clear message, and existing data is preserved.

---

## 7. Data Requirements

### 7.1 Core Entities

| Entity        | Key Attributes                                                                                                                      |
| ------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| Seat          | ID, name, zone, MAC address, status, current session ID                                                                             |
| Session       | ID, seat ID, member ID (nullable), start time, end time, rate locked, package used, promotion applied, status                       |
| Invoice       | ID, session ID, time charge (paise), package credit used (paise), discount amount (paise), POS items, total (paise), payment method |
| Member        | ID, name, phone, wallet balance (paise), loyalty points, tier, join date                                                            |
| Package       | ID, type, total minutes, remaining minutes, member ID, expiry date                                                                  |
| Promotion     | ID, name, type, value, schedule (days/hours), active flag                                                                           |
| Voucher       | ID, code, value (paise or minutes), status, expiry date, redeemed by, redeemed at                                                   |
| POSItem       | ID, name, price (paise), category, stock level (nullable)                                                                           |
| Staff         | ID (e.g., "S001"), name, role (Admin/Cashier), PIN hash (Argon2id), token_version (integer, default 0)                              |
| Shift         | ID, staff ID, open time, close time, float amount, counted amount                                                                   |
| AuditLog      | ID, timestamp, staff ID, action, entity type, entity ID, detail                                                                     |
| Expense       | ID, date, category, amount (paise), note                                                                                            |
| Event         | ID, name, game, date, entry fee, prize pool, bracket type, status                                                                   |
| LicenseStatus | ID (singleton), cafe_name, hardware_id, license_type, issue_date, trial_expires_at, last_verified_at (read-only cache)              |

### 7.2 Billing Precision

All monetary amounts SHALL be stored and processed as integers representing paise (1 rupee = 100 paise). Conversion to rupees for display SHALL occur only at the API response or UI rendering layer.

### 7.3 Retention

- Session and billing records SHALL be retained indefinitely
- Audit log records SHALL be retained indefinitely and SHALL NOT be deletable through the application
- Nightly backups SHALL be retained for a configurable number of days (default: 30)

---

## 8. External Interface Requirements

### 8.1 User Interfaces

- **Staff Dashboard:** Browser-based React application served by the FastAPI backend. Accessible from any machine on the LAN.
- **Launcher GUI:** Tkinter desktop application on the server PC. Displays server status and logs (cross‑platform).
- **Client Agent UI:** Electron application running on each client PC — full‑screen kiosk overlay, splash screen, countdown timer, remote command overlays (cross‑platform).
- **Owner Mobile View:** The React dashboard, accessed via mobile browser on the cafe WiFi. Responsive layout optimised for phone screen sizes.

### 8.2 Hardware Interfaces

- **Thermal Printer:** ESC/POS compatible, interfaced via `python-escpos` over USB or network
- **Smart Plugs:** Tuya-compatible plugs for PS5/Xbox, controlled locally via TinyTuya (no cloud after initial pairing)
- **Client PCs:** Wake-on-LAN via UDP magic packet broadcast on the local subnet
- **Network:** All client machines on wired ethernet (recommended). Server on wired ethernet. Owner mobile view on WiFi.

### 8.3 Software Interfaces

- **TinyTuya:** Local LAN communication with Tuya smart plugs. Credentials (device_id, local_key, ip_address, protocol_version) stored in Settings.
- **`python-escpos`:** Library for thermal printer communication.
- **`systeminformation` (Node.js):** Used by the Electron agent to collect CPU, RAM, temperature, and disk metrics (cross‑platform).
- **`better-sqlite3` (Node.js):** Used by the agent for local session persistence.
- **Alembic:** Handles all database schema migrations. Must be run before server startup.
- **APScheduler (`AsyncIOScheduler`):** Used for scheduled tasks (nightly backup) integrated with FastAPI's event loop.

### 8.4 Communication Interfaces

- **REST API:** FastAPI JSON API for all CRUD operations. Auto-documented at `/docs`.
- **WebSocket:** Persistent connections for real-time seat status, health metrics, remote commands, and announcements. Reconnects automatically with exponential backoff and jitter.

---

## 9. Build Phases

### Phase 1 — Core

**Scope:** Offline license activation (Hardware ID generation with no admin privileges, Ed25519 signature verification) · Launcher with setup wizard · FastAPI project structure with `lifespan` context manager · Alembic migrations · MAC address registration · Wake-on-LAN boot routine · Session start/stop/pause/resume API · React seat grid dashboard · Electron client agent (Windows first) with hardened kiosk overlay and local SQLite persistence skeleton · WebSocket real-time updates · Health check endpoint · Async SQLAlchemy setup with `aiosqlite` and WAL pragmas

**Exit Criteria:** A machine without a valid license is blocked at the Activation screen and cannot reach the setup wizard. Once a valid `license.key` matching the machine's Hardware ID is supplied, setup proceeds. Staff can start a session on a seat, see it update live on the dashboard, and end the session. The client PC shows the kiosk overlay when no session is active (`SHOW_OVERLAY`) and hides it during a session (`HIDE_OVERLAY`) (Windows initially). Kiosk hardening (FR-AGENT-002a, FR-AGENT-002b) is verified.

### Phase 2 — Billing, POS and Printing

**Scope:** Time-based billing across all pricing models · Food and drink POS · Inventory tracking with low-stock alerts · Invoice generation · Thermal printer integration · PDF fallback · Audit log · Billing in paise (integer precision)

**Exit Criteria:** A complete checkout — time charge, food items, printed receipt — works end-to-end. Billing is accurate across per-minute, flat-hourly, and time-block models.

### Phase 3 — Members, Packages and Promotions

**Scope:** Member profiles and prepaid wallet · Loyalty tiers and discounts · Time packages and day passes · Prepaid voucher code generation and redemption · Promotions engine (happy hour, group discount, birthday bonus) · Per-zone pricing · Staff roles and Staff ID+PIN auth (Argon2id) · Peak/off-peak scheduling · JWT with `token_version` revocation

**Exit Criteria:** A member with an active package checks out correctly — package time is drawn first, per-minute billing kicks in on overflow, loyalty discount is applied, and the invoice is correct. PIN change invalidates existing tokens.

### Phase 4 — Operations and Experience

**Scope:** Remote PC commands (restart, shutdown, message, screenshot best‑effort with JPEG compression and scaling) · PC health monitoring (CPU, RAM, temp, disk) · Shift management with cash reconciliation · Expense tracking · Seat reservations · Kiosk overlay improvements · Announcements broadcast · Nightly SQLite backup (30‑day retention) via APScheduler · Graceful shutdown via `lifespan` · Log rotation · Agent persistent session storage (SQLite) and sync · Agent secret authentication

**Exit Criteria:** Staff can restart a frozen PC from the dashboard. Shift opens and closes with a correct cash reconciliation report. Nightly backup runs automatically via APScheduler. Agent survives a crash and restores session state. Agent authentication prevents impersonation.

### Phase 5 — Events and Analytics

**Scope:** Tournament/event mode with bracket management · Owner analytics dashboard (Recharts) · Maintenance mode per seat with downtime tracking · Configurable feature flags · Mobile-responsive dashboard · WoL success tracking and UNREACHABLE state · Screenshot request rate-limiting

**Exit Criteria:** An event is created, participants registered, bracket completed, and entry fees recorded. The analytics dashboard shows accurate revenue, utilisation, and health data from the local database. All feature flags toggle correctly.

### Phase 6 — Cross‑Platform Polish

**Scope:** Complete the agent's platform abstraction layer for macOS and Linux · Packaging for all three OSes (`.exe`, `.dmg`, `.deb`/AppImage) · Auto‑start scripts for each OS · Comprehensive testing on each platform · Update documentation and installation guides · Address OS‑specific permission requirements (macOS Screen Recording, Linux Wayland) · Verify kiosk hardening on all platforms

**Exit Criteria:** The agent runs and controls the kiosk overlay correctly on all three OSes. Remote restart/shutdown works on all platforms. Installation and auto‑start are documented and tested. The server Launcher works on all OSes. Kiosk bypass attempts (Alt+F4, Cmd+Q, F12, Ctrl+P) are blocked on all platforms (with known Ctrl+Alt+Del limitation documented).

### Phase 7 — Growth (V2, Future)

**Scope:** Online public booking portal · WhatsApp/SMS notifications via Sparrow SMS or WhatsApp Business API · Optional WAN remote access (read-only stats endpoint, phone-home pattern) · Multi-location support · PostgreSQL migration path

**Status:** Out of scope for V1. Architecturally planned.

---

## 10. Constraints and Assumptions

### 10.1 Constraints

- The system MUST NOT require an active internet connection for any core operational feature (exception: initial Tuya device pairing, which is a one‑time setup step)
- No user data, billing data, or operational data SHALL be transmitted to any external server
- The billing engine MUST use integer arithmetic throughout to prevent rounding errors
- Database schema changes MUST be performed exclusively via Alembic migrations
- The system is scoped for single-location deployment in V1; multi-location is a V2 concern
- License verification MUST function entirely offline once a `license.key` has been issued; the private signing key MUST never ship inside the distributed application or its repository
- The client agent SHALL use a kiosk overlay for access control, not OS lock/unlock, to ensure cross‑platform consistency
- Agent session persistence MUST use a local SQLite database to survive crashes and reboots
- All backend database operations SHALL use async SQLAlchemy (`AsyncSession` with `aiosqlite`) to prevent blocking the FastAPI event loop
- The `lifespan` context manager SHALL be used for startup and shutdown logic; `@app.on_event` SHALL NOT be used

### 10.2 Assumptions

- Server machine runs one of the supported OSes (Windows, macOS, Linux) with Python 3.11+ and Node.js 20+ (unless packaged)
- Client machines run one of the supported OSes and support Electron
- Client machines support Wake-on-LAN and it is enabled (if using wired Ethernet)
- Client machines are connected to the network via wired ethernet for reliability; WiFi is optional but not recommended
- Consoles have "boot on power restore" enabled in their system settings
- The cafe has a reliable local area network
- The cafe owner accepts responsibility for configuring Tuya smart plugs correctly and performing one‑time pairing via the Tuya app (internet required only then)
- A single counter PC serves as the server throughout operation hours
- For macOS and Linux, the owner will grant the necessary permissions (Screen Recording, etc.) when prompted by the agent, but the system will degrade gracefully if not granted

---

## 11. Acceptance Criteria

The system SHALL be considered ready for production deployment when all of the following criteria are met:

| #     | Criterion                                                                                                                                                                                                                  |
| ----- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| AC-01 | Staff can open the dashboard and see all seat statuses in real time without refreshing the page                                                                                                                            |
| AC-02 | A session can be started and ended in under 10 seconds of total staff interaction                                                                                                                                          |
| AC-03 | Checkout correctly calculates time cost, package usage, applied discounts, and POS items — and produces a printed or PDF receipt with all required fields                                                                  |
| AC-04 | All client PCs boot automatically when the server starts, without staff touching individual machines (WoL success rate is tracked)                                                                                         |
| AC-05 | The owner can view today's revenue summary from their phone while on the cafe WiFi                                                                                                                                         |
| AC-06 | A frozen or unresponsive PC can be restarted from the dashboard without physically walking to the machine                                                                                                                  |
| AC-07 | No billing or session data is lost when the LAN connection between the server and a client agent drops and recovers, even if the agent crashes and restarts                                                                |
| AC-08 | All feature flags toggle their respective UI elements and backend endpoints correctly                                                                                                                                      |
| AC-09 | The audit log records all sensitive operations with correct timestamps, staff identity, and detail fields                                                                                                                  |
| AC-10 | A shift opens and closes with correct revenue, session count, and cash reconciliation figures                                                                                                                              |
| AC-11 | A member with an active package checks out with correct package drawdown and per-minute overflow billing                                                                                                                   |
| AC-12 | The setup wizard cannot be started without a `license.key` that passes signature verification and matches the current machine's Hardware ID; an invalid or mismatched license is clearly rejected without crashing the app |
| AC-13 | The Electron agent shows the kiosk overlay when no session is active and hides it during a session, correctly blocking desktop access on Windows, macOS, and Linux                                                         |
| AC-14 | Remote restart and shutdown commands work on Windows, macOS, and Linux                                                                                                                                                     |
| AC-15 | The server Launcher runs without errors on Windows, macOS, and Linux; the setup wizard and activation flow work identically across OSes                                                                                    |
| AC-16 | Console power is controlled via local TinyTuya without any internet dependency during normal operation                                                                                                                     |
| AC-17 | Kiosk bypass methods (Alt+F4, Cmd+Q, F12 DevTools, Ctrl+P) are blocked on all platforms                                                                                                                                    |
| AC-18 | Screenshots are delivered as JPEG at 80% quality, scaled to 1280×720 max, and rate-limited to one in-flight request per seat                                                                                               |
| AC-19 | The server starts and shuts down cleanly using the `lifespan` context manager; no deprecation warnings for `@app.on_event` appear in logs                                                                                  |
| AC-20 | Nightly backups run via APScheduler and are retained for 30 days with automatic cleanup                                                                                                                                    |
| AC-21 | Agent WebSocket authentication rejects connections with invalid or missing `agent_secret` tokens                                                                                                                           |
| AC-22 | Active sessions are preserved and reconciled when the server restarts                                                                                                                                                      |
| AC-23 | The Launcher prompts for confirmation when closed while the server is running                                                                                                                                              |

---

## 12. Glossary

| Term                 | Definition                                                                                                                                                                                  |
| -------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Agent                | The Electron application installed on each client PC. Handles kiosk overlay, health metrics, remote commands, and local session persistence.                                                |
| Audit Log            | Write-only record of all sensitive system operations for accountability and dispute resolution.                                                                                             |
| Cashier              | Staff role with access to billing, POS, and checkout only.                                                                                                                                  |
| Dashboard            | The React web application used by staff at the counter.                                                                                                                                     |
| Day Pass             | A package type granting unlimited play on a single calendar day for a fixed fee.                                                                                                            |
| Ed25519              | An elliptic-curve digital signature algorithm used to sign and verify license files without requiring network access.                                                                       |
| ESC/POS              | Command language used to communicate with thermal printers.                                                                                                                                 |
| Feature Flag         | A toggleable setting that enables or disables an optional system feature.                                                                                                                   |
| Hardware ID          | A fingerprint derived from `py-machineid` (primary) plus MAC address and available OS identifiers (fallback), hashed with SHA256. Generated without admin privileges on all supported OSes. |
| Keygen Tool          | An internal, non-distributed tool used by Neurotech Biratnagar to generate signed `license.key` files for customers.                                                                        |
| Kiosk Overlay        | Full‑screen, always‑on‑top window that blocks desktop access; used instead of OS lock/unlock for cross‑platform consistency.                                                                |
| Launcher             | The Tkinter GUI that starts and stops the Arcade server and runs the setup wizard on first use.                                                                                             |
| LAN                  | Local Area Network — the internal network of the gaming cafe.                                                                                                                               |
| License Key          | A signed file (`license.key`) issued per customer, containing cafe name, Hardware ID, license type, and a verifiable signature.                                                             |
| Lifespan             | FastAPI context manager pattern for startup and shutdown logic, replacing the deprecated `@app.on_event` decorator.                                                                         |
| Paise                | The smallest monetary unit (1/100th of a Rupee). All amounts are stored in paise for integer precision.                                                                                     |
| Package              | A prepaid bundle of time (hours, day pass, night pass, or monthly pass) associated with a member account.                                                                                   |
| Platform Abstraction | A design pattern that isolates OS‑specific code behind a common interface, allowing the same application to run on Windows, macOS, Linux.                                                   |
| POS                  | Point of Sale — the food and drink ordering component of the system.                                                                                                                        |
| Promotion            | A time-limited discount or offer applied automatically at session start.                                                                                                                    |
| Session              | A single continuous use period of a seat, from start to checkout.                                                                                                                           |
| Smart Plug           | A Tuya-compatible Wi-Fi power outlet used to control console power state; controlled locally via TinyTuya.                                                                                  |
| TinyTuya             | A Python library for local LAN communication with Tuya devices, eliminating cloud dependency.                                                                                               |
| Voucher              | A prepaid code redeemable for session time or wallet credit. Single-use, with optional expiry.                                                                                              |
| WAL Mode             | SQLite Write-Ahead Logging mode — allows concurrent reads during writes, improving performance under load.                                                                                  |
| Walk-in              | A customer without a member account. Supported natively; billed at standard rate with no loyalty features.                                                                                  |
| Wake-on-LAN          | A network standard that allows a PC to be powered on remotely by sending a "magic packet" to its MAC address.                                                                               |
| Zone                 | A named grouping of seats with a shared pricing rate (e.g., Standard PC, VIP PC, Console Corner).                                                                                           |

---

_This document is the authoritative requirements specification for Arcade v2.0._

# Software Requirements Specification

## Arcade — Gaming Cafe Management System

**Document Version:** 1.1  
**Project Version:** 2.0  
**Date:** June 2026  
**Prepared by:** Ashmin Dhungana  
**Status:** Pre‑Development · Planning Complete  
**Classification:** Internal / Private

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [Overall Description](#2-overall-description)
3. [System Architecture](#3-system-architecture)
4. [Functional Requirements](#4-functional-requirements)
   - 4.1 [System Initialisation](#41-system-initialisation)
   - 4.1a [Licensing and Activation](#41a-licensing-and-activation)
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
- PC and console remote control
- Staff shift management and audit logging
- Owner-facing analytics and mobile access
- Tournament and event management

The system runs entirely on the cafe's local network. No internet connection is required during daily operation. No cloud infrastructure, subscription fees, or per-seat licensing applies.

**Cross‑platform:** The server (FastAPI + Launcher) runs on Windows, macOS, and Linux. The client agent (Electron) runs on all three operating systems, with a platform abstraction layer that handles OS‑specific screen locking, remote commands, and auto‑start. This gives cafe owners the freedom to choose their hardware without being locked into a single OS.

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
- Alembic documentation — database migration reference
- Tuya API documentation — smart plug integration reference
- RFC 8032 (Ed25519) — digital signature scheme used for offline license verification

---

## 2. Overall Description

### 2.1 Product Perspective

Arcade is a greenfield self-hosted application. It does not integrate with or depend on any cloud service during operation. The system is designed as a replacement for manual cafe operations and is positioned against cloud-based competitors (SENET, iCafeCloud) that charge recurring per-seat fees and require internet connectivity.

### 2.2 Product Functions (Summary)

- Live seat grid with real-time status updates
- Timed session lifecycle management (start, stop, pause, resume)
- Multi-model billing engine with integer-precision arithmetic
- Food and drink POS with optional inventory tracking
- Member account management with wallet, loyalty, and packages
- Remote PC lock/unlock and command dispatch via Electron agent (cross‑platform)
- Console power control via Tuya smart plug API
- Staff role management with PIN authentication and shift tracking
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
- **Internet:** Not required during operation; required (or a manual offline path available) only for initial license activation, the setup wizard, and Tuya API calls for console control
- **Hardware:** Counter PC (server), individual gaming PCs or Macs (clients), PS5/Xbox via Tuya smart plugs
- **Printing:** ESC/POS thermal printer or any regular printer (PDF fallback)

### 2.5 Design Constraints

- All inter-component communication MUST occur exclusively on the local network
- No user or session data shall be transmitted to external servers
- The billing engine MUST store all monetary values as integers in the lowest denomination (paise) to prevent floating-point rounding errors
- The system MUST remain operable if the LAN connection between server and one or more client agents is temporarily interrupted
- The server MUST be the single source of truth for all session timers
- The license verification mechanism MUST NOT require an active internet connection or any phone-home call during normal day-to-day operation, once activated, consistent with the product's zero-cloud-dependency design
- The client agent MUST abstract all OS‑specific operations (screen locking, shutdown, restart, auto‑start) behind a platform service interface to support Windows, macOS, and Linux without duplicating UI code

### 2.6 Assumptions and Dependencies

- Client machines run one of the supported OSes (Windows, macOS, Linux) and are capable of running Electron
- Client machines support Wake-on-LAN (if using wired Ethernet) – for macOS/Linux, WoL is also supported
- Client machines are connected via wired ethernet for reliable WoL and low‑latency communication; WiFi is supported but not recommended for production
- Consoles (PS5, Xbox) have "boot on power restore" enabled in their system settings
- Tuya-compatible smart plugs are used for all consoles
- Python 3.11+ and Node.js 20+ are available on the server PC (or the packaged build includes them)
- A thermal printer compatible with `python-escpos` is available (or PDF fallback is acceptable)
- For screen locking on macOS, the system must allow the agent to control the screen saver/lock (Accessibility permissions may be required); on Linux, the agent will attempt to use `xdg-screensaver` or DE‑specific tools

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
       │                                           ├── Platform abstraction layer
       │                                           │   ├── Windows: user32, shutdown
       │                                           │   ├── macOS: AppleScript, pmset
       │                                           │   └── Linux: xdg-screensaver, systemctl
       │                                           ├── Screen lock / unlock (OS‑specific)
       │                                           ├── Countdown + low-time warning
       │                                           ├── Branded splash screen
       │                                           ├── Health metrics (CPU, RAM, temp)
       │                                           └── Remote commands (restart, message)
       │
       └── Tuya API ───────────────────────► Smart Plugs
                                              └── PS5 / Xbox
```

### 3.2 Component Descriptions

| Component            | Technology                                                       | Responsibility                                                                                       |
| -------------------- | ---------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| **Arcade Server**    | Python · FastAPI · Uvicorn · SQLite                              | Authoritative business logic, session timing, database, REST API, WebSocket hub (cross‑platform)     |
| **Arcade Dashboard** | React · Vite · TypeScript · TailwindCSS · React Query · Recharts | Staff UI, seat grid, billing, POS, analytics, settings (browser‑based, OS‑agnostic)                  |
| **Arcade Launcher**  | Python · Tkinter                                                 | GUI wrapper to start/stop the server; setup wizard on first run; displays live logs (cross‑platform) |
| **Arcade Agent**     | Electron · React · `systeminformation`                           | Per‑client process; lock/unlock desktop; health metrics; remote command execution (cross‑platform)   |

The **agent** uses a platform abstraction layer inside Electron: the same UI code runs on all OSes, while OS‑specific modules handle screen locking (via `rundll32` on Windows, AppleScript on macOS, `xdg‑screensaver` on Linux), shutdown/restart commands (using appropriate system utilities), and auto‑start registration (registry on Windows, LaunchAgent on macOS, autostart `.desktop` on Linux). This keeps the codebase clean and maintainable.

### 3.3 Tech Stack

| Layer           | Technology                                                | Cross‑Platform                |
| --------------- | --------------------------------------------------------- | ----------------------------- |
| Backend API     | Python · FastAPI · Uvicorn                                | ✅                            |
| Database        | SQLite (WAL mode) · SQLAlchemy · Alembic                  | ✅                            |
| Frontend        | React · Vite · TypeScript · TailwindCSS · React Query     | ✅                            |
| Server Launcher | Python · Tkinter                                          | ✅                            |
| Client Agent    | Electron · React · `systeminformation`                    | ✅                            |
| Console Control | Tuya Smart Plug API                                       | ✅                            |
| Printing        | `python-escpos` · Browser PDF fallback                    | ✅ (printer driver dependent) |
| Real‑time Comms | WebSockets (exponential backoff reconnection + heartbeat) | ✅                            |
| Charts          | Recharts                                                  | ✅                            |
| Task Queue      | Python `schedule` (nightly backup)                        | ✅                            |

### 3.4 Project Structure

```
arcade-cafe/
├── backend/
│   ├── api/
│   │   └── routers/          # FastAPI route handlers
│   ├── services/             # Business logic (billing, sessions, members, packages)
│   ├── repositories/         # All database queries
│   ├── models/               # SQLAlchemy ORM models
│   ├── schemas/              # Pydantic request/response schemas
│   ├── licensing/            # License file parsing + Ed25519 signature verification, hardware fingerprinting
│   └── core/
│       ├── config.py         # Settings loader
│       └── database.py       # Engine, WAL pragmas, session factory
├── frontend/                 # React dashboard (Vite + TailwindCSS)
├── agent/
│   ├── src/
│   │   ├── main/             # Electron main process
│   │   │   ├── index.ts      # entry point
│   │   │   ├── platform/     # OS‑specific modules
│   │   │   │   ├── index.ts  # unified PlatformService interface
│   │   │   │   ├── windows.ts
│   │   │   │   ├── macos.ts
│   │   │   │   └── linux.ts
│   │   │   └── ipc-handlers.ts
│   │   └── renderer/         # React UI (common across OSes)
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
- The server SHALL emit heartbeat pings to detect dead connections
- The agent SHALL cache the session start time locally to ensure billing survives a LAN interruption

---

## 4. Functional Requirements

### 4.1 System Initialisation

**FR-SYS-001:** On first launch, the Launcher SHALL check for a valid, activated license before the setup wizard is permitted to run. If no valid license is present, the Launcher SHALL present the License Activation screen (see §4.1a) instead of the setup wizard, and the setup wizard SHALL NOT be reachable until activation succeeds.

**FR-SYS-002:** Once a valid license is confirmed, the Launcher SHALL run a setup wizard prompting for: cafe name, server host (IP), server port, admin PIN, and cashier PIN.

**FR-SYS-003:** The setup wizard output SHALL be saved to `arcade.config.json`. Subsequent launches SHALL skip both license activation (if already valid) and the wizard, and start the server directly.

**FR-SYS-004:** On server startup, Alembic migrations SHALL be applied automatically (`alembic upgrade head`).

**FR-SYS-005:** On server startup, the system SHALL send Wake-on-LAN magic packets to all registered client PC MAC addresses to boot them.

**FR-SYS-006:** The Launcher SHALL display live server logs and a health indicator in its GUI.

**FR-SYS-007:** The system SHALL expose a health check endpoint at `/health` returning server status, uptime, database connectivity, and license status.

**FR-SYS-008:** On every Launcher start (not just first run), the Launcher SHALL re-verify the locally stored license file's signature and hardware-fingerprint match before starting the server. If verification fails, the server SHALL NOT start and the License Activation screen SHALL be shown instead.

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

**FR-LIC-002:** On first launch with no `license.key` present, the Launcher SHALL compute a Hardware ID by hashing a combination of stable, machine-specific identifiers (e.g. motherboard serial number, primary disk volume serial, Windows machine GUID; on macOS use `system_profiler`; on Linux use `dmidecode`). The Hardware ID SHALL be deterministic across reboots on the same machine and platform‑agnostic.

**FR-LIC-003:** The Launcher SHALL display the computed Hardware ID in the License Activation screen in a clearly copyable format, along with instructions for the cafe owner to send it to Neurotech Biratnagar to receive their `license.key`.

**FR-LIC-004:** A license SHALL be generated using an internal, offline keygen tool (distributed separately from the product, never shipped to customers) that accepts: the customer's Hardware ID, cafe name, license type, and issue date, and produces a `license.key` file signed with the private key.

**FR-LIC-005:** The `license.key` file SHALL be a structured payload (e.g. JSON) containing: cafe name, Hardware ID, license type, issue date, and an Ed25519 signature over the payload. The file MAY be base64-encoded for ease of transport but SHALL NOT be encrypted (signature, not secrecy, is the integrity mechanism).

**FR-LIC-006:** On activation, the cafe owner SHALL place the received `license.key` file in the application's configuration directory (or import it via a file picker in the Activation screen).

**FR-LIC-007:** The Launcher SHALL verify a presented `license.key` by: (a) verifying the Ed25519 signature against the embedded public key, and (b) confirming the Hardware ID inside the license payload matches the Hardware ID computed for the current machine. Both checks SHALL pass for activation to succeed.

**FR-LIC-008:** If signature verification fails, or the Hardware ID does not match, the Launcher SHALL reject the license, SHALL NOT proceed to setup or server start, and SHALL display a clear error distinguishing "invalid license file" from "license does not match this machine."

**FR-LIC-009:** Once activated, license verification SHALL be performed locally on every Launcher start (FR-SYS-008). No network call SHALL be required for this check.

**FR-LIC-010:** If the cafe's counter PC hardware changes (e.g. motherboard replacement) such that the Hardware ID no longer matches, the system SHALL support re-activation by the owner contacting Neurotech Biratnagar with the new Hardware ID to receive a reissued `license.key`. This is a manual, support-driven process in V1; no self-service transfer flow is in scope.

**FR-LIC-011:** The system MAY support a time-limited evaluation/demo mode (e.g. a license payload field marking it as a trial with an expiry date) for prospective customers, gated by the same signature mechanism, without requiring a separate code path.

**FR-LIC-012:** License status (cafe name, activation date, license type, hardware-match status) SHALL be viewable by Admin users from within Settings once the system is running.

**FR-LIC-013:** Tampering with or deleting `license.key` after activation SHALL cause the next Launcher start to fall back to the License Activation screen (per FR-SYS-008); it SHALL NOT crash the application or corrupt existing session/billing data.

---

### 4.2 Seat Management

**FR-SEAT-001:** The dashboard SHALL display all seats in a colour-coded grid reflecting real-time status.

**FR-SEAT-002:** Seat statuses SHALL include at minimum: Available, In Use, Reserved, Paused, Maintenance, Offline.

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

**FR-SES-004:** The agent SHALL cache the session start time locally. If the LAN connection drops, the agent SHALL continue tracking elapsed time locally. On reconnection, the server SHALL reconcile with the agent-reported data.

**FR-SES-005:** No billing data SHALL be lost due to a temporary LAN interruption between the server and an agent.

**FR-SES-006:** When a session is started, the system SHALL check and lock in: the applicable pricing rate, any active package entitlement, and any active promotion. These SHALL NOT change mid-session.

**FR-SES-007:** At 5 minutes remaining in a timed package, the agent SHALL display a low-time warning popup on the client screen.

**FR-SES-008:** When a session ends, the server SHALL trigger the agent to lock the client PC and SHALL generate an invoice.

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

#### 4.12.1 Client Agent (Cross‑Platform)

**FR-AGENT-001:** The Electron agent SHALL automatically connect to the server on boot, register its hardware info (MAC address, hostname, OS version, hardware specs), and begin sending health metrics.

**FR-AGENT-002:** On session start, the agent SHALL unlock the desktop (using OS‑specific methods) and display a branded splash screen for 5 seconds showing: cafe logo, session duration, food menu, and a "Call Staff" button.

**FR-AGENT-003:** After the splash screen, the agent SHALL minimise to a system tray icon showing remaining session time.

**FR-AGENT-004:** On session end, the agent SHALL lock the desktop (using OS‑specific methods).

**FR-AGENT-005:** The agent SHALL send health metrics to the server every 60 seconds including: CPU usage (%), RAM usage (%), CPU temperature, and disk space.

**FR-AGENT-006:** The agent SHALL receive and execute remote commands from the server as specified in FR-CMD-001 through FR-CMD-004.

**FR-AGENT-007:** The agent SHALL implement a platform abstraction layer that exposes a unified interface for screen locking, unlocking, restart, shutdown, and auto‑start. OS‑specific implementations SHALL be selected at runtime based on `process.platform`:

- **Windows:** `user32.dll` for lock, `shutdown` for restart/shutdown, registry for auto‑start
- **macOS:** AppleScript (`osascript`) for lock, `sudo shutdown` for restart/shutdown, LaunchAgent plist for auto‑start
- **Linux:** `xdg-screensaver` or DE‑specific commands for lock, `systemctl`/`shutdown` for restart/shutdown, autostart `.desktop` file for auto‑start

**FR-AGENT-008:** The agent SHALL handle permission prompts gracefully (e.g., Accessibility on macOS, sudoers configuration on Linux) and display clear instructions to the cafe owner for granting necessary permissions.

#### 4.12.2 Remote Commands

**FR-CMD-001:** Staff SHALL be able to trigger a remote restart of any client PC from the dashboard.

**FR-CMD-002:** Staff SHALL be able to trigger a remote shutdown of any or all client PCs from the dashboard.

**FR-CMD-003:** Staff SHALL be able to send an announcement message that displays as an overlay on one or all client screens.

**FR-CMD-004:** Admin users SHALL be able to capture a screenshot of any client PC screen from the dashboard.

#### 4.12.3 Console Control

**FR-CON-001:** The system SHALL control console power state (on/off) via the Tuya smart plug API.

**FR-CON-002:** When a console session starts, the system SHALL call the Tuya API to power on the corresponding smart plug.

**FR-CON-003:** When a console session ends, the system SHALL call the Tuya API to power off the corresponding smart plug.

**FR-CON-004:** Console smart plugs SHALL be configurable and paired via the Settings screen.

---

### 4.13 Staff Roles and Authentication

**FR-AUTH-001:** The system SHALL support two staff roles: Admin and Cashier.

**FR-AUTH-002:** Admin users SHALL have full access to all features including settings, reports, expense tracking, and screenshot commands.

**FR-AUTH-003:** Cashier users SHALL have access to billing, POS, session management, and checkout only. They SHALL NOT access settings, reports, or admin commands.

**FR-AUTH-004:** Authentication SHALL be PIN-based. PINs SHALL be stored hashed.

**FR-AUTH-005:** After 5 consecutive failed PIN attempts, the system SHALL enforce a 60-second lockout before allowing further attempts.

**FR-AUTH-006:** All sensitive operations SHALL be tagged with the authenticated staff member's identity in the audit log.

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

**FR-AUDIT-003:** Audit log entries SHALL NOT be editable or deletable by any user role.

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

---

### 4.22 Nightly Backup

**FR-BACKUP-001:** The system SHALL automatically create a backup of the SQLite database each night at a configurable time (default: 3:00 AM).

**FR-BACKUP-002:** Backups SHALL be stored in a configurable local directory.

**FR-BACKUP-003:** The system SHALL retain a configurable number of recent backups (default: 7) and delete older ones automatically.

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

**NFR-REL-002:** No billing or session data SHALL be lost due to a LAN interruption between the server and any agent.

**NFR-REL-003:** WebSocket connections SHALL reconnect automatically using exponential backoff with jitter after any disconnection.

**NFR-REL-004:** The server SHALL detect dead WebSocket connections via heartbeat pings and mark the affected seat as "Offline" on the dashboard.

**NFR-REL-005:** The system SHALL recover from a server restart without losing any committed session or billing data.

### 5.3 Security

**NFR-SEC-001:** All staff PINs SHALL be stored hashed using a secure one-way algorithm. PINs SHALL NOT be stored in plaintext.

**NFR-SEC-002:** Staff sessions SHALL be authenticated via tokens issued at PIN entry.

**NFR-SEC-003:** The screenshot command SHALL be restricted to Admin role only.

**NFR-SEC-004:** The audit log SHALL be append-only. No user role SHALL be able to modify or delete audit log entries.

**NFR-SEC-005:** The system SHALL NOT transmit any customer or billing data to external servers.

**NFR-SEC-006:** All network communication SHALL remain confined to the local network during normal operation.

### 5.4 Usability

**NFR-USE-001:** The counter dashboard SHALL be operable by a staff member with no technical background after a brief orientation.

**NFR-USE-002:** A session start-to-checkout workflow SHALL require no more than 5 mouse clicks under normal conditions.

**NFR-USE-003:** The Launcher SHALL require only a double-click to start the server. No command line interaction SHALL be required for daily operation.

**NFR-USE-004:** The setup wizard SHALL complete in under 5 minutes for a first-time installation.

**NFR-USE-005:** The dashboard SHALL display only UI elements for features that are currently enabled via feature flags.

### 5.5 Maintainability

**NFR-MAINT-001:** All database schema changes SHALL be managed exclusively through Alembic migration scripts. Direct schema edits SHALL NOT be performed.

**NFR-MAINT-002:** The backend SHALL follow a layered architecture: routers (HTTP), services (business logic), repositories (data access), and models (ORM).

**NFR-MAINT-003:** Feature flags SHALL be toggleable from the Settings UI without requiring code changes or server restarts.

**NFR-MAINT-004:** The server SHALL support graceful shutdown: completing in-progress requests and flushing any pending state before exit.

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

| Entity    | Key Attributes                                                                                                                      |
| --------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| Seat      | ID, name, zone, MAC address, status, current session ID                                                                             |
| Session   | ID, seat ID, member ID (nullable), start time, end time, rate locked, package used, promotion applied, status                       |
| Invoice   | ID, session ID, time charge (paise), package credit used (paise), discount amount (paise), POS items, total (paise), payment method |
| Member    | ID, name, phone, wallet balance (paise), loyalty points, tier, join date                                                            |
| Package   | ID, type, total minutes, remaining minutes, member ID, expiry date                                                                  |
| Promotion | ID, name, type, value, schedule (days/hours), active flag                                                                           |
| Voucher   | ID, code, value (paise or minutes), status, expiry date, redeemed by, redeemed at                                                   |
| POSItem   | ID, name, price (paise), category, stock level (nullable)                                                                           |
| Staff     | ID, name, role (Admin/Cashier), PIN hash                                                                                            |
| Shift     | ID, staff ID, open time, close time, float amount, counted amount                                                                   |
| AuditLog  | ID, timestamp, staff ID, action, entity type, entity ID, detail                                                                     |
| Expense   | ID, date, category, amount (paise), note                                                                                            |
| Event     | ID, name, game, date, entry fee, prize pool, bracket type, status                                                                   |

### 7.2 Billing Precision

All monetary amounts SHALL be stored and processed as integers representing paise (1 rupee = 100 paise). Conversion to rupees for display SHALL occur only at the API response or UI rendering layer.

### 7.3 Retention

- Session and billing records SHALL be retained indefinitely
- Audit log records SHALL be retained indefinitely and SHALL NOT be deletable
- Nightly backups SHALL be retained for a configurable number of days (default: 7)

---

## 8. External Interface Requirements

### 8.1 User Interfaces

- **Staff Dashboard:** Browser-based React application served by the FastAPI backend. Accessible from any machine on the LAN.
- **Launcher GUI:** Tkinter desktop application on the server PC. Displays server status and logs (cross‑platform).
- **Client Agent UI:** Electron application running on each client PC — branded splash screen, system tray icon, countdown timer, remote command overlays (cross‑platform).
- **Owner Mobile View:** The React dashboard, accessed via mobile browser on the cafe WiFi. Responsive layout optimised for phone screen sizes.

### 8.2 Hardware Interfaces

- **Thermal Printer:** ESC/POS compatible, interfaced via `python-escpos` over USB or network
- **Smart Plugs:** Tuya-compatible plugs for PS5/Xbox, interfaced via the Tuya Cloud API (requires internet access for control calls)
- **Client PCs:** Wake-on-LAN via UDP magic packet broadcast on the local subnet
- **Network:** All client machines on wired ethernet (recommended). Server on wired ethernet. Owner mobile view on WiFi.

### 8.3 Software Interfaces

- **Tuya API:** Used for smart plug power control. API credentials configured in Settings. Requires internet access.
- **`python-escpos`:** Library for thermal printer communication.
- **`systeminformation` (Node.js):** Used by the Electron agent to collect CPU, RAM, temperature, and disk metrics (cross‑platform).
- **Alembic:** Handles all database schema migrations. Must be run before server startup.

### 8.4 Communication Interfaces

- **REST API:** FastAPI JSON API for all CRUD operations. Auto-documented at `/docs`.
- **WebSocket:** Persistent connections for real-time seat status, health metrics, remote commands, and announcements. Reconnects automatically with exponential backoff and jitter.

---

## 9. Build Phases

### Phase 1 — Core

**Scope:** Offline license activation (Hardware ID generation, Ed25519 signature verification) · Launcher with setup wizard · FastAPI project structure · Alembic migrations · MAC address registration · Wake-on-LAN boot routine · Session start/stop/pause/resume API · React seat grid dashboard · Electron client agent (Windows first, with abstraction layer skeleton) · WebSocket real-time updates · Health check endpoint

**Exit Criteria:** A machine without a valid license is blocked at the Activation screen and cannot reach the setup wizard. Once a valid `license.key` matching the machine's Hardware ID is supplied, setup proceeds. Staff can start a session on a seat, see it update live on the dashboard, and end the session. The client PC locks on session end (Windows only initially).

### Phase 2 — Billing, POS and Printing

**Scope:** Time-based billing across all pricing models · Food and drink POS · Inventory tracking with low-stock alerts · Invoice generation · Thermal printer integration · PDF fallback · Audit log · Billing in paise (integer precision)

**Exit Criteria:** A complete checkout — time charge, food items, printed receipt — works end-to-end. Billing is accurate across per-minute, flat-hourly, and time-block models.

### Phase 3 — Members, Packages and Promotions

**Scope:** Member profiles and prepaid wallet · Loyalty tiers and discounts · Time packages and day passes · Prepaid voucher code generation and redemption · Promotions engine (happy hour, group discount, birthday bonus) · Per-zone pricing · Staff roles and PIN auth · Peak/off-peak scheduling

**Exit Criteria:** A member with an active package checks out correctly — package time is drawn first, per-minute billing kicks in on overflow, loyalty discount is applied, and the invoice is correct.

### Phase 4 — Operations and Experience

**Scope:** Remote PC commands (restart, shutdown, message, screenshot) · PC health monitoring (CPU, RAM, temp, disk) · Shift management with cash reconciliation · Expense tracking · Seat reservations · Branded lock screen with menu and Call Staff button · Announcements broadcast · Nightly SQLite backup · Graceful shutdown · Log rotation

**Exit Criteria:** Staff can restart a frozen PC from the dashboard. Shift opens and closes with a correct cash reconciliation report. Nightly backup runs automatically.

### Phase 5 — Events and Analytics

**Scope:** Tournament/event mode with bracket management · Owner analytics dashboard (Recharts) · Maintenance mode per seat with downtime tracking · Configurable feature flags · Mobile-responsive dashboard

**Exit Criteria:** An event is created, participants registered, bracket completed, and entry fees recorded. The analytics dashboard shows accurate revenue, utilisation, and health data from the local database. All feature flags toggle correctly.

### Phase 6 — Cross‑Platform Polish

**Scope:** Complete the agent's platform abstraction layer for macOS and Linux · Packaging for all three OSes (`.exe`, `.dmg`, `.deb`/AppImage) · Auto‑start scripts for each OS · Comprehensive testing on each platform · Update documentation and installation guides · Address OS‑specific permission requirements (Accessibility on macOS, sudoers on Linux)

**Exit Criteria:** The agent runs and locks/unlocks screens correctly on all three OSes. Remote restart/shutdown works on all platforms. Installation and auto‑start are documented and tested. The server Launcher works on all OSes.

### Phase 7 — Growth (V2, Future)

**Scope:** Online public booking portal · WhatsApp/SMS notifications via Sparrow SMS or WhatsApp Business API · Optional WAN remote access (read-only stats endpoint, phone-home pattern) · Multi-location support · PostgreSQL migration path

**Status:** Out of scope for V1. Architecturally planned.

---

## 10. Constraints and Assumptions

### 10.1 Constraints

- The system MUST NOT require an active internet connection for any core operational feature (exception: Tuya API for console control)
- No user data, billing data, or operational data SHALL be transmitted to any external server
- The billing engine MUST use integer arithmetic throughout to prevent rounding errors
- Database schema changes MUST be performed exclusively via Alembic migrations
- The system is scoped for single-location deployment in V1; multi-location is a V2 concern
- License verification MUST function entirely offline once a `license.key` has been issued; the private signing key MUST never ship inside the distributed application or its repository
- The client agent MUST abstract OS‑specific operations; platform‑dependent code MUST be isolated in the `platform/` module, with the UI and business logic shared across OSes

### 10.2 Assumptions

- Server machine runs one of the supported OSes (Windows, macOS, Linux) with Python 3.11+ and Node.js 20+ (unless packaged)
- Client machines run one of the supported OSes and support Electron
- Client machines support Wake-on-LAN and it is enabled (if using wired Ethernet)
- Client machines are connected to the network via wired ethernet for reliability; WiFi is optional but not recommended
- Consoles have "boot on power restore" enabled in their system settings
- The cafe has a reliable local area network
- The cafe owner accepts responsibility for configuring Tuya smart plugs correctly
- A single counter PC serves as the server throughout operation hours
- For macOS and Linux, the owner will grant the necessary permissions (Accessibility, screen recording, etc.) when prompted by the agent

---

## 11. Acceptance Criteria

The system SHALL be considered ready for production deployment when all of the following criteria are met:

| #     | Criterion                                                                                                                                                                                                                  |
| ----- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| AC-01 | Staff can open the dashboard and see all seat statuses in real time without refreshing the page                                                                                                                            |
| AC-02 | A session can be started and ended in under 10 seconds of total staff interaction                                                                                                                                          |
| AC-03 | Checkout correctly calculates time cost, package usage, applied discounts, and POS items — and produces a printed or PDF receipt with all required fields                                                                  |
| AC-04 | All client PCs boot automatically when the server starts, without staff touching individual machines                                                                                                                       |
| AC-05 | The owner can view today's revenue summary from their phone while on the cafe WiFi                                                                                                                                         |
| AC-06 | A frozen or unresponsive PC can be restarted from the dashboard without physically walking to the machine                                                                                                                  |
| AC-07 | No billing or session data is lost when the LAN connection between the server and a client agent drops and recovers                                                                                                        |
| AC-08 | All feature flags toggle their respective UI elements and backend endpoints correctly                                                                                                                                      |
| AC-09 | The audit log records all sensitive operations with correct timestamps, staff identity, and detail fields                                                                                                                  |
| AC-10 | A shift opens and closes with correct revenue, session count, and cash reconciliation figures                                                                                                                              |
| AC-11 | A member with an active package checks out with correct package drawdown and per-minute overflow billing                                                                                                                   |
| AC-12 | The setup wizard cannot be started without a `license.key` that passes signature verification and matches the current machine's Hardware ID; an invalid or mismatched license is clearly rejected without crashing the app |
| AC-13 | The Electron agent locks and unlocks the desktop correctly on Windows, macOS, and Linux (tested on each OS)                                                                                                                |
| AC-14 | Remote restart and shutdown commands work on Windows, macOS, and Linux                                                                                                                                                     |
| AC-15 | The server Launcher runs without errors on Windows, macOS, and Linux; the setup wizard and activation flow work identically across OSes                                                                                    |

---

## 12. Glossary

| Term                 | Definition                                                                                                                                |
| -------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| Agent                | The Electron application installed on each client PC. Handles lock/unlock, health metrics, and remote commands.                           |
| Audit Log            | Write-only record of all sensitive system operations for accountability and dispute resolution.                                           |
| Cashier              | Staff role with access to billing, POS, and checkout only.                                                                                |
| Dashboard            | The React web application used by staff at the counter.                                                                                   |
| Day Pass             | A package type granting unlimited play on a single calendar day for a fixed fee.                                                          |
| Ed25519              | An elliptic-curve digital signature algorithm used to sign and verify license files without requiring network access.                     |
| ESC/POS              | Command language used to communicate with thermal printers.                                                                               |
| Feature Flag         | A toggleable setting that enables or disables an optional system feature.                                                                 |
| Hardware ID          | A fingerprint derived from stable machine identifiers (motherboard serial, disk serial, machine GUID), used to lock a license to one PC.  |
| Keygen Tool          | An internal, non-distributed tool used by Neurotech Biratnagar to generate signed `license.key` files for customers.                      |
| Launcher             | The Tkinter GUI that starts and stops the Arcade server and runs the setup wizard on first use.                                           |
| LAN                  | Local Area Network — the internal network of the gaming cafe.                                                                             |
| License Key          | A signed file (`license.key`) issued per customer, containing cafe name, Hardware ID, license type, and a verifiable signature.           |
| Paise                | The smallest monetary unit (1/100th of a Rupee). All amounts are stored in paise for integer precision.                                   |
| Package              | A prepaid bundle of time (hours, day pass, night pass, or monthly pass) associated with a member account.                                 |
| Platform Abstraction | A design pattern that isolates OS‑specific code behind a common interface, allowing the same application to run on Windows, macOS, Linux. |
| POS                  | Point of Sale — the food and drink ordering component of the system.                                                                      |
| Promotion            | A time-limited discount or offer applied automatically at session start.                                                                  |
| Session              | A single continuous use period of a seat, from start to checkout.                                                                         |
| Smart Plug           | A Tuya-compatible Wi-Fi power outlet used to control console power state.                                                                 |
| Tuya API             | The cloud API provided by Tuya to control their compatible smart home devices, including smart plugs.                                     |
| Voucher              | A prepaid code redeemable for session time or wallet credit. Single-use, with optional expiry.                                            |
| WAL Mode             | SQLite Write-Ahead Logging mode — allows concurrent reads during writes, improving performance under load.                                |
| Walk-in              | A customer without a member account. Supported natively; billed at standard rate with no loyalty features.                                |
| Wake-on-LAN          | A network standard that allows a PC to be powered on remotely by sending a "magic packet" to its MAC address.                             |
| Zone                 | A named grouping of seats with a shared pricing rate (e.g., Standard PC, VIP PC, Console Corner).                                         |

---

_This document is the authoritative requirements specification for Arcade v2.0._

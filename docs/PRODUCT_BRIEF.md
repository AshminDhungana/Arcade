# Arcade — Product Brief

**Version 2.0 · June 2026**
**Prepared by:** Ashmin Dhungana
**Status:** Pre‑development · Design Complete

---

## The Problem

Running a gaming cafe on paper and manual timers is error‑prone and slow. Staff have to remember when each session started, calculate bills by hand, chase customers for payment, track food orders separately from the session tab, and walk across the room every time a PC freezes. When there are 30+ seats running at once, things fall through the cracks — time gets undercharged, food orders get lost, checkout takes too long, and the owner has no idea what's happening unless they are physically in the building.

Off‑the‑shelf solutions like SENET or iCafeCloud are cloud‑based, charge per seat per month, and are built for multi‑location chains with dedicated IT teams. A single‑location independent cafe doesn't need cloud infrastructure or a subscription that compounds every month. It needs something that works reliably on a local network, is simple enough for any staff member to operate, covers every real operational need — and can be owned outright.

---

## What Arcade Is

Arcade is a self‑hosted gaming cafe management system. It runs entirely on the cafe's local network. The server lives on the counter PC — **and it runs on Windows, macOS, or Linux** (whichever the cafe prefers). Staff manage everything — seats, billing, food orders, packages, members, console control, staff shifts, inventory, and PC health — from a single dashboard. Client PCs **also run on any OS** (Windows, macOS, Linux) with the Electron‑based agent that controls the desktop via a full‑screen kiosk overlay (not OS lock/unlock, which is inconsistent across platforms), reports health, and responds to remote commands. Consoles power on and off via smart plugs. The owner can check on revenue from their phone while on the cafe WiFi.

No internet required during daily operation. No subscription fees. No per‑seat licensing. Arcade is sold as a one‑time, perpetual license per location, activated offline and locked to the counter PC — the owner buys it once and keeps it.

---

## Who It's For

**Primary user:** Counter staff (cashiers and the cafe owner)
**Secondary user:** Cafe owner reviewing reports, configuring settings, and checking in remotely
**Indirect user:** Customers — who interact with the branded client screen and the printed receipt

Arcade is designed to work at any scale and style of gaming cafe: a simple 10‑seat neighborhood shop that just wants a timer and receipt, or a 50‑seat esports venue running tournaments, loyalty programs, and package deals. Feature flags let each owner turn on only what they need.

---

## Core Workflow

```
Customer walks in (or reservation triggers)
              │
              ▼
Staff picks a seat on the dashboard
              │
              ▼
Session starts → Agent hides kiosk overlay, branded splash shows, timer begins
              │
              ├──► Package check: active bundle? Draw from it first
              ├──► Promotion check: happy hour / discount active? Apply it
              │
              ▼
Timer runs on the server (cached locally on agent in SQLite for LAN‑drop resilience)
              │
              ├──► Low‑time warning popup on client screen (5 min remaining)
              ├──► Staff can add food/drink items to the tab at any time
              │
              ▼
Customer comes to counter → Staff clicks Checkout
              │
              ▼
Invoice: time charge + package usage + food/drink items + any discounts
              │
              ▼
Payment marked → Agent shows kiosk overlay (blocks desktop access)
              │
              ▼
Receipt printed (thermal or PDF)
```

---

## Key Capabilities

### Session Management

Start, stop, pause, and resume timed sessions per seat. The server holds the authoritative timer. If the LAN drops, the agent keeps the session state cached locally in SQLite so billing survives the outage. When reconnected, the server reconciles. Sessions can only be started by the server via the dashboard — the agent does not allow offline session start.

### Seat Reservations

Staff can reserve one or multiple seats in advance — for a group calling ahead, a birthday party, or a school visit. Reserved seats show on the dashboard grid with the customer name and time slot. Walk‑ins can see which seats are coming free and when.

### Billing Engine

All pricing models work simultaneously. The engine checks at session start which applies:

- Per‑minute, flat hourly, or time‑block rates
- Peak and off‑peak scheduling by time of day or day of week
- Device‑type pricing (PC ≠ PS5 ≠ VR)
- Active package entitlement (draws down before per‑minute billing)
- Active promotion modifier (happy hour, group discount, etc.)
- Member loyalty tier discount

Rates are locked at session start. Amounts are stored as integers (paise) to eliminate floating‑point rounding errors across hundreds of daily transactions.

### Time Packages & Day Passes

Customers can prepay time in bundles separate from the per‑minute wallet:

| Package      | Example                           |
| ------------ | --------------------------------- |
| Hour bundle  | Buy 10 hours, use across visits   |
| Day pass     | Unlimited play today for Rs. 200  |
| Night pass   | Rs. 150 — 10 PM to close          |
| Monthly pass | Rs. 800/month — regular customers |

When a session starts, Arcade checks for an active package and draws from it first. When the package runs out, billing switches to per‑minute automatically. Package balance updates are atomic to prevent race conditions.

### Promotions Engine

Time‑limited discounts and offers applied automatically at session start:

- Happy hour rates for specific time windows
- Flash discounts (e.g., 20% off Tuesday evenings)
- First‑visit discount for new members
- Group discounts when multiple seats are booked together
- Birthday month bonus time or discount

Applied discount and reason are stored in the session record and printed on the receipt.

### Prepaid Vouchers

Generate batches of one‑time redemption codes — for parents buying time for kids, event prizes, or retail sale. Codes print as QR codes or alphanumeric slips. Redeemable at the counter or directly at the client screen. Used codes are invalidated; unused ones expire on a set date.

### Food & Drink POS

Add menu items to an open session tab at any point during the session. Items are itemised on the final invoice alongside the time charge. Tied to the seat, not the customer.

### Inventory Tracking

Each menu item can optionally have a stock level tracked. When an item is sold, its stock decrements. When it hits the low‑stock threshold, a badge appears on the POS screen. When it hits zero, the item is greyed out and cannot be added to a bill. The owner restocks manually via the admin panel; restock events are logged with timestamp and quantity.

### Member System

Customers can create an account with a prepaid credit wallet, loyalty points, and tier‑based discounts. Visit history and total hours played are tracked. Walk‑in customers with no account are fully supported — they pay at the end as usual.

### PC & Console Control

**Client PCs (Kiosk Overlay Model):** The Electron agent uses a full‑screen, always‑on‑top kiosk overlay to control workstation access — **not OS lock/unlock**, which is unreliable and inconsistent across platforms. When no session is active, the overlay blocks access to the desktop and displays cafe branding, announcements, and a "Call Staff" button. On session start, the server sends a `HIDE_OVERLAY` command; the overlay is removed, the user gets full desktop access, and a branded splash screen shows session info for 5 seconds. On session end, the `SHOW_OVERLAY` command re‑enables the overlay.

**Kiosk Hardening:** The overlay window is configured with `kiosk: true`, `alwaysOnTop: true`, `closable: false`, and DevTools disabled. Global shortcuts like `Alt+F4`, `Cmd+Q`, `F12`, and `Ctrl+P` are intercepted and consumed to prevent bypass. Known gaps (`Ctrl+Alt+Del` on Windows, Wayland compositor variations on Linux) are documented and handled gracefully.

**Remote commands (from dashboard):**

| Command      | Use                                                     |
| ------------ | ------------------------------------------------------- |
| Restart      | Frozen PC, crashed game — without leaving the counter   |
| Shutdown     | End of night, force all PCs off simultaneously          |
| Send message | Announcement overlay on one or all screens              |
| Screenshot   | Admin‑only, JPEG compressed, rate-limited, max 1280×720 |

**Agent authentication:** Each agent uses a randomly generated `agent_secret` (created during setup) to authenticate with the server. The secret is stored in `agent.config.json` with restricted permissions (`chmod 600` on Linux/macOS).

**Console control:** PS5, Xbox, and other consoles are connected to Tuya‑compatible smart plugs. Arcade controls them via **local LAN (TinyTuya)** — no internet dependency during normal operation. Consoles need "boot on power restore" enabled once in their settings.

**Auto‑boot:** On power strip flip, server boots, launcher auto‑starts, FastAPI initialises, WoL magic packets boot all client PCs, and Tuya powers on all console plugs. No staff interaction needed per machine.

### PC Health Monitoring

Every client agent reports hardware metrics every 60 seconds:

- CPU usage %
- RAM usage %
- CPU temperature
- Disk space remaining
- Uptime

The dashboard shows a health badge on each seat card (green / yellow / red). The owner can see overheating or struggling machines at a glance without walking around.

### Branded Lock Screen & Announcements

The client screen when locked (overlay showing) displays: cafe logo, current time, remaining session time (if session is active), and a low‑balance warning with "Top Up at Counter" when relevant.

Staff can push a text announcement from the dashboard that appears as an overlay on all connected client screens simultaneously — for "Cafe closes in 30 min" end‑of‑night warnings, tournament callouts, or menu specials.

### Staff Roles & Shifts

**Roles:**

| Role    | Access                                                         |
| ------- | -------------------------------------------------------------- |
| Admin   | Full access — settings, reports, all billing, staff management |
| Cashier | Billing, POS, and checkout only — no settings or reports       |

**Staff ID + PIN** authentication with Argon2id hashing (OWASP-recommended). Each staff member has a unique Staff ID (e.g., "S001") and a secret PIN. 60‑second lockout after 5 failed attempts. JWT tokens include a `token_version` claim — changing a PIN or deactivating a staff member immediately invalidates all previously issued tokens without requiring a blacklist. The JWT signing secret is generated during setup using `secrets.token_hex(32)`.

**Shift management:** Staff open a shift (entering the cash float) and close it (entering the cash count). All sessions and transactions are tagged to the active shift. The shift report shows revenue, session count, average duration, cash expected vs counted, and discrepancy. The owner can review any past shift at any time.

### Expense Tracking

The owner logs outgoings in categories: rent, electricity, internet, snacks restock, hardware, maintenance, staff wages, other. Reports show gross revenue minus logged expenses as an approximate P&L. Not a replacement for accounting software — but a single place to see rough financial position without a spreadsheet.

### Tournament / Event Mode

Create events with: name, game title, date, entry fee, and prize pool. Register participants (members or walk‑ins). Assign participants to specific seats. Track match results and advance brackets (single or double elimination). Entry fees are charged to member wallets or as standalone transactions. The event summary shows all results, prize pool, and revenue generated.

### Analytics Dashboard

A single screen showing what the owner actually needs:

- Today's revenue, sessions, average session length, busiest hour
- Weekly revenue trend (bar chart)
- Top‑selling POS items
- Seat utilisation by zone and time of day
- Member registrations, active vs lapsed, top spenders
- Active health alerts (overheating machines, low stock items)
- Upcoming reservations

All data comes from the local SQLite database. No external service needed.

### Owner Mobile View

The React dashboard is fully mobile‑responsive. The owner's phone connected to the cafe WiFi opens the same dashboard in a browser and sees live seat status, today's revenue, and any alerts.

### Receipt & Printing

Receipts print to a thermal printer via `python‑escpos`. Any regular printer is supported via browser print or PDF. Receipt contents: seat number, customer name (if member), session start and end time, duration, time charge, package used (if applicable), discount applied (if applicable), itemised food/drink, total, and payment method.

---

## Licensing & Activation

Arcade uses a fully offline, hardware-locked licensing system. On first launch, the Launcher computes a Hardware ID using `py-machineid` (no admin privileges required, works on Windows/macOS/Linux). The owner sends this ID to Neurotech Biratnagar and receives a signed `license.key` file. The Launcher verifies the file using an embedded Ed25519 public key — **no internet connection or license server is ever required**. If the hardware changes, the owner contacts support for a reissued license. This keeps the system truly self‑hosted with zero recurring costs.

Time-limited trial licenses are supported using the same signature mechanism, with an expiry date encoded in the license payload.

---

## System Architecture

Arcade is a client‑server application that runs entirely on LAN.

| Component            | Description                                                                                                                        |
| -------------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| **Arcade Server**    | FastAPI backend + SQLite (WAL mode) on the counter PC (Windows/macOS/Linux)                                                        |
| **Arcade Dashboard** | React web app — staff UI at the counter, mobile view for the owner                                                                 |
| **Arcade Launcher**  | Tkinter GUI — License Activation, setup wizard, starts/stops the server, live logs (cross‑platform)                                |
| **Arcade Agent**     | Electron app on each client PC — kiosk overlay, health metrics, remote commands, local SQLite session persistence (cross‑platform) |

The backend exposes a REST API for all data operations and WebSocket endpoints for real‑time seat status, health metrics, remote commands, and announcements. Reconnection uses exponential backoff with jitter (starting at 2 seconds, capping at 60 seconds) and server‑side heartbeat pings (30 seconds) to detect dead connections.

The **agent** uses a platform abstraction layer inside Electron: the same UI code runs on all OSes, while OS‑specific modules handle kiosk overlay display, shutdown/restart commands, screenshot capture, and auto‑start registration. OS lock/unlock is **not** used — the kiosk overlay model is consistent across all platforms.

---

## Technical Decisions

| Decision                 | Choice                                                                  | Reason                                                                                                 |
| ------------------------ | ----------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| **Database**             | SQLite with WAL mode + `busy_timeout=5000` + `synchronous=NORMAL`       | Simple, local, no setup. WAL + pragmas handle concurrency without `SQLITE_BUSY` errors                 |
| **Migrations**           | Alembic                                                                 | Versioned, reversible schema changes                                                                   |
| **Backend**              | FastAPI + Uvicorn + Async SQLAlchemy (`aiosqlite`)                      | Fast, async, automatic API docs. Async DB prevents event loop blocking                                 |
| **Frontend**             | React + Vite + TailwindCSS + React Query                                | Industry standard, excellent real‑time support, mobile‑responsive                                      |
| **Launcher**             | Tkinter GUI                                                             | No terminal needed — any staff member can start the server (cross‑platform)                            |
| **Client agent**         | Electron + `systeminformation` + `better-sqlite3`                       | Full system control; hardware metrics; local SQLite session persistence; cross‑platform                |
| **Agent access control** | Kiosk overlay (full‑screen, always‑on‑top, hardened)                    | Consistent across Windows/macOS/Linux; explicit SRS decision; avoids OS lock/unlock issues             |
| **Console control**      | Tuya **local LAN** (TinyTuya), not cloud API                            | No internet dependency after initial pairing; faster and more reliable                                 |
| **Real‑time**            | WebSockets + exponential backoff + heartbeat                            | Instant updates; resilient to LAN drops                                                                |
| **Auth**                 | Staff ID + PIN + Argon2id hashing + JWT with `token_version` revocation | OWASP‑recommended hashing; unique Staff ID per member; immediate revocation on PIN change/deactivation |
| **Agent auth**           | Random `agent_secret` per seat (generated at setup time)                | Prevents impersonation; not hardcoded in source                                                        |
| **Printing**             | python‑escpos + PDF fallback                                            | Works with thermal and any regular printer                                                             |
| **Billing precision**    | Integer storage (paise)                                                 | No floating‑point rounding errors across hundreds of daily transactions                                |
| **Feature flags**        | Toggleable per‑cafe in Settings                                         | One codebase handles a 10‑seat simple cafe and a 50‑seat esports venue                                 |
| **Screenshot delivery**  | JPEG at 80% quality, scaled to 1280×720 max, rate-limited               | Prevents WebSocket payload bloat; adequate for monitoring                                              |
| **Scheduled tasks**      | APScheduler `AsyncIOScheduler`                                          | Integrates natively with FastAPI's event loop; handles exceptions gracefully                           |
| **Shutdown lifecycle**   | `lifespan` context manager                                              | Modern FastAPI pattern; replaces deprecated `@app.on_event`                                            |
| **Hardware fingerprint** | `py-machineid` (primary) + OS fallbacks                                 | No admin privileges required on any OS; works on Windows/macOS/Linux                                   |
| **Cross‑platform**       | Python + Electron                                                       | Both run on Windows, macOS, Linux — no platform lock‑in                                                |
| **Server recovery**      | Load active sessions from DB on startup                                 | Preserves billing data and allows agents to re-sync                                                    |
| **Agent offline start**  | Prohibited — sessions only from server                                  | Simplifies billing reconciliation and prevents fraud                                                   |

---

## Modularity

Arcade is not a fixed product — it adapts to the cafe. Feature flags in Settings let each owner turn on only what they need:

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

The dashboard only shows UI for enabled features. Staff are not overwhelmed by controls they will never use.

---

## Build Plan

### Phase 1 — Core

Offline license activation (Hardware ID via `py-machineid` + Ed25519 signature verification) gating the setup wizard · Launcher with setup wizard · FastAPI project structure with `lifespan` context manager · Alembic migrations · Async SQLAlchemy setup with `aiosqlite` and WAL pragmas · MAC address registration · Wake‑on‑LAN boot routine · Session start/stop/pause/resume API · React seat grid dashboard · Electron client agent with hardened kiosk overlay (Windows first) · Local SQLite persistence skeleton · WebSocket real‑time updates · Health check endpoint · Agent secret authentication

### Phase 2 — Billing, POS & Printing

Time‑based billing across all pricing models · Food & drink POS · Inventory tracking with low‑stock alerts · Invoice generation · Thermal printer integration · PDF fallback · Audit log · Billing in paise (integer precision)

### Phase 3 — Members, Packages & Promotions

Member profiles + prepaid wallet · Loyalty tiers and discounts · Time packages and day passes · Prepaid voucher code generation and redemption · Promotions engine (happy hour, group discount, birthday bonus) · Per‑zone pricing · Staff roles and **Staff ID + PIN** auth (Argon2id) · JWT with `token_version` revocation · Peak/off‑peak scheduling · JWT secret generation via `secrets.token_hex(32)`

### Phase 4 — Operations & Experience

Remote PC commands (restart, shutdown, message, screenshot with JPEG compression) · PC health monitoring (CPU, RAM, temp, disk) · Shift management with cash reconciliation · Expense tracking · Seat reservations (staff‑side) · Branded overlay with menu and Call Staff button · Announcements broadcast · Nightly SQLite backup (APScheduler) · Graceful shutdown via `lifespan` · Log rotation · Agent persistent SQLite session storage and sync · Agent secret authentication

### Phase 5 — Events & Analytics

Tournament/event mode with bracket management · Owner analytics dashboard (Recharts) · Maintenance mode per seat with downtime tracking · Configurable feature flags · Mobile‑responsive dashboard · Screenshot rate‑limiting

### Phase 6 — Cross‑Platform Polish

Complete the agent's platform abstraction layer for macOS and Linux · Packaging for all three OSes (`.exe`, `.dmg`, `.deb`/AppImage) · Auto‑start scripts for each OS · Comprehensive testing on each platform · Update documentation and installation guides · Verify kiosk hardening on all platforms

### Phase 7 — Growth (V2)

Online public booking portal · WhatsApp/SMS notifications via Sparrow SMS / WhatsApp Business API · Optional WAN remote access (read‑only stats endpoint) · Multi‑location support · PostgreSQL migration path

---

## Success Metrics

The system is working when:

- Staff can open the dashboard and see all seat statuses in real time without refreshing
- A session can be started and ended in under 10 seconds of staff interaction
- Checkout correctly calculates time cost, package usage, discounts, and food items — and prints a receipt
- The entire cafe boots in the morning without anyone touching an individual machine
- The owner can check today's revenue from their phone while in the back room
- A frozen PC can be restarted from the dashboard without walking over to it
- No billing data is lost during a LAN interruption, even if the agent crashes
- The kiosk overlay blocks desktop access consistently on Windows, macOS, and Linux
- Bypass attempts (Alt+F4, Cmd+Q, F12, Ctrl+P) are blocked on all platforms
- Active sessions are preserved when the server restarts

---

## V2 Roadmap

| Feature                    | Why                                                                                                     |
| -------------------------- | ------------------------------------------------------------------------------------------------------- |
| Online seat booking portal | Customers reserve from Facebook/Instagram before walking in; reduces walk‑in uncertainty                |
| WhatsApp/SMS notifications | Nepal's dominant channels — low‑balance alerts, booking confirmations, event broadcasts                 |
| Optional WAN remote access | Owner checks in from home via read‑only stats endpoint; no inbound port needed (phone‑home pattern)     |
| Multi‑location             | Owner with two cafes sees both in one dashboard; cross‑location member accounts                         |
| PostgreSQL migration       | SQLite handles one location well; Postgres is the upgrade path when volume or multi‑location demands it |

---

## Out‑of‑the‑Box Experience

On first launch, the owner sees a License Activation screen showing a Hardware ID unique to their counter PC (generated via `py-machineid`, no admin privileges required). They send that ID to Neurotech Biratnagar and receive a `license.key` file back — a one‑time, offline step tied to their purchase. Time-limited trial licenses are also supported.

Once activated, the setup wizard asks for: cafe name, server IP, port, admin Staff ID + PIN, cashier Staff ID + PIN. The wizard generates a unique `agent_secret` for each seat using a cryptographically secure random generator. The owner then configures zones, rates, and the menu in the dashboard. Seat MAC addresses are registered once per machine. Console smart plugs are paired once via Tuya. Feature flags are set to match the cafe's needs.

After that, daily operation requires no technical knowledge and no internet connection — including for license checks, which run locally every time the Launcher starts. The launcher is a double‑click (on any OS). The dashboard is a visual grid. Checkout is three button presses.

If the Launcher is closed while the server is running, a confirmation dialog appears: "The Arcade server is still running. Closing the Launcher will stop the server. Are you sure?"

---

_Arcade is built and maintained by Ashmin Dhungana_

# Arcade — Product Brief

**Version 2.0 · June 2026**  
**Prepared by:** Ashmin Dhungana  
**Status:** Pre‑development · Planning complete

---

## The Problem

Running a gaming cafe on paper and manual timers is error‑prone and slow. Staff have to remember when each session started, calculate bills by hand, chase customers for payment, track food orders separately from the session tab, and walk across the room every time a PC freezes. When there are 30+ seats running at once, things fall through the cracks — time gets undercharged, food orders get lost, checkout takes too long, and the owner has no idea what's happening unless they are physically in the building.

Off‑the‑shelf solutions like SENET or iCafeCloud are cloud‑based, charge per seat per month, and are built for multi‑location chains with dedicated IT teams. A single‑location independent cafe doesn't need cloud infrastructure or a subscription that compounds every month. It needs something that works reliably on a local network, is simple enough for any staff member to operate, covers every real operational need — and can be owned outright.

---

## What Arcade Is

Arcade is a self‑hosted gaming cafe management system. It runs entirely on the cafe's local network. The server lives on the counter PC — **and it runs on Windows, macOS, or Linux** (whichever the cafe prefers). Staff manage everything — seats, billing, food orders, packages, members, console control, staff shifts, inventory, and PC health — from a single dashboard. Client PCs **also run on any OS** (Windows, macOS, Linux) with the Electron‑based agent that locks/unlocks screens, reports health, and responds to remote commands. Consoles power on and off via smart plugs. The owner can check on revenue from their phone while on the cafe WiFi.

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
Session starts → PC unlocks, branded splash shows, timer begins
              │
              ├──► Package check: active bundle? Draw from it first
              ├──► Promotion check: happy hour / discount active? Apply it
              │
              ▼
Timer runs on the server (cached locally on agent for LAN‑drop resilience)
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
Payment marked → PC locks automatically
              │
              ▼
Receipt printed (thermal or PDF)
```

---

## Key Capabilities

### Session Management

Start, stop, pause, and resume timed sessions per seat. The server holds the authoritative timer. If the LAN drops, the agent keeps the session start time cached locally so billing survives the outage. When reconnected, the server reconciles.

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

When a session starts, Arcade checks for an active package and draws from it first. When the package runs out, billing switches to per‑minute automatically.

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

**Client PCs:** The Electron agent locks and unlocks the desktop (on Windows, macOS, and Linux using OS‑specific methods). On session start, a branded splash screen shows for 5 seconds (cafe logo, session time, menu, "Call Staff" button), then minimises to a system tray icon showing remaining time. On session end, the desktop locks.

**Remote commands (from dashboard):**

| Command      | Use                                                   |
| ------------ | ----------------------------------------------------- |
| Restart      | Frozen PC, crashed game — without leaving the counter |
| Shutdown     | End of night, force all PCs off simultaneously        |
| Send message | Announcement overlay on one or all screens            |
| Screenshot   | Admin‑only verification of what's on screen           |

**Console control:** PS5, Xbox, and other consoles are connected to Tuya‑compatible smart plugs. Arcade calls the Tuya API to power them on/off with sessions. Consoles need "boot on power restore" enabled once in their settings.

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

The client screen when locked shows: cafe logo, current time, remaining session time (if session is active), and a low‑balance warning with "Top Up at Counter" when relevant.

Staff can push a text announcement from the dashboard that appears as an overlay on all connected client screens simultaneously — for "Cafe closes in 30 min" end‑of‑night warnings, tournament callouts, or menu specials.

### Staff Roles & Shifts

**Roles:**

| Role    | Access                                                         |
| ------- | -------------------------------------------------------------- |
| Admin   | Full access — settings, reports, all billing, staff management |
| Cashier | Billing, POS, and checkout only — no settings or reports       |

PIN‑based authentication with 60‑second lockout after 5 failed attempts.

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

## System Architecture

Arcade is a client‑server application that runs entirely on LAN.

| Component            | Description                                                                                    |
| -------------------- | ---------------------------------------------------------------------------------------------- |
| **Arcade Server**    | FastAPI backend + SQLite database on the counter PC (Windows/macOS/Linux)                      |
| **Arcade Dashboard** | React web app — staff UI at the counter, mobile view for the owner                             |
| **Arcade Launcher**  | Tkinter GUI — starts/stops the server, shows live logs, health check (cross‑platform)          |
| **Arcade Agent**     | Electron app on each client PC — lock/unlock, health metrics, remote commands (cross‑platform) |

The backend exposes a REST API for all data operations and WebSocket endpoints for real‑time seat status, health metrics, remote commands, and announcements. Reconnection uses exponential backoff with jitter and server‑side heartbeat pings to detect dead connections.

The **agent** uses a platform abstraction layer inside Electron: the same UI code runs on all OSes, while OS‑specific modules handle screen locking (via `rundll32` on Windows, AppleScript on macOS, `xdg‑screensaver` on Linux), shutdown/restart commands, and auto‑start registration. This keeps the codebase clean and maintainable.

---

## Technical Decisions

| Decision          | Choice                                       | Reason                                                                    |
| ----------------- | -------------------------------------------- | ------------------------------------------------------------------------- |
| Database          | SQLite with WAL mode                         | Simple, local, no setup — WAL mode eliminates read/write blocking         |
| Migrations        | Alembic                                      | Versioned, reversible schema changes — essential as the project evolves   |
| Backend           | FastAPI + Uvicorn                            | Fast, async, automatic API docs, Python ecosystem                         |
| Frontend          | React + Vite + TailwindCSS + React Query     | Industry standard, excellent real‑time support, mobile‑responsive         |
| Launcher          | Tkinter GUI                                  | No terminal needed — any staff member can start the server                |
| Client agent      | Electron + `systeminformation`               | Full system control; hardware metrics with no extra tools; cross‑platform |
| Console control   | Tuya smart plug API                          | No agent needed on the console, inexpensive hardware                      |
| Real‑time         | WebSockets + exponential backoff + heartbeat | Instant updates; resilient to LAN drops and server restarts               |
| Auth              | PIN‑based with session tokens + lockout      | Simple for V1; secure enough for a local network                          |
| Printing          | python‑escpos + PDF fallback                 | Works with thermal and any regular printer                                |
| Billing precision | Integer storage (paise)                      | No floating‑point rounding errors across hundreds of daily transactions   |
| Feature flags     | Toggleable per‑cafe in Settings              | One codebase handles a 10‑seat simple cafe and a 50‑seat esports venue    |
| Cross‑platform    | Python + Electron                            | Both run on Windows, macOS, Linux — no platform lock‑in                   |

---

## Modularity

Arcade is not a fixed product — it adapts to the cafe. Feature flags in Settings let each owner turn on only what they need:

- A simple neighborhood cafe: sessions, billing, POS, receipt printing. Everything else off.
- A mid‑size operation: add members, packages, inventory, shift management, seat reservations.
- A full esports venue: everything on — tournaments, promotions, analytics, health monitoring, vouchers.

The dashboard only shows UI for enabled features. Staff are not overwhelmed by controls they will never use.

---

## Build Plan

### Phase 1 — Core

Offline license activation (Hardware ID + Ed25519 signature verification) gating the setup wizard · Launcher with setup wizard · FastAPI project structure · Alembic migrations · MAC address registration · Wake‑on‑LAN boot routine · Session start/stop API · React seat grid dashboard · Electron client agent (Windows first, with abstraction layer for later OS support) · WebSocket real‑time updates · Health check endpoint

### Phase 2 — Billing, POS & Printing

Time‑based billing across all pricing models · Food & drink POS · Inventory tracking with low‑stock alerts · Invoice generation · Thermal printer integration · PDF fallback · Audit log · Billing in paise (integer precision)

### Phase 3 — Members, Packages & Promotions

Member profiles + prepaid wallet · Loyalty tiers and discounts · Time packages and day passes · Prepaid voucher code generation and redemption · Promotions engine (happy hour, group discount, birthday bonus) · Per‑zone pricing · Staff roles and PIN auth · Peak/off‑peak scheduling

### Phase 4 — Operations & Experience

Remote PC commands (restart, shutdown, message, screenshot) · PC health monitoring (CPU, RAM, temp, disk) · Shift management with cash reconciliation · Expense tracking · Seat reservations (staff‑side) · Branded lock screen with menu and Call Staff button · Announcements broadcast · Nightly SQLite backup · Graceful shutdown · Log rotation

### Phase 5 — Events & Analytics

Tournament/event mode with bracket management · Owner analytics dashboard (Recharts) · Maintenance mode per seat with downtime tracking · Configurable feature flags · Mobile‑responsive dashboard

### Phase 6 — Cross‑Platform Polish

Complete the agent's platform abstraction layer for macOS and Linux · Packaging for all three OSes (`.exe`, `.dmg`, `.deb`/AppImage) · Auto‑start scripts for each OS · Comprehensive testing on each platform · Update documentation and installation guides

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
- No billing data is lost during a LAN interruption

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

On first launch, the owner sees a License Activation screen showing a Hardware ID unique to their counter PC. They send that ID to Neurotech Biratnagar and receive a `license.key` file back — a one‑time, offline step tied to their purchase. Once activated, the setup wizard asks for five things: cafe name, server IP, port, admin PIN, cashier PIN. The owner then configures zones, rates, and the menu in the dashboard. Seat MAC addresses are registered once per machine. Console smart plugs are paired once via Tuya. Feature flags are set to match the cafe's needs.

After that, daily operation requires no technical knowledge and no internet connection — including for license checks, which run locally every time the Launcher starts. The launcher is a double‑click (on any OS). The dashboard is a visual grid. Checkout is three button presses.

---

_Arcade is built and maintained by Ashmin Dhungana_

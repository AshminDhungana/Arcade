# Arcade Deployment Guide

This guide covers deploying the Arcade server (Launcher + FastAPI backend), the Arcade Agent on client PCs, and associated infrastructure (printers, smart plugs, networking).

## Security — `arcade.config.json` Permissions

`arcade.config.json` contains Argon2id-hashed PINs, the JWT signing secret, and per-seat `agent_secret` tokens. It **must never be readable by anyone except the owner**.

### Linux / macOS

Set the file permissions to `600` (owner read-write only):

```bash
chmod 600 arcade.config.json
```

### Windows

Restrict the file via ACL by removing inherited permissions and granting only the owner full access:

1. Right-click `arcade.config.json` → **Properties** → **Security** tab.
2. Click **Advanced** → **Disable inheritance** → **Remove all inherited permissions**.
3. Click **Add** → **Select a principal** → enter your username → **Full control**.
4. Confirm with **OK** on all dialogs.

## Feature Flags

Feature flags live in the `AppSettings` table and are toggled from the dashboard
**Settings → Feature Flags** tab (admin). They can also be flipped via
`PATCH /api/settings` with a `Bearer` admin token, e.g.:

```bash
curl -X PATCH http://localhost:8741/api/settings \
  -H "Authorization: Bearer <admin-jwt>" \
  -H "Content-Type: application/json" \
  -d '{"enable_tournaments": "true"}'
```

Unknown / missing flags default to **off**. Defaults below are seeded by
`backend/scripts/seed_dev.py`.

| Flag                      | Default | Scope                                | Recommended setting                          |
| ------------------------- | ------- | ------------------------------------ | -------------------------------------------- |
| `enable_members`          | `true`  | Dashboard / Members page            | **ON** — core membership feature             |
| `enable_packages`         | `true`  | Members / Packages & pricing        | **ON** unless you do not sell time packages  |
| `enable_pos`             | `true`  | POS sales & billing                 | **ON** — core revenue feature                |
| `enable_inventory`        | `false` | POS / Inventory tracking            | ON only if you track stock                  |
| `enable_reservations`     | `true`  | Reservations                        | **ON** if you take seat bookings             |
| `enable_vouchers`         | `false` | Vouchers & promotions               | ON to enable voucher batch generation        |
| `enable_tournaments`      | `false` | Events / Tournaments (Phase 6)      | ON to run in-cafe tournaments               |
| `enable_expense_tracking` | `false` | Expense tracking                    | OFF in v1.0 (no UI/endpoint yet)             |
| `enable_health_monitoring`| `true`  | Agent health dashboard              | **ON** if agents report health metrics       |
| `enable_tuya`             | `false` | Tuya smart-plug power control (HW)  | ON only with paired Tuya plugs (see below)   |

> `require_member_for_session` is a related config-style flag (default `false`):
> when ON, starting a session requires attaching a member. It is not part of the
> 10 UI feature flags above.

## Tuya Smart-Plug Pairing

Console seats can be powered on/off remotely through a Tuya smart plug (local LAN, no cloud at
runtime). **Pairing requires one-time internet access** to extract the plug's `local_key`;
after that, control is fully offline.

### One-time pairing (needs internet)

1. Plug the smart plug in and add it to the **Tuya Smart** (or Smart Life) app on a phone while
   on the cafe LAN and online.
2. On each **console** (PS5/Xbox), enable **"boot on power restore" / auto power-on** in the
   console's system settings — otherwise switching the plug on restores power but does not boot
   the console. This is a one-time console setting.
3. Put the plug on the same Wi-Fi as the server and confirm it responds in the app.
4. Extract the **`device_id`** and **`local_key`** using the TinyTuya wizard. The wizard pulls
   `local_key`s from the **Tuya IoT Platform** (this is the one-time internet step), so first
   create a free developer account at <https://iot.tuya.com>, create a Cloud project, and link
   the same Tuya app account/devices to it. Then, on a machine on the cafe LAN:
   ```bash
   pip install tinytuya
   tinytuya wizard        # prompts for Tuya IoT API Key/Secret, downloads device list
                         # (device_id + local_key), then scans the LAN to match IP addresses
   ```
   The wizard writes `devices.json` / `snapshot.json`. Record each plug's `device_id` (a 20–22
   char ID) and `local_key` (a short hex/base64-like secret). (`tinytuya scan` alone only finds
   IPs — it cannot recover `local_key`s without the cloud step above.)
5. Note the plug's LAN **`ip_address`** (reserve a DHCP lease / static IP so it stays stable) and
   use `protocol_version` `"3.3"` unless the device requires otherwise (newer firmware may need
   `"3.4"` / `"3.5"`).

### Configure (offline from here)

5. Add the plug to `arcade.config.json` under `tuya_devices`, bound to the seat:
   ```json
   {
     "tuya_devices": [
       {
         "seat_id": "seat_001",
         "device_id": "0123456789abcdef0123",
         "local_key": "a1b2c3d4e5f6a7b8",
         "ip_address": "192.168.1.51",
         "protocol_version": "3.3"
       }
     ]
   }
   ```
6. Enable the feature flag (default is `false`):
   ```bash
   curl -X PATCH http://localhost:8741/api/settings \
     -H "Authorization: Bearer <admin-jwt>" \
     -H "Content-Type: application/json" \
     -d '{"enable_tuya": "true"}'
   ```
7. Restart the server. Verify with `POST /api/seats/seat_001/power-on` (Admin) — the plug's
   indicator should turn on and a `TUYA_POWER_ON` audit entry is written.

**Behavior:** `power_on`/`power_off` are best-effort and non-fatal — if the flag is off, the
seat has no Tuya device, or the plug is unreachable, the call is a silent no-op (failure logged
at WARNING). The same service also fires automatically on session start (power ON) and checkout
(power OFF) for seats that have a plug bound. See `docs/api-reference.md` → Remote Commands for
the endpoint contract.

## Agent Installation & Provisioning

The Arcade Agent is distributed as a platform installer (`ArcadeAgent-<ver>-setup.exe`,
`.dmg`, AppImage). **No `agent.config.json` is shipped or hand-copied.** The agent
self-provisions on first launch.

### First-time setup (operator)

1. On the dashboard, open the target seat and click **Enroll Code** (admin). A one-time
   code (e.g. `ABCD-EFGH`) appears — it expires in 15 minutes and is single-use.
2. On the gaming PC, install and launch `ArcadeAgent`. The agent auto-discovers the
   server on the LAN (UDP beacon). If discovery fails on a strict network, the operator
   can set `server_url` in the setup window.
3. In the first-run window, type the enroll code and click **Connect**. The agent
   contacts the server, receives its `seat_id` + `agent_secret`, writes a local
   `agent.config.json`, and relaunches into the kiosk. **Done — no file copying.**

### Later changes (in-agent Settings)

In the agent's staff-override dialog, the **Override** button (enter the staff override
PIN to drop the kiosk) and the **Settings** button are both available. The **Settings**
button currently re-opens the setup window to **re-enroll the agent with a new code**.
Editing the server address or adjusting reconnect/health intervals from in-agent Settings
is a planned **v2** enhancement and is **not** available in v1 — those fields must be set
out-of-band (e.g. hand-editing `agent.config.json`) for now.

### Emergency master PIN

If the agent cannot reach the server, the staff override PIN is unavailable (it is
provisioned by the server). The build-injected **master PIN** then works as an emergency
unlock (see `tools/keygen/generate_keys.py`). It is accepted **only** when the server is
unreachable, and is never shown in the UI.

## Receipt Printer Setup

Arcade prints ESC/POS thermal receipts (via `python-escpos`) automatically on checkout, and
offers a PDF fallback. All money is formatted as `Rs. X.XX` in the print layer only. Printer
settings live in `arcade.config.json` (they are **not** in the `AppSettings` DB table).

### USB printer (recommended)

1. Connect the thermal printer via USB and note its vendor/product IDs (e.g. Epson:
   `0x04b8` / `0x0202`).
2. Set in `arcade.config.json`:
   ```json
   {
     "printer_type": "usb",
     "printer_usb_vendor": "0x04b8",
     "printer_usb_product": "0x0202"
   }
   ```
3. Restart the server. On the next checkout the receipt prints automatically.

### Network printer

Set `"printer_type": "network"`. The current `PrintService` connects to
`Network("127.0.0.1", 9100)` — i.e. a printer reachable at localhost:9100 (common when the
printer is shared through a local print server on the counter PC). See Known Limitations.

### PDF fallback

If no printer is configured (or the printer is unavailable), printing logs a warning and falls
back to a dummy printer — no receipt is emitted. Staff can always open a print-friendly receipt
from the dashboard: `GET /api/invoices/{id}/pdf` returns HTML that triggers the browser's
`window.print()` dialog (save as PDF or print to any available printer).

> **Known limitations:**
> - Network printing is hardcoded to `127.0.0.1:9100`; a directly networked printer at a
>   different IP is not yet configurable without a code change.
> - If `printer_type` is unset or unrecognised, Arcade silently uses the dummy printer (no
>   paper, just a log line) rather than erroring — confirm the receipt actually prints on first
>   setup.

---

# Launcher Setup — macOS & Linux (Operators)

The Launcher is the Tkinter GUI that runs on the **counter/server PC**. It handles license
activation, the first-run setup wizard, and the Start/Stop server controls.

> **Packaged binary (recommended for operators):** Like the Windows NSIS installer, macOS and
> Linux distributables are built with PyInstaller `--onedir` (see ARCH-03 validation). The
> binary bundles Python + Tkinter + all deps. **No system Python install is required at
> runtime** — but `python3-tk` **must be present on the build machine**. The resulting binary
> runs on a clean target machine.
>
> **From source (developers):** Instructions below also cover running from source for
> development or debugging.

---

## Prerequisites

### macOS

| Component | Installation |
|-----------|--------------|
| **Python 3.12** | `brew install python@3.12` (or use pyenv) |
| **Tkinter** | `brew install python-tk@3.12` — **required**; macOS system Python lacks Tkinter in newer versions |
| **Build tools** | `xcode-select --install` (provides `clang`, `make`, etc.) |
| **PyInstaller** | `pip install pyinstaller` (for building the binary) |

**Verify Tkinter works:**
```bash
python3 -c "import tkinter; tkinter._test()"
```
A small test window should appear. If it fails, reinstall `python-tk`.

### Linux (Debian/Ubuntu)

| Component | Installation |
|-----------|--------------|
| **Python 3.12** | `sudo apt update && sudo apt install python3.12 python3.12-venv python3.12-dev` (or use `deadsnakes` PPA for newer Ubuntu) |
| **Tkinter** | `sudo apt install python3.12-tk` — **required** |
| **Build tools** | `sudo apt install build-essential libssl-dev libffi-dev` |
| **PyInstaller** | `pip install pyinstaller` |

**Verify Tkinter works:**
```bash
python3 -c "import tkinter; tkinter._test()"
```

### Linux (Fedora/RHEL)

```bash
sudo dnf install python3.12 python3.12-tkinter python3.12-devel gcc openssl-devel libffi-devel
```

### Linux (Arch)

```bash
sudo pacman -S python tk base-devel
```

---

## Installation Methods

### Method A: Packaged Binary (Operator Workflow)

1. **Download** the platform-specific distributable:
   - macOS: `ArcadeLauncher-<version>.dmg` or `.zip` (contains `ArcadeLauncher.app`)
   - Linux: `ArcadeLauncher-<version>-x86_64.AppImage` or `.deb`

2. **Install:**
   - **macOS:** Open the `.dmg`, drag `ArcadeLauncher.app` to `/Applications`.
     - **Gatekeeper bypass (unsigned v1.0):** The app is unsigned. On first launch,
       right-click → **Open** (shows "Open" button), or run:
       ```bash
       sudo xattr -dr com.apple.quarantine "/Applications/Arcade Launcher.app"
       ```
     - Grant **Accessibility** and **Screen Recording** permissions if prompted
       (required for global hotkeys and screenshots). Re-grant after every update
       (unsigned app has no stable code identity).
   - **Linux (AppImage):** `chmod +x ArcadeLauncher-*.AppImage && ./ArcadeLauncher-*.AppImage`
   - **Linux (.deb):** `sudo dpkg -i arcade-launcher_*.deb && sudo apt -f install`

3. **Run:** Launch from Applications menu or terminal: `ArcadeLauncher` (or `./ArcadeLauncher-*.AppImage`).

### Method B: From Source (Development / Debugging)

```bash
# Clone repo
git clone https://github.com/neurotech-biratnagar/arcade.git
cd arcade

# Create virtual environment
python3.12 -m venv venv
source venv/bin/activate

# Install backend deps (includes Tkinter via system package)
pip install -r backend/requirements.txt

# Run Launcher
python launcher.py
```

---

## First Launch — License Activation

On **every launch**, the Launcher checks the license before showing any UI (FR-SYS-008):

1. **Activation Screen** (license missing / invalid / wrong machine):
   - Displays your **Hardware ID** (copyable read-only field).
   - Instructions: "Send this Hardware ID to Seller to receive your license.key"
   - **Browse for license.key** button: opens file dialog, copies file to app root, re-checks license.
   - Specific error per `LicenseError` variant (see SDD §16.7 table).
   - **Retry** button to re-check without browsing.

2. **Setup Wizard** (valid license, no `arcade.config.json`):
   - Step 1: Café name, server host, port.
   - Step 2: Admin Staff ID + PIN; Cashier Staff ID + PIN; Staff Override Code (optional).
   - Step 3: Number of seats → generates one `agent_secret` per seat via `secrets.token_hex(32)`.
   - On finish: writes `arcade.config.json` with Argon2id-hashed PINs, `jwt_secret`, all `agent_secrets`.
   - Also writes `license_status` record to DB.

3. **Main Screen** (license valid, config exists):
   - **Start/Stop Server** button: spawns/terminates `uvicorn backend.main:app` as subprocess.
   - **Live log display:** `ScrolledText` tailing `stdout`/`stderr`.
   - **Server status indicator** (green/red dot using canvas).
   - **Open Dashboard** button: opens `http://localhost:{port}` in default browser.
   - **Close confirmation (FR-SYS-010):** if server running, asks "The Arcade server is still running. Closing will stop it. Continue?" → terminates server on confirm.

---

## File Permissions (macOS / Linux)

The Launcher writes/reads sensitive files. Apply the same restrictions as the agent:

```bash
chmod 600 arcade.config.json
chmod 600 license.key
```

On macOS, also clear quarantine on the config if you copied it manually:
```bash
xattr -d com.apple.quarantine arcade.config.json 2>/dev/null || true
```

---

## Auto-Start (Server PC)

The Launcher should start automatically on boot so the server is always available.

### macOS — LaunchDaemon (system-wide, runs before login)

Create `/Library/LaunchDaemons/com.arcade.launcher.plist` (requires `sudo`):

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.arcade.launcher</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Applications/Arcade Launcher.app/Contents/MacOS/ArcadeLauncher</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/var/log/arcade-launcher.log</string>
    <key>StandardErrorPath</key>
    <string>/var/log/arcade-launcher.err.log</string>
    <key>WorkingDirectory</key>
    <string>/Applications/Arcade Launcher.app/Contents/Resources</string>
</dict>
</plist>
```

Load it:
```bash
sudo launchctl load /Library/LaunchDaemons/com.arcade.launcher.plist
sudo launchctl start com.arcade.launcher
```

**Unload:** `sudo launchctl unload /Library/LaunchDaemons/com.arcade.launcher.plist`

> **Why LaunchDaemon not LaunchAgent?** The server must be running before any user logs in
> (counter PC may auto-login or be headless). LaunchDaemon runs as root; ensure the
> `WorkingDirectory` and binary path are correct.

### Linux — systemd (user or system service)

**User service (recommended for desktop login):**

Create `~/.config/systemd/user/arcade-launcher.service`:

```ini
[Unit]
Description=Arcade Launcher
After=graphical-session.target network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart=/opt/arcade-launcher/ArcadeLauncher
WorkingDirectory=/opt/arcade-launcher
Restart=always
RestartSec=5
Environment=DISPLAY=:0
Environment=XAUTHORITY=%h/.Xauthority

[Install]
WantedBy=default.target
```

Enable and start:
```bash
systemctl --user daemon-reload
systemctl --user enable --now arcade-launcher.service
```

**System service (headless/server, runs before login):**

Create `/etc/systemd/system/arcade-launcher.service` (requires `sudo`):

```ini
[Unit]
Description=Arcade Launcher
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=arcade
Group=arcade
ExecStart=/opt/arcade-launcher/ArcadeLauncher
WorkingDirectory=/opt/arcade-launcher
Restart=always
RestartSec=5
# For GUI apps on headless, you may need a virtual display (Xvfb) or run under a real seat

[Install]
WantedBy=multi-user.target
```

Enable:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now arcade-launcher.service
```

---

## Firewall Configuration

The server listens on the configured port (default `8741`) for:
- REST API (`/api/*`)
- Dashboard WebSocket (`/ws/dashboard`)
- Agent WebSocket (`/ws/agent/{seat_id}`)

### macOS (Application Firewall)

```bash
# Allow the signed/unsigned binary explicitly
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --add "/Applications/Arcade Launcher.app/Contents/MacOS/ArcadeLauncher"
sudo /usr/libexec/ApplicationFirewall/socketfilterfw --unblockapp "/Applications/Arcade Launcher.app/Contents/MacOS/ArcadeLauncher"
```

Or via **System Settings → Network → Firewall → Options → +** → select the app → **Allow incoming connections**.

### Linux (ufw)

```bash
sudo ufw allow 8741/tcp comment "Arcade API/WS"
sudo ufw reload
```

### Linux (firewall-cmd / RHEL/Fedora)

```bash
sudo firewall-cmd --permanent --add-port=8741/tcp
sudo firewall-cmd --reload
```

### Windows (via Launcher or manually)

The Launcher's first-run wizard (Windows) prompts to allow through Windows Defender Firewall
(Private profile). Manually:
```powershell
New-NetFirewallRule -DisplayName "Arcade Server" -Direction Inbound -LocalPort 8741 -Protocol TCP -Action Allow -Profile Private
```

---

## Database & Backups

- **SQLite database:** `backend/arcade.db` (WAL mode: `arcade.db-wal`, `arcade.db-shm`).
- **Backup directory:** configured in `arcade.config.json` → `backup_dir` (default: `./backups/`).
- **Nightly backup:** runs at `config.backup_time` (default `03:00`) via APScheduler. Retains `config.backup_retain_days` (default 30).
- **Manual backup:** `POST /api/backup/run` (Admin).

Ensure the backup directory is on a separate disk / RAID for production.

---

## Hardware Requirements

| Role | Minimum | Recommended |
|------|---------|-------------|
| **Server (Counter PC)** | 2-core CPU, 4 GB RAM, 20 GB SSD, 2× Ethernet | 4-core, 8 GB RAM, 50 GB NVMe, 2× Gigabit Ethernet |
| **Client (Gaming PC)** | 2-core CPU, 4 GB RAM, 10 GB free, Ethernet | Per game specs; agent uses <50 MB RAM |
| **Network** | 100 Mbps switched LAN | 1 Gbps switched LAN (for WoL + low latency) |
| **Printer** | USB ESC/POS thermal | USB + network fallback |
| **Smart Plugs (optional)** | Tuya-compatible, LAN-local-key extractable | Same |

---

## License Key Management

- **Private key:** `tools/keygen/private_key.pem` — **NEVER commit, never ship**. Store offline (Hardware Security Module, encrypted USB, printed QR in safe).
- **Public key:** embedded in `backend/licensing/public_key.py` (64-char hex).
- **License file:** `license.key` (Base64 JSON + Ed25519 signature) — placed in app root by operator.
- **Hardware ID:** `py-machineid` primary; hostname+MAC fallback. Stable across reboots.
- **Custody policy:** define before issuing any license (audit log, rotation schedule, revocation procedure).

---

## Upgrading

1. Stop the server (Launcher → Stop Server).
2. Backup `arcade.db` and `arcade.config.json`.
3. Replace the binary / app bundle / package.
4. Run the Launcher — it will run `alembic upgrade head` on startup (via lifespan).
5. Start the server.

**Rollback:** Restore `arcade.db` and `arcade.config.json` from backup, reinstall previous binary.

---

## Troubleshooting Launcher

| Symptom | Cause | Fix |
|---------|-------|-----|
| `ModuleNotFoundError: tkinter` | Tkinter not installed | Install `python3-tk` / `python-tk` system package |
| `_tkinter.TclError: no display name` | No X11/Wayland display | Ensure `$DISPLAY` set; use `xvfb-run` for headless |
| `license.key` not found | File missing or wrong location | Place in same dir as Launcher binary / script |
| `arcade.config.json` permissions error | File readable by others | `chmod 600 arcade.config.json` |
| Server won't start, port in use | Another process on 8741 | `lsof -i :8741` / `netstat -ano \| findstr 8741` → kill |
| macOS "App is damaged" | Quarantine flag on unsigned app | `sudo xattr -dr com.apple.quarantine "/Applications/Arcade Launcher.app"` |
| Linux AppImage won't run | Missing FUSE / execute bit | `chmod +x *.AppImage`; install `libfuse2` |
| Auto-start not working (Linux) | systemd user instance not enabled | `systemctl --user enable linger $(whoami)` ; check `XAUTHORITY` |

---

## Cross-References

- `docs/agent-setup.md` — Agent installation, auto-start, kiosk hardening, troubleshooting
- `docs/api-reference.md` — All REST & WebSocket endpoints
- `docs/operator-guide.md` — Shift open/close, reservations, remote commands
- `docs/security/key-management.md` — Keygen process, private key custody, license lifecycle
- `docs/developer-guide.md` — Local dev setup, test commands, migration commands

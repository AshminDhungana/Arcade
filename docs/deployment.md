# Arcade Deployment Guide

> TODO: Document during Phase 11 (Deployment & Packaging) or when deploying to production.
>
> Key topics: PyInstaller packaging, Electron builder, installation on client machines, license activation workflow, hardware requirements.

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
   curl -X PATCH http://localhost:8000/api/settings \
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

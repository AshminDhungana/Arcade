# AC-14: Remote Commands (Restart/Shutdown) — Manual Verification Checklist

## Overview
Agent receives `RESTART` and `SHUTDOWN` commands over WebSocket from dashboard, executes via platform-specific implementations.

## Test Environment
- At least 2 machines: Server (counter PC) + 1 Client (gaming PC)
- Client machine must support restart/shutdown (not a container)

## Manual Test Steps

### 1. Agent Registration & Connection
- [ ] Start server on counter PC
- [ ] Start agent on client PC
- [ ] Verify WebSocket connection: agent shows "Connected" / dashboard shows seat ONLINE
- [ ] Verify agent secret matches between `arcade.config.json` and `agent.config.json`

### 2. Restart Command (POST /api/seats/{id}/restart)
- [ ] Start a session on the client seat
- [ ] From dashboard, click "Restart PC" for that seat
- [ ] **Verify**: Agent receives WebSocket message type `COMMAND` with payload `{ "command": "RESTART" }`
- [ ] **Verify**: Agent executes platform restart:
  - **Windows**: `shutdown /r /t 0 /f`
  - **macOS**: `sudo shutdown -r now` (requires passwordless sudo setup)
  - **Linux (systemd)**: `systemctl reboot` or `reboot`
- [ ] **Verify**: Client PC actually restarts
- [ ] **Verify**: Agent auto-starts on boot (if configured as service)
- [ ] **Verify**: Agent reconnects to server after reboot
- [ ] **Verify**: Seat status transitions: IN_USE → BOOTING → ONLINE (or UNREACHABLE → ONLINE)

### 3. Shutdown Command (POST /api/seats/{id}/shutdown)
- [ ] Start a session on the client seat
- [ ] From dashboard, click "Shutdown PC"
- [ ] **Verify**: Agent receives WebSocket message type `COMMAND` with payload `{ "command": "SHUTDOWN" }`
- [ ] **Verify**: Agent executes platform shutdown:
  - **Windows**: `shutdown /s /t 0 /f`
  - **macOS**: `sudo shutdown -h now`
  - **Linux**: `systemctl poweroff` or `poweroff`
- [ ] **Verify**: Client PC powers off completely
- [ ] **Verify**: Seat status → UNREACHABLE (after 60s WoL watchdog)
- [ ] **Verify**: Manual power-on + WoL from dashboard restores seat

### 4. Authorization & Safety
- [ ] **Admin only**: CASHIER role cannot trigger restart/shutdown (403)
- [ ] **Confirmation**: Dashboard shows confirmation dialog before sending
- [ ] **Active session**: Restart/shutdown allowed with active session (session ends, local cache SYNCs on reconnect)
- [ ] **No session**: Restart/shutdown works on idle seat

### 5. WoL Integration
- [ ] After shutdown, send WoL from dashboard "Wake PC"
- [ ] **Verify**: Magic packet sent to client MAC
- [ ] **Verify**: Seat status → BOOTING
- [ ] **Verify**: Agent registers within 60s → ONLINE

### 6. Network Resilience
- [ ] Disconnect client from LAN during session
- [ ] Send restart command from dashboard
- [ ] **Verify**: Command queued/delivered when agent reconnects (if supported)
- [ ] Reconnect LAN
- [ ] **Verify**: Agent receives command on reconnect

## Platform-Specific Notes

### Windows
- Agent must run with admin privileges for restart/shutdown
- Configure agent as Windows Service (auto-start on boot)
- Test with Fast Startup enabled/disabled

### macOS
- Requires passwordless sudo for `shutdown` command
- Configure via `/etc/sudoers.d/arcade-agent`:
  ```
  arcade-agent ALL=(ALL) NOPASSWD: /sbin/shutdown
  ```
- Agent LaunchAgent/LaunchDaemon for auto-start

### Linux
- systemd service for auto-start
- `systemctl reboot/poweroff` may require polkit rules or sudoers
- Test on systemd and non-systemd (if supported)

## Pass/Fail Criteria
- **PASS**: All ✅ checks pass on target platform
- **FAIL**: Any ✅ check fails
- **PARTIAL**: Works on some platforms but not others (document)

## Evidence
- Video of restart/shutdown flow from dashboard
- Screenshot of seat status transitions
- Agent logs showing COMMAND received and executed

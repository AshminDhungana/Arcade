# AC-07 Manual Test Procedure

**Goal:** Verify that no billing or session data is lost when the LAN connection between the server and a client agent drops for 30 seconds and recovers.

**Prerequisites:**
- Server running on a known IP (e.g., `192.168.1.100:8741`)
- Agent installed and configured on a Windows 10/11 PC on the same LAN subnet
- Dashboard accessible from a browser (staff PC or same agent PC)

**Table: Roles**
| Person | Role |
|--------|------|
| Tester | Performs actions, reads results |
| QA Observer | Watches the dashboard, records times |

---

## Step 1: Validate Pre-Test Environment

1. [ ] Ensure the server is running: `uvicorn backend.main:app --host 0.0.0.0 --port 8741`
2. [ ] Ensure the agent is connected: open the browser at `http://<server_ip>/dashboard`, verify the seat shows **ONLINE**
3. [ ] Verify the agent's agent.config.json has the correct `server_url` pointing to `http://<server_ip>:8741`

## Step 2: Start a Session

1. [ ] In the dashboard, click on the agent's seat (e.g., **Seat 1**)
2. [ ] Click **Start Session** (optional: select a member, or start a walk-in session)
3. [ ] Observe the agent's kiosk overlay **disappears** (HIDE_OVERLAY)
4. [ ] Note the start time on the dashboard -- record it as **T_start**

## Step 3: Disconnect the Network

1. [ ] **Tester:** Physically disconnect the LAN cable from the agent PC, OR disable the Wi-Fi on the agent PC, OR disable the network adapter in Windows
2. [ ] **QA Observer:** On the dashboard, verify the seat status changes from **ONLINE** to **UNREACHABLE** within 40 seconds (this is the heartbeat timeout + disconnect detection)
3. [ ] Wait **exactly 30 seconds** while the network is disconnected
4. [ ] Record the disconnect time as **T_disconnect**

## Step 4: Reconnect the Network

1. [ ] **Tester:** Reconnect the LAN cable, re-enable Wi-Fi, or re-enable the network adapter
2. [ ] **QA Observer:** On the dashboard, watch for the seat status to change back to **ONLINE** within 10 seconds (agent reconnects, REGISTER sent)
3. [ ] **QA Observer:** Watch for the seat card to update with the correct elapsed time (the timer should continue from where it left off, not reset)
4. [ ] Wait 5 more seconds for the SYNC exchange to complete

## Step 5: Verify SYNC was Sent and Processed

1. [ ] Check the server logs -- look for a line similar to:
   ```
   Reconcile action: ACCEPT_SAE (or ADOPT_ALE)
   Agent elapsed: X.Xs, Server elapsed: X.Xs, Drift: X.Xs
   ```
2. [ ] Check the agent logs -- look for:
   ```
   [WS] SYNC_ACK received for session: <session_id>
   ```
3. [ ] Run the verification script:
   ```bash
   cd backend
   python tests/manual/test_ac07_sync.py --base-url http://<server_ip>:8741
   ```
   Expected: Script reports `AC-07: PASS`

## Step 6: Verify Billing Accuracy (Pass Criteria)

1. [ ] Check the dashboard -- the elapsed time on the seat card should be approximately **T_disconnect + 30s** - the 30s of disconnect should be included
2. [ ] End the session via the dashboard
3. [ ] Verify the total billed time matches the expected elapsed
4. [ ] The difference between server-reported elapsed and agent-reported elapsed should be **<= 5 seconds** (the tolerance)

## Step 7: Regression Check (Crash Recovery)

Repeat Steps 2--6, but instead of reconnecting the network:
1. [ ] During the 30-second disconnect, physically power off the agent PC
2. [ ] Wait 10 seconds, then power on the agent PC
3. [ ] Verify the agent reconnects, the session is still active, and billing is accurate
4. [ ] Verify the agent's local SQLite database (`~/.arcade-agent/sessions.db`) still has the session with `is_synced = 0` before reconnect and `is_synced = 1` after

---

## Expected Results (Pass Criteria)

All of the following must be true for AC-07 to pass:

| # | Criterion | Status |
|---|-----------|--------|
| 1 | Agent sends SYNC message within 10 seconds of reconnect | PASS / FAIL |
| 2 | Server responds with SYNC_ACK within 2 seconds | PASS / FAIL |
| 3 | Elapsed time difference between server and agent is <= 5s | PASS / FAIL |
| 4 | Dashboard shows correct elapsed time after reconnect | PASS / FAIL |
| 5 | Session billing is accurate after the disconnect/reconnect cycle | PASS / FAIL |
| 6 | Agent crash + restart recovers session state from SQLite | PASS / FAIL |

---

## Troubleshooting

**Issue:** Agent does not reconnect after network is restored.
**Fix:** Check the agent's `agent.config.json` `server_url` is correct. Check Windows Firewall is not blocking the client. Check the server is actually reachable from the agent PC with Drospite + Ctrl+Alt+Del task).

**Issue:** SYNC message is not sent after reconnect.
**Fix:** Ensure a session was actually in the ACTIVE state before disconnect. The `sendSyncOnReconnect` only fires if `sessionState.session_id` is set. Also check agent logs for `sendSyncOn reconnect` trace.

**Issue:** Drift is larger than 5 seconds.
**Fix:** Verify the server and agent are using the same NTP source (or at least that their system clocks are synchronized). The test assumes clocks are within a few seconds of each other.

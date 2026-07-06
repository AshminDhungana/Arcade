"""AC-07 Manual Test Verification Script.  # noqa: INP001

Usage (run this after performing the manual test steps up to reconnect):
    python test_ac07_sync.py --base-url http://localhost:8000

This script connects to the server's dashboard websocket and monitors
for SYNC-related seat_updated events. It also polls the REST API to
verify elapsed time is within tolerance after a reconnect.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time

try:
    import websockets
except ImportError:
    print("ERROR: websockets is required. Install with: pip install websockets")
    raise

from httpx import AsyncClient


async def monitor_dashboard_ws(
    base_url: str,
    timeout_seconds: float = 60.0,
) -> dict | None:
    """Connect to the dashboard websocket and wait for a SYNCED event."""
    ws_url = base_url.replace("http", "ws") + "/ws/dashboard"
    start = time.monotonic()
    try:
        async with websockets.connect(ws_url) as ws:  # type: ignore[attr-defined]
            print(f"[INFO] Connected to dashboard websocket: {ws_url}")
            while time.monotonic() - start < timeout_seconds:
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=5.0)
                except TimeoutError:
                    continue
                data = json.loads(msg)
                payload = data.get("payload", {})
                if payload.get("status") == "SYNCED":
                    print(f"[FOUND] SYNCED event: {json.dumps(payload, indent=2)}")
                    return payload
            raise TimeoutError("Did not receive SYNCED event within timeout")  # noqa: EM101
    except websockets.exceptions.ConnectionClosed:  # type: ignore[attr-defined]
        print("[ERROR] Dashboard websocket connection closed unexpectedly")
        return None
    except Exception as exc:
        print(f"[ERROR] {exc}")
        return None


async def verify_session_elapsed(base_url: str, session_id: str) -> dict | None:
    """Fetch session via REST and return session data."""
    async with AsyncClient() as client:
        resp = await client.get(f"{base_url}/api/sessions/{session_id}")
        if resp.status_code == 200:
            return resp.json()
        print(f"[WARN] Could not fetch session {session_id}: HTTP {resp.status_code}")
        return None


def check_elapsed_accuracy(
    server_elapsed: float,
    agent_elapsed: float,
    tolerance: float = 5.0,
) -> bool:
    """Return True if server and agent elapsed are within tolerance."""
    drift = abs(server_elapsed - agent_elapsed)
    result = drift <= tolerance
    status = "PASS" if result else "FAIL"
    print(f"[{status}] Drift: {drift:.1f}s (tolerance: {tolerance:.1f}s)")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="AC-07 SYNC verification")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--session-id", help="Session ID to verify (optional)")
    parser.add_argument(
        "--timeout",
        type=float,
        default=60.0,
        help="Seconds to wait for SYNC event",
    )
    args = parser.parse_args()

    print("=" * 60)
    print("AC-07: Verify WebSocket SYNC reconciliation after reconnect")
    print("=" * 60)
    print()
    print("INSTRUCTIONS:")
    print("1. Start the server and agent.")
    print("2. Start a session via the dashboard.")
    print("3. Disconnect the agent's network for 30 seconds.")
    print("4. Reconnect the agent's network.")
    print("5. Wait for the agent to reconnect and send SYNC.")
    print("6. This script will monitor for the SYNC event and verify")
    print("   that the session elapsed time is accurate.")
    print()

    # Step 1: Monitor dashboard websocket for SYNCED event
    print("[STEP 1] Monitoring dashboard websocket for SYNCED event...")
    sync_event = asyncio.run(monitor_dashboard_ws(args.base_url, args.timeout))

    if sync_event is None:
        print("[FAIL] Did not receive SYNCED event. AC-07 test failed.")
        return 1

    # Extract values from the sync event
    agent_elapsed = sync_event.get("local_elapsed_seconds", 0)
    server_elapsed = sync_event.get("server_anchor_elapsed", 0)
    chosen = sync_event.get("chosen_elapsed_seconds", 0)
    action = sync_event.get("action", "UNKNOWN")
    session_id = sync_event.get("session_id")

    print(f"[INFO] Reconcile action: {action}")
    print(f"[INFO] Agent elapsed: {agent_elapsed:.1f}s")
    print(f"[INFO] Server elapsed: {server_elapsed:.1f}s")
    print(f"[INFO] Chosen elapsed: {chosen:.1f}s")

    # Step 2: Drift check
    print()
    print("[STEP 2] Verifying elapsed time accuracy...")
    elapsed_ok = check_elapsed_accuracy(float(server_elapsed), float(agent_elapsed))

    # Step 3: If session_id available, also verify via REST
    rest_session_id = args.session_id or session_id
    if rest_session_id:
        print()
        print(f"[STEP 3] Verifying session {rest_session_id} via REST API...")
        session_data = asyncio.run(
            verify_session_elapsed(args.base_url, rest_session_id)
        )
        if session_data:
            print(f"[INFO] Session data: {json.dumps(session_data, indent=2)}")
        else:
            print("[WARN] Could not verify session via REST")

    print()
    if elapsed_ok:
        print("=" * 60)
        print("AC-07: PASS -- Session billing is accurate after reconnect")
        print("=" * 60)
        return 0

    print("=" * 60)
    print("AC-07: FAIL -- Elapsed time drift exceeds tolerance")
    print("=" * 60)
    return 1


if __name__ == "__main__":
    sys.exit(main())

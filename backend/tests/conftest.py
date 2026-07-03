"""pytest configuration for Arcade backend tests."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Windows: force the selector event loop policy.
#
# aiosqlite runs each connection on a background thread and communicates
# with it via a queue driven by the event loop. On Windows, the default
# ProactorEventLoop can deadlock with this setup — the loop waits on a
# callback that never gets pumped through, causing async DB tests to hang
# indefinitely instead of erroring. This must run before any event loop
# is created, so it belongs here at collection time.
# ---------------------------------------------------------------------------
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# parents[2]: backend/tests -> backend -> repo root
_repo_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_repo_root))

# Ensure a minimal arcade.config.json exists before any test module that
# imports ``backend.main`` is collected (e.g. test_main.py triggers a
# cascading import that instantiates ``app.add_middleware`` at import
# time, which calls ``get_config()``).
_MINIMAL_TEST_CONFIG = {
    "jwt_secret": "a" * 64,
}

_config_path = _repo_root / "arcade.config.json"
if not _config_path.exists():
    _config_path.write_text(json.dumps(_MINIMAL_TEST_CONFIG))

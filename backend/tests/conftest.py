"""pytest configuration for Arcade backend tests."""

from __future__ import annotations

import json
import sys
from pathlib import Path

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

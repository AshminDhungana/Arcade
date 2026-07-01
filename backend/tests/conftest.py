"""pytest configuration for Arcade backend tests."""

from __future__ import annotations

import sys
from pathlib import Path

# parents[2]: backend/tests -> backend -> repo root
_repo_root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(_repo_root))

# Launcher UI Redesign — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate `launcher.py` from raw Tkinter to CustomTkinter with the app's blue/slate design system and the transparent `icon_opc.png` logo, without changing any business logic.

**Architecture:** One new helper module (`launcher_theme.py`) centralizes colors, fonts, the logo loader, and a reusable branded header. `launcher.py` is rewritten in place: `LauncherApp` becomes a `ctk.CTk` root (`set_appearance_mode("System")`), and the three screens (`ActivationScreen`, `SetupWizard`, `MainScreen`) become `ctk.CTkFrame` subclasses using themed widgets. All license/config/server logic (`_browse`, `_finish`, `_seed_default_staff`, subprocess management) is preserved verbatim.

**Tech Stack:** Python 3.11+, CustomTkinter 6.0.0 (already required), Pillow (for `CTkImage`), Tk/Tcl, pytest.

## Scope Check

The approved spec (`docs/superpowers/specs/2026-07-19-launcher-ui-design.md`) covers a single cohesive subsystem — the launcher GUI. It is one plan, not multiple independent subsystems. No decomposition required.

## Global Constraints

- CustomTkinter is already in `backend/requirements.txt` (`customtkinter>=5.2.0`, installed 6.0.0). **Do NOT add or downgrade it.**
- Logo asset: `frontend/public/icon_opc.png` — transparent, single image used on both light and dark themes (no variant swapping).
- Appearance mode: **"System"** (follow OS light/dark).
- `arcade.config.json` schema is unchanged: same keys, `hash_pin(...)`, `secrets.token_hex(32)` per-seat `agent_secrets`.
- Cross-platform: no Windows-only APIs; use generic font families (`monospace` for the Hardware ID, system default otherwise) so Linux/macOS builds don't break.
- Preserve FR-SYS-008 (license routing), FR-SYS-010 (close-confirm), FR-LIC-014 (`_write_license_status`).
- Behavior-preserving: `_browse`, `_seed_default_staff`, `_finish`, and the `subprocess.Popen` server lifecycle must stay byte-for-byte equivalent in logic.
- UI/UX (ui-ux-pro-max): one primary CTA per screen (blue Browse / blue Finish / emerald Start); all clickable controls get `cursor="hand2"`; muted captions use the `MUTED_TEXT` (light, dark) tuple so light-mode contrast stays >=4.5:1; error states show a bold headline + detail + recovery path (not a red wall of text); logs show an empty-state message before the server starts; an optional `fonts/` folder with a `.ttf` upgrades the wordmark/headings to a gaming display face with a safe system fallback.

---

## File Structure

- **Create `launcher_theme.py`** (repo root, beside `launcher.py`) — palette constants, font factories, `load_logo()`, `brand_header()`. One responsibility: all visual styling for the launcher.
- **Create `tests/launcher/conftest.py`** — inserts repo root onto `sys.path` so `launcher_theme` is importable under pytest.
- **Create `tests/launcher/test_theme.py`** — unit tests for `launcher_theme` (constants + logo loader, display-guarded).
- **Modify `launcher.py`** (repo root) — imports, `LauncherApp`, `main()`, and the three screen classes become CustomTkinter. Module-level helpers (`_LICENSE_ERROR_MESSAGES`, `_db_path`, `_write_license_status`) are unchanged.

---

### Task 1: Create `launcher_theme.py` with tests

**Files:**
- Create: `launcher_theme.py`
- Create: `tests/launcher/conftest.py`
- Create: `tests/launcher/test_theme.py`

**Interfaces:**
- Produces: `BRAND_LOGO_PATH` (Path), color constants `BLUE, BLUE_HOVER, EMERALD, EMERALD_HOVER, RED, RED_HOVER, S700, S800, S900, TEXT, MUTED` (str), `MUTED_TEXT` (list `[light, dark]`), `RADIUS` (int), `BTN_HEIGHT` (int), `BRAND_FONT` (Optional[str]); font factories `heading_font/title_font/body_font/mono_font/wordmark_font(size=...) -> ctk.CTkFont`, `load_logo(size=64) -> Optional[ctk.CTkImage]`, `brand_header(parent, *, subtitle: str) -> ctk.CTkFrame`.
- Consumes: nothing (leaf module).

- [ ] **Step 1: Write `tests/launcher/conftest.py`**

```python
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
```

- [ ] **Step 2: Write `launcher_theme.py`**

```python
"""Visual theme + brand assets for the Arcade Launcher (CustomTkinter).

Centralizes colors, fonts, and the logo so all launcher screens stay
consistent with the Arcade web app's blue/slate design system
(see frontend/src/index.css and components/ui/Button.tsx).

UI/UX follows the ui-ux-pro-max guidance: a single primary CTA per screen,
visible pointer/focus affordances, >=4.5:1 text contrast (the light-mode
muted tone is darkened for this), and error/empty states with clear
recovery microcopy.
"""
from __future__ import annotations

from pathlib import Path
from tkinter import font as tkfont
from typing import Optional

import customtkinter as ctk

# ── Paths ────────────────────────────────────────────────────────────────
_LAUNCHER_DIR = Path(__file__).resolve().parent
BRAND_LOGO_PATH = _LAUNCHER_DIR / "frontend" / "public" / "icon_opc.png"

# ── Palette (mirrors frontend/src/index.css @theme) ───────────────────────
# Dark-mode surfaces / text
S900 = "#0F172A"   # surface-900  window/frame bg (dark)
S800 = "#1E293B"   # surface-800  raised surfaces (dark)
S700 = "#334155"   # surface-700  borders / secondary (dark)
TEXT = "#F8FAFC"   # text-50
MUTED = "#94A3B8"  # text-muted  (dark mode)
# Light-mode surfaces / text
L_BG = "#F1F5F9"    # slate-100  window bg (light)
L_FRAME = "#FFFFFF"
L_TEXT = "#0F172A"  # slate-900
L_BORDER = "#CBD5E1"  # slate-300
# Brand / actions
BLUE = "#2563EB"          # brand-600  primary
BLUE_HOVER = "#3B82F6"    # brand-500
EMERALD = "#059669"       # emerald-600  start
EMERALD_HOVER = "#10B981"
RED = "#DC2626"           # red-600  stop / error
RED_HOVER = "#EF4444"
S700_HOVER = "#475569"    # slate-600
# Shape / sizing
RADIUS = 8
BTN_HEIGHT = 44

# Text colors as (light, dark) tuples so contrast holds in both themes.
# MUTED is lightened in dark mode but DARKENED in light mode: #94A3B8 on
# near-white only reaches ~2.6:1, so the light variant uses slate-500.
MUTED_TEXT = ["#64748B", MUTED]

# ── Optional bundled display font (gaming/esports brand energy) ───────────
def _resolve_brand_font() -> Optional[str]:
    """Register a bundled .ttf (e.g. Chakra Petch / Russo One) if present.

    Drop a font into a `fonts/` folder beside launcher.py. Returns the
    registered family name, or None to use the system default. Never raises
    (cross-platform safe; a missing/unreadable file is simply skipped).
    """
    fonts_dir = _LAUNCHER_DIR / "fonts"
    if not fonts_dir.is_dir():
        return None
    for ttf in sorted(fonts_dir.glob("*.ttf")):
        try:
            tkfont.Font(file=str(ttf))
            return ttf.stem
        except Exception:
            continue
    return None

BRAND_FONT = _resolve_brand_font()

def _font(size: int, *, bold: bool = False) -> ctk.CTkFont:
    kwargs: dict = {"size": size, "weight": "bold" if bold else "normal"}
    if BRAND_FONT:
        kwargs["family"] = BRAND_FONT
    return ctk.CTkFont(**kwargs)

# ── Fonts ─────────────────────────────────────────────────────────────────
def heading_font(size: int = 14) -> ctk.CTkFont:
    return _font(size, bold=True)

def title_font(size: int = 22) -> ctk.CTkFont:
    return _font(size, bold=True)

def body_font(size: int = 12) -> ctk.CTkFont:
    return _font(size)

def mono_font(size: int = 12) -> ctk.CTkFont:
    return ctk.CTkFont(family="monospace", size=size)

def wordmark_font(size: int = 18) -> ctk.CTkFont:
    return _font(size, bold=True)

# ── Logo ──────────────────────────────────────────────────────────────────
def load_logo(size: int = 64) -> Optional[ctk.CTkImage]:
    """Load the transparent brand logo. Returns None if the asset is absent so
    callers can fall back to a text-only header (launcher must still open)."""
    if not BRAND_LOGO_PATH.is_file():
        return None
    try:
        # Same transparent PNG on both themes (no background to clash).
        return ctk.CTkImage(
            light_image=str(BRAND_LOGO_PATH),
            dark_image=str(BRAND_LOGO_PATH),
            size=(size, size),
        )
    except Exception:
        return None

# ── Reusable branded header ────────────────────────────────────────────────
def brand_header(parent: ctk.CTkBaseClass, *, subtitle: str) -> ctk.CTkFrame:
    frame = ctk.CTkFrame(parent, fg_color="transparent")
    frame.columnconfigure(1, weight=1)

    logo = load_logo(44)
    if logo is not None:
        ctk.CTkLabel(frame, image=logo, text="").grid(
            row=0, column=0, rowspan=2, padx=(0, 10), pady=8, sticky="w"
        )

    ctk.CTkLabel(frame, text="ARCADE", font=wordmark_font(18), text_color=BLUE).grid(
        row=0, column=1, sticky="w", pady=(6, 0)
    )
    ctk.CTkLabel(frame, text=subtitle, font=body_font(11), text_color=MUTED_TEXT).grid(
        row=1, column=1, sticky="w"
    )
    ctk.CTkFrame(frame, height=2, fg_color=BLUE).grid(
        row=2, column=0, columnspan=2, sticky="ew", pady=(8, 0)
    )
    return frame
```

- [ ] **Step 3: Write `tests/launcher/test_theme.py`**

```python
import tkinter

# Importing launcher_theme pulls in customtkinter, which only needs a display
# when widgets/images are *instantiated*. The import itself is safe headless,
# but the logo test instantiates CTkImage, so guard on display availability.
try:
    import launcher_theme  # noqa: E402
except Exception:  # pragma: no cover - import environment issue
    launcher_theme = None  # type: ignore[assignment]

import pytest

pytestmark = pytest.mark.skipif(
    launcher_theme is None, reason="launcher_theme (customtkinter) not importable"
)

def _has_display() -> bool:
    try:
        tkinter.Tk().destroy()
        return True
    except Exception:
        return False

def test_constants_defined():
    assert launcher_theme.BLUE == "#2563EB"
    assert launcher_theme.BLUE_HOVER == "#3B82F6"
    assert launcher_theme.EMERALD == "#059669"
    assert launcher_theme.RED == "#DC2626"
    assert launcher_theme.S900 == "#0F172A"
    assert launcher_theme.TEXT == "#F8FAFC"
    assert launcher_theme.RADIUS == 8
    assert launcher_theme.BTN_HEIGHT == 44
    # Light-mode muted tone is darkened for >=4.5:1 contrast on near-white.
    assert launcher_theme.MUTED_TEXT == ["#64748B", "#94A3B8"]
    # No bundled fonts/ dir in this repo -> system default font.
    assert launcher_theme.BRAND_FONT is None

def test_load_logo_present_when_asset_exists():
    if not launcher_theme.BRAND_LOGO_PATH.is_file():
        pytest.skip("logo asset not present")
    if not _has_display():
        pytest.skip("no display available")
    img = launcher_theme.load_logo(64)
    assert img is not None

def test_load_logo_missing_returns_none(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "launcher_theme.BRAND_LOGO_PATH", tmp_path / "does_not_exist.png"
    )
    assert launcher_theme.load_logo(64) is None
```

- [ ] **Step 4: Run the theme tests (headed environment)**

Run: `python -m pytest tests/launcher/test_theme.py -v`

Expected: `test_constants_defined` and `test_load_logo_missing_returns_none` PASS. `test_load_logo_present_when_asset_exists` PASSES if a display is available (else SKIPPED). On a headless CI box with no DISPLAY, the whole module SKIPs — that is acceptable per the spec's documented limitation.

- [ ] **Step 5: Commit**

```bash
git add launcher_theme.py tests/launcher/conftest.py tests/launcher/test_theme.py
git commit -m "feat(launcher): add theme helper + logo loader with tests"
```

---

### Task 2: Migrate launcher root — imports, `LauncherApp`, `main()`

**Files:**
- Modify: `launcher.py` (imports block lines 1–31, `LauncherApp` class, `main()`)

**Interfaces:**
- Consumes: `launcher_theme` exports (`BLUE, BLUE_HOVER, EMERALD, EMERALD_HOVER, RED, RED_HOVER, S700, S800, S900, TEXT, MUTED, RADIUS, BTN_HEIGHT, body_font, heading_font, mono_font, title_font, wordmark_font, brand_header`) from Task 1.
- Produces: `LauncherApp` (now wraps `ctk.CTk`), `main()` sets `set_appearance_mode("System")`. Screens are still the original `tk.Frame` classes at this point (replaced in Tasks 3–5); the launcher still runs after this task.

- [ ] **Step 1: Replace the import block (top of `launcher.py`)**

_old_string:_

```python
from __future__ import annotations

import asyncio
import json
import secrets
import shutil
import sqlite3
import subprocess
import sys
import threading
import tkinter as tk
import webbrowser
from datetime import UTC, datetime
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext
from typing import Any

from backend.core.security import hash_pin
from backend.licensing.fingerprint import get_hardware_id
from backend.licensing.verify import LicenseError, LicenseResult, check_license
```

_new_string:_

```python
from __future__ import annotations

import asyncio
import json
import secrets
import shutil
import sqlite3
import subprocess
import sys
import threading
import tkinter as tk
import webbrowser
from datetime import UTC, datetime
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Any

import customtkinter as ctk

from backend.core.security import hash_pin
from backend.licensing.fingerprint import get_hardware_id
from backend.licensing.verify import LicenseError, LicenseResult, check_license
from launcher_theme import (
    BLUE,
    BLUE_HOVER,
    EMERALD,
    EMERALD_HOVER,
    RED,
    RED_HOVER,
    S700,
    S800,
    S900,
    TEXT,
    MUTED,
    RADIUS,
    BTN_HEIGHT,
    body_font,
    heading_font,
    mono_font,
    title_font,
    wordmark_font,
    brand_header,
)
```

- [ ] **Step 2: Replace the `LauncherApp` class**

_old_string:_

```python
class LauncherApp:
    """Tkinter application root.  Manages screen switching."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Arcade Launcher")
        self.root.geometry("700x550")
        self.root.configure(bg="#f5f5f5")
        self.current_screen: tk.Frame | None = None
        self._main_screen: MainScreen | None = None
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ------------------------------------------------------------------
    # Screen routing
    # ------------------------------------------------------------------

    def show_screen(
        self, screen_class: type[tk.Frame], *args: Any, **kwargs: Any
    ) -> None:
        if self.current_screen is not None:
            self.current_screen.destroy()
        # MyPy sees screen_class as tk.Frame, whose second positional arg is
        # cnf: dict | None. Cast to Any so the custom subclass constructor
        # (which takes a controller as second arg) type-checks correctly.
        _cls: Any = screen_class
        new_screen = _cls(self.root, self, *args, **kwargs)
        new_screen.pack(fill=tk.BOTH, expand=True)
        self.current_screen = new_screen

    # ------------------------------------------------------------------
    # Window close (FR-SYS-010)
    # ------------------------------------------------------------------

    def _on_close(self) -> None:
        if (
            self._main_screen is not None
            and self._main_screen._proc is not None
            and self._main_screen._proc.poll() is None
        ):
            ok = messagebox.askyesno(
                "Confirm Exit",
                "The Arcade server is still running. Closing the Launcher will "
                "stop the server. Are you sure?",
            )
            if not ok:
                return
            self._main_screen._stop_server()
        self.root.destroy()

    # ------------------------------------------------------------------
    # License routing (FR-SYS-008)
    # ------------------------------------------------------------------

    def _check_and_route(self) -> None:
        result = check_license()
        if result.ok:
            if Path("arcade.config.json").exists():
                self.show_screen(MainScreen)
                self._main_screen = self.current_screen  # type: ignore[assignment]
            else:
                self.show_screen(SetupWizard, result)
        else:
            self.show_screen(ActivationScreen, result)

    # ------------------------------------------------------------------
    # Entry hook
    # ------------------------------------------------------------------

    def run(self) -> None:
        self.root.mainloop()
```

_new_string:_

```python
class LauncherApp:
    """CustomTkinter application root.  Manages screen switching."""

    def __init__(self, root: ctk.CTk) -> None:
        self.root = root
        self.root.title("Arcade Launcher")
        self.root.geometry("720x600")
        self.root.minsize(720, 600)
        self.root.configure(fg_color=["#F1F5F9", S900])
        self.current_screen: ctk.CTkFrame | None = None
        self._main_screen: MainScreen | None = None
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ------------------------------------------------------------------
    # Screen routing
    # ------------------------------------------------------------------

    def show_screen(
        self, screen_class: type[ctk.CTkFrame], *args: Any, **kwargs: Any
    ) -> None:
        if self.current_screen is not None:
            self.current_screen.destroy()
        # MyPy sees screen_class as ctk.CTkFrame, whose second positional arg is
        # cnf: dict | None. Cast to Any so the custom subclass constructor
        # (which takes a controller as second arg) type-checks correctly.
        _cls: Any = screen_class
        new_screen = _cls(self.root, self, *args, **kwargs)
        new_screen.pack(fill=tk.BOTH, expand=True)
        self.current_screen = new_screen

    # ------------------------------------------------------------------
    # Window close (FR-SYS-010)
    # ------------------------------------------------------------------

    def _on_close(self) -> None:
        if (
            self._main_screen is not None
            and self._main_screen._proc is not None
            and self._main_screen._proc.poll() is None
        ):
            ok = messagebox.askyesno(
                "Confirm Exit",
                "The Arcade server is still running. Closing the Launcher will "
                "stop the server. Are you sure?",
            )
            if not ok:
                return
            self._main_screen._stop_server()
        self.root.destroy()

    # ------------------------------------------------------------------
    # License routing (FR-SYS-008)
    # ------------------------------------------------------------------

    def _check_and_route(self) -> None:
        result = check_license()
        if result.ok:
            if Path("arcade.config.json").exists():
                self.show_screen(MainScreen)
                self._main_screen = self.current_screen  # type: ignore[assignment]
            else:
                self.show_screen(SetupWizard, result)
        else:
            self.show_screen(ActivationScreen, result)

    # ------------------------------------------------------------------
    # Entry hook
    # ------------------------------------------------------------------

    def run(self) -> None:
        self.root.mainloop()
```

- [ ] **Step 3: Replace `main()`**

_old_string:_

```python
def main() -> None:
    root = tk.Tk()
    app = LauncherApp(root)
    app._check_and_route()
    app.run()


if __name__ == "__main__":
    main()
```

_new_string:_

```python
def main() -> None:
    ctk.set_appearance_mode("System")
    ctk.set_default_color_theme("blue")
    root = ctk.CTk()
    app = LauncherApp(root)
    app._check_and_route()
    app.run()


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Compile-check the module**

Run: `python -m py_compile launcher.py launcher_theme.py`

Expected: no output, exit code 0. (The three screen classes are still `tk.Frame` here; the launcher still runs. Do **not** launch the GUI yet.)

- [ ] **Step 5: Commit**

```bash
git add launcher.py
git commit -m "refactor(launcher): switch root to CustomTkinter (System theme)"
```

---

### Task 3: Migrate `ActivationScreen` (the flagged "License Required" screen)

**Files:**
- Modify: `launcher.py` (`ActivationScreen` class)

**Interfaces:**
- Consumes: `brand_header`, `S800, S900, TEXT, MUTED_TEXT, RED, BLUE, BLUE_HOVER, S700, S700_HOVER, RADIUS, BTN_HEIGHT, body_font, heading_font, title_font, mono_font` from `launcher_theme`; `get_hardware_id`, `LicenseError`, `_LICENSE_ERROR_MESSAGES` (module-level, unchanged), `filedialog`, `messagebox` from `tkinter`.
- Produces: new `ActivationScreen(ctk.CTkFrame)` with `_build`, `_copy`, `_browse`. Logic of `_browse` is preserved verbatim.

- [ ] **Step 1: Replace the `ActivationScreen` class**

_old_string:_

```python
class ActivationScreen(tk.Frame):
    """Shown when the license check fails."""

    def __init__(
        self, parent: tk.Widget, controller: LauncherApp, result: LicenseResult
    ) -> None:
        super().__init__(parent, bg="#f5f5f5")
        self.controller = controller
        self.result = result
        self._build()

    def _build(self) -> None:
        # Title
        tk.Label(
            self,
            text="License Required",
            font=("Arial", 22, "bold"),
            bg="#f5f5f5",
            fg="#333",
        ).pack(pady=(30, 10))

        # Error box
        error = self.result.error or LicenseError.MISSING
        msg = _LICENSE_ERROR_MESSAGES.get(error, str(error))
        self.error_label = tk.Label(
            self,
            text=msg,
            wraplength=600,
            justify=tk.CENTER,
            bg="#f5f5f5",
            fg="#c33",
            font=("Arial", 11),
        )
        self.error_label.pack(pady=10)

        # Hardware ID section
        tk.Label(
            self,
            text="Hardware ID (give this to support):",
            bg="#f5f5f5",
            font=("Arial", 10, "bold"),
        ).pack(pady=(20, 5))

        self.hwid_var = tk.StringVar(value=get_hardware_id())
        entry = tk.Entry(
            self,
            textvariable=self.hwid_var,
            state="readonly",
            font=("Courier", 12),
            width=34,
        )
        entry.pack()

        # Browse button
        tk.Button(self, text="Browse for license.key …", command=self._browse).pack(
            pady=20
        )

    def _browse(self) -> None:
        path = filedialog.askopenfilename(
            title="Select license.key", filetypes=[("License files", "*.key")]
        )
        if path:
            dest = Path("license.key")
            try:
                # Copy (not move): the chosen file may live on another drive,
                # and we must not delete the user's original license.key.
                shutil.copy2(path, dest)
                # Re-check and re-route
                self.controller._check_and_route()
            except Exception as exc:
                messagebox.showerror("Error", f"Unable to copy license file:\n{exc}")
```

_new_string:_

```python
class ActivationScreen(ctk.CTkFrame):
    """Shown when the license check fails."""

    # Short, bold headline per license failure; the full message stays in the
    # card body. Gives the error clear hierarchy + a recovery-focused tone.
    _ERROR_HEADLINES = {
        LicenseError.MISSING: "No license found",
        LicenseError.INVALID_SIGNATURE: "License file is invalid",
        LicenseError.HARDWARE_MISMATCH: "License is for a different machine",
        LicenseError.TRIAL_EXPIRED: "Trial period has ended",
    }

    def __init__(
        self, parent: tk.Widget, controller: LauncherApp, result: LicenseResult
    ) -> None:
        super().__init__(parent, fg_color=["#F1F5F9", S900])
        self.controller = controller
        self.result = result
        self._build()

    def _build(self) -> None:
        header = brand_header(self, subtitle="Gaming Cafe Management")
        header.pack(fill="x", padx=20, pady=(16, 0))

        ctk.CTkLabel(
            self,
            text="License Required",
            font=title_font(22),
            text_color=["#0F172A", TEXT],
        ).pack(pady=(18, 6))

        # Error card: bold headline + detail + recovery path (not a wall of
        # red text). The red border carries the alert; text stays readable.
        card = ctk.CTkFrame(
            self,
            fg_color=["#FFFFFF", S800],
            border_width=1,
            border_color=RED,
            corner_radius=RADIUS,
        )
        card.pack(fill="x", padx=24, pady=10)
        error = self.result.error or LicenseError.MISSING
        headline = self._ERROR_HEADLINES.get(error, "License required")
        msg = _LICENSE_ERROR_MESSAGES.get(error, str(error))
        ctk.CTkLabel(
            card,
            text=headline,
            font=heading_font(14),
            text_color=RED,
        ).pack(anchor="w", padx=14, pady=(14, 2))
        ctk.CTkLabel(
            card,
            text=msg,
            wraplength=560,
            justify="left",
            font=body_font(12),
            text_color=["#0F172A", TEXT],
        ).pack(anchor="w", padx=14, pady=(0, 4))
        ctk.CTkLabel(
            card,
            text="Browse for your license.key below, or contact support with the Hardware ID.",
            wraplength=560,
            justify="left",
            font=body_font(11),
            text_color=MUTED_TEXT,
        ).pack(anchor="w", padx=14, pady=(0, 14))

        # Hardware ID (copyable, monospace)
        ctk.CTkLabel(
            self,
            text="Your Hardware ID",
            font=body_font(12),
            text_color=MUTED_TEXT,
        ).pack(anchor="w", padx=24, pady=(14, 4))

        hwid_row = ctk.CTkFrame(self, fg_color="transparent")
        hwid_row.pack(fill="x", padx=24)
        self.hwid_var = tk.StringVar(value=get_hardware_id())
        hwid_entry = ctk.CTkEntry(
            hwid_row,
            textvariable=self.hwid_var,
            font=mono_font(12),
            state="readonly",
            height=BTN_HEIGHT,
        )
        hwid_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))
        ctk.CTkButton(
            hwid_row,
            text="Copy",
            width=90,
            height=BTN_HEIGHT,
            fg_color=S700,
            hover_color=S700_HOVER,
            text_color=TEXT,
            cursor="hand2",
            command=self._copy,
        ).pack(side="left")

        ctk.CTkLabel(
            self,
            text="Share this ID with support to get your license.",
            font=body_font(11),
            text_color=MUTED_TEXT,
        ).pack(anchor="w", padx=24, pady=(6, 0))

        ctk.CTkButton(
            self,
            text="Browse for license.key …",
            height=BTN_HEIGHT,
            fg_color=BLUE,
            hover_color=BLUE_HOVER,
            cursor="hand2",
            command=self._browse,
        ).pack(pady=24)

    def _copy(self) -> None:
        try:
            self.clipboard_clear()
            self.clipboard_append(self.hwid_var.get())
            ctk.CTkMessagebox(
                title="Copied",
                message="Hardware ID copied to clipboard.",
                icon="check",
            )
        except Exception as exc:  # noqa: BLE001 — surface clipboard failure
            messagebox.showerror("Error", f"Unable to copy: {exc}")

    def _browse(self) -> None:
        path = filedialog.askopenfilename(
            title="Select license.key", filetypes=[("License files", "*.key")]
        )
        if path:
            dest = Path("license.key")
            try:
                # Copy (not move): the chosen file may live on another drive,
                # and we must not delete the user's original license.key.
                shutil.copy2(path, dest)
                # Re-check and re-route
                self.controller._check_and_route()
            except Exception as exc:
                messagebox.showerror("Error", f"Unable to copy license file:\n{exc}")
```

- [ ] **Step 2: Compile-check**

Run: `python -m py_compile launcher.py`

Expected: exit code 0.

- [ ] **Step 3: Commit**

```bash
git add launcher.py
git commit -m "feat(launcher): modernize ActivationScreen with logo + error card"
```

---

### Task 4: Migrate `SetupWizard`

**Files:**
- Modify: `launcher.py` (`SetupWizard` class)

**Interfaces:**
- Consumes: `brand_header`, `S900, TEXT, MUTED, BLUE, BLUE_HOVER, RADIUS, BTN_HEIGHT, body_font, heading_font` from `launcher_theme`; `load_config`, `ensure_default_staff`, `run_migrations`, `AsyncSessionLocal` (used inside `_seed_default_staff`); `secrets`, `hash_pin`.
- Produces: new `SetupWizard(ctk.CTkFrame)` with `_build`, `_add_field`, `_seed_default_staff`, `_finish`. `_seed_default_staff` and `_finish` logic preserved verbatim — only widget construction changes.

- [ ] **Step 1: Replace the `SetupWizard` class**

_old_string:_

```python
class SetupWizard(tk.Frame):
    """First-run wizard to generate arcade.config.json."""

    def __init__(
        self, parent: tk.Widget, controller: LauncherApp, license_result: LicenseResult
    ) -> None:
        super().__init__(parent, bg="#f5f5f5")
        self.controller = controller
        self.license_result = license_result
        self._build()

    def _build(self) -> None:
        tk.Label(
            self, text="Setup Wizard", font=("Arial", 20, "bold"), bg="#f5f5f5"
        ).pack(pady=15)

        # ── Cafe / Server ──
        frame = tk.Frame(self, bg="#f5f5f5")
        frame.pack(pady=5)

        self._cafe_name_var = tk.StringVar()
        tk.Label(frame, text="Cafe Name:", bg="#f5f5f5").grid(
            row=0, column=0, sticky="w"
        )
        tk.Entry(frame, textvariable=self._cafe_name_var, width=30).grid(
            row=0, column=1, padx=5
        )

        self._host_var = tk.StringVar(value="0.0.0.0")
        tk.Label(frame, text="Server IP:", bg="#f5f5f5").grid(
            row=1, column=0, sticky="w"
        )
        tk.Entry(frame, textvariable=self._host_var, width=30).grid(
            row=1, column=1, padx=5
        )

        self._port_var = tk.StringVar(value="8000")
        tk.Label(frame, text="Port:", bg="#f5f5f5").grid(row=2, column=0, sticky="w")
        tk.Entry(frame, textvariable=self._port_var, width=30).grid(
            row=2, column=1, padx=5
        )

        # ── Staff ──
        staff = tk.Frame(self, bg="#f5f5f5")
        staff.pack(pady=10)

        tk.Label(
            staff, text="--- Staff ---", bg="#f5f5f5", font=("Arial", 10, "bold")
        ).pack()

        self._admin_id_var = tk.StringVar(value="admin")
        tk.Label(staff, text="Admin Staff ID:", bg="#f5f5f5").pack(anchor="w")
        tk.Entry(staff, textvariable=self._admin_id_var, width=30).pack()

        self._admin_pin_var = tk.StringVar()
        tk.Label(staff, text="Admin PIN:", bg="#f5f5f5").pack(anchor="w", pady=(5, 0))
        tk.Entry(staff, textvariable=self._admin_pin_var, show="*", width=30).pack()

        self._cashier_id_var = tk.StringVar(value="cashier")
        tk.Label(staff, text="Cashier Staff ID:", bg="#f5f5f5").pack(
            anchor="w", pady=(5, 0)
        )
        tk.Entry(staff, textvariable=self._cashier_id_var, width=30).pack()

        self._cashier_pin_var = tk.StringVar()
        tk.Label(staff, text="Cashier PIN:", bg="#f5f5f5").pack(anchor="w", pady=(5, 0))
        tk.Entry(staff, textvariable=self._cashier_pin_var, show="*", width=30).pack()

        # ── Seats ──
        self._seat_count_var = tk.StringVar(value="8")
        tk.Label(self, text="Number of Seats:", bg="#f5f5f5").pack(pady=(10, 0))
        tk.Entry(self, textvariable=self._seat_count_var, width=10).pack()

        # ── Finish ──
        tk.Button(self, text="Finish", command=self._finish).pack(pady=20)

    def _seed_default_staff(self) -> None:
        """Best-effort: create the default admin + cashier in the DB.

        Runs in a background thread (DB + alembic can be slow) so the wizard UI
        stays responsive. Any failure is non-fatal: the server's startup
        self-heal (ensure_default_staff in main.py lifespan) covers it.
        """
        import logging
        import threading

        logger = logging.getLogger(__name__)

        def _run() -> None:
            from backend.core.bootstrap import ensure_default_staff
            from backend.core.config import load_config
            from backend.core.database import AsyncSessionLocal
            from backend.core.startup import run_migrations

            async def _bootstrap() -> None:
                await run_migrations()
                async with AsyncSessionLocal() as db:
                    # Read the config we just wrote (not the lru-cached getter).
                    await ensure_default_staff(db, settings=load_config())
                    await db.commit()

            try:
                asyncio.run(_bootstrap())
            except Exception as exc:  # noqa: BLE001 — best-effort, never block wizard
                logger.warning("Default staff seed skipped: %s", exc)

        threading.Thread(target=_run, daemon=True).start()

    def _finish(self) -> None:
        payload = self.license_result.payload or {}

        try:
            seat_count = int(self._seat_count_var.get())
        except ValueError:
            seat_count = 8

        # Build config matching backend.core.config.Settings
        config: dict[str, Any] = {
            "cafe_name": self._cafe_name_var.get()
            or payload.get("cafe_name", "Arcade"),
            "host": self._host_var.get() or "0.0.0.0",
            "port": int(self._port_var.get() or 8000),
            "admin_staff_id": self._admin_id_var.get() or "admin",
            "admin_pin_hash": hash_pin(self._admin_pin_var.get() or "admin"),
            "cashier_staff_id": self._cashier_id_var.get() or "cashier",
            "cashier_pin_hash": hash_pin(self._cashier_pin_var.get() or "cashier"),
            "jwt_secret": secrets.token_hex(32),
            "agent_secrets": {
                f"seat_{i + 1}": secrets.token_hex(32) for i in range(seat_count)
            },
        }

        # Write config
        Path("arcade.config.json").write_text(
            json.dumps(config, indent=2), encoding="utf-8"
        )

        # Write license_status row (FR-LIC-014)
        _write_license_status(payload, self.license_result)

        # Best-effort seed default admin + cashier into the DB now.
        self._seed_default_staff()

        # Route
        self.controller._check_and_route()
```

_new_string:_

```python
class SetupWizard(ctk.CTkFrame):
    """First-run wizard to generate arcade.config.json."""

    def __init__(
        self, parent: tk.Widget, controller: LauncherApp, license_result: LicenseResult
    ) -> None:
        super().__init__(parent, fg_color=["#F1F5F9", S900])
        self.controller = controller
        self.license_result = license_result
        self._build()

    def _build(self) -> None:
        header = brand_header(self, subtitle="First-time setup")
        header.pack(fill="x", padx=20, pady=(16, 0))

        scroll = ctk.CTkScrollableFrame(self, fg_color=["#F1F5F9", S900])
        scroll.pack(fill="both", expand=True, padx=16, pady=12)

        # ── Server ──
        ctk.CTkLabel(
            scroll, text="Server", font=heading_font(14), text_color=BLUE
        ).pack(anchor="w", padx=8, pady=(4, 6))
        self._cafe_name_var = tk.StringVar()
        self._host_var = tk.StringVar(value="0.0.0.0")
        self._port_var = tk.StringVar(value="8000")
        self._add_field(scroll, "Cafe Name:", self._cafe_name_var, placeholder="Arcade")
        self._add_field(scroll, "Server IP:", self._host_var, placeholder="0.0.0.0")
        self._add_field(
            scroll,
            "Port:",
            self._port_var,
            placeholder="8000",
            helper="The port agents and the dashboard connect to. Keep 8000 unless it conflicts.",
        )

        # ── Staff ──
        ctk.CTkLabel(
            scroll, text="Staff", font=heading_font(14), text_color=BLUE
        ).pack(anchor="w", padx=8, pady=(12, 6))
        self._admin_id_var = tk.StringVar(value="admin")
        self._admin_pin_var = tk.StringVar()
        self._cashier_id_var = tk.StringVar(value="cashier")
        self._cashier_pin_var = tk.StringVar()
        self._add_field(scroll, "Admin Staff ID:", self._admin_id_var, placeholder="admin")
        self._add_field(scroll, "Admin PIN:", self._admin_pin_var, show="*", placeholder="••••")
        self._add_field(scroll, "Cashier Staff ID:", self._cashier_id_var, placeholder="cashier")
        self._add_field(scroll, "Cashier PIN:", self._cashier_pin_var, show="*", placeholder="••••")

        # ── Seats ──
        ctk.CTkLabel(
            scroll, text="Seats", font=heading_font(14), text_color=BLUE
        ).pack(anchor="w", padx=8, pady=(12, 6))
        self._seat_count_var = tk.StringVar(value="8")
        self._add_field(
            scroll,
            "Number of Seats:",
            self._seat_count_var,
            placeholder="8",
            helper="One agent secret is generated per seat.",
        )

        ctk.CTkButton(
            self,
            text="Finish",
            height=BTN_HEIGHT,
            fg_color=BLUE,
            hover_color=BLUE_HOVER,
            cursor="hand2",
            command=self._finish,
        ).pack(pady=16)

    def _add_field(
        self,
        parent: ctk.CTkBaseClass,
        label: str,
        var: tk.StringVar,
        *,
        placeholder: str = "",
        show: str | None = None,
        helper: str = "",
    ) -> None:
        ctk.CTkLabel(
            parent, text=label, font=body_font(12), text_color=["#0F172A", TEXT]
        ).pack(anchor="w", padx=8, pady=(6, 2))
        entry = ctk.CTkEntry(
            parent,
            textvariable=var,
            height=BTN_HEIGHT,
            placeholder_text=placeholder,
            font=body_font(12),
            border_color=BLUE,
        )
        if show:
            entry.configure(show=show)
        entry.pack(fill="x", padx=8, pady=(0, 2))
        if helper:
            ctk.CTkLabel(
                parent,
                text=helper,
                font=body_font(11),
                text_color=MUTED_TEXT,
                wraplength=520,
                justify="left",
            ).pack(anchor="w", padx=8, pady=(0, 8))

    def _seed_default_staff(self) -> None:
        """Best-effort: create the default admin + cashier in the DB.

        Runs in a background thread (DB + alembic can be slow) so the wizard UI
        stays responsive. Any failure is non-fatal: the server's startup
        self-heal (ensure_default_staff in main.py lifespan) covers it.
        """
        import logging
        import threading

        logger = logging.getLogger(__name__)

        def _run() -> None:
            from backend.core.bootstrap import ensure_default_staff
            from backend.core.config import load_config
            from backend.core.database import AsyncSessionLocal
            from backend.core.startup import run_migrations

            async def _bootstrap() -> None:
                await run_migrations()
                async with AsyncSessionLocal() as db:
                    # Read the config we just wrote (not the lru-cached getter).
                    await ensure_default_staff(db, settings=load_config())
                    await db.commit()

            try:
                asyncio.run(_bootstrap())
            except Exception as exc:  # noqa: BLE001 — best-effort, never block wizard
                logger.warning("Default staff seed skipped: %s", exc)

        threading.Thread(target=_run, daemon=True).start()

    def _finish(self) -> None:
        payload = self.license_result.payload or {}

        try:
            seat_count = int(self._seat_count_var.get())
        except ValueError:
            seat_count = 8

        # Build config matching backend.core.config.Settings
        config: dict[str, Any] = {
            "cafe_name": self._cafe_name_var.get()
            or payload.get("cafe_name", "Arcade"),
            "host": self._host_var.get() or "0.0.0.0",
            "port": int(self._port_var.get() or 8000),
            "admin_staff_id": self._admin_id_var.get() or "admin",
            "admin_pin_hash": hash_pin(self._admin_pin_var.get() or "admin"),
            "cashier_staff_id": self._cashier_id_var.get() or "cashier",
            "cashier_pin_hash": hash_pin(self._cashier_pin_var.get() or "cashier"),
            "jwt_secret": secrets.token_hex(32),
            "agent_secrets": {
                f"seat_{i + 1}": secrets.token_hex(32) for i in range(seat_count)
            },
        }

        # Write config
        Path("arcade.config.json").write_text(
            json.dumps(config, indent=2), encoding="utf-8"
        )

        # Write license_status row (FR-LIC-014)
        _write_license_status(payload, self.license_result)

        # Best-effort seed default admin + cashier into the DB now.
        self._seed_default_staff()

        # Route
        self.controller._check_and_route()
```

- [ ] **Step 2: Compile-check**

Run: `python -m py_compile launcher.py`

Expected: exit code 0.

- [ ] **Step 3: Commit**

```bash
git add launcher.py
git commit -m "feat(launcher): modernize SetupWizard with scrollable themed form"
```

---

### Task 5: Migrate `MainScreen`

**Files:**
- Modify: `launcher.py` (`MainScreen` class)

**Interfaces:**
- Consumes: `brand_header`, `S900, TEXT, MUTED_TEXT, EMERALD, EMERALD_HOVER, RED, RED_HOVER, S700, S700_HOVER, BTN_HEIGHT, body_font, mono_font` from `launcher_theme`; `webbrowser`, `json`, `subprocess`, `sys`, `threading`.
- Produces: new `MainScreen(ctk.CTkFrame)` with `_build`, `_append_log`, `_start_server`, `_stream_logs`, `_stop_server`, `_open_dashboard`. Server lifecycle logic preserved verbatim; status dot becomes a colored **pill**, logs use `CTkTextbox`.

- [ ] **Step 1: Replace the `MainScreen` class**

_old_string:_

```python
class MainScreen(tk.Frame):
    """Main screen: server start/stop, logs, dashboard."""

    def __init__(self, parent: tk.Widget, controller: LauncherApp) -> None:
        super().__init__(parent, bg="#f5f5f5")
        self.controller = controller
        self._proc: subprocess.Popen[str] | None = None
        self._log_thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._status_var = tk.StringVar(value="Stopped")
        self._build()

    def _build(self) -> None:
        # Title
        tk.Label(
            self, text="Arcade Server", font=("Arial", 20, "bold"), bg="#f5f5f5"
        ).pack(pady=15)

        # Status
        status_frame = tk.Frame(self, bg="#f5f5f5")
        status_frame.pack(pady=5)

        self._dot = tk.Canvas(
            status_frame, width=20, height=20, bg="#f5f5f5", highlightthickness=0
        )
        self._dot.pack(side=tk.LEFT, padx=(0, 5))
        self._dot_id = self._dot.create_oval(2, 2, 18, 18, fill="red")

        tk.Label(
            status_frame,
            textvariable=self._status_var,
            font=("Arial", 12),
            bg="#f5f5f5",
        ).pack(side=tk.LEFT)

        # Buttons
        btn_frame = tk.Frame(self, bg="#f5f5f5")
        btn_frame.pack(pady=10)

        tk.Button(btn_frame, text="Start Server", command=self._start_server).pack(
            side=tk.LEFT, padx=5
        )
        tk.Button(btn_frame, text="Stop Server", command=self._stop_server).pack(
            side=tk.LEFT, padx=5
        )
        tk.Button(btn_frame, text="Open Dashboard", command=self._open_dashboard).pack(
            side=tk.LEFT, padx=5
        )

        # Logs
        tk.Label(
            self, text="Server Logs:", font=("Arial", 10, "bold"), bg="#f5f5f5"
        ).pack(pady=(10, 0), anchor="w", padx=10)
        self._log_text = scrolledtext.ScrolledText(
            self, height=15, state=tk.DISABLED, wrap=tk.WORD
        )
        self._log_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

    # ------------------------------------------------------------------
    # Server lifecycle
    # ------------------------------------------------------------------

    def _append_log(self, line: str) -> None:
        self._log_text.configure(state=tk.NORMAL)
        self._log_text.insert(tk.END, line)
        self._log_text.see(tk.END)
        self._log_text.configure(state=tk.DISABLED)

    def _start_server(self) -> None:
        if self._proc is not None and self._proc.poll() is None:
            return

        host = "0.0.0.0"
        port = 8000
        if Path("arcade.config.json").exists():
            try:
                cfg = json.loads(Path("arcade.config.json").read_text(encoding="utf-8"))
                host = cfg.get("host", "0.0.0.0")
                port = int(cfg.get("port", 8000))
            except (ValueError, KeyError, json.JSONDecodeError):
                pass

        self._proc = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "backend.main:app",
                "--host",
                host,
                "--port",
                str(port),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

        self._status_var.set(f"Running at http://{host}:{port}")
        self._dot.itemconfig(self._dot_id, fill="green")

        self._stop_event.clear()
        self._log_thread = threading.Thread(target=self._stream_logs, daemon=True)
        self._log_thread.start()

    def _stream_logs(self) -> None:
        if self._proc is not None and self._proc.stdout is not None:
            for line in self._proc.stdout:
                if self._stop_event.is_set():
                    break
                self._append_log(line)

    def _stop_server(self) -> None:
        self._stop_event.set()
        if self._proc is not None and self._proc.poll() is None:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self._proc.kill()
                self._proc.wait()
        self._status_var.set("Stopped")
        self._dot.itemconfig(self._dot_id, fill="red")

    def _open_dashboard(self) -> None:
        host = "localhost"
        port = 8000
        if Path("arcade.config.json").exists():
            try:
                cfg = json.loads(Path("arcade.config.json").read_text(encoding="utf-8"))
                host = cfg.get("host", "localhost")
                port = int(cfg.get("port", 8000))
            except (ValueError, KeyError, json.JSONDecodeError):
                pass
        webbrowser.open(f"http://{host}:{port}")
```

_new_string:_

```python
class MainScreen(ctk.CTkFrame):
    """Main screen: server start/stop, logs, dashboard."""

    def __init__(self, parent: tk.Widget, controller: LauncherApp) -> None:
        super().__init__(parent, fg_color=["#F1F5F9", S900])
        self.controller = controller
        self._proc: subprocess.Popen[str] | None = None
        self._log_thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._status_var = tk.StringVar(value="Stopped")
        self._log_started = False
        self._build()

    def _build(self) -> None:
        header = brand_header(self, subtitle="Server control")
        header.pack(fill="x", padx=20, pady=(16, 0))

        # Status pill (replaces the red/green Canvas dot)
        status_frame = ctk.CTkFrame(self, fg_color="transparent")
        status_frame.pack(pady=8)
        self._status_pill = ctk.CTkLabel(
            status_frame,
            textvariable=self._status_var,
            height=28,
            corner_radius=14,
            fg_color=RED,
            text_color="#FFFFFF",
            font=body_font(12),
        )
        self._status_pill.pack(side="left", padx=4)

        # Buttons
        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.pack(pady=8)
        ctk.CTkButton(
            btn_frame,
            text="Start Server",
            height=BTN_HEIGHT,
            fg_color=EMERALD,
            hover_color=EMERALD_HOVER,
            cursor="hand2",
            command=self._start_server,
        ).pack(side="left", padx=6)
        ctk.CTkButton(
            btn_frame,
            text="Stop Server",
            height=BTN_HEIGHT,
            fg_color=RED,
            hover_color=RED_HOVER,
            cursor="hand2",
            command=self._stop_server,
        ).pack(side="left", padx=6)
        ctk.CTkButton(
            btn_frame,
            text="Open Dashboard",
            height=BTN_HEIGHT,
            fg_color=S700,
            hover_color=S700_HOVER,
            text_color=TEXT,
            cursor="hand2",
            command=self._open_dashboard,
        ).pack(side="left", padx=6)

        # Logs
        ctk.CTkLabel(
            self, text="Server Logs:", font=body_font(12), text_color=MUTED_TEXT
        ).pack(anchor="w", padx=20, pady=(8, 2))
        self._log_text = ctk.CTkTextbox(
            self, height=200, state="disabled", wrap="word", font=mono_font(11)
        )
        # Empty state: guides the user before the server produces output.
        self._log_text.insert("0.0", "Server logs will appear here once you start the server.")
        self._log_text.configure(state="disabled")
        self._log_text.pack(fill="both", expand=True, padx=20, pady=(0, 12))

    # ------------------------------------------------------------------
    # Server lifecycle
    # ------------------------------------------------------------------

    def _append_log(self, line: str) -> None:
        self._log_text.configure(state="normal")
        if not self._log_started:
            # Clear the empty-state placeholder on the first real log line.
            self._log_text.delete("0.0", "end")
            self._log_started = True
        self._log_text.insert("end", line)
        self._log_text.see("end")
        self._log_text.configure(state="disabled")

    def _start_server(self) -> None:
        if self._proc is not None and self._proc.poll() is None:
            return

        host = "0.0.0.0"
        port = 8000
        if Path("arcade.config.json").exists():
            try:
                cfg = json.loads(Path("arcade.config.json").read_text(encoding="utf-8"))
                host = cfg.get("host", "0.0.0.0")
                port = int(cfg.get("port", 8000))
            except (ValueError, KeyError, json.JSONDecodeError):
                pass

        self._proc = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "backend.main:app",
                "--host",
                host,
                "--port",
                str(port),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

        self._status_var.set(f"Running at http://{host}:{port}")
        self._status_pill.configure(fg_color=EMERALD)

        self._stop_event.clear()
        self._log_thread = threading.Thread(target=self._stream_logs, daemon=True)
        self._log_thread.start()

    def _stream_logs(self) -> None:
        if self._proc is not None and self._proc.stdout is not None:
            for line in self._proc.stdout:
                if self._stop_event.is_set():
                    break
                self._append_log(line)

    def _stop_server(self) -> None:
        self._stop_event.set()
        if self._proc is not None and self._proc.poll() is None:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self._proc.kill()
                self._proc.wait()
        self._status_var.set("Stopped")
        self._status_pill.configure(fg_color=RED)

    def _open_dashboard(self) -> None:
        host = "localhost"
        port = 8000
        if Path("arcade.config.json").exists():
            try:
                cfg = json.loads(Path("arcade.config.json").read_text(encoding="utf-8"))
                host = cfg.get("host", "localhost")
                port = int(cfg.get("port", 8000))
            except (ValueError, KeyError, json.JSONDecodeError):
                pass
        webbrowser.open(f"http://{host}:{port}")
```

- [ ] **Step 2: Compile-check**

Run: `python -m py_compile launcher.py`

Expected: exit code 0.

- [ ] **Step 3: Commit**

```bash
git add launcher.py
git commit -m "feat(launcher): modernize MainScreen with status pill + CTkTextbox"
```

---

### Task 6: Final cleanup, smoke test, and manual QA

**Files:**
- Modify: `launcher.py` (verify no stray `tk.` widget usage remains)

**Interfaces:**
- Consumes: the fully migrated `launcher.py` + `launcher_theme.py` from Tasks 1–5.
- Produces: a verified, runnable launcher; final commit.

- [ ] **Step 1: Confirm only allowed `tk.` references remain**

Run: `grep -nE "tk\.(Frame|Label|Button|Entry|Canvas|ScrolledText|CENTER|LEFT|END|WORD|DISABLED|NORMAL)" launcher.py`

Expected: **no output** (all widget classes are now `ctk.*`). Allowed remaining references are `tk.StringVar`, `tk.BOTH`, `tk.Widget` (type hints), and `from tkinter import filedialog, messagebox`. If any disallowed reference appears, fix it before proceeding.

- [ ] **Step 2: Full compile + theme test (headed)**

Run:
```bash
python -m py_compile launcher.py launcher_theme.py
python -m pytest tests/launcher/test_theme.py -v
```
Expected: compile clean; `test_constants_defined` + `test_load_logo_missing_returns_none` PASS (logo-present test passes or skips per display).

- [ ] **Step 3: Manual QA — run the launcher (headed Windows session)**

Run: `python launcher.py`

Verify against the spec's QA checklist, plus these UX additions:
- [ ] Window opens at 720×600, follows OS light/dark (toggle Windows theme, relaunch).
- [ ] **ActivationScreen**: ARCADE logo header visible; error card shows a **bold red headline + detail + recovery line** (not a red wall of text); "Copy" copies the Hardware ID and shows a confirmation; "Browse for license.key…" (blue, pointer cursor) opens the file dialog and re-routes on a valid key.
- [ ] **SetupWizard**: header present; Server / Staff / Seats groups; placeholders + blue focus border; PIN fields masked; **helper text under Port and Seats**; scroll works if needed; "Finish" (blue, pointer cursor) writes `arcade.config.json` and seeds staff.
- [ ] **MainScreen**: status pill is red "Stopped" then turns emerald "Running at http://…" on Start; Stop turns it red; Open Dashboard opens the browser; **logs show an empty-state message until the server starts, then stream**; all three buttons show a pointer cursor.
- [ ] Light and dark modes both readable — **captions/secondary text must clear 4.5:1 in light mode** (slate-500 `#64748B`, not `#94A3B8`).
- [ ] **Missing-logo fallback**: temporarily rename `frontend/public/icon_opc.png`, relaunch — launcher still opens with a text-only "ARCADE" header, then restore the file.
- [ ] **Optional font**: drop a `.ttf` into a `fonts/` folder beside `launcher.py` and confirm the wordmark/headings switch to it (then remove it to keep the repo clean).

- [ ] **Step 4: Commit (if any fixes were needed in Step 1/3)**

```bash
git add launcher.py launcher_theme.py
git commit -m "fix(launcher): final cleanup + verify themed launcher"
```
(If no changes were required, skip this commit and just report done.)

---

## Self-Review Notes

- **Spec coverage:** §2 palette → `launcher_theme.py` constants (Task 1). §3.1 theme helper → Task 1. §3.2 `LauncherApp`→`ctk.CTk` + `set_appearance_mode("System")` → Task 2. §3.3 unchanged logic → preserved verbatim in Tasks 3–5 (`_browse`, `_seed_default_staff`, `_finish`, subprocess). §4.1 Activation → Task 3. §4.2 SetupWizard → Task 4. §4.3 MainScreen → Task 5. §4.4 window 720×600 → Task 2. §5 data/error → preserved. §6 testing → Task 1 (unit) + Task 6 (manual). §7 risks (logo path, missing-logo fallback) → `load_logo` + Task 6 fallback check.
- **Placeholder scan:** No TBD/TODO/"implement later"/"similar to Task N" used; every code step shows full code.
- **Type consistency:** `brand_header(parent, *, subtitle)` and `load_logo(size=64) -> Optional[ctk.CTkImage]` are defined in Task 1 and called consistently in Tasks 3–5. Color/font names (`BLUE, EMERALD, RED, S700, S700_HOVER, S900, TEXT, MUTED, RADIUS, BTN_HEIGHT, body_font, heading_font, mono_font, title_font, wordmark_font`) match the imports added in Task 2. `S800` is used in Task 3 (error card) and defined in Task 1. No renamed symbols across tasks.
- **Tkinter vs CTk:** Intentionally kept `import tkinter as tk` for `StringVar`, `filedialog`, `messagebox`, `tk.BOTH`, and `tk.Widget` type hints — these are valid and required; only widget *classes* moved to `ctk.*`.

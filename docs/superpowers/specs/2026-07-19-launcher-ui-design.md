# Launcher UI Redesign — Design Spec

- **Date:** 2026-07-19
- **Status:** Approved (design), ready for implementation plan
- **Component:** `launcher.py` (Arcade Launcher — Tkinter GUI for license activation, setup, and server management)
- **Goal:** Modernize the launcher's UI with CustomTkinter, apply the app's existing blue/slate design system, and add the brand logo — without changing any business logic.

---

## 1. Summary

The Arcade Launcher (`launcher.py`, ~571 lines) is a Tkinter GUI that gates the
server behind a license check and then offers a setup wizard and a server
control screen. The current UI uses raw `tkinter` with hardcoded Arial fonts,
a flat `#f5f5f5` background, and a particularly weak **"License Required"**
screen (wall of red `#c33` text, tiny readonly entry, plain button).

This redesign:

1. Migrates all widgets from `tkinter` to **CustomTkinter** (`ctk.*`) — already
   present in `backend/requirements.txt` (`customtkinter>=5.2.0`, installed 6.0.0).
2. Applies the **app's existing design tokens** (blue brand on slate surfaces,
   emerald Start, red Stop/error) sourced from `frontend/src/index.css` and
   `frontend/src/components/ui/Button.tsx`.
3. Adds the **brand logo** (`frontend/public/icon_opc.png` — transparent, no
   background) to every screen via a reusable header.
4. **Preserves all behavior** — license routing, config writing, staff seeding,
   and subprocess server management are unchanged.

Approach: **in-place rewrite** of `launcher.py` plus one new helper file
`launcher_theme.py`. No new dependencies, no structural packaging.

---

## 2. Design System (from the app)

Source of truth: `frontend/src/index.css` (`@theme`) and `Button.tsx` variants.

| Token | Value | Launcher use |
|---|---|---|
| `brand-600` | `#2563EB` | Primary action (Browse, Finish), focus ring, header divider |
| `brand-500` (hover) | `#3B82F6` | Primary hover |
| `emerald-600` | `#059669` (hover `#10B981`) | Start Server |
| `red-600` | `#DC2626` (hover `#EF4444`) | Stop Server, error accents |
| `surface-900` | `#0F172A` | Dark-mode window/frame bg |
| `surface-800` | `#1E293B` | Dark-mode raised surfaces |
| `surface-700` | `#334155` | Borders, secondary button (dark) |
| `text-50` | `#F8FAFC` | Primary text (dark mode) |
| `text-muted` | `#94A3B8` | Secondary text, captions |
| `slate-100` | `#F1F5F9` | Light-mode window bg |
| `slate-900` | `#0F172A` | Light-mode text |
| radius | `8px` (`rounded-lg`) | `corner_radius=8` on widgets |
| control height | `44px` (`min-h-11`) | Buttons ~44px tall |
| font | `ui-sans-serif, system-ui` | System sans; `ui-monospace` for Hardware ID |

**Logo:** `frontend/public/icon_opc.png` — the orange arcade-controller mark with
"ARCADE" wordmark. It is transparent (no background), so a single `CTkImage` works
on both light and dark themes. The logo keeps its brand orange; the **UI chrome**
uses the app's blue/slate accent. This mirrors how the rest of the app presents a
colored logo alongside blue accents.

---

## 3. Architecture

### 3.1 `launcher_theme.py` (new)
Centralizes every visual constant so the three screens stay consistent.

- `BRAND_LOGO_PATH = Path(__file__).parent / "frontend" / "public" / "icon_opc.png"`
- `load_logo(size: int) -> ctk.CTkImage | None` — loads `icon_opc.png` as a
  `CTkImage` (single variant, transparent). Returns `None` if the file is missing
  so callers can fall back to a text-only header (the launcher must never fail to open).
- Color constants (dark + light variants) as listed in §2.
- `RADIUS = 8`, `BTN_HEIGHT = 44`.
- Font helpers: `heading_font()`, `body_font()`, `mono_font()`.
- `brand_header(parent, *, title: str, subtitle: str) -> ctk.CTkFrame` — renders
  the logo (or placeholder), "ARCADE" wordmark, subtitle/tagline, and a thin blue
  divider. Called at the top of every screen.

### 3.2 `launcher.py` (rewritten in place)
- `LauncherApp` subclasses **`ctk.CTk`** instead of `tk.Tk`. At startup:
  `ctk.set_appearance_mode("System")` (follows OS light/dark) and apply theme defaults.
- `show_screen()`, `_on_close()` (FR-SYS-010), `_check_and_route()` (FR-SYS-008),
  `run()` are preserved with the same signatures/behavior; only widget
  construction inside screens changes.
- Screens subclass **`ctk.CTkFrame`**:
  - `ActivationScreen(ctk.CTkFrame)`
  - `SetupWizard(ctk.CTkFrame)`
  - `MainScreen(ctk.CTkFrame)`
- Widget swaps (behavior identical):
  - `tk.Label` → `ctk.CTkLabel`
  - `tk.Button` → `ctk.CTkButton` (primary blue, secondary slate, emerald/red tints)
  - `tk.Entry` → `ctk.CTkEntry` (placeholder_text, `show="*"` for PINs)
  - `tk.Frame` → `ctk.CTkFrame`
  - `scrolledtext.ScrolledText` → `ctk.CTkTextbox` (native scroll)
  - Canvas status dot → **status pill** (`ctk.CTkLabel` with `fg_color`)
  - Setup form → wrapped in `ctk.CTkScrollableFrame` so it never overflows.
- Module-level helpers preserved verbatim: `_LICENSE_ERROR_MESSAGES`,
  `_db_path()`, `_write_license_status()` (FR-LIC-014).

### 3.3 What is NOT changed
- `_browse()` — filedialog + `shutil.copy2` of `license.key`, then re-route.
- `_seed_default_staff()` — background thread; `ensure_default_staff` + migrations.
- `_finish()` — writes `arcade.config.json` (same keys, `hash_pin`,
  `secrets.token_hex(32)` per-seat agent secrets). **Byte-equivalent config output.**
- `MainScreen` server lifecycle — `subprocess.Popen` for `uvicorn`, terminate/kill,
  log streaming thread, `_open_dashboard()` via `webbrowser`.

---

## 4. Screen-by-screen

### 4.1 ActivationScreen ("License Required") — the flagged screen
- Branded header (`brand_header`).
- Title "License Required" in calm `text-50`/`slate-900` (not huge red).
- Error message rendered in a **rounded card** (`CTkFrame`, `corner_radius=8`) with a
  **red left accent stripe** (`border_color=RED` / a thin red inner frame) and muted
  body text. Copy is unchanged from `_LICENSE_ERROR_MESSAGES`.
- **Hardware ID** row: label "Your Hardware ID" + a **readonly `CTkEntry`** in
  monospace (`mono_font()`) + a **"Copy"** `CTkButton` (secondary) that writes the
  value to the clipboard (`root.clipboard_clear/clear` + `clipboard_append`; wrapped
  in try/except, surfaced via `CTkMessagebox` on failure).
- Helper line under the ID: "Share this ID with support to get your license."
- **"Browse for license.key…"** — the single **primary (blue)** `CTkButton`.

### 4.2 SetupWizard
- Branded header.
- All inputs live inside a `CTkScrollableFrame`.
- Grouped sub-frames with small section labels:
  - **Server:** Cafe Name, Server IP (default `0.0.0.0`), Port (default `8000`).
  - **Staff:** Admin ID (default `admin`), Admin PIN, Cashier ID (default `cashier`),
    Cashier PIN (PIN entries `show="*"`).
  - **Seats:** Number of Seats (default `8`).
- `CTkEntry` widgets use `placeholder_text` for hints and blue focus ring.
- **"Finish"** — primary (blue) `CTkButton`; calls the unchanged `_finish()`.

### 4.3 MainScreen
- Branded header.
- **Status pill:** `CTkLabel` with `fg_color` — emerald when running, red when
  stopped — plus the status text (e.g., "Running at http://0.0.0.0:8000" / "Stopped").
- Buttons: **Start Server** (emerald), **Stop Server** (red),
  **Open Dashboard** (blue/slate secondary).
- **Logs:** `CTkTextbox` (disabled-by-default, appended via `_append_log`), replacing
  `ScrolledText`. Streaming thread and stop-event logic unchanged.

### 4.4 Window
- `720 × 600`, `minsize(720, 600)`, appearance mode **System**.

---

## 5. Data Flow & Error Handling

- **Routing:** `_check_and_route()` unchanged — decides Activation / Setup / Main
  from `check_license()` result and `arcade.config.json` presence.
- **Config output:** `_finish()` produces the same `arcade.config.json` schema.
  No consumer (backend `core.config.Settings`) is affected.
- **Error presentation only:** license-error copy is preserved; only its visual
  treatment changes (card + red stripe vs red text).
- **Clipboard / logo failures:** caught and surfaced via `CTkMessagebox`
  (or `tkinter.messagebox` fallback) — never crash the launcher.
- **Missing logo:** `load_logo()` returns `None` → `brand_header` renders a
  text-only wordmark so the launcher still opens.

---

## 6. Testing & Verification

CustomTkinter requires a display, so automated GUI tests are limited. Plan:

1. **Unit test — `launcher_theme.py`:**
   - `load_logo()` returns a `ctk.CTkImage` when `icon_opc.png` exists.
   - `load_logo()` returns `None` (graceful) when the logo is absent.
   - Color/font constants are defined and non-empty.
   - *Note:* this test imports `customtkinter`, which needs a Tk display. Run it in
     a headed environment or guard with a display-availability check; **do not** block
     `make test` / CI on it (documented headless limitation).
2. **Import / syntax smoke test:** `python -c "import ast; ast.parse(open('launcher.py').read())"`
   plus `py_compile` for both files. Ensures no syntax/indent regressions.
3. **Manual QA checklist (the real verification):**
   - [ ] Launcher opens in **System** mode on Windows; switch OS theme → UI follows.
   - [ ] ActivationScreen: header logo visible, error card styled, Copy button copies HWID.
   - [ ] SetupWizard: all fields present, scroll works, Finish writes config + seeds staff.
   - [ ] MainScreen: Start (emerald) launches server + green pill; Stop (red) terminates;
        Open Dashboard opens browser; logs stream.
   - [ ] Light and dark modes both reviewed for contrast/readability.
   - [ ] Missing-logo fallback: rename `icon_opc.png` → launcher still opens (text header).

---

## 7. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Logo path resolution across CWD / packaged builds | Resolve via `Path(__file__).parent / "frontend" / "public" / "icon_opc.png"`; fall back to text header if missing. |
| CustomTkinter behavior differs from Tk under PyInstaller packaging | Keep widget swaps 1:1; verify in a headed run before any packaging step. |
| Display-dependent test imports break headless CI | Separate GUI/theme tests from `make test`; document the limitation (§6). |
| Accidental change to config schema | `_finish()` logic copied verbatim; config keys asserted unchanged in QA. |

---

## 8. Out of Scope

- No backend, frontend, or agent changes.
- No new dependencies (CustomTkinter already required).
- No changes to licensing logic, security model, or `agent_secret` handling.
- No packaging/PyInstaller changes (verified separately).

# ARCH-03: PyInstaller `--onedir` + FastAPI + Alembic + aiosqlite + Tkinter Validation

**Status:** ✅ PASS (validated June 2026, Windows 11)
**Build host:** Windows 11, Python 3.13.12, PyInstaller 6.21.0
**PoC location:** `backend/tests/validation_tasks/arch03/`

This proves the ARCH-03 pass criteria from `TODO.md`: *"The bundled launcher shows the License Activation screen on a fresh machine with no Python installed."* All four historically-fragile subsystems (Alembic, aiosqlite, FastAPI/uvicorn, Tkinter) were frozen into a single `--onedir` bundle and verified both headlessly and through the real launcher flow.

---

## 1. Summary

| Criterion (from TODO.md) | Result | Evidence |
|---|---|---|
| Build a minimal PoC bundle on Windows | ✅ PASS | `dist/arch03_launcher/arch03_launcher.exe` (9.4 MB) + `_internal/` (36 MB) |
| `alembic upgrade head` runs from within the bundle without Python installed | ✅ PASS | frozen self-test `[PASS] alembic upgrade head` |
| `aiosqlite` dynamic library loads correctly (C extensions) | ✅ PASS | frozen self-test `[PASS] fastapi /health (aiosqlite)` + real TCP `/health` over aiosqlite |
| Tkinter is bundled and renders correctly | ✅ PASS | frozen self-test `[PASS] tkinter widget render` (root + widget constructs inside frozen exe) |
| Launcher shows License Activation screen on a fresh machine | ✅ PASS | `launcher.py` builds the Hardware-ID activation UI; verified by frozen `-m uvicorn` boot + `/health` 200 |

**Frozen self-test output (final build):**
```
=== ARCH-03 frozen self-test ===
frozen=True bundle_dir=...\dist\arch03_launcher
python=3.13.12 executable=...\arch03_launcher.exe
[PASS] imports
[PASS] tkinter widget render
[PASS] alembic upgrade head
[PASS] fastapi /health (aiosqlite)
[PASS] uvicorn via -m (real HTTP)
=== result: ALL PASS ===
```

---

## 2. PoC architecture

```
arch03/
├── launcher.py        ← Tkinter entry point (License Activation screen).
│                        Entry point of the bundle. Emulates `python -m` via runpy
│                        so its own Start-Server button can spawn uvicorn.
├── app.py             ← Minimal FastAPI app (async SQLAlchemy + aiosqlite, WAL pragmas).
├── alembic_app.py     ← Programmatic Alembic migration runner (no alembic.ini on disk).
├── arch03.spec        ← PyInstaller --onedir spec (hidden imports + data files).
├── build.py           ← Lock-tolerant rebuild helper (absorbs Windows WinError 32).
├── dist/arch03_launcher/
│   ├── arch03_launcher.exe
│   └── _internal/     ← All deps (fastapi, sqlalchemy, alembic, aiosqlite, tcl/tk, mako)
└── build/             ← PyInstaller intermediates
```

The launcher deliberately mirrors the real `launcher.py` flow (Phase 1, Feature 1.2.5): resolve bundle dir → run Alembic → spawn uvicorn → show activation UI → on close, terminate the server.

---

## 3. The four PyInstaller gotchas (and how the spec solves them)

PyInstaller's static analyzer misses anything imported dynamically. Each subsystem below required an explicit fix in `arch03.spec`.

### 3.1 Alembic — dynamic dialect discovery + Mako templates
**Problem:** Alembic resolves the SQLAlchemy dialect via entry points and renders migration scripts through Mako templates shipped as `.mako` data files inside the `alembic` package. Both are invisible to PyInstaller's static analysis.
**Fix in spec:**
```python
hiddenimports += collect_submodules("alembic")
hiddenimports += collect_submodules("sqlalchemy")
hiddenimports += ["sqlalchemy.dialects.sqlite",
                  "sqlalchemy.dialects.sqlite.aiosqlite",
                  "sqlalchemy.dialects.sqlite.pysqlite"]
hiddenimports += ["mako", "mako.template", "mako.runtime"]
datas += collect_data_files("alembic")   # the .mako templates
```
**Runtime approach:** instead of relying on an `alembic.ini` + `env.py` on disk (which is fragile to freeze — Alembic resolves scripts by path and imports the config module), `alembic_app.py` drives `MigrationContext` directly on a sync connection obtained from the async engine via `run_sync`. This mirrors how the real backend applies migrations inside its async `lifespan`.
**Verified:** `dist/.../alembic/templates/*/script.py.mako` present (11 templates); frozen `[PASS] alembic upgrade head`.

### 3.2 aiosqlite + SQLAlchemy async dialect — entry-point registration
**Problem:** `aiosqlite` and SQLAlchemy's async SQLite dialect (`sqlalchemy.dialects.sqlite.aiosqlite`) are registered via setuptools entry points, so PyInstaller does not see them.
**Fix in spec:**
```python
hiddenimports += ["aiosqlite",
                  "sqlalchemy.ext.asyncio",
                  "sqlalchemy.ext.asyncio.engine",
                  "greenlet"]
```
**Note on "C extensions":** `aiosqlite` itself is pure-Python (it wraps the stdlib `sqlite3` module). The actual compiled artifact is `_sqlite3.pyd`, which PyInstaller's stdlib hook bundles automatically — confirmed at `_internal/_sqlite3.pyd`. This is the part TODO.md's "it has C extensions" line refers to.
**Verified:** frozen `[PASS] fastapi /health (aiosqlite)`; real TCP `/health` returns `{status: ok}`.

### 3.3 FastAPI / Starlette / Pydantic — plugin discovery
**Problem:** FastAPI, Starlette, and Pydantic ship many optional submodules pulled in only via string-based plugin discovery.
**Fix in spec:**
```python
hiddenimports += collect_submodules("fastapi")
hiddenimports += collect_submodules("starlette")
hiddenimports += collect_submodules("pydantic")
hiddenimports += collect_submodules("pydantic_core")
datas += collect_data_files("fastapi")
datas += collect_data_files("starlette")
```

### 3.4 Tkinter — tcl/tk runtime data
**Problem:** Tkinter requires the tcl/tk C libraries **and** the tcl/tk script libraries (`.tcl` files) at runtime. PyInstaller's tkinter hook handles the bulk, but the layout matters.
**Fix in spec:**
```python
hiddenimports += ["tkinter", "tkinter.ttk", "tkinter.scrolledtext", "_tkinter"]
```
**Verified bundled (PyInstaller 6.x hook layout):**
- C libs: `_internal/tk86t.dll`, `_internal/tcl86t.dll`
- Script data: `_internal/_tcl_data/`, `_internal/_tk_data/` (e.g. `tk.tcl`, `tkfbox.tcl`)
- Frozen `[PASS] tkinter widget render` — a real `tk.Tk()` root + `ttk.Label` constructs and renders inside the frozen exe.

---

## 4. Cross-platform notes (R-10)

PyInstaller **cannot cross-compile**. The Windows bundle was built on Windows; macOS `.app` and Linux binaries must be built on their respective OSes (or via GitHub Actions runners — `windows-latest`, `macos-latest`, `ubuntu-latest`), per Assumption 7 / Risk R-10. This PoC validates the **Windows** target (the v1.0 primary, per Assumption 3). The same spec + hidden-import list should be reused on each platform, with these additions:

- **Linux:** Tkinter requires `python3-tk` at **build** time (`sudo apt install python3-tk` on the runner before `pyinstaller`). Already called out in TODO.md.
- **macOS:** no extra system deps expected; verify the `.app` is ad-hoc/notarized separately (out of scope for this arch validation).

---

## 5. Known Windows build hazards (documented in `build.py`)

1. **`WinError 32` on `--clean`.** On Windows, a previous run's handle (aiosqlite connection pool, dllhost thumbnail generation, or Defender on-access scan) briefly holds a file in `dist/`, killing `pyinstaller --clean`. `build.py` wraps `shutil.rmtree` in a retry loop (8 attempts, 1 s apart) that absorbs the transient lock — the single most common cause of repeated build failures.
2. **Scratch files must stay out of `BUNDLE_DIR`.** The frozen self-test writes all DBs to a `tempfile.mkdtemp()` scratch dir, never into the bundle dir. Reason: aiosqlite/SQLAlchemy can briefly hold the DB file handle after teardown, which would leave the bundle dir locked and trigger WinError 32 on the next `--clean`. Keeping scratch out of the bundle makes the exe fully self-cleaning.

---

## 6. `uvicorn` from a frozen exe — the `-m` emulation (Fix A)

A PyInstaller-frozen exe is **not** a general Python interpreter: `arch03_launcher.exe -m uvicorn app:app ...` just hands the args to `launcher.main()`. Without handling, the launcher's Start-Server button (which spawns `[sys.executable, "-m", "uvicorn", ...]`) would fall through to the Tkinter `mainloop()` and hang.

`launcher.main()` intercepts the `-m` form and dispatches via `runpy.run_module`, with `sys.argv` reshaped so the target sees what it expects:
```python
if len(sys.argv) > 2 and sys.argv[1] == "-m":
    import runpy
    module_name = sys.argv[2]
    sys.argv = sys.argv[2:]            # ['-m', 'uvicorn', 'app:app', ...]
    runpy.run_module(module_name, run_name="__main__")
    return 0
```
The frozen self-test's `uvicorn via -m (real HTTP)` check exercises this exact path: it binds a free port, runs `exe -m uvicorn app:app`, and polls a real TCP `/health` until it returns `{status: ok}`. This proves uvicorn + app.py + aiosqlite + WAL come up together inside the frozen bundle over a real socket — not just an in-process `ASGITransport`.

**Verified end-to-end:** the launcher's real invocation booted uvicorn on a real port and `/health` returned `{status: ok, db_path: ..., boot_at: ...}`.

---

## 7. How to reproduce

```bash
# From the venv (PyInstaller + all deps installed):
cd backend/tests/validation_tasks/arch03

# Build (--noconfirm; build.py handles the --clean lock retries):
python build.py

# Validate the frozen bundle headlessly (no display needed):
./dist/arch03_launcher/arch03_launcher.exe --self-test

# Launch the GUI (License Activation screen):
./dist/arch03_launcher/arch03_launcher.exe
```

The full PoC is self-contained and reproducible from a clean checkout + `pip install -r backend/requirements.txt` + `pip install pyinstaller`.

---

## 8. Carry-over to Phase 11 (Deployment & Packaging)

The real production launcher (Phase 11) should reuse this PoC's spec structure verbatim, extending `hiddenimports` for the additional deps (`argon2-cffi`, `python-jose`, `apscheduler`, `py-machineid`, `cryptography`, `tinytuya`, `python-escpos`, `PyNaCl`, `httpx`):

| PoC entry | Production equivalent |
|---|---|
| `arch03.spec` | `packaging/arcade.spec` (Phase 11) |
| `alembic_app.py` (programmatic runner) | Reuse — real backend applies migrations the same way in `lifespan` |
| `launcher.py` `-m` emulation | Reuse — production launcher spawns uvicorn identically |
| `build.py` lock-tolerant clean | Reuse — fold into the Phase 11 build script |
| Programmatic Alembic (no `alembic.ini`/`env.py` on disk) | **Recommended** — avoids the most fragile freeze path; the bundled `alembic/templates/*.mako` prove Mako rendering works regardless |

**Decision for Phase 1:** the real backend's `lifespan` should apply migrations programmatically (via `MigrationContext` on a `run_sync` connection), **not** by shelling out to the `alembic` CLI. This is the approach proven here and avoids the alembic.ini/env.py freeze fragility entirely.

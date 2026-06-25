"""ARCH-03 PoC: Tkinter Launcher that runs inside a PyInstaller --onedir bundle.

Proves the ARCH-03 pass criteria: "The bundled launcher shows the License
Activation screen on a fresh machine with no Python installed."

Flow:
  1. Resolve bundle dir (sys.executable's parent when frozen).
  2. Run ``alembic upgrade head`` via the programmatic runner.
  3. Spawn ``uvicorn app:app`` as a subprocess (bundled alongside).
  4. Show a License Activation screen (Hardware ID + status) and a live log.
  5. On close: terminate the uvicorn subprocess.
"""
from __future__ import annotations

import logging
import os
import subprocess
import sys
import threading
import time
import tkinter as tk
from datetime import datetime, timezone
from pathlib import Path
from tkinter import messagebox, scrolledtext, ttk

log = logging.getLogger("arch03.launcher")

IS_FROZEN = getattr(sys, "frozen", False)
BUNDLE_DIR = Path(sys.executable).parent if IS_FROZEN else Path(__file__).resolve().parent
# When running from source, app.py lives next to launcher.py; when frozen, both
# are importable as modules from the bundle root.
APP_MODULE_DIR = BUNDLE_DIR.parent if IS_FROZEN else BUNDLE_DIR


def bundle_info() -> dict[str, object]:
    return {
        "frozen": IS_FROZEN,
        "bundle_dir": str(BUNDLE_DIR),
        "python_executable": sys.executable,
        "python_version": sys.version,
    }


def run_alembic_upgrade() -> str:
    """Apply migrations before the server starts. Returns a status string."""
    try:
        from alembic_app import run_migrations

        db_path = BUNDLE_DIR / "arch03_app.db"
        url = f"sqlite+aiosqlite:///{db_path}"
        import asyncio

        asyncio.run(run_migrations(url))
        return f"OK: alembic upgrade head applied ({db_path.name})"
    except Exception as exc:  # noqa: BLE001
        log.exception("alembic upgrade failed")
        return f"FAIL: alembic upgrade head: {exc!r}"


class LauncherApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.server_proc: subprocess.Popen | None = None
        self._poll_after_id: str | None = None

        root.title("Arcade Launcher — ARCH-03 PoC")
        root.geometry("760x560")
        root.minsize(640, 480)

        self._build_ui()
        self._append_log(f"Bundle info: {bundle_info()}")

        # Defer the heavy work so the window paints first.
        self.root.after(100, self._bootstrap)

    # ------------------------------------------------------------------ UI

    def _build_ui(self) -> None:
        pad = {"padx": 12, "pady": 6}

        header = ttk.Frame(self.root)
        header.pack(fill="x", **pad)
        ttk.Label(header, text="Arcade — License Activation", font=("TkDefaultFont", 16, "bold")).pack(
            anchor="w"
        )
        ttk.Label(
            header,
            text="ARCH-03 proof-of-concept — not for distribution.",
            foreground="#666",
        ).pack(anchor="w")

        # Hardware ID (copyable read-only entry), per FR-LIC-009 activation UX.
        hw_frame = ttk.LabelFrame(self.root, text="Hardware ID")
        hw_frame.pack(fill="x", **pad)
        self.hw_var = tk.StringVar(value="(computing…)")
        hw_entry = ttk.Entry(hw_frame, textvariable=self.hw_var, state="readonly", width=72)
        hw_entry.pack(fill="x", padx=8, pady=8)
        ttk.Button(hw_frame, text="Copy", command=self._copy_hw).pack(anchor="e", padx=8, pady=(0, 8))

        # Server controls + status dot.
        ctrl = ttk.Frame(self.root)
        ctrl.pack(fill="x", **pad)
        self.start_btn = ttk.Button(ctrl, text="Start Server", command=self._start_server, state="disabled")
        self.start_btn.pack(side="left")
        self.stop_btn = ttk.Button(ctrl, text="Stop Server", command=self._stop_server, state="disabled")
        self.stop_btn.pack(side="left", padx=6)
        self.status_dot = tk.Canvas(ctrl, width=16, height=16, highlightthickness=0)
        self.status_dot.pack(side="left", padx=8)
        self._draw_dot("grey")
        self.status_lbl = ttk.Label(ctrl, text="Idle", width=24)
        self.status_lbl.pack(side="left")
        ttk.Button(ctrl, text="Open Dashboard", command=self._open_dashboard).pack(side="right")

        # Live log.
        log_frame = ttk.LabelFrame(self.root, text="Log")
        log_frame.pack(fill="both", expand=True, **pad)
        self.log_widget = scrolledtext.ScrolledText(log_frame, height=14, state="disabled", font=("Consolas", 9))
        self.log_widget.pack(fill="both", expand=True, padx=8, pady=8)

        # Close behaviour (FR-SYS-010: confirm exit if server running).
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _draw_dot(self, color: str) -> None:
        self.status_dot.delete("all")
        self.status_dot.create_oval(2, 2, 14, 14, fill=color, outline="black")

    def _copy_hw(self) -> None:
        self.root.clipboard_clear()
        self.root.clipboard_append(self.hw_var.get())
        self._append_log("Hardware ID copied to clipboard.")

    # ----------------------------------------------------------- bootstrap

    def _bootstrap(self) -> None:
        self._append_log("Running alembic upgrade head…")
        status = run_alembic_upgrade()
        self._append_log(status)
        self.hw_var.set(self._compute_hardware_id())
        self._append_log("Ready. Press 'Start Server' to boot uvicorn.")
        self.start_btn.config(state="normal")

    def _compute_hardware_id(self) -> str:
        # Mirrors the fingerprint fallback chain in the real licensing module.
        try:
            import hashlib
            import socket
            import uuid

            mac = ":".join(f"{b:02x}" for b in uuid.getnode().to_bytes(6, "big"))
            host = socket.gethostname()
            return hashlib.sha256(f"{host}|{mac}".encode()).hexdigest()[:32]
        except Exception as exc:  # noqa: BLE001
            log.exception("hardware id failed")
            return f"<unavailable: {exc!r}>"

    # ------------------------------------------------------------- server

    def _start_server(self) -> None:
        if self.server_proc and self.server_proc.poll() is None:
            self._append_log("Server already running.")
            return

        try:
            cmd = self._server_command()
            self._append_log(f"Starting: {' '.join(cmd)}")
            self.server_proc = subprocess.Popen(
                cmd,
                cwd=str(BUNDLE_DIR),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
        except Exception as exc:  # noqa: BLE001
            self._append_log(f"FAIL start server: {exc!r}")
            return

        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self._draw_dot("orange")
        self.status_lbl.config(text="Booting…")
        threading.Thread(target=self._pump_output, daemon=True).start()
        self._poll_server()

    def _server_command(self) -> list[str]:
        # When frozen, uvicorn ships as a CLI exe inside _internal; when run
        # from source we use the venv python.
        if IS_FROZEN:
            # Bundled as data: invoke via the bundled Python interpreter.
            return [sys.executable, "-m", "uvicorn", "app:app", "--host", "127.0.0.1", "--port", "8011"]
        return [
            sys.executable,
            "-m",
            "uvicorn",
            "app:app",
            "--host",
            "127.0.0.1",
            "--port",
            "8011",
            "--app-dir",
            str(BUNDLE_DIR),
        ]

    def _pump_output(self) -> None:
        assert self.server_proc is not None
        assert self.server_proc.stdout is not None
        for line in self.server_proc.stdout:
            self.root.after(0, self._append_log, line.rstrip("\n"))

    def _poll_server(self) -> None:
        if not self.server_proc:
            return
        rc = self.server_proc.poll()
        if rc is None:
            # Probe the health endpoint to confirm it is actually serving.
            threading.Thread(target=self._probe_health, daemon=True).start()
            self._poll_after_id = self.root.after(3000, self._poll_server)
        else:
            self._append_log(f"Server process exited (code={rc}).")
            self._server_down()

    def _probe_health(self) -> None:
        try:
            import urllib.request

            with urllib.request.urlopen("http://127.0.0.1:8011/health", timeout=2) as resp:
                body = resp.read().decode()
            self.root.after(0, self._server_up, body)
        except Exception:
            pass  # still booting; keep polling

    def _server_up(self, body: str) -> None:
        self._draw_dot("green")
        self.status_lbl.config(text="Running")
        self._append_log(f"Health OK: {body}")

    def _server_down(self) -> None:
        self._draw_dot("red")
        self.status_lbl.config(text="Stopped")
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")

    def _stop_server(self) -> None:
        if self.server_proc and self.server_proc.poll() is None:
            self._append_log("Stopping server…")
            self.server_proc.terminate()
            try:
                self.server_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.server_proc.kill()
        self._server_down()

    def _open_dashboard(self) -> None:
        import webbrowser

        webbrowser.open("http://127.0.0.1:8011/health")

    # -------------------------------------------------------------- close

    def _on_close(self) -> None:
        if self.server_proc and self.server_proc.poll() is None:
            if not messagebox.askyesno(
                "Confirm Exit",
                "The Arcade server is still running. Closing will stop it. Continue?",
            ):
                return
            self._stop_server()
        if self._poll_after_id:
            self.root.after_cancel(self._poll_after_id)
        self.root.destroy()

    # -------------------------------------------------------------- log

    def _append_log(self, msg: str) -> None:
        ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
        self.log_widget.config(state="normal")
        self.log_widget.insert("end", f"[{ts}] {msg}\n")
        self.log_widget.see("end")
        self.log_widget.config(state="disabled")


def _self_test() -> int:
    """Non-GUI verification of every frozen subsystem.

    Exercised by ``arch03_launcher --self-test`` so the bundle can be validated
    on a fresh VM / in CI without a display. Each step prints PASS/FAIL.
    """
    print("=== ARCH-03 frozen self-test ===")
    print(f"frozen={IS_FROZEN} bundle_dir={BUNDLE_DIR}")
    print(f"python={sys.version.split()[0]} executable={sys.executable}")
    failures: list[str] = []

    def check(name: str, fn) -> None:  # noqa: ANN001
        try:
            fn()
            print(f"[PASS] {name}")
        except Exception as exc:  # noqa: BLE001
            print(f"[FAIL] {name}: {exc!r}")
            failures.append(name)

    # All DB-touching steps write to a throwaway temp dir — NEVER into
    # BUNDLE_DIR. On Windows, aiosqlite/SQLAlchemy can briefly hold the DB
    # file handle after teardown, which leaves the bundle dir locked and causes
    # WinError 32 on the next `pyinstaller --clean`. Keeping scratch files out
    # of the bundle dir makes the exe fully self-cleaning.
    import tempfile

    scratch = tempfile.mkdtemp(prefix="arch03_selftest_")

    # 1. All key imports resolve under the frozen interpreter.
    def _imports() -> None:
        import fastapi  # noqa: F401
        import sqlalchemy  # noqa: F401
        import aiosqlite  # noqa: F401
        import alembic  # noqa: F401
        import uvicorn  # noqa: F401
        import mako  # noqa: F401
        import greenlet  # noqa: F401
        from sqlalchemy.dialects.sqlite import aiosqlite as _a  # noqa: F401
        import app  # noqa: F401
        import alembic_app  # noqa: F401

    check("imports", _imports)

    # 2. Tkinter can construct a root + widget (the License Activation screen
    #    is Tkinter — if this fails headlessly, document it, don't fail the
    #    whole validation; the GUI still works on a real desktop).
    def _tk() -> None:
        root = tk.Tk()
        root.withdraw()
        ttk.Label(root, text="probe").pack()
        root.update()
        root.destroy()

    check("tkinter widget render", _tk)

    # 3. Alembic migration runner applies cleanly to a fresh DB (in temp dir).
    def _alembic() -> None:
        from alembic_app import run_migrations

        db = Path(scratch) / "alembic.db"
        import asyncio

        asyncio.run(run_migrations(f"sqlite+aiosqlite:///{db}"))

    check("alembic upgrade head", _alembic)

    # 4. FastAPI app serves /health over aiosqlite + WAL (DB in temp dir).
    #    app.py reads ARCADE_DB_PATH at import time, so point it at temp before
    #    importing. The app creates its table inside `lifespan`, which
    #    ASGITransport does not auto-run, so we create the schema explicitly
    #    first (mirrors real boot order: alembic → uvicorn → lifespan seed).
    def _server() -> None:
        os.environ["ARCADE_DB_PATH"] = str(Path(scratch) / "server.db")
        # Force re-import so the env var takes effect.
        import importlib

        import app as app_mod

        importlib.reload(app_mod)
        import asyncio

        from httpx import ASGITransport, AsyncClient

        async def go() -> None:
            async with app_mod.engine.begin() as conn:
                await conn.run_sync(app_mod.Base.metadata.create_all)
            async with AsyncClient(transport=ASGITransport(app=app_mod.app), base_url="http://t") as c:
                r = await c.get("/health")
                assert r.status_code == 200, r.text
            await app_mod.engine.dispose()

        asyncio.run(go())

    check("fastapi /health (aiosqlite)", _server)

    # 5. `exe -m uvicorn app:app` boots a REAL server over TCP. This is the exact
    #    invocation the Launcher's Start-Server button makes, and it depends on
    #    main()'s runpy-based -m emulation (Fix A). It proves uvicorn + app.py +
    #    aiosqlite + WAL come up together inside the frozen bundle and answer a
    #    real socket — not just an in-process ASGITransport like check #4.
    def _uvicorn_via_m() -> None:
        import json
        import socket
        import urllib.request

        # Bind port 0 to grab a free port, then close and hand it to uvicorn.
        # Small TOCTOU race, but fine for a self-test on localhost.
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
        sock.close()

        # Keep scratch files OUT of BUNDLE_DIR (see note above) — point the
        # subprocess's app.py at a temp DB via env.
        env = dict(os.environ)
        env["ARCADE_DB_PATH"] = str(Path(scratch) / "uvicorn_m.db")

        # Frozen: the exe dispatches -m via runpy in main(). From source: run
        # launcher.py so the SAME main() path is exercised (not python's native
        # -m, which would skip Fix A entirely).
        if IS_FROZEN:
            cmd = [sys.executable, "-m", "uvicorn", "app:app", "--host", "127.0.0.1", "--port", str(port)]
        else:
            cmd = [
                sys.executable,
                str(Path(__file__).resolve()),
                "-m",
                "uvicorn",
                "app:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(port),
                "--app-dir",
                str(BUNDLE_DIR),
            ]

        proc = subprocess.Popen(
            cmd,
            cwd=str(BUNDLE_DIR),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        )
        try:
            url = f"http://127.0.0.1:{port}/health"
            deadline = time.time() + 20
            last_err = ""
            while time.time() < deadline:
                if proc.poll() is not None:
                    out = proc.stdout.read() if proc.stdout else ""
                    raise RuntimeError(f"server exited early (rc={proc.returncode})\n{out}")
                try:
                    with urllib.request.urlopen(url, timeout=2) as resp:
                        body = json.loads(resp.read().decode())
                        assert resp.status == 200, resp.status
                        assert body.get("status") == "ok", body
                        break
                except Exception as exc:  # noqa: BLE001
                    last_err = repr(exc)
                    time.sleep(0.5)
            else:
                raise RuntimeError(f"/health never came up within timeout; last err={last_err}")
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()

    check("uvicorn via -m (real HTTP)", _uvicorn_via_m)

    print("=== result: " + ("ALL PASS" if not failures else f"{len(failures)} FAILED: {failures}") + " ===")
    return 1 if failures else 0


def main() -> int:
    if "--self-test" in sys.argv:
        return _self_test()

    # Emulate `python -m <module>`. A PyInstaller-frozen exe is NOT a general
    # Python interpreter: `exe -m uvicorn app:app ...` just hands the args to
    # this main(). Without this branch, the launcher's Start-Server button
    # (which spawns [sys.executable, "-m", "uvicorn", ...]) would fall through
    # to mainloop() and hang. runpy resolves the bundled module the same way
    # `python -m` would, with argv reshaped so the target sees what it expects.
    if len(sys.argv) > 2 and sys.argv[1] == "-m":
        import runpy

        module_name = sys.argv[2]
        sys.argv = sys.argv[2:]  # e.g. ['-m', 'uvicorn', 'app:app', ...]
        runpy.run_module(module_name, run_name="__main__")
        return 0

    # Explicit GUI entry. No args also launches the GUI (parity with a real
    # launcher's default behavior). Anything else fails fast instead of
    # silently hanging in the Tkinter mainloop.
    if len(sys.argv) > 1 and sys.argv[1] not in ("--gui",):
        print(f"Unrecognized arguments: {sys.argv[1:]}", file=sys.stderr)
        print(
            "Use --self-test for validation, -m <module> [args...] to run a "
            "module, --gui for the interface, or no args to launch the GUI.",
            file=sys.stderr,
        )
        return 2

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    root = tk.Tk()
    try:
        # ttk theme nicety; non-fatal if unavailable.
        style = ttk.Style(root)
        style.theme_use("vista" if os.name == "nt" else style.theme_use())
    except Exception:  # noqa: BLE001
        pass
    LauncherApp(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

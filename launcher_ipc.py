"""Shared IPC protocol for launcher daemon <-> GUI communication."""

from __future__ import annotations

import asyncio
import json
import os
import socket
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

# ─────────────────────────────────────────────────────────────────────────────
# Protocol Constants
# ─────────────────────────────────────────────────────────────────────────────

DEFAULT_SOCKET_PATH = str(Path.home() / ".arcade" / "launcher" / "daemon.sock")
WINDOWS_PIPE_NAME = r"\\.\pipe\arcade_launcher"

COMMANDS = {
    "START",
    "STOP",
    "STATUS",
    "GET_LOGS",
    "GET_CONFIG",
    "INSTALL_SERVICE",
    "UNINSTALL_SERVICE",
    "SERVICE_INSTALLED",
}

# ─────────────────────────────────────────────────────────────────────────────
# Wire Encoding
# ─────────────────────────────────────────────────────────────────────────────


def encode_request(req: dict[str, Any]) -> str:
    """Encode a request dict as JSON Lines (single line + newline)."""
    required = {"id", "cmd", "payload"}
    if not required.issubset(req.keys()):
        raise ValueError(f"Request missing required keys: {required - req.keys()}")
    if req["cmd"] not in COMMANDS:
        raise ValueError(f"Unknown command: {req['cmd']}")
    return json.dumps(req, separators=(",", ":")) + "\n"


def decode_response(line: str) -> dict[str, Any]:
    """Decode a JSON Lines response."""
    resp = json.loads(line.strip())
    required = {"id", "ok"}
    if not required.issubset(resp.keys()):
        raise ValueError(f"Response missing required keys: {required - resp.keys()}")
    return resp


# ─────────────────────────────────────────────────────────────────────────────
# Server (Daemon Side) — asyncio Unix socket / Windows named pipe
# ─────────────────────────────────────────────────────────────────────────────


class DaemonIPCServer:
    """Asyncio-based IPC server for the launcher daemon."""

    def __init__(self, socket_path: str | None = None):
        self.socket_path = socket_path or self._default_socket_path()
        self._server: asyncio.AbstractServer | None = None
        self._windows_pipe_handle = None

    def _default_socket_path(self) -> str:
        if sys.platform == "win32":
            return WINDOWS_PIPE_NAME
        return DEFAULT_SOCKET_PATH

    async def run(self, handler: Callable[[str, dict], Any]) -> None:
        """Run the server. `handler(cmd, payload)` must return a result dict."""
        if sys.platform == "win32":
            await self._run_windows_pipe(handler)
        else:
            await self._run_unix_socket(handler)

    async def _run_unix_socket(self, handler):
        # Ensure directory exists
        Path(self.socket_path).parent.mkdir(parents=True, exist_ok=True)
        # Remove stale socket
        try:
            os.unlink(self.socket_path)
        except FileNotFoundError:
            pass

        self._server = await asyncio.start_unix_server(
            self._client_connected(handler),
            path=self.socket_path,
        )

        async with self._server:
            await self._server.serve_forever()

    async def _run_windows_pipe(self, handler):
        # Windows named pipe server using asyncio + win32file
        try:
            import win32file
            import win32pipe
        except ImportError as err:
            raise RuntimeError(
                "pywin32 required for Windows named pipe support"
            ) from err

        # Windows pipe name must be in format \\.\pipe\name
        pipe_name = self.socket_path
        if not pipe_name.startswith("\\\\.\\pipe\\"):
            pipe_name = "\\\\.\\pipe\\" + pipe_name

        async def pipe_loop():
            while True:
                handle = win32pipe.CreateNamedPipe(
                    pipe_name,
                    win32pipe.PIPE_ACCESS_DUPLEX,
                    win32pipe.PIPE_TYPE_MESSAGE
                    | win32pipe.PIPE_READMODE_MESSAGE
                    | win32pipe.PIPE_WAIT,
                    win32pipe.PIPE_UNLIMITED_INSTANCES,
                    65536,
                    65536,
                    0,
                    None,
                )
                try:
                    await asyncio.get_event_loop().run_in_executor(
                        None, win32pipe.ConnectNamedPipe, handle, None
                    )
                    await self._handle_pipe_client(handle, handler)
                finally:
                    win32file.CloseHandle(handle)

        await pipe_loop()

    async def _handle_pipe_client(self, handle, handler):
        import win32file

        loop = asyncio.get_event_loop()
        while True:
            try:
                # Read message
                result, data = await loop.run_in_executor(
                    None, win32file.ReadFile, handle, 65536
                )
                if not data:
                    break
                request = json.loads(data.decode().strip())
                resp = await self._process_request(request, handler)
                await loop.run_in_executor(
                    None,
                    win32file.WriteFile,
                    handle,
                    (json.dumps(resp, separators=(",", ":")) + "\n").encode(),
                )
            except Exception:
                break

    async def _client_connected(
        self, handler, reader: asyncio.StreamReader, writer: asyncio.StreamWriter
    ):
        while True:
            line = await reader.readline()
            if not line:
                break
            try:
                request = json.loads(line.decode().strip())
                resp = await self._process_request(request, handler)
                writer.write((json.dumps(resp, separators=(",", ":")) + "\n").encode())
                await writer.drain()
            except Exception as e:
                writer.write(
                    (
                        json.dumps(
                            {"id": request.get("id", 0), "ok": False, "error": str(e)}
                        )
                        + "\n"
                    ).encode()
                )
                await writer.drain()
                break
        writer.close()
        await writer.wait_closed()

    async def _process_request(self, request: dict, handler) -> dict:
        req_id = request.get("id", 0)
        cmd = request.get("cmd")
        payload = request.get("payload", {})
        try:
            if cmd not in COMMANDS:
                return {"id": req_id, "ok": False, "error": f"Unknown command: {cmd}"}
            result = await handler(cmd, payload)
            return {"id": req_id, "ok": True, "result": result}
        except Exception as e:
            return {"id": req_id, "ok": False, "error": str(e)}


# ─────────────────────────────────────────────────────────────────────────────
# Client (Launcher Side) — synchronous request/response
# ─────────────────────────────────────────────────────────────────────────────


class LauncherIPCClient:
    """Synchronous IPC client for the launcher GUI."""

    def __init__(self, socket_path: str | None = None, timeout: float = 5.0):
        self.socket_path = socket_path or (
            WINDOWS_PIPE_NAME if sys.platform == "win32" else DEFAULT_SOCKET_PATH
        )
        self.timeout = timeout
        self._request_id = 0

    def request(self, cmd: str, payload: dict) -> dict:
        """Send request, return result dict. Raises on error."""
        self._request_id += 1
        req = {"id": self._request_id, "cmd": cmd, "payload": payload}

        # Use Unix socket for paths that look like Unix socket paths
        # (contain / but not \\.\pipe). Otherwise use Windows named pipe.
        if sys.platform == "win32" and self.socket_path.startswith(r"\\.\pipe"):
            return self._request_windows(req)
        return self._request_unix(req)

    def _request_unix(self, req: dict) -> dict:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)
        sock.connect(self.socket_path)
        try:
            sock.sendall(encode_request(req).encode())
            # Read response line
            data = b""
            while not data.endswith(b"\n"):
                chunk = sock.recv(4096)
                if not chunk:
                    raise ConnectionError("Daemon closed connection")
                data += chunk
            resp = decode_response(data.decode())
            if not resp["ok"]:
                raise RuntimeError(resp.get("error", "Unknown error"))
            return resp["result"]
        finally:
            sock.close()

    def _request_windows(self, req: dict) -> dict:
        try:
            import win32file
        except ImportError as err:
            raise RuntimeError(
                "pywin32 required for Windows named pipe support"
            ) from err

        handle = win32file.CreateFile(
            self.socket_path,
            win32file.GENERIC_READ | win32file.GENERIC_WRITE,
            0,
            None,
            win32file.OPEN_EXISTING,
            0,
            None,
        )
        try:
            win32file.WriteFile(handle, encode_request(req).encode())
            result, data = win32file.ReadFile(handle, 65536)
            resp = decode_response(data.decode())
            if not resp["ok"]:
                raise RuntimeError(resp.get("error", "Unknown error"))
            return resp["result"]
        finally:
            win32file.CloseHandle(handle)

    def start_server(self, host: str, port: int) -> dict:
        return self.request("START", {"host": host, "port": port})

    def stop_server(self) -> dict:
        return self.request("STOP", {})

    def get_status(self) -> dict:
        return self.request("STATUS", {})

    def get_logs(self, lines: int = 200) -> dict:
        return self.request("GET_LOGS", {"lines": lines})

    def get_config(self) -> dict:
        return self.request("GET_CONFIG", {})

    def install_service(self) -> dict:
        return self.request("INSTALL_SERVICE", {})

    def uninstall_service(self) -> dict:
        return self.request("UNINSTALL_SERVICE", {})

    def is_service_installed(self) -> dict:
        return self.request("SERVICE_INSTALLED", {})

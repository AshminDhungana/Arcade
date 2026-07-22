# tests/test_launcher_ipc.py
import asyncio
import json
import sys
import tempfile
from pathlib import Path

import pytest

from launcher_ipc import (
    DaemonIPCServer,
    LauncherIPCClient,
    decode_response,
    encode_request,
)


def test_encode_decode_roundtrip():
    req = {"id": 1, "cmd": "STATUS", "payload": {}}
    line = encode_request(req)
    assert line.endswith("\n")
    parsed = json.loads(line.strip())
    assert parsed == req


def test_decode_response():
    line = '{"id": 1, "ok": true, "result": {"status": "running"}}\n'
    resp = decode_response(line)
    assert resp["ok"] is True
    assert resp["result"]["status"] == "running"


@pytest.mark.asyncio
async def test_ipc_server_client_local():
    # Skip on Windows since Unix sockets and pywin32 may not be available in test env
    if sys.platform == "win32":
        import pytest

        pytest.skip(
            "Unix socket test skipped on Windows (requires pywin32 for named pipe)"
        )

    with tempfile.TemporaryDirectory() as d:
        sock = str(Path(d) / "test.sock")

        server = DaemonIPCServer(sock)
        received = []

        async def handler(cmd, payload):
            received.append((cmd, payload))
            return {"status": "ok"}

        server_task = asyncio.create_task(server.run(handler))
        await asyncio.sleep(0.1)  # let server start

        client = LauncherIPCClient(sock)
        result = client.request("STATUS", {"foo": "bar"})

        server_task.cancel()
        try:
            await server_task
        except asyncio.CancelledError:
            pass

        assert result == {"status": "ok"}
        assert received == [("STATUS", {"foo": "bar"})]

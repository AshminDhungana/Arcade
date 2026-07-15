"""LAN discovery: server advertises itself so agents need no typed URL."""

from __future__ import annotations

import asyncio
import json
import socket
from typing import Any

from backend.core.config import get_config

_BEACON_PORT = 48123
_BEACON_MAGIC = b"ARCADE_DISCOVERY"
_interval_task: asyncio.Task[None] | None = None


def discovery_payload() -> dict[str, Any]:
    cfg = get_config()
    return {"host": cfg.host, "port": cfg.port, "cafe_name": cfg.cafe_name}


async def _beacon_loop() -> None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.setblocking(False)
    payload = _BEACON_MAGIC + b"|" + json.dumps(discovery_payload()).encode()
    while True:
        try:
            sock.sendto(payload, ("<broadcast>", _BEACON_PORT))
        except OSError:
            pass
        await asyncio.sleep(3)


def start_discovery_beacon() -> None:
    global _interval_task
    if _interval_task is None or _interval_task.done():
        _interval_task = asyncio.create_task(_beacon_loop())


def stop_discovery_beacon() -> None:
    global _interval_task
    if _interval_task is not None:
        _interval_task.cancel()
        _interval_task = None

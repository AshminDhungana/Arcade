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

_lan_ip_cache: str | None = None


def _detect_lan_ip() -> str:
    """Detect the server's actual LAN IP address.

    Uses a UDP socket connected to a public IP (8.8.8.8) to determine
    which local interface would be used for outbound traffic.
    """
    global _lan_ip_cache
    if _lan_ip_cache:
        return _lan_ip_cache

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            ip: str = s.getsockname()[0]
            _lan_ip_cache = ip
            return ip
    except Exception:
        # Fallback to localhost if detection fails
        _lan_ip_cache = "127.0.0.1"
        return _lan_ip_cache


def _resolve_advertised_host(cfg_host: str) -> str:
    """Resolve the host to advertise in discovery.

    If the config host is a bind address (0.0.0.0 or ::), return the detected LAN IP.
    Otherwise return the configured host as-is.
    """
    if cfg_host in ("0.0.0.0", "::"):  # noqa: S104  # nosec B104 - comparing, not binding
        return _detect_lan_ip()
    return cfg_host


def discovery_payload() -> dict[str, Any]:
    cfg = get_config()
    return {
        "host": _resolve_advertised_host(cfg.host),
        "port": cfg.port,
        "cafe_name": cfg.cafe_name,
    }


async def _beacon_loop() -> None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.setblocking(False)
    payload = _BEACON_MAGIC + b"|" + json.dumps(discovery_payload()).encode()
    # Also send on loopback for same-machine discovery (agent on same host)
    loopback_addr = ("127.0.0.1", _BEACON_PORT)
    while True:
        try:
            sock.sendto(payload, ("<broadcast>", _BEACON_PORT))
            sock.sendto(payload, loopback_addr)
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

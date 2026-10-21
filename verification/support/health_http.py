"""A bare HTTP/1.1 call to an engine's health server, for checks that run on the engine's own event loop."""

from __future__ import annotations

import asyncio
import json
from typing import Any

# A probe that hangs fails the test instead of the whole run.
TIMEOUT_SECONDS = 10


async def health_request(host: str, port: int, method: str, path: str) -> tuple[int, Any]:
    """Send one request and return `(status code, body)`. The body is parsed JSON, or text when it is not JSON."""
    return await asyncio.wait_for(_request(host, port, method, path), TIMEOUT_SECONDS)


async def _request(host: str, port: int, method: str, path: str) -> tuple[int, Any]:
    reader, writer = await asyncio.open_connection(host, port)
    request = f"{method} {path} HTTP/1.1\r\nHost: {host}\r\nContent-Length: 0\r\nConnection: close\r\n\r\n"
    writer.write(request.encode())
    await writer.drain()
    raw = await reader.read()
    writer.close()
    await writer.wait_closed()
    head, _, body = raw.partition(b"\r\n\r\n")
    status = head.split()
    if len(status) < 2:
        raise AssertionError(f"{method} {path}: no HTTP status line in {raw[:200]!r}")
    try:
        return int(status[1]), json.loads(body)
    except ValueError:
        return int(status[1]), body.decode("utf-8", errors="replace")

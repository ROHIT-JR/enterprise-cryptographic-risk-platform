"""In-process pub/sub for streaming live scan progress over SSE.

Single-process, in-memory only - the same pattern the benchmarks endpoint
already uses for its run lock and latest-results cache. This is correct for
one backend replica; a multi-replica deployment would need Redis pub/sub or
similar instead of a module-level dict.
"""

from __future__ import annotations

import asyncio
import contextlib
import time
from typing import Any

_MAX_QUEUE_SIZE = 500
_subscribers: dict[str, list[asyncio.Queue[dict[str, Any]]]] = {}


def subscribe(scan_id: str) -> asyncio.Queue[dict[str, Any]]:
    queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue(maxsize=_MAX_QUEUE_SIZE)
    _subscribers.setdefault(scan_id, []).append(queue)
    return queue


def unsubscribe(scan_id: str, queue: asyncio.Queue[dict[str, Any]]) -> None:
    subscribers = _subscribers.get(scan_id)
    if not subscribers:
        return
    if queue in subscribers:
        subscribers.remove(queue)
    if not subscribers:
        _subscribers.pop(scan_id, None)


def publish(scan_id: str, event: dict[str, Any]) -> None:
    """Fan out an event to every subscriber of ``scan_id``.

    Best-effort: if a subscriber's queue is full (a slow or abandoned
    client), the event is dropped for that subscriber rather than blocking
    the scan itself.
    """
    payload = {**event, "ts": time.time()}
    for queue in list(_subscribers.get(scan_id, [])):
        with contextlib.suppress(asyncio.QueueFull):
            queue.put_nowait(payload)

from __future__ import annotations

import time
from collections import deque
from threading import Lock

from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Bounded per-process request limiter; production proxy adds a shared outer limit."""

    def __init__(self, app, *, requests_per_minute: int = 120) -> None:
        super().__init__(app)
        self.limit = max(requests_per_minute, 1)
        self.max_clients = 10_000
        self.requests: dict[str, deque[float]] = {}
        # Starlette's TestClient and multi-loop ASGI servers may execute this
        # middleware on different event loops. A process-local mutex keeps the
        # very small bucket update atomic without binding it to one loop.
        self.lock = Lock()

    async def dispatch(self, request: Request, call_next):
        if request.url.path in {"/health", "/health/full"}:
            return await call_next(request)
        client = request.client.host if request.client else "unknown"
        now = time.monotonic()
        with self.lock:
            if client not in self.requests and len(self.requests) >= self.max_clients:
                expired = [
                    key
                    for key, values in self.requests.items()
                    if not values or values[-1] <= now - 60
                ]
                for key in expired:
                    self.requests.pop(key, None)
                if len(self.requests) >= self.max_clients:
                    oldest = min(self.requests, key=lambda key: self.requests[key][-1])
                    self.requests.pop(oldest, None)
            bucket = self.requests.setdefault(client, deque())
            while bucket and bucket[0] <= now - 60:
                bucket.popleft()
            if len(bucket) >= self.limit:
                retry_after = max(1, round(60 - (now - bucket[0])))
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Rate limit exceeded"},
                    headers={"Retry-After": str(retry_after)},
                )
            bucket.append(now)
        return await call_next(request)

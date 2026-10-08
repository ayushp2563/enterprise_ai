"""Request IDs, timing, and bounded in-memory abuse protection."""

import hashlib
import logging
import threading
import time
from collections import defaultdict, deque
from uuid import uuid4

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


logger = logging.getLogger(__name__)


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid4())
        request.state.request_id = request_id
        started = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "request_completed",
            extra={
                "request_id": request_id,
                "duration_ms": duration_ms,
            },
        )
        return response


class InMemoryRateLimitMiddleware(BaseHTTPMiddleware):
    """Per-process rate limit suitable for a portfolio deployment.

    A shared gateway-backed limiter is required when running multiple replicas.
    """

    def __init__(self, app, requests_per_minute: int):
        super().__init__(app)
        self.limit = requests_per_minute
        self.events = defaultdict(deque)
        self.lock = threading.Lock()

    def _key(self, request: Request) -> str:
        authorization = request.headers.get("Authorization", "")
        if authorization:
            return hashlib.sha256(authorization.encode()).hexdigest()
        return request.client.host if request.client else "unknown"

    async def dispatch(self, request: Request, call_next):
        if request.url.path in {"/health", "/ready"}:
            return await call_next(request)

        now = time.monotonic()
        key = self._key(request)
        with self.lock:
            events = self.events[key]
            while events and events[0] <= now - 60:
                events.popleft()
            if len(events) >= self.limit:
                return JSONResponse(
                    status_code=429,
                    content={"detail": "Rate limit exceeded"},
                    headers={"Retry-After": "60"},
                )
            events.append(now)
        return await call_next(request)

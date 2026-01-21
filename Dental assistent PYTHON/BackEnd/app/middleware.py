import logging
import asyncio
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import PlainTextResponse

logger = logging.getLogger("dental_assistant.middleware")


class MaxRequestSizeMiddleware(BaseHTTPMiddleware):
    """
    MVP: Reject requests with Content-Length > max_bytes.

    Note:
    - This only catches requests that *include* Content-Length.
    - Upload endpoints must still enforce a streaming cap while reading the body
      (we do that in api/transcribe.py).
    """
    def __init__(self, app, max_bytes: int = 10 * 1024 * 1024):
        super().__init__(app)
        self.max_bytes = max_bytes

    async def dispatch(self, request: Request, call_next):
        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                if int(content_length) > self.max_bytes:
                    logger.warning(
                        "Request blocked: content-length %s > max %s",
                        content_length,
                        self.max_bytes,
                    )
                    return PlainTextResponse("Request entity too large", status_code=413)
            except ValueError:
                logger.warning("Malformed content-length header: %s", content_length)
                return PlainTextResponse("Bad Request", status_code=400)

        return await call_next(request)


class SimpleRateLimitMiddleware(BaseHTTPMiddleware):
    """
    Thread-safe rate limiting middleware (optional, disabled by default).

    Kept for compatibility but disabled unless ENABLE_DEV_RATE_LIMIT=1.
    Uses asyncio.Lock for thread-safe dictionary access.
    """
    def __init__(self, app, *args, **kwargs):
        super().__init__(app)
        self.enabled = False
        try:
            import os
            self.enabled = os.getenv("ENABLE_DEV_RATE_LIMIT") == "1"
        except Exception:
            self.enabled = False

        # If disabled, we don't allocate state.
        if self.enabled:
            import time
            self._time = time
            self.max_requests = kwargs.get("max_requests", 60)
            self.window_seconds = kwargs.get("window_seconds", 60)
            self.clients = {}  # ip -> (count, window_start)
            self._lock = asyncio.Lock()  # Protect dictionary access
            self._last_cleanup = time.time()
            self._cleanup_interval = 300  # Cleanup every 5 minutes instead of clearing all

    async def dispatch(self, request: Request, call_next):
        if not self.enabled:
            return await call_next(request)

        client_host = request.client.host if request.client else "unknown"
        now = self._time.time()

        # Thread-safe access to clients dictionary
        async with self._lock:
            count, start = self.clients.get(client_host, (0, now))

            # Reset window if expired
            if now - start > self.window_seconds:
                count, start = 0, now

            count += 1
            self.clients[client_host] = (count, start)

            # Check if rate limit exceeded
            if count > self.max_requests:
                logger.warning("Rate limit exceeded for %s", client_host)
                return PlainTextResponse("Too Many Requests", status_code=429)

            # Periodic cleanup of expired entries (not all at once)
            if now - self._last_cleanup > self._cleanup_interval:
                self._cleanup_expired_entries(now)
                self._last_cleanup = now

        return await call_next(request)

    def _cleanup_expired_entries(self, now: float):
        """Remove expired rate limit entries to prevent unbounded growth."""
        expired = [
            ip for ip, (_, start) in self.clients.items()
            if now - start > self.window_seconds
        ]
        for ip in expired:
            del self.clients[ip]
        if expired:
            logger.debug("Cleaned up %d expired rate limit entries", len(expired))

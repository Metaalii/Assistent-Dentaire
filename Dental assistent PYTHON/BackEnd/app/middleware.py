import logging
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
    Deprecated for MVP.

    Kept only so older imports don't break, but it does nothing unless enabled.
    If you *really* want it for dev, set ENABLE_DEV_RATE_LIMIT=1.
    """
    def __init__(self, app, *args, **kwargs):
        super().__init__(app)
        self.enabled = False
        try:
            import os
            self.enabled = os.getenv("ENABLE_DEV_RATE_LIMIT") == "1"
        except Exception:
            self.enabled = False

        # If disabled, we don’t allocate state.
        if self.enabled:
            import time
            self._time = time
            self.max_requests = kwargs.get("max_requests", 60)
            self.window_seconds = kwargs.get("window_seconds", 60)
            self.clients = {}  # ip -> (count, window_start)

    async def dispatch(self, request: Request, call_next):
        if not self.enabled:
            return await call_next(request)

        client_host = request.client.host if request.client else "unknown"
        now = self._time.time()
        count, start = self.clients.get(client_host, (0, now))

        if now - start > self.window_seconds:
            count, start = 0, now

        count += 1
        self.clients[client_host] = (count, start)

        if count > self.max_requests:
            logger.warning("Rate limit exceeded for %s", client_host)
            return PlainTextResponse("Too Many Requests", status_code=429)

        # MVP: prevent unbounded growth (very simple pruning)
        if len(self.clients) > 5000:
            self.clients.clear()

        return await call_next(request)

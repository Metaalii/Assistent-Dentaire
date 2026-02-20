"""
Request-size and rate-limiting middleware.

MaxRequestSizeMiddleware   — reject oversized payloads early.
RateLimitMiddleware        — tiered, sliding-window rate limiter (enabled by default).
"""

import logging
import os
import time
from collections import deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import PlainTextResponse, Response

logger = logging.getLogger("dental_assistant.middleware")


# ---------------------------------------------------------------------------
# MaxRequestSizeMiddleware (unchanged)
# ---------------------------------------------------------------------------

class MaxRequestSizeMiddleware(BaseHTTPMiddleware):
    """
    Reject requests with Content-Length > max_bytes.

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


# ---------------------------------------------------------------------------
# Tiered rate-limit configuration
# ---------------------------------------------------------------------------

# Tier definitions: (requests, window_seconds)
# Smaller window = burstier but recovers faster; larger window = smoother.

_TIER_HEAVY = "heavy"       # LLM inference, transcription — expensive
_TIER_MODERATE = "moderate"  # RAG search, consultation save — moderate cost
_TIER_LIGHT = "light"        # health, status, setup checks  — cheap

_DEFAULT_LIMITS: dict[str, tuple[int, int]] = {
    _TIER_HEAVY: (6, 60),       # 6 requests / 60s  (inference is slow anyway)
    _TIER_MODERATE: (30, 60),    # 30 requests / 60s
    _TIER_LIGHT: (120, 60),      # 120 requests / 60s
}

# Path prefix → tier mapping.  Longest-prefix match wins.
# Order doesn't matter — the lookup function handles specificity.
_PATH_TIERS: list[tuple[str, str]] = [
    # Heavy — LLM / Whisper
    ("/summarize-stream-rag", _TIER_HEAVY),
    ("/summarize-stream", _TIER_HEAVY),
    ("/summarize-rag", _TIER_HEAVY),
    ("/summarize", _TIER_HEAVY),
    ("/transcribe", _TIER_HEAVY),
    # Moderate — RAG retrieval, consultation writes, model downloads
    ("/consultations/", _TIER_MODERATE),
    ("/rag/", _TIER_MODERATE),
    ("/setup/download", _TIER_MODERATE),
    # Everything else falls to light (health, setup/check, llm/status, etc.)
]


def _classify(path: str) -> str:
    """Return the rate-limit tier for a given request path."""
    best_match = ""
    best_tier = _TIER_LIGHT
    for prefix, tier in _PATH_TIERS:
        if path.startswith(prefix) and len(prefix) > len(best_match):
            best_match = prefix
            best_tier = tier
    return best_tier


# ---------------------------------------------------------------------------
# Sliding-window bucket
# ---------------------------------------------------------------------------

class _SlidingWindow:
    """Per-client, per-tier sliding-window counter."""

    __slots__ = ("_timestamps", "_max_requests", "_window")

    def __init__(self, max_requests: int, window_seconds: int):
        self._timestamps: deque[float] = deque()
        self._max_requests = max_requests
        self._window = window_seconds

    def allow(self, now: float) -> tuple[bool, int, float]:
        """
        Record a request and return (allowed, remaining, retry_after).

        Returns:
            allowed: True if within limit
            remaining: how many requests left in the window
            retry_after: seconds until a slot frees (0.0 if allowed)
        """
        cutoff = now - self._window
        # Evict expired timestamps
        while self._timestamps and self._timestamps[0] <= cutoff:
            self._timestamps.popleft()

        if len(self._timestamps) >= self._max_requests:
            retry_after = self._timestamps[0] + self._window - now
            return False, 0, max(retry_after, 0.1)

        self._timestamps.append(now)
        remaining = self._max_requests - len(self._timestamps)
        return True, remaining, 0.0


# ---------------------------------------------------------------------------
# RateLimitMiddleware
# ---------------------------------------------------------------------------

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Production-ready, tiered, sliding-window rate limiter.

    Enabled by default.  Disable with RATE_LIMIT_ENABLED=0.
    Override per-tier limits with env vars:
        RATE_LIMIT_HEAVY=10/60    (requests/window_seconds)
        RATE_LIMIT_MODERATE=60/60
        RATE_LIMIT_LIGHT=200/60

    Sets standard rate-limit response headers:
        X-RateLimit-Limit, X-RateLimit-Remaining, Retry-After (on 429).
    """

    def __init__(self, app):
        super().__init__(app)
        self.enabled = os.getenv("RATE_LIMIT_ENABLED", "1") != "0"
        self._limits = dict(_DEFAULT_LIMITS)
        self._buckets: dict[str, _SlidingWindow] = {}   # key = "ip:tier"
        self._last_cleanup = time.monotonic()
        self._cleanup_interval = 300  # 5 minutes

        # Allow env-var overrides per tier
        for tier in (_TIER_HEAVY, _TIER_MODERATE, _TIER_LIGHT):
            env_val = os.getenv(f"RATE_LIMIT_{tier.upper()}")
            if env_val:
                try:
                    reqs, window = env_val.split("/")
                    self._limits[tier] = (int(reqs), int(window))
                    logger.info("Rate limit override: %s = %s/%ss", tier, reqs, window)
                except (ValueError, TypeError):
                    logger.warning("Invalid RATE_LIMIT_%s value: %s (expected N/S)", tier.upper(), env_val)

        if self.enabled:
            logger.info(
                "Rate limiting enabled — heavy=%s/%ss, moderate=%s/%ss, light=%s/%ss",
                *self._limits[_TIER_HEAVY],
                *self._limits[_TIER_MODERATE],
                *self._limits[_TIER_LIGHT],
            )
        else:
            logger.info("Rate limiting disabled via RATE_LIMIT_ENABLED=0")

    def _get_bucket(self, key: str, tier: str) -> _SlidingWindow:
        bucket = self._buckets.get(key)
        if bucket is None:
            max_req, window = self._limits[tier]
            bucket = _SlidingWindow(max_req, window)
            self._buckets[key] = bucket
        return bucket

    def _cleanup(self, now: float) -> None:
        """Remove buckets that have been idle for more than 2x their window."""
        stale = []
        for key, bucket in self._buckets.items():
            if bucket._timestamps and (now - bucket._timestamps[-1]) > bucket._window * 2:
                stale.append(key)
            elif not bucket._timestamps:
                stale.append(key)
        for key in stale:
            del self._buckets[key]
        if stale:
            logger.debug("Cleaned up %d idle rate-limit buckets", len(stale))

    async def dispatch(self, request: Request, call_next) -> Response:
        if not self.enabled:
            return await call_next(request)

        # Skip pre-flight CORS
        if request.method == "OPTIONS":
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        tier = _classify(request.url.path)
        key = f"{client_ip}:{tier}"
        now = time.monotonic()

        # Periodic cleanup
        if now - self._last_cleanup > self._cleanup_interval:
            self._cleanup(now)
            self._last_cleanup = now

        bucket = self._get_bucket(key, tier)
        allowed, remaining, retry_after = bucket.allow(now)

        if not allowed:
            max_req, _ = self._limits[tier]
            logger.warning(
                "Rate limit exceeded: %s on %s (tier=%s, limit=%d)",
                client_ip, request.url.path, tier, max_req,
            )
            return PlainTextResponse(
                "Too Many Requests",
                status_code=429,
                headers={
                    "Retry-After": str(int(retry_after) + 1),
                    "X-RateLimit-Limit": str(max_req),
                    "X-RateLimit-Remaining": "0",
                },
            )

        response = await call_next(request)
        max_req, _ = self._limits[tier]
        response.headers["X-RateLimit-Limit"] = str(max_req)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response

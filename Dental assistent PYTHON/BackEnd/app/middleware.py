"""
Request-size and rate-limiting middleware.

MaxRequestSizeMiddleware   — reject oversized payloads early.
RateLimitMiddleware        — tiered, sliding-window rate limiter backed by
                             SQLite so it works correctly across multiple
                             OS processes (e.g. uvicorn --workers N).
"""

import logging
import os
import sqlite3
import threading
import time
from pathlib import Path

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

_TIER_HEAVY = "heavy"        # LLM inference, transcription — expensive
_TIER_MODERATE = "moderate"  # RAG search, consultation save — moderate cost
_TIER_LIGHT = "light"        # health, status, setup checks  — cheap

_DEFAULT_LIMITS: dict[str, tuple[int, int]] = {
    _TIER_HEAVY:    (6,   60),   # 6 requests / 60s  (inference is slow anyway)
    _TIER_MODERATE: (30,  60),   # 30 requests / 60s
    _TIER_LIGHT:    (120, 60),   # 120 requests / 60s
}

# Path prefix → tier mapping.  Longest-prefix match wins.
_PATH_TIERS: list[tuple[str, str]] = [
    # Heavy — LLM / Whisper
    ("/summarize-stream-rag", _TIER_HEAVY),
    ("/summarize-stream",     _TIER_HEAVY),
    ("/summarize-rag",        _TIER_HEAVY),
    ("/summarize",            _TIER_HEAVY),
    ("/transcribe",           _TIER_HEAVY),
    # Moderate — RAG retrieval, consultation writes, model downloads
    ("/consultations/",       _TIER_MODERATE),
    ("/rag/",                 _TIER_MODERATE),
    ("/setup/download",       _TIER_MODERATE),
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
# SQLite-backed sliding-window store
# ---------------------------------------------------------------------------

class _SqliteRateLimitStore:
    """
    Process-safe sliding-window store backed by a SQLite database.

    Why SQLite instead of an in-memory dict:
        The in-memory dict lives inside a single process.  When Uvicorn is
        run with --workers N each worker maintains its own dict, making the
        effective rate limit N × the configured value.  SQLite is a shared
        file on disk — all workers on the same machine read and write the
        same counters.

    Concurrency model:
        WAL journal mode allows multiple concurrent readers.  Writes use
        BEGIN IMMEDIATE, which acquires the write lock upfront and prevents
        two processes from both passing the count check before either has
        recorded its hit.

    Timestamps:
        Uses time.time() (wall clock) rather than time.monotonic() because
        monotonic clocks are per-process and cannot be compared across them.

    Thread safety:
        sqlite3.Connection objects must not be shared across threads.
        A threading.local() pool gives each OS thread its own connection
        while still pointing at the same on-disk database.
    """

    # How often to run a full DELETE sweep to compact old rows (seconds).
    _VACUUM_INTERVAL = 300

    def __init__(self, db_path: Path) -> None:
        self._db_path = db_path
        self._local = threading.local()
        self._last_vacuum = time.time()
        self._vacuum_lock = threading.Lock()
        self._init_schema()

    # ----- connection management -----

    def _conn(self) -> sqlite3.Connection:
        """Return a per-thread SQLite connection, creating it on first use."""
        conn: sqlite3.Connection | None = getattr(self._local, "conn", None)
        if conn is None:
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
            conn = sqlite3.connect(
                str(self._db_path),
                isolation_level=None,   # manual transaction control
                check_same_thread=False,
            )
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            self._local.conn = conn
        return conn

    def _init_schema(self) -> None:
        conn = self._conn()
        conn.execute("BEGIN IMMEDIATE")
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS rate_limit_hits (
                    bucket  TEXT NOT NULL,
                    ts      REAL NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_bucket_ts "
                "ON rate_limit_hits (bucket, ts)"
            )
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise

    # ----- public API -----

    def allow(
        self,
        bucket: str,
        max_requests: int,
        window_seconds: int,
        now: float,
    ) -> tuple[bool, int, float]:
        """
        Atomically check and record a request hit.

        Returns:
            allowed       True if the request is within the limit.
            remaining     How many requests are left in the current window.
            retry_after   Seconds until a slot frees up (0.0 when allowed).
        """
        cutoff = now - window_seconds
        conn = self._conn()

        conn.execute("BEGIN IMMEDIATE")
        try:
            # Evict expired hits for this bucket
            conn.execute(
                "DELETE FROM rate_limit_hits WHERE bucket = ? AND ts <= ?",
                (bucket, cutoff),
            )

            count: int = conn.execute(
                "SELECT COUNT(*) FROM rate_limit_hits WHERE bucket = ?",
                (bucket,),
            ).fetchone()[0]

            if count >= max_requests:
                oldest_ts: float | None = conn.execute(
                    "SELECT ts FROM rate_limit_hits "
                    "WHERE bucket = ? ORDER BY ts ASC LIMIT 1",
                    (bucket,),
                ).fetchone()[0]
                conn.execute("ROLLBACK")
                retry_after = (oldest_ts + window_seconds - now) if oldest_ts else 1.0
                return False, 0, max(retry_after, 0.1)

            conn.execute(
                "INSERT INTO rate_limit_hits (bucket, ts) VALUES (?, ?)",
                (bucket, now),
            )
            conn.execute("COMMIT")
            return True, max_requests - count - 1, 0.0

        except Exception:
            conn.execute("ROLLBACK")
            raise

    def vacuum(self, now: float) -> None:
        """Periodically remove all expired rows across all buckets."""
        if now - self._last_vacuum < self._VACUUM_INTERVAL:
            return
        with self._vacuum_lock:
            if now - self._last_vacuum < self._VACUUM_INTERVAL:
                return
            conn = self._conn()
            conn.execute("BEGIN IMMEDIATE")
            try:
                # Use the longest window to stay conservative
                max_window = max(w for _, w in _DEFAULT_LIMITS.values())
                conn.execute(
                    "DELETE FROM rate_limit_hits WHERE ts <= ?",
                    (now - max_window,),
                )
                conn.execute("COMMIT")
                self._last_vacuum = now
                logger.debug("Rate-limit store: vacuumed expired rows")
            except Exception:
                conn.execute("ROLLBACK")


# ---------------------------------------------------------------------------
# RateLimitMiddleware
# ---------------------------------------------------------------------------

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Tiered, sliding-window rate limiter backed by SQLite.

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

        # Allow env-var overrides per tier
        for tier in (_TIER_HEAVY, _TIER_MODERATE, _TIER_LIGHT):
            env_val = os.getenv(f"RATE_LIMIT_{tier.upper()}")
            if env_val:
                try:
                    reqs, window = env_val.split("/")
                    self._limits[tier] = (int(reqs), int(window))
                    logger.info("Rate limit override: %s = %s/%ss", tier, reqs, window)
                except (ValueError, TypeError):
                    logger.warning(
                        "Invalid RATE_LIMIT_%s value: %s (expected N/S)",
                        tier.upper(), env_val,
                    )

        if self.enabled:
            from app.config import user_data_dir
            db_path = user_data_dir() / "ratelimit.db"
            self._store = _SqliteRateLimitStore(db_path)
            logger.info(
                "Rate limiting enabled (SQLite) — heavy=%s/%ss, moderate=%s/%ss, light=%s/%ss",
                *self._limits[_TIER_HEAVY],
                *self._limits[_TIER_MODERATE],
                *self._limits[_TIER_LIGHT],
            )
        else:
            self._store = None
            logger.info("Rate limiting disabled via RATE_LIMIT_ENABLED=0")

    async def dispatch(self, request: Request, call_next) -> Response:
        if not self.enabled:
            return await call_next(request)

        # Skip pre-flight CORS
        if request.method == "OPTIONS":
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        tier = _classify(request.url.path)
        bucket = f"{client_ip}:{tier}"
        now = time.time()

        # Periodic vacuum of expired rows
        self._store.vacuum(now)

        max_req, window = self._limits[tier]
        allowed, remaining, retry_after = self._store.allow(bucket, max_req, window, now)

        if not allowed:
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
        response.headers["X-RateLimit-Limit"] = str(max_req)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response

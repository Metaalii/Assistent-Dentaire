"""
Lightweight, zero-dependency observability for the Dental Assistant backend.

Provides:
- RequestTracingMiddleware  — assigns X-Request-ID, logs method/path/status/latency,
                              and feeds the in-process MetricsCollector.
- MetricsCollector          — singleton that tracks request counts, latency percentiles,
                              error counts by endpoint, and a ring buffer of recent errors.
- get_metrics()             — snapshot for the GET /metrics endpoint.

No external services required — everything lives in-process.
"""

import bisect
import logging
import os
import time
import uuid
from collections import defaultdict, deque
from dataclasses import dataclass, field
from threading import Lock
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("dental_assistant.observability")

# How many recent errors to keep in the ring buffer
_ERROR_BUFFER_SIZE = int(os.getenv("ERROR_BUFFER_SIZE", "50"))

# Maximum number of latency samples per endpoint (for percentile calculation)
_MAX_LATENCY_SAMPLES = 500


# ---------------------------------------------------------------------------
# MetricsCollector (singleton)
# ---------------------------------------------------------------------------

@dataclass
class _EndpointStats:
    """Per-endpoint aggregated stats."""
    request_count: int = 0
    error_count: int = 0          # status >= 500
    client_error_count: int = 0   # 400 <= status < 500
    total_latency_ms: float = 0.0
    latencies: list[float] = field(default_factory=list)  # sorted samples for percentiles


class MetricsCollector:
    """
    In-process metrics collector.  Thread-safe, singleton.

    Tracks:
    - Per-endpoint: request count, error count, latency percentiles (p50/p95/p99)
    - Global: total requests, uptime, active request count
    - Recent errors: ring buffer with timestamp, path, status, request_id, detail
    """

    _instance = None
    _init_lock = Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._init_lock:
                if cls._instance is None:
                    inst = super().__new__(cls)
                    inst._lock = Lock()
                    inst._endpoints: dict[str, _EndpointStats] = defaultdict(_EndpointStats)
                    inst._recent_errors: deque[dict[str, Any]] = deque(maxlen=_ERROR_BUFFER_SIZE)
                    inst._start_time = time.monotonic()
                    inst._total_requests = 0
                    inst._active_requests = 0
                    cls._instance = inst
        return cls._instance

    # ----- recording -----

    def request_started(self) -> None:
        with self._lock:
            self._active_requests += 1

    def request_finished(
        self,
        path: str,
        method: str,
        status_code: int,
        latency_ms: float,
        request_id: str,
        detail: str = "",
    ) -> None:
        with self._lock:
            self._active_requests = max(0, self._active_requests - 1)
            self._total_requests += 1

            key = f"{method} {path}"
            stats = self._endpoints[key]
            stats.request_count += 1
            stats.total_latency_ms += latency_ms

            # Keep sorted latency samples (capped)
            if len(stats.latencies) < _MAX_LATENCY_SAMPLES:
                bisect.insort(stats.latencies, latency_ms)
            else:
                # Replace a random old sample to keep distribution fresh
                idx = stats.request_count % _MAX_LATENCY_SAMPLES
                stats.latencies[idx] = latency_ms
                stats.latencies.sort()

            if status_code >= 500:
                stats.error_count += 1
                self._recent_errors.append({
                    "timestamp": time.time(),
                    "request_id": request_id,
                    "method": method,
                    "path": path,
                    "status": status_code,
                    "detail": detail[:500],
                })
            elif 400 <= status_code < 500:
                stats.client_error_count += 1

    # ----- querying -----

    def snapshot(self) -> dict[str, Any]:
        """Return a JSON-serialisable metrics snapshot."""
        with self._lock:
            uptime_s = time.monotonic() - self._start_time
            endpoints = {}
            for key, stats in self._endpoints.items():
                endpoints[key] = {
                    "requests": stats.request_count,
                    "errors_5xx": stats.error_count,
                    "errors_4xx": stats.client_error_count,
                    "avg_latency_ms": round(stats.total_latency_ms / stats.request_count, 1) if stats.request_count else 0,
                    **self._percentiles(stats.latencies),
                }

            return {
                "uptime_seconds": round(uptime_s, 1),
                "total_requests": self._total_requests,
                "active_requests": self._active_requests,
                "endpoints": endpoints,
                "recent_errors": list(self._recent_errors),
            }

    @staticmethod
    def _percentiles(sorted_latencies: list[float]) -> dict[str, float]:
        n = len(sorted_latencies)
        if n == 0:
            return {"p50_ms": 0, "p95_ms": 0, "p99_ms": 0}
        return {
            "p50_ms": round(sorted_latencies[n * 50 // 100], 1),
            "p95_ms": round(sorted_latencies[min(n * 95 // 100, n - 1)], 1),
            "p99_ms": round(sorted_latencies[min(n * 99 // 100, n - 1)], 1),
        }


def get_metrics() -> dict[str, Any]:
    """Public helper — returns the current metrics snapshot."""
    return MetricsCollector().snapshot()


# ---------------------------------------------------------------------------
# RequestTracingMiddleware
# ---------------------------------------------------------------------------

class RequestTracingMiddleware(BaseHTTPMiddleware):
    """
    Assigns a unique X-Request-ID to every request (or reuses an incoming one),
    logs structured request/response info, and feeds the MetricsCollector.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # Reuse client-provided ID or generate one
        request_id = request.headers.get("x-request-id") or uuid.uuid4().hex[:12]

        collector = MetricsCollector()
        collector.request_started()

        start = time.monotonic()
        status_code = 500  # default in case call_next raises
        detail = ""

        try:
            response = await call_next(request)
            status_code = response.status_code
            response.headers["X-Request-ID"] = request_id
            return response
        except Exception as exc:
            detail = str(exc)
            raise
        finally:
            latency_ms = (time.monotonic() - start) * 1000
            path = request.url.path
            method = request.method

            # Structured log line
            log_fn = logger.warning if status_code >= 400 else logger.info
            log_fn(
                "%s %s %d %.0fms [%s]",
                method,
                path,
                status_code,
                latency_ms,
                request_id,
            )

            collector.request_finished(
                path=path,
                method=method,
                status_code=status_code,
                latency_ms=latency_ms,
                request_id=request_id,
                detail=detail,
            )

"""
Unified worker pool for CPU/GPU-heavy operations.

Each heavy operation type (whisper, rag) gets a named pool with:
- Bounded concurrency  (asyncio.Semaphore)
- Thread-pool executor (so sync code never blocks the event loop)
- Per-pool metrics      (running, queued, total, errors)

LLM inference keeps its own priority-aware gate (_InferenceGate in local_llm.py)
because it needs priority ordering and cancellation — features the general pool
doesn't need.  Its status is included in the combined /workers/status endpoint.

┌───────────────────────────────────────────────────────────────┐
│  HORIZONTAL SCALING PATH                                      │
│                                                               │
│  Current:  in-process  (asyncio.Semaphore + ThreadPoolExec)   │
│                                                               │
│  To scale out:                                                │
│  1. Replace _Pool.run() internals with Celery task.delay()    │
│  2. Workers become separate processes / containers             │
│  3. Redis or RabbitMQ replaces asyncio.Semaphore              │
│  4. The WorkerPool.run() interface stays identical             │
│                                                               │
│  Endpoints, middleware, and all callers need ZERO changes —   │
│  they keep calling  await worker_pool.run("rag", fn, ...).    │
└───────────────────────────────────────────────────────────────┘
"""

import asyncio
import functools
import logging
import os
import time
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from typing import Any, Callable

logger = logging.getLogger("dental_assistant.worker")


# ---------------------------------------------------------------------------
# Pool defaults (overridable via environment variables)
# ---------------------------------------------------------------------------

_POOL_CONFIGS: dict[str, dict[str, Any]] = {
    "whisper": {
        "concurrency": int(os.getenv("WHISPER_CONCURRENCY", "1")),
        "timeout": 180,
        "description": "Audio transcription (faster-whisper)",
    },
    "rag": {
        "concurrency": int(os.getenv("RAG_CONCURRENCY", "2")),
        "timeout": 60,
        "description": "RAG embedding & retrieval",
    },
}


# ---------------------------------------------------------------------------
# _Pool — a single named, bounded worker pool
# ---------------------------------------------------------------------------

class _Pool:
    """Named pool with a concurrency semaphore and a dedicated thread executor."""

    __slots__ = (
        "name", "concurrency", "timeout", "description",
        "_semaphore", "_executor",
        "_running", "_queued", "_total", "_errors", "_lock",
    )

    def __init__(self, name: str, concurrency: int, timeout: float, description: str):
        self.name = name
        self.concurrency = concurrency
        self.timeout = timeout
        self.description = description
        self._semaphore = asyncio.Semaphore(concurrency)
        self._executor = ThreadPoolExecutor(
            max_workers=max(concurrency, 1),
            thread_name_prefix=f"pool-{name}",
        )
        self._running = 0
        self._queued = 0
        self._total = 0
        self._errors = 0
        self._lock = Lock()

    async def run(self, fn: Callable[..., Any], *args: Any, timeout: float | None = None) -> Any:
        """
        Submit *fn(*args)* to this pool's thread executor, respecting concurrency.

        Raises TimeoutError if the pool is full and the caller waits too long.
        """
        effective_timeout = timeout if timeout is not None else self.timeout

        with self._lock:
            self._queued += 1

        try:
            # Wait for a slot
            await asyncio.wait_for(self._semaphore.acquire(), timeout=effective_timeout)
        except asyncio.TimeoutError:
            with self._lock:
                self._queued -= 1
            raise TimeoutError(
                f"Worker pool '{self.name}' is busy — all {self.concurrency} slot(s) "
                f"occupied for >{effective_timeout}s"
            )

        with self._lock:
            self._queued -= 1
            self._running += 1
            self._total += 1

        try:
            loop = asyncio.get_running_loop()
            return await loop.run_in_executor(self._executor, fn, *args)
        except Exception:
            with self._lock:
                self._errors += 1
            raise
        finally:
            self._semaphore.release()
            with self._lock:
                self._running -= 1

    def status(self) -> dict[str, Any]:
        with self._lock:
            return {
                "description": self.description,
                "concurrency": self.concurrency,
                "running": self._running,
                "queued": self._queued,
                "total_processed": self._total,
                "total_errors": self._errors,
                "is_busy": self._running >= self.concurrency,
            }

    def shutdown(self) -> None:
        self._executor.shutdown(wait=False)


# ---------------------------------------------------------------------------
# WorkerPool — singleton manager for all named pools
# ---------------------------------------------------------------------------

class WorkerPool:
    """
    Singleton that manages named worker pools.

    Usage::

        pool = WorkerPool()
        result = await pool.run("rag", pipeline.get_rag_context, text)
    """

    _instance = None
    _init_lock = Lock()

    def __new__(cls) -> "WorkerPool":
        if cls._instance is None:
            with cls._init_lock:
                if cls._instance is None:
                    inst = super().__new__(cls)
                    inst._pools: dict[str, _Pool] = {}
                    for name, cfg in _POOL_CONFIGS.items():
                        inst._pools[name] = _Pool(
                            name=name,
                            concurrency=cfg["concurrency"],
                            timeout=cfg["timeout"],
                            description=cfg["description"],
                        )
                    logger.info(
                        "WorkerPool ready: %s",
                        ", ".join(
                            f"{n}(concurrency={p.concurrency})"
                            for n, p in inst._pools.items()
                        ),
                    )
                    cls._instance = inst
        return cls._instance

    async def run(
        self,
        pool_name: str,
        fn: Callable[..., Any],
        *args: Any,
        timeout: float | None = None,
    ) -> Any:
        """Run *fn* in the named pool's thread executor."""
        pool = self._pools.get(pool_name)
        if pool is None:
            raise ValueError(f"Unknown worker pool: '{pool_name}'")
        return await pool.run(fn, *args, timeout=timeout)

    def status(self) -> dict[str, dict[str, Any]]:
        """Combined status of every pool (for the /workers/status endpoint)."""
        result: dict[str, Any] = {}
        for name, pool in self._pools.items():
            result[name] = pool.status()

        # Include LLM gate status from its own singleton
        try:
            from app.llm.local_llm import LocalLLM
            llm_status = LocalLLM().get_queue_status()
            result["llm"] = {
                "description": "LLM inference (priority queue)",
                **llm_status,
            }
        except Exception:
            result["llm"] = {"description": "LLM inference (not loaded)"}

        return result

    def shutdown(self) -> None:
        """Shut down all thread executors (call from lifespan teardown)."""
        for pool in self._pools.values():
            pool.shutdown()
        logger.info("WorkerPool shut down")

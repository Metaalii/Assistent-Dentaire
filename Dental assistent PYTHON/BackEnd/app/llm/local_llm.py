import asyncio
import logging
import os
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, AsyncIterator

from fastapi import HTTPException

from app.config import get_llm_model_path, get_hardware_info
from app.llm_config import (
    CONTEXT_LENGTH,
    CPU_THREADS,
    BATCH_SIZES,
    GPU_LAYERS,
    GPU_LAYERS_APPLE_SILICON,
    GENERATION_PARAMS,
    STOP_TOKENS,
    MAX_GENERATION_TOKENS,
    MEMORY_CONFIG,
    CHUNKING_THRESHOLD,
    CHUNK_SIZE_TOKENS,
    CHUNK_SUMMARY_PROMPT,
    COMBINE_SUMMARIES_PROMPT,
)

logger = logging.getLogger("dental_assistant.local_llm")

# ---------------------------------------------------------------------------
# Priority levels — lower value = higher priority
# ---------------------------------------------------------------------------
PRIORITY_INTERACTIVE = 0   # streaming / user-facing
PRIORITY_BATCH = 10        # chunked summarization, background tasks


@dataclass(order=True)
class _QueueEntry:
    """A priority-queue entry that carries an asyncio.Event for notification."""
    priority: int
    seq: int = field(compare=True)          # tie-breaker (FIFO within same priority)
    ready: asyncio.Event = field(compare=False, repr=False, default_factory=asyncio.Event)
    cancel: Optional[threading.Event] = field(compare=False, repr=False, default=None)


class _InferenceGate:
    """
    Priority-aware concurrency gate for LLM inference.

    * ``max_concurrency`` slots can run simultaneously (default 1).
    * Waiters are ordered by (priority, FIFO).
    * Cancelled requests (via ``threading.Event``) are skipped automatically.
    """

    def __init__(self, max_concurrency: int = 1):
        self._max = max_concurrency
        self._running = 0
        self._lock = asyncio.Lock()
        self._seq = 0
        self._waiters: list[_QueueEntry] = []

    async def acquire(
        self,
        priority: int = PRIORITY_INTERACTIVE,
        timeout: float = 300.0,
        cancel: Optional[threading.Event] = None,
    ) -> None:
        async with self._lock:
            if self._running < self._max:
                self._running += 1
                return
            self._seq += 1
            entry = _QueueEntry(priority=priority, seq=self._seq, cancel=cancel)
            self._waiters.append(entry)
            self._waiters.sort()

        # Wait outside the lock
        try:
            await asyncio.wait_for(entry.ready.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            # Remove ourselves from the queue
            async with self._lock:
                if entry in self._waiters:
                    self._waiters.remove(entry)
            raise HTTPException(
                status_code=503,
                detail="Server is busy processing other requests. Please try again later.",
            )

    async def release(self) -> None:
        async with self._lock:
            self._running -= 1
            # Wake the highest-priority non-cancelled waiter
            while self._waiters:
                entry = self._waiters.pop(0)
                # Skip cancelled requests
                if entry.cancel and entry.cancel.is_set():
                    continue
                self._running += 1
                entry.ready.set()
                return

    def status(self) -> dict:
        return {
            "max_concurrency": self._max,
            "running": self._running,
            "waiting": len(self._waiters),
            "is_busy": self._running >= self._max,
        }


class LocalLLM:
    """
    Singleton wrapper around llama-cpp-python with automatic GPU acceleration.

    Features:
    - No heavy imports at module import time
    - Lazy model loading with hardware detection
    - Automatic GPU layer offloading based on detected hardware
    - Priority-aware concurrency gate (configurable via LLM_CONCURRENCY env var)
    - Cancellation support for streaming generation
    - Thread-safe initialization
    - Streaming support for reduced perceived latency
    - Optimized memory configuration
    - Queue status tracking for UX feedback
    """

    _instance: Optional["LocalLLM"] = None
    _instance_lock = threading.Lock()

    DEFAULT_QUEUE_TIMEOUT = 300  # 5 minutes

    def __new__(cls) -> "LocalLLM":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._llm = None
                    cls._instance._load_lock = threading.Lock()
                    max_concurrency = int(os.environ.get("LLM_CONCURRENCY", "1"))
                    cls._instance._gate = _InferenceGate(max_concurrency)
                    cls._instance._hw_profile = None
        return cls._instance

    def get_queue_status(self) -> dict:
        """Get current queue status for UX feedback."""
        return self._gate.status()

    def _ensure_model_file(self) -> Path:
        model_path = get_llm_model_path()
        if not model_path.exists():
            raise HTTPException(
                status_code=503,
                detail=f"LLM model not found at {model_path}. Run setup/download first.",
            )
        return model_path

    def _get_optimized_config(self, hw_info: dict) -> dict:
        """Determine optimized llama.cpp configuration based on hardware."""
        profile = hw_info["profile"]
        is_apple_silicon = hw_info.get("detection_method") == "apple_silicon"

        if hw_info["gpu_detected"] and hw_info["backend_gpu_support"]:
            if is_apple_silicon:
                gpu_layers = GPU_LAYERS_APPLE_SILICON
            else:
                gpu_layers = GPU_LAYERS.get(profile, 0)
        else:
            gpu_layers = 0

        n_batch = BATCH_SIZES.get(profile, 256)

        return {
            "n_ctx": CONTEXT_LENGTH,
            "n_threads": CPU_THREADS,
            "n_gpu_layers": gpu_layers,
            "n_batch": n_batch,
            "use_mlock": MEMORY_CONFIG["use_mlock"],
            "use_mmap": MEMORY_CONFIG["use_mmap"],
            "verbose": False,
        }

    def _load_model_if_needed(self) -> None:
        if self._llm is not None:
            return

        with self._load_lock:
            if self._llm is not None:
                return

            model_path = self._ensure_model_file()

            try:
                from llama_cpp import Llama  # type: ignore
            except Exception as e:
                raise HTTPException(
                    status_code=503,
                    detail="LLM dependency not installed (llama-cpp-python). Install it to enable summarization.",
                ) from e

            hw_info = get_hardware_info()
            self._hw_profile = hw_info["profile"]
            config = self._get_optimized_config(hw_info)

            if config["n_gpu_layers"] > 0:
                logger.info(
                    "Loading LLM with GPU acceleration: %s (%d layers, batch=%d, ctx=%d, threads=%d)",
                    hw_info.get("gpu_name", "GPU"),
                    config["n_gpu_layers"],
                    config["n_batch"],
                    config["n_ctx"],
                    config["n_threads"],
                )
            else:
                logger.info(
                    "Loading LLM in CPU mode (batch=%d, ctx=%d, threads=%d)",
                    config["n_batch"],
                    config["n_ctx"],
                    config["n_threads"],
                )

            self._llm = Llama(model_path=str(model_path), **config)

    def _estimate_tokens(self, text: str) -> int:
        """Rough token estimation: ~3 characters per token for French/multilingual text."""
        return len(text) // 3

    def _chunk_text(self, text: str, max_chunk_tokens: int = CHUNK_SIZE_TOKENS) -> list[str]:
        """Split text into chunks that fit within token limits."""
        max_chars = max_chunk_tokens * 3

        sentences = text.replace('\n', ' ').split('. ')
        chunks = []
        current_chunk = ""

        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            sentence_with_period = sentence + ". "

            if len(current_chunk) + len(sentence_with_period) > max_chars:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                current_chunk = sentence_with_period
            else:
                current_chunk += sentence_with_period

        if current_chunk.strip():
            chunks.append(current_chunk.strip())

        return chunks if chunks else [text]

    # ------------------------------------------------------------------
    # Public generation API
    # ------------------------------------------------------------------

    async def generate(self, prompt: str, timeout: Optional[float] = None) -> str:
        """
        Generate text from the local LLM (batch priority).

        Uses PRIORITY_BATCH so interactive streaming requests take precedence.
        """
        self._load_model_if_needed()
        timeout = timeout or self.DEFAULT_QUEUE_TIMEOUT

        await self._gate.acquire(priority=PRIORITY_BATCH, timeout=timeout)
        try:
            estimated_tokens = self._estimate_tokens(prompt)

            if estimated_tokens > CHUNKING_THRESHOLD:
                logger.info("Long text detected (%d estimated tokens), using chunked summarization", estimated_tokens)
                return await asyncio.to_thread(self._generate_chunked_sync, prompt)
            else:
                return await asyncio.to_thread(self._generate_sync, prompt)
        finally:
            await self._gate.release()

    async def generate_stream(
        self,
        prompt: str,
        timeout: Optional[float] = None,
        cancel_event: Optional[threading.Event] = None,
    ) -> AsyncIterator[str]:
        """
        Stream tokens as they are generated (interactive priority).

        Args:
            prompt: The prompt to generate from
            timeout: Maximum time to wait in queue (default: 5 minutes)
            cancel_event: If set externally, generation stops early
        """
        self._load_model_if_needed()
        timeout = timeout or self.DEFAULT_QUEUE_TIMEOUT

        await self._gate.acquire(
            priority=PRIORITY_INTERACTIVE,
            timeout=timeout,
            cancel=cancel_event,
        )
        try:
            queue: asyncio.Queue[str | None] = asyncio.Queue()
            loop = asyncio.get_running_loop()

            def stream_worker():
                try:
                    for token in self._llm(
                        prompt,
                        max_tokens=MAX_GENERATION_TOKENS,
                        stop=STOP_TOKENS,
                        stream=True,
                        **GENERATION_PARAMS,
                    ):
                        # Check cancellation
                        if cancel_event and cancel_event.is_set():
                            logger.info("Generation cancelled by client")
                            break
                        chunk = token["choices"][0]["text"]
                        loop.call_soon_threadsafe(queue.put_nowait, chunk)
                except Exception as e:
                    logger.exception("Streaming generation error")
                finally:
                    loop.call_soon_threadsafe(queue.put_nowait, None)

            thread = threading.Thread(target=stream_worker, daemon=True)
            thread.start()

            while True:
                chunk = await queue.get()
                if chunk is None:
                    break
                yield chunk
        finally:
            await self._gate.release()

    # ------------------------------------------------------------------
    # Sync helpers (run inside threads)
    # ------------------------------------------------------------------

    def _generate_chunked_sync(self, prompt: str) -> str:
        """Handle long transcriptions by chunking and combining summaries."""
        assert self._llm is not None

        if "Consultation:" in prompt:
            text = prompt.split("Consultation:")[-1].strip()
            if text.endswith("SmartNote:"):
                text = text[:-10].strip()
        elif ":\n" in prompt:
            _, text = prompt.split(":\n", 1)
        else:
            text = prompt

        chunks = self._chunk_text(text)
        logger.info("Split transcription into %d chunks", len(chunks))

        chunk_summaries = []
        for i, chunk in enumerate(chunks):
            chunk_prompt = CHUNK_SUMMARY_PROMPT.format(
                part=i + 1,
                total=len(chunks),
                text=chunk
            )

            result = self._llm(
                chunk_prompt,
                max_tokens=400,
                stop=STOP_TOKENS,
                **GENERATION_PARAMS,
            )

            try:
                summary = result["choices"][0]["text"].strip()
                chunk_summaries.append(summary)
                logger.debug("Chunk %d/%d summarized", i + 1, len(chunks))
            except Exception:
                logger.warning("Failed to summarize chunk %d", i + 1)
                continue

        if len(chunk_summaries) == 1:
            return chunk_summaries[0]

        combined = "\n\n".join(chunk_summaries)
        final_prompt = COMBINE_SUMMARIES_PROMPT.format(summaries=combined)

        result = self._llm(
            final_prompt,
            max_tokens=MAX_GENERATION_TOKENS,
            stop=STOP_TOKENS,
            **GENERATION_PARAMS,
        )

        try:
            return result["choices"][0]["text"].strip()
        except Exception:
            return "\n\n".join(chunk_summaries)

    def _generate_sync(self, prompt: str) -> str:
        assert self._llm is not None

        result = self._llm(
            prompt,
            max_tokens=MAX_GENERATION_TOKENS,
            stop=STOP_TOKENS,
            **GENERATION_PARAMS,
        )

        try:
            return result["choices"][0]["text"].strip()
        except Exception:
            logger.exception("Unexpected LLM output format")
            raise HTTPException(
                status_code=500,
                detail="LLM returned an unexpected response format.",
            )

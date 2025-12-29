from __future__ import annotations

import asyncio
import logging
import threading
from pathlib import Path
from typing import Optional

from fastapi import HTTPException

from app.config import LLM_MODEL_PATH

logger = logging.getLogger("dental_assistant.local_llm")


class LocalLLM:
    """
    MVP singleton wrapper around llama-cpp-python.

    Rules:
    - No heavy imports at module import time
    - Lazy model loading
    - Single in-flight inference at a time
    """

    _instance: Optional["LocalLLM"] = None
    _instance_lock = threading.Lock()

    def __new__(cls) -> "LocalLLM":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._llm = None
                    cls._instance._load_lock = threading.Lock()
                    cls._instance._inference_semaphore = asyncio.Semaphore(1)
        return cls._instance

    def _ensure_model_file(self) -> None:
        model_path = Path(LLM_MODEL_PATH)
        if not model_path.exists():
            raise HTTPException(
                status_code=503,
                detail=f"LLM model not found at {model_path}. Run setup/download first.",
            )

    def _load_model_if_needed(self) -> None:
        if self._llm is not None:
            return

        with self._load_lock:
            if self._llm is not None:
                return

            self._ensure_model_file()

            # Lazy import so backend can start without llama-cpp-python installed
            try:
                from llama_cpp import Llama  # type: ignore
            except Exception as e:
                raise HTTPException(
                    status_code=503,
                    detail="LLM dependency not installed (llama-cpp-python). Install it to enable summarization.",
                ) from e

            logger.info("Loading LLM model from %s ...", LLM_MODEL_PATH)

            # MVP defaults — conservative, stable
            self._llm = Llama(
                model_path=str(LLM_MODEL_PATH),
                n_ctx=4096,
                n_threads=None,  # let llama.cpp decide
                n_gpu_layers=0,  # CPU-only MVP (safe default)
                verbose=False,
            )

    async def generate(self, prompt: str) -> str:
        """
        Generate text from the local LLM.
        Enforces single in-flight inference.
        """
        self._load_model_if_needed()

        async with self._inference_semaphore:
            return await asyncio.to_thread(self._generate_sync, prompt)

    def _generate_sync(self, prompt: str) -> str:
        assert self._llm is not None  # guaranteed by _load_model_if_needed()

        result = self._llm(
            prompt,
            max_tokens=512,
            stop=["</s>"],
        )

        try:
            return result["choices"][0]["text"].strip()
        except Exception:
            logger.exception("Unexpected LLM output format")
            raise HTTPException(
                status_code=500,
                detail="LLM returned an unexpected response format.",
            )

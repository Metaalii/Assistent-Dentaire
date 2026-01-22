import asyncio
import logging
import threading
from pathlib import Path
from typing import Optional

from fastapi import HTTPException

from app.config import get_llm_model_path, get_hardware_info

logger = logging.getLogger("dental_assistant.local_llm")


class LocalLLM:
    """
    Singleton wrapper around llama-cpp-python with automatic GPU acceleration.

    Features:
    - No heavy imports at module import time
    - Lazy model loading with hardware detection
    - Automatic GPU layer offloading based on detected hardware
    - Single in-flight inference at a time
    - Thread-safe initialization
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

    def _ensure_model_file(self) -> Path:
        model_path = get_llm_model_path()
        if not model_path.exists():
            raise HTTPException(
                status_code=503,
                detail=f"LLM model not found at {model_path}. Run setup/download first.",
            )
        return model_path

    def _load_model_if_needed(self) -> None:
        if self._llm is not None:
            return

        with self._load_lock:
            if self._llm is not None:
                return

            model_path = self._ensure_model_file()

            # Lazy import so backend can start without llama-cpp-python installed
            try:
                from llama_cpp import Llama  # type: ignore
            except Exception as e:
                raise HTTPException(
                    status_code=503,
                    detail="LLM dependency not installed (llama-cpp-python). Install it to enable summarization.",
                ) from e

            # Detect hardware and configure GPU acceleration
            hw_info = get_hardware_info()
            profile = hw_info["profile"]

            # Determine optimal GPU layer offloading based on hardware
            gpu_layers = 0
            if hw_info["gpu_detected"] and hw_info["backend_gpu_support"]:
                if profile == "high_vram":
                    gpu_layers = 35  # Offload most layers to GPU (8GB+ VRAM)
                elif profile == "low_vram":
                    gpu_layers = 20  # Offload some layers to GPU (4-8GB VRAM)
                # cpu_only profile stays at 0 layers

                logger.info(
                    "Loading LLM model from %s with GPU acceleration (%s: %d layers)...",
                    model_path,
                    hw_info.get("gpu_name", "GPU"),
                    gpu_layers
                )
            else:
                logger.info("Loading LLM model from %s in CPU mode...", model_path)

            self._llm = Llama(
                model_path=str(model_path),
                n_ctx=4096,
                n_threads=None,  # let llama.cpp decide
                n_gpu_layers=gpu_layers,
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

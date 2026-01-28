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
                n_ctx=8192,  # Increased for longer transcriptions
                n_threads=None,  # let llama.cpp decide
                n_gpu_layers=gpu_layers,
                verbose=False,
            )

    def _estimate_tokens(self, text: str) -> int:
        """Rough token estimation: ~3 characters per token for French/multilingual text."""
        return len(text) // 3

    def _chunk_text(self, text: str, max_chunk_tokens: int = 2500) -> list[str]:
        """Split text into chunks that fit within token limits."""
        max_chars = max_chunk_tokens * 3  # Approximate chars per chunk (conservative for French)

        # Split by sentences to avoid cutting mid-sentence
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

    async def generate(self, prompt: str) -> str:
        """
        Generate text from the local LLM.
        Enforces single in-flight inference.
        Handles long text by chunking if necessary.
        """
        self._load_model_if_needed()

        async with self._inference_semaphore:
            # Check if text is too long and needs chunking
            estimated_tokens = self._estimate_tokens(prompt)

            if estimated_tokens > 6000:  # Leave room for response tokens
                logger.info("Long text detected (%d estimated tokens), using chunked summarization", estimated_tokens)
                return await asyncio.to_thread(self._generate_chunked_sync, prompt)
            else:
                return await asyncio.to_thread(self._generate_sync, prompt)

    def _generate_chunked_sync(self, prompt: str) -> str:
        """Handle long transcriptions by chunking and combining summaries."""
        assert self._llm is not None

        # Extract the actual text content from the prompt
        # Find the transcription text after the prompt header
        if "Transcription de la consultation:" in prompt:
            text = prompt.split("Transcription de la consultation:")[-1].strip()
        elif ":\n" in prompt:
            _, text = prompt.split(":\n", 1)
        else:
            text = prompt

        chunks = self._chunk_text(text)
        logger.info("Split transcription into %d chunks", len(chunks))

        chunk_summaries = []
        for i, chunk in enumerate(chunks):
            chunk_prompt = f"Résume cette partie ({i+1}/{len(chunks)}) d'une consultation dentaire en français:\n{chunk}"

            result = self._llm(
                chunk_prompt,
                max_tokens=500,
                stop=["<|eot_id|>", "<|end_of_text|>"],
            )

            try:
                summary = result["choices"][0]["text"].strip()
                chunk_summaries.append(summary)
                logger.debug("Chunk %d/%d summarized", i+1, len(chunks))
            except Exception:
                logger.warning("Failed to summarize chunk %d", i+1)
                continue

        # Combine chunk summaries into final SmartNote
        if len(chunk_summaries) == 1:
            return chunk_summaries[0]

        combined = "\n\n".join(chunk_summaries)
        final_prompt = f"""Combine ces résumés partiels en une SmartNote dentaire concise (5-10 lignes) en français:

{combined}

Format:
Motif : ...
• Antécédents : ...
• Examen : ...
• Plan de traitement : ...
• Risques : ...
• Recommandations : ...
• Prochaine étape : ...
• Administratif : ..."""

        result = self._llm(
            final_prompt,
            max_tokens=1000,
            stop=["<|eot_id|>", "<|end_of_text|>"],
        )

        try:
            return result["choices"][0]["text"].strip()
        except Exception:
            # If final combination fails, return joined summaries
            return "\n\n".join(chunk_summaries)

    def _generate_sync(self, prompt: str) -> str:
        assert self._llm is not None  # guaranteed by _load_model_if_needed()

        result = self._llm(
            prompt,
            max_tokens=1024,  # Increased for longer French documents
            stop=["<|eot_id|>", "<|end_of_text|>"],
        )

        try:
            return result["choices"][0]["text"].strip()
        except Exception:
            logger.exception("Unexpected LLM output format")
            raise HTTPException(
                status_code=500,
                detail="LLM returned an unexpected response format.",
            )

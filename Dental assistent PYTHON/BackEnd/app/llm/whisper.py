from __future__ import annotations

import asyncio
import logging
import threading
from pathlib import Path
from typing import Optional, Tuple

from fastapi import HTTPException

from app.config import WHISPER_MODEL_PATH, get_device_settings

logger = logging.getLogger("dental_assistant.whisper")


class LocalWhisper:
    """
    MVP singleton wrapper for faster-whisper.

    Key rules:
    - No heavy imports at module import time.
    - Model loads lazily on first use.
    - Thread-safe initialization.
    """

    _instance: Optional["LocalWhisper"] = None
    _instance_lock = threading.Lock()

    def __new__(cls) -> "LocalWhisper":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._model = None
                    cls._instance._model_lock = threading.Lock()
        return cls._instance

    def _ensure_model_dir(self) -> None:
        model_path = Path(WHISPER_MODEL_PATH)
        if not model_path.exists():
            raise HTTPException(
                status_code=503,
                detail=f"Whisper model not found at {model_path}. Run setup/download first.",
            )

    def _load_model_if_needed(self) -> None:
        if self._model is not None:
            return

        with self._model_lock:
            if self._model is not None:
                return

            self._ensure_model_dir()

            # Lazy import so backend can boot without faster-whisper installed.
            try:
                from faster_whisper import WhisperModel  # type: ignore
            except Exception as e:
                raise HTTPException(
                    status_code=503,
                    detail="Whisper dependency not installed (faster-whisper). Install it to enable transcription.",
                ) from e

            device, compute_type = get_device_settings()
            logger.info("Loading Whisper model from %s on %s (%s)...", WHISPER_MODEL_PATH, device, compute_type)

            self._model = WhisperModel(
                str(WHISPER_MODEL_PATH),
                device=device,
                compute_type=compute_type,
            )

    async def transcribe(self, audio_path: str) -> str:
        """
        Runs transcription in a worker thread.
        """
        # Ensure model exists / dependency exists before starting the thread
        self._load_model_if_needed()
        return await asyncio.to_thread(self._transcribe_sync, audio_path)

    def _transcribe_sync(self, audio_path: str) -> str:
        assert self._model is not None  # guaranteed by _load_model_if_needed()
        segments, _ = self._model.transcribe(audio_path)
        return " ".join(segment.text for segment in segments)

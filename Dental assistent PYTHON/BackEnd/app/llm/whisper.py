import asyncio
import logging
import threading
from pathlib import Path
from typing import Optional

from fastapi import HTTPException

from app.config import WHISPER_MODEL_PATH, get_device_settings, get_hardware_info
from app.llm_config import WHISPER_CONFIG, WHISPER_WORKERS, WHISPER_DEFAULT_LANGUAGE

logger = logging.getLogger("dental_assistant.whisper")


class LocalWhisper:
    """
    Optimized singleton wrapper for faster-whisper.

    Key features:
    - No heavy imports at module import time
    - Model loads lazily on first use
    - Thread-safe initialization
    - VAD filtering for faster transcription
    - French language optimization
    - Hardware-aware worker configuration
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
                    cls._instance._hw_profile = None
        return cls._instance

    def _ensure_model_dir(self) -> None:
        """Ensure Whisper model directory exists and contains model files."""
        model_path = Path(WHISPER_MODEL_PATH)
        if not model_path.exists():
            raise HTTPException(
                status_code=503,
                detail=f"Whisper model directory not found at {model_path}. Please download the model first.",
            )

        # Check if model files actually exist (directory could be empty)
        if not any(model_path.iterdir()):
            raise HTTPException(
                status_code=503,
                detail=f"Whisper model directory exists but is empty at {model_path}. Please download the model files.",
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
            hw_info = get_hardware_info()
            self._hw_profile = hw_info["profile"]

            # Get optimal number of workers based on hardware
            num_workers = WHISPER_WORKERS.get(self._hw_profile, 1)

            logger.info(
                "Loading Whisper model from %s (device=%s, compute=%s, workers=%d)",
                WHISPER_MODEL_PATH,
                device,
                compute_type,
                num_workers
            )

            self._model = WhisperModel(
                str(WHISPER_MODEL_PATH),
                device=device,
                compute_type=compute_type,
                num_workers=num_workers,
            )

    async def transcribe(self, audio_path: str, language: Optional[str] = None) -> str:
        """
        Runs transcription in a worker thread.

        Args:
            audio_path: Path to the audio file
            language: Language code (e.g. "fr", "en"). Defaults to WHISPER_DEFAULT_LANGUAGE.
        """
        self._load_model_if_needed()
        lang = language or WHISPER_DEFAULT_LANGUAGE
        return await asyncio.to_thread(self._transcribe_sync, audio_path, lang)

    def _transcribe_sync(self, audio_path: str, language: str = "fr") -> str:
        """
        Synchronous transcription with optimized parameters.

        Optimizations:
        - VAD filtering to skip silence (20-30% faster)
        - Language hint avoids detection overhead
        - condition_on_previous_text=False for speed
        """
        assert self._model is not None  # guaranteed by _load_model_if_needed()

        segments, info = self._model.transcribe(
            audio_path,
            language=language,
            vad_filter=WHISPER_CONFIG["vad_filter"],
            vad_parameters=WHISPER_CONFIG["vad_parameters"],
            condition_on_previous_text=WHISPER_CONFIG["condition_on_previous_text"],
            compression_ratio_threshold=WHISPER_CONFIG["compression_ratio_threshold"],
            log_prob_threshold=WHISPER_CONFIG["log_prob_threshold"],
            no_speech_threshold=WHISPER_CONFIG["no_speech_threshold"],
        )

        logger.debug(
            "Transcription complete: detected=%s (prob=%.2f), requested=%s",
            info.language, info.language_probability, language
        )

        return " ".join(segment.text for segment in segments)

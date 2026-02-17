"""
Health-check endpoint.

GET /health — quick liveness probe used by the Tauri frontend boot sequence.
"""

import logging
from pathlib import Path

from fastapi import APIRouter

from app.config import (
    MODEL_CONFIGS,
    WHISPER_MODEL_PATH,
    analyze_hardware,
    get_llm_model_path,
)

router = APIRouter()
logger = logging.getLogger("dental_assistant.health")


def _is_model_valid(model_path: Path, expected_size_gb: float) -> bool:
    """Check if the model file exists and has a reasonable size."""
    if not model_path.exists():
        return False
    file_size_gb = model_path.stat().st_size / (1024 ** 3)
    min_expected = expected_size_gb * 0.8
    if file_size_gb < min_expected:
        logger.warning(
            "Model file appears incomplete: %.2f GB (expected ~%.1f GB)",
            file_size_gb,
            expected_size_gb,
        )
        return False
    return True


def _is_whisper_valid() -> bool:
    """Check if the Whisper model directory exists and contains the required files."""
    model_dir = Path(WHISPER_MODEL_PATH)
    if not model_dir.exists():
        return False
    required = {"model.bin", "config.json"}
    existing = {f.name for f in model_dir.iterdir()}
    if not required.issubset(existing):
        return False
    model_bin = model_dir / "model.bin"
    if model_bin.stat().st_size < 350 * 1024 * 1024:
        logger.warning("Whisper model.bin appears incomplete: %d bytes", model_bin.stat().st_size)
        return False
    return True


@router.get("/health")
async def health():
    profile = analyze_hardware()
    cfg = MODEL_CONFIGS[profile]
    model_path = get_llm_model_path(profile)
    expected_size = cfg.get("size_gb", 0)
    models_ready = _is_model_valid(model_path, expected_size)
    whisper_ready = _is_whisper_valid()
    return {"status": "ok", "models_ready": models_ready, "whisper_ready": whisper_ready}

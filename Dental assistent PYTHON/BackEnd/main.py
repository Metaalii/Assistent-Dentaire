import asyncio
import json
import logging
import os
import re
import shutil
import threading
import time
from contextlib import asynccontextmanager
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.config import (
    MODEL_CONFIGS, ALTERNATIVE_MODELS, get_llm_model_path, analyze_hardware,
    get_hardware_info, WHISPER_MODEL_PATH, WHISPER_MODEL_FILES, WHISPER_EXPECTED_SIZE_MB,
)
from app.middleware import MaxRequestSizeMiddleware, SimpleRateLimitMiddleware
from app.security import verify_api_key, check_api_key_configured, validate_security_config
from app.llm_config import SMARTNOTE_PROMPT_OPTIMIZED

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("dental_assistant")

# ---------------------------------------------------------------------------
# Download state tracking & concurrency locks
# ---------------------------------------------------------------------------
_download_lock = threading.Lock()  # Prevents concurrent LLM downloads
_whisper_download_lock = threading.Lock()  # Prevents concurrent Whisper downloads

# Shared mutable state for LLM download progress (read by SSE endpoint)
_download_state: dict = {
    "active": False,
    "progress": 0.0,       # 0-100
    "downloaded_bytes": 0,
    "total_bytes": 0,
    "error": None,
    "done": False,
}

# Shared mutable state for Whisper download progress
_whisper_download_state: dict = {
    "active": False,
    "progress": 0.0,
    "downloaded_bytes": 0,
    "total_bytes": 0,
    "current_file": "",
    "error": None,
    "done": False,
}

# ---------------------------------------------------------------------------
# Lightweight cache for GET /setup/check-models
# ---------------------------------------------------------------------------
_check_models_cache: dict = {"result": None, "ts": 0.0}
_CHECK_MODELS_TTL = 5.0  # seconds


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup and shutdown events."""
    # Startup - validate security first (will raise in production without API key)
    validate_security_config()

    if check_api_key_configured():
        logger.info("✓ API key configured from environment")

    # Log hardware detection results
    hw_info = get_hardware_info()
    logger.info(
        "Hardware detected: %s (GPU: %s, VRAM: %s GB, Backend: %s)",
        hw_info["profile"],
        hw_info.get("gpu_name", "None"),
        hw_info.get("vram_gb", "N/A"),
        "supported" if hw_info.get("backend_gpu_support") else "not supported"
    )

    yield  # Application runs here

    # Shutdown (add cleanup here if needed)
    logger.info("Dental Assistant Backend shutting down")


app = FastAPI(title="Dental Assistant Backend", lifespan=lifespan)

# Router import from app/llm/api/transcribe.py
from app.llm.api.transcribe import router as transcribe_router  # noqa: E402

app.include_router(transcribe_router)

# --- Middlewares ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:1420",
        "tauri://localhost",
        "https://tauri.localhost",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["X-API-Key", "Content-Type"],
)
app.add_middleware(MaxRequestSizeMiddleware, max_bytes=100 * 1024 * 1024)

# MVP: keep class for compatibility; it is disabled unless ENABLE_DEV_RATE_LIMIT=1
app.add_middleware(SimpleRateLimitMiddleware)


# --- Input Sanitization ---
def sanitize_input(text: str, max_length: int = 50000) -> str:
    """
    Sanitize user input before LLM processing.

    - Removes potential prompt injection patterns
    - Limits text length to prevent memory issues
    - Removes control characters except newlines
    - Normalizes whitespace
    """
    if not text:
        return ""

    # Truncate to max length
    text = text[:max_length]

    # Remove control characters except newlines and tabs
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)

    # Remove potential prompt injection patterns (basic protection)
    # These patterns try to override system instructions
    injection_patterns = [
        r'(?i)ignore\s+(all\s+)?(previous|above)\s+instructions?',
        r'(?i)disregard\s+(all\s+)?(previous|above)',
        r'(?i)forget\s+(everything|all)',
        r'(?i)you\s+are\s+now\s+a',
        r'(?i)new\s+instructions?:',
        r'(?i)system\s*:\s*',
    ]

    for pattern in injection_patterns:
        text = re.sub(pattern, '[FILTERED]', text)

    # Normalize excessive whitespace (but keep structure)
    text = re.sub(r'[ \t]+', ' ', text)  # Multiple spaces/tabs to single space
    text = re.sub(r'\n{4,}', '\n\n\n', text)  # Max 3 consecutive newlines

    return text.strip()


# --- Business Logic ---
class SummaryRequest(BaseModel):
    text: str


@app.post("/summarize", dependencies=[Depends(verify_api_key)])
async def summarize(req: SummaryRequest):
    """
    Generate a SmartNote summary from transcribed text.
    Returns the complete summary when generation is finished.
    """
    if not get_llm_model_path().exists():
        raise HTTPException(status_code=503, detail="Model not downloaded. Please run setup.")

    # Sanitize input before LLM processing
    sanitized_text = sanitize_input(req.text)
    if not sanitized_text:
        raise HTTPException(status_code=400, detail="Text input is empty or invalid.")

    # Lazy import: backend boots even without llama-cpp-python installed.
    from app.llm.local_llm import LocalLLM  # noqa: WPS433

    llm = LocalLLM()
    prompt = SMARTNOTE_PROMPT_OPTIMIZED.format(text=sanitized_text)
    summary = await llm.generate(prompt)
    return {"summary": summary}


@app.post("/summarize-stream", dependencies=[Depends(verify_api_key)])
async def summarize_stream(req: SummaryRequest):
    """
    Stream SmartNote generation using Server-Sent Events (SSE).
    Returns tokens as they are generated for reduced perceived latency.

    Event format:
    - data: {"chunk": "token text"}  - for each generated token
    - data: [DONE]                    - when generation is complete
    """
    if not get_llm_model_path().exists():
        raise HTTPException(status_code=503, detail="Model not downloaded. Please run setup.")

    # Sanitize input before LLM processing
    sanitized_text = sanitize_input(req.text)
    if not sanitized_text:
        raise HTTPException(status_code=400, detail="Text input is empty or invalid.")

    from app.llm.local_llm import LocalLLM  # noqa: WPS433

    llm = LocalLLM()
    prompt = SMARTNOTE_PROMPT_OPTIMIZED.format(text=sanitized_text)

    async def event_generator():
        try:
            async for chunk in llm.generate_stream(prompt):
                yield f"data: {json.dumps({'chunk': chunk})}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            logger.exception("Streaming error")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )


# --- Setup / download ---
def _ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _atomic_download(url: str, dest_path: Path) -> None:
    """
    MVP-safe download with progress tracking:
    - stream download in chunks (tracks bytes for SSE progress)
    - raise_for_status() to avoid saving error pages
    - write to .part then rename atomically
    - updates _download_state so the SSE endpoint can push progress
    - guarded by _download_lock to prevent concurrent downloads
    """
    global _download_state

    if not _download_lock.acquire(blocking=False):
        logger.warning("Download already in progress, skipping duplicate request")
        return

    try:
        _download_state = {
            "active": True, "progress": 0.0,
            "downloaded_bytes": 0, "total_bytes": 0,
            "error": None, "done": False,
        }

        _ensure_parent_dir(dest_path)
        tmp_path = dest_path.with_suffix(dest_path.suffix + ".part")

        logger.info("Downloading model: %s -> %s", url, dest_path)

        headers = {}
        hf_token = os.getenv("HUGGINGFACE_HUB_TOKEN")
        if hf_token:
            headers["Authorization"] = f"Bearer {hf_token}"

        with requests.get(url, headers=headers, stream=True, timeout=(10, 180)) as r:
            r.raise_for_status()
            total = int(r.headers.get("Content-Length", 0))
            _download_state["total_bytes"] = total
            downloaded = 0
            chunk_size = 256 * 1024  # 256 KB chunks

            with open(tmp_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        _download_state["downloaded_bytes"] = downloaded
                        if total > 0:
                            _download_state["progress"] = round(
                                (downloaded / total) * 100, 1
                            )
                f.flush()

        tmp_path.replace(dest_path)
        _download_state["progress"] = 100.0
        _download_state["done"] = True
        _download_state["active"] = False
        # Invalidate check-models cache so next call sees the new file
        _check_models_cache["ts"] = 0.0
        logger.info("Model download complete: %s", dest_path)

    except Exception as exc:
        logger.exception("Model download failed")
        _download_state["error"] = str(exc)
        _download_state["active"] = False
        try:
            tmp_path = dest_path.with_suffix(dest_path.suffix + ".part")
            if tmp_path.exists():
                tmp_path.unlink()
        except Exception:
            logger.warning("Failed to remove partial file: %s", tmp_path)
        raise
    finally:
        _download_lock.release()


def _is_model_valid(model_path: Path, expected_size_gb: float) -> bool:
    """
    Check if the model file exists and has a reasonable size.
    Returns False for missing, empty, or corrupted (too small) files.
    """
    if not model_path.exists():
        return False

    # Check file size - should be at least 80% of expected size
    # This catches partial downloads and corrupted files
    file_size_gb = model_path.stat().st_size / (1024 ** 3)
    min_expected = expected_size_gb * 0.8

    if file_size_gb < min_expected:
        logger.warning(
            "Model file appears incomplete: %.2f GB (expected ~%.1f GB). "
            "Consider re-downloading.",
            file_size_gb, expected_size_gb
        )
        return False

    return True


@app.get("/setup/check-models")
async def check_models():
    # Return cached result if still fresh (avoids repeated disk I/O + hw detection)
    now = time.monotonic()
    if (
        _check_models_cache["result"] is not None
        and (now - _check_models_cache["ts"]) < _CHECK_MODELS_TTL
    ):
        return _check_models_cache["result"]

    # Get detailed hardware info from tiered detection
    hw_info = get_hardware_info()
    profile = hw_info["profile"]
    cfg = MODEL_CONFIGS[profile]
    model_path = get_llm_model_path(profile)
    expected_size = cfg.get("size_gb", 0)

    # Validate model file exists AND has correct size
    is_valid = _is_model_valid(model_path, expected_size)

    # Get alternative model recommendations
    alternatives = ALTERNATIVE_MODELS.get(profile, [])

    # Check Whisper model status
    whisper_valid = _is_whisper_valid()

    result = {
        # Core info
        "hardware_profile": profile,
        "is_downloaded": is_valid,
        "model_exists": is_valid,  # backward compat
        "recommended_model": cfg["filename"],
        "download_url": cfg["url"],
        "model_size_gb": expected_size,
        "model_description": cfg.get("description"),
        # Whisper model info
        "whisper_downloaded": whisper_valid,
        "whisper_size_mb": WHISPER_EXPECTED_SIZE_MB,
        # Detailed hardware info
        "gpu_detected": hw_info.get("gpu_detected", False),
        "gpu_name": hw_info.get("gpu_name"),
        "vram_gb": hw_info.get("vram_gb"),
        "backend_gpu_support": hw_info.get("backend_gpu_support", False),
        "detection_method": hw_info.get("detection_method", "none"),
        # Alternative model recommendations
        "alternative_models": alternatives,
        "model_recommendation_note": _get_recommendation_note(profile),
    }

    _check_models_cache["result"] = result
    _check_models_cache["ts"] = now
    return result


def _get_recommendation_note(profile: str) -> str:
    """Get a user-friendly recommendation note based on hardware profile."""
    notes = {
        "high_vram": (
            "Votre GPU puissant permet d'utiliser des modèles de haute qualité. "
            "Mistral 7B est recommandé pour un excellent support du français."
        ),
        "low_vram": (
            "Votre GPU a une VRAM limitée. Les modèles Q4 offrent un bon équilibre. "
            "Mistral 7B Q4 est idéal pour le français médical."
        ),
        "cpu_only": (
            "Mode CPU détecté. Les modèles compacts comme Phi-3 Mini ou Mistral Q3 "
            "offrent de bonnes performances. Le traitement sera plus lent qu'avec un GPU."
        ),
    }
    return notes.get(profile, "")


@app.post("/setup/download-model", dependencies=[Depends(verify_api_key)])
async def download_model(background_tasks: BackgroundTasks):
    # Reject if a download is already running
    if _download_state["active"]:
        return {"status": "already_downloading"}

    profile = analyze_hardware()
    cfg = MODEL_CONFIGS[profile]
    model_path = get_llm_model_path(profile)
    expected_size = cfg.get("size_gb", 0)

    # Check if model is already valid (exists + correct size)
    if _is_model_valid(model_path, expected_size):
        return {"status": "already_exists"}

    # Remove incomplete/corrupted file if it exists
    if model_path.exists():
        logger.info("Removing incomplete model file before re-download: %s", model_path)
        model_path.unlink()

    url = cfg["url"]
    background_tasks.add_task(_atomic_download, url, model_path)
    return {"status": "started", "profile": profile}


@app.get("/setup/download-progress")
async def download_progress():
    """
    SSE endpoint streaming download progress.
    Opens a single connection; the backend pushes events until done/error.
    Events:
      data: {"progress": 42.1, "downloaded_bytes": ..., "total_bytes": ...}
      data: {"progress": 100, "done": true}
      data: {"error": "..."}
    """
    async def event_stream():
        # Push current state immediately, then every ~1 s
        while True:
            state = _download_state.copy()

            if state.get("error"):
                yield f"data: {json.dumps({'error': state['error']})}\n\n"
                return

            payload = {
                "progress": state["progress"],
                "downloaded_bytes": state["downloaded_bytes"],
                "total_bytes": state["total_bytes"],
            }

            if state.get("done"):
                payload["done"] = True
                yield f"data: {json.dumps(payload)}\n\n"
                return

            yield f"data: {json.dumps(payload)}\n\n"
            await asyncio.sleep(1)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# --- Whisper model download ---

def _is_whisper_valid() -> bool:
    """Check if the Whisper model directory exists and contains the required files."""
    model_dir = Path(WHISPER_MODEL_PATH)
    if not model_dir.exists():
        return False
    # Must contain at least model.bin and config.json
    required = {"model.bin", "config.json"}
    existing = {f.name for f in model_dir.iterdir()}
    if not required.issubset(existing):
        return False
    # model.bin must be large enough (~461 MB, check ≥ 80%)
    model_bin = model_dir / "model.bin"
    if model_bin.stat().st_size < 350 * 1024 * 1024:
        logger.warning("Whisper model.bin appears incomplete: %d bytes", model_bin.stat().st_size)
        return False
    return True


def _download_whisper_files() -> None:
    """
    Download all Whisper model files into the whisper-small directory.
    Tracks cumulative progress across all files.
    Guarded by _whisper_download_lock.
    """
    global _whisper_download_state

    if not _whisper_download_lock.acquire(blocking=False):
        logger.warning("Whisper download already in progress, skipping")
        return

    try:
        total_expected = sum(f["size_mb"] for f in WHISPER_MODEL_FILES) * 1024 * 1024
        _whisper_download_state = {
            "active": True, "progress": 0.0,
            "downloaded_bytes": 0, "total_bytes": int(total_expected),
            "current_file": "", "error": None, "done": False,
        }

        dest_dir = Path(WHISPER_MODEL_PATH)
        dest_dir.mkdir(parents=True, exist_ok=True)

        headers = {}
        hf_token = os.getenv("HUGGINGFACE_HUB_TOKEN")
        if hf_token:
            headers["Authorization"] = f"Bearer {hf_token}"

        cumulative = 0
        # Track estimated vs actual totals per file for accurate progress
        remaining_estimate = int(total_expected)

        for file_info in WHISPER_MODEL_FILES:
            fname = file_info["name"]
            url = file_info["url"]
            dest_file = dest_dir / fname
            tmp_file = dest_file.with_suffix(dest_file.suffix + ".part")
            _whisper_download_state["current_file"] = fname
            file_estimate = int(file_info["size_mb"] * 1024 * 1024)

            logger.info("Downloading Whisper file: %s", fname)

            with requests.get(url, headers=headers, stream=True, timeout=(10, 300)) as r:
                r.raise_for_status()
                file_total = int(r.headers.get("Content-Length", 0))
                # Refine total_bytes: replace this file's estimate with actual size
                if file_total:
                    remaining_estimate -= file_estimate
                    _whisper_download_state["total_bytes"] = cumulative + file_total + remaining_estimate
                else:
                    remaining_estimate -= file_estimate

                chunk_size = 256 * 1024
                with open(tmp_file, "wb") as f:
                    for chunk in r.iter_content(chunk_size=chunk_size):
                        if chunk:
                            f.write(chunk)
                            cumulative += len(chunk)
                            _whisper_download_state["downloaded_bytes"] = cumulative
                            actual_total = _whisper_download_state["total_bytes"]
                            if actual_total > 0:
                                _whisper_download_state["progress"] = round(
                                    (cumulative / actual_total) * 100, 1
                                )
                    f.flush()

            tmp_file.replace(dest_file)
            logger.info("Whisper file complete: %s", fname)

        _whisper_download_state["progress"] = 100.0
        _whisper_download_state["done"] = True
        _whisper_download_state["active"] = False
        _check_models_cache["ts"] = 0.0
        logger.info("Whisper model download complete: %s", dest_dir)

    except Exception as exc:
        logger.exception("Whisper model download failed")
        _whisper_download_state["error"] = str(exc)
        _whisper_download_state["active"] = False
        raise
    finally:
        _whisper_download_lock.release()


@app.post("/setup/download-whisper", dependencies=[Depends(verify_api_key)])
async def download_whisper(background_tasks: BackgroundTasks):
    """Start downloading the Whisper model files in the background."""
    if _whisper_download_state["active"]:
        return {"status": "already_downloading"}

    if _is_whisper_valid():
        return {"status": "already_exists"}

    background_tasks.add_task(_download_whisper_files)
    return {"status": "started"}


@app.get("/setup/whisper-download-progress")
async def whisper_download_progress():
    """SSE endpoint streaming Whisper download progress."""
    async def event_stream():
        while True:
            state = _whisper_download_state.copy()

            if state.get("error"):
                yield f"data: {json.dumps({'error': state['error']})}\n\n"
                return

            payload = {
                "progress": state["progress"],
                "downloaded_bytes": state["downloaded_bytes"],
                "total_bytes": state["total_bytes"],
                "current_file": state.get("current_file", ""),
            }

            if state.get("done"):
                payload["done"] = True
                yield f"data: {json.dumps(payload)}\n\n"
                return

            yield f"data: {json.dumps(payload)}\n\n"
            await asyncio.sleep(1)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/health")
async def health():
    profile = analyze_hardware()
    cfg = MODEL_CONFIGS[profile]
    model_path = get_llm_model_path(profile)
    expected_size = cfg.get("size_gb", 0)
    models_ready = _is_model_valid(model_path, expected_size)
    whisper_ready = _is_whisper_valid()
    return {"status": "ok", "models_ready": models_ready, "whisper_ready": whisper_ready}

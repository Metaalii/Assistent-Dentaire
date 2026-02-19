"""
Model setup & download endpoints.

GET  /setup/check-models            — hardware profile + model status
POST /setup/download-model          — start LLM model download
GET  /setup/download-progress       — SSE for LLM download progress
POST /setup/download-whisper        — start Whisper model download
GET  /setup/whisper-download-progress — SSE for Whisper download progress
"""

import asyncio
import hashlib
import json
import logging
import os
import threading
import time
from pathlib import Path

import requests
from fastapi import APIRouter, BackgroundTasks, Depends
from fastapi.responses import StreamingResponse

from app.config import (
    ALTERNATIVE_MODELS,
    MODEL_CONFIGS,
    WHISPER_EXPECTED_SIZE_MB,
    WHISPER_MODEL_FILES,
    WHISPER_MODEL_PATH,
    analyze_hardware,
    get_hardware_info,
    get_llm_model_path,
)
from app.security import verify_api_key

router = APIRouter(prefix="/setup", tags=["setup"])
logger = logging.getLogger("dental_assistant.setup")

# ---------------------------------------------------------------------------
# Thread-safe download progress tracker
# ---------------------------------------------------------------------------


class DownloadTracker:
    """
    Encapsulates download state behind a lock so that background-thread
    writers and async SSE readers never see torn state.

    ``try_start()`` is an atomic check-and-set that prevents two
    concurrent POST requests from both launching a download.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._active = False
        self._progress = 0.0
        self._downloaded_bytes = 0
        self._total_bytes = 0
        self._current_file = ""
        self._error: str | None = None
        self._done = False

    # -- mutations (called from the download thread) ----------------------

    def try_start(self) -> bool:
        """Atomically set active if not already. Returns True on success."""
        with self._lock:
            if self._active:
                return False
            self._active = True
            self._progress = 0.0
            self._downloaded_bytes = 0
            self._total_bytes = 0
            self._current_file = ""
            self._error = None
            self._done = False
            return True

    def update(
        self,
        downloaded_bytes: int,
        total_bytes: int,
        current_file: str = "",
    ) -> None:
        with self._lock:
            self._downloaded_bytes = downloaded_bytes
            self._total_bytes = total_bytes
            if total_bytes > 0:
                self._progress = round((downloaded_bytes / total_bytes) * 100, 1)
            if current_file:
                self._current_file = current_file

    def finish(self) -> None:
        with self._lock:
            self._progress = 100.0
            self._done = True
            self._active = False

    def fail(self, error: str) -> None:
        with self._lock:
            self._error = error
            self._active = False

    # -- reads (called from async SSE handlers) ---------------------------

    def snapshot(self) -> dict:
        """Return a consistent, point-in-time copy of the state."""
        with self._lock:
            return {
                "active": self._active,
                "progress": self._progress,
                "downloaded_bytes": self._downloaded_bytes,
                "total_bytes": self._total_bytes,
                "current_file": self._current_file,
                "error": self._error,
                "done": self._done,
            }

    @property
    def is_active(self) -> bool:
        with self._lock:
            return self._active


_llm_tracker = DownloadTracker()
_whisper_tracker = DownloadTracker()

# ---------------------------------------------------------------------------
# Lightweight cache for GET /setup/check-models
# ---------------------------------------------------------------------------
_check_models_cache: dict = {"result": None, "ts": 0.0}
_CHECK_MODELS_TTL = 5.0  # seconds


# ---------------------------------------------------------------------------
# Helpers (shared with health router via import if needed)
# ---------------------------------------------------------------------------

def _ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _sha256_file(path: Path) -> str:
    """Compute the SHA-256 hex digest of *path* using a streaming read."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(256 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _verify_sha256(path: Path, expected: str | None) -> bool:
    """
    If *expected* is set, verify the file's SHA-256 matches.
    Returns True when the hash matches **or** when no expected hash is
    configured (opt-in verification).
    """
    if not expected:
        return True
    actual = _sha256_file(path)
    if actual != expected.lower():
        logger.error(
            "SHA-256 mismatch for %s: expected %s, got %s",
            path.name, expected, actual,
        )
        return False
    return True


def _is_model_valid(
    model_path: Path,
    expected_size_gb: float,
    expected_sha256: str | None = None,
) -> bool:
    """Check if the model file exists, has a reasonable size, and matches its checksum."""
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
    if not _verify_sha256(model_path, expected_sha256):
        return False
    return True


def _is_whisper_valid() -> bool:
    """Check if the Whisper model directory exists and contains required files."""
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
    # Verify per-file checksums when configured
    for file_info in WHISPER_MODEL_FILES:
        fpath = model_dir / file_info["name"]
        if fpath.exists() and not _verify_sha256(fpath, file_info.get("sha256")):
            return False
    return True


# ---------------------------------------------------------------------------
# LLM download internals
# ---------------------------------------------------------------------------

def _atomic_download(
    url: str,
    dest_path: Path,
    expected_sha256: str | None = None,
) -> None:
    """
    Stream download with progress tracking and optional SHA-256 verification.
    Writes to .part file then renames atomically.
    Progress is published via ``_llm_tracker`` for the SSE endpoint.
    """
    try:
        _ensure_parent_dir(dest_path)
        tmp_path = dest_path.with_suffix(dest_path.suffix + ".part")

        logger.info("Downloading model: %s -> %s", url, dest_path)

        headers = {}
        hf_token = os.getenv("HUGGINGFACE_HUB_TOKEN")
        if hf_token:
            headers["Authorization"] = f"Bearer {hf_token}"

        sha256_hash = hashlib.sha256()

        with requests.get(url, headers=headers, stream=True, timeout=(10, 180)) as r:
            r.raise_for_status()
            total = int(r.headers.get("Content-Length", 0))
            downloaded = 0
            chunk_size = 256 * 1024

            with open(tmp_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=chunk_size):
                    if chunk:
                        f.write(chunk)
                        sha256_hash.update(chunk)
                        downloaded += len(chunk)
                        _llm_tracker.update(downloaded, total)
                f.flush()

        actual_hash = sha256_hash.hexdigest()
        logger.info("Model SHA-256: %s", actual_hash)

        if expected_sha256 and actual_hash != expected_sha256.lower():
            msg = (
                f"SHA-256 mismatch for {dest_path.name}: "
                f"expected {expected_sha256}, got {actual_hash}"
            )
            logger.error(msg)
            tmp_path.unlink(missing_ok=True)
            raise ValueError(msg)

        tmp_path.replace(dest_path)
        _llm_tracker.finish()
        _check_models_cache["ts"] = 0.0
        logger.info("Model download complete: %s", dest_path)

    except Exception as exc:
        logger.exception("Model download failed")
        _llm_tracker.fail(str(exc))
        try:
            tmp_path = dest_path.with_suffix(dest_path.suffix + ".part")
            if tmp_path.exists():
                tmp_path.unlink()
        except Exception:
            logger.warning("Failed to remove partial file: %s", tmp_path)
        raise


# ---------------------------------------------------------------------------
# Whisper download internals
# ---------------------------------------------------------------------------

def _download_whisper_files() -> None:
    """
    Download all Whisper model files into the whisper-small directory.
    Tracks cumulative progress across all files via ``_whisper_tracker``.
    Each file is SHA-256-verified when a known hash is configured.
    """
    try:
        total_expected = int(
            sum(f["size_mb"] for f in WHISPER_MODEL_FILES) * 1024 * 1024
        )

        dest_dir = Path(WHISPER_MODEL_PATH)
        dest_dir.mkdir(parents=True, exist_ok=True)

        headers = {}
        hf_token = os.getenv("HUGGINGFACE_HUB_TOKEN")
        if hf_token:
            headers["Authorization"] = f"Bearer {hf_token}"

        cumulative = 0
        remaining_estimate = total_expected

        for file_info in WHISPER_MODEL_FILES:
            fname = file_info["name"]
            url = file_info["url"]
            expected_sha = file_info.get("sha256")
            dest_file = dest_dir / fname
            tmp_file = dest_file.with_suffix(dest_file.suffix + ".part")
            file_estimate = int(file_info["size_mb"] * 1024 * 1024)

            logger.info("Downloading Whisper file: %s", fname)
            file_hash = hashlib.sha256()

            with requests.get(url, headers=headers, stream=True, timeout=(10, 300)) as r:
                r.raise_for_status()
                file_total = int(r.headers.get("Content-Length", 0))
                if file_total:
                    remaining_estimate -= file_estimate
                    adjusted_total = cumulative + file_total + remaining_estimate
                else:
                    remaining_estimate -= file_estimate
                    adjusted_total = total_expected

                chunk_size = 256 * 1024
                with open(tmp_file, "wb") as f:
                    for chunk in r.iter_content(chunk_size=chunk_size):
                        if chunk:
                            f.write(chunk)
                            file_hash.update(chunk)
                            cumulative += len(chunk)
                            _whisper_tracker.update(
                                cumulative, adjusted_total, fname
                            )
                    f.flush()

            actual_hash = file_hash.hexdigest()
            logger.info("Whisper %s SHA-256: %s", fname, actual_hash)

            if expected_sha and actual_hash != expected_sha.lower():
                tmp_file.unlink(missing_ok=True)
                raise ValueError(
                    f"SHA-256 mismatch for {fname}: "
                    f"expected {expected_sha}, got {actual_hash}"
                )

            tmp_file.replace(dest_file)
            logger.info("Whisper file complete: %s", fname)

        _whisper_tracker.finish()
        _check_models_cache["ts"] = 0.0
        logger.info("Whisper model download complete: %s", dest_dir)

    except Exception as exc:
        logger.exception("Whisper model download failed")
        _whisper_tracker.fail(str(exc))
        raise


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

def _get_recommendation_note(profile: str) -> str:
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


@router.get("/check-models")
async def check_models():
    now = time.monotonic()
    if (
        _check_models_cache["result"] is not None
        and (now - _check_models_cache["ts"]) < _CHECK_MODELS_TTL
    ):
        return _check_models_cache["result"]

    hw_info = get_hardware_info()
    profile = hw_info["profile"]
    cfg = MODEL_CONFIGS[profile]
    model_path = get_llm_model_path(profile)
    expected_size = cfg.get("size_gb", 0)

    is_valid = _is_model_valid(model_path, expected_size, cfg.get("sha256"))
    alternatives = ALTERNATIVE_MODELS.get(profile, [])
    whisper_valid = _is_whisper_valid()

    result = {
        "hardware_profile": profile,
        "is_downloaded": is_valid,
        "model_exists": is_valid,
        "recommended_model": cfg["filename"],
        "download_url": cfg["url"],
        "model_size_gb": expected_size,
        "model_description": cfg.get("description"),
        "whisper_downloaded": whisper_valid,
        "whisper_size_mb": WHISPER_EXPECTED_SIZE_MB,
        "gpu_detected": hw_info.get("gpu_detected", False),
        "gpu_name": hw_info.get("gpu_name"),
        "vram_gb": hw_info.get("vram_gb"),
        "backend_gpu_support": hw_info.get("backend_gpu_support", False),
        "detection_method": hw_info.get("detection_method", "none"),
        "alternative_models": alternatives,
        "model_recommendation_note": _get_recommendation_note(profile),
    }

    _check_models_cache["result"] = result
    _check_models_cache["ts"] = now
    return result


@router.post("/download-model", dependencies=[Depends(verify_api_key)])
async def download_model(background_tasks: BackgroundTasks):
    if _llm_tracker.is_active:
        return {"status": "already_downloading"}

    profile = analyze_hardware()
    cfg = MODEL_CONFIGS[profile]
    model_path = get_llm_model_path(profile)
    expected_size = cfg.get("size_gb", 0)

    expected_sha256 = cfg.get("sha256")

    if _is_model_valid(model_path, expected_size, expected_sha256):
        return {"status": "already_exists"}

    if not _llm_tracker.try_start():
        return {"status": "already_downloading"}

    if model_path.exists():
        logger.info("Removing incomplete model file before re-download: %s", model_path)
        model_path.unlink()

    url = cfg["url"]
    background_tasks.add_task(_atomic_download, url, model_path, expected_sha256)
    return {"status": "started", "profile": profile}


@router.get("/download-progress")
async def download_progress():
    """SSE endpoint streaming LLM download progress."""

    async def event_stream():
        while True:
            snap = _llm_tracker.snapshot()

            if snap["error"]:
                yield f"data: {json.dumps({'error': snap['error']})}\n\n"
                return

            payload = {
                "progress": snap["progress"],
                "downloaded_bytes": snap["downloaded_bytes"],
                "total_bytes": snap["total_bytes"],
            }

            if snap["done"]:
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


@router.post("/download-whisper", dependencies=[Depends(verify_api_key)])
async def download_whisper(background_tasks: BackgroundTasks):
    """Start downloading the Whisper model files in the background."""
    if _whisper_tracker.is_active:
        return {"status": "already_downloading"}

    if _is_whisper_valid():
        return {"status": "already_exists"}

    if not _whisper_tracker.try_start():
        return {"status": "already_downloading"}

    background_tasks.add_task(_download_whisper_files)
    return {"status": "started"}


@router.get("/whisper-download-progress")
async def whisper_download_progress():
    """SSE endpoint streaming Whisper download progress."""

    async def event_stream():
        while True:
            snap = _whisper_tracker.snapshot()

            if snap["error"]:
                yield f"data: {json.dumps({'error': snap['error']})}\n\n"
                return

            payload = {
                "progress": snap["progress"],
                "downloaded_bytes": snap["downloaded_bytes"],
                "total_bytes": snap["total_bytes"],
                "current_file": snap["current_file"],
            }

            if snap["done"]:
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

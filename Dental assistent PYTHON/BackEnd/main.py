import logging
import shutil
from pathlib import Path

import requests
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.config import MODEL_CONFIGS, get_llm_model_path, analyze_hardware, get_hardware_info
from app.middleware import MaxRequestSizeMiddleware, SimpleRateLimitMiddleware
from app.security import verify_api_key

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("dental_assistant")

app = FastAPI(title="Dental Assistant Backend")

# Router import from app/llm/api/transcribe.py
from app.llm.api.transcribe import router as transcribe_router  # noqa: E402

app.include_router(transcribe_router)

# --- Middlewares ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "tauri://localhost"],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["X-API-Key", "Content-Type"],
)
app.add_middleware(MaxRequestSizeMiddleware, max_bytes=10 * 1024 * 1024)

# MVP: keep class for compatibility; it is disabled unless ENABLE_DEV_RATE_LIMIT=1
app.add_middleware(SimpleRateLimitMiddleware)


# --- Business Logic ---
class SummaryRequest(BaseModel):
    text: str


@app.post("/summarize", dependencies=[Depends(verify_api_key)])
async def summarize(req: SummaryRequest):
    if not get_llm_model_path().exists():
        raise HTTPException(status_code=503, detail="Model not downloaded. Please run setup.")

    # Lazy import: backend boots even without llama-cpp-python installed.
    from app.llm.local_llm import LocalLLM  # noqa: WPS433

    llm = LocalLLM()
    prompt = f"ANALYSE THIS MEDICAL CONSULTATION:\n{req.text}"
    summary = await llm.generate(prompt)
    return {"summary": summary}


# --- Setup / download ---
def _ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _atomic_download(url: str, dest_path: Path) -> None:
    """
    MVP-safe download:
    - stream download
    - raise_for_status() to avoid saving error pages
    - write to .part then rename atomically
    """
    _ensure_parent_dir(dest_path)
    tmp_path = dest_path.with_suffix(dest_path.suffix + ".part")

    logger.info("Downloading model: %s -> %s", url, dest_path)

    try:
        with requests.get(url, stream=True, timeout=(10, 180)) as r:
            r.raise_for_status()
            with open(tmp_path, "wb") as f:
                shutil.copyfileobj(r.raw, f)
                f.flush()

        tmp_path.replace(dest_path)
        logger.info("Model download complete: %s", dest_path)

    except Exception:
        logger.exception("Model download failed")
        try:
            if tmp_path.exists():
                tmp_path.unlink()
        except Exception:
            logger.warning("Failed to remove partial file: %s", tmp_path)
        raise


@app.get("/setup/check-models")
async def check_models():
    # Get detailed hardware info from tiered detection
    hw_info = get_hardware_info()
    profile = hw_info["profile"]
    cfg = MODEL_CONFIGS[profile]
    model_path = get_llm_model_path(profile)
    downloaded = model_path.exists()

    return {
        # Core info
        "hardware_profile": profile,
        "is_downloaded": downloaded,
        "model_exists": downloaded,  # backward compat
        "recommended_model": cfg["filename"],
        "download_url": cfg["url"],
        "model_size_gb": cfg.get("size_gb"),
        "model_description": cfg.get("description"),
        # Detailed hardware info
        "gpu_detected": hw_info.get("gpu_detected", False),
        "gpu_name": hw_info.get("gpu_name"),
        "vram_gb": hw_info.get("vram_gb"),
        "backend_gpu_support": hw_info.get("backend_gpu_support", False),
        "detection_method": hw_info.get("detection_method", "none"),
    }


@app.post("/setup/download-model", dependencies=[Depends(verify_api_key)])
async def download_model(background_tasks: BackgroundTasks):
    profile = analyze_hardware()
    model_path = get_llm_model_path(profile)

    if model_path.exists():
        return {"status": "already_exists"}

    url = MODEL_CONFIGS[profile]["url"]

    background_tasks.add_task(_atomic_download, url, model_path)
    return {"status": "started", "profile": profile}


@app.get("/health")
async def health():
    return {"status": "ok", "models_ready": get_llm_model_path().exists()}

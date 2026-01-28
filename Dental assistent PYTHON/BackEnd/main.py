import logging
import os
import shutil
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()
from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.config import MODEL_CONFIGS, get_llm_model_path, analyze_hardware, get_hardware_info
from app.middleware import MaxRequestSizeMiddleware, SimpleRateLimitMiddleware
from app.security import verify_api_key, check_api_key_configured

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
app.add_middleware(MaxRequestSizeMiddleware, max_bytes=100 * 1024 * 1024)

# MVP: keep class for compatibility; it is disabled unless ENABLE_DEV_RATE_LIMIT=1
app.add_middleware(SimpleRateLimitMiddleware)


# --- Startup Checks ---
@app.on_event("startup")
async def startup_checks():
    """Run startup validation checks."""
    # Check API key configuration
    if not check_api_key_configured():
        logger.info(
            "ℹ️  Using default development API key. "
            "Set APP_API_KEY environment variable for production use."
        )
    else:
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


# --- Business Logic ---
class SummaryRequest(BaseModel):
    text: str


SMARTNOTE_PROMPT = """Tu es un assistant dentaire professionnel français. À partir de la transcription suivante d'une consultation dentaire, génère une SmartNote concise de 5 à 10 lignes.

Format de la SmartNote:
Patient envoyé par Dr… (cabinet…)
Motif : [motif de consultation]
• Antécédents : [antécédents médicaux et dentaires pertinents]
• Examen : [observations cliniques principales]
• Plan de traitement : [traitements proposés]
• Risques : [risques identifiés]
• Recommandations : [conseils au patient]
• Prochaine étape : [prochains rendez-vous ou actions]
• Administratif : [informations sur devis, paiement, etc.]

Transcription de la consultation:
{text}

Génère uniquement la SmartNote en français, sans commentaires supplémentaires."""


@app.post("/summarize", dependencies=[Depends(verify_api_key)])
async def summarize(req: SummaryRequest):
    if not get_llm_model_path().exists():
        raise HTTPException(status_code=503, detail="Model not downloaded. Please run setup.")

    # Lazy import: backend boots even without llama-cpp-python installed.
    from app.llm.local_llm import LocalLLM  # noqa: WPS433

    llm = LocalLLM()
    prompt = SMARTNOTE_PROMPT.format(text=req.text)
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

    headers = {}
    hf_token = os.getenv("HUGGINGFACE_HUB_TOKEN")
    if hf_token:
        headers["Authorization"] = f"Bearer {hf_token}"

    try:
        with requests.get(url, headers=headers, stream=True, timeout=(10, 180)) as r:
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
    # Get detailed hardware info from tiered detection
    hw_info = get_hardware_info()
    profile = hw_info["profile"]
    cfg = MODEL_CONFIGS[profile]
    model_path = get_llm_model_path(profile)
    expected_size = cfg.get("size_gb", 0)

    # Validate model file exists AND has correct size
    is_valid = _is_model_valid(model_path, expected_size)

    return {
        # Core info
        "hardware_profile": profile,
        "is_downloaded": is_valid,
        "model_exists": is_valid,  # backward compat
        "recommended_model": cfg["filename"],
        "download_url": cfg["url"],
        "model_size_gb": expected_size,
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


@app.get("/health")
async def health():
    profile = analyze_hardware()
    cfg = MODEL_CONFIGS[profile]
    model_path = get_llm_model_path(profile)
    expected_size = cfg.get("size_gb", 0)
    models_ready = _is_model_valid(model_path, expected_size)
    return {"status": "ok", "models_ready": models_ready}

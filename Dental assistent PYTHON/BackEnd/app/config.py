import os
import sys
import logging
import threading
from pathlib import Path
from typing import Tuple, Optional, Dict, Any
from .platform import get_platform

logger = logging.getLogger("dental_assistant.config")

# -------- Paths (dev vs frozen) --------

def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def app_base_dir() -> Path:
    """
    Base dir for *read-only* packaged assets.
    In PyInstaller onefile mode, this is sys._MEIPASS.
    In dev mode, it's the project root-ish.
    """
    if is_frozen():
        return Path(getattr(sys, "_MEIPASS"))  # type: ignore[attr-defined]
    return Path(__file__).resolve().parent.parent


def user_data_dir(app_name: str = "DentalAssistant") -> Path:
    """
    Cross-platform, dependency-free app data directory.

    Override with DENTAL_ASSISTANT_DATA_DIR env var (useful for CI/tests).
    Otherwise uses platform-specific implementation:
    - Windows: %APPDATA%\\DentalAssistant
    - macOS:   ~/Library/Application Support/DentalAssistant
    - Linux:   ~/.local/share/DentalAssistant  (or $XDG_DATA_HOME)
    """
    override = os.getenv("DENTAL_ASSISTANT_DATA_DIR")
    if override:
        return Path(override)
    platform = get_platform()
    return platform.get_user_data_dir(app_name)


BASE_DIR = app_base_dir()

# Where models live — directory is created lazily, not at import time.
# Use ensure_models_dir() when you need the directory to exist on disk.
MODELS_DIR = user_data_dir() / "models"

# Whisper model path (fixed location)
WHISPER_MODEL_PATH = MODELS_DIR / "whisper-small"

# RAG data directory (ChromaDB vector stores)
RAG_DATA_DIR = user_data_dir() / "rag_data"


def ensure_models_dir() -> Path:
    """Create MODELS_DIR on disk if it doesn't exist yet. Returns the path."""
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    return MODELS_DIR

# ============================================
# WHISPER MODEL DOWNLOAD CONFIGURATION
# ============================================
# faster-whisper uses CTranslate2 format: a directory with multiple files.
# Source: https://huggingface.co/Systran/faster-whisper-small

_WHISPER_HF_BASE = "https://huggingface.co/Systran/faster-whisper-small/resolve/main"

WHISPER_MODEL_FILES = [
    {"name": "config.json",     "url": f"{_WHISPER_HF_BASE}/config.json",     "size_mb": 0.002},
    {"name": "model.bin",       "url": f"{_WHISPER_HF_BASE}/model.bin",       "size_mb": 461},
    {"name": "tokenizer.json",  "url": f"{_WHISPER_HF_BASE}/tokenizer.json",  "size_mb": 2.2},
    {"name": "vocabulary.txt",  "url": f"{_WHISPER_HF_BASE}/vocabulary.txt",  "size_mb": 0.8},
]

WHISPER_EXPECTED_SIZE_MB = 464  # approximate total


# ============================================
# TIERED HARDWARE DETECTION
# ============================================

class HardwareDetector:
    """
    Tiered hardware detection without requiring PyTorch.

    Detection order:
    1. Check for GPU driver presence (nvidia-smi, Metal, ROCm)
    2. Verify llama-cpp-python GPU support
    3. Run probe test if available
    4. Return appropriate profile

    Thread-safe with caching for performance.
    """

    _cached_result: Optional[Dict[str, Any]] = None
    _cache_lock: threading.Lock = threading.Lock()

    @classmethod
    def detect(cls, force_refresh: bool = False) -> Dict[str, Any]:
        """
        Returns detailed hardware info:
        {
            "profile": "high_vram" | "low_vram" | "cpu_only",
            "gpu_detected": bool,
            "gpu_name": str | None,
            "vram_gb": float | None,
            "backend_gpu_support": bool,
            "detection_method": str,
        }
        """
        # Quick check without lock for already cached result
        if cls._cached_result is not None and not force_refresh:
            return cls._cached_result

        # Thread-safe initialization with double-checked locking
        with cls._cache_lock:
            # Check again inside lock in case another thread cached it
            if cls._cached_result is not None and not force_refresh:
                return cls._cached_result

            result = {
                "profile": "cpu_only",
                "gpu_detected": False,
                "gpu_name": None,
                "vram_gb": None,
                "backend_gpu_support": False,
                "detection_method": "none",
            }

            # Tier 1: Detect GPU driver
            gpu_info = cls._detect_gpu_driver()
            if gpu_info:
                result.update(gpu_info)
                result["gpu_detected"] = True

            # Tier 2: Check if llama-cpp-python has GPU support
            backend_support = cls._check_backend_gpu_support()
            result["backend_gpu_support"] = backend_support

            # Tier 3: Determine profile based on detection
            if result["gpu_detected"] and result["backend_gpu_support"]:
                vram = result.get("vram_gb") or 0
                if vram >= 8 or result.get("detection_method") == "apple_silicon":
                    result["profile"] = "high_vram"
                elif vram >= 4:
                    result["profile"] = "low_vram"
                else:
                    result["profile"] = "cpu_only"
            elif result["gpu_detected"] and not result["backend_gpu_support"]:
                # GPU exists but backend doesn't support it
                logger.warning(
                    "GPU detected (%s) but llama-cpp-python lacks GPU support. "
                    "Reinstall with CUDA/Metal support for better performance.",
                    result.get("gpu_name", "unknown")
                )
                result["profile"] = "cpu_only"

            cls._cached_result = result
            logger.info("Hardware detection: %s", result)
            return result

    @classmethod
    def _detect_gpu_driver(cls) -> Optional[Dict[str, Any]]:
        """Detect GPU via platform-specific implementation."""
        platform = get_platform()
        return platform.detect_gpu()


    @classmethod
    def _check_backend_gpu_support(cls) -> bool:
        """Check if llama-cpp-python was built with GPU support."""
        try:
            # Use platform-specific backend support check
            platform = get_platform()
            return platform.check_gpu_backend_support()

        except ImportError:
            # llama-cpp-python not installed
            return False
        except Exception as e:
            logger.debug("Backend GPU check failed: %s", e)
            return False


def analyze_hardware() -> str:
    """
    Returns a profile: 'high_vram', 'low_vram', or 'cpu_only'.
    Uses tiered detection without requiring PyTorch.
    """
    result = HardwareDetector.detect()
    return result["profile"]


def get_hardware_info() -> Dict[str, Any]:
    """Get detailed hardware information for the frontend."""
    return HardwareDetector.detect()


def get_device_settings() -> Tuple[str, str]:
    """
    Device settings for faster-whisper.
    Returns (device, compute_type).
    """
    info = HardwareDetector.detect()
    profile = info["profile"]

    if profile == "high_vram":
        if info.get("detection_method") == "apple_silicon":
            # Apple Silicon - use CPU with int8 (faster-whisper MPS support varies)
            return ("cpu", "int8")
        return ("cuda", "float16")

    if profile == "low_vram":
        return ("cuda", "int8_float16")

    return ("cpu", "int8")


# -------- Model configs --------
# IMPORTANT: filenames differ per profile to avoid ambiguity / accidental overwrites.

# ============================================
# MODEL CONFIGURATIONS BY HARDWARE PROFILE
# ============================================
# Each profile has a default model and alternative recommendations
# Users can choose based on their specific needs (speed vs quality)

MODEL_CONFIGS = {
    "high_vram": {
        "url": "https://huggingface.co/bartowski/Meta-Llama-3-8B-Instruct-GGUF/resolve/main/Meta-Llama-3-8B-Instruct-Q6_K.gguf",
        "filename": "Meta-Llama-3-8B-Instruct-Q6_K.gguf",
        "size_gb": 6.6,
        "description": "Highest quality, best for powerful GPUs (≥8GB VRAM)",
    },
    "low_vram": {
        "url": "https://huggingface.co/bartowski/Meta-Llama-3-8B-Instruct-GGUF/resolve/main/Meta-Llama-3-8B-Instruct-Q4_K_M.gguf",
        "filename": "Meta-Llama-3-8B-Instruct-Q4_K_M.gguf",
        "size_gb": 4.9,
        "description": "Balanced quality and speed",
    },
    "cpu_only": {
        "url": "https://huggingface.co/bartowski/Meta-Llama-3-8B-Instruct-GGUF/resolve/main/Meta-Llama-3-8B-Instruct-Q4_K_S.gguf",
        "filename": "Meta-Llama-3-8B-Instruct-Q4_K_S.gguf",
        "size_gb": 4.6,
        "description": "Optimized for CPU, smallest size",
    },
}

# ============================================
# ALTERNATIVE MODEL RECOMMENDATIONS
# ============================================
# These models can be used as alternatives based on user preference
# Includes Mistral for better French language support

ALTERNATIVE_MODELS = {
    "high_vram": [
        {
            "id": "mistral-7b-instruct-q6",
            "name": "Mistral 7B Instruct Q6",
            "url": "https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF/resolve/main/mistral-7b-instruct-v0.2.Q6_K.gguf",
            "filename": "mistral-7b-instruct-v0.2.Q6_K.gguf",
            "size_gb": 5.9,
            "description": "Excellent for French, very fast",
            "recommended_for": ["French", "Speed", "Medical"],
        },
        {
            "id": "llama3-8b-q8",
            "name": "Llama 3 8B Q8 (Maximum Quality)",
            "url": "https://huggingface.co/bartowski/Meta-Llama-3-8B-Instruct-GGUF/resolve/main/Meta-Llama-3-8B-Instruct-Q8_0.gguf",
            "filename": "Meta-Llama-3-8B-Instruct-Q8_0.gguf",
            "size_gb": 8.5,
            "description": "Maximum quality, requires ≥12GB VRAM",
            "recommended_for": ["Quality", "Accuracy"],
        },
    ],
    "low_vram": [
        {
            "id": "mistral-7b-instruct-q4",
            "name": "Mistral 7B Instruct Q4",
            "url": "https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF/resolve/main/mistral-7b-instruct-v0.2.Q4_K_M.gguf",
            "filename": "mistral-7b-instruct-v0.2.Q4_K_M.gguf",
            "size_gb": 4.4,
            "description": "Best for French language, good balance",
            "recommended_for": ["French", "Speed"],
        },
        {
            "id": "phi3-mini-q4",
            "name": "Phi-3 Mini Q4 (Ultra Fast)",
            "url": "https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf/resolve/main/Phi-3-mini-4k-instruct-q4.gguf",
            "filename": "Phi-3-mini-4k-instruct-q4.gguf",
            "size_gb": 2.2,
            "description": "Very fast, good for simple notes",
            "recommended_for": ["Speed", "Low Memory"],
        },
    ],
    "cpu_only": [
        {
            "id": "mistral-7b-instruct-q3",
            "name": "Mistral 7B Instruct Q3 (CPU Optimized)",
            "url": "https://huggingface.co/TheBloke/Mistral-7B-Instruct-v0.2-GGUF/resolve/main/mistral-7b-instruct-v0.2.Q3_K_M.gguf",
            "filename": "mistral-7b-instruct-v0.2.Q3_K_M.gguf",
            "size_gb": 3.5,
            "description": "CPU optimized, good French support",
            "recommended_for": ["French", "CPU"],
        },
        {
            "id": "phi3-mini-q3",
            "name": "Phi-3 Mini Q3 (Fastest)",
            "url": "https://huggingface.co/microsoft/Phi-3-mini-4k-instruct-gguf/resolve/main/Phi-3-mini-4k-instruct-q3_k_m.gguf",
            "filename": "Phi-3-mini-4k-instruct-q3_k_m.gguf",
            "size_gb": 1.8,
            "description": "Ultra fast on CPU, lightweight",
            "recommended_for": ["Speed", "Low Memory", "CPU"],
        },
    ],
}


def get_model_recommendations(profile: str = None) -> dict:
    """
    Get model recommendations based on hardware profile.

    Returns:
        dict with 'default' model and 'alternatives' list
    """
    if profile is None:
        profile = analyze_hardware()

    return {
        "profile": profile,
        "default": MODEL_CONFIGS.get(profile, MODEL_CONFIGS["cpu_only"]),
        "alternatives": ALTERNATIVE_MODELS.get(profile, []),
    }


def get_llm_model_path(profile: str = None) -> Path:
    """
    Get the LLM model path for a specific hardware profile.
    If no profile is provided, uses the current hardware profile.
    """
    if profile is None:
        profile = analyze_hardware()
    cfg = MODEL_CONFIGS.get(profile) or MODEL_CONFIGS["cpu_only"]
    return MODELS_DIR / cfg["filename"]

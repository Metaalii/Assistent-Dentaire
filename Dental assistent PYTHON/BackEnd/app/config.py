import os
import sys
from pathlib import Path
from typing import Tuple


# -------- Paths (dev vs frozen) --------

def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def app_base_dir() -> Path:
    """
    Base dir for *read-only* packaged assets.
    In PyInstaller onefile mode, this is sys._MEIPASS.
    In dev mode, it’s the project root-ish.
    """
    if is_frozen():
        return Path(getattr(sys, "_MEIPASS"))  # type: ignore[attr-defined]
    return Path(__file__).resolve().parent.parent


def user_data_dir(app_name: str = "DentalAssistant") -> Path:
    """
    Cross-platform, dependency-free app data directory.
    - Windows: %APPDATA%\\DentalAssistant
    - macOS:   ~/Library/Application Support/DentalAssistant
    - Linux:   ~/.local/share/DentalAssistant  (or $XDG_DATA_HOME)
    """
    if sys.platform.startswith("win"):
        root = os.getenv("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        return Path(root) / app_name

    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / app_name

    # Linux / other unix
    xdg = os.getenv("XDG_DATA_HOME")
    root = Path(xdg) if xdg else (Path.home() / ".local" / "share")
    return root / app_name


BASE_DIR = app_base_dir()

# Where models live (must be writable)
MODELS_DIR = user_data_dir() / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

# Backward-compatible “canonical” paths
# (We keep these stable so existing code keeps working.)
LLM_MODEL_PATH = MODELS_DIR / "llama-3-8b.gguf"
WHISPER_MODEL_PATH = MODELS_DIR / "whisper-small"


# -------- Hardware detection (safe when torch is absent) --------

def _try_import_torch():
    try:
        import torch  # type: ignore
        return torch
    except Exception:
        return None


def analyze_hardware() -> str:
    """
    Returns a profile: 'high_vram', 'low_vram', or 'cpu_only'.
    Safe if torch isn't installed.
    """
    torch = _try_import_torch()
    if torch is None:
        return "cpu_only"

    # CUDA
    try:
        if torch.cuda.is_available():
            vram_bytes = torch.cuda.get_device_properties(0).total_memory
            vram_gb = vram_bytes / (1024 ** 3)
            return "high_vram" if vram_gb >= 8 else "low_vram"
    except Exception:
        pass

    # Apple Silicon (MPS)
    try:
        if getattr(torch.backends, "mps", None) and torch.backends.mps.is_available():
            # Treat Apple Silicon as high-tier; compute_type will be decided elsewhere.
            return "high_vram"
    except Exception:
        pass

    return "cpu_only"


def get_device_settings() -> Tuple[str, str]:
    """
    Device settings for faster-whisper.
    Returns (device, compute_type).

    Notes:
    - faster-whisper supports device='cuda' or 'cpu' reliably.
    - On Apple Silicon, many setups run faster-whisper on CPU with int8.
    """
    profile = analyze_hardware()
    torch = _try_import_torch()

    # CUDA available
    if torch is not None:
        try:
            if torch.cuda.is_available():
                if profile == "high_vram":
                    return ("cuda", "float16")
                # Low VRAM: int8_float16 is a common tradeoff
                return ("cuda", "int8_float16")
        except Exception:
            pass

    # Default CPU
    # (If you later add explicit MPS support, this is the place.)
    return ("cpu", "int8")


# -------- Model configs --------
# IMPORTANT: filenames differ per profile to avoid ambiguity / accidental overwrites.

MODEL_CONFIGS = {
    "high_vram": {
        "url": "https://huggingface.co/TheBloke/Llama-3-8B-Instruct-GGUF/resolve/main/llama-3-8b-instruct.Q6_K.gguf",
        "filename": "llama-3-8b-instruct.Q6_K.gguf",
    },
    "low_vram": {
        "url": "https://huggingface.co/TheBloke/Llama-3-8B-Instruct-GGUF/resolve/main/llama-3-8b-instruct.Q4_K_M.gguf",
        "filename": "llama-3-8b-instruct.Q4_K_M.gguf",
    },
    "cpu_only": {
        "url": "https://huggingface.co/TheBloke/Llama-3-8B-Instruct-GGUF/resolve/main/llama-3-8b-instruct.Q4_K_S.gguf",
        "filename": "llama-3-8b-instruct.Q4_K_S.gguf",
    },
}

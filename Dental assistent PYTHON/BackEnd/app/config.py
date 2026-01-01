import os
import sys
import subprocess
import logging
from pathlib import Path
from typing import Tuple, Optional, Dict, Any

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

# Whisper model path (fixed location)
WHISPER_MODEL_PATH = MODELS_DIR / "whisper-small"


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
    """

    _cached_result: Optional[Dict[str, Any]] = None

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
        """Detect GPU via system commands (no Python GPU libraries needed)."""

        # Try NVIDIA first (most common)
        nvidia_info = cls._detect_nvidia()
        if nvidia_info:
            return nvidia_info

        # Try Apple Silicon
        apple_info = cls._detect_apple_silicon()
        if apple_info:
            return apple_info

        # Try AMD ROCm
        amd_info = cls._detect_amd()
        if amd_info:
            return amd_info

        return None

    @classmethod
    def _detect_nvidia(cls) -> Optional[Dict[str, Any]]:
        """Detect NVIDIA GPU using nvidia-smi."""
        try:
            # Query GPU name and memory
            result = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=name,memory.total",
                    "--format=csv,noheader,nounits"
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode == 0 and result.stdout.strip():
                line = result.stdout.strip().split("\n")[0]
                parts = line.split(", ")
                if len(parts) >= 2:
                    gpu_name = parts[0].strip()
                    vram_mb = float(parts[1].strip())
                    vram_gb = vram_mb / 1024

                    return {
                        "gpu_name": gpu_name,
                        "vram_gb": round(vram_gb, 1),
                        "detection_method": "nvidia_smi",
                    }
        except FileNotFoundError:
            pass  # nvidia-smi not installed
        except Exception as e:
            logger.debug("NVIDIA detection failed: %s", e)

        return None

    @classmethod
    def _detect_apple_silicon(cls) -> Optional[Dict[str, Any]]:
        """Detect Apple Silicon (M1/M2/M3) on macOS."""
        if sys.platform != "darwin":
            return None

        try:
            # Check for Apple Silicon via sysctl
            result = subprocess.run(
                ["sysctl", "-n", "machdep.cpu.brand_string"],
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode == 0:
                cpu_brand = result.stdout.strip()
                if "Apple" in cpu_brand:
                    # Get unified memory size
                    mem_result = subprocess.run(
                        ["sysctl", "-n", "hw.memsize"],
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )

                    vram_gb = None
                    if mem_result.returncode == 0:
                        total_bytes = int(mem_result.stdout.strip())
                        # Apple Silicon shares RAM with GPU, estimate ~75% available
                        vram_gb = round((total_bytes / (1024**3)) * 0.75, 1)

                    return {
                        "gpu_name": cpu_brand,
                        "vram_gb": vram_gb,
                        "detection_method": "apple_silicon",
                    }
        except Exception as e:
            logger.debug("Apple Silicon detection failed: %s", e)

        return None

    @classmethod
    def _detect_amd(cls) -> Optional[Dict[str, Any]]:
        """Detect AMD GPU using rocm-smi."""
        try:
            result = subprocess.run(
                ["rocm-smi", "--showproductname"],
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode == 0 and result.stdout.strip():
                # Parse ROCm output
                for line in result.stdout.split("\n"):
                    if "GPU" in line or "Card" in line:
                        gpu_name = line.strip()

                        # Try to get VRAM
                        vram_result = subprocess.run(
                            ["rocm-smi", "--showmeminfo", "vram"],
                            capture_output=True,
                            text=True,
                            timeout=5,
                        )

                        vram_gb = None
                        if vram_result.returncode == 0:
                            for vline in vram_result.stdout.split("\n"):
                                if "Total" in vline:
                                    # Parse VRAM in MB or GB
                                    parts = vline.split()
                                    for i, p in enumerate(parts):
                                        if p.isdigit():
                                            vram_gb = float(p) / 1024  # Assume MB
                                            break

                        return {
                            "gpu_name": gpu_name,
                            "vram_gb": round(vram_gb, 1) if vram_gb else None,
                            "detection_method": "rocm_smi",
                        }
        except FileNotFoundError:
            pass  # rocm-smi not installed
        except Exception as e:
            logger.debug("AMD detection failed: %s", e)

        return None

    @classmethod
    def _check_backend_gpu_support(cls) -> bool:
        """Check if llama-cpp-python was built with GPU support."""
        try:
            from llama_cpp import Llama

            # Check for CUDA support
            # llama-cpp-python exposes this via the library
            import llama_cpp

            # Try to detect GPU layers support
            # If the library was built with CUBLAS/Metal, it will have these
            lib_path = getattr(llama_cpp, "__file__", "")

            # On most systems, GPU-enabled builds have different binary names
            # or we can try creating a model with n_gpu_layers > 0
            # For now, we'll do a simple check

            # Check environment hints
            if os.getenv("LLAMA_CUBLAS") == "1":
                return True
            if os.getenv("LLAMA_METAL") == "1":
                return True

            # Check if CUDA libraries are loadable
            if sys.platform != "darwin":
                try:
                    import ctypes
                    ctypes.CDLL("libcudart.so")
                    return True
                except OSError:
                    pass
            else:
                # macOS Metal is usually available if on Apple Silicon
                return cls._detect_apple_silicon() is not None

            return False

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

MODEL_CONFIGS = {
    "high_vram": {
        "url": "https://huggingface.co/TheBloke/Llama-3-8B-Instruct-GGUF/resolve/main/llama-3-8b-instruct.Q6_K.gguf",
        "filename": "llama-3-8b-instruct.Q6_K.gguf",
        "size_gb": 6.6,
        "description": "Highest quality, best for powerful GPUs",
    },
    "low_vram": {
        "url": "https://huggingface.co/TheBloke/Llama-3-8B-Instruct-GGUF/resolve/main/llama-3-8b-instruct.Q4_K_M.gguf",
        "filename": "llama-3-8b-instruct.Q4_K_M.gguf",
        "size_gb": 4.4,
        "description": "Balanced quality and speed",
    },
    "cpu_only": {
        "url": "https://huggingface.co/TheBloke/Llama-3-8B-Instruct-GGUF/resolve/main/llama-3-8b-instruct.Q4_K_S.gguf",
        "filename": "llama-3-8b-instruct.Q4_K_S.gguf",
        "size_gb": 3.6,
        "description": "Optimized for CPU, smallest size",
    },
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

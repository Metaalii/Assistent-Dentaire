"""
Windows-specific platform implementation.
Handles Windows-specific paths, GPU detection, and backend support.
"""

import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from .base import PlatformBase

logger = logging.getLogger("dental_assistant.platform.windows")


class WindowsPlatform(PlatformBase):
    """Windows-specific platform operations."""

    def get_user_data_dir(self, app_name: str = "DentalAssistant") -> Path:
        """
        Get Windows user data directory.
        Uses %APPDATA%\\AppName pattern.

        Args:
            app_name: Name of the application

        Returns:
            Path to Windows AppData\\Roaming\\AppName
        """
        root = os.getenv("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        return Path(root) / app_name

    def detect_gpu(self) -> Optional[Dict[str, Any]]:
        """
        Detect GPU on Windows.
        Tries NVIDIA (nvidia-smi) and AMD (rocm-smi) detection.

        Returns:
            GPU info dict or None
        """
        # Try NVIDIA first (most common on Windows)
        nvidia_info = self._detect_nvidia()
        if nvidia_info:
            return nvidia_info

        # Try AMD ROCm (less common on Windows but possible)
        amd_info = self._detect_amd()
        if amd_info:
            return amd_info

        return None

    def _detect_nvidia(self) -> Optional[Dict[str, Any]]:
        """Detect NVIDIA GPU using nvidia-smi on Windows."""
        import subprocess

        try:
            # nvidia-smi is usually in PATH on Windows if drivers are installed
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
            logger.debug("nvidia-smi not found on Windows")
        except Exception as e:
            logger.debug("NVIDIA detection failed on Windows: %s", e)

        return None

    def _detect_amd(self) -> Optional[Dict[str, Any]]:
        """Detect AMD GPU using rocm-smi on Windows (rare but possible)."""
        import subprocess

        try:
            result = subprocess.run(
                ["rocm-smi", "--showproductname"],
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode == 0 and result.stdout.strip():
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
                                    parts = vline.split()
                                    for i, p in enumerate(parts):
                                        if p.isdigit():
                                            vram_gb = float(p) / 1024
                                            break

                        return {
                            "gpu_name": gpu_name,
                            "vram_gb": round(vram_gb, 1) if vram_gb else None,
                            "detection_method": "rocm_smi",
                        }
        except FileNotFoundError:
            logger.debug("rocm-smi not found on Windows")
        except Exception as e:
            logger.debug("AMD detection failed on Windows: %s", e)

        return None

    def check_gpu_backend_support(self) -> bool:
        """
        Check if llama-cpp-python has GPU support on Windows.
        Primarily checks for CUDA support.

        Returns:
            True if GPU backend is supported
        """
        # Check environment hints
        if os.getenv("LLAMA_CUBLAS") == "1":
            return True

        # On Windows, check for CUDA DLLs
        try:
            import ctypes
            # Try to load CUDA runtime DLL
            ctypes.CDLL("cudart64_110.dll")  # CUDA 11.x
            return True
        except OSError:
            try:
                ctypes.CDLL("cudart64_12.dll")  # CUDA 12.x
                return True
            except OSError:
                pass

        return False

    @classmethod
    def get_platform_name(cls) -> str:
        """Get the platform name."""
        return "Windows"

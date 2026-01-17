"""
Linux-specific platform implementation.
Handles Linux-specific paths, GPU detection (NVIDIA/AMD), and CUDA backend support.
"""

import os
import logging
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any
from .base import PlatformBase

logger = logging.getLogger("dental_assistant.platform.linux")


class LinuxPlatform(PlatformBase):
    """Linux-specific platform operations."""

    def get_user_data_dir(self, app_name: str = "DentalAssistant") -> Path:
        """
        Get Linux user data directory.
        Uses XDG Base Directory specification (~/.local/share/AppName).

        Args:
            app_name: Name of the application

        Returns:
            Path to $XDG_DATA_HOME/AppName or ~/.local/share/AppName
        """
        xdg = os.getenv("XDG_DATA_HOME")
        root = Path(xdg) if xdg else (Path.home() / ".local" / "share")
        return root / app_name

    def detect_gpu(self) -> Optional[Dict[str, Any]]:
        """
        Detect GPU on Linux.
        Tries NVIDIA (nvidia-smi) and AMD (rocm-smi) detection.

        Returns:
            GPU info dict or None
        """
        # Try NVIDIA first (most common for ML/AI workloads)
        nvidia_info = self._detect_nvidia()
        if nvidia_info:
            return nvidia_info

        # Try AMD ROCm (common on Linux for AMD GPUs)
        amd_info = self._detect_amd()
        if amd_info:
            return amd_info

        return None

    def _detect_nvidia(self) -> Optional[Dict[str, Any]]:
        """
        Detect NVIDIA GPU using nvidia-smi on Linux.

        Returns:
            GPU info dict or None
        """
        try:
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
            logger.debug("nvidia-smi not found on Linux")
        except Exception as e:
            logger.debug("NVIDIA detection failed on Linux: %s", e)

        return None

    def _detect_amd(self) -> Optional[Dict[str, Any]]:
        """
        Detect AMD GPU using rocm-smi on Linux.
        ROCm is primarily available on Linux.

        Returns:
            GPU info dict or None
        """
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
            logger.debug("rocm-smi not found on Linux")
        except Exception as e:
            logger.debug("AMD detection failed on Linux: %s", e)

        return None

    def check_gpu_backend_support(self) -> bool:
        """
        Check if llama-cpp-python has GPU support on Linux.
        Checks for CUDA support by trying to load CUDA runtime library.

        Returns:
            True if CUDA backend is supported
        """
        # Check environment hints
        if os.getenv("LLAMA_CUBLAS") == "1":
            return True

        # Try to load CUDA runtime library on Linux
        try:
            import ctypes
            ctypes.CDLL("libcudart.so")
            return True
        except OSError:
            # Try alternative CUDA versions
            try:
                ctypes.CDLL("libcudart.so.11")
                return True
            except OSError:
                try:
                    ctypes.CDLL("libcudart.so.12")
                    return True
                except OSError:
                    pass

        return False

    @classmethod
    def get_platform_name(cls) -> str:
        """Get the platform name."""
        return "Linux"

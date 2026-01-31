"""
Linux-specific platform implementation.
Handles Linux-specific paths, GPU detection (NVIDIA/AMD), and CUDA backend support.
"""

import os
import logging
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
        Uses shared detection methods from base class.

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

    def check_gpu_backend_support(self) -> bool:
        """
        Check if llama-cpp-python has GPU support on Linux.
        Checks for CUDA support by trying to load CUDA runtime library.

        Returns:
            True if CUDA backend is supported
        """
        # Use shared cross-platform CUDA detection from base class
        return self.check_cuda_available()

    @classmethod
    def get_platform_name(cls) -> str:
        """Get the platform name."""
        return "Linux"

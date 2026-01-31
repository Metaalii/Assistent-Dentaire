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
        Uses shared detection methods from base class.

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

    def check_gpu_backend_support(self) -> bool:
        """
        Check if llama-cpp-python has GPU support on Windows.
        Primarily checks for CUDA support.

        Returns:
            True if GPU backend is supported
        """
        # Use shared cross-platform CUDA detection from base class
        return self.check_cuda_available()

    @classmethod
    def get_platform_name(cls) -> str:
        """Get the platform name."""
        return "Windows"

"""
macOS-specific platform implementation.
Handles macOS-specific paths, Apple Silicon GPU detection, and Metal backend support.
"""

import os
import logging
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any
from .base import PlatformBase

logger = logging.getLogger("dental_assistant.platform.macos")


class MacOSPlatform(PlatformBase):
    """macOS-specific platform operations."""

    def get_user_data_dir(self, app_name: str = "DentalAssistant") -> Path:
        """
        Get macOS user data directory.
        Uses ~/Library/Application Support/AppName pattern.

        Args:
            app_name: Name of the application

        Returns:
            Path to ~/Library/Application Support/AppName
        """
        return Path.home() / "Library" / "Application Support" / app_name

    def detect_gpu(self) -> Optional[Dict[str, Any]]:
        """
        Detect GPU on macOS.
        Primarily detects Apple Silicon (M1/M2/M3/M4).
        Also checks for NVIDIA (legacy Mac Pro with eGPU) using shared base method.

        Returns:
            GPU info dict or None
        """
        # Try Apple Silicon first (most common on modern Macs)
        apple_info = self._detect_apple_silicon()
        if apple_info:
            return apple_info

        # Try NVIDIA (rare, only on older Mac Pros or eGPUs)
        nvidia_info = self._detect_nvidia()
        if nvidia_info:
            return nvidia_info

        return None

    def _detect_apple_silicon(self) -> Optional[Dict[str, Any]]:
        """
        Detect Apple Silicon (M1/M2/M3/M4) on macOS.
        Uses sysctl to check CPU brand and memory.

        Returns:
            GPU info dict or None
        """
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
            logger.debug("Apple Silicon detection failed on macOS: %s", e)

        return None

    def check_gpu_backend_support(self) -> bool:
        """
        Check if llama-cpp-python has GPU support on macOS.
        Checks for Metal backend support (Apple Silicon).

        Returns:
            True if Metal backend is supported
        """
        # Check environment hints for Metal
        if os.getenv("LLAMA_METAL") == "1":
            return True

        # Metal is usually available if we're on Apple Silicon
        apple_info = self._detect_apple_silicon()
        if apple_info is not None:
            return True

        return False

    @classmethod
    def get_platform_name(cls) -> str:
        """Get the platform name."""
        return "macOS"

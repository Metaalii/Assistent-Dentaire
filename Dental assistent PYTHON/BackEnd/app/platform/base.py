"""
Base class for platform-specific implementations.
Defines the common interface that all platform classes must implement.
"""

import logging
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger("dental_assistant.platform")


class PlatformBase(ABC):
    """Abstract base class for platform-specific operations."""

    @abstractmethod
    def get_user_data_dir(self, app_name: str = "DentalAssistant") -> Path:
        """
        Get the platform-specific user data directory.

        Args:
            app_name: Name of the application

        Returns:
            Path to the user data directory
        """
        pass

    @abstractmethod
    def detect_gpu(self) -> Optional[Dict[str, Any]]:
        """
        Detect GPU hardware on this platform.

        Returns:
            Dictionary with GPU info or None if no GPU detected:
            {
                "gpu_name": str,
                "vram_gb": float,
                "detection_method": str,
            }
        """
        pass

    @abstractmethod
    def check_gpu_backend_support(self) -> bool:
        """
        Check if llama-cpp-python has GPU support on this platform.

        Returns:
            True if GPU backend is supported, False otherwise
        """
        pass

    @classmethod
    @abstractmethod
    def get_platform_name(cls) -> str:
        """
        Get the platform name for logging.

        Returns:
            Platform name (e.g., "Windows", "macOS", "Linux")
        """
        pass

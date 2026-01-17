"""
Platform abstraction layer for OS-specific operations.

This module provides a unified interface for platform-specific operations
like getting user data directories and detecting GPU hardware.

Usage:
    from app.platform import get_platform

    platform = get_platform()
    user_dir = platform.get_user_data_dir()
    gpu_info = platform.detect_gpu()
"""

import sys
import logging
from typing import Optional
from .base import PlatformBase
from .platform_windows import WindowsPlatform
from .platform_macos import MacOSPlatform
from .platform_linux import LinuxPlatform

logger = logging.getLogger("dental_assistant.platform")

# Singleton instance
_platform_instance: Optional[PlatformBase] = None


def get_platform() -> PlatformBase:
    """
    Get the platform-specific implementation for the current operating system.

    Returns:
        Platform instance (WindowsPlatform, MacOSPlatform, or LinuxPlatform)

    Raises:
        RuntimeError: If the platform is not supported
    """
    global _platform_instance

    if _platform_instance is not None:
        return _platform_instance

    # Detect platform and create appropriate instance
    if sys.platform.startswith("win"):
        _platform_instance = WindowsPlatform()
        logger.info("Initialized Windows platform")
    elif sys.platform == "darwin":
        _platform_instance = MacOSPlatform()
        logger.info("Initialized macOS platform")
    elif sys.platform.startswith("linux"):
        _platform_instance = LinuxPlatform()
        logger.info("Initialized Linux platform")
    else:
        raise RuntimeError(f"Unsupported platform: {sys.platform}")

    return _platform_instance


def reset_platform():
    """
    Reset the platform singleton instance.
    Useful for testing or when platform detection needs to be re-run.
    """
    global _platform_instance
    _platform_instance = None


# Export public API
__all__ = [
    "get_platform",
    "reset_platform",
    "PlatformBase",
    "WindowsPlatform",
    "MacOSPlatform",
    "LinuxPlatform",
]

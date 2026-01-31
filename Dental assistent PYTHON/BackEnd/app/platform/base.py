"""
Base class for platform-specific implementations.
Defines the common interface that all platform classes must implement.
"""

import ctypes
import glob
import logging
import os
import subprocess
import sys
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Dict, Any, List

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

    def check_cuda_available(self) -> bool:
        """
        Cross-platform CUDA availability check for Windows and Linux.
        Dynamically detects CUDA runtime libraries without hardcoding versions.

        Returns:
            True if CUDA runtime is available, False otherwise
        """
        # Check environment hint first (fast path)
        if os.getenv("LLAMA_CUBLAS") == "1":
            return True

        # Platform-specific library patterns and search paths
        if sys.platform.startswith("win"):
            # Windows: cudart64_*.dll (e.g., cudart64_110.dll, cudart64_12.dll)
            lib_patterns = ["cudart64_*.dll", "cudart*.dll"]
            search_paths = self._get_windows_cuda_paths()
        elif sys.platform.startswith("linux"):
            # Linux: libcudart.so* (e.g., libcudart.so.11, libcudart.so.12)
            lib_patterns = ["libcudart.so*"]
            search_paths = self._get_linux_cuda_paths()
        else:
            # macOS uses Metal, not CUDA
            return False

        # Try to find and load CUDA runtime library
        for search_path in search_paths:
            for pattern in lib_patterns:
                full_pattern = os.path.join(search_path, pattern)
                matches = glob.glob(full_pattern)
                for lib_path in matches:
                    if self._try_load_library(lib_path):
                        logger.debug("Found CUDA runtime: %s", lib_path)
                        return True

        # Fallback: try loading by name (relies on system PATH/LD_LIBRARY_PATH)
        fallback_names = self._get_cuda_fallback_names()
        for lib_name in fallback_names:
            if self._try_load_library(lib_name):
                logger.debug("Found CUDA runtime via fallback: %s", lib_name)
                return True

        return False

    def _get_windows_cuda_paths(self) -> List[str]:
        """
        Get common CUDA installation paths on Windows.

        Note: These paths are only used for searching - the actual CUDA availability
        is verified by attempting to load the DLL with ctypes.CDLL, not by path existence.
        """
        paths = []

        # CUDA_PATH environment variable (standard NVIDIA installation)
        # We add this to search paths but verify by loading the DLL
        cuda_path = os.getenv("CUDA_PATH")
        if cuda_path:
            bin_path = os.path.join(cuda_path, "bin")
            if os.path.isdir(bin_path):
                paths.append(bin_path)

        # Common installation directories
        program_files = os.getenv("ProgramFiles", r"C:\Program Files")
        nvidia_path = os.path.join(program_files, "NVIDIA GPU Computing Toolkit", "CUDA")
        if os.path.exists(nvidia_path):
            # Find all installed CUDA versions
            try:
                for version_dir in os.listdir(nvidia_path):
                    bin_path = os.path.join(nvidia_path, version_dir, "bin")
                    if os.path.exists(bin_path):
                        paths.append(bin_path)
            except OSError:
                pass

        # System PATH directories
        system_path = os.getenv("PATH", "")
        paths.extend(system_path.split(os.pathsep))

        return paths

    def _get_linux_cuda_paths(self) -> List[str]:
        """
        Get common CUDA installation paths on Linux.

        Note: These paths are only used for searching - the actual CUDA availability
        is verified by attempting to load the library with ctypes.CDLL.
        """
        paths = [
            "/usr/local/cuda/lib64",
            "/usr/local/cuda/lib",
            "/usr/lib/x86_64-linux-gnu",
            "/usr/lib64",
            "/usr/lib",
        ]

        # CUDA_PATH environment variable
        cuda_path = os.getenv("CUDA_PATH")
        if cuda_path:
            paths.insert(0, os.path.join(cuda_path, "lib64"))
            paths.insert(1, os.path.join(cuda_path, "lib"))

        # LD_LIBRARY_PATH
        ld_path = os.getenv("LD_LIBRARY_PATH", "")
        if ld_path:
            paths.extend(ld_path.split(":"))

        return paths

    def _get_cuda_fallback_names(self) -> List[str]:
        """Get CUDA library names to try loading directly."""
        if sys.platform.startswith("win"):
            # Windows DLL names - try common versions
            return [
                "cudart64_12.dll",
                "cudart64_120.dll",
                "cudart64_110.dll",
                "cudart64_11.dll",
                "cudart64_102.dll",
                "cudart64_101.dll",
            ]
        elif sys.platform.startswith("linux"):
            return [
                "libcudart.so",
                "libcudart.so.12",
                "libcudart.so.11",
            ]
        return []

    def _try_load_library(self, lib_path: str) -> bool:
        """Attempt to load a shared library."""
        try:
            ctypes.CDLL(lib_path)
            return True
        except OSError:
            return False

    def _detect_nvidia(self) -> Optional[Dict[str, Any]]:
        """
        Detect NVIDIA GPU using nvidia-smi.
        Cross-platform method that works on Windows, Linux, and macOS.

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
            logger.debug("nvidia-smi not found")
        except Exception as e:
            logger.debug("NVIDIA detection failed: %s", e)

        return None

    def _detect_amd(self) -> Optional[Dict[str, Any]]:
        """
        Detect AMD GPU using rocm-smi.
        Cross-platform method for AMD ROCm detection.

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
                                    for p in parts:
                                        if p.isdigit():
                                            vram_gb = float(p) / 1024
                                            break

                        return {
                            "gpu_name": gpu_name,
                            "vram_gb": round(vram_gb, 1) if vram_gb else None,
                            "detection_method": "rocm_smi",
                        }
        except FileNotFoundError:
            logger.debug("rocm-smi not found")
        except Exception as e:
            logger.debug("AMD detection failed: %s", e)

        return None

#!/usr/bin/env python3
"""
Build script for creating the dental-backend executable.

This script uses PyInstaller to create a standalone executable
that Tauri can launch as a sidecar process.

Usage:
    python build_backend.py

The output will be placed in:
    - Windows: ../FrontEnd/src-tauri/binaries/dental-backend-x86_64-pc-windows-msvc.exe
    - macOS:   ../FrontEnd/src-tauri/binaries/dental-backend-aarch64-apple-darwin (or x86_64)
    - Linux:   ../FrontEnd/src-tauri/binaries/dental-backend-x86_64-unknown-linux-gnu
"""

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

# Determine the target triple for Tauri sidecar naming
def get_target_triple():
    """Get the Rust-style target triple for the current platform."""
    system = platform.system().lower()
    machine = platform.machine().lower()

    if system == "windows":
        if machine in ("amd64", "x86_64"):
            return "x86_64-pc-windows-msvc"
        elif machine in ("arm64", "aarch64"):
            return "aarch64-pc-windows-msvc"
        else:
            return "i686-pc-windows-msvc"

    elif system == "darwin":  # macOS
        if machine in ("arm64", "aarch64"):
            return "aarch64-apple-darwin"
        else:
            return "x86_64-apple-darwin"

    elif system == "linux":
        if machine in ("amd64", "x86_64"):
            return "x86_64-unknown-linux-gnu"
        elif machine in ("arm64", "aarch64"):
            return "aarch64-unknown-linux-gnu"
        else:
            return "i686-unknown-linux-gnu"

    else:
        raise RuntimeError(f"Unsupported platform: {system} {machine}")


def build_backend():
    """Build the backend executable using PyInstaller."""

    # Paths
    backend_dir = Path(__file__).parent.resolve()
    frontend_dir = backend_dir.parent / "FrontEnd"
    binaries_dir = frontend_dir / "src-tauri" / "binaries"
    main_script = backend_dir / "main.py"

    # Ensure binaries directory exists
    binaries_dir.mkdir(parents=True, exist_ok=True)

    # Get target triple
    target = get_target_triple()
    ext = ".exe" if platform.system() == "Windows" else ""
    output_name = f"dental-backend-{target}{ext}"
    output_path = binaries_dir / output_name

    print(f"Building dental-backend for {target}...")
    print(f"Output: {output_path}")

    # PyInstaller command
    pyinstaller_args = [
        sys.executable, "-m", "PyInstaller",
        "--onefile",  # Single executable
        "--name", "dental-backend",
        "--distpath", str(binaries_dir),
        "--workpath", str(backend_dir / "build"),
        "--specpath", str(backend_dir),
        # Hidden imports for dynamic dependencies
        "--hidden-import", "uvicorn.logging",
        "--hidden-import", "uvicorn.loops",
        "--hidden-import", "uvicorn.loops.auto",
        "--hidden-import", "uvicorn.protocols",
        "--hidden-import", "uvicorn.protocols.http",
        "--hidden-import", "uvicorn.protocols.http.auto",
        "--hidden-import", "uvicorn.protocols.websockets",
        "--hidden-import", "uvicorn.protocols.websockets.auto",
        "--hidden-import", "uvicorn.lifespan",
        "--hidden-import", "uvicorn.lifespan.on",
        "--hidden-import", "app",
        "--hidden-import", "app.config",
        "--hidden-import", "app.security",
        "--hidden-import", "app.middleware",
        "--hidden-import", "app.llm_config",
        "--hidden-import", "app.llm",
        "--hidden-import", "app.llm.local_llm",
        "--hidden-import", "app.llm.whisper",
        "--hidden-import", "app.platform",
        # Collect all app packages
        "--collect-all", "app",
        # Additional data files if needed
        # PyInstaller uses ';' on Windows and ':' on Unix for --add-data separator
        "--add-data", f"{backend_dir / 'app'}{os.pathsep}app",
        # Clean build
        "--clean",
        "--noconfirm",
        # Main script
        str(main_script),
    ]

    # Run PyInstaller
    try:
        subprocess.run(pyinstaller_args, check=True, cwd=backend_dir)
    except subprocess.CalledProcessError as e:
        print(f"PyInstaller failed with exit code {e.returncode}")
        sys.exit(1)

    # Rename output to include target triple
    temp_output = binaries_dir / f"dental-backend{ext}"
    if temp_output.exists():
        # Remove old file if exists
        if output_path.exists():
            output_path.unlink()
        temp_output.rename(output_path)
        print(f"Renamed {temp_output.name} -> {output_name}")

    # Make executable on Unix
    if platform.system() != "Windows":
        os.chmod(output_path, 0o755)

    # Clean up build artifacts
    build_dir = backend_dir / "build"
    if build_dir.exists():
        shutil.rmtree(build_dir)

    spec_file = backend_dir / "dental-backend.spec"
    if spec_file.exists():
        spec_file.unlink()

    print(f"\nBuild complete: {output_path}")
    print(f"Size: {output_path.stat().st_size / (1024*1024):.1f} MB")

    return output_path


if __name__ == "__main__":
    build_backend()

#!/bin/bash
# 1. Install PyInstaller
pip install pyinstaller

# 2. Run the build using the spec file
pyinstaller dental-backend.spec --clean --noconfirm

# 3. Move the result to the Tauri frontend location (The "Sidecar" step)
#    Tauri expects sidecars to have the architecture in the name.
#    e.g., dental-backend-x86_64-apple-darwin
ARCH=$(uname -m)
OS="unknown"

if [[ "$OSTYPE" == "darwin"* ]]; then
  OS="apple-darwin"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
  OS="unknown-linux-gnu"
fi

TARGET_NAME="dental-backend-${ARCH}-${OS}"

echo "Moving binary to Tauri sidecar location: ../src-tauri/binaries/${TARGET_NAME}"
mkdir -p ../src-tauri/binaries
cp -r dist/dental-backend/* ../src-tauri/binaries/
# Rename the main executable inside to match Tauri's expectation if you use single-file mode,
# but since we used COLLECT (directory mode), you point Tauri to the dir.
# Dental Assistant Backend

Quick notes to get the backend running locally.

## Prerequisites
- Python 3.11+
- (Optional) `llama-cpp-python` and `faster-whisper` if you want local model inference
- (Windows) Visual Studio Build Tools with C++ workload for compiling native dependencies

## Setup

### 1. Create and activate a virtual environment

**Windows (PowerShell):**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

**Windows (Command Prompt):**
```cmd
python -m venv .venv
.venv\Scripts\activate.bat
```

**macOS / Linux:**
```bash
python -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure models and API key
- Set `APP_API_KEY` environment variable to a secret value used by the frontend
- Place your LLM model at `models/llama-3-8b-q4.gguf` (relative to BackEnd folder)
- Place Whisper model at `models/whisper-small` (relative to BackEnd folder)

## Running the Backend

```bash
python -m uvicorn main:app --host 127.0.0.1 --port 9000
```

Or using the main module directly:
```bash
python main.py
```

## Building Standalone Executable (for Tauri Sidecar)

This creates a single executable that Tauri can launch automatically:

```bash
pip install pyinstaller
python build_backend.py
```

The executable will be placed in `../FrontEnd/src-tauri/binaries/` with the appropriate platform suffix.

## Testing

Run unit tests:
```bash
pytest
```

## Troubleshooting

### Windows: CUDA/GPU not detected
1. Install NVIDIA CUDA Toolkit from https://developer.nvidia.com/cuda-downloads
2. Ensure `nvidia-smi` command works in terminal
3. Add CUDA bin directory to PATH (e.g., `C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.0\bin`)

### Windows: Build fails with compiler errors
1. Install Visual Studio Build Tools: https://visualstudio.microsoft.com/visual-cpp-build-tools/
2. Select "Desktop development with C++" workload
3. Restart terminal after installation

### Port 9000 already in use
Change the port using:
```bash
python -m uvicorn main:app --host 127.0.0.1 --port 9001
```

## Notes
- The app enforces a 10 MB upload size limit and a small in-memory rate limiter (for dev)
- For production, use a proper external rate limiter and robust upload handling
- Heavy model dependencies (llama-cpp-python, faster-whisper) are optional

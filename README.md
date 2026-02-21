# Dental Assistant

An AI-powered desktop application for dental consultation documentation. It transcribes audio recordings of consultations, generates structured clinical notes (SmartNotes) using a local LLM, and builds a searchable history of past consultations — all running entirely on-device, with no data sent to external servers.

---

## Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
  - [1. Clone the repository](#1-clone-the-repository)
  - [2. Backend setup](#2-backend-setup)
  - [3. Frontend setup](#3-frontend-setup)
- [Configuration](#configuration)
- [Running in development](#running-in-development)
- [Building for production](#building-for-production)
- [Running the tests](#running-the-tests)
- [Data & file locations](#data--file-locations)
- [API reference](#api-reference)
- [Security & compliance](#security--compliance)

---

## Features

- **Audio transcription** — records live audio or accepts uploaded files (`.wav`, `.mp3`, `.m4a`, `.ogg`, `.webm`, `.mp4`) and transcribes them with OpenAI Whisper (runs locally via `faster-whisper`).
- **SmartNote generation** — converts raw transcription text into a structured clinical note using a quantized LLaMA 3 8B model running on-device via `llama-cpp-python`.
- **RAG-enhanced notes** — retrieves relevant dental knowledge from a local ChromaDB vector store (powered by Haystack) to ground notes in verified medical references before generation.
- **Consultation history** — saves every SmartNote to a durable append-only journal and a semantic vector index, enabling full-text and semantic search across past consultations.
- **GPU acceleration** — automatically detects NVIDIA, AMD (ROCm) and Apple Silicon GPUs and selects the appropriate model quantization and inference backend.
- **Multi-language UI** — French and English interfaces, with a language hint passed to Whisper for more accurate transcription.
- **PDF export** — exports any SmartNote as a formatted PDF document.
- **Patient-data audit trail** — every action touching patient data is logged to an append-only audit log with actor, timestamp, and outcome (see [Security & compliance](#security--compliance)).
- **Desktop app** — packaged as a native desktop application (Windows, macOS, Linux) using Tauri, with the Python backend running as a bundled sidecar process.

---

## Architecture

```
┌─────────────────────────────────────────┐
│  Tauri Desktop App (Rust)               │
│  ┌───────────────────────────────────┐  │
│  │  React 18 + TypeScript Frontend   │  │
│  │  Vite · Tailwind · i18n (FR/EN)   │  │
│  └────────────────┬──────────────────┘  │
│                   │ HTTP (localhost)     │
│  ┌────────────────▼──────────────────┐  │
│  │  FastAPI Backend (Python sidecar) │  │
│  │                                   │  │
│  │  Whisper (faster-whisper)         │  │
│  │  LLaMA 3 8B (llama-cpp-python)    │  │
│  │  Haystack RAG + ChromaDB          │  │
│  │  Append-only audit log            │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
         All data stays on-device
```

The backend exposes a REST API on `127.0.0.1:9000`. The frontend communicates with it over localhost — no internet connection is required after the initial model download.

---

## Prerequisites

### System

| Requirement | Version |
|---|---|
| Python | 3.11 or later |
| Node.js | 18 or later |
| Rust + Cargo | latest stable (for Tauri) |
| npm | 9 or later |

### Optional (for GPU acceleration)

- **NVIDIA GPU** — CUDA 11.8+ drivers + `llama-cpp-python` compiled with CUDA support
- **AMD GPU** — ROCm 5.6+ + `llama-cpp-python` compiled with ROCm support
- **Apple Silicon** — no extra driver needed; Metal is detected automatically

> Without a GPU the app runs fine in CPU-only mode, which is slower but fully functional.

---

## Installation

### 1. Clone the repository

```bash
git clone <repository-url>
cd Assistent-Dentaire
```

### 2. Backend setup

```bash
cd "Dental assistent PYTHON/BackEnd"

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate        # macOS / Linux
# .venv\Scripts\activate         # Windows

# Install dependencies
pip install -r requirements.txt
```

**GPU-accelerated install (optional)**

For NVIDIA CUDA:
```bash
CMAKE_ARGS="-DLLAMA_CUBLAS=on" pip install llama-cpp-python --force-reinstall --no-cache-dir
```

For Apple Silicon (Metal):
```bash
CMAKE_ARGS="-DLLAMA_METAL=on" pip install llama-cpp-python --force-reinstall --no-cache-dir
```

### 3. Frontend setup

```bash
cd "Dental assistent PYTHON/FrontEnd"
npm install
```

Install the Tauri CLI (if not already installed):
```bash
npm install -g @tauri-apps/cli
```

---

## Configuration

### Backend

The backend is configured via environment variables. Copy the example file and edit it:

```bash
cd "Dental assistent PYTHON/BackEnd"
cp .env.example .env
```

| Variable | Default | Description |
|---|---|---|
| `APP_API_KEY` | `dental-assistant-local-dev-key` | API key required on every request. Change this in production. |
| `ENV` | `development` | Set to `production` to enforce a non-default API key. |
| `DENTAL_ASSISTANT_DATA_DIR` | Platform-specific (see below) | Override the directory where models, the journal, and the audit log are stored. |

### Frontend

```bash
cd "Dental assistent PYTHON/FrontEnd"
cp .env.example .env
```

| Variable | Default | Description |
|---|---|---|
| `VITE_API_URL` | `http://127.0.0.1:9000` | Backend base URL. |
| `VITE_DEV_API_KEY` | dev key | Only used when running in browser mode (not in the packaged Tauri app). |

---

## Running in development

Open two terminals.

**Terminal 1 — Backend**

```bash
cd "Dental assistent PYTHON/BackEnd"
source .venv/bin/activate
python -m uvicorn main:app --host 127.0.0.1 --port 9000 --reload
```

**Terminal 2 — Frontend (browser mode)**

```bash
cd "Dental assistent PYTHON/FrontEnd"
npm run dev
```

Then open `http://localhost:3000` in your browser.

**Or run as a desktop app (Tauri dev mode)**

```bash
cd "Dental assistent PYTHON/FrontEnd"
npm run tauri dev
```

> On first launch the app will guide you through downloading the AI models (~460 MB for Whisper + ~5–7 GB for the LLM depending on your hardware profile). This only happens once; models are cached locally.

---

## Building for production

### Step 1 — Build the backend binary

The backend is compiled into a standalone executable using PyInstaller so it can be bundled as a Tauri sidecar.

```bash
cd "Dental assistent PYTHON/BackEnd"
source .venv/bin/activate
python build_backend.py
```

The output binary is written to `FrontEnd/src-tauri/binaries/dental-backend-<target-triple>`.

### Step 2 — Package the desktop app

```bash
cd "Dental assistent PYTHON/FrontEnd"
npm run tauri build
```

Tauri produces platform-specific installers:

| Platform | Output |
|---|---|
| Windows | `.exe` installer in `src-tauri/target/release/bundle/nsis/` |
| macOS | `.dmg` in `src-tauri/target/release/bundle/dmg/` |
| Linux | `.AppImage` / `.deb` in `src-tauri/target/release/bundle/` |

---

## Running the tests

```bash
cd "Dental assistent PYTHON/BackEnd"
source .venv/bin/activate

# All tests with coverage
pytest --cov=app tests/

# Specific suites
pytest tests/test_api_contracts.py      # REST contract tests
pytest tests/test_pipeline.py           # RAG pipeline tests
pytest tests/test_smartnote_eval.py     # SmartNote quality evaluation
pytest test_platform_integration.py     # Platform-specific integration tests
```

---

## Data & file locations

All runtime data is stored in a platform-specific directory that can be overridden with the `DENTAL_ASSISTANT_DATA_DIR` environment variable.

| Platform | Default path |
|---|---|
| Windows | `%APPDATA%\DentalAssistant\` |
| macOS | `~/Library/Application Support/DentalAssistant/` |
| Linux | `~/.local/share/DentalAssistant/` |

Inside that directory:

```
DentalAssistant/
├── models/
│   ├── whisper-small/          # Whisper model files (~464 MB)
│   └── Meta-Llama-3-8B-*.gguf # LLM model (~5–7 GB, profile-dependent)
├── rag_data/                   # ChromaDB vector index
├── consultations.jsonl         # Durable consultation journal (authoritative backup)
└── audit.jsonl                 # Patient-data audit log (append-only, mode 0600)
```

> The consultation journal is intentionally stored outside `rag_data/` so that wiping the ChromaDB index does not destroy the records. If the index becomes corrupted, the app automatically rebuilds it from the journal on next startup.

---

## API reference

The backend API runs on `http://127.0.0.1:9000`. All endpoints except `/health` require the `X-API-Key` header.

### Health & observability

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Liveness probe — returns model readiness status |
| `GET` | `/llm/status` | LLM inference queue status (concurrency, running, waiting) |
| `GET` | `/metrics` | Request counts, latency percentiles, recent errors |
| `GET` | `/workers/status` | Worker pool status per queue (llm, whisper, rag) |
| `GET` | `/audit/recent?n=100` | Most recent audit log entries (requires API key) |

### Transcription

| Method | Path | Description |
|---|---|---|
| `POST` | `/transcribe` | Transcribe an audio file. Body: `multipart/form-data` with `file` and optional `language` (`fr` or `en`) |

### Summarization

| Method | Path | Description |
|---|---|---|
| `POST` | `/summarize` | Generate a SmartNote from text. Body: `{"text": "..."}` |
| `POST` | `/summarize-stream` | Same, streamed via Server-Sent Events |
| `POST` | `/summarize-rag` | RAG-enhanced SmartNote (retrieves dental knowledge first) |
| `POST` | `/summarize-stream-rag` | Same, streamed via SSE |

### Consultation history

| Method | Path | Description |
|---|---|---|
| `POST` | `/consultations/save` | Save a SmartNote to history. Body: `{"smartnote": "...", "dentist_name": "...", "patient_id": "...", "consultation_type": "..."}` |
| `POST` | `/consultations/search` | Semantic search. Body: `{"query": "...", "top_k": 10}` |
| `GET` | `/consultations/export` | Export all consultations as a JSON file |
| `GET` | `/rag/status` | RAG system readiness and document counts |

### Setup

| Method | Path | Description |
|---|---|---|
| `POST` | `/setup/download` | Trigger model download |
| `GET` | `/setup/progress` | Download progress (SSE stream) |

---

## Security & compliance

### Local-only processing

All audio and patient data is processed entirely on the local machine. No data is transmitted to any external server or cloud service. Model weights are downloaded from HuggingFace once at setup time and then used offline.

### API authentication

Every request (except `/health`) must include the `X-API-Key` header matching the value of the `APP_API_KEY` environment variable. In production mode (`ENV=production`) the app refuses to start without an explicitly configured key.

### Patient-data audit trail

Every action that touches patient data is recorded in an append-only JSONL audit log (`audit.jsonl`, file mode `0600`). Each entry captures:

| Field | Example |
|---|---|
| `timestamp` | `2026-02-21T10:30:00.123456+00:00` |
| `action` | `CONSULTATION_SAVE` |
| `actor` | `Dr. Dupont` (from request body) or `local-user` |
| `resource` | `patient:P042` |
| `request_id` | correlates to backend operational logs |
| `outcome` | `success` or `failure` |
| `detail` | error message or extra context |

Audited actions: `TRANSCRIBE`, `SUMMARIZE`, `SUMMARIZE_STREAM`, `SUMMARIZE_RAG`, `SUMMARIZE_STREAM_RAG`, `CONSULTATION_SAVE`, `CONSULTATION_SEARCH`, `CONSULTATION_EXPORT`.

The audit log is readable via `GET /audit/recent` (requires API key) and is never deleted or rotated by the application.

### Input sanitization & rate limiting

All text inputs are sanitized before reaching the LLM. The API enforces per-endpoint rate limits and a 100 MB request size cap. Detailed error telemetry is collected in-process and exposed to the frontend for optional bug reporting.

# Dental Assistant Backend

Quick notes to get the backend running locally.

Prereqs:
- Python 3.11+
- (Optional) `llama-cpp-python` and `faster-whisper` if you want local model inference

Setup:
1. Create and activate a virtual environment:
   python -m venv .venv && source .venv/bin/activate
2. Install core deps:
   pip install -r requirements.txt
3. Set the API key and place model files:
   - Set `APP_API_KEY` env var to a secret value used by the frontend
   - Place your LLM model at `BackEnd/models/llama-3-8b-q4.gguf`
   - Place Whisper model at `BackEnd/models/whisper-small`

Run:
- Start the backend: `python -m uvicorn app.main:app --host 127.0.0.1 --port 9000`
- Start the frontend (see FrontEnd README / Tauri instructions)

Testing:
- Run unit tests: `pytest`

Notes:
- The app enforces a 10 MB upload size limit and a small in-memory rate limiter (for dev). For production, use a proper external rate limiter and robust upload handling.
- Heavy model dependencies are optional and can be installed separately.

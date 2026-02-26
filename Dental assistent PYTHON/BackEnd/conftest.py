"""
Shared test fixtures for the Dental Assistant backend.

Provides a TestClient with all heavy dependencies mocked out,
so tests run without GPU, models, or RAG infrastructure.
"""

from __future__ import annotations

import os
import sys
import types
from pathlib import Path
from typing import AsyncIterator
from unittest.mock import patch

import pytest


# ---------------------------------------------------------------------------
# Environment: use the default dev API key, isolated data dir
# ---------------------------------------------------------------------------
os.environ.setdefault("APP_API_KEY", "dental-assistant-local-dev-key")
os.environ["DENTAL_ASSISTANT_DATA_DIR"] = "/tmp/dental-test-data"
os.environ["RATE_LIMIT_ENABLED"] = "0"


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
API_KEY = os.environ["APP_API_KEY"]
AUTH_HEADERS = {"X-API-Key": API_KEY}

SAMPLE_TRANSCRIPTION = (
    "Bonjour, le patient se plaint d'une douleur sur la molaire 36 "
    "depuis trois jours. Examen: carie profonde occlusale. "
    "Plan: detartrage et obturation composite. "
    "Prochain rendez-vous dans deux semaines."
)

SAMPLE_SMARTNOTE = (
    "- Motif : Douleur molaire 36 depuis 3 jours\n"
    "- Antecedents : Non renseignes\n"
    "- Examen : Carie profonde occlusale 36\n"
    "- Plan : Detartrage, obturation composite\n"
    "- Risques : Pulpite evolutive\n"
    "- Recommandations : Brossage doux secteur concerne\n"
    "- Prochain RDV : 2 semaines\n"
    "- Admin : Non mentionne"
)


# ---------------------------------------------------------------------------
# Mock LLM — returns a canned SmartNote
# ---------------------------------------------------------------------------
class FakeLLM:
    """Stands in for LocalLLM during tests."""

    _instance = None

    def __new__(cls) -> "FakeLLM":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def generate(self, prompt: str, timeout=None) -> str:
        return SAMPLE_SMARTNOTE

    async def generate_stream(
        self, prompt: str, timeout=None, cancel_event=None
    ) -> AsyncIterator[str]:
        for token in SAMPLE_SMARTNOTE.split():
            yield token + " "

    def get_queue_status(self) -> dict:
        return {
            "max_concurrency": 1,
            "running": 0,
            "waiting": 0,
            "is_busy": False,
        }

    @classmethod
    def reset(cls):
        cls._instance = None


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def _reset_singletons():
    """Reset singletons between tests to avoid cross-contamination."""
    FakeLLM.reset()
    yield


@pytest.fixture()
def fake_model_path(tmp_path: Path) -> Path:
    """Create a dummy model file so model-existence checks pass."""
    model_file = tmp_path / "model.gguf"
    model_file.write_bytes(b"\x00" * 1024)
    return model_file


@pytest.fixture()
def client(tmp_path: Path):
    """
    FastAPI TestClient with all heavy deps mocked.

    Mocks:
    - app.llm.local_llm.LocalLLM → FakeLLM  (the source; lazy imports in
      endpoint functions resolve to this)
    - get_llm_model_path → tiny temp file
    - initialize_rag → no-op
    - HardwareDetector → cpu_only
    - health checks → always True
    """
    from app.worker import WorkerPool
    WorkerPool._instance = None

    model_file = tmp_path / "fake-model.gguf"
    model_file.write_bytes(b"\x00" * 1024)

    hw_info = {
        "profile": "cpu_only",
        "gpu_detected": False,
        "gpu_name": None,
        "vram_gb": None,
        "backend_gpu_support": False,
        "detection_method": "test",
    }

    # Inject a stub for app.llm.local_llm so importing it doesn't pull in
    # llama-cpp-python.  The stub exposes LocalLLM = FakeLLM.
    stub_mod = types.ModuleType("app.llm.local_llm")
    stub_mod.LocalLLM = FakeLLM  # type: ignore[attr-defined]
    stub_mod.PRIORITY_INTERACTIVE = 0  # type: ignore[attr-defined]
    stub_mod.PRIORITY_BATCH = 10  # type: ignore[attr-defined]
    saved = sys.modules.get("app.llm.local_llm")
    sys.modules["app.llm.local_llm"] = stub_mod

    with (
        patch("app.config.get_llm_model_path", return_value=model_file),
        patch("app.api.rag.get_llm_model_path", return_value=model_file),
        patch("app.api.summarize.get_llm_model_path", return_value=model_file),
        patch("app.api.rag.initialize_rag"),
        patch("app.config.HardwareDetector.detect", return_value=hw_info),
        patch("app.config.analyze_hardware", return_value="cpu_only"),
        patch("app.api.health._is_model_valid", return_value=True),
        patch("app.api.health._is_whisper_valid", return_value=True),
    ):
        from fastapi.testclient import TestClient
        from main import app
        with TestClient(app) as tc:
            yield tc

    # Restore
    if saved is not None:
        sys.modules["app.llm.local_llm"] = saved
    else:
        sys.modules.pop("app.llm.local_llm", None)
    WorkerPool._instance = None


@pytest.fixture()
def lenient_client(tmp_path: Path):
    """
    Same as ``client`` but with raise_server_exceptions=False.

    Use this when testing that the server returns 500 for unhandled exceptions
    rather than crashing.  Starlette's BaseHTTPMiddleware re-raises non-HTTP
    exceptions through the middleware stack; the TestClient default
    (raise_server_exceptions=True) surfaces them as test errors.  This fixture
    uses raise_server_exceptions=False so the test sees the actual HTTP response
    (500) instead of an exception, matching production behaviour.
    """
    from app.worker import WorkerPool
    WorkerPool._instance = None

    model_file = tmp_path / "fake-model.gguf"
    model_file.write_bytes(b"\x00" * 1024)

    hw_info = {
        "profile": "cpu_only",
        "gpu_detected": False,
        "gpu_name": None,
        "vram_gb": None,
        "backend_gpu_support": False,
        "detection_method": "test",
    }

    stub_mod = types.ModuleType("app.llm.local_llm")
    stub_mod.LocalLLM = FakeLLM  # type: ignore[attr-defined]
    stub_mod.PRIORITY_INTERACTIVE = 0  # type: ignore[attr-defined]
    stub_mod.PRIORITY_BATCH = 10  # type: ignore[attr-defined]
    saved = sys.modules.get("app.llm.local_llm")
    sys.modules["app.llm.local_llm"] = stub_mod

    with (
        patch("app.config.get_llm_model_path", return_value=model_file),
        patch("app.api.rag.get_llm_model_path", return_value=model_file),
        patch("app.api.summarize.get_llm_model_path", return_value=model_file),
        patch("app.api.rag.initialize_rag"),
        patch("app.config.HardwareDetector.detect", return_value=hw_info),
        patch("app.config.analyze_hardware", return_value="cpu_only"),
        patch("app.api.health._is_model_valid", return_value=True),
        patch("app.api.health._is_whisper_valid", return_value=True),
    ):
        from fastapi.testclient import TestClient
        from main import app
        with TestClient(app, raise_server_exceptions=False) as tc:
            yield tc

    if saved is not None:
        sys.modules["app.llm.local_llm"] = saved
    else:
        sys.modules.pop("app.llm.local_llm", None)
    WorkerPool._instance = None

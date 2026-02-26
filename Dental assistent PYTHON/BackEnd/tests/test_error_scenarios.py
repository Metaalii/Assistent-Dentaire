"""
Error scenario tests: model not loaded, inference failure, disk full,
concurrent requests.

These tests verify that the API degrades gracefully under adverse
conditions — returning well-formed error responses instead of crashing,
hanging, or returning confusing 200 OKs with garbage bodies.

Run:  pytest tests/test_error_scenarios.py -v
"""

from __future__ import annotations

import errno
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from conftest import AUTH_HEADERS, SAMPLE_TRANSCRIPTION, FakeLLM


# ===========================================================================
# Helpers
# ===========================================================================

def _nonexistent(tmp_path: Path) -> Path:
    """Return a Path that does not exist on disk."""
    return tmp_path / "does-not-exist.gguf"


# ===========================================================================
# Model not loaded
# ===========================================================================

class TestModelNotLoaded:
    """
    Every summarization endpoint must return 503 when the LLM model file
    is absent, rather than crashing or returning a misleading error.
    """

    def test_summarize_returns_503(self, client, tmp_path):
        missing = _nonexistent(tmp_path)
        with patch("app.api.summarize.get_llm_model_path", return_value=missing):
            resp = client.post(
                "/summarize",
                json={"text": SAMPLE_TRANSCRIPTION},
                headers=AUTH_HEADERS,
            )
        assert resp.status_code == 503

    def test_summarize_stream_returns_503(self, client, tmp_path):
        missing = _nonexistent(tmp_path)
        with patch("app.api.summarize.get_llm_model_path", return_value=missing):
            resp = client.post(
                "/summarize-stream",
                json={"text": SAMPLE_TRANSCRIPTION},
                headers=AUTH_HEADERS,
            )
        assert resp.status_code == 503

    def test_summarize_rag_returns_503(self, client, tmp_path):
        missing = _nonexistent(tmp_path)
        with patch("app.api.rag.get_llm_model_path", return_value=missing):
            resp = client.post(
                "/summarize-rag",
                json={"text": SAMPLE_TRANSCRIPTION},
                headers=AUTH_HEADERS,
            )
        assert resp.status_code == 503

    def test_summarize_stream_rag_returns_503(self, client, tmp_path):
        missing = _nonexistent(tmp_path)
        with patch("app.api.rag.get_llm_model_path", return_value=missing):
            resp = client.post(
                "/summarize-stream-rag",
                json={"text": SAMPLE_TRANSCRIPTION},
                headers=AUTH_HEADERS,
            )
        assert resp.status_code == 503

    def test_503_response_is_json(self, client, tmp_path):
        """503 body must be parseable JSON, not an HTML error page."""
        missing = _nonexistent(tmp_path)
        with patch("app.api.summarize.get_llm_model_path", return_value=missing):
            resp = client.post(
                "/summarize",
                json={"text": SAMPLE_TRANSCRIPTION},
                headers=AUTH_HEADERS,
            )
        # Must not raise
        data = resp.json()
        # FastAPI wraps HTTPException detail in {"detail": ...}
        assert "detail" in data

    def test_health_still_responds_when_model_missing(self, client, tmp_path):
        """/health must remain reachable even when the model file is absent."""
        missing = _nonexistent(tmp_path)
        with patch("app.api.health._is_model_valid", return_value=False):
            resp = client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"
        # models_ready is false, but the server is up
        assert resp.json()["models_ready"] is False


# ===========================================================================
# LLM inference failure
# ===========================================================================

class TestLLMInferenceFailure:
    """
    When the LLM raises an exception mid-inference the API must return 500
    with a structured body — not crash the worker or return a confusing 200.

    Uses ``lenient_client`` (raise_server_exceptions=False) because
    Starlette's BaseHTTPMiddleware surfaces non-HTTP exceptions through the
    middleware stack before the application's exception handlers can convert
    them to responses.  raise_server_exceptions=False gives us the actual
    HTTP 500 that a production client would receive.
    """

    def test_summarize_returns_500_on_llm_error(self, lenient_client):
        fake = FakeLLM()
        fake.generate = AsyncMock(side_effect=RuntimeError("GPU out of memory"))
        with patch("app.llm.local_llm.LocalLLM", return_value=fake):
            resp = lenient_client.post(
                "/summarize",
                json={"text": SAMPLE_TRANSCRIPTION},
                headers=AUTH_HEADERS,
            )
        assert resp.status_code == 500
        assert resp.json() is not None  # structured JSON, not empty

    def test_summarize_rag_returns_500_on_llm_error(self, lenient_client):
        fake = FakeLLM()
        fake.generate = AsyncMock(side_effect=RuntimeError("GPU out of memory"))
        with (
            patch("app.api.rag._get_rag_context", new_callable=AsyncMock, return_value=""),
            patch("app.llm.local_llm.LocalLLM", return_value=fake),
        ):
            resp = lenient_client.post(
                "/summarize-rag",
                json={"text": SAMPLE_TRANSCRIPTION},
                headers=AUTH_HEADERS,
            )
        assert resp.status_code == 500

    def test_subsequent_requests_succeed_after_llm_error(self, lenient_client):
        """A single inference failure must not poison the server for later requests."""
        fake_broken = FakeLLM()
        fake_broken.generate = AsyncMock(side_effect=RuntimeError("transient error"))

        # First request: broken — lenient_client receives the 500 instead of raising
        with patch("app.llm.local_llm.LocalLLM", return_value=fake_broken):
            resp_fail = lenient_client.post(
                "/summarize",
                json={"text": SAMPLE_TRANSCRIPTION},
                headers=AUTH_HEADERS,
            )
        assert resp_fail.status_code == 500

        # Reset the singleton so the next LocalLLM() call creates a fresh
        # instance without the broken generate attribute set above.
        FakeLLM.reset()

        # Second request: normal FakeLLM in place — must succeed
        resp_ok = lenient_client.post(
            "/summarize",
            json={"text": SAMPLE_TRANSCRIPTION},
            headers=AUTH_HEADERS,
        )
        assert resp_ok.status_code == 200
        assert "summary" in resp_ok.json()


# ===========================================================================
# Transcription failure
# ===========================================================================

class TestTranscriptionFailure:
    """
    When Whisper raises an exception, /transcribe must return a structured
    500 with error code INFERENCE_004 — never a bare unhandled traceback.
    """

    def test_whisper_exception_returns_500(self, client):
        broken_whisper = MagicMock()
        broken_whisper.transcribe = AsyncMock(
            side_effect=RuntimeError("CUDA error: device-side assert triggered")
        )
        wav_bytes = b"RIFF" + b"\x00" * 40
        with patch("app.llm.api.transcribe.get_whisper", return_value=broken_whisper):
            resp = client.post(
                "/transcribe",
                headers=AUTH_HEADERS,
                files={"file": ("recording.wav", wav_bytes, "audio/wav")},
            )
        assert resp.status_code == 500
        data = resp.json()
        # AppError wraps the detail; FastAPI puts it under "detail"
        detail = data.get("detail", data)
        if isinstance(detail, dict):
            assert detail.get("error_code") == "INFERENCE_004"

    def test_unsupported_format_returns_400(self, client):
        resp = client.post(
            "/transcribe",
            headers=AUTH_HEADERS,
            files={"file": ("note.pdf", b"%PDF-1.4", "application/pdf")},
        )
        assert resp.status_code == 400

    def test_missing_file_returns_422(self, client):
        resp = client.post("/transcribe", headers=AUTH_HEADERS)
        assert resp.status_code == 422


# ===========================================================================
# Disk full — audit log
# ===========================================================================

class TestDiskFullAuditLog:
    """
    audit.log_action() must NEVER propagate an OSError to the caller.
    A full disk on the audit log file should be logged but must not abort
    the clinical action that triggered it.
    """

    def test_summarize_succeeds_when_audit_write_fails(self, client):
        disk_full = OSError(errno.ENOSPC, "No space left on device")
        with patch("app.audit._write", side_effect=disk_full):
            resp = client.post(
                "/summarize",
                json={"text": SAMPLE_TRANSCRIPTION},
                headers=AUTH_HEADERS,
            )
        # The endpoint must still return 200 — audit failure is non-fatal
        assert resp.status_code == 200
        assert "summary" in resp.json()

    def test_consultation_save_succeeds_when_audit_write_fails(self, client):
        disk_full = OSError(errno.ENOSPC, "No space left on device")
        with patch("app.audit._write", side_effect=disk_full):
            resp = client.post(
                "/consultations/save",
                json={
                    "smartnote": "- Motif : douleur",
                    "dentist_name": "Dr Test",
                    "patient_id": "P001",
                },
                headers=AUTH_HEADERS,
            )
        # RAG is unavailable in tests, so the response is rag_unavailable —
        # but the key point is no 500 from the audit write failure
        assert resp.status_code == 200

    def test_transcribe_succeeds_when_audit_write_fails(self, client):
        ok_whisper = MagicMock()
        ok_whisper.transcribe = AsyncMock(return_value="bonjour le patient")
        disk_full = OSError(errno.ENOSPC, "No space left on device")
        wav_bytes = b"RIFF" + b"\x00" * 40
        with (
            patch("app.llm.api.transcribe.get_whisper", return_value=ok_whisper),
            patch("app.audit._write", side_effect=disk_full),
        ):
            resp = client.post(
                "/transcribe",
                headers=AUTH_HEADERS,
                files={"file": ("recording.wav", wav_bytes, "audio/wav")},
            )
        assert resp.status_code == 200
        assert resp.json()["text"] == "bonjour le patient"


# ===========================================================================
# Disk full — consultation journal
# ===========================================================================

class TestDiskFullJournal:
    """
    When the durable JSONL journal cannot be written (disk full),
    consultation save must return an error — it must not silently acknowledge
    a save that did not persist.
    """

    def test_journal_write_failure_surfaces_as_error(self, lenient_client):
        """
        If the underlying save raises OSError (e.g. disk full), the endpoint
        must not return {"status": "saved"} — that would be a false confirmation.

        We patch WorkerPool.run to raise the error directly so this test does
        not require Haystack (which is an optional dependency) to be installed.
        """
        import app.api.rag as rag_mod

        disk_full = OSError(errno.ENOSPC, "No space left on device")
        original = rag_mod._rag_available
        rag_mod._rag_available = True
        try:
            with patch("app.worker.WorkerPool.run", new_callable=AsyncMock, side_effect=disk_full):
                resp = lenient_client.post(
                    "/consultations/save",
                    json={
                        "smartnote": "- Motif : douleur",
                        "dentist_name": "Dr Test",
                        "patient_id": "P002",
                    },
                    headers=AUTH_HEADERS,
                )
        finally:
            rag_mod._rag_available = original

        # Must not return 200 with status "saved" — that would be a lie
        if resp.status_code == 200:
            assert resp.json().get("status") != "saved"
        else:
            assert resp.status_code in (500, 503)


# ===========================================================================
# Concurrent requests
# ===========================================================================

class TestConcurrentRequests:
    """
    Firing multiple simultaneous requests must not produce race conditions,
    data corruption, or unhandled 500s that stem from concurrency bugs
    (as opposed to expected errors like 429 rate-limit or 503 busy).
    """

    def test_concurrent_summarize_all_return_valid_status(self, client):
        """
        10 simultaneous /summarize requests should each return a well-formed
        HTTP response.  We accept 200, 429 (rate-limited), or 503 (queue
        full) — we reject any 500 caused by a race condition.
        """
        CONCURRENCY = 10
        VALID_CODES = {200, 429, 503}
        results: list[int] = []

        def call(_):
            r = client.post(
                "/summarize",
                json={"text": SAMPLE_TRANSCRIPTION},
                headers=AUTH_HEADERS,
            )
            return r.status_code

        with ThreadPoolExecutor(max_workers=CONCURRENCY) as pool:
            futures = [pool.submit(call, i) for i in range(CONCURRENCY)]
            for f in as_completed(futures):
                results.append(f.result())

        assert len(results) == CONCURRENCY
        unexpected = [c for c in results if c not in VALID_CODES]
        assert not unexpected, f"Unexpected status codes from concurrent requests: {unexpected}"

    def test_concurrent_audit_writes_no_corruption(self, tmp_path):
        """
        Simultaneous log_action() calls from multiple threads must all
        succeed and each write a complete, parseable JSON line.
        """
        import json
        import app.audit as audit_mod

        db_path = tmp_path / "concurrent_audit.jsonl"
        THREADS = 20

        errors: list[Exception] = []

        def write_entry(i):
            try:
                audit_mod.log_action(
                    action="SUMMARIZE",
                    actor=f"dentist-{i}",
                    resource="smartnote",
                    request_id=f"req-{i:04d}",
                    outcome="success",
                    path=db_path,
                )
            except Exception as exc:  # noqa: BLE001
                errors.append(exc)

        threads = [threading.Thread(target=write_entry, args=(i,)) for i in range(THREADS)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Audit write errors in concurrent test: {errors}"

        records = audit_mod.read_recent(n=THREADS + 10, path=db_path)
        assert len(records) == THREADS, (
            f"Expected {THREADS} records, got {len(records)} — "
            "some writes were lost or corrupted"
        )
        for r in records:
            assert r["action"] == "SUMMARIZE"
            assert r["outcome"] == "success"
            assert r["actor"].startswith("dentist-")

    def test_concurrent_rate_limiter_no_double_counting(self, tmp_path):
        """
        When multiple threads call _SqliteRateLimitStore.allow() simultaneously
        with max_requests=5, exactly 5 should be allowed and the rest blocked —
        never more than 5.
        """
        import time
        from app.middleware import _SqliteRateLimitStore

        store = _SqliteRateLimitStore(tmp_path / "rl.db")
        THREADS = 20
        MAX = 5
        WINDOW = 60

        allowed_count = 0
        lock = threading.Lock()

        def attempt(_):
            nonlocal allowed_count
            now = time.time()
            ok, _remaining, _retry = store.allow("testclient:heavy", MAX, WINDOW, now)
            if ok:
                with lock:
                    allowed_count += 1

        threads = [threading.Thread(target=attempt, args=(i,)) for i in range(THREADS)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert allowed_count == MAX, (
            f"Expected exactly {MAX} allowed requests, got {allowed_count}. "
            "SQLite BEGIN IMMEDIATE failed to prevent double-counting."
        )

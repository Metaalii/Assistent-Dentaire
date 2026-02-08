import logging
import os
import tempfile
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from starlette.concurrency import run_in_threadpool
from starlette.requests import Request

from app.security import verify_api_key

router = APIRouter()
logger = logging.getLogger("dental_assistant.transcribe")

# MVP: keep it simple
ALLOWED_EXTENSIONS = {".wav", ".mp3", ".m4a", ".ogg", ".webm", ".mp4"}
MAX_UPLOAD_BYTES = 100 * 1024 * 1024  # 100MB (aligns with middleware)


# Lazily create singleton so importing this module doesn't load heavy models
_whisper = None


def get_whisper():
    global _whisper
    if _whisper is None:
        # Lazy import so backend boots even without faster-whisper installed
        from app.llm.whisper import LocalWhisper  # noqa: WPS433

        _whisper = LocalWhisper()
    return _whisper


def _validate_upload(file: UploadFile) -> str:
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported extension. Allowed: {sorted(ALLOWED_EXTENSIONS)}",
        )
    return ext


def _copy_with_limit(src, dst, max_bytes: int) -> int:
    """
    Copy from src file-like object to dst file-like object with a hard cap.
    Returns bytes written. Raises HTTPException(413) if exceeded.
    """
    written = 0
    chunk_size = 1024 * 1024  # 1MB

    while True:
        chunk = src.read(chunk_size)
        if not chunk:
            break
        written += len(chunk)
        if written > max_bytes:
            raise HTTPException(status_code=413, detail="Request entity too large")
        dst.write(chunk)

    return written


@router.post("/transcribe", dependencies=[Depends(verify_api_key)])
async def transcribe_audio(
    request: Request,
    file: UploadFile = File(...),
    language: Optional[str] = Form(None),
):
    """
    Transcribe an audio file to text.
    - Validate extension
    - Stream to a secure temp file (bounded by MAX_UPLOAD_BYTES)
    - Transcribe via LocalWhisper (runs in background thread)
    - Always cleanup temp file

    Args:
        file: Audio file upload
        language: Optional language hint ("fr", "en"). Defaults to "fr".
    """
    request_id = uuid.uuid4().hex
    ext = _validate_upload(file)

    tmp_path: Optional[str] = None

    try:
        # 1) Write to a temp file with size cap (don't trust Content-Length)
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            tmp_path = tmp.name

            # UploadFile.file is a SpooledTemporaryFile; .read() is blocking.
            # Copy it off the event loop.
            await run_in_threadpool(_copy_with_limit, file.file, tmp, MAX_UPLOAD_BYTES)

        # 2) If the client disconnected, don't waste time transcribing
        if await request.is_disconnected():
            raise HTTPException(status_code=499, detail="Client closed request")

        # 3) Transcribe with language hint
        whisper = get_whisper()
        text = await whisper.transcribe(tmp_path, language=language)

        return {"text": text, "request_id": request_id}

    except HTTPException:
        # Keep clean HTTP errors as-is
        raise

    except Exception:
        logger.exception(
            "Transcription failed [request_id=%s, filename=%s]",
            request_id,
            getattr(file, "filename", "N/A"),
        )
        # Don’t leak internal errors to UI; keep request_id for debugging
        raise HTTPException(
            status_code=500,
            detail=f"Transcription failed (request_id={request_id})",
        )

    finally:
        # 4) Cleanup
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                logger.warning("Failed to remove temp file %s [request_id=%s]", tmp_path, request_id)

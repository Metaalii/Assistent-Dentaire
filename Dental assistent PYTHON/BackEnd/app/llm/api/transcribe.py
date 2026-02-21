import logging
import os
import tempfile
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, UploadFile
from starlette.concurrency import run_in_threadpool
from starlette.requests import Request

from app.audit import log_action
from app.errors import (
    AppError,
    INPUT_MISSING_FILENAME,
    INPUT_UNSUPPORTED_EXT,
    INPUT_TOO_LARGE,
    SYSTEM_CLIENT_DISCONNECTED,
    INFERENCE_TRANSCRIPTION_FAILED,
)
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
        raise AppError(INPUT_MISSING_FILENAME)

    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise AppError(
            INPUT_UNSUPPORTED_EXT,
            detail=f"Got '{ext}'. Allowed: {sorted(ALLOWED_EXTENSIONS)}",
        )
    return ext


def _copy_with_limit(src, dst, max_bytes: int) -> int:
    """
    Copy from src file-like object to dst file-like object with a hard cap.
    Returns bytes written. Raises AppError(INPUT_TOO_LARGE) if exceeded.
    """
    written = 0
    chunk_size = 1024 * 1024  # 1MB

    while True:
        chunk = src.read(chunk_size)
        if not chunk:
            break
        written += len(chunk)
        if written > max_bytes:
            raise AppError(
                INPUT_TOO_LARGE,
                detail=f"Upload exceeds {max_bytes // (1024*1024)} MB limit",
            )
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
    request_id = uuid.uuid4().hex[:12]
    ext = _validate_upload(file)

    tmp_path: Optional[str] = None

    audit_request_id = request.headers.get("x-request-id", request_id)
    audit_resource = f"audio:{getattr(file, 'filename', 'unknown')}"

    try:
        # 1) Write to a temp file with size cap (don't trust Content-Length)
        with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
            tmp_path = tmp.name

            # UploadFile.file is a SpooledTemporaryFile; .read() is blocking.
            # Copy it off the event loop.
            await run_in_threadpool(_copy_with_limit, file.file, tmp, MAX_UPLOAD_BYTES)

        # 2) If the client disconnected, don't waste time transcribing
        if await request.is_disconnected():
            raise AppError(SYSTEM_CLIENT_DISCONNECTED, request_id=request_id)

        # 3) Transcribe with language hint
        whisper = get_whisper()
        text = await whisper.transcribe(tmp_path, language=language)

        log_action(
            action="TRANSCRIBE",
            actor="local-user",
            resource=audit_resource,
            request_id=audit_request_id,
            outcome="success",
            detail=f"lang:{language or 'auto'}",
        )
        return {"text": text, "request_id": request_id}

    except AppError as exc:
        log_action(
            action="TRANSCRIBE",
            actor="local-user",
            resource=audit_resource,
            request_id=audit_request_id,
            outcome="failure",
            detail=str(exc),
        )
        raise

    except Exception:
        logger.exception(
            "[%s] Transcription failed [request_id=%s, filename=%s]",
            INFERENCE_TRANSCRIPTION_FAILED.code,
            request_id,
            getattr(file, "filename", "N/A"),
        )
        log_action(
            action="TRANSCRIBE",
            actor="local-user",
            resource=audit_resource,
            request_id=audit_request_id,
            outcome="failure",
            detail=f"filename={getattr(file, 'filename', 'N/A')}",
        )
        raise AppError(
            INFERENCE_TRANSCRIPTION_FAILED,
            request_id=request_id,
            detail=f"filename={getattr(file, 'filename', 'N/A')}",
        )

    finally:
        # 4) Cleanup
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                logger.warning(
                    "Failed to remove temp file %s [request_id=%s]",
                    tmp_path, request_id,
                )

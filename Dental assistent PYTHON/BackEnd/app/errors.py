"""
Centralized error definitions for the Dental Assistant backend.

Every error in the application maps to a unique code for easy debugging.
Codes follow the pattern: DOMAIN_NNN

Domains:
    AUTH        Authentication & authorization
    INPUT       Input validation & sanitization
    MODEL       Model availability & loading
    INFERENCE   LLM / Whisper inference
    DOWNLOAD    Model download operations
    SYSTEM      Server-level issues (rate limits, connectivity, etc.)
"""

import logging
import uuid
from dataclasses import dataclass, field
from typing import Optional

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger("dental_assistant.errors")


# ---------------------------------------------------------------------------
# Error code definitions
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ErrorDef:
    """Immutable error definition."""
    code: str
    http_status: int
    message: str


# -- Authentication ---------------------------------------------------------
AUTH_MISSING_KEY = ErrorDef("AUTH_001", 403, "API key header is missing.")
AUTH_INVALID_KEY = ErrorDef("AUTH_002", 403, "Invalid API key.")
AUTH_NOT_CONFIGURED = ErrorDef(
    "AUTH_003", 500,
    "API key must be configured in production mode. Set APP_API_KEY.",
)

# -- Input validation -------------------------------------------------------
INPUT_EMPTY_TEXT = ErrorDef("INPUT_001", 400, "Text input is empty or invalid after sanitization.")
INPUT_MISSING_FILENAME = ErrorDef("INPUT_002", 400, "Uploaded file is missing a filename.")
INPUT_UNSUPPORTED_EXT = ErrorDef("INPUT_003", 400, "Unsupported file extension.")
INPUT_TOO_LARGE = ErrorDef("INPUT_004", 413, "Request entity too large.")
INPUT_MALFORMED_HEADER = ErrorDef("INPUT_005", 400, "Malformed Content-Length header.")

# -- Model availability -----------------------------------------------------
MODEL_LLM_NOT_FOUND = ErrorDef(
    "MODEL_001", 503,
    "LLM model not downloaded. Please run setup first.",
)
MODEL_WHISPER_NOT_FOUND = ErrorDef(
    "MODEL_002", 503,
    "Whisper model not downloaded. Please download the model first.",
)
MODEL_WHISPER_EMPTY = ErrorDef(
    "MODEL_003", 503,
    "Whisper model directory is empty. Please download the model files.",
)
MODEL_LLM_DEP_MISSING = ErrorDef(
    "MODEL_004", 503,
    "LLM dependency not installed (llama-cpp-python). Install it to enable summarization.",
)
MODEL_WHISPER_DEP_MISSING = ErrorDef(
    "MODEL_005", 503,
    "Whisper dependency not installed (faster-whisper). Install it to enable transcription.",
)

# -- Inference --------------------------------------------------------------
INFERENCE_BUSY = ErrorDef(
    "INFERENCE_001", 503,
    "Server is busy processing other requests. Please try again later.",
)
INFERENCE_LLM_BAD_OUTPUT = ErrorDef(
    "INFERENCE_002", 500,
    "LLM returned an unexpected response format.",
)
INFERENCE_STREAM_ERROR = ErrorDef(
    "INFERENCE_003", 500,
    "An error occurred during streaming generation.",
)
INFERENCE_TRANSCRIPTION_FAILED = ErrorDef(
    "INFERENCE_004", 500,
    "Transcription failed.",
)

# -- Download ---------------------------------------------------------------
DOWNLOAD_ALREADY_ACTIVE = ErrorDef(
    "DOWNLOAD_001", 409,
    "A download is already in progress.",
)
DOWNLOAD_FAILED = ErrorDef(
    "DOWNLOAD_002", 500,
    "Model download failed.",
)

# -- System -----------------------------------------------------------------
SYSTEM_BACKEND_NOT_READY = ErrorDef(
    "SYSTEM_001", 503,
    "Backend is not ready yet.",
)
SYSTEM_CLIENT_DISCONNECTED = ErrorDef(
    "SYSTEM_002", 499,
    "Client closed the connection before processing completed.",
)
SYSTEM_RATE_LIMITED = ErrorDef(
    "SYSTEM_003", 429,
    "Too many requests. Please slow down.",
)
SYSTEM_INTERNAL = ErrorDef(
    "SYSTEM_004", 500,
    "Internal server error.",
)


# ---------------------------------------------------------------------------
# Application-specific exception
# ---------------------------------------------------------------------------

class AppError(HTTPException):
    """
    Structured application error.

    Carries an ``ErrorDef`` so every raised error automatically includes
    its code, HTTP status, default message, and an optional detail string
    for additional context (e.g. file paths, request IDs).

    Usage::

        raise AppError(MODEL_LLM_NOT_FOUND)
        raise AppError(INPUT_UNSUPPORTED_EXT, detail="Allowed: .wav, .mp3")
        raise AppError(INFERENCE_TRANSCRIPTION_FAILED, request_id=rid)
    """

    def __init__(
        self,
        error_def: ErrorDef,
        *,
        detail: Optional[str] = None,
        request_id: Optional[str] = None,
    ):
        self.error_def = error_def
        self.error_code = error_def.code
        self.request_id = request_id or uuid.uuid4().hex[:12]
        # ``detail`` refines the default message; if omitted, use the default.
        self._detail = detail
        super().__init__(
            status_code=error_def.http_status,
            detail=self._build_detail_dict(),
        )

    def _build_detail_dict(self) -> dict:
        return {
            "error_code": self.error_code,
            "message": self.error_def.message,
            "detail": self._detail,
            "request_id": self.request_id,
        }


# ---------------------------------------------------------------------------
# Global exception handlers (register on the FastAPI app)
# ---------------------------------------------------------------------------

async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
    """Handle ``AppError`` and return a structured JSON body."""
    body = exc._build_detail_dict()
    logger.warning(
        "[%s] %s – %s (request_id=%s)",
        exc.error_code,
        exc.error_def.message,
        exc._detail or "",
        exc.request_id,
    )
    return JSONResponse(status_code=exc.error_def.http_status, content=body)


async def generic_http_handler(_request: Request, exc: HTTPException) -> JSONResponse:
    """
    Catch any plain ``HTTPException`` that wasn't wrapped in ``AppError``
    and normalise the response to the same JSON shape.
    """
    body = {
        "error_code": "SYSTEM_004",
        "message": str(exc.detail) if isinstance(exc.detail, str) else "HTTP error",
        "detail": exc.detail if not isinstance(exc.detail, str) else None,
        "request_id": uuid.uuid4().hex[:12],
    }
    return JSONResponse(status_code=exc.status_code, content=body)


async def unhandled_error_handler(_request: Request, exc: Exception) -> JSONResponse:
    """
    Last-resort handler for truly unexpected errors.
    Logs the full traceback and returns a safe message to the client.
    """
    request_id = uuid.uuid4().hex[:12]
    logger.exception("Unhandled exception (request_id=%s)", request_id)
    body = {
        "error_code": SYSTEM_INTERNAL.code,
        "message": SYSTEM_INTERNAL.message,
        "detail": None,
        "request_id": request_id,
    }
    return JSONResponse(status_code=500, content=body)

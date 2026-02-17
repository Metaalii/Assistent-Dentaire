"""
Dental Assistant Backend — application entry point.

Responsibilities (and nothing else):
1. Load environment
2. Create the FastAPI app with lifespan
3. Register middleware
4. Mount routers
"""

import logging
from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_hardware_info
from app.middleware import MaxRequestSizeMiddleware, RateLimitMiddleware
from app.observability import RequestTracingMiddleware
from app.security import check_api_key_configured, validate_security_config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("dental_assistant")


# ---------------------------------------------------------------------------
# Lifespan: startup / shutdown
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup and shutdown events."""
    # Security
    validate_security_config()
    if check_api_key_configured():
        logger.info("API key configured from environment")

    # Hardware
    hw_info = get_hardware_info()
    logger.info(
        "Hardware detected: %s (GPU: %s, VRAM: %s GB, Backend: %s)",
        hw_info["profile"],
        hw_info.get("gpu_name", "None"),
        hw_info.get("vram_gb", "N/A"),
        "supported" if hw_info.get("backend_gpu_support") else "not supported",
    )

    # RAG (non-blocking — degrades gracefully if deps are missing)
    from app.api.rag import initialize_rag

    initialize_rag()

    yield

    logger.info("Dental Assistant Backend shutting down")


# ---------------------------------------------------------------------------
# App creation
# ---------------------------------------------------------------------------

app = FastAPI(title="Dental Assistant Backend", lifespan=lifespan)

# ---------------------------------------------------------------------------
# Middleware (evaluated bottom → top; order matters for CORS)
# ---------------------------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:1420",
        "tauri://localhost",
        "https://tauri.localhost",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["X-API-Key", "Content-Type", "X-Request-ID"],
    expose_headers=["X-Request-ID"],
)
app.add_middleware(MaxRequestSizeMiddleware, max_bytes=100 * 1024 * 1024)
app.add_middleware(RateLimitMiddleware)
# Tracing is outermost (added last → evaluated first) so it captures
# the full lifecycle including rate-limit rejections.
app.add_middleware(RequestTracingMiddleware)

# ---------------------------------------------------------------------------
# Routers
# ---------------------------------------------------------------------------

from app.api.health import router as health_router  # noqa: E402
from app.api.summarize import router as summarize_router  # noqa: E402
from app.api.setup import router as setup_router  # noqa: E402
from app.api.rag import router as rag_router  # noqa: E402
from app.llm.api.transcribe import router as transcribe_router  # noqa: E402
from app.api.error_report import router as error_report_router  # noqa: E402

app.include_router(health_router)
app.include_router(summarize_router)
app.include_router(setup_router)
app.include_router(rag_router)
app.include_router(transcribe_router)
app.include_router(error_report_router)

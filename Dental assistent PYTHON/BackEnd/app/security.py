"""
API key authentication.

Key lifecycle (desktop app — Tauri):
    1. Tauri ``main.rs`` generates a fresh UUID at startup and sets
       ``APP_API_KEY`` in the backend process environment *before* the
       FastAPI server starts.
    2. This module reads the key **once** at import time and immediately
       removes it from ``os.environ`` so it cannot be read later via
       ``/proc/{pid}/environ`` or similar side-channels.
    3. Every request is verified against the in-memory copy.

Key lifecycle (development / browser mode):
    If ``APP_API_KEY`` is absent, a cryptographically random key is
    generated via ``secrets.token_urlsafe`` and printed to stdout so a
    developer can copy it into ``FrontEnd/.env.local`` as
    ``VITE_DEV_API_KEY``.  No hardcoded default key is ever used.
"""

import os
import secrets
import logging

from fastapi.security.api_key import APIKeyHeader
from fastapi import Security

from app.errors import AppError, AUTH_INVALID_KEY, AUTH_NOT_CONFIGURED

logger = logging.getLogger("dental_assistant.security")

# ---------------------------------------------------------------------------
# Read and immediately scrub the key from the environment (C3).
# After this pop() the key is only in _api_key — not in /proc/*/environ.
# ---------------------------------------------------------------------------

_raw = os.environ.pop("APP_API_KEY", None)

if _raw:
    _api_key: str = _raw
    _is_configured: bool = True
    logger.info("API key loaded from APP_API_KEY and scrubbed from environment.")
else:
    # Generate a cryptographically random ephemeral key.
    # Never falls back to a well-known hardcoded string.
    _api_key = secrets.token_urlsafe(32)
    _is_configured = False
    logger.warning(
        "[%s] APP_API_KEY not set. Generated ephemeral key for this session: %s\n"
        "  → Copy to FrontEnd/.env.local:  VITE_DEV_API_KEY=%s",
        AUTH_NOT_CONFIGURED.code,
        _api_key,
        _api_key,
    )

# ---------------------------------------------------------------------------
# FastAPI / Starlette auth plumbing
# ---------------------------------------------------------------------------

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)


def is_production_mode() -> bool:
    """True when ENV=production or PRODUCTION=1."""
    env = os.getenv("ENV", "").lower()
    production_flag = os.getenv("PRODUCTION", "0")
    return env == "production" or production_flag == "1"


def validate_security_config() -> None:
    """Called at startup. Raises RuntimeError if production mode has no key."""
    if is_production_mode() and not _is_configured:
        raise RuntimeError(
            f"[{AUTH_NOT_CONFIGURED.code}] {AUTH_NOT_CONFIGURED.message}"
        )


async def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    """FastAPI dependency — raises AppError(AUTH_INVALID_KEY) on mismatch."""
    if api_key != _api_key:
        logger.warning("[%s] Invalid API key attempt", AUTH_INVALID_KEY.code)
        raise AppError(AUTH_INVALID_KEY)
    return api_key


def check_api_key_configured() -> bool:
    """True when the key was explicitly set via APP_API_KEY (not ephemeral)."""
    return _is_configured


def get_active_api_key() -> str:
    """Return the active API key (used by Tauri IPC handler to send to frontend)."""
    return _api_key

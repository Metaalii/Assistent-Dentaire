from fastapi.security.api_key import APIKeyHeader
from fastapi import Security
import os
import logging

from app.errors import AppError, AUTH_INVALID_KEY, AUTH_NOT_CONFIGURED

logger = logging.getLogger("dental_assistant.security")

# Default development API key for local development
# This matches the frontend default so the app works out of the box
DEFAULT_DEV_KEY = "dental-assistant-local-dev-key"

# Centralized auth helpers to avoid circular imports
# Read the API key at verification time (not import time) so tests and
# runtime which set APP_API_KEY after import continue to work.
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)


def is_production_mode() -> bool:
    """
    Check if running in production mode.
    Production is detected via ENV=production or PRODUCTION=1 environment variable.
    """
    env = os.getenv("ENV", "").lower()
    production_flag = os.getenv("PRODUCTION", "0")
    return env == "production" or production_flag == "1"


def validate_security_config():
    """
    Validate security configuration at startup.
    Raises RuntimeError in production if API key is not configured.
    """
    if is_production_mode() and not check_api_key_configured():
        raise RuntimeError(
            f"[{AUTH_NOT_CONFIGURED.code}] {AUTH_NOT_CONFIGURED.message}"
        )

    if not check_api_key_configured():
        logger.warning(
            "[%s] Using default development API key. "
            "Set APP_API_KEY environment variable for production.",
            AUTH_NOT_CONFIGURED.code,
        )


async def verify_api_key(api_key: str = Security(api_key_header)):
    """
    Verify the API key from request headers.

    Raises:
        AppError: AUTH_INVALID_KEY if the key does not match.
    """
    expected = os.getenv("APP_API_KEY", DEFAULT_DEV_KEY)

    if api_key != expected:
        logger.warning("[%s] Invalid API key attempt", AUTH_INVALID_KEY.code)
        raise AppError(AUTH_INVALID_KEY)

    return api_key


def check_api_key_configured() -> bool:
    """
    Check if API key is explicitly configured at startup.
    Returns True if configured via environment variable, False if using default.
    """
    return os.getenv("APP_API_KEY") is not None

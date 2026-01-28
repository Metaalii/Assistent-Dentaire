from fastapi.security.api_key import APIKeyHeader
from fastapi import Security, HTTPException
import os
import logging

logger = logging.getLogger("dental_assistant.security")

# Default development API key - used when APP_API_KEY is not set
# This allows easy local development without manual configuration
DEV_API_KEY = "dev-dental-assistant-key"

# Centralized auth helpers to avoid circular imports
# Read the API key at verification time (not import time) so tests and
# runtime which set APP_API_KEY after import continue to work.
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)


async def verify_api_key(api_key: str = Security(api_key_header)):
    """
    Verify the API key from request headers.

    Raises:
        HTTPException: 403 if invalid key
    """
    expected = os.getenv("APP_API_KEY")

    # Use default dev key if not configured
    if expected is None:
        logger.warning("APP_API_KEY not set, using default dev key")
        expected = DEV_API_KEY

    # Invalid API key provided
    if api_key != expected:
        logger.warning("Invalid API key attempt")
        raise HTTPException(
            status_code=403,
            detail="Invalid API key"
        )

    return api_key


def check_api_key_configured() -> bool:
    """
    Check if API key is configured at startup.
    Returns True always (uses default dev key if not set).
    """
    return True


def is_using_dev_key() -> bool:
    """Check if using the default development key."""
    return os.getenv("APP_API_KEY") is None

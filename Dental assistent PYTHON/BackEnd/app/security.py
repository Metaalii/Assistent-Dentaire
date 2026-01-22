from fastapi.security.api_key import APIKeyHeader
from fastapi import Security, HTTPException
import os
import logging

logger = logging.getLogger("dental_assistant.security")

# Centralized auth helpers to avoid circular imports
# Read the API key at verification time (not import time) so tests and
# runtime which set APP_API_KEY after import continue to work.
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)


async def verify_api_key(api_key: str = Security(api_key_header)):
    """
    Verify the API key from request headers.

    Raises:
        HTTPException: 500 if API key not configured, 403 if invalid key
    """
    expected = os.getenv("APP_API_KEY")

    # Server misconfiguration - API key not set
    if expected is None:
        logger.error("APP_API_KEY environment variable not set!")
        raise HTTPException(
            status_code=500,
            detail="Server misconfiguration: API authentication not properly configured"
        )

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
    Returns True if configured, False otherwise.
    """
    return os.getenv("APP_API_KEY") is not None

from fastapi.security.api_key import APIKeyHeader
from fastapi import Security, HTTPException
import os

# Centralized auth helpers to avoid circular imports
# Read the API key at verification time (not import time) so tests and
# runtime which set APP_API_KEY after import continue to work.
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)


async def verify_api_key(api_key: str = Security(api_key_header)):
    expected = os.getenv("APP_API_KEY")
    if expected is None or api_key != expected:
        raise HTTPException(status_code=403, detail="Could not validate credentials")
    return api_key

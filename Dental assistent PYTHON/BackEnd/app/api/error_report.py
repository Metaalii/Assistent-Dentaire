"""
User-facing bug-report endpoints.

Flow (frontend → backend):
1. Frontend polls  GET  /errors/pending   → list of unacknowledged 5xx errors.
2. For each error the UI asks: "A bug occurred — send a report to help improve the app?"
3. User accepts  → POST /errors/{error_id}/report   (relays to developer endpoint)
   User declines → POST /errors/{error_id}/dismiss  (removes from pending, nothing sent)

The developer endpoint URL is read from the BUG_REPORT_URL environment variable.
When the variable is not set the report is accepted locally but *not* forwarded
(so the feature degrades gracefully until you configure your website).
"""

import logging
import os
import platform
import time

import requests as http_client
from fastapi import APIRouter
from pydantic import BaseModel

from app.observability import MetricsCollector

router = APIRouter(prefix="/errors", tags=["error-report"])
logger = logging.getLogger("dental_assistant.error_report")

# Will be set to your website URL later.
# Example: BUG_REPORT_URL=https://your-site.com/api/bug-reports
_DEVELOPER_URL = os.getenv("BUG_REPORT_URL", "")

# Timeout for the outbound HTTP call (seconds)
_SEND_TIMEOUT = int(os.getenv("BUG_REPORT_TIMEOUT", "10"))


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class UserContext(BaseModel):
    """Optional extra context the user can attach when accepting a report."""
    description: str = ""


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/pending")
async def pending_errors():
    """
    Return errors the user hasn't acted on yet.

    The frontend should poll this (or call it after receiving a 5xx)
    and show a prompt for each entry.
    """
    errors = MetricsCollector().get_pending_errors()
    return {"pending": errors, "count": len(errors)}


@router.post("/{error_id}/report")
async def report_error(error_id: str, ctx: UserContext | None = None):
    """
    User accepted — send the bug report to the developer endpoint.

    If BUG_REPORT_URL is not configured yet the error is acknowledged
    locally and a warning is logged, but no HTTP call is made.
    """
    collector = MetricsCollector()
    error = collector.pop_error(error_id)
    if error is None:
        return {"status": "not_found", "detail": "Error already reported or dismissed."}

    payload = {
        "error": error,
        "user_description": ctx.description if ctx else "",
        "reported_at": time.time(),
        "environment": {
            "platform": platform.system(),
            "platform_version": platform.version(),
            "python": platform.python_version(),
        },
    }

    if not _DEVELOPER_URL:
        logger.warning(
            "BUG_REPORT_URL not configured — report for error %s saved locally only",
            error_id,
        )
        return {
            "status": "accepted_locally",
            "detail": "Report saved. Developer endpoint not configured yet.",
            "error_id": error_id,
        }

    # Forward to developer website
    try:
        resp = http_client.post(
            _DEVELOPER_URL,
            json=payload,
            timeout=_SEND_TIMEOUT,
            headers={"Content-Type": "application/json"},
        )
        resp.raise_for_status()
        logger.info("Bug report %s sent to developer endpoint (%d)", error_id, resp.status_code)
        return {"status": "sent", "error_id": error_id}
    except http_client.RequestException as exc:
        logger.error("Failed to send bug report %s: %s", error_id, exc)
        return {
            "status": "send_failed",
            "detail": "Could not reach the developer endpoint. Report saved locally.",
            "error_id": error_id,
        }


@router.post("/{error_id}/dismiss")
async def dismiss_error(error_id: str):
    """User declined — remove from pending without sending anything."""
    collector = MetricsCollector()
    error = collector.pop_error(error_id)
    if error is None:
        return {"status": "not_found", "detail": "Error already reported or dismissed."}
    return {"status": "dismissed", "error_id": error_id}

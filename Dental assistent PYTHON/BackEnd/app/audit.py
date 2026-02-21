"""
Append-only JSONL audit trail for all actions touching patient data.

In healthcare every create/read/update on patient data must be logged with
who performed the action, what they did, and when.  This module provides
that log.  It is intentionally separate from the operational observability
module (observability.py), which tracks HTTP metrics — not user intent.

File location: ``user_data_dir() / "audit.jsonl"``
Permissions  : 0o600 (owner read/write only — patient data is sensitive)

Each line is a JSON object with:

    timestamp   ISO 8601 UTC timestamp
    action      upper-case verb: TRANSCRIBE, SUMMARIZE, CONSULTATION_SAVE,
                CONSULTATION_SEARCH, CONSULTATION_EXPORT, …
    actor       dentist name when present in the request body, otherwise
                "local-user" (the API key already authenticated the caller)
    resource    what was acted on — patient ID, filename, "all", etc.
    request_id  correlates to RequestTracingMiddleware and operational logs
    outcome     "success" | "failure"
    detail      free-form context string (error message on failure, etc.)
"""

import json
import logging
import os
import threading
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger("dental_assistant.audit")

_write_lock = threading.Lock()


def _default_path() -> Path:
    from app.config import user_data_dir

    return user_data_dir() / "audit.jsonl"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def log_action(
    *,
    action: str,
    actor: str,
    resource: str,
    request_id: str = "",
    outcome: str = "success",
    detail: str = "",
    path: Path | None = None,
) -> None:
    """Append a single audit record.

    Never raises — audit failures are logged but must not abort the request
    that triggered them.
    """
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "actor": actor or "local-user",
        "resource": resource,
        "request_id": request_id,
        "outcome": outcome,
        "detail": detail[:500] if detail else "",
    }
    try:
        _write(record, path=path or _default_path())
    except Exception:
        logger.exception("Failed to write audit record: action=%s resource=%s", action, resource)


def read_recent(n: int = 100, *, path: Path | None = None) -> list[dict]:
    """Return the *n* most recent audit records (tail of the file)."""
    path = path or _default_path()
    if not path.exists():
        return []

    lines: list[str] = []
    with open(path, "r", encoding="utf-8") as f:
        for raw in f:
            raw = raw.strip()
            if raw:
                lines.append(raw)

    records: list[dict] = []
    for raw in lines[-n:]:
        try:
            records.append(json.loads(raw))
        except json.JSONDecodeError:
            pass
    return records


# ---------------------------------------------------------------------------
# Internal write helper
# ---------------------------------------------------------------------------

def _write(record: dict, *, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record, ensure_ascii=False) + "\n"

    with _write_lock:
        # 0o600: audit log is patient-sensitive; only the owner should read it
        fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
        try:
            os.write(fd, line.encode("utf-8"))
            os.fsync(fd)
        finally:
            os.close(fd)

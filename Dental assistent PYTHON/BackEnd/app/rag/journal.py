"""
Append-only JSONL journal for consultation records.

Every consultation is written here *before* being indexed into ChromaDB.
If ChromaDB files corrupt, the journal is the authoritative backup and
can be used to rebuild the vector index from scratch.

File location: ``user_data_dir() / "consultations.jsonl"``
(deliberately outside the ``rag_data/`` directory so that wiping
ChromaDB does not destroy the journal).
"""

import json
import logging
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import List

logger = logging.getLogger("dental_assistant.rag.journal")

# All writes go through this lock to guarantee one writer at a time.
_write_lock = threading.Lock()


def _default_path() -> Path:
    """Journal lives next to, but outside, the ChromaDB rag_data dir."""
    from app.config import user_data_dir

    return user_data_dir() / "consultations.jsonl"


def append(
    record: dict,
    *,
    path: Path | None = None,
) -> None:
    """
    Append a single consultation record to the journal.

    Writes are flushed and fsynced so the record survives a crash
    immediately after this call returns.
    """
    path = path or _default_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    line = json.dumps(record, ensure_ascii=False, default=str) + "\n"

    with _write_lock:
        fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
        try:
            os.write(fd, line.encode("utf-8"))
            os.fsync(fd)
        finally:
            os.close(fd)


def read_all(*, path: Path | None = None) -> List[dict]:
    """
    Read every record from the journal.

    Skips malformed lines (e.g. partial writes from a hard crash)
    rather than failing entirely.
    """
    path = path or _default_path()
    if not path.exists():
        return []

    records: list[dict] = []
    with open(path, "r", encoding="utf-8") as f:
        for lineno, raw in enumerate(f, 1):
            raw = raw.strip()
            if not raw:
                continue
            try:
                records.append(json.loads(raw))
            except json.JSONDecodeError:
                logger.warning("Skipping malformed journal line %d", lineno)
    return records


def count(*, path: Path | None = None) -> int:
    """Return the number of records without loading them all into memory."""
    path = path or _default_path()
    if not path.exists():
        return 0
    n = 0
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                n += 1
    return n

"""
Persistent document store for dental consultations and knowledge base.

Uses ChromaDB via Haystack for local-first vector storage.
All data stays on the machine - no cloud services required.
"""

import logging
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger("dental_assistant.rag.store")

# Embedding model: multilingual for French dental terminology
EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


class DentalDocumentStore:
    """
    Singleton wrapper around ChromaDB-backed Haystack document store.

    Manages two collections:
    - consultations: past SmartNotes for history & semantic search
    - knowledge: dental guidelines, protocols, drug databases
    """

    _instance: Optional["DentalDocumentStore"] = None
    _instance_lock = threading.Lock()

    def __new__(cls, persist_dir: Optional[Path] = None) -> "DentalDocumentStore":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    inst = super().__new__(cls)
                    inst._initialized = False
                    cls._instance = inst
        return cls._instance

    def initialize(self, persist_dir: Path) -> None:
        """Lazy initialization - avoids heavy imports at module load time."""
        if self._initialized:
            return

        with self._instance_lock:
            if self._initialized:
                return

            try:
                from haystack_integrations.document_stores.chroma import (
                    ChromaDocumentStore,
                )

                self._persist_dir = persist_dir
                persist_dir.mkdir(parents=True, exist_ok=True)

                self._consultations_store = ChromaDocumentStore(
                    collection_name="consultations",
                    persist_path=str(persist_dir / "consultations"),
                )
                self._knowledge_store = ChromaDocumentStore(
                    collection_name="knowledge",
                    persist_path=str(persist_dir / "knowledge"),
                )
                self._initialized = True
                logger.info(
                    "Document stores initialized at %s", persist_dir
                )
            except ImportError:
                logger.warning(
                    "Haystack ChromaDB integration not installed. "
                    "RAG features disabled. Install with: "
                    "pip install chroma-haystack"
                )
                self._initialized = False
                raise

    @property
    def is_ready(self) -> bool:
        return self._initialized

    @property
    def consultations(self):
        """Access the consultations document store."""
        if not self._initialized:
            raise RuntimeError("Document store not initialized. Call initialize() first.")
        return self._consultations_store

    @property
    def knowledge(self):
        """Access the knowledge base document store."""
        if not self._initialized:
            raise RuntimeError("Document store not initialized. Call initialize() first.")
        return self._knowledge_store

    def get_stats(self) -> dict:
        """Return document counts for both collections."""
        if not self._initialized:
            return {
                "initialized": False,
                "consultations_count": 0,
                "knowledge_count": 0,
            }
        return {
            "initialized": True,
            "consultations_count": self._consultations_store.count_documents(),
            "knowledge_count": self._knowledge_store.count_documents(),
            "persist_dir": str(self._persist_dir),
        }

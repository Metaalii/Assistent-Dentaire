"""
Haystack pipelines for dental RAG operations.

Pipelines:
- Indexing: embed and store documents (consultations or knowledge)
- Retrieval: semantic search across stored documents
- RAG context: retrieve relevant knowledge for SmartNote generation
"""

import logging
import threading
from datetime import datetime
from typing import Optional

from haystack import Document, Pipeline
from haystack.components.writers import DocumentWriter
from haystack.document_stores.types import DuplicatePolicy

from app.rag.store import DentalDocumentStore, EMBEDDING_MODEL

logger = logging.getLogger("dental_assistant.rag.pipelines")


class DentalRAGPipeline:
    """
    Manages all Haystack pipelines for the dental assistant.

    Provides:
    - save_consultation(): index a completed SmartNote
    - search_consultations(): semantic search across past notes
    - get_rag_context(): retrieve relevant knowledge for a transcription
    - index_knowledge(): add dental guidelines/protocols to knowledge base
    """

    _instance: Optional["DentalRAGPipeline"] = None
    _instance_lock = threading.Lock()

    def __new__(cls) -> "DentalRAGPipeline":
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    inst = super().__new__(cls)
                    inst._initialized = False
                    cls._instance = inst
        return cls._instance

    def initialize(self, store: DentalDocumentStore) -> None:
        """Build all pipelines. Call after DentalDocumentStore.initialize()."""
        if self._initialized:
            return

        with self._instance_lock:
            if self._initialized:
                return

            self._store = store
            self._build_consultation_pipelines()
            self._build_knowledge_pipelines()
            self._initialized = True
            logger.info("RAG pipelines initialized")

    @property
    def is_ready(self) -> bool:
        return self._initialized

    # ------------------------------------------------------------------
    # Consultation pipelines
    # ------------------------------------------------------------------

    def _build_consultation_pipelines(self) -> None:
        """Build indexing and search pipelines for consultations."""
        from haystack.components.embedders import (
            SentenceTransformersDocumentEmbedder,
            SentenceTransformersTextEmbedder,
        )
        from haystack_integrations.components.retrievers.chroma import (
            ChromaEmbeddingRetriever,
        )

        # Indexing pipeline: embed + write consultation documents
        self._consultation_indexer = Pipeline()
        self._consultation_indexer.add_component(
            "embedder",
            SentenceTransformersDocumentEmbedder(model=EMBEDDING_MODEL),
        )
        self._consultation_indexer.add_component(
            "writer",
            DocumentWriter(
                document_store=self._store.consultations,
                policy=DuplicatePolicy.SKIP,
            ),
        )
        self._consultation_indexer.connect("embedder.documents", "writer.documents")

        # Search pipeline: embed query + retrieve similar consultations
        self._consultation_searcher = Pipeline()
        self._consultation_searcher.add_component(
            "embedder",
            SentenceTransformersTextEmbedder(model=EMBEDDING_MODEL),
        )
        self._consultation_searcher.add_component(
            "retriever",
            ChromaEmbeddingRetriever(
                document_store=self._store.consultations,
                top_k=10,
            ),
        )
        self._consultation_searcher.connect(
            "embedder.embedding", "retriever.query_embedding"
        )

    def save_consultation(
        self,
        smartnote: str,
        transcription: str = "",
        dentist_name: str = "",
        consultation_type: str = "",
        patient_id: str = "",
    ) -> dict:
        """
        Save a completed SmartNote to the consultation archive.

        Stores both the SmartNote and transcription as searchable content.
        """
        if not self._initialized:
            return {"status": "error", "detail": "RAG not initialized"}

        now = datetime.now()
        # Combine SmartNote and transcription for richer semantic search
        content = smartnote
        if transcription:
            content = f"{smartnote}\n\n---\nTranscription:\n{transcription}"

        doc = Document(
            content=content,
            meta={
                "type": "consultation",
                "smartnote": smartnote,
                "transcription": transcription,
                "dentist_name": dentist_name,
                "consultation_type": consultation_type,
                "patient_id": patient_id,
                "date": now.isoformat(),
                "date_display": now.strftime("%d/%m/%Y %H:%M"),
            },
        )

        try:
            self._consultation_indexer.run(
                {"embedder": {"documents": [doc]}}
            )
            logger.info("Consultation saved: %s", now.isoformat())
            return {"status": "saved", "date": now.isoformat()}
        except Exception as e:
            logger.exception("Failed to save consultation")
            return {"status": "error", "detail": str(e)}

    def search_consultations(self, query: str, top_k: int = 10) -> list[dict]:
        """
        Semantic search across past consultations.

        Returns a list of consultation results with metadata and relevance score.
        """
        if not self._initialized:
            return []

        try:
            result = self._consultation_searcher.run(
                {
                    "embedder": {"text": query},
                    "retriever": {"top_k": top_k},
                }
            )
            documents = result.get("retriever", {}).get("documents", [])

            return [
                {
                    "smartnote": doc.meta.get("smartnote", doc.content),
                    "transcription": doc.meta.get("transcription", ""),
                    "date": doc.meta.get("date", ""),
                    "date_display": doc.meta.get("date_display", ""),
                    "dentist_name": doc.meta.get("dentist_name", ""),
                    "consultation_type": doc.meta.get("consultation_type", ""),
                    "patient_id": doc.meta.get("patient_id", ""),
                    "score": doc.score if doc.score is not None else 0.0,
                }
                for doc in documents
            ]
        except Exception as e:
            logger.exception("Consultation search failed")
            return []

    # ------------------------------------------------------------------
    # Knowledge base pipelines
    # ------------------------------------------------------------------

    def _build_knowledge_pipelines(self) -> None:
        """Build indexing and retrieval pipelines for dental knowledge."""
        from haystack.components.embedders import (
            SentenceTransformersDocumentEmbedder,
            SentenceTransformersTextEmbedder,
        )
        from haystack_integrations.components.retrievers.chroma import (
            ChromaEmbeddingRetriever,
        )

        # Indexing pipeline for knowledge documents
        self._knowledge_indexer = Pipeline()
        self._knowledge_indexer.add_component(
            "embedder",
            SentenceTransformersDocumentEmbedder(model=EMBEDDING_MODEL),
        )
        self._knowledge_indexer.add_component(
            "writer",
            DocumentWriter(
                document_store=self._store.knowledge,
                policy=DuplicatePolicy.SKIP,
            ),
        )
        self._knowledge_indexer.connect("embedder.documents", "writer.documents")

        # Retrieval pipeline for RAG context
        self._knowledge_retriever = Pipeline()
        self._knowledge_retriever.add_component(
            "embedder",
            SentenceTransformersTextEmbedder(model=EMBEDDING_MODEL),
        )
        self._knowledge_retriever.add_component(
            "retriever",
            ChromaEmbeddingRetriever(
                document_store=self._store.knowledge,
                top_k=5,
            ),
        )
        self._knowledge_retriever.connect(
            "embedder.embedding", "retriever.query_embedding"
        )

    def index_knowledge(self, documents: list[Document]) -> dict:
        """Index dental knowledge documents (guidelines, protocols, etc.)."""
        if not self._initialized:
            return {"status": "error", "detail": "RAG not initialized"}

        try:
            result = self._knowledge_indexer.run(
                {"embedder": {"documents": documents}}
            )
            written = result.get("writer", {}).get("documents_written", 0)
            logger.info("Indexed %d knowledge documents", written)
            return {"status": "indexed", "documents_written": written}
        except Exception as e:
            logger.exception("Knowledge indexing failed")
            return {"status": "error", "detail": str(e)}

    def get_rag_context(self, transcription: str, top_k: int = 5) -> str:
        """
        Retrieve relevant dental knowledge for a transcription.

        Returns formatted context string to inject into the LLM prompt.
        Returns empty string if no relevant knowledge found or RAG not ready.
        """
        if not self._initialized:
            return ""

        # Check if knowledge base has documents
        if self._store.knowledge.count_documents() == 0:
            return ""

        try:
            result = self._knowledge_retriever.run(
                {
                    "embedder": {"text": transcription},
                    "retriever": {"top_k": top_k},
                }
            )
            documents = result.get("retriever", {}).get("documents", [])

            if not documents:
                return ""

            # Format retrieved context for the LLM prompt
            context_parts = []
            for i, doc in enumerate(documents, 1):
                source = doc.meta.get("source", "Reference")
                category = doc.meta.get("category", "")
                prefix = f"[{source}]" if not category else f"[{source} - {category}]"
                context_parts.append(f"{prefix}\n{doc.content}")

            return "\n\n".join(context_parts)

        except Exception as e:
            logger.warning("RAG context retrieval failed: %s", e)
            return ""

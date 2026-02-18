"""
RAG (Retrieval-Augmented Generation) module for Dental Assistant.

Provides:
- Persistent vector storage via ChromaDB + Haystack
- Semantic search across past consultations
- RAG-enhanced SmartNote generation with dental knowledge retrieval
"""

from app.rag.store import DentalDocumentStore
from app.rag.pipelines import DentalRAGPipeline

__all__ = ["DentalDocumentStore", "DentalRAGPipeline"]

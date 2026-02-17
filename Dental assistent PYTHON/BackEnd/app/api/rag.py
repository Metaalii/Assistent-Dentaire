"""
RAG & consultation history endpoints.

GET  /rag/status              — RAG system availability + document counts
POST /consultations/save      — save a SmartNote to history
POST /consultations/search    — semantic search across past notes
POST /summarize-rag           — RAG-enhanced SmartNote (blocking)
POST /summarize-stream-rag    — RAG-enhanced SmartNote (SSE streaming)
"""

import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.config import RAG_DATA_DIR, get_llm_model_path
from app.llm_config import build_rag_smartnote_prompt
from app.sanitize import sanitize_input
from app.security import verify_api_key

router = APIRouter(tags=["rag"])
logger = logging.getLogger("dental_assistant.rag")

# ---------------------------------------------------------------------------
# Module-level RAG readiness flag
# ---------------------------------------------------------------------------
_rag_available = False


def is_rag_available() -> bool:
    return _rag_available


def initialize_rag() -> None:
    """
    Initialize RAG system at startup.

    Non-fatal: if Haystack/ChromaDB are not installed the app still works
    without RAG features.
    """
    global _rag_available
    try:
        from app.rag.store import DentalDocumentStore
        from app.rag.pipelines import DentalRAGPipeline
        from app.rag.dental_knowledge import get_seed_knowledge

        store = DentalDocumentStore()
        store.initialize(RAG_DATA_DIR)

        pipeline = DentalRAGPipeline()
        pipeline.initialize(store)

        # Seed knowledge base on first run
        stats = store.get_stats()
        if stats["knowledge_count"] == 0:
            logger.info("Seeding dental knowledge base...")
            seed_docs = get_seed_knowledge()
            result = pipeline.index_knowledge(seed_docs)
            logger.info("Seeded %s knowledge documents", result.get("documents_written", 0))

        _rag_available = True
        logger.info(
            "RAG system ready: %d knowledge docs, %d consultations",
            stats.get("knowledge_count", 0) or len(get_seed_knowledge()),
            stats.get("consultations_count", 0),
        )
    except ImportError:
        logger.info(
            "RAG dependencies not installed (haystack-ai, chroma-haystack). "
            "RAG features disabled. Install with: "
            "pip install haystack-ai chroma-haystack sentence-transformers"
        )
    except Exception:
        logger.exception("Failed to initialize RAG system. RAG features disabled.")


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class SummaryRequest(BaseModel):
    text: str


class SaveConsultationRequest(BaseModel):
    smartnote: str
    transcription: str = ""
    dentist_name: str = ""
    consultation_type: str = ""
    patient_id: str = ""


class SearchRequest(BaseModel):
    query: str
    top_k: int = 10


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/rag/status")
async def rag_status():
    """Check RAG system status and document counts."""
    if not _rag_available:
        return {
            "available": False,
            "detail": "RAG dependencies not installed",
            "consultations_count": 0,
            "knowledge_count": 0,
        }
    try:
        from app.rag.store import DentalDocumentStore

        store = DentalDocumentStore()
        stats = store.get_stats()
        return {"available": True, **stats}
    except Exception as e:
        return {"available": False, "detail": str(e)}


@router.post("/consultations/save", dependencies=[Depends(verify_api_key)])
async def save_consultation(req: SaveConsultationRequest):
    """Save a completed SmartNote to the consultation archive."""
    if not _rag_available:
        return {"status": "rag_unavailable", "detail": "RAG system not available"}

    from app.rag.pipelines import DentalRAGPipeline

    pipeline = DentalRAGPipeline()
    return pipeline.save_consultation(
        smartnote=req.smartnote,
        transcription=req.transcription,
        dentist_name=req.dentist_name,
        consultation_type=req.consultation_type,
        patient_id=req.patient_id,
    )


@router.post("/consultations/search", dependencies=[Depends(verify_api_key)])
async def search_consultations(req: SearchRequest):
    """Semantic search across past consultations."""
    if not _rag_available:
        return {"results": [], "detail": "RAG system not available"}

    from app.rag.pipelines import DentalRAGPipeline

    sanitized_query = sanitize_input(req.query, max_length=500)
    if not sanitized_query:
        raise HTTPException(status_code=400, detail="Search query is empty or invalid.")

    pipeline = DentalRAGPipeline()
    results = pipeline.search_consultations(
        query=sanitized_query,
        top_k=min(req.top_k, 50),
    )
    return {"results": results, "count": len(results)}


# ---------------------------------------------------------------------------
# RAG-enhanced summarization helpers
# ---------------------------------------------------------------------------

def _get_rag_context(text: str) -> str:
    """Retrieve relevant dental knowledge for the given text. Returns '' if unavailable."""
    if not _rag_available:
        return ""
    from app.rag.pipelines import DentalRAGPipeline

    pipeline = DentalRAGPipeline()
    return pipeline.get_rag_context(text)


@router.post("/summarize-rag", dependencies=[Depends(verify_api_key)])
async def summarize_with_rag(req: SummaryRequest):
    """
    Generate a RAG-enhanced SmartNote.

    Retrieves relevant dental knowledge before generation to ground
    the SmartNote in verified medical references and protocols.
    Falls back to standard summarization if RAG is unavailable.
    """
    if not get_llm_model_path().exists():
        raise HTTPException(status_code=503, detail="Model not downloaded. Please run setup.")

    sanitized_text = sanitize_input(req.text)
    if not sanitized_text:
        raise HTTPException(status_code=400, detail="Text input is empty or invalid.")

    rag_context = _get_rag_context(sanitized_text)

    from app.llm.local_llm import LocalLLM

    llm = LocalLLM()
    prompt = build_rag_smartnote_prompt(sanitized_text, rag_context)
    summary = await llm.generate(prompt)
    return {
        "summary": summary,
        "rag_enhanced": bool(rag_context),
        "sources_used": len(rag_context.split("\n\n")) if rag_context else 0,
    }


@router.post("/summarize-stream-rag", dependencies=[Depends(verify_api_key)])
async def summarize_stream_with_rag(req: SummaryRequest):
    """
    Stream RAG-enhanced SmartNote generation using SSE.

    Same as /summarize-stream but with dental knowledge retrieval
    for higher quality, reference-grounded SmartNotes.
    """
    if not get_llm_model_path().exists():
        raise HTTPException(status_code=503, detail="Model not downloaded. Please run setup.")

    sanitized_text = sanitize_input(req.text)
    if not sanitized_text:
        raise HTTPException(status_code=400, detail="Text input is empty or invalid.")

    rag_context = _get_rag_context(sanitized_text)

    from app.llm.local_llm import LocalLLM

    llm = LocalLLM()
    prompt = build_rag_smartnote_prompt(sanitized_text, rag_context)
    rag_enhanced = bool(rag_context)

    async def event_generator():
        try:
            yield f"data: {json.dumps({'rag_enhanced': rag_enhanced})}\n\n"
            async for chunk in llm.generate_stream(prompt):
                yield f"data: {json.dumps({'chunk': chunk})}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            logger.exception("RAG streaming error")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )

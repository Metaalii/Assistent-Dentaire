# Haystack Integration Exploration for Assistent-Dentaire

## What is Haystack?

[Haystack](https://github.com/deepset-ai/haystack) is an open-source AI orchestration framework by deepset that enables building LLM-powered applications with:

- **Retrieval-Augmented Generation (RAG)** - ground LLM answers in real documents
- **Pipelines** - composable, modular processing chains
- **Document Stores** - unified interface for vector databases (FAISS, Qdrant, Elasticsearch, ChromaDB, etc.)
- **Converters & Preprocessors** - ingest PDFs, DOCX, HTML, audio, etc.
- **Technology-agnostic** - works with OpenAI, Hugging Face, Llama.cpp, Ollama, and more

## Why Integrate Haystack?

Our current architecture is **stateless and single-session**: upload audio -> transcribe -> summarize -> display. There is no persistence, no consultation history, and no knowledge base. Haystack addresses all three gaps.

---

## Integration Ideas (Ranked by Impact)

### 1. RAG-Powered SmartNotes (High Impact)

**Problem:** Our Llama-3 model generates SmartNotes purely from its training data. It has no access to up-to-date dental guidelines, drug interaction databases, or clinic-specific protocols.

**Solution:** Build a RAG pipeline that retrieves relevant dental knowledge before generating the SmartNote.

```
Current Flow:
  Transcription -> LLM Prompt -> SmartNote

Proposed Flow:
  Transcription -> Haystack Retriever (query dental knowledge base)
                -> Augmented LLM Prompt (transcription + relevant docs)
                -> Higher-quality SmartNote
```

**What this gives us:**
- SmartNotes grounded in real dental guidelines (e.g., HAS, ADF recommendations)
- Automatic drug interaction warnings when medications are mentioned
- Procedure-specific templates pulled from a knowledge base
- Consistent terminology aligned with official dental nomenclature (CCAM codes)

**Haystack components needed:**
- `DocumentStore` (InMemoryDocumentStore or ChromaDB for local use)
- `SentenceTransformersDocumentEmbedder` for indexing
- `SentenceTransformersTextEmbedder` for query embedding
- `InMemoryEmbeddingRetriever` for finding relevant documents
- Custom `PromptBuilder` to combine retrieved docs with transcription

**Example architecture:**

```python
from haystack import Pipeline
from haystack.components.embedders import (
    SentenceTransformersTextEmbedder,
    SentenceTransformersDocumentEmbedder,
)
from haystack.components.retrievers.in_memory import InMemoryEmbeddingRetriever
from haystack.components.builders import PromptBuilder
from haystack.document_stores.in_memory import InMemoryDocumentStore

# --- Indexing pipeline (run once at startup) ---
document_store = InMemoryDocumentStore()

indexing_pipeline = Pipeline()
indexing_pipeline.add_component(
    "embedder",
    SentenceTransformersDocumentEmbedder(model="sentence-transformers/all-MiniLM-L6-v2")
)
indexing_pipeline.add_component("writer", DocumentWriter(document_store=document_store))
indexing_pipeline.connect("embedder", "writer")

# Index dental guidelines, protocols, drug databases
indexing_pipeline.run({"embedder": {"documents": dental_documents}})

# --- Query pipeline (called per consultation) ---
rag_template = """
Tu es un assistant dentaire professionnel.
Voici des informations de reference pertinentes:
{% for doc in documents %}
  - {{ doc.content }}
{% endfor %}

Voici la transcription de la consultation:
{{ transcription }}

Genere une SmartNote structuree basee sur la transcription
et les references ci-dessus.
"""

rag_pipeline = Pipeline()
rag_pipeline.add_component("embedder", SentenceTransformersTextEmbedder(
    model="sentence-transformers/all-MiniLM-L6-v2"
))
rag_pipeline.add_component("retriever", InMemoryEmbeddingRetriever(
    document_store=document_store, top_k=5
))
rag_pipeline.add_component("prompt_builder", PromptBuilder(template=rag_template))
# Generator could use our existing Llama-3 or Haystack's LlamaCppGenerator
rag_pipeline.add_component("llm", LlamaCppGenerator(model="path/to/model.gguf"))

rag_pipeline.connect("embedder.embedding", "retriever.query_embedding")
rag_pipeline.connect("retriever", "prompt_builder.documents")
rag_pipeline.connect("prompt_builder", "llm")
```

---

### 2. Consultation History & Semantic Search (High Impact)

**Problem:** Every consultation is lost once the window closes. Dentists cannot search past consultations, track patient treatment history, or review previous notes.

**Solution:** Store completed SmartNotes in a Haystack DocumentStore with embeddings, enabling semantic search across all past consultations.

```
Proposed Feature:
  "Rechercher: patient avec douleur molaire superieure"
  -> Returns relevant past SmartNotes ranked by semantic similarity
```

**What this gives us:**
- Searchable consultation archive
- Find similar past cases ("show me consultations with similar symptoms")
- Track treatment patterns over time
- Export consultation history

**Haystack components needed:**
- `DocumentStore` (ChromaDB or FAISS for persistent local storage)
- `SentenceTransformersDocumentEmbedder` for indexing new notes
- `SentenceTransformersTextEmbedder` for search queries
- `InMemoryEmbeddingRetriever` or `ChromaEmbeddingRetriever`

**Integration point in our codebase:**

```python
# In main.py - new endpoint
@app.post("/consultations/save", dependencies=[Depends(verify_api_key)])
async def save_consultation(req: ConsultationRequest):
    """Save a completed SmartNote to the consultation archive."""
    doc = Document(
        content=req.smartnote,
        meta={
            "patient_id": req.patient_id,  # optional, anonymized
            "date": datetime.now().isoformat(),
            "dentist": req.dentist_name,
            "type": req.consultation_type,  # examen, urgence, suivi...
        }
    )
    # Embed and store
    indexing_pipeline.run({"embedder": {"documents": [doc]}})
    return {"status": "saved"}

@app.get("/consultations/search", dependencies=[Depends(verify_api_key)])
async def search_consultations(query: str, top_k: int = 5):
    """Semantic search across past consultations."""
    results = search_pipeline.run({
        "embedder": {"text": query},
        "retriever": {"top_k": top_k}
    })
    return {"results": results["retriever"]["documents"]}
```

---

### 3. Dental Document Ingestion (Medium Impact)

**Problem:** Dentists have existing documents (PDFs, clinical guides, insurance forms, X-ray reports) that are not leveraged by the system.

**Solution:** Use Haystack's file converters to ingest and index dental documents.

**What this gives us:**
- Upload and search through dental PDFs (guidelines, protocols)
- Automatically reference relevant documents during consultation
- Build a clinic-specific knowledge base over time

**Haystack components needed:**
- `PyPDFToDocument` - convert PDFs to indexable documents
- `DocumentCleaner` - clean extracted text
- `DocumentSplitter` - split long documents into chunks
- `SentenceTransformersDocumentEmbedder` - create embeddings
- `DocumentWriter` - store in DocumentStore

```python
from haystack.components.converters import PyPDFToDocument
from haystack.components.preprocessors import DocumentCleaner, DocumentSplitter

ingestion_pipeline = Pipeline()
ingestion_pipeline.add_component("converter", PyPDFToDocument())
ingestion_pipeline.add_component("cleaner", DocumentCleaner())
ingestion_pipeline.add_component("splitter", DocumentSplitter(
    split_by="sentence", split_length=5, split_overlap=1
))
ingestion_pipeline.add_component("embedder", SentenceTransformersDocumentEmbedder(
    model="sentence-transformers/all-MiniLM-L6-v2"
))
ingestion_pipeline.add_component("writer", DocumentWriter(document_store=document_store))

ingestion_pipeline.connect("converter", "cleaner")
ingestion_pipeline.connect("cleaner", "splitter")
ingestion_pipeline.connect("splitter", "embedder")
ingestion_pipeline.connect("embedder", "writer")

# Usage: dentist uploads a PDF guideline
ingestion_pipeline.run({"converter": {"sources": ["guide_has_2024.pdf"]}})
```

---

### 4. Pipeline Orchestration (Medium Impact)

**Problem:** Our current audio->transcription->summary flow is hardcoded with manual wiring between components. Adding new steps (translation, classification, entity extraction) requires modifying core code.

**Solution:** Replace the ad-hoc flow with a Haystack Pipeline for modularity.

```python
from haystack import Pipeline
from haystack.components.builders import PromptBuilder

# Custom Haystack component wrapping our Whisper transcriber
@component
class WhisperTranscriber:
    @component.output_types(transcription=str)
    def run(self, audio_path: str):
        from app.llm.whisper import WhisperModel
        model = WhisperModel()
        result = model.transcribe(audio_path)
        return {"transcription": result}

# Custom component wrapping our LLM
@component
class DentalSmartNoteGenerator:
    @component.output_types(smartnote=str)
    def run(self, prompt: str):
        from app.llm.local_llm import LocalLLM
        llm = LocalLLM()
        result = llm.generate_sync(prompt)
        return {"smartnote": result}

# Full pipeline
consultation_pipeline = Pipeline()
consultation_pipeline.add_component("transcriber", WhisperTranscriber())
consultation_pipeline.add_component("prompt_builder", PromptBuilder(
    template=SMARTNOTE_PROMPT_TEMPLATE
))
consultation_pipeline.add_component("retriever", InMemoryEmbeddingRetriever(...))
consultation_pipeline.add_component("generator", DentalSmartNoteGenerator())

# Wire them together
consultation_pipeline.connect("transcriber.transcription", "prompt_builder.transcription")
consultation_pipeline.connect("retriever.documents", "prompt_builder.documents")
consultation_pipeline.connect("prompt_builder", "generator")
```

**Benefits:**
- Add/remove steps without touching core code
- Easy to add: language detection, medical entity extraction, CCAM code suggestion
- Pipeline visualization and debugging built-in
- Each component is independently testable

---

### 5. Medical Entity Extraction (Lower Impact, Future)

**Problem:** SmartNotes are free-text. There's no structured extraction of teeth numbers, procedures, medications, or diagnoses.

**Solution:** Add a Haystack component that extracts dental entities from transcriptions.

**What this gives us:**
- Automatic tooth numbering (FDI notation: 11, 21, 36, etc.)
- Procedure code suggestions (CCAM: HBMD038, HBBD040, etc.)
- Medication tracking and interaction checking
- Structured data for analytics

---

## Technical Considerations

### Compatibility with Our Stack

| Aspect | Current | With Haystack |
|--------|---------|---------------|
| Python version | 3.11+ | Compatible (Haystack requires 3.9+) |
| LLM | llama-cpp-python | Can wrap as Haystack component or use built-in `LlamaCppGenerator` |
| Whisper | faster-whisper | Wrap as custom Haystack component |
| Database | None | Add ChromaDB or FAISS (both local, no server needed) |
| Embedding model | None | Add sentence-transformers (~90MB model) |
| API framework | FastAPI | Fully compatible, Haystack runs inside FastAPI |

### Dependencies to Add

```
# In requirements.txt
haystack-ai>=2.0.0          # Core framework (~lightweight)
sentence-transformers>=2.2   # For embeddings (~90MB model download)
chromadb>=0.4.0              # Local vector store (no server needed)
# Optional
pypdf>=3.0                   # For PDF ingestion
```

### Resource Impact

- **Embedding model** (all-MiniLM-L6-v2): ~90MB RAM, very fast on CPU
- **ChromaDB**: Lightweight, file-based, no separate server
- **Indexing**: One-time cost per document, ~100ms per page
- **Retrieval**: ~10-50ms per query (fast even on CPU)
- **Total additional RAM**: ~200-400MB depending on document store size

### Privacy & Local-First

Haystack supports fully local operation:
- `InMemoryDocumentStore` or `ChromaDB` - no cloud database needed
- `sentence-transformers` - runs locally, no API calls
- Our existing `llama-cpp-python` LLM - stays fully local
- **Zero data leaves the machine** - maintains our privacy promise

---

## Recommended Phased Approach

### Phase 1: Consultation History (Quickest Win)
1. Add ChromaDB as a local document store
2. Store SmartNotes with metadata after generation
3. Add search endpoint to FastAPI
4. Add search UI to the frontend
5. **Effort:** ~2-3 days | **Impact:** High

### Phase 2: RAG-Enhanced SmartNotes
1. Curate a dental knowledge base (guidelines, protocols)
2. Build indexing pipeline for dental documents
3. Modify `/summarize` to retrieve relevant context before generation
4. **Effort:** ~3-5 days | **Impact:** High (significantly better SmartNote quality)

### Phase 3: Document Ingestion
1. Add PDF upload endpoint
2. Build ingestion pipeline (convert -> clean -> split -> embed -> store)
3. Allow dentists to upload their own reference documents
4. **Effort:** ~2-3 days | **Impact:** Medium

### Phase 4: Full Pipeline Orchestration
1. Wrap Whisper and LLM as Haystack components
2. Replace hardcoded flow with Haystack Pipeline
3. Add optional steps (entity extraction, CCAM coding)
4. **Effort:** ~3-5 days | **Impact:** Medium (better architecture for future features)

---

## Quick Start Prototype

To validate the approach, here's a minimal proof-of-concept that can be added to the existing backend:

```python
# haystack_integration.py - Minimal RAG proof of concept

from haystack import Document, Pipeline
from haystack.document_stores.in_memory import InMemoryDocumentStore
from haystack.components.embedders import (
    SentenceTransformersDocumentEmbedder,
    SentenceTransformersTextEmbedder,
)
from haystack.components.retrievers.in_memory import InMemoryEmbeddingRetriever
from haystack.components.writers import DocumentWriter

EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


class DentalKnowledgeBase:
    """Local dental knowledge base powered by Haystack."""

    def __init__(self):
        self.document_store = InMemoryDocumentStore()
        self._build_pipelines()

    def _build_pipelines(self):
        # Indexing pipeline
        self.indexing = Pipeline()
        self.indexing.add_component(
            "embedder",
            SentenceTransformersDocumentEmbedder(model=EMBEDDING_MODEL)
        )
        self.indexing.add_component(
            "writer",
            DocumentWriter(document_store=self.document_store)
        )
        self.indexing.connect("embedder", "writer")

        # Search pipeline
        self.search = Pipeline()
        self.search.add_component(
            "embedder",
            SentenceTransformersTextEmbedder(model=EMBEDDING_MODEL)
        )
        self.search.add_component(
            "retriever",
            InMemoryEmbeddingRetriever(
                document_store=self.document_store, top_k=5
            )
        )
        self.search.connect("embedder.embedding", "retriever.query_embedding")

    def add_documents(self, documents: list[Document]):
        """Index new documents into the knowledge base."""
        self.indexing.run({"embedder": {"documents": documents}})

    def search_similar(self, query: str, top_k: int = 5) -> list[Document]:
        """Find documents similar to the query."""
        result = self.search.run({
            "embedder": {"text": query},
            "retriever": {"top_k": top_k}
        })
        return result["retriever"]["documents"]

    def save_consultation(self, smartnote: str, metadata: dict):
        """Save a completed SmartNote for future reference."""
        doc = Document(content=smartnote, meta=metadata)
        self.add_documents([doc])
```

---

## Conclusion

Haystack is an excellent fit for Assistent-Dentaire because:

1. **It fills our biggest gap** - no persistence, no search, no knowledge base
2. **It's local-first** - respects our privacy-first architecture
3. **It's Python/FastAPI compatible** - integrates directly into our backend
4. **It's modular** - we adopt only what we need, incrementally
5. **It's production-ready** - used by enterprises, well-maintained by deepset

The highest-impact first step is **Phase 1 (Consultation History)** - it gives dentists immediate value with searchable past consultations, and lays the groundwork for RAG-enhanced SmartNotes in Phase 2.

"""
API routers package.

Each module is a self-contained FastAPI APIRouter handling one domain:
- health:     /health
- setup:      /setup/*   (model download, hardware check)
- summarize:  /summarize, /summarize-stream
- rag:        /rag/*, /consultations/*, /summarize-rag, /summarize-stream-rag
"""

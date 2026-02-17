"""
SmartNote summarization endpoints (non-RAG).

POST /summarize         — generate complete SmartNote
POST /summarize-stream  — stream SmartNote generation via SSE
"""

import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.config import get_llm_model_path
from app.llm_config import SMARTNOTE_PROMPT_OPTIMIZED
from app.sanitize import sanitize_input
from app.security import verify_api_key

router = APIRouter()
logger = logging.getLogger("dental_assistant.summarize")


class SummaryRequest(BaseModel):
    text: str


@router.post("/summarize", dependencies=[Depends(verify_api_key)])
async def summarize(req: SummaryRequest):
    """
    Generate a SmartNote summary from transcribed text.
    Returns the complete summary when generation is finished.
    """
    if not get_llm_model_path().exists():
        raise HTTPException(status_code=503, detail="Model not downloaded. Please run setup.")

    sanitized_text = sanitize_input(req.text)
    if not sanitized_text:
        raise HTTPException(status_code=400, detail="Text input is empty or invalid.")

    from app.llm.local_llm import LocalLLM

    llm = LocalLLM()
    prompt = SMARTNOTE_PROMPT_OPTIMIZED.format(text=sanitized_text)
    summary = await llm.generate(prompt)
    return {"summary": summary}


@router.post("/summarize-stream", dependencies=[Depends(verify_api_key)])
async def summarize_stream(req: SummaryRequest):
    """
    Stream SmartNote generation using Server-Sent Events (SSE).
    Returns tokens as they are generated for reduced perceived latency.

    Event format:
    - data: {"chunk": "token text"}  — for each generated token
    - data: [DONE]                   — when generation is complete
    """
    if not get_llm_model_path().exists():
        raise HTTPException(status_code=503, detail="Model not downloaded. Please run setup.")

    sanitized_text = sanitize_input(req.text)
    if not sanitized_text:
        raise HTTPException(status_code=400, detail="Text input is empty or invalid.")

    from app.llm.local_llm import LocalLLM

    llm = LocalLLM()
    prompt = SMARTNOTE_PROMPT_OPTIMIZED.format(text=sanitized_text)

    async def event_generator():
        try:
            async for chunk in llm.generate_stream(prompt):
                yield f"data: {json.dumps({'chunk': chunk})}\n\n"
            yield "data: [DONE]\n\n"
        except Exception as e:
            logger.exception("Streaming error")
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

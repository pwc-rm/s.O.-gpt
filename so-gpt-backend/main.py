"""
S.O. GPT Backend — FastAPI Application

Endpoint: POST /chat  → Server-Sent Events (streaming)
Auth:      x-api-key header (value from BACKEND_API_KEY in .env)

7-step RAG pipeline per request:
  ① Validate API key
  ② Load session history (Cosmos DB)
  ③ Query Rewriting (gpt-4.1-mini — fast, cheap, deterministic)
  ④ Hybrid Search + Semantic Ranking + Session Reranking (Azure AI Search)
  ⑤ Build prompt
  ⑥ Stream GPT-4o response as Server-Sent Events
  ⑦ Save Q&A turn to session store (after stream completes)

SSE event format:
  data: {"type":"meta","session_id":"...","quellen":[...],"rewritten_query":"..."}\n\n
  data: {"type":"token","content":"Laut"}\n\n
  data: [DONE]\n\n
"""
from __future__ import annotations

import json
import logging
import uuid
from typing import Optional, Iterator

from fastapi import FastAPI, HTTPException, Header, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import pathlib

import config
from session_store import load_session, save_session, get_docs_used, list_sessions, get_session_messages
from query_rewriter import rewrite_query
from retrieval import hybrid_search
from prompt_builder import build_prompt

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="S.O. GPT Backend", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://apim-so-gpt-showcase.azure-api.net",
        "https://app-so-gpt-showcase-backend.azurewebsites.net",
    ],
    allow_methods=["POST", "GET", "OPTIONS"],
    allow_headers=["Content-Type", "x-api-key"],
)


# ── Frontend ──────────────────────────────────────────────────────────────────
_frontend = pathlib.Path(__file__).parent / "static" / "index.html"

@app.get("/", include_in_schema=False)
def serve_frontend():
    if _frontend.exists():
        return FileResponse(_frontend)
    return {"status": "backend running — frontend not bundled"}

# ── Request model ─────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    frage: str
    session_id: Optional[str] = None


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    """Returns service configuration status."""
    return {"status": "ok", "services": config.service_status()}


@app.get("/sessions")
def sessions():
    """Returns the 30 most recent chat sessions."""
    try:
        return list_sessions(limit=30)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@app.get("/sessions/{session_id}/messages")
def session_messages(session_id: str):
    """Returns all messages for a given session."""
    try:
        return get_session_messages(session_id)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@app.post("/chat")
def chat(
    request: ChatRequest,
    x_api_key: Optional[str] = Header(default=None),
):
    """
    Streams the RAG response as Server-Sent Events.

    Steps ①–⑥ (retrieval) complete synchronously before the stream starts.
    Any retrieval failure returns a normal HTTP error — no partial stream.
    Step ⑦ (OpenAI) streams tokens as they arrive.
    Step ⑧ (session save) runs after the stream is fully consumed.
    """
    # ① Validate API key
    if not config.BACKEND_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="BACKEND_API_KEY not configured — set it in .env",
        )
    if x_api_key != config.BACKEND_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing x-api-key header",
        )

    question = request.frage.strip()
    if not question:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="'frage' darf nicht leer sein",
        )

    session_id = request.session_id or str(uuid.uuid4())

    # Steps ②–⑤ — retrieval (synchronous, errors returned as HTTP before streaming)
    try:
        history = load_session(session_id)
        docs_used = get_docs_used(session_id)

        rewritten = rewrite_query(question, history)

        chunks, _ = hybrid_search(rewritten, docs_used)

        messages = build_prompt(rewritten, chunks, history)

    except RuntimeError as exc:
        logger.error("Retrieval error: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )

    # Serialize sources once (reused in the SSE meta event)
    sources = [
        {
            "document_title": c["document_title"],
            "page_number": c.get("page_number"),
            "source_file": c.get("source_file", ""),
            "source_url": c.get("source_url", ""),
            "is_web": c.get("is_web", False),
        }
        for c in chunks
    ]

    # ⑥ Stream GPT-4o response
    return StreamingResponse(
        _stream(messages, session_id, question, chunks, sources, rewritten),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # disable nginx response buffering on App Service
        },
    )


# ── Streaming generator ───────────────────────────────────────────────────────

def _stream(
    messages: list[dict],
    session_id: str,
    question: str,
    chunks: list[dict],
    sources: list[dict],
    rewritten: str,
) -> Iterator[str]:
    if not (config.OPENAI_ENDPOINT and config.OPENAI_API_KEY):
        yield _sse({"type": "error", "message": "Azure OpenAI not configured — set OPENAI_ENDPOINT and OPENAI_API_KEY"})
        return

    # Send session metadata first — frontend renders sources panel immediately
    yield _sse({
        "type": "meta",
        "session_id": session_id,
        "quellen": sources,
        "rewritten_query": rewritten if rewritten != question else None,
    })

    from openai import AzureOpenAI
    client = AzureOpenAI(
        azure_endpoint=config.OPENAI_ENDPOINT,
        api_key=config.OPENAI_API_KEY,
        api_version=config.OPENAI_API_VERSION,
    )

    full_answer = ""
    try:
        stream = client.chat.completions.create(
            model=config.OPENAI_CHAT_DEPLOYMENT,
            messages=messages,
            temperature=0.2,
            max_tokens=800,
            stream=True,
        )
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                token = chunk.choices[0].delta.content
                full_answer += token
                yield _sse({"type": "token", "content": token})

    except Exception as exc:
        logger.error("OpenAI streaming error: %s", exc)
        yield _sse({"type": "error", "message": str(exc)})
        return

    yield "data: [DONE]\n\n"

    # ⑧ Save Q&A turn after stream completes
    used_files = [c["source_file"] for c in chunks if c.get("source_file")]
    try:
        save_session(session_id, question, full_answer, used_files, sources)
    except Exception as exc:
        logger.error("Session save failed (non-critical): %s", exc)


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

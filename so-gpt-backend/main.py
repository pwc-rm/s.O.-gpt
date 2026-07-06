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
import os
import uuid
from typing import Optional, Iterator

from fastapi import FastAPI, HTTPException, Header, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import pathlib

import config
from session_store import (
    load_session, save_session, get_docs_used, list_sessions,
    get_session_messages, delete_session,
    save_urlaub_antrag, update_urlaub_status, get_urlaub_antrag,
    save_canvas, list_canvases,
)
from query_rewriter import rewrite_query
from retrieval import hybrid_search
from prompt_builder import build_prompt
from mock_data import detect_doc_kind, build_handover_context, build_ooo_context

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
_static_dir = pathlib.Path(__file__).parent / "static"
_frontend = _static_dir / "index.html"

if _static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")

@app.get("/", include_in_schema=False)
def serve_frontend():
    if _frontend.exists():
        return FileResponse(_frontend, headers={"Cache-Control": "no-store"})
    return {"status": "backend running — frontend not bundled"}

# ── Request model ─────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    frage: str
    session_id: Optional[str] = None


class UrlaubAntragRequest(BaseModel):
    session_id: str
    von: str
    bis: str
    days: int
    overtime: bool = False
    time: str
    ticket: Optional[str] = None


class CanvasSaveRequest(BaseModel):
    session_id: str
    canvas_id: str
    title: str
    content: str
    sources: list[dict] = []


# ── Deterministic vacation-flow transitions ───────────────────────────────────
# The saldo→form confirmation steps must never depend on the LLM correctly
# distinguishing two identical "ja" replies. We detect them from the previous
# assistant turn and emit the next marker deterministically — rock-solid for
# live demos. Step 1 (the initial vacation question + offer) still runs via RAG.

_AFFIRM = {
    "ja", "jo", "jop", "jup", "jap", "jawohl", "klar", "gerne", "ok", "okay",
    "yes", "yep", "sicher", "bitte", "passt", "los", "mach", "machen",
}


def _is_affirmative(text: str) -> bool:
    t = text.strip().lower().rstrip("!.")
    if t in _AFFIRM:
        return True
    return any(t.startswith(a + " ") or t.startswith(a + ",") for a in _AFFIRM)


def _fmt_de(iso: str) -> str:
    """ISO date 'YYYY-MM-DD' → German 'DD.MM.YYYY' (leaves other formats untouched)."""
    try:
        y, m, d = iso.split("-")
        return f"{d}.{m}.{y}"
    except Exception:
        return iso


def _urlaub_flow_shortcut(question: str, history: list[dict]) -> Optional[str]:
    """Returns the next flow message if this turn is a vacation confirmation."""
    if not history or not _is_affirmative(question):
        return None
    last_answer = history[-1].get("answer", "")
    # Step 2 → 3: saldo already shown, user confirms → show the request form.
    if "[[URLAUB_SALDO]]" in last_answer:
        return "Gerne, hier ist das Antragsformular:\n\n[[URLAUB_FORMULAR]]"
    # Step 1 → 2: offer to check the account was made, user confirms → show saldo.
    if "persönlichen Urlaubskonto" in last_answer:
        return (
            "Ich habe dein Urlaubskonto abgerufen:\n\n[[URLAUB_SALDO]]\n\n"
            "Möchtest du direkt einen Urlaubsantrag stellen?"
        )
    return None


def _stream_static(text: str, session_id: str, question: str) -> Iterator[str]:
    """Streams a fixed reply as SSE (no LLM call, no token cost).

    Streams line-by-line with a small pause so the deterministic vacation flow
    feels like a natural, followable conversation instead of appearing instantly.
    """
    import time

    yield _sse({"type": "meta", "session_id": session_id, "quellen": [], "rewritten_query": None})
    time.sleep(0.6)  # brief "thinking" pause before the reply starts
    for line in text.split("\n"):
        yield _sse({"type": "token", "content": line + "\n"})
        time.sleep(0.18)  # per-line pacing
    yield _sse({"type": "usage", "prompt_tokens": 0, "completion_tokens": 0})
    yield "data: [DONE]\n\n"
    try:
        save_session(session_id, question, text, [], [], prompt_tokens=0, completion_tokens=0)
    except Exception as exc:
        logger.error("Session save failed (non-critical): %s", exc)


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


@app.delete("/sessions/{session_id}")
def session_delete(session_id: str):
    """Deletes all messages for a given session."""
    try:
        delete_session(session_id)
        return {"status": "deleted"}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@app.post("/canvas/save")
def canvas_save(req: CanvasSaveRequest):
    """Persists a canvas document (create or overwrite)."""
    try:
        save_canvas(req.session_id, req.canvas_id, req.title, req.content, req.sources)
        return {"status": "saved"}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@app.get("/sessions/{session_id}/canvases")
def session_canvases(session_id: str):
    """Returns all canvas documents for a session."""
    try:
        return list_canvases(session_id)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@app.post("/urlaub/antrag")
def urlaub_antrag_create(req: UrlaubAntragRequest):
    """Persists a submitted vacation request (Demo-Feature)."""
    try:
        save_urlaub_antrag(req.session_id, req.von, req.bis, req.days,
                           req.overtime, req.time, "pending", req.ticket)
        return {"status": "pending"}
    except Exception as exc:
        raise HTTPException(status_code=503, detail=str(exc))


@app.post("/urlaub/antrag/{session_id}/withdraw")
def urlaub_antrag_withdraw(session_id: str):
    """Marks a vacation request as withdrawn (Demo-Feature)."""
    try:
        update_urlaub_status(session_id, "withdrawn")
        return {"status": "withdrawn"}
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
    # ① Validate API key (skipped only for local dev when DEV_SKIP_AUTH=1)
    if os.getenv("DEV_SKIP_AUTH") != "1":
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

        # Deterministic saldo→form transitions — short-circuit before retrieval.
        flow_reply = _urlaub_flow_shortcut(question, history)
        if flow_reply is not None:
            return StreamingResponse(
                _stream_static(flow_reply, session_id, question),
                media_type="text/event-stream",
                headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
            )

        docs_used = get_docs_used(session_id)

        # Rewritten query is used ONLY for retrieval — the final prompt keeps the
        # user's original utterance so conversational turns (e.g. "Ja, gerne") are
        # recognised as such and not replaced by a standalone search query.
        rewritten = rewrite_query(question, history)

        chunks, _ = hybrid_search(rewritten, docs_used)

        # Mock-context injection for the handover checklist / out-of-office note.
        # The document is still model-generated (not deterministic) — we only feed
        # it persistent, simulated calendar/mailbox data plus (for the OOO note) the
        # dates from a previously submitted vacation request.
        extra_context = None
        doc_kind = detect_doc_kind(question)
        if doc_kind == "handover":
            extra_context = build_handover_context()
        elif doc_kind == "ooo":
            antrag = get_urlaub_antrag(session_id)
            von = _fmt_de(antrag["von"]) if antrag else None
            bis = _fmt_de(antrag["bis"]) if antrag else None
            extra_context = build_ooo_context(von, bis)

        messages = build_prompt(question, chunks, history, extra_context=extra_context)

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
        _stream(messages, session_id, question, chunks, sources, rewritten, doc_kind),
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
    doc_kind: str | None = None,
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
        "mock_used": doc_kind,
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
            stream_options={"include_usage": True},
        )
        usage = None
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                token = chunk.choices[0].delta.content
                full_answer += token
                yield _sse({"type": "token", "content": token})
            if chunk.usage:
                usage = chunk.usage

    except Exception as exc:
        logger.error("OpenAI streaming error: %s", exc)
        yield _sse({"type": "error", "message": str(exc)})
        return

    if usage:
        yield _sse({
            "type": "usage",
            "prompt_tokens": usage.prompt_tokens,
            "completion_tokens": usage.completion_tokens,
        })

    yield "data: [DONE]\n\n"

    # ⑧ Save Q&A turn after stream completes
    used_files = [c["source_file"] for c in chunks if c.get("source_file")]
    try:
        save_session(
            session_id, question, full_answer, used_files, sources,
            prompt_tokens=usage.prompt_tokens if usage else 0,
            completion_tokens=usage.completion_tokens if usage else 0,
        )
    except Exception as exc:
        logger.error("Session save failed (non-critical): %s", exc)


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

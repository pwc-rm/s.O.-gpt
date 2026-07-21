"""
s.Oliver Agent Cockpit — FastAPI Application

Serves the Cockpit SPA (/) and the agent-chat UI (/agent/{id}/chat), plus a small
REST + SSE API. The agent chat is REAL: it calls Azure OpenAI (gpt-4o) with the
agent's own system prompt and streams the answer token-by-token. Chat history is
reserved per agent in Cosmos (agent-cockpit-db/agent_chat).
"""
from __future__ import annotations

import json
import logging
import pathlib
from typing import Iterator, Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import config
import catalog_store
import mock_seed

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="s.Oliver Agent Cockpit", version="1.0.0")


@app.on_event("startup")
def _startup():
    try:
        catalog_store.ensure_seeded()
        logger.info("Catalog seeded (cosmos=%s)", bool(config.COSMOS_CONNECTION_STRING))
    except Exception as exc:
        logger.error("Seeding failed (non-critical): %s", exc)


# ── Static frontend ───────────────────────────────────────────────────────────
_static_dir = pathlib.Path(__file__).parent / "static"
if _static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")


@app.get("/", include_in_schema=False)
def serve_cockpit():
    f = _static_dir / "index.html"
    if f.exists():
        return FileResponse(f, headers={"Cache-Control": "no-store"})
    return {"status": "cockpit backend running — frontend not bundled"}


@app.get("/agent/{agent_id}/chat", include_in_schema=False)
def serve_agent_chat(agent_id: str):
    f = _static_dir / "agent-chat.html"
    if f.exists():
        return FileResponse(f, headers={"Cache-Control": "no-store"})
    return {"status": "agent chat frontend not bundled"}


# ── Health ────────────────────────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok", "services": config.service_status()}


# ── Config for the frontend (sources map + s.O GPT link) ──────────────────────
@app.get("/api/config")
def api_config():
    return {"sources": mock_seed.SOURCES, "sogpt_url": config.SOGPT_URL}


# ── Agents ────────────────────────────────────────────────────────────────────
@app.get("/api/agents")
def api_agents(category: Optional[str] = None, status: Optional[str] = None):
    agents = catalog_store.list_agents()
    if category and category != "Alle Kategorien":
        agents = [a for a in agents if a.get("category") == category]
    if status:
        agents = [a for a in agents if a.get("status") == status]
    return agents


@app.get("/api/agents/{agent_id}")
def api_agent(agent_id: str):
    agent = catalog_store.get_agent(agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


class AgentPatch(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    model: Optional[str] = None
    temperature: Optional[float] = None
    system_prompt: Optional[str] = None
    business_owner: Optional[str] = None
    org_unit: Optional[str] = None
    cmdb: Optional[dict] = None
    permissions: Optional[list] = None
    knowledge: Optional[dict] = None
    grundfragen: Optional[list] = None


@app.put("/api/agents/{agent_id}")
def api_agent_update(agent_id: str, patch: AgentPatch):
    updated = catalog_store.update_agent(agent_id, patch.model_dump(exclude_none=True))
    if updated is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return updated


class BudgetPatch(BaseModel):
    budget_eur: Optional[float] = None
    quota: Optional[int] = None
    alert_threshold_pct: Optional[int] = None


@app.put("/api/agents/{agent_id}/budget")
def api_agent_budget(agent_id: str, patch: BudgetPatch):
    updated = catalog_store.update_budget(agent_id, patch.model_dump(exclude_none=True))
    if updated is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return updated


class RateRequest(BaseModel):
    value: str  # "up" | "down"


@app.post("/api/agents/{agent_id}/rate")
def api_agent_rate(agent_id: str, req: RateRequest):
    if req.value not in ("up", "down"):
        raise HTTPException(status_code=400, detail="value must be 'up' or 'down'")
    rating = catalog_store.rate_agent(agent_id, req.value)
    if rating is None:
        raise HTTPException(status_code=404, detail="Agent not found")
    return rating


# ── Dashboards (mock) ─────────────────────────────────────────────────────────
@app.get("/api/finops")
def api_finops():
    return mock_seed.finops_summary(catalog_store.list_agents())


@app.get("/api/agentops")
def api_agentops():
    return mock_seed.agentops_summary(catalog_store.list_agents())


@app.get("/api/settings")
def api_settings():
    return {"profile": mock_seed.USER_PROFILE, "api_keys": mock_seed.API_KEYS, "org_units": mock_seed.ORG_UNITS}


# ── Chat history (reserved per agent) ─────────────────────────────────────────
@app.get("/api/agents/{agent_id}/chats")
def api_agent_chats(agent_id: str):
    return catalog_store.list_chats(agent_id)


@app.get("/api/agents/{agent_id}/chats/{chat_id}")
def api_agent_chat_history(agent_id: str, chat_id: str):
    return {"messages": catalog_store.get_history(agent_id, chat_id)}


# ── Real chat (Azure OpenAI, SSE) ─────────────────────────────────────────────
class ChatRequest(BaseModel):
    message: str
    chat_id: Optional[str] = None


@app.post("/api/agents/{agent_id}/chat")
def api_agent_chat(agent_id: str, req: ChatRequest):
    agent = catalog_store.get_agent(agent_id)
    if agent is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    message = req.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="message darf nicht leer sein")

    chat_id = req.chat_id or catalog_store.create_chat(agent_id)
    history = catalog_store.get_history(agent_id, chat_id)

    return StreamingResponse(
        _stream_chat(agent, chat_id, message, history),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


def _stream_chat(agent: dict, chat_id: str, message: str, history: list[dict]) -> Iterator[str]:
    agent_id = agent["id"]
    yield _sse({"type": "meta", "chat_id": chat_id, "agent": agent["name"]})

    if not (config.OPENAI_ENDPOINT and config.OPENAI_API_KEY):
        yield _sse({"type": "error", "message": "Azure OpenAI nicht konfiguriert"})
        return

    # Build the message list: agent's own system prompt + prior turns + new message.
    messages = [{"role": "system", "content": agent.get("system_prompt", "")}]
    for m in history:
        messages.append({"role": m["role"], "content": m["content"]})
    messages.append({"role": "user", "content": message})

    from openai import AzureOpenAI
    client = AzureOpenAI(
        azure_endpoint=config.OPENAI_ENDPOINT,
        api_key=config.OPENAI_API_KEY,
        api_version=config.OPENAI_API_VERSION,
    )

    full_answer = ""
    usage = None
    try:
        stream = client.chat.completions.create(
            model=config.OPENAI_CHAT_DEPLOYMENT,
            messages=messages,
            temperature=float(agent.get("temperature", 0.2)),
            max_tokens=800,
            stream=True,
            stream_options={"include_usage": True},
        )
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
        yield _sse({"type": "usage", "prompt_tokens": usage.prompt_tokens, "completion_tokens": usage.completion_tokens})
    yield "data: [DONE]\n\n"

    # Persist both turns (reserved to this agent).
    try:
        catalog_store.append_message(agent_id, chat_id, "user", message)
        catalog_store.append_message(agent_id, chat_id, "assistant", full_answer,
                                     tokens=usage.completion_tokens if usage else 0)
    except Exception as exc:
        logger.error("Chat save failed (non-critical): %s", exc)


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

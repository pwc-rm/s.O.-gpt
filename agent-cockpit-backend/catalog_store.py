"""
Catalog Store — Agent catalog + per-agent chat history.

Cosmos DB: database `agent-cockpit-db` (isolated from Raj's so-gpt-db).
  • container `agents`      (PK /category)   — the agent catalog
  • container `agent_chat`  (PK /agent_id)   — reserved chat history per agent

If COSMOS_CONNECTION_STRING is not set (e.g. local dev without Cosmos), the store
falls back to an in-memory copy of the seed so the app still runs. In Azure, the
catalog is seeded into Cosmos on first startup.
"""
from __future__ import annotations
import copy
import time
import uuid

import config
import mock_seed

_USE_COSMOS = bool(config.COSMOS_CONNECTION_STRING)

# In-memory fallback state
_MEM_AGENTS: dict[str, dict] = {}
_MEM_CHATS: dict[str, dict] = {}   # chat_id -> {id, agent_id, title, messages, ts}

_agents_container = None
_chat_container = None


# ── Cosmos wiring ─────────────────────────────────────────────────────────────

def _containers():
    global _agents_container, _chat_container
    if _agents_container is None:
        from azure.cosmos import CosmosClient
        client = CosmosClient.from_connection_string(config.COSMOS_CONNECTION_STRING)
        db = client.get_database_client(config.COSMOS_DATABASE)
        _agents_container = db.get_container_client(config.COSMOS_AGENTS_CONTAINER)
        _chat_container = db.get_container_client(config.COSMOS_AGENTCHAT_CONTAINER)
    return _agents_container, _chat_container


def ensure_seeded() -> None:
    """Seed the catalog on first run (idempotent)."""
    if not _USE_COSMOS:
        if not _MEM_AGENTS:
            for a in mock_seed.AGENTS:
                _MEM_AGENTS[a["id"]] = copy.deepcopy(a)
        return
    agents, _ = _containers()
    existing = list(agents.query_items(
        query="SELECT VALUE COUNT(1) FROM c WHERE c.doc_type = 'agent'",
        enable_cross_partition_query=True,
    ))
    if existing and existing[0] > 0:
        _refresh(agents)
        return
    for a in mock_seed.AGENTS:
        agents.upsert_item(copy.deepcopy(a))


# User-editable fields that must survive a seed refresh (their stored value wins).
_PRESERVE_TOP = {
    "name", "description", "system_prompt", "business_owner", "org_unit",
    "model", "temperature", "grundfragen", "permissions", "knowledge", "cmdb",
    "rating",
}
_PRESERVE_FINOPS = {"budget_eur", "alert_threshold_pct"}


def _refresh(agents) -> None:
    """Refresh demo/mock fields from the seed (so data-model changes propagate),
    while preserving genuine user edits (config, planned budget, ratings)."""
    stored = {d["id"]: d for d in agents.query_items(
        query="SELECT * FROM c WHERE c.doc_type = 'agent'",
        enable_cross_partition_query=True,
    )}
    for seed in mock_seed.AGENTS:
        doc = stored.get(seed["id"])
        if doc is None:
            agents.upsert_item(copy.deepcopy(seed))
            continue
        new = copy.deepcopy(seed)
        for k in _PRESERVE_TOP:
            if k in doc:
                new[k] = doc[k]
        if isinstance(doc.get("finops"), dict):
            for k in _PRESERVE_FINOPS:
                if k in doc["finops"]:
                    new["finops"][k] = doc["finops"][k]
        agents.upsert_item(new)


# ── Agents ────────────────────────────────────────────────────────────────────

def list_agents() -> list[dict]:
    if not _USE_COSMOS:
        return [copy.deepcopy(a) for a in _MEM_AGENTS.values()]
    agents, _ = _containers()
    return list(agents.query_items(
        query="SELECT * FROM c WHERE c.doc_type = 'agent'",
        enable_cross_partition_query=True,
    ))


def get_agent(agent_id: str) -> dict | None:
    if not _USE_COSMOS:
        a = _MEM_AGENTS.get(agent_id)
        return copy.deepcopy(a) if a else None
    agents, _ = _containers()
    items = list(agents.query_items(
        query="SELECT * FROM c WHERE c.id = @id AND c.doc_type = 'agent'",
        parameters=[{"name": "@id", "value": agent_id}],
        enable_cross_partition_query=True,
    ))
    return items[0] if items else None


# Fields the Agent-Detail screen is allowed to update.
_EDITABLE = {
    "name", "description", "status", "model", "temperature",
    "system_prompt", "business_owner", "org_unit", "cmdb",
    "permissions", "knowledge", "grundfragen",
}


def update_agent(agent_id: str, patch: dict) -> dict | None:
    agent = get_agent(agent_id)
    if agent is None:
        return None
    for k, v in patch.items():
        if k in _EDITABLE:
            agent[k] = v
    if not _USE_COSMOS:
        _MEM_AGENTS[agent_id] = agent
        return copy.deepcopy(agent)
    agents, _ = _containers()
    agents.upsert_item(agent)
    return agent


_BUDGET_FIELDS = {"budget_eur", "quota", "alert_threshold_pct"}


def update_budget(agent_id: str, patch: dict) -> dict | None:
    """Merges budget/quota/threshold into the agent's finops, keeping actuals
    (tokens_used, cost_eur) intact. Returns the full updated agent."""
    agent = get_agent(agent_id)
    if agent is None:
        return None
    f = agent.get("finops") or {}
    for k, v in patch.items():
        if k in _BUDGET_FIELDS and v is not None:
            f[k] = v
    agent["finops"] = f
    if not _USE_COSMOS:
        _MEM_AGENTS[agent_id] = agent
    else:
        agents, _ = _containers()
        agents.upsert_item(agent)
    return agent


def rate_agent(agent_id: str, value: str) -> dict | None:
    """Records a thumbs up/down for an agent; returns the updated {up, down}."""
    agent = get_agent(agent_id)
    if agent is None:
        return None
    r = agent.get("rating") or {"up": 0, "down": 0}
    if value == "up":
        r["up"] = r.get("up", 0) + 1
    elif value == "down":
        r["down"] = r.get("down", 0) + 1
    agent["rating"] = r
    if not _USE_COSMOS:
        _MEM_AGENTS[agent_id] = agent
    else:
        agents, _ = _containers()
        agents.upsert_item(agent)
    return r


# ── Chats (reserved per agent) ────────────────────────────────────────────────

def create_chat(agent_id: str, title: str = "Neuer Chat") -> str:
    chat_id = str(uuid.uuid4())
    doc = {
        "id": chat_id,
        "doc_type": "agent_chat",
        "agent_id": agent_id,
        "title": title,
        "messages": [],
        "ts": int(time.time()),
    }
    if not _USE_COSMOS:
        _MEM_CHATS[chat_id] = doc
    else:
        _, chats = _containers()
        chats.upsert_item(doc)
    return chat_id


def _get_chat_doc(agent_id: str, chat_id: str) -> dict | None:
    if not _USE_COSMOS:
        doc = _MEM_CHATS.get(chat_id)
        return doc if doc and doc["agent_id"] == agent_id else None
    _, chats = _containers()
    try:
        return chats.read_item(item=chat_id, partition_key=agent_id)
    except Exception:
        return None


def list_chats(agent_id: str) -> list[dict]:
    if not _USE_COSMOS:
        docs = [d for d in _MEM_CHATS.values() if d["agent_id"] == agent_id]
    else:
        _, chats = _containers()
        docs = list(chats.query_items(
            query="SELECT * FROM c WHERE c.agent_id = @aid ORDER BY c.ts DESC",
            parameters=[{"name": "@aid", "value": agent_id}],
            enable_cross_partition_query=False,
        ))
    return sorted(
        [{"chat_id": d["id"], "title": d.get("title", "Neuer Chat"), "ts": d.get("ts", 0)} for d in docs],
        key=lambda c: c["ts"], reverse=True,
    )


def get_history(agent_id: str, chat_id: str) -> list[dict]:
    doc = _get_chat_doc(agent_id, chat_id)
    return doc["messages"] if doc else []


def append_message(agent_id: str, chat_id: str, role: str, content: str, tokens: int = 0) -> None:
    doc = _get_chat_doc(agent_id, chat_id)
    if doc is None:
        doc = {"id": chat_id, "doc_type": "agent_chat", "agent_id": agent_id,
               "title": "Neuer Chat", "messages": [], "ts": int(time.time())}
    doc["messages"].append({"role": role, "content": content, "tokens": tokens})
    # First user message becomes the chat title.
    if role == "user" and doc["title"] == "Neuer Chat":
        doc["title"] = content[:60]
    doc["ts"] = int(time.time())
    if not _USE_COSMOS:
        _MEM_CHATS[chat_id] = doc
    else:
        _, chats = _containers()
        chats.upsert_item(doc)

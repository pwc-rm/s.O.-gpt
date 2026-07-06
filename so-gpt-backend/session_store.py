"""
Session Store — Azure Cosmos DB

Partition key: /session_id
Database:      so-gpt-db
Container:     sessions

Requires COSMOS_CONNECTION_STRING in .env.
"""
from __future__ import annotations
import time
import uuid

import config


_container = None


def _get_container():
    # Reuse a single CosmosClient across requests. With Cosmos' default
    # "Session" consistency the client retains its session token, giving
    # read-your-writes — so a just-saved turn is visible to the next request
    # (e.g. rapid "ja" confirmations in the vacation flow).
    # TODO: Azure — switch to Managed Identity once App Service identity is configured
    global _container
    if _container is None:
        from azure.cosmos import CosmosClient
        client = CosmosClient.from_connection_string(config.COSMOS_CONNECTION_STRING)
        _container = (
            client
            .get_database_client(config.COSMOS_DATABASE)
            .get_container_client(config.COSMOS_CONTAINER)
        )
    return _container


_URLAUB_TYPE = "urlaub_antrag"


def load_session(session_id: str) -> list[dict]:
    """Returns the last N Q&A turns for a session, oldest first."""
    container = _get_container()
    query = (
        "SELECT c.question, c.answer, c.docs_used FROM c "
        "WHERE c.session_id = @sid AND NOT IS_DEFINED(c.doc_type) "
        "ORDER BY c._ts DESC "
        f"OFFSET 0 LIMIT {config.SESSION_HISTORY_TURNS}"
    )
    items = list(container.query_items(
        query=query,
        parameters=[{"name": "@sid", "value": session_id}],
        enable_cross_partition_query=True,
    ))
    return list(reversed(items))


def save_session(session_id: str, question: str, answer: str, docs_used: list[str], sources: list[dict] | None = None, prompt_tokens: int = 0, completion_tokens: int = 0) -> None:
    """Persists a single Q&A turn."""
    container = _get_container()
    container.upsert_item({
        "id": str(uuid.uuid4()),
        "session_id": session_id,
        "question": question,
        "answer": answer,
        "docs_used": docs_used,
        "sources": sources or [],
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "timestamp": int(time.time()),
    })


def get_docs_used(session_id: str) -> list[str]:
    """Returns all source files referenced in previous turns (for Session Reranking)."""
    history = load_session(session_id)
    seen: dict[str, None] = {}
    for turn in history:
        for doc in turn.get("docs_used", []):
            seen[doc] = None
    return list(seen)


def list_sessions(limit: int = 30) -> list[dict]:
    """Returns the most recent sessions (one entry per session_id, title = first question)."""
    container = _get_container()
    # ASC so the oldest turn per session comes first — that's the session title.
    query = (
        "SELECT c.session_id, c.question, c._ts FROM c "
        "WHERE NOT IS_DEFINED(c.doc_type) "
        "ORDER BY c._ts ASC OFFSET 0 LIMIT 200"
    )
    items = list(container.query_items(query=query, enable_cross_partition_query=True))

    seen: dict[str, dict] = {}
    for item in items:
        sid = item["session_id"]
        if sid not in seen:
            # First occurrence (oldest turn) → title
            seen[sid] = {"id": sid, "title": item["question"][:60], "ts": item["_ts"]}
        else:
            # Keep updating ts so ordering reflects the session's most recent activity
            seen[sid]["ts"] = item["_ts"]

    sessions = sorted(seen.values(), key=lambda s: s["ts"], reverse=True)
    return sessions[:limit]


def delete_session(session_id: str) -> None:
    """Deletes all turns for a given session."""
    container = _get_container()
    query = "SELECT c.id FROM c WHERE c.session_id = @sid"
    items = list(container.query_items(
        query=query,
        parameters=[{"name": "@sid", "value": session_id}],
        enable_cross_partition_query=True,
    ))
    for item in items:
        container.delete_item(item["id"], partition_key=session_id)


def get_session_messages(session_id: str) -> dict:
    """Returns all turns + last sources + cumulative token usage for a session, oldest first."""
    container = _get_container()
    query = (
        "SELECT c.question, c.answer, c.sources, c.prompt_tokens, c.completion_tokens FROM c "
        "WHERE c.session_id = @sid AND NOT IS_DEFINED(c.doc_type) "
        "ORDER BY c._ts ASC"
    )
    items = list(container.query_items(
        query=query,
        parameters=[{"name": "@sid", "value": session_id}],
        enable_cross_partition_query=True,
    ))
    messages = []
    last_sources = []
    total_prompt = 0
    total_completion = 0
    for item in items:
        messages.append({"role": "user", "text": item["question"]})
        messages.append({"role": "ai", "text": item["answer"]})
        if item.get("sources"):
            last_sources = item["sources"]
        total_prompt += item.get("prompt_tokens", 0)
        total_completion += item.get("completion_tokens", 0)
    return {
        "messages": messages,
        "sources": last_sources,
        "prompt_tokens": total_prompt,
        "completion_tokens": total_completion,
        "urlaub_antrag": get_urlaub_antrag(session_id),
        "canvases": list_canvases(session_id),
    }


# ── Canvas (Demo-Feature) ────────────────────────────────────────────────────

_CANVAS_TYPE = "canvas"


def save_canvas(session_id: str, canvas_id: str, title: str, content: str,
                sources: list[dict] | None = None) -> None:
    """Creates or overwrites a canvas document for a session."""
    container = _get_container()
    container.upsert_item({
        "id": f"canvas-{canvas_id}",
        "session_id": session_id,
        "doc_type": _CANVAS_TYPE,
        "canvas_id": canvas_id,
        "title": title,
        "content": content,
        "sources": sources or [],
        "timestamp": int(time.time()),
    })


def list_canvases(session_id: str) -> list[dict]:
    """Returns all canvas documents for a session, newest first."""
    container = _get_container()
    items = list(container.query_items(
        query=(
            "SELECT c.canvas_id, c.title, c.content, c.sources, c._ts FROM c "
            "WHERE c.session_id = @sid AND c.doc_type = @t "
            "ORDER BY c._ts DESC"
        ),
        parameters=[
            {"name": "@sid", "value": session_id},
            {"name": "@t", "value": _CANVAS_TYPE},
        ],
        enable_cross_partition_query=True,
    ))
    return items


# ── Urlaubsantrag (Demo-Feature) ──────────────────────────────────────────────

def save_urlaub_antrag(session_id: str, von: str, bis: str, days: int,
                       overtime: bool, time_str: str, status: str = "pending",
                       ticket: str | None = None) -> None:
    """Persists (or overwrites) the vacation request for a session."""
    container = _get_container()
    container.upsert_item({
        "id": f"urlaub-{session_id}",   # deterministic → one request per session
        "session_id": session_id,
        "doc_type": _URLAUB_TYPE,
        "von": von,
        "bis": bis,
        "days": days,
        "overtime": overtime,
        "time": time_str,
        "status": status,
        "ticket": ticket,
        "timestamp": int(time.time()),
    })


def get_urlaub_antrag(session_id: str) -> dict | None:
    """Returns the vacation request for a session, or None."""
    container = _get_container()
    items = list(container.query_items(
        query=(
            "SELECT c.von, c.bis, c.days, c.overtime, c.time, c.status, c.ticket FROM c "
            "WHERE c.session_id = @sid AND c.doc_type = @t"
        ),
        parameters=[
            {"name": "@sid", "value": session_id},
            {"name": "@t", "value": _URLAUB_TYPE},
        ],
        enable_cross_partition_query=True,
    ))
    return items[0] if items else None


def update_urlaub_status(session_id: str, status: str) -> None:
    """Updates the status of an existing vacation request (e.g. 'withdrawn')."""
    container = _get_container()
    item = container.read_item(item=f"urlaub-{session_id}", partition_key=session_id)
    item["status"] = status
    container.upsert_item(item)

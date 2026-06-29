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


def _get_container():
    # TODO: Azure — switch to Managed Identity once App Service identity is configured
    from azure.cosmos import CosmosClient
    client = CosmosClient.from_connection_string(config.COSMOS_CONNECTION_STRING)
    return (
        client
        .get_database_client(config.COSMOS_DATABASE)
        .get_container_client(config.COSMOS_CONTAINER)
    )


def load_session(session_id: str) -> list[dict]:
    """Returns the last N Q&A turns for a session, oldest first."""
    container = _get_container()
    query = (
        "SELECT c.question, c.answer, c.docs_used FROM c "
        "WHERE c.session_id = @sid "
        "ORDER BY c._ts DESC "
        f"OFFSET 0 LIMIT {config.SESSION_HISTORY_TURNS}"
    )
    items = list(container.query_items(
        query=query,
        parameters=[{"name": "@sid", "value": session_id}],
        enable_cross_partition_query=True,
    ))
    return list(reversed(items))


def save_session(session_id: str, question: str, answer: str, docs_used: list[str], sources: list[dict] | None = None) -> None:
    """Persists a single Q&A turn."""
    container = _get_container()
    container.upsert_item({
        "id": str(uuid.uuid4()),
        "session_id": session_id,
        "question": question,
        "answer": answer,
        "docs_used": docs_used,
        "sources": sources or [],
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
    query = (
        "SELECT c.session_id, c.question, c._ts FROM c "
        "ORDER BY c._ts DESC OFFSET 0 LIMIT 200"
    )
    items = list(container.query_items(query=query, enable_cross_partition_query=True))

    seen: dict[str, dict] = {}
    for item in items:
        sid = item["session_id"]
        if sid not in seen:
            seen[sid] = {"id": sid, "title": item["question"][:60], "ts": item["_ts"]}

    sessions = sorted(seen.values(), key=lambda s: s["ts"], reverse=True)
    return sessions[:limit]


def get_session_messages(session_id: str) -> dict:
    """Returns all turns + last sources for a session, oldest first."""
    container = _get_container()
    query = (
        "SELECT c.question, c.answer, c.sources FROM c "
        "WHERE c.session_id = @sid "
        "ORDER BY c._ts ASC"
    )
    items = list(container.query_items(
        query=query,
        parameters=[{"name": "@sid", "value": session_id}],
        enable_cross_partition_query=True,
    ))
    messages = []
    last_sources = []
    for item in items:
        messages.append({"role": "user", "text": item["question"]})
        messages.append({"role": "ai", "text": item["answer"]})
        if item.get("sources"):
            last_sources = item["sources"]
    return {"messages": messages, "sources": last_sources}

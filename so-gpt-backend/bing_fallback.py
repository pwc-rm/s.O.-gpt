"""
Bing Web Search Fallback — Step ⑤ (optional)

Activated when the highest relevance score from Azure AI Search falls below
RELEVANCE_THRESHOLD. Returns web results in the same Chunk format as retrieval.py
so prompt_builder.py can handle both transparently.

Returns empty list if BING_API_KEY is not configured (graceful degradation).
"""
from __future__ import annotations
import logging

import requests

import config

logger = logging.getLogger(__name__)


def bing_search(query: str, count: int = 3) -> list[dict]:
    """
    Returns web search results as chunks, or [] if Bing is not configured.
    """
    if not config.BING_API_KEY:
        logger.warning("BING_API_KEY not set — Bing fallback disabled")
        return []

    headers = {"Ocp-Apim-Subscription-Key": config.BING_API_KEY}
    params = {
        "q": query,
        "count": count,
        "mkt": "de-DE",
        "responseFilter": "Webpages",
        "safeSearch": "Strict",
    }

    response = requests.get(
        config.BING_ENDPOINT,
        headers=headers,
        params=params,
        timeout=5,
    )
    response.raise_for_status()

    results = []
    for item in response.json().get("webPages", {}).get("value", [])[:count]:
        results.append({
            "chunk_id": None,
            "content": item.get("snippet", ""),
            "document_title": item.get("name", ""),
            "page_number": None,
            "source_file": "",
            "source_url": item.get("url", ""),
            "score": 0.5,
            "is_web": True,
        })

    return results
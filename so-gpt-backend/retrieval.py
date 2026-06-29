"""
Retrieval — Steps ①–④ of the 4-step retrieval strategy

① Vector Search       — semantic similarity via text-embedding-3-large
② BM25 Keyword Search — exact term matching (built into Azure AI Search hybrid mode)
③ Semantic Ranking    — Azure AI Search Cross-Encoder (query + chunk together)
④ Session Reranking   — backend boost for documents already used in this session

Returns: (chunks: list[dict], max_score: float)
Raises:  RuntimeError if Azure AI Search is not configured (required service).
"""
from __future__ import annotations
import logging

import config

logger = logging.getLogger(__name__)

Chunk = dict  # keys: chunk_id, content, document_title, page_number, source_file, source_url, score


def _get_embedding(text: str) -> list[float]:
    """Calls Azure OpenAI Embedding model to vectorise a query or chunk."""
    from openai import AzureOpenAI
    client = AzureOpenAI(
        azure_endpoint=config.OPENAI_ENDPOINT,
        api_key=config.OPENAI_API_KEY,
        api_version=config.OPENAI_API_VERSION,
    )
    response = client.embeddings.create(
        input=text,
        model=config.OPENAI_EMBEDDING_DEPLOYMENT,
    )
    return response.data[0].embedding


def hybrid_search(query: str, docs_used: list[str]) -> tuple[list[Chunk], float]:
    """
    Runs steps ①–④ against Azure AI Search and returns top-N chunks.

    Requires SEARCH_ENDPOINT, SEARCH_API_KEY, OPENAI_ENDPOINT, OPENAI_API_KEY.
    """
    if not (config.SEARCH_ENDPOINT and config.SEARCH_API_KEY):
        raise RuntimeError(
            "Azure AI Search not configured. "
            "Set SEARCH_ENDPOINT and SEARCH_API_KEY in .env"
        )
    if not (config.OPENAI_ENDPOINT and config.OPENAI_API_KEY):
        raise RuntimeError(
            "Azure OpenAI not configured (needed for embeddings). "
            "Set OPENAI_ENDPOINT and OPENAI_API_KEY in .env"
        )

    from azure.search.documents import SearchClient
    from azure.search.documents.models import VectorizedQuery
    from azure.core.credentials import AzureKeyCredential

    # ① + ② — Hybrid Search: vector query + BM25 run in parallel
    query_vector = _get_embedding(query)
    vector_query = VectorizedQuery(
        vector=query_vector,
        k_nearest_neighbors=config.TOP_N_CHUNKS * 3,
        fields="content_vector",
    )

    client = SearchClient(
        endpoint=config.SEARCH_ENDPOINT,
        index_name=config.SEARCH_INDEX_NAME,
        credential=AzureKeyCredential(config.SEARCH_API_KEY),
    )

    # ③ — Semantic Ranking (Cross-Encoder) applied server-side by Azure AI Search
    results = client.search(
        search_text=query,
        vector_queries=[vector_query],
        query_type="semantic",
        semantic_configuration_name=config.SEARCH_SEMANTIC_CONFIG,
        top=config.TOP_N_CHUNKS * 2,
        select=[
            "chunk_id", "content", "document_title",
            "page_number", "source_file", "source_url",
        ],
    )

    chunks: list[Chunk] = []
    for r in results:
        # Prefer reranker score (semantic), fall back to hybrid score
        score = r.get("@search.reranker_score") or r.get("@search.score", 0.0)
        chunks.append({
            "chunk_id": r["chunk_id"],
            "content": r["content"],
            "document_title": r.get("document_title", ""),
            "page_number": r.get("page_number"),
            "source_file": r.get("source_file", ""),
            "source_url": r.get("source_url", ""),
            "score": score,
            "is_web": False,
        })

    # ④ — Session Reranking: move previously-used documents to the front
    if docs_used:
        chunks.sort(key=lambda c: (c["source_file"] not in docs_used, -c["score"]))

    top_chunks = chunks[: config.TOP_N_CHUNKS]
    max_score = max((c["score"] for c in top_chunks), default=0.0)

    return top_chunks, max_score
